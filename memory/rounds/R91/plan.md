---
round: R91
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R91 plan — D3 obs sufficiency on cached SOTA trajectory

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: [[CLM-0160]] (R84-W3-traj on-manifold pass) refuted the
critic-side mechanism for the R57-R82 91-round plateau. PI 简报推荐
PRIORITY 1 = D3 obs sufficiency (can paper-faithful 7-dim obs + LSTM h
carry enough information for an ε-optimal policy?). R83-W3
(area_mean_freq) closed RED (geo=0.328 vs baseline 0.391, -16%);
R83-W4 (all 3 aug combined) running. PI: "继续研究". R91 = the
D3 axis the R84 plan originally specified as W4 — never run.
**Parent**: R84 W3-traj / CLM-0160 (R85+ pivot recommendation).

## TL;DR

D3 = mutual-information lower bound for obs → optimal value & action.
Capture one full SOTA rollout on LS1+LS2 with full obs vector + per-step
reward + LSTM h_actor, then fit 4 MLP regressors offline:

- **R1**: obs → return_γ (discounted return, multiple γ)
- **R2**: obs → action* (memoryless BC ceiling)
- **R3**: (obs, h_actor) → action* (BC with LSTM h, full-info ceiling)
- **R4**: obs → next_obs (forward model sufficiency)

Gate criteria:

| Outcome | R85+ implication |
|---|---|
| R1 ≥ 0.5 AND R2 ≥ 0.7 | obs is sufficient → plateau is **policy class** (CTDE / attention msg) or **env floor** (D4). R83 obs aug 失败有 root cause |
| R1 ≥ 0.5 AND R2 < 0.7 AND R3 - R2 ≥ 0.3 | **h_actor is essential** — memoryless can't recover SOTA action even with obs. LSTM is critical, R83 obs aug 弱效果是因为信息已经在 h 里, 加 obs 是冗余 |
| R1 < 0.5 | obs **insufficient for value** — V*(s) can't be reduced to obs. R83 obs aug 路径 motivated, 但需要找到 right features (D4 reward shape + power-system audit) |
| R4 < 0.5 | obs **insufficient for dynamics** — Markovian assumption breaks. R85 走 stacked-frame / explicit-memory aug |

## Wave 1 (W1) — Rollout capture + 4-regressor fit

Inputs:
- R72_w4 SOTA ckpt: `results/r72_w4_lstm_tau001_warmup5_s54/agent_*_best.pt`
- ANDES eval × 2 scenarios × 50 steps × 4 agents = 400 (obs, action, reward, h) tuples
- 1 short ANDES eval (~30s wall, 1 WSL slot in `andes_venv`)

Offline analysis:
- Split per-agent samples 80/20 train/test
- 2-layer MLP regressor, hidden 64, Adam lr 1e-3, 200 epochs
- Report R² on test set per (agent, scenario, γ)

Output: `results/r91_d3_obs_sufficiency/{summary.json, per_agent_r2.csv}`

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `scripts/r91_d3_obs_sufficiency.py`, `results/r91_d3_obs_sufficiency/`,
`memory/rounds/R91/{plan.md, verdict.md}`, 1 CLM (numbered ≥ 0161 to dodge
parallel-session reservations).

## Cross-references

- [[CLM-0160]] (R85+ priority pivot from critic-side to D3/D4/reward-shape)
- [[CLM-0144]] (R57-R82 91-round algo plateau evidence)
- R83 plan / R83-W3 verdict-pending (geo=0.328 RED, area_mean_freq alone insufficient)
- R85 plan (classical PI/Droop baseline — different session, no conflict)
- R86 plan (cross-ckpt synthetic — different framing, R91 cites their data only
  for completeness)
- R87 plan (phase-resolved on-manifold critic — companion to R91; R87 deepens
  CLM-0160's critic picture, R91 opens the obs picture)
- Q-0014 (algo backlog — R91 result either closes negatively "obs insufficient"
  or stays open with policy-class focus)

## Risks

1. **ANDES 3-slot saturation**: R83-W4 + R85-classical occupy 2/3 slots.
   R91 ANDES occupancy is brief (~30s) but pushes to 3/3 momentarily.
   Mitigation: capture only what 1 deterministic eval gives, no retry loops.
2. **N=400 may be small for MLP regression**: 4 agents × 80 train samples each
   could overfit. Mitigation: dropout 0.1 + report training R² alongside test R²;
   if gap > 0.2 flag overfitting in verdict.
3. **γ choice arbitrary**: trying γ ∈ {0.0, 0.9, 0.99, 1.0} covers
   instantaneous, paper γ=0.99 (V4Config.gamma), and undiscounted limits.
