"""Strict, *tiny* Abaqus-style C3D4 static INP importer + actual 3D sparse FE solve.

This is not an Abaqus interpreter. Unsupported physics/keywords are rejected,
never silently approximated. Only small-strain isotropic linear statics, SI.
"""
from __future__ import annotations
import json
import math
import re
import warnings
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve, MatrixRankWarning
from .fem3d import Mesh,PhysicsError,_tet_B,_constitutive
from .outputs import sha256,write_native

ALLOWED={'HEADING','PREPRINT','NODE','ELEMENT','NSET','ELSET','MATERIAL','ELASTIC',
         'SOLID SECTION','STEP','STATIC','BOUNDARY','CLOAD','END STEP',
         'NODE FILE','EL FILE','NODE OUTPUT','ELEMENT OUTPUT','OUTPUT'}
SILENT={'HEADING','PREPRINT','SOLID SECTION','STEP','STATIC','END STEP',
        'NODE FILE','EL FILE','NODE OUTPUT','ELEMENT OUTPUT','OUTPUT'}


def parse_inp(path):
    path=Path(path)
    text=path.read_text(encoding='utf-8-sig',errors='replace')
    active=None; opts={}; nodes={};elements={};nsets={};elsets={}
    matname=None;elastic=[];fix_raw=[];loads_raw=[];sections=[];steps=0
    for line_nr,line in enumerate(text.splitlines(),1):
        line=line.strip()
        if not line or line.startswith('**'):continue
        if line.startswith('*'):
            parts=[x.strip() for x in line[1:].split(',')]
            active=parts[0].upper()
            if active not in ALLOWED:raise PhysicsError(f'INP unsupported keyword *{active} line {line_nr}')
            opts={}
            for part in parts[1:]:
                key,sep,val=part.partition('=');opts[key.strip().upper()]=val.strip().strip('"\'') if sep else True
            if active=='ELEMENT' and opts.get('TYPE','').upper()!='C3D4':
                raise PhysicsError('INP element type must be C3D4')
            if active=='MATERIAL':
                if matname is not None:raise PhysicsError('INP supports exactly one material')
                matname=str(opts.get('NAME','')).upper()
                if not matname:raise PhysicsError('MATERIAL NAME required')
            if active=='ELASTIC' and opts:
                raise PhysicsError('only constant isotropic *ELASTIC without options supported')
            if active=='STEP':
                steps+=1
                if steps>1 or str(opts.get('NLGEOM','NO')).upper() not in ('NO','FALSE'):
                    raise PhysicsError('only one small-deformation static step supported')
            if active=='SOLID SECTION':
                sections.append((str(opts.get('ELSET','')).upper(),str(opts.get('MATERIAL','')).upper()))
            continue
        if active is None:raise PhysicsError(f'INP data outside keyword section on line {line_nr}')
        if active in SILENT:
            continue
        cells=[v.strip() for v in line.split(',') if v.strip()]
        try:
            if active=='NODE':
                if len(cells)!=4:raise PhysicsError('NODE line must have id,x,y,z')
                nid=int(cells[0]); xyz=tuple(float(v.replace('D','E')) for v in cells[1:])
                if nid<=0 or nid in nodes or not all(math.isfinite(x) for x in xyz):
                    raise PhysicsError('invalid/duplicate node')
                nodes[nid]=xyz
                if 'NSET' in opts:nsets.setdefault(str(opts['NSET']).upper(),set()).add(nid)
            elif active=='ELEMENT':
                if len(cells)!=5:raise PhysicsError('C3D4 requires id and four node indices')
                eid=int(cells[0]); conn=[int(x) for x in cells[1:]]
                if eid<=0 or eid in elements or len(set(conn))!=4:raise PhysicsError('invalid/duplicate tetrahedron')
                elements[eid]=conn
                if 'ELSET' in opts:elsets.setdefault(str(opts['ELSET']).upper(),set()).add(eid)
            elif active in ('NSET','ELSET'):
                name=str(opts.get(active,'')).upper()
                if not name:raise PhysicsError(f'{active} name missing')
                if 'GENERATE' in opts:
                    if len(cells) not in (2,3):raise PhysicsError('GENERATE expected start,end[,increment]')
                    a,b=int(cells[0]),int(cells[1]);step=int(cells[2]) if len(cells)==3 else 1
                    if step<=0 or b<a or (b-a)//step>100000:raise PhysicsError('invalid set GENERATE range')
                    ids=range(a,b+1,step)
                else:ids=[int(x) for x in cells]
                (nsets if active=='NSET' else elsets).setdefault(name,set()).update(ids)
            elif active=='ELASTIC':
                if len(cells)!=2 or elastic:raise PhysicsError('single E,nu isotropic ELASTIC row required')
                elastic=[float(x.replace('D','E')) for x in cells]
            elif active=='BOUNDARY':
                if len(cells)<2 or len(cells)>4:raise PhysicsError('BOUNDARY expects node/set, dof1[,dof2,0]')
                if len(cells)==2:first=last=int(cells[1]);value=0.
                else:first=int(cells[1]);last=int(cells[2]);value=float(cells[3]) if len(cells)==4 else 0.
                if first<1 or last>3 or first>last or value!=0:
                    raise PhysicsError('only zero translational BOUNDARY DOF 1..3 supported')
                fix_raw.append((cells[0],first,last))
            elif active=='CLOAD':
                if len(cells)!=3:raise PhysicsError('CLOAD expects node/set,dof,force')
                dof=int(cells[1]);force=float(cells[2])
                if dof not in (1,2,3) or not math.isfinite(force):raise PhysicsError('invalid CLOAD')
                loads_raw.append((cells[0],dof,force))
        except (IndexError,ValueError,OverflowError) as exc:
            raise PhysicsError(f'INP parse failure near line {line_nr}: {exc}') from exc
    if not nodes or not elements or not elastic or not fix_raw or not loads_raw or not sections or steps!=1:
        raise PhysicsError('INP needs NODE,ELEMENT,ELASTIC,SOLID SECTION,one STEP,BOUNDARY,CLOAD')
    if len(elements)>20000:raise PhysicsError('INP exceeds conservative 20000-C3D4 element limit')
    if len(sections)!=1 or sections[0][1]!=matname or not sections[0][0]:
        raise PhysicsError('one SOLID SECTION referencing material and ELSET required')
    sel=sections[0][0]
    if elsets.get(sel)!=set(elements):raise PhysicsError('SOLID SECTION must explicitly cover every C3D4 element')
    E,nu=elastic;_constitutive(E,nu)
    nodeids=sorted(nodes);lookup={n:i for i,n in enumerate(nodeids)}
    if any(n not in lookup for tet in elements.values() for n in tet):
        raise PhysicsError('element references nonexistent node')
    mesh=Mesh(np.array([nodes[n] for n in nodeids],dtype=float),
              np.array([[lookup[n] for n in elements[e]] for e in sorted(elements)],dtype=int))
    def resolve(target):
        try:
            n=int(target)
            if n not in nodes:raise PhysicsError('unknown node ID in BC/load')
            return (n,)
        except ValueError:
            name=target.upper()
            ids=nsets.get(name)
            if not ids or not ids.issubset(nodes):raise PhysicsError(f'unknown/invalid NSET {target}')
            return sorted(ids)
    fixed=set();force=np.zeros((len(nodeids),3))
    for target,first,last in fix_raw:
        for n in resolve(target):
            for dof in range(first,last+1):fixed.add(3*lookup[n]+dof-1)
    for target,dof,value in loads_raw:
        for n in resolve(target):force[lookup[n],dof-1]+=value
    if not np.any(force):raise PhysicsError('CLOAD resultant cannot be all zeros')
    # Verify connectivity/positive Jacobian; input orientation cannot be guessed away.
    for tet in mesh.tets:_tet_B(mesh.xyz[tet])
    detail={'analysis':'linear_elastic_static_C3D4_inp','unit_system':'SI (caller-confirmed)',
            'material':{'young_pa':E,'poisson':nu},
            'input_sha256':sha256(path),'node_ids':nodeids,'nodes_xyz_m':mesh.xyz.tolist(),
            'element_ids':sorted(elements),'tets_zero_based':mesh.tets.tolist(),
            'fixed_dof_zero_based':sorted(fixed),'nodal_loads_n':force.tolist(),
            'supported_keywords_only':True}
    return mesh,np.array(sorted(fixed),dtype=int),force.ravel(),detail


