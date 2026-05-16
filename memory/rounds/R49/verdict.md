# R49 verdict — System audit clean + R03 obs probe negative

**Date**: 2026-05-17
**Status**: **COMPLETE**. System health verified, R03 probe tested
and refuted.
**Type**: audit + experiment (negative result)
**Wall**: ~30 min (audit + diagnostic + 3 trainings ~10 min wall in
parallel + scoring)

---

## TL;DR

> **System is healthy**: pytest 60/60 PASS, no-control eval bit-
> identical (LS1=0.189 LS2=0.168), s51 h=64 ckpt reproduces 0.365
> byte-for-byte, ckpt schemas correct, action traces sane. Only
> known gaps: monitor prints "SAC: mean critic_loss" for TD3 runs
> (cosmetic), eval_ddic/eval_ensemble don't expose `--hidden-size`
> (R48 workaround), `checkpoint_loader.load_agents` doesn't read
> instance-level OBS_DIM (R49 workaround).
>
> **Data analysis refined the bottleneck**: action utilization is
> low NOT because actions are tiny (max |dM|=145, |dD|=445 per step)
> NOR because of uncoordinated cross-agent cancellation (corr is
> mixed +0.04 to +0.46) but because **each agent's action is
> temporally flat** — per-agent dM_span over 6s is only 9–21 % of
> paper-claimed 400, dD_span only 11–13 % of 800.
>
> **R49-α refutes the R03 obs hypothesis**. Adding action history
> to observations (INCLUDE_OWN_ACTION_OBS=1) makes things WORSE:
> mean 6-axis = 0.263 vs R48-β baseline 0.334, −21 % drop. The
> deterministic TD3 actor latches onto "copy previous action" as
> a stable point — coordination rises but temporal variation
> drops further. CLM-0057.

---

## Part audit — system health

| Check | Result |
|---|---|
| `pytest tests/` | **60/60 PASS** (1.6 min) |
| `eval_no_control.py` bit-identical | ✓ LS1 max_df=0.189, LS2=0.168 |
| s51 h=64 reproduces R48 number | ✓ geo=0.3649 (R48 reported 0.3649) |
| s51 h=64 ckpt schema | algo='td3' ✓, log_alpha absent ✓, net.0.weight=(64,7) ✓ |
| Action-magnitude in trace | max \|dM\|=145, max \|dD\|=445 (NOT tiny) |
| Memory validator | exit 0, 56 claims, 4 questions, 9 warnings |

Known gaps (all known + intentional):
- `monitor.py` prints "SAC: mean critic_loss" even when --algo td3.
  Cosmetic only — TD3 actually runs.
- `scripts/eval_ddic.py` and `scripts/eval_ensemble.py` don't take
  `--hidden-size` CLI flag. R48-β used inline-Python workaround.
- `checkpoint_loader.load_agents` reads `AndesMultiVSGEnvV4.OBS_DIM`
  (class attr = 7), not the instance attr that
  `INCLUDE_OWN_ACTION_OBS=1` bumps to 9. R49-α used inline-Python
  workaround constructing TD3Agent directly.

None of these affect the published numbers. All deferred to a
future infra round (R50+) when consolidation is worthwhile.

---

## Part diagnostic — what makes utilization low

R48 verdict's interpretation of "low utilization = small actions"
was empirically wrong. Re-running s51 h=64 LS1 and inspecting
the trace:

| metric | s51 h64 LS1 | What it means |
|---|---:|---|
| max |delta_M| (single step) | 145 | individual action **up to 36 % of paper |dM|=400** |
| max |delta_D| (single step) | 445 | individual action **up to 56 % of paper |dD|=800** |
| per-agent dM_span over 6s | 36.8 (avg across 4 agents) | each agent only swings 9.2 % of paper span |
| per-agent dD_span over 6s | 89.0 | 11.1 % of paper |
| cross-agent corr(dM) | +0.40 | partial coordination |
| cross-agent corr(dD) | −0.03 | independent |
| **cross-agent mean dM span (utilization input)** | **33.6** | **8.4 % of paper 400** |
| **cross-agent mean dD span** | **65.1** | **8.1 % of paper 800** |

The `_action_utilization` formula in `paper_grade_axes.py:177` is
`min(1.0, proj_span / paper_span)` where `proj_span = max - min of
cross-agent-mean action curve over the first 6 seconds`. Our actors
push hard (individual peaks > 100 of dM, > 400 of dD) but each
agent settles to a near-constant setpoint very quickly — the
cross-agent average curve barely sweeps over the 6s window.

Pattern: "push briefly at the disturbance, then hold". Paper
benchmark presumably uses agents that traverse a wider time-varying
trajectory (peak action ramping up, then ramping down).

---

## Part α — INCLUDE_OWN_ACTION_OBS probe

If the static-setpoint behaviour stems from the actor lacking
trajectory information, giving it knowledge of its own previous
action should help. The `INCLUDE_OWN_ACTION_OBS` env-var probe
(base_env.py:139-144, flagged in the post-R41 handoff as untested)
appends `(delta_M_prev_i, delta_D_prev_i)` to agent i's observation,
bumping OBS_DIM 7 → 9.

Setup: 3 seeds × 75 ep, `--algo td3 --normalize-actions
--hidden-size 64`, `INCLUDE_OWN_ACTION_OBS=1` set in shell at both
train and eval time. Same seeds as R48-β (49/50/51).

### Results

