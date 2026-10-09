"""C3D8 CalculiX benchmark regression, including an independent numerical solve."""
import math
import numpy as np
import pytest
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
from nopc_bridge.ccx_bar import (
    LENGTH, FORCE, EXACT_UX, EXACT_SIGMA, YOUNG,
    BarVerificationError, _jacobian, _parse_deck, generate_deck,
    preflight, parse_frd, validate_results
)

def test_preflight_shared_nodes():
    audit=preflight(generate_deck())
    assert (audit['nodes'],audit['elements'])==(24,5)
    assert audit['root_nodes']==[1,2,3,4]
    assert audit['tip_nodes']==[21,22,23,24]
    nodes,elements,*_=_parse_deck(generate_deck())
    assert set(elements[1])&set(elements[2])=={5,6,7,8}
    assert all(_jacobian(np.array([nodes[i] for i in e]),0,0,0)>0 for e in elements.values())

def test_bad_node_connectivity_rejected():
    inp=generate_deck().replace('2, 5, 9, 10, 6, 8, 12, 11, 7',
                                '2, 5, 9, 10, 6, 4, 12, 11, 7')
    with pytest.raises(BarVerificationError,match='connectivity'):
        preflight(inp)

def test_bad_constraint_load_rejected():
    with pytest.raises(BarVerificationError,match='boundary'):
        preflight(generate_deck().replace('ROOT,1,3','TIP,1,3'))
    with pytest.raises(BarVerificationError,match='load'):
        preflight(generate_deck().replace('21,1,250','21,1,500'))

def synthetic_frd(displacement=EXACT_UX,force=-FORCE,stress=EXACT_SIGMA):
    rows=['    1C test',' -4  DISP        3    1']
    for i in range(1,25):
        rows.append(f' -1 {i:5d} {displacement*((i-1)//4)/5:.5E} 0.00000E+00 0.00000E+00')
    rows+=[' -3',' -4  FORC        3    1']
    for i in range(1,25):
        rows.append(f' -1 {i:5d} {force/4 if i<=4 else 0:.5E} 0.00000E+00 0.00000E+00')
    rows+=[' -3',' -4  STRESS        6    1']
    for i in range(1,25):
        rows.append(f' -1 {i:5d} {stress:.5E} 0.00000E+00 0.00000E+00')
    rows+=[' -3',' -4  ERROR        3    1']
    for i in range(1,25):
        rows.append(f' -1 {i:5d} 6.35000E+01 0.00000E+00 0.00000E+00')
    rows+=[' -3',' 9999']
    return '\n'.join(rows)+'\n'

def test_frd_does_not_confuse_error_estimate(tmp_path):
    file=tmp_path/'mock.frd';file.write_text(synthetic_frd(),encoding='ascii')
    fields=parse_frd(file)
    assert fields['ERROR'][24][0]==63.5
    result=validate_results(generate_deck(),file)
    assert result['status']=='BENCHMARK_PASS'
    assert result['force_balance_relative_error']==0

def test_absurd_frd_displacement_rejected(tmp_path):
    file=tmp_path/'mock.frd';file.write_text(synthetic_frd(displacement=-7.3e9),encoding='ascii')
    with pytest.raises(BarVerificationError,match='displacement'):
        validate_results(generate_deck(),file)
    file.write_text(synthetic_frd(force=-500),encoding='ascii')
    with pytest.raises(BarVerificationError,match='reaction'):
        validate_results(generate_deck(),file)
    file.write_text(synthetic_frd(stress=EXACT_SIGMA*.365),encoding='ascii')
    with pytest.raises(BarVerificationError,match='stress'):
        validate_results(generate_deck(),file)

def test_binary_or_incomplete_frd_rejected(tmp_path):
    file=tmp_path/'mock.frd';file.write_bytes(b' 1C \x00')
    with pytest.raises(BarVerificationError,match='binary'):
        parse_frd(file)
    file.write_text(' -4 DISP\n -1    1 0 0 0\n',encoding='ascii')
    with pytest.raises(BarVerificationError,match='unterminated'):
        parse_frd(file)

def test_independent_c3d8_fem_solve():
    """2x2x2 integration, full stiffness assembly and nonprescribed x-extension."""
    nodes,elements,*_=_parse_deck(generate_deck())
    nn=len(nodes);K=lil_matrix((3*nn,3*nn));F=np.zeros(3*nn)
    mu=YOUNG/2
    D=np.diag([2*mu,2*mu,2*mu,mu,mu,mu])
    nat=((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
         (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))
    gp=1/math.sqrt(3)
    for e in elements.values():
        xyz=np.array([nodes[i] for i in e]);ke=np.zeros((24,24))
        for r in (-gp,gp):
            for s in (-gp,gp):
                for t in (-gp,gp):
                    dn=np.array([[a*(1+b*s)*(1+c*t)/8,
                                  b*(1+a*r)*(1+c*t)/8,
                                  c*(1+a*r)*(1+b*s)/8] for a,b,c in nat])
                    J=xyz.T@dn;g=dn@np.linalg.inv(J)
                    B=np.zeros((6,24))
                    for a,(dx,dy,dz) in enumerate(g):
                        col=3*a
                        B[0,col]=dx;B[1,col+1]=dy;B[2,col+2]=dz
                        B[3,col]=dy;B[3,col+1]=dx
                        B[4,col+1]=dz;B[4,col+2]=dy
                        B[5,col]=dz;B[5,col+2]=dx
                    ke+=B.T@D@B*np.linalg.det(J)
        indices=[3*(v-1)+k for v in e for k in range(3)]
        for a,ia in enumerate(indices):
            for b,ib in enumerate(indices):
                K[ia,ib]+=ke[a,b]
    for i in range(21,25):F[3*(i-1)]=FORCE/4
    fixed=np.array([3*i+k for i in range(4) for k in range(3)])
    free=np.setdiff1d(np.arange(3*nn),fixed)
    u=np.zeros(3*nn);u[free]=spsolve(K.tocsr()[free,:][:,free],F[free])
    for i in range(1,nn+1):
        expected=nodes[i][0]/LENGTH*EXACT_UX
        assert u[3*(i-1)]==pytest.approx(expected,rel=1e-8,abs=1e-13)
        assert abs(u[3*(i-1)+1])<1e-13
        assert abs(u[3*(i-1)+2])<1e-13
    reaction=K@u-F
    assert sum(reaction[3*i] for i in range(4))==pytest.approx(-FORCE,rel=1e-9)
