# NoPC CAE Cloud Bridge v0.2.0 — numerical and integration evidence

**Date:** 2026-10-09. **Environment:** active ChatGPT tool container (Python 3.13.5, NumPy/SciPy). **Not a Codex Cloud run.**

## Actual runs

1. **Native 3D C3D4 prismatic bar**: 96-tetrahedron baseline; in `research` mode also **768** and **2,592** tetrahedron refinements. E=70 GPa, ν=0, L=1 m, section 0.1×0.1 m, applied force 100 N. Mean axial tip displacement = **1.4285714285714155e-7 m**, analytic = **1.4285714285714285e-7 m**, relative mismatch **9.079e-15**. Von Mises ≈ **10,000 Pa**; fixed-X reaction ≈ **−100 N**. Force, solver residual and energy balance are all ~1e-14 or better. This is a constant-strain patch, not a general mesh-convergence benchmark.
2. **Strict imported C3D4 Abaqus/CalculiX-style INP**: `examples/minimal_ccx.inp` treated as SI (unit confirmation required). **4 nodes, 1 tetrahedron**. Calculated maximum displacement = **0.006367346938775511 m**, von Mises ≈ **342.857142857 Pa**, applied vertical force **−100 N**, reactions **+100 N**, reported equilibrium/energy residuals 0 within machine precision. The verifier separately reassembles nodal internal forces from stored strain/stress and rechecks reactions and energy. This is not an Abaqus-vs-CalculiX or experimental benchmark; the example is a simple artificial input case.

## Automated acceptance

- **41 tests passed**. See `verification/pytest.log`.
- Tests include analytic comparison, mesh Jacobian/orientation, invalid materials, unsupported physics, negative loads, ZIP safety/CRC, tampered result checksums, manually rehashed inconsistent stress rejection, immutable retry attempt preservation, completed job reuse, SI unit enforcement, forbidden Abaqus analysis keywords, and mocked external programs.
- End-to-end generated and verified **two actual result ZIPs**: `verification/Job_Tension3D.zip` and `verification/Job_C3D4_INP.zip`. Source files, raw arrays, VTK, HTML, reports, logs and manifest hashes are included; `verify` has been run on both directory and ZIP.
- Wheel `nopc_cae_cloud_bridge-0.2.0-py3-none-any.whl` generated; `scripts/install_skill.py` copy installation completed successfully. Real Codex Cloud Skill registration remains untested.

## External solver constraint

`doctor` detected **no CalculiX, no OpenRadioss Starter, and no OpenRadioss Engine** in this specific ChatGPT container. Adapter tests use mocked processes and do not establish that actual solver packages installed or that complex structural physics was simulated. VUMAT/UMAT, composite delamination, impact/contact, industrial certification are **not implemented or verified** here.

## Evidence inventory

- `verification/job_research_execution.json` and `verification/inp_execution.json`: real solver summary data.
- `verification/job_verify.json`, `verification/inp_verify.json`: source run checks.
- `verification/job_zip_verify.json`, `verification/inp_zip_verify.json`: archive checks.
- `verification/doctor.json`: actual environment diagnostics.
- `verification/pytest.log`: test exit summary; no mock is labeled as a real external solver computation.

Success criterion is narrowly **verified baseline C3D4 linear-static execution and reproducible artifacts**, not general Abaqus equivalence.
