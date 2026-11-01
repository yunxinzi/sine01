# Suxing PPT Skill

An [Agent Skills](https://agentskills.io/specification) compatible **workflow and QA toolkit** for designing visually faithful presentations: eight distinct visual styleboards, human style selection, approved full-slide references, pilot validation, genuine editable layer reconstruction, animation planning, and verifiable delivery.

**This is not a turnkey AI slide generator.** It ships instructions, reference documents, and small standard-library audit utilities. Your agent must supply actual image-generation, PPTX editing/rendering, and PowerPoint/WPS playback tools. Do not claim validation that did not occur.

Workflow: **DEFINE → EXPLORE → PILOT → ARTWORK → REBUILD → VERIFY → DELIVER**. Style exploration and full-deck approval are mandatory for fresh projects unless explicitly waived by the user. Preserve prior approvals in continuation or review tasks.

Install by copying `suxing-ppt-skill/` into a supported Agent Skills directory (e.g., `.agents/skills/`). Read `SKILL.md` for the executable instructions. The full Chinese README explains the available modes: editable, image-only, hybrid, PDF-only, and review.

```bash
python3 scripts/validate_skill.py .
python3 scripts/validate_project.py assets/project-template.json
python3 -m unittest discover -s tests -v
python3 scripts/audit_pptx.py /path/to/slides.pptx --mode editable
```

The PPTX tool is a structural risk scan, not a fidelity or editability certification; use actual target-application testing before asserting real compatibility.

License: MIT. Third-party assets must be licensed separately.
