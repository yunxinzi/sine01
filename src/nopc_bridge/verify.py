"""Independent, fail-closed artifact auditing; NOT physical validation or certification.

Provenance hashes protect against accidental changes, not against an adversary
who controls both data and manifest. Field checks recompute constitutive stress
from stored displacement and geometry; they do not replace benchmark validation.
"""
from __future__ import annotations

import json
import math
import stat
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile

import numpy as np

from .outputs import sha256
from .fem3d import _tet_B, _constitutive, PhysicsError


class VerificationError(ValueError):
    pass


def _load_json(p: Path):
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise VerificationError(f'invalid/missing JSON: {p.name}') from exc
    if not isinstance(obj, dict):
        raise VerificationError(f'{p.name} must be an object')
    return obj


def _verified_files(folder: Path, manifest: dict):
    expected = manifest.get('files_sha256')
    if not isinstance(expected, dict) or not expected:
        raise VerificationError('missing per-file checksums')
    actual = {p.name for p in folder.iterdir() if p.is_file()}
    if actual != (set(expected) | {'manifest.json'}):
        raise VerificationError(f'file list mismatch: expected={sorted(expected)} actual={sorted(actual)}')
    for rel, digest in expected.items():
        if Path(rel).name != rel or len(digest) != 64 or not (folder/rel).is_file():
            raise VerificationError('invalid manifest file entry')
        if (folder/rel).is_symlink() or sha256(folder/rel) != digest:
            raise VerificationError(f'checksum mismatch: {rel}')
    return len(expected)


