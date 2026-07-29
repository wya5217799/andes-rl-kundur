# Archived research-loop scripts

These scripts ran specific experimental rounds (R01–R36) or one-off
analyses. They are not on the paper path. Their findings are captured
in `memory/rounds/RNN/verdict.md` and the corresponding atomic claims
in `memory/claims/CLM-NNNN.md`.

Kept for research auditability. **Do not delete** — historical
provenance is the only purpose of this directory.

Current lifecycle policy is canonical in
`docs/repo-hygiene/contract.json` and explained in
`docs/repo-hygiene/executables.md`. New round-specific logic starts in
`probes/`; stable execution adapters remain in top-level `scripts/`.

---

## Active evaluation adapters

The maintained top-level adapters are:

- `eval_no_control.py` — zero-action baseline
- `eval_ddic.py` — DDIC evaluation
- `eval_all_seeds.py` — batch evaluation across seeds
- `eval_ensemble.py` — HAWE inference-time ensemble
- `eval_hybrid.py` — maintained hybrid evaluation
- `score_run.py` — paper-grade scoring adapter

The reusable ranker implementation lives behind the package interface.

---

## Contents of this directory

### Specialty eval drivers (variant ablations)

| File | Originating round | Status |
|------|-------------------|--------|
| `eval_v4_ctde.py` | R11–R13 (CTDE shared-critic) | replicated in V2; not retried in V4 |
| `eval_v4_ensemble_stoch.py` | R32 stochastic-actor ensemble | refuted; worse than no-control |
| `eval_v4_ensemble_peraxis.py` | per-axis ensemble probe | inconclusive |
| `eval_swa_baseline.py` | R26 SWA / model-soup baseline | SWA ≈ HAWE at sweet spot |
| `eval_n2_fresh_seed_hawe.py` | R34 N2 fresh-seed HAWE | refuted lineage hypothesis |
| `eval_freshseed_hawe_sweep.py` | R34 sweep | confirmed 99.3% R21 recovery |

### Round analysis scripts

| File | Round | Purpose |
|------|-------|---------|
| `dump_eval_v4_ranking.py` | post-R21 | dump ranking table |
| `dump_freshseed_sweep.py` | R34 | sweep scoreboard |
| `dump_n2_freshseed_scores.py` | R34 | N2 fresh-seed table |
| `dump_per_axis_breakdown.py` | R35 | per-axis breakdown for Table III |
| `dump_principal_gini_table.py` | R33 | Gini-vs-score statistics |
| `analyze_per_agent_contribution.py` | post-R30 | per-agent contribution analysis |
| `experiment_r36_ranker_tuning.py` | R36 | ranker sensitivity sweep |

### Daemon / state-tracking utilities

| File | Purpose |
|------|---------|
| `_tick.py` | daemon tick logic for live monitoring |
| `state_io.py` | research-loop state JSON I/O |
| `check_state.py` | state inspection CLI |
| `handoff_index.py` | handoff-doc index builder |
| `k_max_calc.py` | k_max computation helper |

These are remnants of an early "research-loop daemon" workflow that
was superseded by the `memory/` ledger system (claims + rounds +
auto-rendered STATE.md).
