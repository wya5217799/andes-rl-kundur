# Migration Complete — andes-rl-kundur (2026-05-15)

## What was migrated

From `Multi-Agent  VSGs`:
- **ANDES code**: env/andes (8 files), scenarios/kundur/train_andes*.py (5 files),
  probes/andes_common (4 modules + README), agents (SAC, SAC_CTDE, MA_manager, networks),
  utils/monitor, evaluation/paper_grade_axes
- **scripts/research_loop**: r01-r36 evaluation drivers + exploratory scripts (41 files; 2 archived to _archive/)
- **Paper**: main.tex + 21 figure scripts + ~36MB figures (174 files)
- **Documentation**: docs/paper/kd_4agent_paper_facts.md, andes_replication_status_2026-05-07_6axis.md
- **Memory structure**: 25 round folders (memory/rounds/R01-R36), 10 handoffs, claim ledger
- **Audit trail**: _legacy/ folder (RESEARCH_TRAIL.md, CONTEXT.md, ANDES.md, frozen)

From `毕业论文`:
- Dissertation main.tex + figures (37) + refs.bib + class file
- CONTEXT.md, WRITING_STANDARD.md (dissertation-scoped)
- Appendix_B_Weekly_Records.docx

## Memory system status

- **39 claims** (19 findings / 6 decisions / 14 corrections) fully indexed
- **2 Python tools**: validate.py (schema + drift chain), render.py (STATE.md auto-gen)
- **8 pytest tests** passing (100%)
- **STATE.md** auto-rendered with post-fix headlines as current view
- **Drift chain**: pre-fix headlines (0.613/0.554/0.607/0.110) properly mapped to post-fix
  (0.444/0.415/0.439/0.104) via CLM supersedes graph; validator enforces consistency

## Not migrated (intentional per spec §6)

- ODE backend (env/ode/)
- Simulink backend (env/simulink/, engine/, slx_helpers/, scenarios/*/train_simulink.py)
- Simulink-specific config sections (trimmed from config.py)
- Full results/ tree (only whitelist manifest + headline JSON files)

## Ledger readiness

The memory ledger is now the single source of truth for:
- Round plans (memory/rounds/R01-R36/*.md)
- All claims (memory/claims/CLM-*.md) with full audit trail
- All findings, decisions, corrections with causality
- Drift accounting and paper magnitude calibration
- Handoff chain (memory/handoffs/)
- Current STATE.md (re-generated from claims)

## Next steps for continuation

1. New round: `mkdir memory/rounds/R37 && create memory/rounds/R37/plan.md`
2. Add post-review revisions as new claims (cite CLM-IDs in paper)
3. Maintain drift chain if pre-fix numbers resurface
4. Optional: full-depth replay of R01-R37 findings (currently lite seed, 39 headlines)
5. Populate results/whitelist with R21 best.pt + HAWE ensemble v4_ens3 configs (deferred)

## GitHub

- Private repo: https://github.com/wya5217799/andes-rl-kundur
- Main branch (tracks origin/main)
- Handoff registered in STATE.md "Most Recent Handoff" section
