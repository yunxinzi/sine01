---
name: nopc-cae-cloud-bridge
description: Execute auditable limited 3D FEM analyses in the AI agent's own cloud/terminal, strict Abaqus C3D4 static INP import, safe solver adapters, resumable job records and verifiable ZIP exports. Reject unsupported composite impact/VUMAT rather than fabricate results.
license: MIT
compatibility: Python 3.10+, NumPy and SciPy, a real Agent shell and file access; external solver binaries optional.
metadata:
  author: NoPC CAE Project
  version: "0.2.0"
---

# NoPC CAE Cloud Bridge Skill 0.2.0

## Compute policy

Compute ONLY in the AI provider's current built-in execution environment (ChatGPT/Codex Work etc.). External GitHub/Drive may store data, **never run compute on GitHub Actions/Colab/external VPS** under the user's constraints. Skill installation does not grant additional CPU, memory or uptime. Explicitly identify whether commands are executing in ChatGPT container or a separate Codex Cloud task.

## Mandatory workflow

1. Inspect the input and file permissions. Run `python -m nopc_bridge doctor`. For arbitrary `.inp` first run `audit-inp`, for `.for` run `audit-for` (audit only). Do not compile untrusted Fortran code.
2. Identify physics and confirm the original unit system. Abaqus INP has no implicit units; `solve-inp` requires `--units SI` and explicit confirmation of metre, newton and pascal. If material/contact parameters essential to the requested outcome are missing, ask for them, do not fabricate.
3. For baseline JSON run `preflight` and `run-job ... --out jobs/<id>`. For currently supported C3D4 linear-static INP use `solve-inp <file> --units SI --out runs/<id>`; reject anything beyond documented subset. Do not pretend to solve impact, composite fracture, nonlinear contact or VUMAT using isotropic static elasticity.
4. Only when true CCX/OpenRadioss binaries and compatible models are available, call `run-ccx` or `run-radioss`. Their local process tests with fake binaries do not establish real-solver validity or benchmark accuracy.
5. Run `verify` on run directory and on packaged ZIP. Verification recomputes field constitutive consistency and for INP nodal equilibrium/energy, but **is not independent experimental or industrial validation**. For scientific claims, compare actual external references, convergence and material tests.
6. For failed/interrupted JSON jobs use `run-job ... --resume`; preserves attempts and restarts calculation, **not true solver-state checkpointing**. Save the entire job directory as external storage before environments expire if needed.
7. Return real results, assumptions, units, the exact solver used, test evidence and a ZIP. Distinguish clearly computed, numerically consistent, independently benchmarked, experimentally validated and unverified.

## Commands

```bash
python -m pip install -e '.[viz,test]'
python -m nopc_bridge doctor
python -m pytest -q tests
python -m nopc_bridge preflight examples/tension3d.json
python -m nopc_bridge run-job examples/tension3d.json --out jobs/tension --mode research
python -m nopc_bridge run-job examples/tension3d.json --out jobs/tension --mode research --resume
python -m nopc_bridge audit-inp examples/minimal_ccx.inp
python -m nopc_bridge solve-inp examples/minimal_ccx.inp --units SI --out runs/c3d4
python -m nopc_bridge verify runs/c3d4
python -m nopc_bridge bundle runs/c3d4 --out c3d4.zip
python -m nopc_bridge verify c3d4.zip
```

This Cloud Bridge is **not** the more feature-rich legacy `NoPC CAE Skill v0.2.0` and cannot claim to have migrated its inaccessible archive. Keep them separate until real integration tests are possible.
