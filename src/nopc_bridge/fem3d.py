"""Verified baseline: 3D linear elastic 4-node tetrahedron for a uniform prismatic bar.

Not a general Abaqus input parser. SI units only. Quasi-static, small strain,
isotropic homogeneous linear elasticity, no nonlinear contact or fracture.
"""
from __future__ import annotations
import itertools
import math
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


class PhysicsError(ValueError):
    pass


@dataclass
class Mesh:
    xyz: np.ndarray
    tets: np.ndarray


def mesh_bar(length: float, width: float, height: float, nx: int, ny: int, nz: int) -> Mesh:
    if any((not math.isfinite(k) or k <= 0) for k in (length, width, height)):
        raise PhysicsError("dimensions must be positive, finite SI metres")
    if min(nx, ny, nz) < 1 or max(nx, ny, nz) > 100:
        raise PhysicsError("mesh subdivisions must be in [1,100]")
    if nx * ny * nz * 6 > 250000:
        raise PhysicsError("case exceeds conservative native mesh limit")
    xyz = np.array([(length*i/nx, width*j/ny, height*k/nz)
                    for k in range(nz+1) for j in range(ny+1) for i in range(nx+1)], dtype=float)
    def node(i, j, k):
        return (k*(ny+1)+j)*(nx+1)+i
    tets = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                for perm in itertools.permutations(range(3)):
                    offsets = [(0,0,0)]
                    cursor = [0,0,0]
                    for ax in perm:
                        cursor[ax] += 1
                        offsets.append(tuple(cursor))
                    t = [node(i+x, j+y, k+z) for x,y,z in offsets]
                    pts = xyz[t]
                    J = (pts[1:]-pts[0]).T
                    if np.linalg.det(J) < 0:
                        t[2],t[3]=t[3],t[2]
                    tets.append(t)
    return Mesh(xyz, np.array(tets, dtype=int))


def _constitutive(E, nu):
    if not (math.isfinite(E) and E > 0):
        raise PhysicsError("Young's modulus must be positive finite Pa")
    if not math.isfinite(nu) or not (-0.99 < nu < 0.49):
        raise PhysicsError("Poisson ratio outside conservative stable range")
    lam = E*nu/((1+nu)*(1-2*nu)); mu = E/(2*(1+nu))
    D=np.zeros((6,6))
    D[:3,:3]=lam
    for i in range(3): D[i,i]=lam+2*mu
    for i in range(3,6): D[i,i]=mu
    return D


def _tet_B(coords):
    M = np.column_stack((np.ones(4), coords))
    det = np.linalg.det(M)
    if det < 1e-16:
        raise PhysicsError("degenerate or inverted tetrahedron; invalid Jacobian")
    grad = np.linalg.inv(M)[1:,:].T
    B=np.zeros((6,12))
    for a,(gx,gy,gz) in enumerate(grad):
        c=3*a
        B[0,c]=gx; B[1,c+1]=gy; B[2,c+2]=gz
        B[3,c]=gy; B[3,c+1]=gx
        B[4,c+1]=gz; B[4,c+2]=gy
        B[5,c]=gz; B[5,c+2]=gx
    return B, det/6


def _face_load(mesh: Mesh, Fx: float, length: float, width: float, height: float):
    """Integrate consistent, uniformly distributed traction over x=L exterior faces."""
    faces={}
    for tet in mesh.tets:
        for ijk in itertools.combinations(tet.tolist(),3):
            key=tuple(sorted(ijk))
            faces[key]=faces.get(key,0)+1
    force=np.zeros((len(mesh.xyz),3))
    area_total=0
    tol=1e-10*max(length,width,height)
    for nodes,nface in faces.items():
        if nface != 1:
            continue
        coords=mesh.xyz[list(nodes)]
        if not np.all(np.abs(coords[:,0]-length)<tol):
            continue
        area = 0.5*np.linalg.norm(np.cross(coords[1]-coords[0],coords[2]-coords[0]))
        area_total+=area
        for n in nodes:
            force[n,0]+=Fx/(width*height)*area/3
    if not np.isclose(area_total,width*height,rtol=1e-10,atol=1e-13):
        raise PhysicsError("failed boundary face identification / surface load integration")
    return force.ravel(),area_total


