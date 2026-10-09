"""Regression + adversarial checks for provenance and job recovery."""
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from nopc_bridge.cli import run_native,bundle
from nopc_bridge.external import audit_inp,run_ccx,ExternalSolverError
from nopc_bridge.jobs import preflight,execute_job
from nopc_bridge.outputs import sha256
from nopc_bridge.verify import verify,verify_folder,VerificationError

BASE={'analysis':'linear_elastic_static_3d_bar','geometry':{'length_m':1,'width_m':.1,'height_m':.1},
      'mesh':{'nx':2,'ny':1,'nz':1},'material':{'young_pa':70e9,'poisson':0},'load_x_n':100}


def _case(tmp_path):
    p=tmp_path/'case.json';p.write_text(json.dumps(BASE));return p


def test_preflight_rejects_arbitrary_impact():
    case=dict(BASE,analysis='impact_damage')
    report=preflight(case)
    assert report['supported'] is False
    assert report['status']=='rejected_unsupported_physics'


def test_preflight_int_and_estimate():
    d=preflight(BASE)
    assert d['supported'] and d['elements_expected']==12
    assert d['checkpoint_available'] is False
    c=json.loads(json.dumps(BASE));c['mesh']['nx']=2.5
    assert not preflight(c)['supported']


def test_native_verify_and_zip(tmp_path):
    case=_case(tmp_path);dest=tmp_path/'case_out'
    run_native(case,dest,'quick')
    report=verify(dest)
    assert report['status']=='verified_artifact_and_limited_numerical_consistency'
    archive=tmp_path/'complete.zip'
    bundle(dest,archive)
    assert verify(archive)['status']==report['status']


def test_native_tamper_checksum_detected(tmp_path):
    case=_case(tmp_path); dest=tmp_path/'result'
    run_native(case,dest,'quick')
    (dest/'result.json').write_text('{}')
    with pytest.raises(VerificationError,match='checksum mismatch'):
        verify(dest)
    with pytest.raises(VerificationError,match='checksum mismatch'):
        bundle(dest,tmp_path/'never.zip')


def test_native_tamper_stress_detected_even_with_rehashed_manifest(tmp_path):
    case=_case(tmp_path);dest=tmp_path/'result';run_native(case,dest,'quick')
    path=dest/'fields.npz'
    with np.load(path) as data:
        arrays={k:data[k].copy() for k in data.files}
    arrays['stress_pa'][0,0]+=1e7
    np.savez_compressed(path,**arrays)
    manifest_path=dest/'manifest.json';m=json.loads(manifest_path.read_text())
    m['files_sha256']['fields.npz']=sha256(path)
    manifest_path.write_text(json.dumps(m))
    with pytest.raises(VerificationError,match='stress mismatch'):
        verify(dest)


def test_job_resumes_completed_without_recomputation(tmp_path):
    case=_case(tmp_path);root=tmp_path/'session'
    run=execute_job(case,root,mode='quick')
    assert run['status']=='completed_verified_limited'
    again=execute_job(case,root,mode='quick',resume=True)
    assert again['status']=='already_completed_verified'
    assert len(json.loads((root/'journal.json').read_text())['attempts'])==1
    assert verify(root)['status']=='verified_completed_job'
    archive=tmp_path/'journal.zip';bundle(root,archive)
    assert verify(archive)['kind']=='job'


def test_job_failed_attempt_preserved_then_retried(tmp_path,monkeypatch):
    case=_case(tmp_path);root=tmp_path/'session'
    import nopc_bridge.cli as cli
    original=cli.run_native
    def broken(*args,**kwargs):
        p=Path(args[1]);p.mkdir(parents=True)
        (p/'failure.log').write_text('simulated interruption')
        raise RuntimeError('simulated interruption')
    monkeypatch.setattr(cli,'run_native',broken)
    with pytest.raises(RuntimeError,match='interruption'):
        execute_job(case,root)
    assert (root/'attempts/attempt_001/failure.log').exists()
    monkeypatch.setattr(cli,'run_native',original)
    r=execute_job(case,root,resume=True)
    assert r['attempt']==2
    assert (root/'attempts/attempt_001/failure.log').exists()
    assert (root/'attempts/attempt_002/manifest.json').exists()
    assert [a['status'] for a in json.loads((root/'journal.json').read_text())['attempts']]==['failed','completed']


def test_job_changed_input_rejected(tmp_path):
    case=_case(tmp_path);root=tmp_path/'job';execute_job(case,root)
    new=json.loads(case.read_text());new['load_x_n']=200;case.write_text(json.dumps(new))
    with pytest.raises(ValueError,match='changed case'):
        execute_job(case,root,resume=True)


def test_incomplete_job_not_bundled(tmp_path):
    root=tmp_path/'f';root.mkdir();(root/'journal.json').write_text('{"status":"running"}')
    with pytest.raises(VerificationError,match='incomplete'):
        bundle(root,tmp_path/'bad.zip')


def test_archive_path_traversal_rejected(tmp_path):
    zp=tmp_path/'evil.zip'
    with zipfile.ZipFile(zp,'w') as z:z.writestr('../escape','evil')
    with pytest.raises(VerificationError,match='unsafe'):
        verify(zp)


def test_include_quoted_name_and_symlink_denied(tmp_path):
    root=tmp_path/'inputs';root.mkdir()
    deck=root/'bar.inp';deck.write_text('*INCLUDE, INPUT="some file.inp"\n')
    child=root/'some file.inp';child.write_text('*NODE\n1,0,0,0\n')
    assert audit_inp(deck)['include_targets']==['some file.inp']
    fake=tmp_path/'fake';fake.write_text('#!/bin/sh\necho mock > bar.frd\n');fake.chmod(0o755)
    run_ccx(deck,tmp_path/'ok',exe=str(fake))
    assert verify(tmp_path/'ok')['status']=='verified_output_hashes_only'
    child.unlink();real=tmp_path/'elsewhere';real.write_text('*NODE\n')
    child.symlink_to(real)
    with pytest.raises(ExternalSolverError,match='symlink'):
        run_ccx(deck,tmp_path/'blocked',exe=str(fake))
