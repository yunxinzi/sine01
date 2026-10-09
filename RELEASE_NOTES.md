# v0.2.0 — release notes

Compared with Cloud Bridge v0.1.0:

1. **Actual Abaqus-style INP native compute**: C3D4 mesh, node/element sets, isotropic elasticity, zero prescribed BC, nodal loads, one static step. Strict fail-closed keyword checks. Explicit SI-unit confirmation.
2. **Artifact verifier**: validate manifest checksums, safe ZIP members, field array dimensions, material stress from displacement/strain, INP imported mesh/forces/supports, recomputed equilibrium/energy checks. This is not experimental validation.
3. **Durable job journaling**: `run-job` and `--resume`; retain failed attempts, prohibit changing source input/quality mode when resuming, re-use a verified completed result. Entire solve is restarted after a failed attempt; no solver checkpoint serialization.
4. **External adapters hardened**: validated quoted INCLUDE filenames, block path traversal and symlinks, append per-output checksums. Real CalculiX/OpenRadioss still not installed in this session.
5. **41 passing tests** plus two actually executed finite element job ZIPs, installable wheel, Codex directions and an explicit capability matrix.

This release upgrades **Cloud Bridge** only. Historical NoPC CAE Skill v0.2.0 remains a separate package and was not source-merged due to unavailable editable archive bytes.
