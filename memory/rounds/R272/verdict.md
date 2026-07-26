# R272 verdict — active-power proxy implemented, formal bank INVALID

**Date**: 2026-07-26
**Status**: CLOSED-INVALID
**Type**: sealed real-ANDES active-power authority feasibility gate
**Claim**: CLM-0570

## TL;DR

R272 implemented the programme's first explicit, source-hashed,
energy-feasible active-power channel: four independent grid-following ESD1
devices alongside the unchanged four PV+GENCLS VSG proxies, with M/D fixed at
200/100.  The corrected sealed batch retained all 40 formal rows.

The registered result is **INVALID**, not AUTHORITY-PARTIAL or a performance
failure.  The identical-DAE zero-support baseline completed only 17/20
scenarios, while droop+PI completed 13/20.  Because the baseline itself is
numerically infeasible on the formal bank, the 13 complete pairs cannot
support a bank-level active-power authority claim.  Their large frequency
improvements are diagnostic only, and Gate 2 remains closed.

## Frozen experiment and provenance

- Hybrid authority proxy: unchanged PV+GENCLS VSG layer plus independent GFL
  ESD1 at Bus12, Bus16, Bus14, and Bus15; this is not unified GFM-BESS.
- Four 36 MVA / 28 MWh equivalents: 144 MVA / 112 MWh total.
- SOC initial/min/max: 0.50/0.20/0.80.
- Per-device system-base power limit: 0.36 pu; external ramp:
  0.36 system pu/s; active-priority converter capability projection.
- Charge/discharge efficiency:
  `sqrt(0.97)=0.9848857802`; active-current lag 0.02 s.
- VSG action frozen to zero normalized action, exactly M=200 and D=100.
- Primary controller: equal-sharing physical-60-Hz droop+PI,
  Kp=2.0 and Ki=0.2 system-pu units per device.
- Formal bank: 20 no-anchor scenarios, seed 2026072601; 300 steps/60 s;
  final window 50 steps/10 s.
- Paired bootstrap: 10,000 shared-index resamples, seed 2026072602.
- Real simulator: WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0.

Immutable corrected-seal hashes:

| Artifact | SHA-256 |
|---|---|
| actuator contract | `220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c` |
| scenario bank | `184d1233b0e75482b444e513857c3d28dc7d7af2f7fe9d0a59ba09da146901c7` |
| v2 formal seal | `28fa96b182c7905cc2b704b44ff2b9f056781fefb5769b797ffad55127ce9119` |
| formal summary | `7ab0240386983154859420f0915ded3203301336d69523e3e225ada3ec2c3f85` |
| formal provenance | `2fb4960bb613662307453a56e05aeb6871e6be4585cae4621d2a25ed07fe99ec` |

All 40 recomputed trace hashes match the summary.  The manifest's plan hash
refers to the sealed pre-result plan; the lifecycle frontmatter was changed
only after the formal summary and provenance were written.

## Test-first corrections before the final seal

R272's public seams were implemented test-first.

1. A real-ANDES equivalence test showed that merely adding zero-command ESD1
   states changes the DAE trajectory: the first VSG frequency differed from
   original V4 by up to about 2.16e-4 Hz.  The primary baseline was therefore
   prospectively corrected to the same storage DAE with zero active-power
   support; original V4 became a structural secondary only.
2. The first formal seal produced retained 6/300-step failures on its first
   pair.  A red analyser test then showed that the sealed analyser incorrectly
   required every row to complete, contrary to the registered
   failure-retention rule.  The stopped seal and two failure traces were
   preserved.  The v2 analyser keeps every row in failure/constraint
   denominators and computes endpoints only on an explicitly named
   complete-pair subset.

No capacity, placement, controller gain, horizon, seed, threshold, or formal
bank changed between the stopped first seal and v2.

## Formal completion and failure result

| Controller | complete | TDS failures | complete pairs | constraint violations |
|---|---:|---:|---:|---:|
| zero support | 17/20 | 3/20 | 13 | 0 |
| droop+PI | 13/20 | 7/20 | 13 | 0 |

