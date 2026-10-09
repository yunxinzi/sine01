"""Fail-closed external solver launchers, never claiming benchmark validation."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from .outputs import sha256


class ExternalSolverError(RuntimeError):
    pass


def _command(binary, guessed_names):
    if binary:
        resolved = shutil.which(binary) or (str(Path(binary).resolve()) if Path(binary).is_file() else None)
    else:
        resolved=next((shutil.which(x) for x in guessed_names if shutil.which(x)),None)
    if not resolved:
        raise ExternalSolverError(f"solver executable not available ({', '.join(guessed_names)})")
    return resolved


def _write_status(out, data):
    out.mkdir(parents=True,exist_ok=True)
    (out/'external_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def _run_capture(args,cwd,outfile,timeout,env=None):
    start=time.monotonic()
    with open(outfile,'w',encoding='utf-8') as f:
        try:
            cp=subprocess.run(args,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,
                              env=env,check=False)
        except subprocess.TimeoutExpired as e:
            raise ExternalSolverError(f"solver timed out after {timeout}s; no success claim") from e
    if cp.returncode != 0:
        raise ExternalSolverError(f"solver exited {cp.returncode}, see {outfile.name}")
    return round(time.monotonic()-start,4)


def audit_inp(input_path: str):
    p=Path(input_path)
    text=p.read_text(encoding='utf-8',errors='replace')
    keywords=[x.strip() for x in text.splitlines() if x.lstrip().startswith('*') and not x.lstrip().startswith('**')]
    includes=[]
    for kw in keywords:
        if kw.upper().startswith('*INCLUDE'):
            m=re.search(r'INPUT\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^,]+))',kw,re.I)
            includes.append(next((g.strip() for g in m.groups() if g), 'UNPARSEABLE INCLUDE') if m else 'UNPARSEABLE INCLUDE')
    unsupported=[kw for kw in keywords if any(w in kw.upper() for w in ('*USER MATERIAL','*UEL','*DEPVAR','*USDFLD','*DLOAD, USER', '*CREEP, LAW=USER'))]
    analysis = {
      'file':str(p), 'sha256':sha256(p), 'keywords':keywords,'include_targets':includes,
      'user_subroutine_related_keywords':unsupported,
      'message':'Audit only; does not certify Abaqus compatibility or correct physics.'}
    return analysis


def audit_for(path: str):
    p=Path(path); txt=p.read_text(encoding='utf-8',errors='replace')
    names=re.findall(r'^\s*(?:subroutine|recursive\s+subroutine)\s+(\w+)\s*\(',txt,flags=re.I|re.M)
    return {'file':str(p),'sha256':sha256(p),'subroutines':names,
            'abaqus_interface_candidates':[n for n in names if n.upper() in ('UMAT','VUMAT','VUSDFLD','USDFLD','UEL','VUEL')],
            'status':'audit_only_no_fortran_execution_or_interface_port'}


def _copy_deck_and_includes(deck, out):
    # Do not resolve away symlink evidence before checking each path component.
    original=Path(deck).absolute()
    if original.is_symlink() or not original.is_file():
        raise ExternalSolverError('input deck must be a regular, nonsymlink file')
    src=original.resolve(strict=True)
    if src.suffix.lower() != '.inp':raise ExternalSolverError('CalculiX input must have .inp extension')
    data=audit_inp(src)
    if data['user_subroutine_related_keywords']:
        raise ExternalSolverError('Abaqus user material/custom element detected; explicit verified port required')
    out.mkdir(parents=True,exist_ok=True)
    root=src.parent
    files=[src]
    seen=set()
    while files:
        f=files.pop()
        if f in seen:continue
        seen.add(f)
        try: rel=f.relative_to(root)
        except ValueError:raise ExternalSolverError('INCLUDE path escapes input directory')
        if not f.is_file() or f.is_symlink():
            raise ExternalSolverError('symlink/missing INCLUDE forbidden')
        dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(f,dst)
        audit=audit_inp(f)
        if audit['user_subroutine_related_keywords']:
            raise ExternalSolverError('user subroutine/custom keyword found in INCLUDE')
        for name in audit['include_targets']:
            raw=Path(name)
            if raw.is_absolute() or '..' in raw.parts:
                raise ExternalSolverError('INCLUDE path escapes input directory')
            if name=='UNPARSEABLE INCLUDE' or not raw.parts:
                raise ExternalSolverError('unsafe or unparseable INCLUDE target')
            # Prevent symlink escapes even when canonical resolved path lies within root.
            cur=f.parent
            for part in raw.parts:
                cur=cur/part
                if cur.is_symlink():
                    raise ExternalSolverError('symlink INCLUDE forbidden')
            nxt=cur.resolve()
            if not nxt.is_relative_to(root):
                raise ExternalSolverError('INCLUDE path escapes input directory')
            if not nxt.is_file():raise ExternalSolverError(f'missing INCLUDE: {name}')
            if nxt not in seen:files.append(nxt)
    return data, [str(i.relative_to(root)) for i in sorted(seen)]


def run_ccx(deck, outdir, exe=None, timeout=120, threads=2):
    if not 0 < timeout <= 86400:raise ExternalSolverError('timeout must be 1..86400 seconds')
    binary=_command(exe,['ccx','ccx_2.22','ccx_2.21','ccx_2.20'])
    out=Path(outdir).resolve()
    if out.exists() and any(out.iterdir()):raise ExternalSolverError('output directory must be empty to avoid stale result detection')
    job=out/'workspace';audit,includes=_copy_deck_and_includes(deck,job)
    run_stem=Path(deck).stem
    if re.search(r'[^\w.-]',run_stem):raise ExternalSolverError('unsafe input basename')
    env=os.environ.copy();env['OMP_NUM_THREADS']=str(max(1,min(threads,8)))
    manifest={'solver':'CalculiX','binary':binary,'input':str(deck),'input_sha256':sha256(deck),
              'includes':includes,'status':'running','validation':'not_independently_validated'}
    try:
        elapsed=_run_capture([binary,run_stem],job,out/'ccx.log',timeout,env)
        products=[p.name for p in job.iterdir() if p.suffix.lower() in ('.frd','.dat','.sta') and p.stat().st_size>0]
        if not any(x.endswith('.frd') for x in products):
            raise ExternalSolverError('ccx finished but no nonempty FRD produced; no success claim')
        manifest.update(status='solver_executed_output_unvalidated',elapsed_s=elapsed,outputs=products,output_sha256={x:sha256(job/x) for x in products})
    except Exception as e:
        manifest.update(status='failed',error=str(e))
        _write_status(out,manifest)
        raise
    _write_status(out,manifest)
    return manifest


def run_radioss(starter_input, engine_input, outdir, root=None, starter=None, engine=None, timeout=120, threads=2):
    if not 0 < timeout <= 86400:raise ExternalSolverError('timeout must be 1..86400 seconds')
    root=Path(root).resolve() if root else None
    stb=str(root/'exec'/'starter_linux64_gf') if root and not starter else starter
    eng=str(root/'exec'/'engine_linux64_gf') if root and not engine else engine
    starter_bin=_command(stb,['starter_linux64_gf'])
    engine_bin=_command(eng,['engine_linux64_gf'])
    src1,src2=Path(starter_input).resolve(),Path(engine_input).resolve()
    if not (src1.is_file() and src2.is_file()):raise ExternalSolverError('both Starter/Engine deck files required')
    out=Path(outdir).resolve()
    if out.exists() and any(out.iterdir()):raise ExternalSolverError('output directory must be empty')
    work=out/'workspace';work.mkdir(parents=True)
    for p in (src1,src2):shutil.copy2(p,work/p.name)
    env=os.environ.copy();env['OMP_NUM_THREADS']=str(max(1,min(threads,8)))
    env['OMP_STACKSIZE']='400m'
    if root:
        env['OPENRADIOSS_PATH']=str(root)
        env['RAD_CFG_PATH']=str(root/'hm_cfg_files')
        env['RAD_H3D_PATH']=str(root/'extlib'/'h3d'/'lib'/'linux64')
        libpaths=[str(root/'extlib'/'hm_reader'/'linux64'),str(root/'extlib'/'h3d'/'lib'/'linux64')]
        env['LD_LIBRARY_PATH']=':'.join(libpaths+[env.get('LD_LIBRARY_PATH','')])
    status={'solver':'OpenRadioss','binary_starter':starter_bin,'binary_engine':engine_bin,
            'inputs':{src1.name:sha256(src1),src2.name:sha256(src2)},'status':'running',
            'validation':'not_independently_validated'}
    try:
        t1=_run_capture([starter_bin,'-i',src1.name,'-np','1'],work,out/'starter.log',timeout,env)
        t2=_run_capture([engine_bin,'-i',src2.name],work,out/'engine.log',timeout,env)
        # RadiOSS may emit many different output suffixes. Record exact newly created files;
        # successful process alone is not sufficient to call physics validated.
        outputs=[f.name for f in work.iterdir() if f.is_file() and f.name not in (src1.name,src2.name) and f.stat().st_size>0]
        if not outputs:raise ExternalSolverError('no result files from radioss; no success claim')
        status.update(status='solver_executed_output_unvalidated',elapsed_s=t1+t2,outputs=outputs,output_sha256={x:sha256(work/x) for x in outputs})
    except Exception as e:
        status.update(status='failed',error=str(e))
        _write_status(out,status)
        raise
    _write_status(out,status)
    return status
