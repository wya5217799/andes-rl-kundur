---
round: R107
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R107 plan — Warm-h_0 actor drop-in + obs-magnitude sweep

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "一直干活". After R104 (CLM-0188) universalised Q-0022
architectural feasibility across 9 ckpts, two zero-conflict tasks:
(W1) write drop-in code, (W2) understand if slack is obs-magnitude
dependent.
**Parent**: CLM-0188, CLM-0183, Q-0022

## TL;DR

W1: `src/andes_rl_kundur/agents/networks_warmh0.py` — new class
`WarmH0RecurrentActor` extending RecurrentActor via separate file.
Two MLP heads for (h_0, c_0) from obs. ~4.7K extra params. Unit-tested.
`from_pretrained()` bootstraps a vanilla R57+ ckpt.

W2: R72_w4 SOTA ||obs|| sweep [0.10, 2.00] × 7 norms × 4 agents.
Slack stays constant at +89 pp across the 20× range. LSTM
categorically cannot saturate from (h=c=0) regardless of obs
magnitude. Warm-h_0 short-circuits the 10-step hidden-state
accumulation.

Zero ANDES. Zero WSL. Zero conflict with R83/R85/R87/R91/R94 etc.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | `networks_warmh0.py` + unit test | ~25 min |
| **W2** | `r107_warm_h0_obs_norm_sweep.py` + run | ~20 min |
| **W3** | Verdict + CLM-0193 + render | ~30 min |

Total wall ~75 min.

## 资源冲突 gate

- networks.py 不动: ✅ (separate file). R83/R87/R94 in-flight 训练
  imports `networks.RecurrentActor`, R107 不 break.
- WSL: ✅ zero use
- ckpt R72_w4 read-only: ✅

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/td3_lstm.py /
agents/td3.py / agents/sac.py / agents/networks.py / scripts/train.py /
R57+ ckpt / R83-R106 in-flight data / any test.

新建:
- `src/andes_rl_kundur/agents/networks_warmh0.py`
- `scripts/r107_warm_h0_obs_norm_sweep.py`
- `results/r107_warm_h0_obs_norm_sweep/summary.json`
- `memory/rounds/R107/{plan.md, verdict.md}`
- `memory/claims/CLM-0193.md`

## 测试不变量

V4 regression 不重跑 (R107 不动 env). networks.py unchanged → all
TD3-LSTM ckpts loadable as before.

## Cross-references

- CLM-0188 (R104 9-ckpt universal feasibility) — parent
- CLM-0183 (R99 N=1 feasibility) — grandparent
- CLM-0174 (R95 LSTM ramp-up observation) — mechanism this confirms architectural
- CLM-0175 (R94 prediction) — R107-W2 strengthens it
- Q-0022 — implementation code ready
- CLM-0193 (this round, combines W1 + W2)
