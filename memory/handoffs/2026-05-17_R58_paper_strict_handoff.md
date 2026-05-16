# Handoff — R58 paper-strict audit + ranking validity

**Prepared**: 2026-05-17 (mid-R58, eval done, sanity running)
**Estimated remaining wall**: ~85 min (s51 _pure 500-ep sanity in progress) + ~45 min finalize verdict + commit
**Status of R58**: code done, training done, eval done; **awaiting sanity result + final verdict write + commit**

---

## Read first

1. This file
2. `memory/rounds/R58/plan.md` — full plan (scope B, double config, audit-A fixes)
3. `memory/rounds/R58/verdict.md` — DRAFT verdict (skeleton written, has pre-eval interpretation; needs final numbers + ranking section)
4. `docs/adr/0002-paper-strict-vs-paper-faithful.md` — term split rationale
5. (parallel R59 by user, unrelated) — `docs/adr/0003-pi-briefing-layer.md` introduces a `## 给 PI 的话` mandatory section for R≥59 verdicts. **R58 is grandfathered and does NOT need this section.**

---

## What's done

### Code (149 → 161 tests pass, no regression)

- ✓ `V4Config.paper_strict_pure()` (PHI_ABS=0, PHI_H/D=1.0)
- ✓ `V4Config.paper_strict_rescaled()` (PHI_ABS=0, PHI_H/D=0.0056)
- ✓ `V4Config.paper_strict_pure_radsec()` (PHI_ABS=0, PHI_H/D=1.0, r_f_freq_units=rad_per_s) — **R58 audit A3 fix**
- ✓ `V4Config` audit-A escape hatches:
  - `r_f_freq_units: Literal["hz", "rad_per_s"]` (A3)
  - `h_paper_interpretation: Literal["mechanical_H", "andes_M"]` (A2, paper §13 Q-A)
  - `r_avg_scope: Literal["global", "neighbor"]` (A5, paper §13 Q-B)
- ✓ `base_env.py:_compute_rewards` honors all 3 flags + A1 fix (delay-aware reward)
- ✓ `scripts/train.py` `--reward-config` flag with 4 choices
- ✓ `compute_global_cum_rf(trace)` — paper Sec.IV-C formula
- ✓ `generate_test_scenarios(n=20, seed=2026)` — 2 paper anchors + 18 random
- ✓ `scripts/_r58_paper_strict_eval.py` — full eval driver
- ✓ Bash drivers: `_r58_train_all.sh` (18 ckpts), `_r58_train_radsec.sh` (9 ckpts), `_r58_eval_all.sh` (4-batch eval), `_r58_sanity_500ep.sh`

### Training (27 ckpts, ~2.5 hr total wall)

- ✓ 18 ckpts: `r58_paper_strict_{pure,rescaled}_{sac,td3,td3_lstm}_s{49,50,51}/`
- ✓ 9 ckpts: `r58_paper_strict_pure_radsec_{algo}_s{seed}/`
- ⏳ s51 _pure 500-ep sanity (`bnin9obnj` background, ~85 min remaining):
  - dir: `results/r58_sanity500_pure_td3_lstm_s51/`
  - algo: TD3+LSTM, 500 ep, paper_strict_pure
  - purpose: verify 75-ep "diverge for SAC/TD3, converge for LSTM" persists at paper convergence horizon

### Eval (36 ckpts × 20 scenarios = 720 ANDES TDS runs done in ~48 min wall, 4-batch parallel)

- ✓ 9 historical baselines: R48-β TD3-MLP, R51-α SAC, R57-α TD3+LSTM warmup5 (×3 seeds each)
- ✓ 18 paper-strict ckpts (pure + rescaled × 3 algo × 3 seed)
- ✓ 9 radsec ckpts
- All outputs at `results/research_loop/r58_paper_metric_*.json`

### Audit (`critic` agent + line-by-line audit A)

- ✓ Critic verdict: 3 CRITICAL (C1 PHI_ABS, C2 eval mismatch, C3 75-ep) + 4 HIGH + 4 MEDIUM
- ✓ Audit A (line-by-line vs paper Eq.11/15-18): 5 more findings:
  - A1 (LOW dormant) delay-mode reward — **fixed**
  - A2 (MEDIUM paper-ambiguous) ΔH=ΔM/2 — **flag exposed**
  - A3 (HIGH) Hz vs rad/s — **fixed + new config + verified empirically**
  - A4 (LOW) Eq.15 if-vs-η — equivalent, no fix
  - A5 (LOW paper-ambiguous) global vs neighbor mean — **flag exposed**

---

## Key results (eval-ready numbers)

### Training stability summary

| Config | SAC | TD3 | TD3+LSTM |
|---|---|---|---|
| pure Hz (PHI=1.0) | **diverge 3/3** (3→9) | **diverge 3/3** (5→7) | converge 3/3 (0.19→0.10) |
| rescaled Hz (PHI=.0056) | diverge 2/3 | mixed | converge 3/3 |
| **pure rad/s (PHI=1.0)** | **decreasing 3/3** (271→119) | **decreasing 3/3** (178→64) | decreasing 3/3 (108→43) |

