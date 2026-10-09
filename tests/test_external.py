from pathlib import Path
import json
import pytest
from nopc_bridge.external import audit_inp,audit_for,run_ccx,run_radioss,ExternalSolverError


def _fake_exe(p,body):
    p.write_text('#!/usr/bin/env python3\n'+body)
    p.chmod(0o755)
    return str(p)


def test_audit_rejects_fortran_user_material(tmp_path):
    deck=tmp_path/'case.inp'
    deck.write_text('*HEADING\n*USER MATERIAL, CONSTANTS=1\n1\n*DEPVAR\n1\n')
    result=audit_inp(deck)
    assert len(result['user_subroutine_related_keywords'])==2
    with pytest.raises(ExternalSolverError,match='user material'):run_ccx(deck,tmp_path/'out',exe=_fake_exe(tmp_path/'ccx','print("unused")'))


def test_for_audit_no_exec(tmp_path):
    f=tmp_path/'m.for';f.write_text('      SUBROUTINE VUMAT(\n      END\n')
    result=audit_for(f)
    assert result['abaqus_interface_candidates']==['VUMAT']
    assert result['status'].startswith('audit_only')


def test_ccx_protocol_mock_only(tmp_path):
    exe=_fake_exe(tmp_path/'fake_ccx', 'import sys, pathlib\npathlib.Path(sys.argv[1]+".frd").write_text("FAKE RESULT FOR ADAPTER TEST")\n')
    deck=tmp_path/'sample.inp';deck.write_text('*HEADING\n*NODE\n1,0,0,0\n')
    result=run_ccx(deck,tmp_path/'out',exe=exe)
    assert result['status']=='solver_executed_output_unvalidated'
    assert 'sample.frd' in result['outputs']
    assert result['validation']=='not_independently_validated'


def test_ccx_missing_result_detected(tmp_path):
    exe=_fake_exe(tmp_path/'fake_ccx','print("apparently succeeded without FRD")')
    deck=tmp_path/'sample.inp';deck.write_text('*HEADING\n')
    with pytest.raises(ExternalSolverError,match='no nonempty FRD'):
        run_ccx(deck,tmp_path/'out',exe=exe)
    status=json.loads((tmp_path/'out'/'external_manifest.json').read_text())
    assert status['status']=='failed'


def test_include_path_traversal_rejected(tmp_path):
    inside=tmp_path/'inside';inside.mkdir()
    outside=tmp_path/'outside.inp';outside.write_text('*NODE\n')
    deck=inside/'sample.inp';deck.write_text('*INCLUDE, INPUT=../outside.inp\n')
    exe=_fake_exe(tmp_path/'fake_ccx','print("nothing")')
    with pytest.raises(ExternalSolverError,match='escapes input directory'):
        run_ccx(deck,tmp_path/'out',exe=exe)


def test_missing_binary_rejected(tmp_path):
    deck=tmp_path/'model.inp';deck.write_text('*HEADING\n')
    with pytest.raises(ExternalSolverError,match='not available'):
        run_ccx(deck,tmp_path/'out',exe=str(tmp_path/'definitely_missing_ccx'))


def test_radioss_adapter_mock_only(tmp_path):
    starter=_fake_exe(tmp_path/'mock_starter', 'from pathlib import Path\nPath("starter_result.out").write_text("nonphysical mock")')
    engine=_fake_exe(tmp_path/'mock_engine','from pathlib import Path\nPath("engine_result.out").write_text("nonphysical mock")')
    st=tmp_path/'model_0000.rad';st.write_text('/BEGIN\n')
    en=tmp_path/'model_0001.rad';en.write_text('/RUN\n')
    result=run_radioss(st,en,tmp_path/'results',starter=starter,engine=engine)
    assert result['status']=='solver_executed_output_unvalidated'
    assert len(result['outputs'])==2
