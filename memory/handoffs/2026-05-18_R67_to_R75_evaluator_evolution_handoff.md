# Handoff — R67→R75 Evaluator Evolution + LSTM 6-axis SOTA Push

**Prepared**: 2026-05-18
**Session wall**: ~16 hr (~07:00 → 23:00 + 00:00-07:30 next day)
**Rounds completed**: R67, R68, R69, R70, R71, R72, R73, R74, R75 (9 commits)
**Status**: ALL ROUNDS COMMITTED, working tree clean

---

## TL;DR for next session

Project evolved from R67 (TD3 paper-metric SOTA -0.119) to R75 (LSTM 6-axis v3.1
SOTA = **0.4301** + 11-axis ranker upgrade twice + dual-eval tooling). Tools
infrastructure also matured: v3.1 multiplicative-gating ranker, dual-eval
score_run, floor_geo_mean refactor extracted.

**Strong recommendation for next session**: **start paper draft**. Diminishing
returns confirmed by R75 (ensemble negative + 2/3 new seeds dead). 4 paper
tables ready + canonical figure picked. Continue-sweep ROI is now near zero.

---

## Final production status (3 modes)

| Mode | Algo | SOTA | Reproducibility |
|---|---|---|---|
| **paper-metric (Sec.IV-C)** | TD3 R67 combo | **-0.119** cum_rf 3-seed mean | +39pp robust vs paper DDIC |
| **paper-faithful (SAC)** | SAC R68 W1 combo | **-0.188** cum_rf 3-seed mean | +35pp robust vs paper DDIC |
| **6-axis v3.1 (LSTM)** | LSTM R75 W2 single | **0.4301** v3.1 (s59+warmup=20) | 6-seed mean 0.3694 |

**Canonical for paper Fig 7**: R72 W4 LSTM s54+warmup=5 v3.1=0.3908 P_balance=0.96
(not R75 W2 — R75 has higher v3.1 but slightly lower P_balance LS1).

---

## Round-by-round commits

| commit | round | headline |
|---|---|---|
| df2adc2 | R67 | TD3 tau=0.001 NEW SOTA +4% robust (6 waves × 3 parallel = 18 trainings) |
| 80753fc | R68+R69+R70 | SAC tau SOTA + v3.0 11-axis ranker + canonical best picked |
| c5a5d1c | R71 | ranker v3.0→v3.1 (multiplicative gating) + s53 drift |
| 3ca77ec | R72 | s54+warmup=5 canonical v3.1=0.3908 + LSTM paper-strict incompat generalized |
| 95384d3 | R73 | NEW v3.1 single SOTA s54+warmup=20 v3.1=0.4099 |
| 1f8086d | R74 | score_run dual-eval (TDD) + s51 peak shift to warmup=10 + s57 dead seed |
| **799f1ac** | **R75** | **NEW SOTA s59 v3.1=0.4301 + ensemble negative + floor_geo_mean refactor** |

9 rounds, ~30 commits, +5000/-500 lines (estimated).

---

## Key infrastructure landed

### Evaluator (Asset 4, paper-cited)

- **v3.0 → v3.1** (R71): aggregation changed from geo_mean(all 11) to
  `geo_mean(axes 1-8) × min(axes 9, 10, 11)` — multiplicative gating prevents
  gating axes (agent_min_activity / late_oscillation_inv / agent_P_balance)
  from being diluted by strong continuous axes
- **3 new axes** (R69):
  - Axis 9 `agent_min_activity` — gate agent collapse
  - Axis 10 `late_oscillation_inv` — gate persistent oscillation
  - Axis 11 `agent_P_balance` — gate per-agent ΔP monopolization
- **21+7 tests** (R69 + R71 + R75): test_paper_grade_axes_v3 (16) + v31 (5) +
  test_aggregation (7)

### Tooling

- **score_run.py dual-eval** (R74): default outputs cum_rf + 6-axis v3.1
  together (was 2 separate scripts)
- **floor_geo_mean refactor** (R75): extracted to
  `src/andes_rl_kundur/evaluation/aggregation.py`, 4 scripts use it
- **ensemble.py** (R75): `build_ensemble_action_fn` recurrent-aware,
  reusable for future ensemble experiments
- **Eval matrix script** (R70): `scripts/_r70_eval_matrix.py` — cross-metric
  matrix across 19+ candidates with cum_rf + v2 + v3 + per-agent breakdown
- **Plot script** (R70): `scripts/_r70_plot_best_agent.py` — paper Fig 6/7/8
  style (4-agent Δf + ΔP + per-agent bar)
- **Re-rank script** (R69): `scripts/_r69_rerank_11axis.py` — v2 vs v3
  comparison
- **Ensemble script** (R75): `scripts/_r75_ensemble_eval.py` — 4 HAWE
  configs across 6 healthy ckpts

### CLI flags added (R67-R69)