Shared failures:

| Scenario | Disturbance | zero-support steps | droop+PI steps |
|---|---|---:|---:|
| random_00 | PQ_Bus14 +2.2000 pu | 6/300 | 6/300 |
| random_05 | PQ_Bus14 +2.2772 pu | 6/300 | 6/300 |
| random_10 | PQ_Bus14 +2.1841 pu | 6/300 | 6/300 |

Additional candidate failures:

| Scenario | Disturbance | zero support | droop+PI |
|---|---|---:|---:|
| random_04 | PQ_Bus15 -2.9683 pu | 300/300 | 48/300 |
| random_14 | PQ_0 -2.8214 pu | 300/300 | 108/300 |
| random_15 | PQ_0 -2.8450 pu | 300/300 | 108/300 |
| random_16 | PQ_Bus14 -2.1415 pu | 300/300 | 279/300 |

The three baseline failures make the registered comparison INVALID.  The four
additional PI failures independently fail the candidate-completion guard.
Failed rows were not retried, replaced, or removed.

## Complete-pair diagnostics — not confirmatory

The following evidence uses only the 13 scenarios where both arms completed.
It is reported because the plan required measured endpoints, but the INVALID
classification blocks a performance claim.

| Endpoint | zero support mean | droop+PI mean | effect | paired-bootstrap 95% interval |
|---|---:|---:|---:|---:|
| physical VSG-mean IAE (Hz s) | 2.51174295 | 1.05247396 | -58.097864% | [-58.682127%, -57.126866%] |
| final-10-s common absolute mean (Hz) | 0.0389715417 | 0.0096914845 | -75.131894% | [-77.379006%, -71.222455%] |
| normalized synchronization loss | — | — | -0.764531% | diagnostic |
| worst-bus peak absolute frequency | — | — | -20.504098% | diagnostic |
| max sampled RoCoF | — | — | -2.836679% | diagnostic |

Negative values are improvements.  All 13 complete pairs improved both
co-primary endpoints, but complete-case conditioning cannot repair the
baseline's 3/20 numerical infeasibility or the candidate's higher failure
rate.

## Physical-contract audit

The raw traces independently satisfy the implemented projection contract:

- SOC across every retained sample: `[0.4813797103, 0.5148229077]`, within
  the frozen `[0.20, 0.80]` bounds.
- Maximum absolute requested, projected-commanded, and actual storage power:
  `0.36017770`, `0.35823473`, and `0.35796878` system pu respectively.
  Requests beyond instantaneous capability were projected rather than
  silently applied.
- 484 non-empty capability/saturation reason entries were retained.
- Registered SOC, energy, power, ramp, and converter-capability violations:
  zero.
- M and D had exactly one value each across all traces: 200 and 100.
- Development validity remained 4/4 full trajectories, zero TDS failures,
  zero registered violations, with PI SOC in
  `[0.4853192692, 0.5112170186]`.

This validates the bounded interface and accounting on the samples that
exist.  It does not make the formal disturbance/DAE contract numerically
feasible.

## Outcome against the pre-registered gate

| Gate | Result |
|---|---|
| bank/contract/manifest/source/trace hashes match | PASS |
| all 20 zero-support baselines complete | FAIL — 17/20 |
| candidate completion no worse than baseline | FAIL — 13/20 versus 17/20 |
| zero registered physical-contract violations | PASS |
| both co-primary effects ≤ -2% with upper interval < 0 | NOT ELIGIBLE — complete-pair diagnostic only |
| synchronization/peak/RoCoF no worse than +5% | FAIL-CLOSED — baseline numerical infeasibility blocks formal safety effects |
| Gate 2 may open | NO |

Classification: **INVALID**.

Q-0034 is closed-partial by CLM-0570: the exact frozen contract produced a
large mechanism signal on its feasible subset, but no valid bank-level answer.
This is not AUTHORITY-PARTIAL under the performance gate and is not evidence
for learned control.

## Feasibility decision

- **Physical active-power interface:** implemented and auditable.  Units,
  power projection, energy/SOC accounting, M/D isolation, trace retention,
  and provenance checks passed.
