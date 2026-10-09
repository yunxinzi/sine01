"""Actual FE execution and strict parser rejection tests for restricted INP files."""
import json
from pathlib import Path
import numpy as np
import pytest
from nopc_bridge.inp3d import parse_inp,solve_inp
from nopc_bridge.verify import verify
from nopc_bridge.fem3d import PhysicsError

BASE='''*HEADING
Minimal C3D4 with explicit SI units assumed by caller.
*NODE
1,0,0,0
2,1,0,0
3,0,1,0
4,0,0,1
*ELEMENT,TYPE=C3D4,ELSET=SOLID
1,1,2,3,4
*MATERIAL,NAME=M
*ELASTIC
70000,0.3
*SOLID SECTION,ELSET=SOLID,MATERIAL=M
*NSET,NSET=SUPPORT
1,2,3
*BOUNDARY
SUPPORT,1,3,0
*STEP
*STATIC
*CLOAD
4,3,-100
*END STEP
'''


def test_c3d4_inp_physics_and_reaction(tmp_path):
    f=tmp_path/'test.inp';f.write_text(BASE)
    result=solve_inp(f,tmp_path/'out','SI')
    assert result['elements']==1
    assert np.isclose(result['support_reaction_xyz_n'][2],100)
    assert result['max_displacement_m']>0
    assert result['energy_balance_rel']<1e-9
    verified=verify(tmp_path/'out')
    assert verified['kind']=='native'
    assert (tmp_path/'out'/'source.inp').read_text()==BASE


def test_requires_units(tmp_path):
    f=tmp_path/'m.inp';f.write_text(BASE)
    with pytest.raises(PhysicsError,match='Abaqus INP has no declared units'):
        solve_inp(f,tmp_path/'result','mm')


@pytest.mark.parametrize('bad_keyword',['*DYNAMIC','*USER MATERIAL,CONSTANTS=3','*CONTACT','*SOLID SECTION,ELSET=SOLID,MATERIAL=WRONG'])
def test_unsupported_inp_fails_closed(tmp_path,bad_keyword):
    f=tmp_path/'m.inp'
    if bad_keyword.startswith('*SOLID SECTION'):
        src=BASE.replace('*SOLID SECTION,ELSET=SOLID,MATERIAL=M',bad_keyword)
    else:
        src=BASE.replace('*STEP',bad_keyword+'\n*STEP')
    f.write_text(src)
    with pytest.raises(PhysicsError):parse_inp(f)


def test_nonzero_boundary_forbidden(tmp_path):
    f=tmp_path/'m.inp';f.write_text(BASE.replace('SUPPORT,1,3,0','SUPPORT,1,3,1.25'))
    with pytest.raises(PhysicsError,match='zero translational'):
        parse_inp(f)


def test_nonpositive_jacobian_denied(tmp_path):
    f=tmp_path/'m.inp';f.write_text(BASE.replace('1,1,2,3,4','1,1,3,2,4'))
    with pytest.raises(PhysicsError,match='inverted tetrahedron'):
        parse_inp(f)


def test_multi_step_denied(tmp_path):
    f=tmp_path/'m.inp';f.write_text(BASE.replace('*END STEP','*END STEP\n*STEP\n*STATIC\n*END STEP'))
    with pytest.raises(PhysicsError,match='one small-deformation static step'):
        parse_inp(f)