| seed | LS1 | LS2 | **geo** | dH_util | dD_util | dM_span% | dD_span% | corr_dM | corr_dD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.262 | 0.319 | 0.289 | 0.040 | 0.033 | 10.6 % | 3.4 % | +0.54 | +0.85 |
| 50 | 0.211 | 0.220 | **0.215** | 0.158 | 0.030 | 40.8 % | 3.6 % | +0.39 | +0.47 |
| 51 | 0.278 | 0.292 | 0.285 | 0.023 | 0.039 | 6.5 % | 6.8 % | +0.12 | −0.01 |
| **mean** | — | — | **0.263** | 0.074 | 0.034 | 19 % | 4.6 % | +0.35 | +0.43 |

vs R48-β baseline (mean 0.334, range [0.295, 0.365]):
- **mean: 0.263 vs 0.334 = −21 %**
- All 3 seeds below baseline minimum (0.295)
- dH utilization: 0.074 vs 0.040 — slightly UP (+0.034)
- dD utilization: 0.034 vs 0.100 — DOWN (−0.066)
- per-agent dM_span: 19 % vs 9-21 % — slightly up, mixed
- per-agent dD_span: 4.6 % vs 11-13 % — DOWN (worse)
- cross-agent corr: substantially up (+0.35 vs ~+0.15, and +0.43 vs ~+0.20)

### Implication

The R03 obs probe doesn't help — it actively hurts. The mechanism
is the OPPOSITE of what was hoped:

- With access to `delta_M_prev`, the deterministic TD3 actor learns
  the local stable point "if I just took action X, take action X
  again" — because X was the policy's best estimate last step, and
  no incentive exists to vary it.
- This creates a self-reinforcing loop: action history becomes a
  fixed-point attractor → temporal variation collapses → utilization
  drops further.
- Cross-agent coordination rises because each agent's local history
  is correlated with neighbours' (they all reacted to the same
  disturbance, so their action histories are similar).

The result is a more coordinated, more temporally-static actor pool
— exactly wrong for the utilization axis.

### Conclusion

V4 actor's static-setpoint behaviour is **not** caused by missing
information about its own action history. The bottleneck must lie
elsewhere. CLM-0057 captures this negative finding.

---

## What remains as candidate levers (post-R49)

The "temporal variation" bottleneck is now well-diagnosed and three
hypotheses are remaining:

1. **Reward shaping**: add an explicit reward term for action change
   over time (`+λ × |delta_M[t] - delta_M[t-1]|`). Directly attacks
   the bottleneck. Requires base_env.py reward edit (~30 min impl).
2. **Stochastic policy**: SAC at h=64 with normalized — entropy
   noise might prevent the static-setpoint attractor. But CLM-0048
   showed SAC + normalized at h=128 underperforms TD3 by ≈ 0.18
   (0.117 vs 0.275). May not net positive at h=64 either.
3. **Recurrent policy (LSTM actor)**: gives true memory of the
   trajectory phase. Major architectural change (need new actor
   class, modified training loop). Untested.

Plus the existing levers from previous rounds:
- More seeds at h=64 (lottery for >0.40 single seed) — cheap
- Curriculum on disturbance magnitude — bigger
- PPO algorithm — major

---

## Project-wide 6-axis scoreboard (post-R49)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed (R44) |
| R43-α SAC normalized h=128 | 0.117 | H3 |
| R41-A SAC phi=0 h=128 | 0.117 | |
| R47-β TD3 norm 200 ep h=128 | 0.269 | plateau (CLM-0053) |
| R41-C TD3 phi=0 200 ep 5-seed | 0.268 | |
| R41-B TD3 norm 75 ep h=128 | 0.275 | superseded (CLM-0047) |
| **R49-α TD3 norm h=64 R03 obs** | **0.263** | **R03 obs probe NEGATIVE** |
| R43-β HAWE h=128 uniform | 0.310 | |
| R47-α HAWE top-3 uniform | 0.315 | |
| R44-α HAWE s52-anchored 90% | 0.347 | hybrid |
| **R48-β TD3 norm 75ep h=64** | **0.334** | **current production single-seed (CLM-0055)** |
| **R48-δ HAWE h=64 median** | **0.351** | **current production ensemble (CLM-0056)** |
| R41-C s52 single seed | 0.353 | lucky-tail |
| **R48-β s51 h=64 single** | **0.365** | **strongest single actor (CLM-0054)** |
| R21 lucky basin SAC | 0.444 | |
| HAWE w9802 (R34) | 0.439 | |
| paper target | ~1.00 | unreached |

---

## What R49 establishes

- **System health**: pipeline is correct; R48 numbers reproduce
  byte-for-byte; no silent regressions from Codex's R45+R46+R47
  refactor + hotfix work.
- **Refined bottleneck diagnosis (CLM-0057 context)**: temporal
  action flatness per agent, not action magnitude or cross-agent
  coordination.
- **CLM-0057**: R03 obs probe negative — adding own action history
  to obs creates a self-reinforcing static-setpoint attractor;
  utilization drops, overall 6-axis drops 21 %.

## What R49 does not establish

- Whether reward shaping for temporal action variation helps. R50+.
- Whether SAC at h=64 + normalized escapes the static-setpoint
  attractor (its entropy noise may help where R03 obs failed). R50+.
- Whether recurrent policies (LSTM) help. R50+.

## New claims this round

- `CLM-0057` — R49-α: INCLUDE_OWN_ACTION_OBS probe reduces 6-axis
  21 %, creating self-reinforcing static-setpoint attractor.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)