- **R272 formal bank-level authority experiment:** infeasible as registered,
  because the matched zero-support plant itself fails on 15% of the bank.
- **Frozen droop+PI candidate:** not robust on the same bank; its 35% failure
  rate is worse than the baseline's 15%.
- **Complete-pair mechanism signal:** strong enough to justify a narrowly
  scoped correctness diagnosis, but not another controller or learning round.
- **Next research boundary:** Q-0035 must distinguish disturbance-envelope
  infeasibility from a zero-command ESD1 DAE confound using original V4 versus
  identical-DAE zero support only.  No PI endpoint may select the repair.

## Assets

- `memory/rounds/R272/plan.md`
- `memory/rounds/R272/actuator_contract.json`
- `memory/rounds/R272/scenario_bank.json`
- `memory/rounds/R272/formal_seal_v2.json`
- `src/andes_rl_kundur/control/active_power.py`
- `src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py`
- `src/andes_rl_kundur/evaluation/active_power_authority.py`
- `scripts/eval_active_power_authority.py`
- `tests/test_energy_feasible_bess.py`
- `tests/test_energy_feasible_storage_env.py`
- `tests/test_active_power_authority.py`
- `results/r272_active_power_authority_v2/active_power_authority_summary.json`
- `results/r272_active_power_authority_v2/active_power_authority_summary.md`
- `results/r272_active_power_authority_v2/provenance.json`
- `memory/claims/CLM-0570.md`

## Verification

- corrected sealed formal execution: 40/40 rows retained, one real-ANDES
  process, no residual evaluate process;
- formal bank, contract, and v2 manifest hashes matched before analysis;
- independent trace-hash audit: 0/40 mismatches;
- focused WSL active-power tests: 17 passed;
- focused WSL tests including the existing V4 regression: 19 passed;
- Ruff on all R272 source, runner, and test files: passed;
- full Windows suite before formal execution: 397 passed, 5 skipped,
  1 expected xfail;
- dual-metric lint, repository validation, render, and final selector are run
  again after lifecycle closure.

## Questions opened (this round)

- Q-0035 — determine whether R272's formal TDS failures come from the
  disturbance envelope, the zero-support ESD1 DAE, or both.

## Questions closed (this round)

- Q-0034 — closed-partial by CLM-0570.  The frozen contract is INVALID at
  bank level; complete-pair improvements remain diagnostic and Gate 2 stays
  closed.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了什么**：先把真正有功功率、额定能量、SOC、效率、ramp、lag 和变流器能力都落进了可审计的 ANDES 接口，再用 20 个冻结场景跑完零支持与 droop+PI 的 40 条正式轨迹。M/D 全程固定，没有训练网络，也没有碰拓扑或论文。

**一句话结果**：正式结论是 **INVALID**。零支持基线自己就有 3/20 条 TDS 失败，PI 有 7/20 条失败，所以不能说这个控制器在整个 bank 上通过了有功权威门槛，更不能进入 Gate 2。

**最重要的信号**：在双方都跑完的 13 对里，物理 IAE 改善 58.10%，最后 10 秒共同频差改善 75.13%，而且 SOC、功率、能量和能力约束没有违规。这说明显式有功通道很可能有真正的恢复作用；但删掉失败样本后再宣布成功会破坏 sealed evaluation，所以这些数字只能作为机制诊断。

**为什么计划框架有用**：它提前冻结了“失败行必须保留”和“基线失败即 INVALID”。因此中途看到很强的频率改善时，我们没有改 bank、补跑失败样本或把完整子集包装成正结论。测试优先还抓到了两个结构问题：零指令 ESD1 会改变 DAE，以及旧 analyser 无法保留失败行。

**下一步只做什么**：Q-0035 只比较原始 V4 与相同 DAE 的零支持系统，判断失败究竟来自过大的扰动包络，还是 ESD1 初始化/DAE 混杂。这个问题没回答前，不再跑 PI，不调容量或增益，也不启动 RL/GNN。
