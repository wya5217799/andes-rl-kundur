# Handoff — Post R55 arc summary (R43 → R55, end-of-session 2026-05-17)

**Branch**: `main` (all 14 commits this arc pushed local; remote sync TBD by user)
**Last claim**: CLM-0062 (R55 windowed anti-smoothness fails)
**Test suite**: 60 passing
**`memory/STATE.md`**: auto-rendered, 62 claims, R55 current
**validate.py**: exit 0, 44 warnings (all pre-existing)

---

## Where we ended

Two distinct phases this session:

**Phase 1 (R43 → R48): positive — built the production triangle**
1. R43 (1623a69) — H3 triple-confirmed; first non-lucky > 0.30 (HAWE-3 norm = 0.310)
2. R44 (158bc09) — HAWE single-best cap; Q-0001 closed-negative
3. R47 (fe7effb) — HAWE robust to aggregation; 200ep plateau (R50 fail in waiting)
4. R48 (655c7f0) — **hidden=64 +21 % over default; CLM-0055 supersedes CLM-0047**
   - new production single-seed: TD3 norm 75ep h=64 mean **0.334**
   - new production ensemble: HAWE h=64 median **0.351**
   - strongest single non-lucky actor: s51 h=64 **0.365**

**Phase 2 (R49 → R55): six negatives — temporal-flatness hexagon**

| Round | commit | Lever attacked | mean | Δ vs 0.334 | Distinct sub-mechanism |
|---|---|---|---:|---:|---|
| R49 | 109050f | INCLUDE_OWN_ACTION_OBS=1 (last-action obs) | 0.263 | −21 % | self-reinforcing static loop (CLM-0057) |
| R50 | 7783185 | LAMBDA_SMOOTH=-100 (per-step) | 0.110 | −67 % | exploration-noise hijack (CLM-0058) |
| R51 | bfff893 | --algo sac at h=64 | 0.107 | −68 % | deterministic-eval-setpoint (CLM-0059) |
| R52 | 45c4987 | INCLUDE_TIME_OBS=1 | 0.270 | −19 % | phase info unused (CLM-0060) |
| R54 | b80c67b | --warmstart-shared from s51 | 0.306 | −8 % | uniformity-vs-peak-tracking trade-off (CLM-0061) |
| R55 | 7231b26 | LAMBDA=-100 SMOOTHNESS_WINDOW=10 | 0.110 | −67 % | hijack is W-independent (CLM-0062) |

Codex parallel rounds during this arc: R45 (Q-0001 escalation, mooted by R44),
R46 (architectural deepening Phase A + Q-0004 deferred), R53 (memory hygiene).
None conflict with research findings; some made my workarounds obsolete
(checkpoint_loader auto-detect, V4Config field standardisation).

---

## Production triangle (end-of-R55, stable since R48)

```
                                                paper target 1.0
                                                ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                3× gap (structural)
                                                ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                ─────────────
  0.444 R21 lucky basin SAC entropy lottery     unreproducible
  0.439 HAWE w9802 (ensemble of lucky)          unreproducible
                                                ─────────────
                                                ↑↑↑ structural ceiling ↑↑↑
  0.365 s51 h64 single (strongest non-lucky)    CLM-0054
  0.353 R41-C s52 lucky-tail (200ep phi=0)      historical
  0.351 HAWE h64 median (production ensemble)   CLM-0056
  0.347 HAWE s52-anchored 90% (hybrid)          CLM-0050
  0.334 TD3 norm 75ep h64 3-seed mean           CLM-0055 (production)
                                                ─────────────
  0.310 R43-β HAWE h128 uniform (old ensemble)  CLM-0049
  0.306 R54 warmstart-shared (axis trade-off)   CLM-0061
  0.275 R41-B TD3 norm h128 3-seed (SUPERSEDED) CLM-0047 → 0055
                                                ─────────────
  0.270 R52 INCLUDE_TIME_OBS                    CLM-0060
  0.269 R47-β TD3 norm 200ep h128 (plateau)     CLM-0053
  0.263 R49 R03 obs probe                       CLM-0057
                                                ─────────────
  0.137 SAC multi-seed attractor                R23-R27
  0.117 SAC norm h=128                          CLM-0048
  0.110 R50 / R55 anti-smoothness (W=1, W=10)   CLM-0058/0062
  0.107 R51 SAC h=64                            CLM-0059
                                                ─────────────
  0.101 no_control G4-preserved                 CLM-0051 (Q-0001)
  0.094 no_control G4-zeroed (current ranker)   baseline
```

