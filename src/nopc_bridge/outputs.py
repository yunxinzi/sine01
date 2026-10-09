"""Self-contained provenance and legacy ASCII VTK for plotting/inspection."""
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def _vtk(path,mesh,u,vmis):
    with open(path,'w',encoding='utf-8') as f:
        f.write('# vtk DataFile Version 3.0\nNoPC C3D4 computed field\nASCII\nDATASET UNSTRUCTURED_GRID\n')
        f.write(f'POINTS {len(mesh.xyz)} double\n')
        for p in mesh.xyz:f.write(' '.join(map(str,p))+'\n')
        f.write(f'CELLS {len(mesh.tets)} {len(mesh.tets)*5}\n')
        for c in mesh.tets:f.write('4 '+' '.join(map(str,c))+'\n')
        f.write(f'CELL_TYPES {len(mesh.tets)}\n'+('10\n'*len(mesh.tets)))
        f.write(f'POINT_DATA {len(mesh.xyz)}\nVECTORS Displacement_m double\n')
        for vec in u:f.write(' '.join(map(str,vec))+'\n')
        f.write(f'CELL_DATA {len(mesh.tets)}\nSCALARS VonMises_Pa double 1\nLOOKUP_TABLE default\n')
        for val in vmis:f.write(f'{val}\n')


def write_native(outdir, source, case, mesh,u,strains,stresses,vmis,summary,mode):
    p=Path(outdir);p.mkdir(parents=True,exist_ok=True)
    with open(p/'case_used.json','w') as f:json.dump(case,f,indent=2,ensure_ascii=False)
    if Path(source).suffix.lower()=='.inp':
        import shutil
        shutil.copy2(source,p/'source.inp')
    with open(p/'result.json','w') as f:json.dump(summary,f,indent=2,ensure_ascii=False,allow_nan=False)
    np.savez_compressed(p/'fields.npz',nodes=mesh.xyz,tets=mesh.tets,displacement_m=u,strain=strains,stress_pa=stresses,von_mises_pa=vmis)
    _vtk(p/'result.vtk',mesh,u,vmis)
    # One real computed-data plot, suitable for viewing on a phone.
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        coords=mesh.xyz[:,0]
        x=np.unique(coords)
        mean_u=np.array([np.mean(u[np.isclose(coords,xx),0]) for xx in x])
        fig,ax=plt.subplots(figsize=(7,4))
        ax.plot(x,mean_u,marker='o',label='FEM: average nodal ux at each x plane')
        if case.get('analysis')=='linear_elastic_static_3d_bar' and case.get('material',{}).get('poisson') == 0:
            F=float(case['load_x_n']); E=float(case['material']['young_pa'])
            W=float(case['geometry']['width_m']);H=float(case['geometry']['height_m'])
            ax.plot(x,F*x/(E*W*H),'--',label='1D analytical displacement')
        ax.set(xlabel='Position x (m)',ylabel='Axial displacement ux (m)',title='Computed C3D4 response (not a convergence test)')
        ax.grid(alpha=0.25);ax.legend(loc='best');fig.tight_layout()
        fig.savefig(p/'displacement.png',dpi=160);plt.close(fig)
    except ImportError:
        pass
    is_inp=case.get('analysis')=='linear_elastic_static_C3D4_inp'
    if is_inp:
        report=f"""# NoPC CAE — strict INP C3D4 solve

- Method: {summary['method']}
- Status: **computed, NOT experimentally or industrially validated**
- Nodes: {summary['nodes']}; tetrahedra: {summary['elements']}
- Max displacement: {summary['max_displacement_m']:.12g} m
- Max von Mises stress: {summary['max_von_mises_pa']:.12g} Pa
- Total applied force (N): {summary['applied_force_xyz_n']}
- Total support reaction (N): {summary['support_reaction_xyz_n']}
- Force residual: {summary['force_balance_rel']:.4g}
- Free-DOF residual: {summary['free_dof_residual_rel']:.4g}
- Energy check: {summary['energy_balance_rel']:.4g}

**Scope:** one material, small-strain isotropic linear static C3D4 with nodal forces and zero displacements. No contact, composite failure, nonlinear mechanics, UMAT or VUMAT. Abaqus INP units were confirmed as SI by CLI flag, not inferred automatically.

Reproduction: `nopc-bridge solve-inp source.inp --units SI --out recheck`. `fields.npz` contains the actual nodal/element arrays. No independent reference or experimental data were supplied.
"""
    else:
        report=f"""# NoPC CAE computed baseline result

- Analysis: {summary['method']}
- Status: **computed, NOT experimentally or industrially validated**
- Precision request: {mode}
- Nodes: {summary['nodes']}; tetrahedra: {summary['elements']}
- End displacement: {summary['mean_end_ux_m']:.12g} m
- Maximum von Mises: {summary['max_von_mises_pa']:.12g} Pa
- Fixed-support reaction X: {summary['reaction_x_n']:.12g} N
- Force equilibrium residual: {summary['force_balance_rel']:.4g}
- Free-DOF solver residual: {summary['free_dof_residual_rel']:.4g}
- Internal/external energy check: {summary['energy_balance_rel']:.4g}

**Scope:** no damage, nonlinear contact, transient impact, or VUMAT. There is no experimental validation, and this single patch test must not be taken as an industrial design certificate.

Reproduction: `nopc-bridge run case_used.json --out rerun`. Input is SI. Files `fields.npz` and `result.vtk` hold actual computed fields.
"""
        if 'analytic_relative_error' in summary:
            report+=f"\n- Analytic (nu=0) mean end-displacement relative error: {summary['analytic_relative_error']:.4g}\n"
    (p/'REPORT.md').write_text(report,encoding='utf-8')
    from .html_report import write_html_report
    write_html_report(p,summary)
    manifest={"tool":"NoPC CAE Cloud Bridge", "version":__import__("nopc_bridge").__version__, "utc":datetime.now(timezone.utc).isoformat(),
              "python":sys.version.split()[0],"platform":platform.platform(),"requested_mode":mode,
              "input_source_sha256":sha256(source), "result_provenance":"native Python+SciPy solver executed",
              "numpy":np.__version__,
              "solver_source_sha256":sha256(Path(__file__).parent/'fem3d.py'),
              "inp_import_source_sha256":sha256(Path(__file__).parent/'inp3d.py') if is_inp else None,
              "files_sha256":{q.name:sha256(q) for q in p.iterdir() if q.is_file()}}
    (p/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return summary
