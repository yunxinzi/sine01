# Changelog

## [2.0.0] - 2026-11-01 (release candidate)

- Migrated the full V1.9 workflow into a portable Agent Skills `SKILL.md` with focused reference files.
- Formalized visual-preview and artwork approval Gates; added a one-complex-page pilot as an internal validation step.
- Clarified editable/hybrid/image-only/PDF/review delivery mode boundaries; added foreground move test.
- Defined 4 separate test layers: PPTX structure, rendered fidelity, real editability, and target-software playback.
- Added dependency-light skill/project validation, PPTX risk scanner, image diff helper, sample manifest, and unit tests.
- Codified incremental repair, checkpoint/recovery and build-id consistency.

## [1.9] - 2026-10-22 (prompt baseline)

- Quality-first speed improvements: caching, parallel independent tasks, incremental rebuild, targeted repair, resumable saves.
- Explicit user approval Gates and same-build exports; honest validation terminology.

## [1.6–1.8] - 2026-10-21

- Added full artwork review, editable decomposition, motion preplanning, independent foreground requirements, and actual target-app checks.
- Hard lessons: screenshot-only PPTs falsely claimed as editable; cropping objects from a full-page screenshot does not remove source ghosts; all-fade animations are not high-end choreography; some shapes/fonts produce blank WPS pages.

## [1.0–1.5] - earlier iterations

- Established requirement intake, at least eight visual style previews, narrative planning, editable PPTX, reference-image comparison, iterative QA and delivery discipline.
