# Project Learning Registry | 项目基础知识图

This directory is the repository-owned learning interface for transferable
foundations needed to understand `andes-rl-kundur`.

It is **non-authoritative** and **not evidence**. Source code, project Context,
experiment feeds, claims, verdicts, and manuscripts remain authoritative for
project-local names, current results, and paper conclusions.

## Assets

- `project-map.md` keeps the stable project-use spine.
- `branches/*.md` stores compact Foundation Atoms, `requires` prerequisites,
  `used-in` stages, one-sentence project roles, and typed repository anchors.
- Full explanations, teaching-method selections, learner progress, project
  identifiers, and concrete experiment conclusions remain outside this graph.

The same registry is reused across repository-learning questions. Read-only
Tutor sessions may propose transient candidates but do not change these files.
Only an explicit `$enrich-project-learning` request merges one useful bounded
slice. Branch count scales with project size; a new file is created only when
an existing branch becomes difficult to navigate.

Validate with the `$enrich-project-learning` bundled script:

```powershell
python <enrich-project-learning>/scripts/validate_project_registry.py learning
```