def solve_inp(path,outdir,units):
    if units!='SI':
        raise PhysicsError('Abaqus INP has no declared units: pass --units SI ONLY after confirming metre/newton/pascal')
    p=Path(path);out=Path(outdir)
    if out.exists() and any(out.iterdir()):raise PhysicsError('output directory must be empty')
    mesh,fixed,F,case=parse_inp(p)
    nn=len(mesh.xyz);ne=len(mesh.tets);ndof=3*nn
    D=_constitutive(case['material']['young_pa'],case['material']['poisson'])
    rows=[];cols=[];vals=[];Bs=[]
    for tet in mesh.tets:
        B,V=_tet_B(mesh.xyz[tet]);Bs.append(B)
        dofs=np.array([3*int(n)+d for n in tet for d in range(3)])
        ke=V*B.T@D@B
        rows.extend(np.repeat(dofs,12));cols.extend(np.tile(dofs,12));vals.extend(ke.ravel())
    K=coo_matrix((vals,(rows,cols)),shape=(ndof,ndof)).tocsr()
    free=np.setdiff1d(np.arange(ndof),fixed)
    if len(free)==0:raise PhysicsError('no unconstrained degrees of freedom')
    u=np.zeros(ndof)
    with warnings.catch_warnings():
        warnings.simplefilter('error',MatrixRankWarning)
        try:u[free]=spsolve(K[free,:][:,free],F[free])
        except MatrixRankWarning as exc:raise PhysicsError('singular or insufficient boundary constraints') from exc
    if not np.all(np.isfinite(u)):raise PhysicsError('nonfinite/disconnected solution')
    reaction=K@u-F
    strains=np.array([B@u[[3*int(n)+d for n in tet for d in range(3)]]
                      for B,tet in zip(Bs,mesh.tets)])
    stress=strains@D.T
    vm=np.sqrt(.5*((stress[:,0]-stress[:,1])**2+(stress[:,1]-stress[:,2])**2+(stress[:,2]-stress[:,0])**2)+
               3*(stress[:,3]**2+stress[:,4]**2+stress[:,5]**2))
    # For equilibrium report all components, not just an assumed axial direction.
    rvec=np.array([reaction[fixed[fixed%3==a]].sum() for a in range(3)])
    total=np.reshape(F,(-1,3)).sum(axis=0)
    den=max(np.linalg.norm(total),np.linalg.norm(F),1e-12)
    forcebal=float(np.linalg.norm(rvec+total)/den)
    resid=float(np.linalg.norm(reaction[free])/max(np.linalg.norm(F[free]),1e-12))
    energy=.5*float(u@(K@u));work=float(u@F)
    ebal=abs(2*energy-work)/max(abs(work),1e-12)
    summary={'status':'computed_not_experimentally_validated',
             'method':'strict imported Abaqus/CalculiX-style INP C3D4 isotropic linear statics',
             'scope':'C3D4 small-strain, single linear isotropic material, nodal CLOAD, zero BC only',
             'nodes':nn,'elements':ne,'dofs':ndof,
             'max_displacement_m':float(np.linalg.norm(u.reshape(-1,3),axis=1).max()),
             'max_von_mises_pa':float(vm.max()),
             'applied_force_xyz_n':total.tolist(),'support_reaction_xyz_n':rvec.tolist(),
             'strain_energy_j':energy,'external_work_j':work,
             'force_balance_rel':forcebal,'free_dof_residual_rel':resid,
             'energy_balance_rel':ebal,'unit_system':'SI: m,N,Pa,J',
             'requested_quality_mode':'strict_inp'}
    if max(forcebal,resid,ebal)>1e-7:raise PhysicsError('imported INP calculation failed equilibrium gates')
    return write_native(out,p,case,mesh,u.reshape(-1,3),strains,stress,vm,summary,'strict_inp')
