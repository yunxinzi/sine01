# Codex Cloud integration — specific steps

1. Put this repository on GitHub as code/data storage, not as a place to run Actions. Do not commit private materials or access tokens.
2. In a Codex Cloud task open this repository and use its terminal. Confirm that Python, NumPy and SciPy are available. Install from requirements if permitted.
3. Execute `python -m nopc_bridge doctor`, `python -m pytest -q tests` and `python -m nopc_bridge run-job examples/tension3d.json --out jobs/first --mode research`.
4. Verify computed outputs: `python -m nopc_bridge verify jobs/first`; archive: `python -m nopc_bridge bundle jobs/first --out first.zip`; re-verify ZIP.
5. For restricted C3D4 INP input with **confirmed SI units**, run `python -m nopc_bridge solve-inp file.inp --units SI --out runs/imported`; verify and bundle.
6. Optional: if the Codex environment permits apt and the package is truly available, try `bash scripts/setup_codex.sh --install-ccx`. Then run a valid official CalculiX benchmark and compare it with an independent reference. A mock executable test is not sufficient.
7. Save source, job attempts, logs and results to GitHub/Drive storage as required. Do not assume interrupted sessions keep local files.

Agent Skills-compatible install: `python scripts/install_skill.py --target ~/.agents/skills` (or to the supported platform-specific Skill directory). Native support differs by provider; the repository root `AGENTS.md` remains a fallback when Skill discovery is unavailable.

## Compatibility with previous NoPC CAE Skill v0.2.0

The original v0.2.0 code/ZIP was referenced in the user's project but not accessible as programmatically editable bytes in this runtime. Current Cloud Bridge v0.2.0 is a separate install, not a replacement or merged upgrade. Future integration needs the original archive and a passing cross-package regression suite.
