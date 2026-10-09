"""CalculiX C3D8 axial patch: deterministic mesh and fail-closed FRD verification."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
import numpy as np

LENGTH=0.1
WIDTH=HEIGHT=0.01
YOUNG=2.0e11
FORCE=1000.0
EXACT_UX=FORCE*LENGTH/(YOUNG*WIDTH*HEIGHT)
EXACT_SIGMA=FORCE/(WIDTH*HEIGHT)
STEM='verified_axial_bar'

class BarVerificationError(ValueError):
    pass

def generate_deck(segments:int=5)->str:
    if type(segments) is not int or not 1<=segments<=100:
        raise ValueError('segments must be integer 1..100')
    lines=['*HEADING','SI | connected C3D8 axial bar | E=2e11 Pa, nu=0, F=1000 N','*NODE']
    for i in range(segments+1):
        x=LENGTH*i/segments
        for j,(y,z) in enumerate(((0,0),(WIDTH,0),(WIDTH,HEIGHT),(0,HEIGHT)),1):
            lines.append(f'{4*i+j}, {x:.12g}, {y:.12g}, {z:.12g}')
    lines.append('*ELEMENT,TYPE=C3D8,ELSET=EALL')
    for i in range(segments):
        b,t=4*i,4*(i+1)
        lines.append(f'{i+1}, '+', '.join(map(str,(b+1,t+1,t+2,b+2,b+4,t+4,t+3,b+3))))
    lines+=['*NSET,NSET=ROOT','1, 2, 3, 4','*NSET,NSET=TIP',
            ', '.join(str(x) for x in range(4*segments+1,4*segments+5)),
            '*NSET,NSET=ALLNODES']
    for i in range(0,4*(segments+1),16):
        lines.append(', '.join(map(str,range(i+1,min(i+17,4*(segments+1)+1)))))
    lines+=['*MATERIAL,NAME=ISOTROPIC','*ELASTIC','2.0E11, 0.0',
            '*SOLID SECTION,ELSET=EALL,MATERIAL=ISOTROPIC','*STEP','*STATIC',
            '1.,1.','*BOUNDARY','ROOT,1,3','*CLOAD']
    for node in range(4*segments+1,4*segments+5):
        lines.append(f'{node},1,250')
    lines+=['*NODE FILE','U,RF','*EL FILE','S,E',
            '*NODE PRINT,NSET=ALLNODES','U,RF','*END STEP']
    return '\n'.join(lines)+'\n'

def _keywords(content):
    active=None;parts=[]
    for raw in content.splitlines():
        line=raw.strip()
        if not line or line.startswith('**'): continue
        if line.startswith('*'):
            if active is not None: yield active,parts
            active=line[1:].split(',')[0].strip().upper()
            parts=[]
        else:parts.append(line)
    if active is not None:yield active,parts

def _parse_deck(content):
    nodes={};elems={};elastic=[];boundary=[];loads=[]
    for k,rows in _keywords(content):
        if k=='NODE':
            for row in rows:
                a=[v.strip() for v in row.split(',')]
                if len(a)!=4:raise BarVerificationError('invalid node row')
                i=int(a[0]);xyz=np.array([float(x) for x in a[1:]])
                if i in nodes or not np.isfinite(xyz).all():raise BarVerificationError('duplicate/nonfinite node')
                nodes[i]=xyz
        elif k=='ELEMENT':
            for row in rows:
                a=[int(v) for v in row.split(',')]
                if len(a)!=9 or a[0] in elems:raise BarVerificationError('invalid C3D8 connectivity')
                elems[a[0]]=a[1:]
        elif k=='ELASTIC':
            for row in rows:elastic.extend(float(x) for x in row.split(','))
        elif k=='BOUNDARY':boundary.extend(rows)
        elif k=='CLOAD':loads.extend(rows)
    return nodes,elems,elastic,boundary,loads

def _jacobian(xyz,r,s,t):
    natural=((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
             (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))
    grad=np.array([[a*(1+b*s)*(1+c*t)/8,b*(1+a*r)*(1+c*t)/8,c*(1+a*r)*(1+b*s)/8]
                   for a,b,c in natural])
    return float(np.linalg.det(xyz.T@grad))

def preflight(content):
    nodes,elems,elastic,bc,loads=_parse_deck(content)
    n=len(elems)
    if n<1 or len(nodes)!=4*(n+1) or set(nodes)!=set(range(1,4*(n+1)+1)) or set(elems)!=set(range(1,n+1)):
        raise BarVerificationError('expected 4*(n+1) globally shared nodes and n C3D8 elements')
    if len(elastic)!=2 or not np.allclose(elastic,(YOUNG,0),rtol=1e-12,atol=1e-14):
        raise BarVerificationError('E=2e11 Pa, nu=0 required for analytical patch')
    root={i for i,p in nodes.items() if abs(p[0])<1e-12}
    tip={i for i,p in nodes.items() if abs(p[0]-LENGTH)<1e-12}
    if root!={1,2,3,4} or tip!=set(range(4*n+1,4*n+5)):
        raise BarVerificationError('bad root/tip geometry or node numbering')
    for eid,conn in elems.items():
        b,t=4*(eid-1),4*eid
        target=[b+1,t+1,t+2,b+2,b+4,t+4,t+3,b+3]
        if conn!=target:raise BarVerificationError(f'wrong shared connectivity in element {eid}')
        xyz=np.array([nodes[i] for i in conn])
        for r in (-1/math.sqrt(3),1/math.sqrt(3)):
            for s in (-1/math.sqrt(3),1/math.sqrt(3)):
                for t in (-1/math.sqrt(3),1/math.sqrt(3)):
                    if _jacobian(xyz,r,s,t)<=1e-15:
                        raise BarVerificationError(f'inverted/degenerate Jacobian in element {eid}')
    if bc!=['ROOT,1,3']:raise BarVerificationError('wrong root boundary: ROOT,1,3 required')
    applied={}
    for row in loads:
        a=[v.strip() for v in row.split(',')]
        if len(a)!=3:raise BarVerificationError('malformed CLOAD')
        node,dof=int(a[0]),int(a[1]);force=float(a[2])
        if node in applied or dof!=1:raise BarVerificationError('duplicated/invalid CLOAD')
        applied[node]=force
    if set(applied)!=tip or any(abs(f-FORCE/4)>1e-9 for f in applied.values()):
        raise BarVerificationError('load must be +250 N X at each of four tip nodes')
    upper=content.upper()
    required=('*ELEMENT,TYPE=C3D8,ELSET=EALL','*SOLID SECTION,ELSET=EALL,MATERIAL=ISOTROPIC',
              '*NSET,NSET=ROOT\n1, 2, 3, 4\n','*NSET,NSET=TIP\n',
              '*NODE FILE\nU,RF','*EL FILE\nS,E')
    if any(key not in upper for key in required):
        raise BarVerificationError('required material/node sets/output keywords missing')
    return {'status':'PREFLIGHT_PASS','nodes':len(nodes),'elements':n,
            'root_nodes':sorted(root),'tip_nodes':sorted(tip),
            'applied_fx_n':sum(applied.values()),
            'analytical_tip_ux_m':EXACT_UX,'analytical_sxx_pa':EXACT_SIGMA,
            'units':'m-N-Pa'}

_FLOAT=re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EDed][+-]?\d+)?')

def parse_frd(path):
    data=Path(path).read_bytes()
    if b'\x00' in data:raise BarVerificationError('binary FRD not supported; request *NODE FILE')
    try:lines=data.decode('ascii').splitlines()
    except UnicodeDecodeError as exc:
        raise BarVerificationError('non-ASCII FRD; request *NODE FILE') from exc
    datasets={};name=None;current={}
    for row in lines:
        tag=row[:3].strip()
        if tag=='-4':
            if name is not None:raise BarVerificationError('incomplete FRD dataset')
            parts=row[3:].split()
            name=parts[0].upper() if parts else None;current={}
        elif tag=='-1' and name:
            raw=row[3:].lstrip()
            m=re.match(r'(\d+)',raw)
            if not m:raise BarVerificationError('bad FRD node id')
            node=int(m.group(1))
            vals=[float(x.replace('D','E').replace('d','E')) for x in _FLOAT.findall(raw[m.end():])]
            if len(vals)<3 or not all(math.isfinite(x) for x in vals[:3]):
                raise BarVerificationError('nonfinite/missing FRD components')
            if node in current:raise BarVerificationError('duplicate FRD node')
            current[node]=vals
        elif tag=='-3' and name:
            datasets[name]=current;name=None;current={}
    if name is not None:raise BarVerificationError('unterminated FRD dataset')
    return datasets

def validate_results(content,frd):
    info=preflight(content)
    ds=parse_frd(frd)
    nodes=_parse_deck(content)[0]
    root=info['root_nodes'];tip=info['tip_nodes']
    u=ds.get('DISP')
    if u is None or set(u)!=set(nodes):
        raise BarVerificationError('DISP missing or incomplete')
    tip_u=[u[i][0] for i in tip]
    root_u=max(abs(value) for node in root for value in u[node][:3])
    displacement_error=max(abs(x-EXACT_UX) for x in tip_u)/EXACT_UX
    if displacement_error>0.01 or root_u>EXACT_UX*0.001:
        raise BarVerificationError(f'nonphysical displacement: relative error={displacement_error:.6g}')
    rf=ds.get('FORC')
    if rf is None or not set(root).issubset(rf):
        raise BarVerificationError('FORC (nodal RF) missing')
    support_fx=sum(rf[i][0] for i in root)
    force_error=abs(support_fx+FORCE)/FORCE
    if force_error>0.01:raise BarVerificationError(f'reaction imbalance: {support_fx:.6g} N')
    stress=ds.get('STRESS')
    if stress is None or set(stress)!=set(nodes):
        raise BarVerificationError('STRESS missing/incomplete')
    stress_error=max(abs(v[0]-EXACT_SIGMA) for v in stress.values())/EXACT_SIGMA
    if stress_error>0.02:
        raise BarVerificationError(f'axial stress mismatch: {stress_error:.6g}')
    return {**info,'status':'BENCHMARK_PASS','solver':'CalculiX',
            'mean_tip_ux_m':sum(tip_u)/len(tip),'tip_ux_relative_error':displacement_error,
            'root_reaction_fx_n':support_fx,'force_balance_relative_error':force_error,
            'stress_xx_relative_error':stress_error,
            'scope':'C3D8 isotropic linear static patch; no composite impact validation'}

def run_benchmark(outdir,exe=None,timeout=120,threads=2):
    from .external import run_ccx
    out=Path(outdir)
    if out.exists() and any(out.iterdir()):
        raise BarVerificationError('output directory must be empty')
    inputs=out/'input';inputs.mkdir(parents=True)
    deck=inputs/(STEM+'.inp')
    content=generate_deck()
    deck.write_text(content,encoding='ascii')
    audit=preflight(content)
    (out/'preflight.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    try:
        m=run_ccx(str(deck),str(out/'solver'),exe=exe,timeout=timeout,threads=threads)
        if m.get('status')!='solver_executed_output_unvalidated':
            raise BarVerificationError('CalculiX solver did not execute')
        report=validate_results(content,out/'solver'/'workspace'/(STEM+'.frd'))
    except Exception as exc:
        (out/'validation.json').write_text(json.dumps({'status':'FAILED','reason':str(exc)},indent=2),encoding='utf-8')
        raise
    (out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
