---
round: R109
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R109 plan — TD3LSTMWarmH0Agent code drop-in (R96 prep)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "一直干活". R107 (CLM-0193) shipped the actor module
`WarmH0RecurrentActor` but not the agent integration. R109 adds the
agent class as a separate file so R96 launch only needs 2 × 5-line
edits to train.py + checkpoint_loader.py.

## TL;DR

New file `src/andes_rl_kundur/agents/td3_lstm_warmh0.py::
TD3LSTMWarmH0Agent` extending `TD3LSTMAgent`. 4 override methods. Smoke
test passes. Zero lines changed in existing files.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | `td3_lstm_warmh0.py` + smoke test | ~30 min |
| **W2** | Verdict + CLM-0194 + render | ~20 min |

Total wall ~50 min.

## 资源冲突 gate

R83 / R87 / R94 in-flight training: zero impact ✅ (no existing file modified)
WSL: zero ✅
Other concurrent windows (R100-R108): no overlap ✅

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/td3_lstm.py
(base class extended via subclass, not modified) / agents/networks.py /
agents/networks_warmh0.py (R107 product) / scripts/train.py /
checkpoint_loader.py / R57+ ckpt / any test.

新建:
- `src/andes_rl_kundur/agents/td3_lstm_warmh0.py`
- `memory/rounds/R109/{plan.md, verdict.md}`
- `memory/claims/CLM-0194.md`

## 测试不变量

V4 regression 不重跑. TD3LSTMAgent (base class) 行为不变.

## Cross-references

- CLM-0193 (R107 actor module) — direct parent
- CLM-0188 (R104 universalisation) — feasibility grandparent
- CLM-0183 (R99 N=1 feasibility)
- Q-0022 — implementation surface now complete
- CLM-0194 (this round)
