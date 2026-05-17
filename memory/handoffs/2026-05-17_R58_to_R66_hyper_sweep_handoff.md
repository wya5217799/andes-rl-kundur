# Handoff — R58→R66 Hyper Sweep & Paper-Metric SOTA Push

**Prepared**: 2026-05-17 19:34
**Session wall**: ~13 hr (~07:00 → 19:34)
**Rounds completed**: R58, R60, R61, R62, R63, R64, R65 (7 commits)
**R66 status**: in-flight (Q-0010 fix in code, Q-0013 partial)

---

## TL;DR for next session

Project went from "持平 paper DDIC +9pp" (R57 baseline) → **完全碾压 paper DDIC + 30-37pp robust 3-seed mean** across 8 rounds today. Found 4 major optima:

- **lr=3e-3** (paper Table I default 3e-4 was 10× sub-optimal, **CLM-0092**)
- **MAX_GRAD_NORM=0.5** (`sac_base.py` hardcode 1.0 was sub-optimal, **CLM-0087**)
- **batch_size=512** (paper 256 default sub-optimal, **CLM-0088**)
- **N_SUBSTEPS=3** (free 2× faster training, +3.6% paper-metric, **CLM-0086**)

Plus Q-0007 (best-by-eval-score) empirically verified +14-20% lift across SAC and TD3 (**CLM-0080**, **CLM-0093**).

---

## Production candidates (final R65 state)

### Mode paper-metric (V4 historical, paper Sec.IV-C)

**R64 TD3 combo (lr=3e-3) 3-seed**:
- 3-seed best_eval mean = **-0.124** total_cum_rf
- Best single: s51 = **-0.118**
- vs paper DDIC: **84% vs 46.5% improvement-rate = +37.5pp robust**
- Ckpts: `results/r64_w3_td3_combo_lr3e3_s{49,51}/agent_*_best_eval.pt`,
  `results/r64_w2_td3_combo_lr3e3_s50/agent_*_best_eval.pt`
- Reproduce:
  ```
  N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 python scripts/train.py \
    --algo td3 --normalize-actions --episodes 75 --seed <S> \
    --hidden-size 64 --batch-size 512 --eval-every-n-eps 5 \
    --save-dir results/<...>
  ```
- Wall: ~7.5 min per seed

### Mode paper-faithful (paper-strict-radsec)

**R65 W1 SAC combo (lr=3e-3) 3-seed**:
- 3-seed best_eval mean = **-0.194** total_cum_rf
- Best single: s49/s50 = **-0.163** (tied)
- vs paper DDIC: **79.2% vs 46.5% = +32.7pp robust**
- Ckpts: `results/r65_w1_sac_combo_s{49,50,51}/agent_*_best_eval.pt`
- s51 training collapsed mid-run (best.pt = -0.965) but Q-0007 caught earlier peak via `best_eval.pt = -0.255`. **Q-0007 saves the seed**
- Same hyper as Mode paper-metric, only `--algo sac --reward-config paper_strict_pure_radsec`

### Mode 6-axis (V4 paper-faithful + project ranker)

**CLM-0067 unchanged from R57**:
- Single SOTA: R57-α s51 LSTM = **0.543** (`results/td3_lstm_h64_warmup5_s51/`)
- Ensemble SOTA: R57-β HAWE-LSTM top2 = **0.501**
- LSTM does NOT benefit from new hyper (R65 W2 shows -24%, CLM-0099)
- **Use OLD hyper for LSTM training**: default lr (clamped to 1e-4), gc default, bs default, ns=5

---

## Round-by-round commits

| commit | round | headline |
|---|---|---|
| e8427df | R58 | Paper-strict audit + ranking validity (V4 TD3 wins on paper metric) |
| 2752a8f | R60 | S-tier triple-probe (Q-0006 closed-neg, Q-0009 closed-pos, Q-0007 advanced) |
| 1a3a4ad | R61 | Q-0007 full impl + SAC HAWE negative + 5-seed final.pt scan |
| 48c466c | R62 | Q-0007 真重训 + new SOTA TD3 (+24pp vs paper) |
| 6671e8d | R63 | Hyper sweep N_SUBSTEPS / gc / batch — combo 3-seed +29.5pp |
| 6c27ae1 | R64 | lr=3e-3 unlocks new SOTA: 3-seed -0.124 (+37.5pp) |
| 4c5327a | R65 | SAC + new hyper: paper-faithful SOTA -0.194 (+54%) |

7 commits, +5,000 / -500 lines (estimated).

---

## R66 in-flight state (NOT YET COMMITTED)

### Code changes uncommitted

`scripts/train.py` modified with **Q-0010 fix**:
- Eval probe moved from BEFORE `env.close()` to AFTER → eliminates ANDES single-session conflict (per `paper_path.py:148-152` "single-session limit on Windows")
- Added numpy/torch RNG state save+restore around eval probe to prevent training stochastics drift
- 12 regression tests still green (`test_q0007_eval_tracked_best.py` + `test_v4_env_regression.py`)
- Diff at lines ~679-720 in `scripts/train.py`