def solve_bar(case: dict):
    geom=case.get("geometry",{})
    meshdef=case.get("mesh",{})
    mat=case.get("material",{})
    if case.get("analysis")!="linear_elastic_static_3d_bar":
        raise PhysicsError("native solver only supports linear_elastic_static_3d_bar")
    L=float(geom["length_m"]); W=float(geom["width_m"]); H=float(geom["height_m"])
    nx=int(meshdef["nx"]);ny=int(meshdef["ny"]);nz=int(meshdef["nz"])
    E=float(mat["young_pa"]);nu=float(mat["poisson"])
    Fx=float(case["load_x_n"])
    if not math.isfinite(Fx): raise PhysicsError("load force must be finite")
    D=_constitutive(E,nu)
    mesh=mesh_bar(L,W,H,nx,ny,nz)
    ndof=len(mesh.xyz)*3
    rows=[];cols=[];vals=[]
    B_list=[];volumes=[]
    for tet in mesh.tets:
        B,vol=_tet_B(mesh.xyz[tet]); B_list.append(B);volumes.append(vol)
        dofs=np.array([3*int(n)+d for n in tet for d in range(3)])
        ke = vol*(B.T@D@B)
        rows.extend(np.repeat(dofs,12)); cols.extend(np.tile(dofs,12)); vals.extend(ke.ravel())
    K=coo_matrix((vals,(rows,cols)),shape=(ndof,ndof)).tocsr()
    rhs,area=_face_load(mesh,Fx,L,W,H)
    clamped=np.flatnonzero(np.abs(mesh.xyz[:,0])<1e-12*max(L,W,H))
    fixed=np.array([3*n+d for n in clamped for d in range(3)],dtype=int)
    free=np.setdiff1d(np.arange(ndof),fixed)
    if len(free)==0: raise PhysicsError("no free degrees of freedom")
    u=np.zeros(ndof)
    uf=spsolve(K[free,:][:,free],rhs[free])
    if not np.all(np.isfinite(uf)): raise PhysicsError("singular or nonfinite FE solution")
    u[free]=uf
    reaction=(K@u)-rhs
    e=np.array([B@u[np.array([3*int(n)+d for n in tet for d in range(3)])] for tet,B in zip(mesh.tets,B_list)])
    sig=e@D.T
    vmis=np.sqrt(.5*((sig[:,0]-sig[:,1])**2+(sig[:,1]-sig[:,2])**2+(sig[:,2]-sig[:,0])**2)+3*(sig[:,3]**2+sig[:,4]**2+sig[:,5]**2))
    strain_energy=.5*float(u@(K@u))
    work=float(u@rhs)
    residual=float(np.linalg.norm(reaction[free])/max(np.linalg.norm(rhs[free]),1e-12))
    rx=float(reaction[fixed[fixed%3==0]].sum())
    force_err=abs(rx+Fx)/max(abs(Fx),1)
    energy_err=abs(2*strain_energy-work)/max(abs(work),1e-12)
    end=np.flatnonzero(np.abs(mesh.xyz[:,0]-L)<1e-10*L)
    result={
        "status":"computed_not_experimentally_validated",
        "method":"small-strain isotropic linear FEM, C3D4 tetrahedron",
        "nodes":len(mesh.xyz),"elements":len(mesh.tets),"dofs":ndof,
        "max_end_ux_m":float(np.max(u.reshape(-1,3)[end,0])),
        "mean_end_ux_m":float(np.mean(u.reshape(-1,3)[end,0])),
        "max_von_mises_pa":float(np.max(vmis)),
        "reaction_x_n":rx,"applied_force_x_n":Fx,
        "strain_energy_j":strain_energy,"external_work_j":work,
        "free_dof_residual_rel":residual,
        "force_balance_rel":force_err,"energy_balance_rel":energy_err,
        "volume_m3":float(np.sum(volumes)),"loaded_area_m2":area,
        "unit_system":"SI: m,N,Pa,J",
        "scope":"prismatic 3D bar, linear elastic static only"
    }
    if nu==0.0:
        exact=Fx*L/(E*W*H)
        result["analytical_end_ux_m"]=exact
        result["analytic_relative_error"]=abs(result["mean_end_ux_m"]-exact)/max(abs(exact),1e-25)
    return mesh,u.reshape(-1,3),e,sig,vmis,result