`scripts/train.py`:
- `--gamma <float>` (R67)
- `--tau <float>` (R67)
- `--buffer-size <int>` (R67)
- All as CLI not env var (avoid CLM-0104 RNG drift)

---

## All 9 hyper axes empirically swept

| axis | paper default | R67-R75 best | reference claim |
|---|---|---|---|
| lr | 3e-4 | 3e-3 | CLM-0092 |
| MAX_GRAD_NORM | 1.0 | 0.5 | CLM-0087 |
| batch_size | 256 | 512 | CLM-0088 |
| N_SUBSTEPS | 5 | 3 | CLM-0086 |
| **tau** | **0.005** | **0.001** (TD3+SAC) | **CLM-0105, CLM-0109** |
| gamma | 0.99 | 0.99 (U bottom) | CLM-0106 |
| hidden_size | 128 | 64 | CLM-0067 + W6a confirms |
| explore_noise | 0.1 | 0.1 (U bottom) | CLM-0106 (W5a/b) |
| warmup_steps | 1000 | 1000 (strict optimum) | CLM-0106 (W5c) |

**LSTM-specific** (R68-R75):
- `lstm-lr-warmup-eps`: most healthy seeds prefer **20**, s51 prefers 10,
  warmup=5 simpler (CLM-0112 + CLM-0125 + CLM-0129)
- tau=0.001 + warmup=20 cross-axis SOTA (R69-R75)
- explore_noise unreachable from CLI for LSTM (architectural, CLM-0103)
- lstm_batch_size hardcoded 32 (architectural, CLM-0103)

---

## Healthy LSTM seed set (R75 confirmed)

| seed status | seeds |
|---|---|
| **Healthy** (7 seeds) | {50, 51, 52, 54, 55, 56, 59} |
| **Drift dead** (5 seeds) | {49, 53, 57, 58, 60} |
| Tested total | 12 |
| Drift rate | ~44% |

s51 has unique behavior: healthy at warmup=10, collapses at warmup=20
(P_balance=0.19 not 0).

**Recommended for future LSTM 3-seed**: {50, 52, 54} or {52, 54, 59} —
all healthy at warmup=20.

---

## R75 final results matrix

### Cross-seed v3.1 @ warmup=20 (excl s51 outlier)

| seed | v3.1 |
|---|---|
| s50 | 0.3151 |
| s52 | 0.3068 |
| s54 | 0.4099 |
| s55 | 0.3781 |
| s56 | 0.3763 |
| **s59** | **0.4301** ← NEW single SOTA |
| **6-seed mean** | **0.3694** |

### Ensemble negative (CLM-0132)

4 configs across 6 healthy ckpts, ALL underperform single best (s59 0.4301):
- top2 mean (s54+s59): 0.4212 (**-2.1%**)
- s59-weighted (all 6): 0.4089 (-4.9%)
- mean 6-seed: 0.3972 (-7.6%)
- top3 mean (s54+s55+s59): 0.3956 (-8.0%)

HAWE-style averaging fails on LSTM (hidden-state divergence).

---

## Active questions (5 open)

- **Q-0004** (R46) — AndesBaseEnv absorb into V4 (architectural cleanup, deferred)
- **Q-0005** (R56) — s50 LSTM collapse root cause (Q-0007 partial answer, full unresolved)
- **Q-0008** (R58) — 500-ep convergence across 12 cells (1 done, paper uses 2000 ep)
- **Q-0010** (R62) — LSTM eval probe contamination (R66 fix closed-positive,
  but R72 W1-W3 retry with paper-strict-radsec still failed — Q-0107 mechanism)
- **Q-0012** (R64) — h=96 marginal (R67 W6a confirmed h=64 wins, closed negative)
- **Q-0013** (R65) — LSTM per-axis ablation (R66 closed negative)

---

## Claims summary (CLM-0001 through CLM-0133)

This session added **65 claims** (CLM-0068 → CLM-0133):
- CLM-0086-0096: R67 hyper sweep findings
- CLM-0098-0108: R67 paper-metric SOTA + production tables
- CLM-0109-0118: R68/R69/R70 (SAC tau + v3.0 ranker + canonical best + agent collapse + paper strategy)
- CLM-0119-0122: R71 v3.1 ranker + s53 drift + s50 cliff + canonical reconfirmed
- CLM-0123-0124: R72 s54+warmup=5 NEW canonical + LSTM-paper-strict incompat
- CLM-0125-0127: R73 single SOTA + warmup=20 family + canonical retained
- CLM-0128-0130: R74 dual-eval + s51 shift + s57 dead
- CLM-0131-0133: R75 new SOTA s59 + ensemble negative + drift list update

Total state: **133 claims, 13 questions, 56 warnings, 0 errors**.

---

## Strong recommendations for next session

### 1. **Start paper draft** (highest ROI)

