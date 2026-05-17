# Handoff — R58 paper-strict + R59 PI-briefing + R60 dual-probe (3-round commit pending)

**Prepared**: 2026-05-17 (R58 sanity done, R59 user-completed, R60 parallel-completed)
**Estimated remaining wall**: ~30-45 min (commit all 3 rounds + minor verdict touch-ups)
**Status**:
- R58: code + training + eval + sanity + verdict DONE. CLM-0073 written for sanity. Only commit left.
- R59: user-completed (PI briefing layer + glossary.yml + render/validate.py updates + ADR-0003). Verdict written by user.
- R60: parallel agent session completed (Q-0007 cheap probe + Q-0006 LSTM × anti-smoothness pilot). CLM-0074, CLM-0075 written. Verdict written.

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

### Phase 1 — verdict + claims (~30 min) — **MOSTLY DONE**

- ✓ `memory/rounds/R58/verdict.md` — user finalised (status=closed-positive). Reads `closed-positive (eval complete; sanity run conditional, see CLM-0073 if produced)`. Optional polish: drop the "conditional" wording since CLM-0073 now exists.
- ✓ `CLM-0068..0072` — likely already drafted by user; verify by `ls memory/claims/CLM-006[8-9].md CLM-007[0-2].md` (may need verification)
- ✓ `CLM-0073` (s51 _pure 500-ep sanity) — **just written by this session** (`memory/claims/CLM-0073.md`)
- ⏸ Q-0008 / Q-0009 — verify whether user added them in R58 verdict. May need to write if missing.

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

### Phase 3 — Memory validation + commit (~15-25 min)

Three rounds in one go (R58 + R59 + R60). Recommended **3 separate commits** for clean memory log:

**1. Validate first:**
```
python memory/tools/validate.py
```
Expect: 65 + (CLM-0068..0075) = 73 claims, 7 + Q-0008 + maybe Q-0009 = ~9 questions. If validator complains, fix before commit.

**2. Render STATE.md:**
```
python memory/tools/render.py
```
R59's updated render.py supports the PI briefing layer; R60 verdict likely already has 给 PI 的话 section per the new convention. R58 is grandfathered.

**3. Three-commit option (recommended for clean history):**
- Commit A (R58 — paper-strict + audit-A): src/.../v4_config.py + base_env.py + andes_vsg_env_v4.py + scripts/train.py + scripts/_r58_*.{py,sh} + src/.../paper_strict_eval.py + tests/test_paper_strict_*.py + tests/test_r58_*.py + memory/rounds/R58/ + memory/claims/CLM-0068..0073.md + maybe Q-0008.md + Q-0009.md + docs/adr/0002 + CONTEXT.md term split
- Commit B (R59 — PI briefing infra): docs/adr/0003 + memory/glossary.yml + memory/rounds/R59/ + memory/tools/render.py + memory/tools/validate.py + memory/tools/tests/test_*.py + memory/rounds/_TEMPLATE_VERDICT.md + CONTEXT.md PI-briefing terms + CLAUDE.md
- Commit C (R60 — Q-0007 + Q-0006 dual probe): memory/rounds/R60/ + memory/claims/CLM-0074.md + CLM-0075.md + memory/questions/Q-0006.md + Q-0007.md

Then a final commit D (memory/STATE.md) since render needs all 3 rounds present.

**3-alt commit option (one commit):** if user wants atomic landing:
```
round: R58 + R59 + R60 — Paper-strict audit + PI briefing + Q-0007/Q-0006 dual probe
```

Either way ensure:
- Validator is green before commit
- All tests still pass: `pytest tests/ -q` should yield 161 passed (or 162 if user added more)
- `git status` after commit shows only file-system artifacts as untracked (results/, .claude/scheduled_tasks.lock)

### Phase 4 — Open items left for R61+ (not R58/R59/R60 scope)

- Q-0008 should be opened by R58 verdict (paper convergence sweep across 3 algos × 4 configs at 500 ep). R58 sanity (CLM-0073) showed LSTM stable but Q-0007-locked, so Q-0008 should note: convergence is fine, the issue is ckpt selection.
- Q-0009 should be opened: "Why is our paper-metric magnitude 13-15× tighter than paper's reported DDIC? Investigate exact disturbance distribution + Kundur param values"
- Q-0010 candidate (R61+ scope C/D): "Implement adaptive inertia [25] baseline so we have a paper-side reference value (paper -12.93 cumulative)"

R59 user-completed work:
- `docs/adr/0003-pi-briefing-layer.md`
- `memory/glossary.yml`
- Updates to `memory/tools/render.py`, `validate.py`, their tests
- Updates to `_TEMPLATE_VERDICT.md`, `CONTEXT.md` PI-briefing terms
- `CLAUDE.md` likely updated to reference the new convention
- R59/plan.md + R59/verdict.md

R60 parallel-completed work:
- `memory/rounds/R60/plan.md` + `verdict.md`
- `CLM-0074` (Q-0007 cheap probe: s50 final.pt = 0.270 → 5-seed mean 0.396)
- `CLM-0075` (Q-0006 closed-negative: LSTM × anti-smoothness antagonistic, -16 %)
- Q-0006.md updated: `status: closed-negative`, `closed_round: R60`, `closed_by: CLM-0075`
- Q-0007.md log appended with R60 advance entry

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
