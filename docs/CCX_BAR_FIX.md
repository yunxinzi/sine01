# CalculiX C3D8 bar repair — NoPC CAE V0.2

This patch fixes the axial-bar benchmark configuration described by MiniMax. The original malformed five-element INP was not present in the repository, so its actual root cause is still a hypothesis.

## Correct SI configuration

- 5 connected C3D8 elements, 24 unique global nodes (4 nodes per x-section).
- Root x=0: nodes 1–4, all three translations fixed by ROOT,1,3.
- Tip x=0.1m: nodes 21–24; +250N each in X (total +1000N).
- E=2e11 Pa, nu=0 (exact 3D uniform axial patch); W=H=0.01m.
- Exact tip displacement: 5e-6m; axial SXX: 10MPa; root reaction Fx: -1000N.
- FRD ERROR is a finite-element error estimator, not analytical stress error.
- An empty DAT alone is not failure; NODE PRINT controls requested DAT output.

## Run on MiniMax with actual CalculiX installed

    python -m pip install -e '.[test]'
    python -m pytest -q tests/test_ccx_bar_repair.py
    command -v ccx
    python -m nopc_bridge ccx-bar --out runs/ccx_bar_verified --exe "$(command -v ccx)"
    cat runs/ccx_bar_verified/validation.json

Use a new empty output directory. The CLI generates and preflights the INP, executes actual CCX through the existing adapter and validates FRD datasets.

Output includes:
- input/verified_axial_bar.inp — exact executed input.
- preflight.json — mesh Jacobian, node sharing, loads and boundary check.
- solver/ccx.log and solver/workspace/*.frd, optional .dat and manifest.
- validation.json — BENCHMARK_PASS or FAILED with explanation.

Required data: DISP at every node, FORC reaction at clamped nodes, STRESS with SXX. Tip displacement relative error must be <=1%; root reaction balance <=1%; SXX deviation <=2%; root displacement <=0.1% of theoretical tip displacement. Missing/invalid files or impossible results fail. The general-purpose run-ccx path remains output_unvalidated by design.

## Scope and evidence

Python/SciPy independent C3D8 Gauss integration is covered by automated tests. Parser tests use synthetic FRD fixtures; they do not claim an external CalculiX run. Real CCX execution was not possible in the local ChatGPT container, which lacks the CCX binary. This does not establish validity for nonlinear contact, composite fracture, VUMAT, impact or Abaqus equivalence.