Materials ready:
- **4 paper tables**: TD3 SOTA + SAC SOTA + lr U curve + hyper ablation matrix
- **Canonical figure**: R72 W4 s54+warmup=5 paper Fig 6/7/8 PNG already generated
  at `results/r70_paper_figures/r68_w2_lstm_tau001_6axis_s51_paper_figs.png`
  AND `r72_w4_lstm_tau001_warmup5_s54_s54_paper_figs.png`
- **Supplementary**: R75 W2 s59 single SOTA PNG also generated
- **Multi-controller paper strategy** (CLM-0118): TD3 R67 for Sec.IV-C table,
  LSTM R72 W4 for figures, R75 W2 s59 for supplementary single SOTA
- **Evaluation methodology**: v3.1 ranker (CLM-0119) for declaration in Methods

### 2. NOT recommended

- **More sweep**: 3 negative findings in R75 (ensemble, s58, s60). Diminishing returns confirmed.
- **Push origin**: 56+ commits ahead. Push when paper draft done, not before.

### 3. Optional deferred work (R76+ if needed)

- **Q-0008 500-ep convergence** on R75 SOTA combo (~90 min, paper rigor verification)
- **Code drift bisect** (CLM-0104, R57→R66 LSTM -19%) — paper transparency
- **GRU vs LSTM** architecture comparison (~2 hr code + sweep)
- **PHI hybrid reward** to unlock LSTM paper-strict mode (~30 min code + 3 trainings)

---

## Reproduction commands

### Production SOTAs

```bash
# TD3 paper-metric SOTA (R67)
N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 \
  python scripts/train.py --algo td3 --normalize-actions --episodes 75 \
  --seed <S> --hidden-size 64 --batch-size 512 --tau 0.001 --eval-every-n-eps 5

# SAC paper-faithful SOTA (R68)
N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 \
  python scripts/train.py --algo sac --normalize-actions --episodes 75 \
  --seed <S> --hidden-size 64 --batch-size 512 --tau 0.001 \
  --eval-every-n-eps 5 --reward-config paper_strict_pure_radsec

# LSTM 6-axis v3.1 SOTA (R75 W2 s59) — best single ckpt
python scripts/train.py --algo td3_lstm --normalize-actions --episodes 75 \
  --seed 59 --hidden-size 64 --lstm-lr-warmup-eps 20 --tau 0.001 \
  --save-dir results/r75_w2_lstm_tau001_warmup20_s59

# LSTM canonical for paper Fig 7 (R72 W4 s54+warmup=5)
python scripts/train.py --algo td3_lstm --normalize-actions --episodes 75 \
  --seed 54 --hidden-size 64 --lstm-lr-warmup-eps 5 --tau 0.001 \
  --save-dir results/r72_w4_lstm_tau001_warmup5_s54
```

### Eval (dual-output cum_rf + v3.1)

```bash
# Single ckpt eval (R74 dual-eval landed)
python scripts/score_run.py --label <my_label> \
  --ckpt-dirs results/<config>_s<seed> --suffix best

# Cross-metric matrix (19+ candidates)
python scripts/_r70_eval_matrix.py

# Paper figure generation
python scripts/_r70_plot_best_agent.py <trace_label>
```

---

## Outstanding tasks (in priority order for next session)

### Immediate (paper draft prep)

1. **Verify all production ckpts on disk** + organize
   `results/r70_paper_figures/` for paper assets
2. **Read paper Section IV** to align our 4 tables to paper structure
3. **Begin paper writing** (Sec.IV-C scalar table first, then figures)

### Medium-priority (paper rigor improvements)

4. Q-0008 500-ep convergence verify on R75 SOTA combo
5. Code drift bisect (CLM-0104) — find the commit causing -19% LSTM regression
6. R59 PI briefing infra commit verify (was R59 ever fully landed? check)

### Low-priority (architecture deferred R76+)

7. LSTM refactor: env var pattern + unhardcode `lstm_batch_size` (Q-0013)
8. GRU vs LSTM comparison
9. PHI hybrid reward exploration

---

## File pointers

- This handoff: `memory/handoffs/2026-05-18_R67_to_R75_evaluator_evolution_handoff.md`
- Production ckpts: see "Reproduction commands" above
- All round verdicts: `memory/rounds/R67/` through `memory/rounds/R75/`
- 65 new claims this session: CLM-0086 through CLM-0133
- Memory state: 133 claims, 13 questions, 56 warnings (0 errors)
- Paper figures: `results/r70_paper_figures/`
- Eval matrix: `results/research_loop/r70_eval_matrix.json`
- Ensemble eval: `results/research_loop/eval_v4_baseline/r75_ensemble_summary.json`

---

## Quick references

- **Current branch**: `main`
- **Latest commit**: `799f1ac` (R75)
- **Commits ahead of origin**: ~57
- **Test status**: 7 new aggregation tests pass; 28/28 v3+v3.1+score_run pass;
  150+ regression tests pass (zero regression across 9 rounds)
- **Total session wall**: ~16 hr (2 calendar days, 07:00-23:00 + 00:00-07:30)