### Q-0013 ablation findings (LSTM per-axis)

| LSTM config | s51 6-axis | note |
|---|---|---|
| R57-α (original, R56 history) | 0.526 | from CLM-0065 historical |
| R66 W1 N_SUBSTEPS=3 only | 0.437 | -17% |
| R66 W1 MAX_GRAD_NORM=0.5 only | **0.4259** | env var **NOT picked up by LSTM** (LSTM not in _SACBase) — actual config = R57-α default |
| R66 W1 batch_size=512 only | **0.4259** | `--batch-size` flag **ignored by LSTM** (uses hardcoded `lstm_batch_size=32`) — actual = R57-α default |

**KEY DISCOVERY — code drift**: R57-α default (LSTM gc05only AND bs512only both effectively R57-α default with same seed) reproduces today at **0.4259** vs original **0.526** = **-19% drift**.

Causes (suspect):
- Q-0007 code path additions (R61) silently affecting LSTM training even when not invoked
- R63 env var additions (N_SUBSTEPS / MAX_GRAD_NORM) imports adding RNG state shift
- General code accretion (R58→R65)

Q-0013 conclusion: **NONE of the axes (nsub, gc, bs) actually transfer to LSTM** because:
1. gc env var doesn't reach LSTM (architectural — `TD3LSTMAgent` not in `_SACBase`)
2. bs flag ignored by LSTM (hardcoded `lstm_batch_size=32`)
3. nsub=3 alone hurts -17%

R57-α path is the **only** LSTM viable config. Q-0013 closes negative.

### Q-0010 verify training (still running)

`results/r66_w2_lstm_q7_fixed_s51/` — LSTM + Q-0007 with Q-0010 fix applied.
- Started ~19:21
- Expected ~10-15 min wall
- Will tell us if Q-0010 fix (eval probe after env.close + RNG state save) enables LSTM + Q-0007

If result > 0.4259 (today's R57-α reproduction) → Q-0010 fixed, Q-0007 also works for LSTM.
If result ≈ 0.115 (R62 W1 anomaly) → Q-0010 not fully fixed, more debug needed.

---

## Open Questions (5 open, 8 closed)

### Open

- **Q-0004** (R46) — AndesBaseEnv absorb into V4 (architectural cleanup, not perf)
- **Q-0005** (R56) — s50 LSTM collapse root cause (Q-0007 partial answer, full mechanism unresolved)
- **Q-0008** (R58) — 500-ep convergence across 12 cells (1 cell done, others not — paper uses 2000ep)
- **Q-0010** (R62) — LSTM eval probe contamination (R66 fix uncommitted, verification training in progress)
- **Q-0012** (R64) — h=96 marginal 3-seed (noise-level, deferred)
- **Q-0013** (R65) — LSTM per-axis ablation (R66 partial, mostly closes negative due to architectural unreachability)

### Closed in this session

- **Q-0006** (R60) — LSTM + anti-smoothness antagonistic (CLM-0075)
- **Q-0007** (R62) — best-by-eval-score empirically validated (CLM-0080)
- **Q-0009** (R60) — paper-metric scale gap = env scale artifact (CLM-0076)
- **Q-0011** (R65) — SAC h=64 wins under new hyper (CLM-0098)

---

## Three big surprises this session

### Surprise 1 — paper Table I defaults are systematically sub-optimal

- **lr**: paper 3e-4 vs our optimum 3e-3 (10×)
- **batch_size**: paper 256 vs our optimum 512 (2×)
- **MAX_GRAD_NORM**: SAC_base hardcoded 1.0 vs optimum 0.5

Each axis alone gives 6-17% lift. Combined: +37.5pp improvement-rate over paper DDIC.

Mechanism (CLM-0092): paper hyper tuned for their env (action space 20× larger, CLM-0076). Under our env's smaller action space, larger lr compensates.

### Surprise 2 — Q-0007 真救命 in production

R65 W1 s51 SAC trained, best.pt = -0.965 (training collapsed mid-run). But `best_eval.pt` (Q-0007 prospective probe) caught earlier peak at -0.255. **Without Q-0007, this seed would be discarded as garbage**. With Q-0007, it's a usable ckpt.

R64-R65 Q-0007 lift consistently +14-20% across SAC and TD3.

### Surprise 3 — LSTM is hyper-asymmetric from TD3/SAC

- TD3 / SAC: love lr=3e-3, gc=0.5
- LSTM: needs lr=1e-4 (clamp in `train.py:305` verified empirically optimal, CLM-0100)
- BPTT chain through 25-step sequences amplifies lr → instability above 1e-4

CLM-0100: `train.py:305` clamp at 1e-4 is correct, not a bug.

LSTM也 doesn't accept new hyper combo for other reasons (architectural: gc env var doesn't reach LSTM, bs flag ignored).

---

## Untouched scratchpad — R59 work

