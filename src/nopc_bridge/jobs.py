"""Durable finite-element job journal: safe restart, NOT numerical checkpoint recovery.

Each attempt is immutable by naming. Running the native sparse solver after failure
starts the entire solve again. Journal enables retry and evidence recovery after
an interrupted Agent session; genuine solver checkpointing is not implemented.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

from .outputs import sha256
from .fem3d import PhysicsError, _constitutive
from .verify import verify_folder, VerificationError


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(dest, data):
    tmp=dest.with_name(dest.name+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    os.replace(tmp,dest)


def preflight(case):
    if not isinstance(case,dict) or case.get('analysis')!='linear_elastic_static_3d_bar':
        return {'supported':False,'status':'rejected_unsupported_physics',
                'reason':'This package natively solves ONLY a uniform 3D linear-elastic static bar; external solvers require separate validated decks'}
    try:
        g=case['geometry'];m=case['mesh'];mat=case['material']
        nx,ny,nz=(m[k] for k in ('nx','ny','nz'))
        if any(type(v) is not int or not 1<=v<=100 for v in (nx,ny,nz)):
            raise ValueError('mesh subdivisions must be integers in 1..100')
        lengths=[float(g[k]) for k in ('length_m','width_m','height_m')]
        if not all(math.isfinite(v) and v>0 for v in lengths):
            raise ValueError('geometry must have positive finite SI lengths')
        _constitutive(float(mat['young_pa']),float(mat['poisson']))
        force=float(case['load_x_n'])
        if not math.isfinite(force):raise ValueError('load must be finite')
        els=nx*ny*nz*6;nodes=(nx+1)*(ny+1)*(nz+1)
        if els>250000:raise ValueError('native solver 250000-element limit')
        # Conservative heuristic, not a measured peak-memory guarantee.
        ram_guess=int(els*2500+nodes*5000)
        return {'supported':True,'status':'preflight_passed','solver':'native_c3d4',
                'elements_expected':els,'nodes_expected':nodes,
                'ram_heuristic_mib':round(ram_guess/2**20,1),
                'resource_warning':'RAM is an order-of-magnitude heuristic, not an enforced quota',
                'checkpoint_available':False,'genuine_resume_available':False,
                'unit_system':'SI','model_scope':'small strain, static, isotropic, no composites or contact'}
    except (KeyError,TypeError,ValueError,OverflowError) as exc:
        return {'supported':False,'status':'rejected_invalid_case','reason':str(exc)}


def execute_job(case_file,job_dir,mode='quick',resume=False,max_attempts=3):
    from .cli import run_native   # avoid cyclical import during CLI initialization
    source=Path(case_file).resolve();root=Path(job_dir).resolve()
    if not source.is_file():raise PhysicsError('input case JSON does not exist')
    case=json.loads(source.read_text(encoding='utf-8'))
    decision=preflight(case)
    if not decision['supported']:
        raise PhysicsError(f'preflight denied: {decision["reason"]}')
    if mode not in ('quick','research'):
        raise PhysicsError('job quality request is quick or research; no industrial certification')
    if not 1<=max_attempts<=10:raise PhysicsError('max_attempts must be within 1..10')
    case_hash=sha256(source)
    journal_file=root/'journal.json'
    if root.exists() and not root.is_dir():raise PhysicsError('job destination is not a directory')
    if journal_file.is_file():
        if not resume:raise PhysicsError('job already exists, specify --resume to inspect or retry')
        journal=json.loads(journal_file.read_text(encoding='utf-8'))
        if case_hash!=journal['input_sha256'] or mode!=journal['mode']:
            raise PhysicsError('cannot resume with changed case or quality mode')
        if (root/'input.json').is_symlink() or sha256(root/'input.json') != case_hash:
            raise PhysicsError('saved source input was changed after job creation')
        if journal['status']=='completed':
            try:
                audited=verify_folder(root)
            except VerificationError as e:
                raise PhysicsError(f'completed job integrity failed: {e}') from e
            return {'status':'already_completed_verified','job':str(root),'verification':audited,
                    'notes':'No new computation; reuses existing verified calculation artifacts'}
    else:
        if resume:raise PhysicsError('no previous job to resume')
        if root.exists() and any(root.iterdir()):
            raise PhysicsError('job directory must start empty')
        root.mkdir(parents=True,exist_ok=True)
        copy2(source,root/'input.json')
        journal={'format_version':1,'status':'created','mode':mode,'created_utc':_utc(),
                 'input_sha256':case_hash,'preflight':decision,'attempts':[],
                 'resume_semantics':'restart entire calculation; NO solver state/checkpoint available'}
    attempts=journal['attempts']
    if len(attempts)>=max_attempts:
        raise PhysicsError('retry count reached configured limit; preserve failed files and diagnose before proceeding')
    number=len(attempts)+1
    out_rel=f'attempts/attempt_{number:03d}'
    out=root/out_rel
    out.parent.mkdir(parents=True,exist_ok=True)
    attempt={'number':number,'status':'running','start_utc':_utc(),'output':out_rel}
    attempts.append(attempt)
    journal.update(status='running',latest_output=out_rel,updated_utc=_utc())
    _atomic_json(journal_file,journal)
    try:
        summary=run_native(root/'input.json',out,mode)
        checked=verify_folder(out)
        attempt.update(status='completed',end_utc=_utc(),verification_status=checked['status'])
        journal.update(status='completed',updated_utc=_utc())
        _atomic_json(journal_file,journal)
        return {'status':'completed_verified_limited','job':str(root),'attempt':number,
                'latest_output':out_rel,'result':summary,'verification':checked}
    except Exception as exc:
        attempt.update(status='failed',end_utc=_utc(),error=f'{type(exc).__name__}: {exc}')
        journal.update(status='failed',updated_utc=_utc())
        _atomic_json(journal_file,journal)
        raise
