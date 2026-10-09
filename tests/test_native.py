import json
from pathlib import Path
import numpy as np
import pytest
from nopc_bridge.fem3d import solve_bar,mesh_bar,PhysicsError
from nopc_bridge.cli import run_native,bundle

BASE={
  'analysis':'linear_elastic_static_3d_bar',
  'geometry':{'length_m':1.,'width_m':0.1,'height_m':0.1},
  'mesh':{'nx':2,'ny':1,'nz':1},
  'material':{'young_pa':70e9,'poisson':0.},'load_x_n':100.
}

@pytest.mark.parametrize('meshsize',[(1,1,1),(2,1,1),(3,2,2)])
def test_analytical_patch_exact(meshsize):
    cfg=json.loads(json.dumps(BASE))
    cfg['mesh']=dict(zip(('nx','ny','nz'),meshsize))
    mesh,u,e,s,v,summary=solve_bar(cfg)
    assert abs(summary['mean_end_ux_m'] - 100/(70e9*.01)) < 1e-17
    assert summary['analytic_relative_error']<1e-9
    assert summary['force_balance_rel']<1e-10
    assert summary['energy_balance_rel']<1e-10
    assert summary['free_dof_residual_rel']<1e-10
    assert np.isclose(summary['volume_m3'],.01)
    assert np.isclose(summary['loaded_area_m2'],.01)
    assert np.isclose(summary['max_von_mises_pa'],1e4,rtol=1e-10)


def test_mesh_positive():
    mesh=mesh_bar(1,.2,.1,2,2,2)
    assert mesh.tets.shape==(48,4)
    dets=[np.linalg.det((mesh.xyz[t[1:]]-mesh.xyz[t[0]]).T) for t in mesh.tets]
    assert min(dets)>0


def test_invalid_material():
    cfg=json.loads(json.dumps(BASE));cfg['material']['young_pa']=-1
    with pytest.raises(PhysicsError):solve_bar(cfg)


def test_invalid_nu():
    cfg=json.loads(json.dumps(BASE));cfg['material']['poisson']=.5
    with pytest.raises(PhysicsError):solve_bar(cfg)


def test_invalid_geometry():
    cfg=json.loads(json.dumps(BASE));cfg['geometry']['height_m']=0
    with pytest.raises(PhysicsError):solve_bar(cfg)


def test_bad_analysis_rejected():
    cfg=dict(BASE);cfg['analysis']='composite_impact'
    with pytest.raises(PhysicsError,match='only supports'):solve_bar(cfg)


def test_negative_force():
    cfg=json.loads(json.dumps(BASE));cfg['load_x_n']=-100
    *_,r=solve_bar(cfg)
    assert r['reaction_x_n']>0


def test_outputs_bundle(tmp_path):
    example=tmp_path/'in.json';example.write_text(json.dumps(BASE))
    dest=tmp_path/'run';r=run_native(example,dest,'quick')
    assert r['status']=='computed_not_experimentally_validated'
    for filename in ('result.json','fields.npz','manifest.json','REPORT.md','result.vtk','case_used.json'):
        assert (dest/filename).exists()
    data=np.load(dest/'fields.npz')
    assert data['stress_pa'].shape[0] == r['elements']
    output=tmp_path/'test_case.zip'
    from zipfile import ZipFile
    bundle(dest,output)
    with ZipFile(output) as z:
        assert set(z.namelist())=={x.name for x in dest.iterdir()}
        assert 'result.json' in z.namelist()


def test_refuse_reuse(tmp_path):
    case=tmp_path/'case.json';case.write_text(json.dumps(BASE))
    job=tmp_path/'job';job.mkdir();(job/'old.txt').write_text('stale')
    with pytest.raises(PhysicsError,match='must be empty'):run_native(case,job,'quick')


def test_engineering_not_certified(tmp_path):
    case=tmp_path/'case.json';case.write_text(json.dumps(BASE))
    with pytest.raises(PhysicsError,match='cannot be granted'):run_native(case,tmp_path/'out','engineering')


def test_research_has_mesh_study(tmp_path):
    case=tmp_path/'case.json';case.write_text(json.dumps(BASE))
    out=tmp_path/'research'
    result=run_native(case,out,'research')
    assert len(result['mesh_study']['mesh_levels'])==3
    assert result['mesh_study']['displacement_relative_span']<1e-9
