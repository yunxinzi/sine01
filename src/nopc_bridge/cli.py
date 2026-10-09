"""Phone-friendly CLI front end. Strict non-overclaim status & reproducibility."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
from . import __version__
from .fem3d import solve_bar, PhysicsError
from .outputs import write_native,sha256
from .external import audit_for,audit_inp,run_ccx,run_radioss,ExternalSolverError
from .verify import verify,VerificationError
from .jobs import preflight,execute_job
from .inp3d import solve_inp
from .ccx_bar import run_benchmark


def doctor():
    import importlib.util
    return {'version':__version__,'python':sys.version.split()[0],
       'numpy':importlib.util.find_spec('numpy') is not None,
       'scipy':importlib.util.find_spec('scipy') is not None,
       'nopc_cae_v02_installed':importlib.util.find_spec('nopc_cae') is not None,
       'calculix':next((shutil.which(x) for x in ['ccx','ccx_2.22','ccx_2.21','ccx_2.20'] if shutil.which(x)),None),
       'openradioss_starter':shutil.which('starter_linux64_gf'),
       'openradioss_engine':shutil.which('engine_linux64_gf'),
       'cloud_note':'diagnostics for THIS environment only, not Codex Cloud'}


def run_native(case_path,outdir,mode):
    p=Path(case_path)
    case=json.loads(p.read_text(encoding='utf-8'))
    if mode=='engineering':
        raise PhysicsError('Engineering certification cannot be granted automatically; request research/quick and independently validate')
    if Path(outdir).exists() and any(Path(outdir).iterdir()):
        raise PhysicsError('output directory must be empty to avoid mixing old & new results')
    mesh,u,strains,stress,vmis,summary=solve_bar(case)
    if summary['free_dof_residual_rel']>1e-7 or summary['force_balance_rel']>1e-7 or summary['energy_balance_rel']>1e-7:
        raise PhysicsError('numerical conservation checks failed')
    if 'analytic_relative_error' in summary and summary['analytic_relative_error']>1e-5:
        raise PhysicsError('analytic patch test failed')
    if mode=='research':
        meshes=[]
        for mult in (1,2,3):
            study_case=json.loads(json.dumps(case))
            for ax in ('nx','ny','nz'):study_case['mesh'][ax]*=mult
            _,_,_,_,_,one=solve_bar(study_case)
            meshes.append({'subdivisions':study_case['mesh'],'n_tets':one['elements'],
                           'mean_end_ux_m':one['mean_end_ux_m']})
        span=max(z['mean_end_ux_m'] for z in meshes)-min(z['mean_end_ux_m'] for z in meshes)
        denom=max(abs(meshes[-1]['mean_end_ux_m']),1e-25)
        summary['mesh_study']={'mesh_levels':meshes,'displacement_relative_span':float(span/denom),
          'interpretation':'uniform patch field only; not singularity/error estimator or experimental validation'}
        if span/denom>0.01:raise PhysicsError('mesh study indicates >1% response variation')
    summary['requested_quality_mode']=mode
    return write_native(outdir,p,case,mesh,u,strains,stress,vmis,summary,mode)


def bundle(folder,output):
    root=Path(folder).resolve();dst=Path(output).resolve()
    if not root.is_dir():raise ValueError('job directory missing')
    if dst.is_relative_to(root):raise ValueError('do not put the archive inside input job directory')
    files=[p for p in root.rglob('*') if p.is_file()]
    if any(p.is_symlink() for p in root.rglob('*')):raise ValueError('symlinks in job forbidden')
    from .verify import verify_folder
    verify_folder(root)  # block bundling stale, failed or corrupted results
    dst.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in files:z.write(p,arcname=p.relative_to(root))
    return {'zip':str(dst),'sha256':sha256(dst),'files':len(files)}


def main(argv=None):
    ap=argparse.ArgumentParser(prog='nopc-bridge',description='Verified FEM & AI cloud adapter (no external computing)')
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    for n in ['audit-inp','audit-for']:
        p=sub.add_parser(n);p.add_argument('file')
    p=sub.add_parser('run');p.add_argument('case');p.add_argument('--out',required=True);p.add_argument('--mode',choices=['quick','research','engineering'],default='quick')
    p=sub.add_parser('run-ccx');p.add_argument('file');p.add_argument('--out',required=True);p.add_argument('--exe');p.add_argument('--timeout',type=int,default=120);p.add_argument('--threads',type=int,default=2)
    p=sub.add_parser('ccx-bar');p.add_argument('--out',required=True);p.add_argument('--exe');p.add_argument('--timeout',type=int,default=120);p.add_argument('--threads',type=int,default=2)
    p=sub.add_parser('run-radioss');p.add_argument('starter_input');p.add_argument('engine_input');p.add_argument('--out',required=True);p.add_argument('--root');p.add_argument('--starter');p.add_argument('--engine');p.add_argument('--timeout',type=int,default=120);p.add_argument('--threads',type=int,default=2)
    p=sub.add_parser('bundle');p.add_argument('job_dir');p.add_argument('--out',required=True)
    p=sub.add_parser('solve-inp');p.add_argument('file');p.add_argument('--units',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('preflight');p.add_argument('case')
    p=sub.add_parser('verify');p.add_argument('artifact')
    p=sub.add_parser('run-job');p.add_argument('case');p.add_argument('--out',required=True);p.add_argument('--mode',choices=['quick','research'],default='quick');p.add_argument('--resume',action='store_true');p.add_argument('--max-attempts',type=int,default=3)
    opts=ap.parse_args(argv)
    try:
        if opts.command=='doctor':data=doctor()
        elif opts.command=='audit-inp':data=audit_inp(opts.file)
        elif opts.command=='audit-for':data=audit_for(opts.file)
        elif opts.command=='run':data=run_native(opts.case,opts.out,opts.mode)
        elif opts.command=='run-ccx':data=run_ccx(opts.file,opts.out,opts.exe,opts.timeout,opts.threads)
        elif opts.command=='ccx-bar':data=run_benchmark(opts.out,opts.exe,opts.timeout,opts.threads)
        elif opts.command=='run-radioss':data=run_radioss(opts.starter_input,opts.engine_input,opts.out,opts.root,opts.starter,opts.engine,opts.timeout,opts.threads)
        elif opts.command=='solve-inp':data=solve_inp(opts.file,opts.out,opts.units)
        elif opts.command=='preflight':data=preflight(json.loads(Path(opts.case).read_text(encoding='utf-8')))
        elif opts.command=='verify':data=verify(opts.artifact)
        elif opts.command=='run-job':data=execute_job(opts.case,opts.out,opts.mode,opts.resume,opts.max_attempts)
        else:data=bundle(opts.job_dir,opts.out)
        print(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False));return 0
    except (ExternalSolverError,PhysicsError,VerificationError,ValueError,KeyError,OSError,TypeError) as e:
        print(json.dumps({'status':'failed','message':str(e),'command':opts.command},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