def _numeric_check(folder: Path):
    case = _load_json(folder/'case_used.json')
    result = _load_json(folder/'result.json')
    is_inp=case.get('analysis')=='linear_elastic_static_C3D4_inp'
    if case.get('analysis') not in ('linear_elastic_static_3d_bar','linear_elastic_static_C3D4_inp'):
        raise VerificationError('unknown native physics model')
    if result.get('status') != 'computed_not_experimentally_validated':
        raise VerificationError('not a successful native result')
    try:
        with np.load(folder/'fields.npz', allow_pickle=False) as data:
            xyz = data['nodes']; tets = data['tets']; u = data['displacement_m']
            strain = data['strain']; stress = data['stress_pa']; vm = data['von_mises_pa']
    except (OSError, ValueError, KeyError) as exc:
        raise VerificationError('could not load raw numerical field arrays') from exc
    ne,nn = len(tets),len(xyz)
    if (xyz.shape != (nn,3) or tets.shape != (ne,4) or
        u.shape != (nn,3) or strain.shape != (ne,6) or
        stress.shape != (ne,6) or vm.shape != (ne,)):
        raise VerificationError('incorrect numerical array shape')
    if not nn or not ne or not np.issubdtype(tets.dtype,np.integer):
        raise VerificationError('empty or nonintegral mesh')
    if np.any(tets < 0) or np.any(tets >= nn):
        raise VerificationError('out-of-range connectivity')
    if not all(np.all(np.isfinite(a)) for a in (xyz,u,strain,stress,vm)):
        raise VerificationError('nonfinite numerical output')
    try:
        D = _constitutive(float(case['material']['young_pa']),float(case['material']['poisson']))
        for i,tet in enumerate(tets):
            B,_ = _tet_B(xyz[tet])
            eps = B @ u[tet].reshape(12)
            sigma = D @ eps
            if not np.allclose(eps,strain[i],rtol=2e-8,atol=1e-12):
                raise VerificationError(f'strain mismatch element {i}')
            if not np.allclose(sigma,stress[i],rtol=2e-8,atol=1e-3):
                raise VerificationError(f'stress mismatch element {i}')
    except (PhysicsError, ValueError, KeyError) as exc:
        raise VerificationError(f'constitutive recheck failed: {exc}') from exc
    recalc = np.sqrt(.5*((stress[:,0]-stress[:,1])**2+
                           (stress[:,1]-stress[:,2])**2+
                           (stress[:,2]-stress[:,0])**2)+
                      3*(stress[:,3]**2+stress[:,4]**2+stress[:,5]**2))
    if not np.allclose(recalc,vm,rtol=1e-8,atol=1e-4):
        raise VerificationError('von Mises field is inconsistent')
    if is_inp:
        if not (folder/'source.inp').is_file() or sha256(folder/'source.inp')!=case['input_sha256']:
            raise VerificationError('original imported INP was altered')
        if not np.allclose(np.asarray(case['nodes_xyz_m']),xyz,rtol=0,atol=1e-14):
            raise VerificationError('nodes do not match imported model')
        if not np.array_equal(np.asarray(case['tets_zero_based']),tets):
            raise VerificationError('elements do not match imported model')
        try:
            force=np.asarray(case['nodal_loads_n'],dtype=float).reshape(-1)
            fixed=np.asarray(case['fixed_dof_zero_based'],dtype=int)
            if force.shape!=(3*nn,) or not len(fixed) or np.any(fixed<0) or np.any(fixed>=3*nn):
                raise ValueError('wrong load/constraint dimensions')
            if not np.all(np.isfinite(force)):
                raise ValueError('nonfinite nodal loads')
            internal=np.zeros(3*nn)
            elastic_energy=0.0
            for i,tet in enumerate(tets):
                B,vol=_tet_B(xyz[tet])
                dofs=np.array([3*int(n)+d for n in tet for d in range(3)])
                internal[dofs] += vol*(B.T@stress[i])
                elastic_energy += .5*vol*float(strain[i]@stress[i])
            free=np.setdiff1d(np.arange(3*nn),fixed)
            residual=internal-force
            reaction=np.array([residual[fixed[fixed%3==a]].sum() for a in range(3)])
            applied=force.reshape(-1,3).sum(axis=0)
            force_error=float(np.linalg.norm(reaction+applied)/max(np.linalg.norm(applied),np.linalg.norm(force),1e-12))
            free_error=float(np.linalg.norm(residual[free])/max(np.linalg.norm(force[free]),1e-12))
            work=float(u.reshape(-1)@force)
            energy_error=abs(2*elastic_energy-work)/max(abs(work),1e-12)
            if max(force_error,free_error,energy_error)>1e-7:
                raise VerificationError('recomputed force/residual/energy gate failed')
            if not np.allclose(applied,np.asarray(result['applied_force_xyz_n']),rtol=1e-7,atol=1e-8):
                raise VerificationError('reported applied resultant mismatch')
            if not np.allclose(reaction,np.asarray(result['support_reaction_xyz_n']),rtol=1e-7,atol=1e-8):
                raise VerificationError('reported support reaction mismatch')
        except (ValueError,KeyError,TypeError) as exc:
            raise VerificationError(f'failed to reassemble nodal equilibrium: {exc}') from exc
        if not np.isclose(np.linalg.norm(u,axis=1).max(),result['max_displacement_m'],rtol=1e-8,atol=1e-14):
            raise VerificationError('reported max displacement mismatch')
        if not np.isclose(np.max(vm),result['max_von_mises_pa'],rtol=1e-8,atol=1e-3):
            raise VerificationError('reported maximum stress mismatch')
        for name in ('force_balance_rel','energy_balance_rel','free_dof_residual_rel'):
            value=float(result[name])
            if not math.isfinite(value) or not 0<=value<=1e-7:
                raise VerificationError(f'numerical check unacceptable: {name}')
        return {'nodes':nn,'elements':ne,'max_vm_pa':float(np.max(vm)),
                'max_displacement_m':float(np.linalg.norm(u,axis=1).max()),
                'method':'recompute material stress, internal forces, residual and energy (not experimental validation)'}
    end = np.isclose(xyz[:,0],float(case['geometry']['length_m']),rtol=1e-12,atol=1e-14)
    if not np.any(end) or not np.isclose(np.mean(u[end,0]),result['mean_end_ux_m'],rtol=1e-8,atol=1e-14):
        raise VerificationError('reported tip displacement mismatch')
    if not np.isclose(np.max(vm),result['max_von_mises_pa'],rtol=1e-8,atol=1e-3):
        raise VerificationError('reported maximum stress mismatch')
    for name in ('force_balance_rel','energy_balance_rel','free_dof_residual_rel'):
        number = float(result[name])
        if not math.isfinite(number) or not (0 <= number <= 1e-7):
            raise VerificationError(f'numerical check unacceptable: {name}')
    # Closed form is an applicable comparison only for Poisson=0 uniform axial extension.
    if float(case['material']['poisson']) == 0:
        exact = (float(case['load_x_n'])*float(case['geometry']['length_m']) /
                 (float(case['material']['young_pa'])*float(case['geometry']['width_m'])*
                  float(case['geometry']['height_m'])))
        if not np.isclose(np.mean(u[end,0]),exact,rtol=1e-5,atol=1e-13):
            raise VerificationError('analytical extension test failed')
    return {'nodes':nn,'elements':ne,'max_vm_pa':float(np.max(vm)),
            'mean_tip_ux_m':float(np.mean(u[end,0])),
            'method':'stored fields vs constitutive law + limited analytic/summary gates'}


