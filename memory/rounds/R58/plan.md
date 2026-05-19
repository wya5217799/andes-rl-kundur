---
round: R58
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R58 plan — Paper-strict audit + ranking validity verification

**Date**: 2026-05-17
**Type**: audit (Phase 0) + experiment (Phase 1-3, paper-strict reward + paper eval metric)
**Wall budget**: ~4.2 hr (~30 min code + ~72 min train + ~85 min sanity + ~1 hr historical re-eval + ~50 min paper-strict eval + ~30 min verdict)

## Trigger

`critic`-agent audit (logged in this round's verdict as the Phase-0
finding) revealed that what `CONTEXT.md:85-87` calls "V4 paper-faithful"
materially deviates from Yang et al., IEEE TPWRS 2023, in three
CRITICAL ways:

1. **PHI_ABS = 50** adds a non-paper reward term `-(d_omega)²` that
   dominates the frequency component when nodes are approximately
   synchronized (paper's `r^f` is sync-only, not deviation-only)
2. **PHI_H = PHI_D = 0.0056** (1/178 of paper Eq.14 nominal 1.0)
   effectively nullifies the parameter-conservation constraint (paper
   §0.5 dual objective)
3. **Evaluation protocol is incommensurable** with the paper: we score
   on 2 specific scenarios (LS1/LS2) with a project-invented 6-axis
   composite, while the paper scores on 50 random scenarios with a
   global cumulative frequency reward formula

Plus a 4th gap: **training horizon 75 ep vs paper 2000 ep** (paper
says 500 to stabilize). All R56/R57 results are "early snapshot," not
converged.

This means CLM-0063/0065/0066/0067 headline numbers (0.526 / 0.501 /
0.3674) cannot be compared to paper Table III (-8.04 / -15.2 etc.).
**The internal algorithm ranking (TD3+LSTM > TD3 > SAC) may or may not
hold under paper-strict reward + paper-strict eval.** This round
verifies it.

## Hypotheses

### H1 — Ranking robustness (primary question)

Under paper-strict reward (PHI_ABS=0, PHI_H=PHI_D=1.0) and paper
evaluation metric (global cumulative `r^f`):

- **H1.A** TD3+LSTM > TD3 > SAC ranking holds → previous research is
  valid, algorithm choice is the load-bearing factor, reward hack is
  necessary engineering but doesn't bias conclusions
- **H1.B** ranking partially holds (e.g., TD3+LSTM ≈ TD3, SAC still
  worst) → LSTM bonus was inflated by PHI_ABS interaction, but TD3 >
  SAC is robust
- **H1.C** ranking reverses (SAC > TD3 / TD3+LSTM) → previous
  conclusions are artifacts of the reward hack; paper's SAC choice is
  actually optimal for paper's reward
- **H1.D** all algorithms collapse (geo ≈ 0 across the board) → paper
  reward at 75 ep is untrainable on ANDES; need 500+ ep, scope C

### H2 — Pure vs rescaled (secondary question)

Comparing `paper_strict_pure` (PHI_H/D=1.0) vs `paper_strict_rescaled`
(PHI_H/D=0.0056, both PHI_ABS=0):

- **H2.A** _pure diverges as predicted by R18 verdict ("r_h/r_f ≈
  36000:1 → training fails") → confirms R18 mechanism, justifies
  rescale as engineering necessity (not paper hack)
- **H2.B** _pure trains but slower / worse than _rescaled → rescale
  is a positive tweak, paper Eq.14 nominal values are sub-optimal in
  the ANDES regime
- **H2.C** _pure trains as well as _rescaled → R18 verdict was wrong;
  PHI_H/D rescale was unnecessary
- **H2.D** _pure trains BETTER than _rescaled → catastrophic; rescale
  is harmful

### H3 — s51 _pure 500-ep sanity (tertiary)

If H2.A confirmed at 75 ep, does the divergence persist at 500 ep, or
does the pure config eventually converge given enough time?

## Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Old `V4Config.paper_faithful()` | **Retained unchanged** | Don't break R56/R57 reproducibility |
| New configs | `paper_strict_pure()`, `paper_strict_rescaled()` classmethods on V4Config | Same dataclass, sibling classmethods |
| Eval metric | `compute_global_cum_rf(trace)` returning `-Σ_t Σ_i (f_i,t - f̄_t)²` (paper Sec.IV-C) | Direct paper formula |
| Test set | N=20 (18 random + LS1 + LS2 anchors), fixed seed=2026 → JSON | Reproducible, paper-aligned distribution |
| Disturbance distribution | random PQ bus ∈ {6,7,8,9,10,11,12,14,15,16}, magnitude ∈ [-300, +300] MW, ± uniform | Covers LS1 (-248) and LS2 (+188) |
| Algo matrix | SAC + TD3 + TD3+LSTM warmup, all 3 | Discriminates LSTM vs TD3 vs SAC contributions |
| Seeds | 49 / 50 / 51 | Match R56/R57 |
| Config matrix | 2 configs (_pure, _rescaled) | Discriminates PHI_H/D effect |
| Training horizon | 75 ep (main) + 1 seed 500 ep (sanity) | Match R57 + paper convergence check on cheapest single |
| Historical re-eval | All 9 V4 historical SOTAs (R48-β s49/50/51, R51-α s49/50/51 SAC, R57-α s49/50/51) under paper metric | Cross-config comparability |

## File-by-file implementation

| Step | File | Change | TDD test |
|---|---|---|---|
| 1 | `docs/adr/0002-paper-strict-vs-paper-faithful.md` (new) | ADR documenting term split | — |
| 2 | `CONTEXT.md` | Amend `paper-faithful` def + add `paper-strict-pure` / `paper-strict-rescaled` terms | — |
| 3 | `src/.../env/andes/v4_config.py` | `@classmethod paper_strict_pure()` + `@classmethod paper_strict_rescaled()` | unit: returns expected PHI values |
| 4 | `src/.../evaluation/paper_strict_eval.py` (new) | `compute_global_cum_rf(trace)` paper Sec.IV-C formula | unit: hand-computed cross-check |
| 5 | `src/.../evaluation/paper_strict_eval.py` | `generate_test_scenarios(n, seed, include_anchors)` | unit: deterministic + LS1/LS2 included |
| 6 | `scripts/_r58_paper_strict_train.py` (new) | Driver for 18-seed sweep | (e2e via train.py) |
| 7 | `scripts/_r58_paper_strict_eval.py` (new) | Driver: load ckpt → run 20 scen → paper metric | integration smoke test |
| 8 | `tests/test_paper_strict_config.py` (new) | step-3 tests | — |
| 9 | `tests/test_paper_strict_eval.py` (new) | step-4 + step-5 tests | — |
| 10 | `tests/test_paper_strict_integration.py` (new) | smoke load-run-metric integration | — |

## Training command (paper-strict driver)

```bash
# For each config in {pure, rescaled}, for each algo in {sac, td3, td3_lstm},
# for each seed in {49, 50, 51}:
PAPER_STRICT_CONFIG=$cfg /home/wya/andes_venv/bin/python scripts/train.py \
    --algo $algo --normalize-actions --episodes 75 \
    --seed $seed --hidden-size 64 \
    $([ "$algo" = "td3_lstm" ] && echo "--lstm-lr-warmup-eps 5") \
    --save-dir results/r58_${cfg}_${algo}_s${seed} \
    --log-interval 10
```

3 parallel WSL waves, ~12 min/seed → ~72 min total for 18 seeds.
Plus s51 _pure 500-ep ~85 min wall single.

## Eval command (paper metric)

```bash
/home/wya/andes_venv/bin/python scripts/_r58_paper_strict_eval.py
# Iterates 27 ckpt dirs × 20 scenarios
# Outputs: results/research_loop/r58_paper_metric.json (per-ckpt geo + cum_rf)
```

## Risk register

| Risk | Mitigation |
|---|---|
| _pure config diverges → no ckpt to evaluate | Hypothesis-confirming, not failure — verdict still meaningful |
| Eval 27 × 20 scenarios takes longer than estimate | Pre-budget 50 min wall; report if exceeds |
| Disturbance distribution choice affects relative ranking | Cover paper LS1/LS2 magnitudes; anchor results to those 2 known cases |
| Old `V4Config.paper_faithful()` callers break | All callers retained; new classmethods are additive only |
| Codex parallel session takes R58 | Atomically reserved via `reserve_round.py` |
| Test suite regression | Full pytest after each TDD cycle |

## Success criteria (pre-registered)

**Round-level POSITIVE** iff any of:
- H1.A / H1.B confirmed under paper metric → ranking validity established
- H2.A confirmed → R18 verdict mechanism validated
- s51 _pure 500-ep gives meaningful gradient signal vs 75 ep → guides scope-C decision

**Round-level NEGATIVE** iff:
- H1.D + H2.D both trigger → previous research questionable across-the-board, requires full scope-D rework

## Schema plan

Expected:
- **CLM-0068** (finding/V) — Paper-strict audit findings (formal write-up of critic-agent verdict)
- **CLM-0069** (finding/V) — `paper_strict_pure` 3 algo × 3 seed result at 75 ep
- **CLM-0070** (finding/V) — `paper_strict_rescaled` 3 algo × 3 seed result at 75 ep
- **CLM-0071** (finding/V) — Historical V4 ckpts (R48-β/R51-α/R57-α) under paper metric
- **CLM-0072** (decision/S) — Ranking-validity conclusion: do CLM-0063/0065/0066/0067 still hold?

Conditional:
- **CLM-0073** (finding/V) — s51 _pure 500-ep sanity result
- **Q-0008** "paper convergence 500-ep across all 3 algo × 2 config" — only opened if 75-ep results inconclusive

## What R58 does not establish

- Paper-faithful Kundur 4-VSG full reproduction (requires scope D: adaptive inertia [25] baseline, REGCA1 wind farm, 500-ep training, 50-scen eval — multi-day commit)
- Whether 500 ep is sufficient (paper's 2000 ep is even longer)
- Whether the specific 20-scen distribution we picked is representative of "real" paper distribution (paper §13 Q-C ambiguity)
- Effect of N_SUBSTEPS=5 vs 1 (would require separate study)
- Effect of obs/reward frequency-scale mismatch (rad/s vs Hz)
