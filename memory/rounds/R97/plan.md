# R97 plan — Cross-ckpt bang-bang policy universalization (CLM-0170 replicate)

**Status**: ACTIVE (W0 script ready, W1 waits ANDES slot)
**Opened**: 2026-05-19
**Driver**: R92 CLM-0170 mechanism finding on **N=1 ckpt** (R72_w4 s54 only). Mirror R86 universalisation pattern (CLM-0149 N=1 → CLM-0155 N=6). Independent verification + paper writeup needs N≥5 ckpts. PI 简报 "继续研究, 只要有价值就干".
**Parent**: R92 + CLM-0170 (bang-bang 256-action quantised, saturation 76%, ΔD lockstep r≈+0.99) + R86 N=6 critic-monotone-Q universalisation pattern

## TL;DR

R92 找到 mechanism candidate "R72_w4 SOTA = bang-bang policy + action saturation"
基于单 ckpt trajectory. R97 cross-ckpt replicate on N=6 ckpts spanning 3 algo
classes (SAC, TD3-LSTM v1/v2 配置) × R58/R68/R69/R72/R73/R75 × multi-seed.
Reuse R92-W1 analysis logic, generate new per_step.json per ckpt via
R84-d2b ANDES rollout protocol. Output: 6-ckpt aggregate of saturation /
boundary-pinning / cross-agent lockstep / specialisation / consistency.

**Pass criteria** (mirror R86 N=6 universalisation gate):
- ≥ 5/6 ckpts saturation_max ≥ 0.50 → CLM-0170 universalised
- ≥ 4/6 ckpts ΔD lockstep |r| ≥ 0.9 → redundant ΔD universalised  
- 1-2/6 ckpts low saturation → partial replication, narrows to specific hyper

## Methodology

### Candidate ckpts (N=6, V4 obs_dim=7 compatible, paper-faithful baseline)

| ID | dir | algo | seed | round | role |
|---|---|---|---|---|---|
| **C1** | `r72_w4_lstm_tau001_warmup5_s54` | TD3-LSTM | 54 | R72 | **R92 baseline (re-run for control)** |
| C2 | `r68_w2_lstm_tau001_s51` | TD3-LSTM | 51 | R68 | Fig 7 canonical (CLM-0123) |
| C3 | `r69_w3_lstm_tau001_warmup20_s50` | TD3-LSTM | 50 | R69 | Numeric SOTA (CLM-0115) |
| C4 | `r73_w3_lstm_tau001_warmup20_s54` | TD3-LSTM | 54 | R73 | Prior single SOTA (CLM-0125) |
| C5 | `r75_w2_lstm_tau001_warmup20_s59` | TD3-LSTM | 59 | R75 | v3.1 SOTA (CLM-0131) |
| C6 | `r58_paper_strict_pure_radsec_sac_s49` | **SAC** | 49 | R58 | Algo class diversity (SAC vs TD3-LSTM 5×) |

5 TD3-LSTM (multi-seed, multi-hyper) + 1 SAC (algo class diversity). R86 same
ckpt pool used (cross-validates with critic-monotone-Q finding lineage).

### Per-ckpt protocol (mirror R84-d2b but no critic Q probes — we only need actions)

For each ckpt × 2 scenarios (LS1, LS2) × 50 steps × 4 agents:
1. `load_agents(ckpt_dir, suffix="best")` — V4 env paper-faithful
2. `env.reset(delta_u=...)` — paper-strict LS1/LS2 anchors
3. Per step: `actor.forward(obs, h_actor) → sota_action`, advance hidden
4. Record `{ckpt_id, scenario, step, agent, sota_action[ΔM, ΔD]}`
5. `env.step(actions)`, no critic probe (saves time vs R84-d2b)
6. → 400 records per ckpt × 6 ckpts = 2400 records total

Wall: ~15-25s per ckpt × 6 = ~2.5 min total. ANDES single-session per WSL
process, sequential.

### Per-ckpt analysis (reuse R92-W1 axes)

For each ckpt's 400 records, compute:
- **Axis A** effort per agent (mean L2, max L2, effort share)
- **Axis B** 4×4 corr matrix per (scen, comp), find max |off-diag|
- **Axis D** specialisation (dM share per agent)
- **Axis E** saturation (|a| > 0.95 frequency)
- **Axis F** cross-scenario consistency

### Cross-ckpt aggregate (R97-W1 new)

| Metric | Calculation | Pass criterion |
|---|---|---|
| `n_ckpts_saturation_high` | Count ckpts with max saturation ≥ 0.50 | ≥ 5/6 → universalised |
| `n_ckpts_lockstep_dD` | Count ckpts with any ΔD pair \|r\| ≥ 0.9 | ≥ 4/6 → ΔD redundancy universalised |
| `n_ckpts_area_corr_signature` | Count ckpts with ag0-ag1 ΔM r > 0.8 AND ag0-ag2 r < -0.8 (Kundur 2-area signature) | ≥ 4/6 → physics signature universalised |
| `median_saturation_across_ckpts` | Median of per-ckpt max_saturation_fraction | informational |
| `median_off_diag_corr` | Median of per-ckpt max\|off-diag\| | informational |

## Wave order

| Wave | Content | Wall |
|---|---|---|
| **W0** | Implement `scripts/r97_w1_cross_ckpt_action_coord.py` (already in this round) | ~30 min code |
| **W1** | Run 6 ckpts × ANDES rollout, save per-ckpt per_step.json + summary | ~3 min wall (waits ANDES slot) |
| **W2** | Cross-ckpt aggregate + viz + 6-panel saturation heatmap | ~5 min |
| **W3** | Verdict + 2 claims (R97 universalisation finding + decision: R94+ widen-bound applies cross-ckpt) | ~15 min |

Sequential, total wall ~50 min including code.

## Resource respect

- R85 droop scan (PID 815) 占 1 slot since 05:45, 持续跑
- R94 W1 (PID 1507) 占 1 slot since 06:07, ~13 min wall
- R97 W1 等 R94 释 slot 再跑, 总 2/3 slot 占用同时
- R97 输出 dir: `results/r97_cross_ckpt_action_coord/` (新 namespace)
- 不动 V4 / V5 / V4Config / paper_grade_axes / agents/ / 任何 SOTA ckpt

## Falsification scenarios

| Outcome | Interpretation |
|---|---|
| **5/6 saturation high + 4/6 ΔD lockstep + 4/6 Kundur signature** | CLM-0170 universalised → R94+ widen-bound is correct R57-R86 plateau fix |
| 3/6 saturation high | partial — bang-bang specific to LSTM tau=0.001 warmup={5,20}, SAC differs |
| ≤ 2/6 saturation high | R92 finding is R72_w4-specific artefact, R94 widen-bound not generalizable |
| SAC ckpt diverges from TD3-LSTM pattern | Algo class matters — narrows scope of CLM-0170 |

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py /
任何 R57+ ckpt / V5 env / R94 working tree / R85 working tree.

新建: `scripts/r97_w1_cross_ckpt_action_coord.py`, `results/r97_cross_ckpt_action_coord/`.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 env 改动)
- R57+ SOTA ckpt **read-only loaded**

## Cross-references

- R92 verdict + [CLM-0170](../../claims/CLM-0170.md) (R72_w4 bang-bang N=1)
- R84-d2b + per_step.json schema (rollout protocol source)
- R86 + [CLM-0155](../../claims/CLM-0155.md) (N=6 universalisation pattern blueprint)
- R94 plan (parallel falsification — widen-bound test, R97 mechanism layer)