---

## Structural finding (six-failure hexagon)

After six distinct lever-class attacks, the temporal-flatness bottleneck
is bounded by:

> **Any deterministic-mode policy on V4 + decentralized obs +
> paper-faithful reward converges to static setpoint at eval, INVARIANT
> under: training algorithm (TD3/SAC), obs augmentation (action history,
> phase), per-step reward shaping (anti-smoothness W=1 OR W=10), shared
> initialisation, and capacity (h=32/64/128/256).**

Per-agent action span over 6 s is empirically capped at 9–21 % of
paper's claimed `paper_dH_span=400` / `paper_dD_span=800`. Cross-agent
mean curve span (the actual utilization metric input) is bottlenecked
by the same static-setpoint behaviour.

R54 (warmstart-shared) is the ONLY probe with structurally informative
axis trade-off:
- shared init → uniform actors → settling axis up (+25 %), corr_dD up
  (+0.17 raw)
- uniform actors → can't track per-agent local peak → max_df down
  (−19 %)
- net: −8 % on geo-mean (least-bad of the six failures)

This trade-off implies V4 may have an intrinsic settling-vs-max_df
tension that no decentralized memoryless policy can fully resolve.

---

## What's left (remaining architectural pivots, all expensive)

| Lever | Cost | Mechanism | Confidence |
|---|---|---|---|
| (a) **Deterministic-output smoothness reward** | ~1-2 hr | Compute r_smooth on actor MEAN, not noise-augmented action. Refactor env.step to receive both. Structurally hijack-immune. | **High** |
| (b) **Sparse end-of-episode reward** | ~30 min impl | Reward = std(action over episode) at episode end. Per-step path unchanged. | Medium — TD3 sparse learning unreliable |
| (c) **LSTM recurrent actor** | ~1 day | Hidden state encodes trajectory phase → policy structurally time-varying even at deterministic eval. | **Highest** — only structural fix |
| (d) **True parameter-sharing (SharedTD3Agent)** | ~1-2 hr | One actor weights, all agents call it. Forces coordination structurally. | Medium |
| (e) **Curriculum disturbance magnitude** | ~2-3 hr | Harder disturbances force wider actions; learned policy carries over. | Medium |

Cheapest highest-confidence path: **(a) deterministic-output reward**.
Cleanest theoretical path: **(c) LSTM**.

R55 verdict notes the cheap+medium-cost lever space is now empty —
any further attack requires architectural change.

---

## Code state at end of R55

### V4Config fields (research probes, all default OFF / 0.0 / 1)

| Field | Default | What it does | Tested in |
|---|---|---|---|
| `lambda_smooth` | 0.0 | r_smooth = -λ × Σ((Δa - Δa_ref)/range)² per step | R50 (W=1), R55 (W=10) |
| `include_own_action_obs` | False | Appends last action to obs (OBS_DIM 7→9) | R49 negative |
| `include_time_obs` | False | Appends step_count/STEPS_PER_EPISODE to obs (OBS_DIM 7→8) | R52 negative |
| `smoothness_window` | 1 | Reference action for r_smooth: prev (W=1) or W-steps-old (W>1) | R55 negative |
| `action_penalty_mode` | "physical" | Reward action cost in physical Δ vs normalized [-1,1] | R41-B → production "normalized" |
| `zero_g4_inertia` | True | Paper headline pin (Q-0001 closed-negative R44) | always True |

### Env var shortcuts (research-only, V4Config preferred for permanence)

- `LAMBDA_SMOOTH=N` → cfg.lambda_smooth fallback (R55 fix: cfg only overrides if non-default)
- `INCLUDE_OWN_ACTION_OBS=1` / `INCLUDE_TIME_OBS=1` (mutually exclusive)
- `SMOOTHNESS_WINDOW=N` (N≥1)
- `DISTURB_SCALE=X` (R05 disturbance magnitude calibration)

### Files modified this arc (research-impacting only)