def verify_folder(folder):
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise VerificationError('job directory not found')
    manifest_file = folder/'manifest.json'
    if manifest_file.is_file():
        m = _load_json(manifest_file)
        n = _verified_files(folder,m)
        nresult = _numeric_check(folder)
        return {'status':'verified_artifact_and_limited_numerical_consistency',
                'kind':'native','files_checked':n,'numerics':nresult,
                'scope':'Not an experimental validation, not industrial certification'}
    if (folder/'external_manifest.json').is_file():
        m = _load_json(folder/'external_manifest.json')
        if m.get('status') != 'solver_executed_output_unvalidated':
            raise VerificationError('external solver did not finish successfully')
        hashes = m.get('output_sha256')
        if not isinstance(hashes,dict) or not hashes:
            raise VerificationError('external solver outputs lack per-file checksums')
        work = folder/'workspace'
        for filename,digest in hashes.items():
            fp = work/filename
            if Path(filename).name != filename or fp.is_symlink() or not fp.is_file() or sha256(fp)!=digest:
                raise VerificationError('external solver output checksum mismatch')
        return {'status':'verified_output_hashes_only','kind':'external',
                'files_checked':len(hashes),'scope':'Solver result has NOT been physically or independently verified'}
    if (folder/'journal.json').is_file():
        journal = _load_json(folder/'journal.json')
        if journal.get('status')!='completed':
            raise VerificationError('job is incomplete')
        if (folder/'input.json').is_symlink() or sha256(folder/'input.json') != journal['input_sha256']:
            raise VerificationError('journal source input checksum mismatch')
        result_path=folder/journal['latest_output']
        if not result_path.resolve().is_relative_to(folder):
            raise VerificationError('journal output path escapes job')
        nested=verify_folder(result_path)
        return {'status':'verified_completed_job','kind':'job','attempts':journal.get('attempts'),
                'result':nested}
    raise VerificationError('no recognizable calculation manifest')


def _safe_member(info):
    name = info.filename
    p = PurePosixPath(name)
    if (not name or name.startswith('/') or '\\' in name or '..' in p.parts or
        any(part in ('','.','..') for part in p.parts) or ':' in name):
        raise VerificationError('unsafe archive entry')
    if stat.S_ISLNK(info.external_attr >> 16):
        raise VerificationError('ZIP symlinks forbidden')


def verify(target):
    p = Path(target)
    if p.is_dir():
        return verify_folder(p)
    if not p.is_file() or p.suffix.lower() != '.zip':
        raise VerificationError('specify a job directory or .zip archive')
    try:
        with ZipFile(p) as z:
            members=z.infolist()
            if len(members)>20000 or sum(x.file_size for x in members)>512*1024*1024:
                raise VerificationError('archive exceeds conservative verification limits')
            if len({x.filename for x in members}) != len(members):
                raise VerificationError('duplicate archive members')
            for entry in members:
                _safe_member(entry)
            if z.testzip():
                raise VerificationError('corrupted ZIP member')
            with tempfile.TemporaryDirectory(prefix='nopc-verify-') as td:
                z.extractall(td)
                result=verify_folder(Path(td))
    except BadZipFile as exc:
        raise VerificationError('invalid ZIP archive') from exc
    return {'archive_sha256':sha256(p),**result}
