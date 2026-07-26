# R277 verdict — a material zero-sum inertia learning margin exists

**Date**: 2026-07-26
**Status**: CLOSED-POSITIVE — LEARNING-GAP-PRESENT
**Type**: prospectively sealed real-ANDES learning-margin diagnosis
**Claim**: CLM-0595

## TL;DR

R277 is `LEARNING-GAP-PRESENT`. A deliberately optimistic, outcome-seeing
oracle chose among six prospectively frozen zero-sum inertia schedules and
the strong R274+R275 classical reference on the same 24-case bank. It selected
a non-baseline action in 18/24 scenarios, reduced normalized synchronization
loss by 25.642428% and first-3-s inter-area IAE by 19.655067%, and passed every
uncertainty, common-mode, restoration, tail, action, storage, completion, and
provenance guard.

This proves that a disturbance-adaptive differential control target exists.
It does not prove that MARL can learn or deploy the oracle. One narrow,
structured residual-policy experiment is now justified; HAWE and lucky-seed
claims are not.

## Methodology

R277 reused the 24 immutable R275 combined traces as the baseline. On each
matching scenario it evaluated six signed Hadamard directions spanning the
complete three-dimensional zero-sum subspace of four VSG inertia actions.
For the first 3 s, two VSGs used physical inertia 500 and two used 200 while
fleet-mean inertia stayed exactly 350; all four then returned to 200.
Damping action remained zero.

The development oracle saw the complete trajectory and could select only a
candidate that improved both differential endpoints scenario by scenario,
kept RoCoF and peak within +5%, kept full-horizon and final-window restoration
within +2%, and passed completion, exact-action, storage, SOC, power, energy,
and constraint checks. It otherwise fell back to the baseline. This is an
attainable-margin upper bound, not a deployable controller.

All thresholds, directions, amplitude, duration, bank, solver, endpoints,
bootstrap settings, and stopping rules were frozen by formal-seal SHA-256
`85754c16f6f3befc767dd059deb405500c683601f50c3cd331197324284fb590`
before the first of 144 candidate trajectories.

## Results

All six candidates completed 24/24 scenarios for 300/300 steps: 144/144 new
candidate trajectories, zero TDS failures, zero missing tasks, and empty
stderr logs. The oracle retained the R275 baseline in 6 scenarios, selected
`h1_neg` in 12, `h1_pos` in 5, and `h3_pos` in 1.

| Registered endpoint | R275 reference mean | Outcome oracle mean | Effect | Paired-bootstrap 95% interval |
|---|---:|---:|---:|---:|
| normalized synchronization loss (Hz²) | 3.007308e-05 | 2.236161e-05 | **-25.642428%** | [-32.969540%, -18.889390%] |
| first-3-s inter-area IAE (Hz s) | 0.059127155 | 0.047505673 | **-19.655067%** | [-26.520699%, -12.460633%] |
| max sampled RoCoF (Hz/s) | 0.100509055 | 0.089030704 | -11.420215% | [-16.079888%, -6.696243%] |
| worst-bus peak (Hz) | 0.075207271 | 0.071110884 | -5.446796% | [-8.426575%, -2.626226%] |
| VSG-mean IAE (Hz s) | 0.967095671 | 0.967547607 | +0.046731% | [+0.024111%, +0.072916%] |
| final-10-s common absolute error (Hz) | 0.008319568 | 0.008309525 | -0.120722% | [-0.188501%, -0.062319%] |

Both primary differential effects exceeded the registered 2% materiality
threshold and their paired 95% upper bounds were below zero. All upper-tail
audits passed. Storage command L1, TV, charge energy, and discharge energy
changed by +0.120764%, -4.973834%, +0.068343%, and +0.158415%, respectively.
Candidate SOC stayed within `[0.486062008, 0.511456799]`; maximum commanded
and actual storage power stayed below 0.314 system pu; no saturation reason
or constraint violation occurred.

## Integrity-only analysis repair

The first sealed analysis attempt stopped before writing any endpoint output
because the R275-derived trace summariser did not expose
`bess_saturation_reason_count`, although every immutable trace contained the
underlying per-step `bess_saturation_reasons`. A focused regression test
reproduced the deterministic `KeyError`.

The sealed learning-gap module was restored byte-for-byte to its registered
SHA-256
`c1b38815881919b3e75da42cd19674cb9a30880619adb9e19c6a6fed37965ea2`.
An explicit compatibility wrapper then counted non-empty saturation reasons
already present in each trace and supplied only that missing summary field.
It changed no trace, endpoint, threshold, guard, bootstrap, candidate,
selection rule, or experimental result. The repair sources and final output
hashes are independently recorded in
`results/r277_learning_gap_oracle/analysis_integrity_repair.json`.

## Interpretation and ICEMS boundary

The result changes the answer from “MARL may be unnecessary” to “a narrow
adaptive target exists.” The target is not general VSG parameter tuning. It
is specifically disturbance-dependent redistribution of a fixed fleet-mean
inertia budget around the already validated common fast pulse, while the
validated slow droop+PI/storage layer remains frozen.