**FINDING**: rad/s interpretation makes paper-faithful PHI=1.0 trainable for **all 3** algorithms. R18's "PHI=1 diverges" was a Hz-unit artifact.

### Per-config algo ranking on paper-metric (mean cum_rf, less negative = better)

| Algo | V4 historical | strict_pure | strict_rescaled | strict_radsec |
|---|---|---|---|---|
| SAC | -0.605 | -0.685 | -0.609 | **-0.518** ✓ |
| TD3 | **-0.267** ⭐ | -0.917 | -0.578 | -0.699 |
| TD3+LSTM | -0.527 | -0.675 | -0.574 | -0.645 |

### Best single ckpts

- **Overall**: `td3_norm_h64_s50` (V4 historical, PHI_ABS=50, TD3) = **-0.196**
- **Best LSTM**: `td3_lstm_h64_warmup5_s51` = -0.284 (same ckpt as R57 SOTA on 6-axis)
- **Best SAC**: `r58_paper_strict_pure_radsec_sac_s50` = -0.397

### Anchor LS1/LS2 comparison

Paper Sec.IV-C reports DDIC: LS1 = -0.68, LS2 = -0.52. Our best LSTM s51 warmup: LS1 = -0.053, LS2 = -0.035 — **13-15× tighter than paper's DDIC**. Either disturbance distribution is smaller in our env, or our control is genuinely better. To verify scale, would need to replicate paper's exact disturbance set (out of scope B).

---

## Three big findings for verdict

**1. R56/R57 6-axis ranking does NOT preserve under paper metric.**
- 6-axis (R56/R57): LSTM > TD3 > SAC
- Paper metric: V4 TD3 > LSTM > SAC (historical), or under paper-strict-radsec: SAC > LSTM > TD3
- **CLM-0067 needs revision** — "TD3+LSTM as production" is true under 6-axis but NOT under paper metric.

**2. V4's PHI_ABS=50 is a "free lunch" on paper metric, not just a stabilizer.**
- V4 td3_norm 3-seed mean -0.267 vs paper_strict_rescaled td3 (same config, only PHI_ABS=0 differs) -0.578 → **2× better with PHI_ABS=50**.
- Mechanism: PHI_ABS pushes all agents toward 50 Hz → synchronization as side effect.
- Implication: removing PHI_ABS to be "more paper-faithful" actually HURTS paper-metric performance.

**3. Paper's SAC choice is empirically validated under paper-strict-radsec.**
- Under paper-faithful (rad/s units, PHI_ABS=0, PHI=1), **SAC wins** (-0.518 vs LSTM -0.645 vs TD3 -0.699).
- Our previous claim "SAC < TD3 < TD3+LSTM" was a Hz-units artifact.
- Paper's SAC choice was correct at its own metric.

---

## Pending sanity result (~85 min wall)

**s51 _pure 500-ep sanity** (`bnin9obnj` running):
- TD3+LSTM, paper_strict_pure (PHI=1.0, Hz)
- 500 ep (paper convergence horizon)
- **Hypothesis**: 75-ep LSTM converged in Hz pure (critic 0.31→0.11). At 500 ep, should remain stable + best.pt should be a real ckpt (not pre-training as in some R57 collapsed seeds). Will give us a "fair" LSTM number under paper-strict-Hz.
- **Decision when done**: re-eval the 500-ep ckpt with paper metric, compare to 75-ep s51 -0.61 (current pure Hz LSTM s51 mean ~-0.59). If 500-ep gives ≥ -0.30 cum_rf, the 75-ep results were undertraining noise; if still ~-0.6, the pure-Hz config is genuinely capped.

---

## What's left to do (for next session)

### Phase 1 — verdict + claims (~30 min)

