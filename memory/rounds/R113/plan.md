---
round: R113
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R113 plan — Toggler-Line_8 ablation (Q-0025 A1, paper-critical disturbance audit)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: R110/CLM-0194 audit 发现 V4 env ships with hidden Toggler trip
on Line_8 at t=2s. **Every R57-R85 / R100 / R103 LS1/LS2 scenario 实际是
compound disturbance** (paper load step at t=0.5s + ANDES default line trip
at t=2s). Paper Sec.IV-C 是 single-event claim. 不 ablate Toggler 之前,
所有 plateau 0.391 / classical droop 0.197 / R100/R103 in-flight training
结果都建立在 paper-mismatched scenario 上.
**Parent**: CLM-0194 (R110 file-inspection audit) + Q-0025 (opens this test).

## TL;DR

跑 Q-0025 A1: V4 env × zero-action × LS1+LS2 × {Toggler u=1 default, u=0 disabled}
= 4 ANDES TDS eval. ~10 min wall. 比较 max_df + cum_rf + 11-axis geo. 三个
regimes (CLM-0194 Q-0025 框架):

| max_df drop | 结论 | 后续 |
|---|---|---|
| **≥30%** | Toggler is dominant residual cause; R57-R85 paper-mismatch | R114+ re-baseline 所有 SOTA on Toggler-removed V4 |
| 10-30% | Toggler + F2 load topology 一起 close residual | partial paper rewrite |
| <10% | Toggler minor; F2/F3 (CLM-0173) dominant | Q-0025 closed-negative |

**两侧都 paper-publishable**:
- 大 effect → paper Sec.IV-C 数据需 re-eval, R72_w4 SOTA 0.391 数字可能改;
  R110 finding 是关键修正
- 小 effect → R110 是 false alarm, paper claim 已 robust 至复合扰动, 文章
  立论更强

## R110 audit + R113 falsification target

R110 (CLM-0194) 是 zero-compute file inspection. R113 是 first quantitative
test. Audit 发现 Toggler ships in `andes/cases/kundur/kundur_full.xlsx`,
V4 env._build_system() 没 mutation 它. 实际仿真:

```
t=0.0   TDS warmup starts
t=0.5   load step (paper-intended LS1/LS2)
t=0.7   agent control begins (or zero_action for baseline)
t=2.0   *** Line_8 trip (Toggler.u=1 ANDES default, UNINTENDED) ***
t=10.5  STEPS_PER_EPISODE=50 end
```

R113 disables Toggler at the reset boundary (`env.ss.Toggler.u.v[:] = 0`)
post-`_build_system`. Result tells us how much of R57-R85 was actually
training/eval ON the compound vs paper-intended scenario.

## Implementation

`scripts/r113_toggler_ablation.py`:

1. Reuse `paper_path` style: V4Config.paper_faithful + LS1/LS2 SCENARIOS
2. For each scenario × each toggler state (default=u=1, ablated=u=0):
   - construct env
   - env.reset(delta_u=...) — runs `_build_system` + warmup-to-t=0.5 + apply disturbance
   - **R113 patch**: `env.ss.Toggler.u.v[:] = float(toggle_value)` 在 step
     loop 开始前 (post-reset, pre-step). 因 reset 跑到 t=0.5, Toggler t=2
     还没 fire, set u=0 在 t<2 触发前阻止.
   - run zero_action step loop until done or STEPS=150
   - record max_df, cum_rf, freq_hz traces
3. Score with `evaluation.summary.score_trace_files`: 4 files (u=1 LS1, u=1 LS2,
   u=0 LS1, u=0 LS2) → 2 geo numbers + max_df diffs.
4. Output `results/r113_toggler_ablation/`:
   - `toggler_u{0,1}_load_step_{1,2}.json` traces
   - `no_control_load_step_{1,2}.json` references (axis-8)
   - `r113_summary.json` 含 max_df drop + geo + decision rule

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | (this) plan.md | done |
| **W2** | `scripts/r113_toggler_ablation.py` | ~20 min code |
| **W3** | WSL launch + monitor | ~10 min ANDES |
| **W4** | Verdict + CLM(s) + close-or-keep Q-0025 | ~25 min |

Total wall ~1 h, **1 ANDES WSL slot used** (跟 R102 + R106 共 3 process,
on CLAUDE.md max 3 limit).

## 资源冲突 gate

- R102 (magnitude PI eval, ~11 min in): completes before R113 finishes
- R106 (env floor eval, ~10 min in): may overlap most of R113 wall
- R109 (warmh0 agent, CLOSED-POSITIVE, no WSL)
- R110 (audit, DONE, no WSL)
- R111/R112 (reserved by other sessions, empty plan dirs)
- Output namespace: `scripts/r113_toggler_ablation.py` + `results/r113_toggler_ablation/`

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py /
任何 R57+ ckpt / 任何 existing test.

新建: `scripts/r113_toggler_ablation.py` + `results/r113_toggler_ablation/` +
`memory/rounds/R113/{plan,verdict}.md` + 1-2 CLM.

**Patch principle**: 我**不**在 V4 env 加 toggler_remove field. R113 只是
*forensic*, 不是 production change. 若 max_df drop ≥30%, R114 才提议 V4Config
新 field + ADR + paper re-baseline 决定.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 V4 代码改动)
- R57+ SOTA ckpt 完全不 load 不 write
- R102/R106/R98 prototype 全部 unaffected

## Gate

Pass = R113 跑完出 max_df drop 数字; Q-0025 ≥30% / 10-30% / <10% 三选一记录决策.
Fail = ANDES TDS crash 或 patch 没 disable Toggler (verify 通过 `env.ss.Toggler.u.v`
读 0 in post-patch logging).

## Cross-references

- CLM-0194 (R110 audit, R113 quantitative follow-up)
- Q-0025 (opens this test, R113 closes)
- R09 §2 Finding 2 (2× max_df residual) — R113 may explain
- R89/CLM-0173 (F1-F5 audit) — Toggler 是 F-missing-from-list, R113 closes gap
- R85 best droop K=2 geo=0.197 — 若 max_df drop ≥30%, droop ceiling 也会变
- CLM-0144 (91 round algo plateau) — 若 toggler 显著, plateau 可能 phantom
- paper Sec.IV-C — single-event claim, R113 量化是否需要修正