For the ICEMS paper, the existing title may remain provisionally because a
genuine MARL experiment is now scientifically motivated. The minimum honest
method is one memoryless, parameter-shared policy with a hard zero-sum output
projection and bounded slew. It must be compared directly with R274+R275 on
unseen scenarios and all seeds must be reported. R277 is an oracle upper
bound and must not be presented as learned-controller performance.

HAWE remains outside the main contribution. The paper does not need topology
generalisation, HIL, EMT, cross-simulator transfer, a formal stability proof,
an algorithm zoo, or a large hyperparameter sweep for the ICEMS target.

## Assets and provenance

- `memory/rounds/R277/plan.md`
- `memory/rounds/R277/formal_seal.json`
- `results/r277_learning_gap_oracle/formal_traces/`
- `results/r277_learning_gap_oracle/learning_gap_oracle_summary.json`
- `results/r277_learning_gap_oracle/learning_gap_oracle_summary.md`
- `results/r277_learning_gap_oracle/provenance.json`
- `results/r277_learning_gap_oracle/analysis_integrity_repair.json`
- `src/andes_rl_kundur/evaluation/learning_gap_oracle.py`
- `src/andes_rl_kundur/evaluation/learning_gap_analysis_repair.py`
- `scripts/eval_learning_gap_oracle.py`
- `scripts/analyse_r277_with_saturation_repair.py`
- `tests/test_learning_gap_oracle.py`
- `memory/claims/CLM-0595.md`

The final summary SHA-256 is
`6bbc2dea133c2b089964167072bab06ffe77e5b9c05594389e665d2b5e9290b3`;
the provenance SHA-256 is
`ca4ddd20e266b653f5924eb24c98c443d61c9b913265dcaaf4957c95e51e5368`;
the integrity-repair audit SHA-256 is
`58b3b508fa156e4bd46dd5758be839e35878ce0c60740a7b1f3928b84b97c9de`.

## Verification

- Formal candidate trajectories: 144/144 complete, 300/300 steps, zero TDS
  failures; all eight shard stderr logs are empty.
- Immutable R275 baseline pairs: 24/24 verified by recorded trace hash.
- Oracle: 18/24 non-baseline selections; both primary differential endpoints
  clear materiality and paired uncertainty.
- Completion, exact zero-sum/fleet-mean action, common-mode, restoration,
  storage, SOC, power, energy, tail, and provenance guards: all pass.
- Focused Windows R277 tests after the integrity repair: 12 passed, 1 WSL-only
  skipped.
- Final Windows suite: 434 passed, 9 skipped, 1 expected xfail.
- Final WSL R277 suite including the real-ANDES smoke: 13 passed.
- Ruff on the sealed module, repair module, repair runner, and R277 tests:
  passed.
- Dual-metric lint passed. Ledger validation passed with 23 warnings:
  22 historical missing-path warnings and one expected heuristic warning that
  Q-0038 remains open after the prerequisite CLM-0595; no errors.
- Rendering completed. The selector reported no active round; its legacy
  TPWRS programme had no currently eligible question, while the PI's explicit
  ICEMS redirection is recorded separately in the execution plan.

## Questions opened (this round)

- None.

## Questions closed (this round)

- Q-0040 — closed-positive by CLM-0595 with the registered
  `LEARNING-GAP-PRESENT` classification.

## Questions advanced (this round, status unchanged)

- Q-0038 — the prerequisite margin now exists. Proceed only with one
  memoryless, parameter-shared, hard-projected zero-sum inertia residual
  trained against the unchanged R274+R275 classical reference.

## 给 PI 的话

**这轮干了什么**：没有训练 AI，而是先做了一个对 MARL 极其有利的上限测试。对同一套 24 个场景，允许一个“看完结果才选动作”的理想裁判，在六种零和惯量分配和现有最强经典控制之间逐场景挑选；144 条新仿真全部完成。

**结果（一句话）**：结论是 **LEARNING-GAP-PRESENT**——理想裁判在 18/24 个场景选择了差异化惯量分配，同步损失降低 25.64%，前三秒区域间振荡累积量降低 19.66%，所有安全、储能、尾部风险和统计门槛都通过。

**意外**：真正有研究价值的不是 HAWE 加权，也不是某个幸运种子，而是一个很窄、很清楚的物理问题：总惯量不变时，应该根据扰动把惯量在四台 VSG 之间怎么重新分配。这个问题确实存在，而且简单固定规则还没有完全吃掉它。

**我默认下一步做**：按你刚改的目标，只冲 ICEMS，不再做 TPWRS 那套大工程。题目先不改；只训练一个共享、无 LSTM、硬零和投影、限幅限速的 MARL 残差，跑 3 个种子，直接对比现有最强经典控制。HAWE 从主方法删除，只保留一句负面消融。

**你想插一脚就说**：你不需要发邮件，也暂时不需要改标题；下一步只要看这个简单 MARL 能不能在未见场景上兑现一部分 25.64%/19.66% 的上限。兑现不了，我会明确告诉你标题最后的 MARL 必须改，绝不再拿幸运种子包装。