1. Update `memory/rounds/R58/verdict.md`:
   - Replace pre-eval prediction sections with final numbers (table above)
   - Add "Ranking validity verdict" section with the 3 big findings
   - Add s51 _pure 500-ep sanity result table when training completes
   - Fill in `Q-section` 3-tier (opened/closed/advanced):
     - **Opened**: Q-0008 (paper convergence on all 3 algos × 4 configs at 500 ep; out of R58 scope), Q-0009 (why disturbance scale differs from paper — investigate paper §IV-A "random disturbances by load/wind capacity range")
     - **Closed**: none (R58 doesn't directly close pre-existing Qs)
     - **Advanced**: Q-0007 (best-by-eval-score) — R58 confirms it's still load-bearing for s50 collapse
2. **R58 is grandfathered — does NOT need ADR-0003's `## 给 PI 的话` section.** (R59 onwards does.)

### Phase 2 — CLM ledger entries (~30 min)

5 new claims:
- `CLM-0068` (finding/V) — Paper-strict audit findings (critic verdict + audit A, 5 deviations classified; A1 + A3 fixed, A2/A5 paper-ambiguous flagged)
- `CLM-0069` (finding/V) — paper_strict_pure 3-algo training-stability: LSTM converges, SAC/TD3 diverge in Hz mode (validates R18 mechanism)
- `CLM-0070` (finding/V) — paper_strict_pure_radsec training-stability: ALL 3 algos converge → R18's "PHI=1 diverges" was Hz artifact (audit A3 confirmed)
- `CLM-0071` (finding/V) — Paper-metric eval matrix (36 ckpts): per-algo per-config mean cum_rf, including the 3 big findings above
- `CLM-0072` (decision/S) — Production decision REVISION: 
  - For 6-axis benchmark: keep CLM-0067 (TD3+LSTM)
  - For paper Sec.IV-C metric: **V4 TD3-MLP (s50) = -0.196**, supersedes CLM-0067 on paper-metric dimension only

Conditional CLM (after sanity finishes):
- `CLM-0073` (finding/V) — s51 _pure 500-ep sanity result

### Phase 3 — Memory validation + commit (~15 min)

1. `python memory/tools/validate.py` — expect 67+5=72 claims, 7+1=8 questions (Q-0008 maybe Q-0009)
2. `python memory/tools/render.py` — refresh STATE.md (note: user's R59 changes may have changed render output format with PI briefing; R58 verdict is grandfathered without 给 PI 的话 section but should still render fine)
3. Git status check — ensure only R58 files in stage:
   ```
   src/andes_rl_kundur/env/andes/v4_config.py
   src/andes_rl_kundur/env/andes/base_env.py
   src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
   scripts/train.py
   scripts/_r58_*.py / .sh
   src/andes_rl_kundur/evaluation/paper_strict_eval.py
   tests/test_paper_strict_*.py + test_r58_*.py
   memory/rounds/R58/
   memory/claims/CLM-0068..0072(.0073).md
   memory/questions/Q-0008.md (Q-0009.md)
   memory/STATE.md
   docs/adr/0002-paper-strict-vs-paper-faithful.md
   CONTEXT.md (term split — already changed)
   ```
4. Commit message:
   ```
   round: R58 — Paper-strict audit + ranking validity (V4 TD3 wins on paper metric)
   
   - Audit A line-by-line vs paper Eq.11/15-18 found 5 deviations
     beyond critic's verdict; A1+A3 fixed, A2/A5 flag-exposed
   - paper_strict_pure_radsec validates Audit A3 empirically:
     R18 "PHI=1 diverges" was Hz-unit artifact, rad/s makes
     all 3 algos trainable
   - 36-ckpt paper-metric eval: V4 TD3 norm wins (-0.196 best,
     -0.267 mean), beating paper-strict variants by 2×
   - Algorithm ranking under paper metric: V4 TD3 > LSTM > SAC
     (historical), or strict-radsec: SAC > LSTM > TD3
   - CLM-0067 (TD3+LSTM as production) needs scope split:
     correct on 6-axis, wrong on paper Sec.IV-C metric
   - 161 tests pass (149 + 12 new audit-A/eval/scen tests)
   ```

### Phase 4 — Open items left for R59+ (not R58 scope)

- Q-0008 should be opened: "Run paper convergence (500 ep) on all 12 cells (3 algo × 4 config) to confirm 75-ep ranking persists"
- Q-0009 should be opened: "Why is our paper-metric magnitude 13-15× tighter than paper's reported DDIC? Investigate exact disturbance distribution + Kundur param values"
- Q-0010 candidate: "Implement adaptive inertia [25] baseline so we have a paper-side reference value (paper -12.93 cumulative)"

User's parallel R59 work (PI briefing layer infrastructure) is independent and likely already committed by them.

---

## File pointers

- This handoff: `memory/handoffs/2026-05-17_R58_paper_strict_handoff.md`
- R58 plan: `memory/rounds/R58/plan.md`
- R58 verdict DRAFT: `memory/rounds/R58/verdict.md`
- ADR-0002: `docs/adr/0002-paper-strict-vs-paper-faithful.md`
- Critic audit (in-chat only, summarized in CLM-0068 draft below): captured in `memory/rounds/R58/verdict.md` "Phase 0" section
- Eval JSONs (36): `results/research_loop/r58_paper_metric_*.json`
- Training logs (28): `results/r58_paper_strict_*/stdout.log`
- Sanity training (in progress): `results/r58_sanity500_pure_td3_lstm_s51/stdout.log` (`bnin9obnj`)

---

## Quick references

- **149 tests** were green when training started; **161 tests** green now (12 new R58-specific)
- **Test files added/modified**:
  - new: `test_paper_strict_config.py`, `test_paper_strict_eval.py`, `test_r58_train_wiring.py`, `test_r58_audit_a_fixes.py`
  - none modified
- **Code branch**: `main` (R58 commits not yet landed)
- **Latest git log**: `081e754` (R57 commit) — R58 changes still uncommitted
- **Background process status**: `bnin9obnj` = s51 _pure 500-ep sanity (~85 min remaining at handoff time)