Codex parallel session work from prior session is still **uncommitted**:
- CLAUDE.md (chat-delivery contract)
- CONTEXT.md (PI briefing + glossary terms)
- memory/glossary.yml
- memory/rounds/R59/
- memory/rounds/_TEMPLATE_VERDICT.md (PI briefing mandatory section)
- memory/tools/render.py + tests/test_render.py (briefing extraction)
- memory/tools/validate.py + tests/test_validate.py (briefing required for R≥59)
- docs/adr/0003-pi-briefing-layer.md

These have been load-bearing throughout the session (render extracts briefing
to STATE.md, validate requires 给 PI 的话 section). They will need to land
eventually but were intentionally kept separate to keep round commits clean.

---

## Outstanding tasks for next session

### Immediate (if continuing R66)

1. **Wait for Q-0010 verify training** (`results/r66_w2_lstm_q7_fixed_s51/`):
   - Eval suffix=best, suffix=best_eval
   - Compare to R57-α 0.526 baseline AND today's drifted 0.4259
   - If > 0.4259 → Q-0010 fix works; consider 3-seed scan
   - If < 0.4259 → more debug needed

2. **Commit R66**: write verdict + CLM-0102 (Q-0010 fix), CLM-0103
   (Q-0013 closes negative), CLM-0104 (code drift discovery 0.526 → 0.4259).
   Close Q-0010 (positive if fix works) and Q-0013 (negative).

### Medium-priority

3. **Code drift investigation**: R57-α s51 reproduces at 0.4259 today vs
   0.526 historical. R63-R65 code additions caused -19% drift. Bisect to
   find which commit (e8427df R58? 2752a8f R60? 1a3a4ad R61?). Maybe just
   document and update CLM-0067 with new R57-α reproduction number.

4. **R59 commit**: land the PI briefing infrastructure that's been carrying
   the entire session. Now would be a good consolidation moment.

5. **Paper draft**: 4 tables ready (TD3 SOTA, SAC SOTA, lr sweep U-curve,
   hyper ablation matrix). Section IV-C objective comparison is ready.

### Low-priority

6. **Q-0008 500-ep convergence** on optimal hyper combo. Single cell already
   shows N_SUBSTEPS=3 enables paper-aligned 500-ep training at ~4-min/ep =
   ~30 min wall. Paper baseline 2000 ep would be ~2 hr.

7. **Action space scale fix** (CLM-0076): 20× scale gap is the root cause of
   paper-metric absolute-number gap. Expanding action space to paper levels
   risks training instability (R02-R10 history) but would enable
   apples-to-apples paper-table reporting.

8. **Q-0004 AndesBaseEnv absorb into V4** (R46 carry-over, architectural).

---

## File pointers

- This handoff: `memory/handoffs/2026-05-17_R58_to_R66_hyper_sweep_handoff.md`
- Previous handoff: `memory/handoffs/2026-05-17_R58_paper_strict_handoff.md` (consumed at session start)
- Production ckpts: see Mode tables above
- All round plans + verdicts: `memory/rounds/R58/` through `memory/rounds/R65/`
- 32 new claims this session: CLM-0068 through CLM-0101
- 6 new questions: Q-0008 through Q-0013
- Memory state: 101 claims, 13 questions (5 open, 8 closed), 37 warnings
  (run `python memory/tools/validate.py --fix` to verify after R66 commit)

---

## Quick references

- **Current branch**: `main`
- **Latest commit**: `4c5327a` (R65)
- **R66 in code, uncommitted**: `scripts/train.py` Q-0010 fix
- **Background process**: Q-0010 verify training (LSTM s51 + Q-0007 with fix)
  at `results/r66_w2_lstm_q7_fixed_s51/`. Started 19:21, ETA 19:33 + eval.
- **Test status**: 12 regression tests green after Q-0010 fix
- **160 total tests** (before R66 Q-0010 fix; unchanged after)
- **Total wall this session**: ~13 hr (07:00 → 19:34)

---

## Hyper combo cheat sheet

For **paper-metric / paper-faithful** training (TD3 or SAC):
```bash
N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 \
  python scripts/train.py --algo {td3,sac} --normalize-actions \
    --episodes 75 --seed <S> --hidden-size 64 --batch-size 512 \
    --eval-every-n-eps 5 [--reward-config paper_strict_pure_radsec for SAC] \
    --save-dir results/<...>
```
Wall: ~7.5 min/seed for TD3, ~8 min for SAC. Eval suffix: `best_eval`.

For **6-axis / LSTM** training (R57-α canonical):
```bash
# No env vars, default lr clamped to 1e-4 in train.py:305
python scripts/train.py --algo td3_lstm --normalize-actions \
  --episodes 75 --seed <S> --hidden-size 64 --lstm-lr-warmup-eps 5 \
  --save-dir results/<...>
```
Wall: ~12 min/seed. Eval suffix: `best`. **DO NOT add new hyper combo to LSTM**.

For **eval**:
```bash
# Paper-metric (paper_strict_pure_radsec config, 20-scen test set)
python scripts/_r58_paper_strict_eval.py \
  --ckpt-dirs results/<...> --suffix best_eval

# 6-axis (project ranker, LS1+LS2 anchors)
python scripts/score_run.py --label <...> \
  --ckpt-dirs results/<...> --suffix best
```