- `src/andes_rl_kundur/env/andes/v4_config.py` — 3 new fields (lambda, time, window)
- `src/andes_rl_kundur/env/andes/base_env.py` — env var read for 3 probes,
  deque init for window, telescoping branch in r_smooth, reset clears
- `src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py` — conditional cfg
  overrides for all 3 probes
- `scripts/train.py` — obs_dim_with_optional_action handles both obs probes
- `scripts/_r51_score_sac_h64.py` — full-diagnostic scoring template
  (mirrored ad-hoc for R52/R54/R55 inline)
- `memory/claims/CLM-{0048..0062}.md` — 15 new claims (incl. CLM-0055 with
  supersedes-CLM-0047 back-edge)
- `memory/rounds/{R43,R44,R47,R48,R49,R50,R51,R52,R54,R55}/{plan,verdict}.md`

### Files Codex added in parallel (infra, helpful)

- `memory/tools/query.py` — tag + best-metric CLI over claim ledger
- `scripts/score_run.py` — consolidated scoring driver
- `src/andes_rl_kundur/agents/checkpoint_loader.py` — auto-detect hidden +
  obs from ckpt (no more inline workarounds for non-default sizes)
- Various V4Config refactor, archive moves, tags backfill

---

## Sanity ladder (run first in next session)

```bash
# 1. Validate memory (~1 s)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python memory/tools/validate.py"
# Expect: OK: 62 claims, 4 questions, ≤44 warnings

# 2. Full pytest (~1.6 min)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python -m pytest tests/"
# Expect: 60 passed

# 3. no_control bit-identical (~1 min)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python scripts/eval_no_control.py"
# Expect: LS1 max_df=0.189, LS2 max_df=0.168

# 4. Reproduce production single-seed best (s51 h=64) (~30 s)
# (No retraining; just reload + eval)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python -c \"
from pathlib import Path; import sys, math, json
sys.path.insert(0, 'src')
from andes_rl_kundur.agents.checkpoint_loader import load_agents
from andes_rl_kundur.evaluation.paper_path import run_scenario, deterministic_actor_action_fn
from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS
agents = load_agents(Path('results/td3_norm_h64_s51'), suffix='best', hidden_sizes=(64,)*4)
afn = deterministic_actor_action_fn(agents)
per = {}
for scen, du in SCENARIOS.items():
    rec = run_scenario(scen, du, action_fn=afn, label='s51_h64_repro', seed=42, steps=150)
    Path(f'results/research_loop/eval_v4_baseline/s51_h64_repro_{scen}.json').write_text(json.dumps(rec))
    ts = evaluate_trace(Path(f'results/research_loop/eval_v4_baseline/s51_h64_repro_{scen}.json'), PAPER[scen], is_ddic=True, label='s51_h64_repro')
    per[scen] = ts.overall
print(f'geo = {math.exp(sum(math.log(max(x,0.01)) for x in per.values())/len(per)):.4f}  (expect 0.3649)')
\""
```

---

## Production training command (canonical, end of R48 → still current)

```bash
/home/wya/andes_venv/bin/python scripts/train.py \
    --algo td3 --normalize-actions \
    --episodes 75 --seed <S> \
    --hidden-size 64 \
    --save-dir results/td3_norm_h64_s<S>
```

3-seed mean 6-axis = **0.334** (range [0.295, 0.365]).
Single-seed s51 = **0.365** (strongest non-lucky in project history).

To get the production ensemble:

```bash
/home/wya/andes_venv/bin/python scripts/eval_ensemble.py \
    --ckpt-dirs results/td3_norm_h64_s49 results/td3_norm_h64_s50 results/td3_norm_h64_s51 \
    --suffixes best best best \
    --agg median \
    --label hawe_h64_median \
    --out-dir results/research_loop/eval_v4_baseline
```

→ 6-axis = **0.351** (best multi-seed reproducible ensemble).

---

## Open questions

- `Q-0001` (R37) — G4 inertia preservation; **closed-negative R44** by CLM-0051
- `Q-0002` (R41 → R43) — SAC norm matches TD3 norm? **closed-negative** by CLM-0048
- `Q-0003` (R41 → R43) — HAWE on TD3 norm > 0.30? **closed-positive** by CLM-0049
- `Q-0004` (R46, Codex) — AndesBaseEnv absorb-into-V4 (paper-faithful test); **OPEN**,
  needs WSL session, full implementation package in `memory/rounds/R46/`

