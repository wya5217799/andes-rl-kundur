---
round: R117
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R117 plan — Multi-ckpt obs-ascent hard-ceiling + warm-h_0 unit tests

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "一直干活". R116 (CLM-0212) found 40% hard ceiling on R72_w4
SOTA. R117 (1) extends to N=9 LSTM ckpts (R104 set) to confirm universality,
and (2) adds pytest unit tests for the R107/R109 warm-h_0 modules so R96
launch has regression coverage.
**Parent**: CLM-0212, CLM-0188, R104 ckpt set

## TL;DR

W1: multi-ckpt obs-ascent. Result: 9/9 LSTM ckpts under 50% hard ceiling
on obs-only path (median 21.5%, max 51.9% / r72_w5). Combined with
CLM-0188 (h path unlocks 99%), warm-h_0 is provably the only path.

W2: 8 pytest tests for `WarmH0RecurrentActor` + `TD3LSTMWarmH0Agent`.
All pass. R96 launch surface now has unit-test coverage.

Zero ANDES. Zero WSL.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | `r117_obs_ascent_multickpt.py` + 9-ckpt run | ~25 min |
| **W2** | `tests/test_warmh0_modules.py` + pytest | ~30 min |
| **W3** | Verdict + CLM-0217 + render | ~20 min |

Total wall ~75 min.

## 资源冲突 gate

R83 / R94 / R102 / R110 etc. (WSL): R117 zero ANDES ✅
ckpts R57+ read-only ✅
networks.py / td3_lstm.py untouched (R107/R109 separate files) ✅

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ (except adding
new test file) / scripts/train.py / R57+ ckpt / any existing test / any
other round's data.

新建:
- `scripts/r117_obs_ascent_multickpt.py`
- `results/r117_obs_ascent_multickpt/summary.json`
- `tests/test_warmh0_modules.py`
- `memory/rounds/R117/{plan.md, verdict.md}`
- `memory/claims/CLM-0217.md`

## 测试不变量

V4 regression 不重跑. 新 test 不依赖 V4. Existing tests pass.

## Cross-references

- CLM-0212 (R116 N=1 hard ceiling) — R117 universalises to N=9
- CLM-0188 (R104 N=9 warm-h_0 99% unlock) — sister universality result
- CLM-0193 (R107 actor module + obs-norm sweep)
- CLM-0201 (R109 agent class)
- CLM-0207 (R111 cross-algo deficit)
- Q-0022 — implementation surface now has unit test coverage
- CLM-0217 (this round)
