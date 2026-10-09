# Capability and acceptance boundaries — v0.2.0

- Real static FEM: uniform rectangular 3D isotropic small-strain bar in native JSON; restricted single-material C3D4 linear-static Abaqus/CalculiX-style INP. NSET/ELSET, zero displacement and concentrated nodal force supported. C3D4 constant strain cannot represent bending accurately with a single coarse element; mesh refinement is essential.
- Unsupported: `.odb`, Abaqus proprietary GUI, VUMAT/UMAT, large deformations, plasticity, general contact, cohesive layers, laminate progressive failure, thermal coupling, genuine 3D impact, shells, high-order elements, dynamically coupled physics, multi-step models, CAD reconstruction. Previous NoPC CAE Skill v0.2.0 may support additional modes but is distinct.
- Abaqus `.inp` does not declare a unit system. `--units SI` is a positive user confirmation, not automatic detection or conversion.
- No solution-vector checkpoint: --resume preserves attempt history but redoes the full solver from the beginning after failure, only reuses previously completed and verified results.
- `verify` hashes files and re-evaluates material stress, equilibrium and energy for supported configurations. It cannot prove material calibration, nonlinearity, mesh convergence, experimental accuracy or industrial design adequacy.
- CalculiX/OpenRadioss external adapters are conditional and had no actual external-binary solve in the current ChatGPT environment. Fake-process tests are explicitly not physical simulations.
- All runs were performed in this conversation's available ChatGPT tool container, not in the user's personal Codex Cloud task. CPU/storage/timeout restrictions must be verified separately on the actual platform.