My research raised no new questions worth schema-formalising — the six
negative findings are atomic claims that don't open follow-up uncertainty.

---

## Anti-patterns / gotchas (R43-R55 learnings)

1. **Per-step reward × Gaussian exploration noise = hijack channel.**
   Any `(action_change)²` reward term is dominated by noise variance
   regardless of horizon W. Established by R50 (W=1) and R55 (W=10).

2. **Deterministic eval ≠ stochastic train.** SAC's entropy provides
   exploration variation during training but the eval-mode policy
   mean is just as static as TD3's. Established by R51 (SAC h=64 fails
   identically to SAC h=128).

3. **More obs ≠ better policy.** Adding INCLUDE_OWN_ACTION_OBS made
   things worse (R49 self-reinforcing static loop). Adding
   INCLUDE_TIME_OBS slightly worse (R52, phase info unused).
   omega_dot is ALREADY in obs (R49 audit, base_env.py:470).

4. **U-curve on hidden_size.** V4's obs_dim=7 is small; h=128 default
   is over-parameterised. h=64 is the sweet spot (CLM-0054). h=32 is
   under-parameterised, h=256 over.

5. **HAWE caps at single best actor** (CLM-0050/0052/0056/0062
   re-confirmation). No aggregation strategy (uniform/median/anchored)
   ever exceeds max(individual). The R34 0.439 HAWE w9802 reached its
   score because the lucky-seed R21 was already 0.444.

6. **75 ep is the optimal stop point.** CLM-0046 (phi=0) + CLM-0053
   (normalized) both confirm 200 ep degrades on some seeds without
   raising the mean.

7. **Codex parallel session caveats.** Concurrent commits may sweep
   into my staged area. Always use `git commit -- <paths>` to restrict
   commits. Round numbers may collide (R42, R45, R46, R53 all taken by
   Codex); check `memory/rounds/` before claiming a number.

8. **ANDES is WSL-only.** All training/eval through
   `/home/wya/andes_venv/bin/python`. Max 3 parallel WSL python
   processes (R23 hard limit).

9. **`load_agents` now auto-detects** hidden_size + obs_dim from ckpt
   (Codex commit 1fd945b). No more inline workarounds required for
   non-default architectures.

---

## Recommended next-session decision path

Choice (per user discretion):

**Option A — Accept ceiling, harden for publication later**
- Production triangle 0.334 / 0.351 / 0.365 + 6 ablations is a complete story
- R49-R55 ARE the natural ablation tables
- No further experiments needed

**Option B — Cheapest structural pivot (a)**
- Refactor env.step interface to receive (mean_action, noisy_action)
- Compute r_smooth on mean_action (hijack-immune)
- Train 3 seeds at h=64 norm 75ep λ=-100 with new smoothness
- ~1-2 hr work; medium-high confidence

**Option C — Highest-confidence structural pivot (c)**
- Implement LSTMTD3Agent (~1 day)
- Hidden state encodes trajectory phase → deterministic eval naturally
  time-varying
- Most likely to break the structural ceiling

**Option D — Quick lottery extension**
- Train seeds 52-58 at h=64 norm 75ep (~30 min wall)
- 7 fresh draws; ~20 % chance of a 0.40+ single-seed by R41-C precedent
- Doesn't fix mechanism, just rolls dice

---

## Pointers (most relevant for resume)

- This handoff: `memory/handoffs/2026-05-17_post-R55_arc-summary.md`
- Previous handoff (start of session): `memory/handoffs/2026-05-17_post-R41.md`
- Live oracle: `memory/STATE.md` (regenerated by `memory/tools/render.py`)
- Production training command: this doc § "Production training command"
- Sanity ladder: this doc § "Sanity ladder"
- All R43-R55 plan + verdict: `memory/rounds/R{43,44,47,48,49,50,51,52,54,55}/`
- All CLM-0048..0062: `memory/claims/`
- Codex infra: `scripts/score_run.py`, `memory/tools/query.py`,
  `src/andes_rl_kundur/agents/checkpoint_loader.py`
