# R273 verdict — shared disturbance-envelope failure, ESD1-only confound rejected

**Date**: 2026-07-26
**Status**: CLOSED-POSITIVE
**Type**: sealed real-ANDES completion/solver attribution and conditional boundary map
**Claim**: CLM-0575

## TL;DR

R273 answers Q-0035 with the registered classification
**ENVELOPE-INFEASIBLE**.  Original V4 and the identical storage DAE with
exactly zero active-power support failed the same three large positive Bus14
cases and completed the same four signed/location controls.  The added four
ESD1 devices change DAE dimensions and failure time slightly, but they do not
create the registered failures by themselves.

A separately sealed four-iteration, completion-only bisection bounded the
common positive-Bus14 transition between **1.530775 pu complete** and
**1.6396625 pu failed** for the frozen model, solver, timing, seed, and
M/D=200/100 contract.  This is a local scenario-generation boundary, not a
universal voltage-stability limit and not active-power-controller evidence.
R272 remains INVALID and Gate 2 remains closed.

R273 also implements a prospective feasibility-screen contract.  It refuses
to freeze after controller traces exist, retains every excluded scenario,
reports the excluded fraction, and stratifies by disturbance location and
sign.  It was not used to retroactively repair R272.

## Frozen attribution experiment

The primary experiment compared only:

1. original `AndesMultiVSGEnvV4`; and
2. `AndesMultiVSGEnvV4Storage` with zero requested BESS power at every step.

Both arms used seed 42, 300 steps/60 seconds, the same ANDES TDS configuration,
the R272 disturbance definitions, and exactly M=200/D=100.  No droop+PI,
candidate performance endpoint, capacity/gain/placement change, learning, or
topology experiment entered the attribution.

The seven registered cases were:

- shared R272 failures: `random_00` Bus14 +2.2000 pu, `random_05`
  Bus14 +2.2772 pu, and `random_10` Bus14 +2.1841 pu;
- signed/location controls: `random_01` Bus14 +0.4419 pu, `random_11`
  Bus14 -0.6458 pu, `random_16` Bus14 -2.1415 pu, and `random_09`
  Bus15 +2.1086 pu.

Immutable primary hashes:

| Artifact | SHA-256 |
|---|---|
| R272 scenario bank | `184d1233b0e75482b444e513857c3d28dc7d7af2f7fe9d0a59ba09da146901c7` |
| active-power contract | `220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c` |
| R273 core seal | `565aca7b4d602fbd74b0f1879d512760cab74f0795df028c270075b36dd10f9b` |
| core summary | `2f465d07ae40e7e81f2d74a410f70baa879e2821184fca6e91547c7073ddd7ea` |
| core provenance | `717045fae8396c1d9785024c2eee28fe723885536f691d9bf1ab3d9ffc27294f` |

## Primary completion/solver evidence

| Scenario | Disturbance | original V4 | storage zero | result |
|---|---|---:|---:|---|
| `random_00` | Bus14 +2.2000 | 6/300, t=1.8887 s | 6/300, t=1.8462 s | shared failure |
| `random_05` | Bus14 +2.2772 | 6/300, t=1.8225 s | 6/300, t=1.7829 s | shared failure |
| `random_10` | Bus14 +2.1841 | 7/300, t=1.9045 s | 6/300, t=1.8602 s | shared failure |
| `random_01` | Bus14 +0.4419 | 300/300 | 300/300 | shared completion |
| `random_11` | Bus14 -0.6458 | 300/300 | 300/300 | shared completion |
| `random_16` | Bus14 -2.1415 | 300/300 | 300/300 | shared completion |
| `random_09` | Bus15 +2.1086 | 300/300 | 300/300 | shared completion |

Every failed row reported “Time step reduced to zero. Convergence is not
likely.” and retained the simulator termination time.  Every completed row
reached simulator time 60.5 s.

The DAE structures are observably different:

- original V4: `n=102`, `m=284`, 0 ESD1, 8 PV;
- storage zero: `n=122`, `m=376`, 4 ESD1, 12 PV.

Nevertheless, their seven-case completion vectors are identical.  The three
registered failures are therefore not attributable to the presence of
zero-command ESD1 alone.  The slight arm-to-arm failure-time differences show
that ESD1 changes the trajectory, but not the registered completion class.

Independent audit of all 14 core traces found:

- 0 trace-hash mismatches;
- one identical TDS configuration across every row;
- successful setup, finite initialization, and converged power flow in every
  row;
- M/D exactly 200/100;
- storage requested, commanded, and actual active power exactly zero;
- storage SOC exactly 0.5 and zero constraint violations.

Primary classification: **ENVELOPE-INFEASIBLE**.

## Conditional completion boundary

The plan allowed a secondary positive-Bus14 boundary map only after the
primary classification supported the envelope hypothesis.  The secondary
seal references the immutable core summary and uses no controller endpoint.

| Iteration | tested magnitude | original V4 | storage zero | bracket decision |
|---:|---:|---:|---:|---|
| 1 | 1.3130000 pu | 300/300 complete | 300/300 complete | raise lower bound |
| 2 | 1.7485500 pu | 10/300 failed | 9/300 failed | lower upper bound |
| 3 | 1.5307750 pu | 300/300 complete | 300/300 complete | raise lower bound |
| 4 | 1.6396625 pu | 15/300 failed | 12/300 failed | lower upper bound |

Final common conditional bracket:

- lower complete: `1.5307750` pu;
- upper failed: `1.6396625` pu;
- bracket width: `0.1088875` pu.

Immutable boundary hashes:

| Artifact | SHA-256 |
|---|---|
| boundary seal | `11ced378359fcee464f744cf35e25376801192799fa7fdbd2e8b3e779d718366` |
| boundary summary | `1646df23ec0e0d1d0eb7afa7d322dd6750f37872e329ad3509b760690d664de8` |
| boundary provenance | `79dbdeced2ff0c564ae5b87af36d9819b50f81d7f1fc53a74997f0ba9e25a5ab` |

All 8 boundary trace hashes match.  The TDS configuration remained identical,
M/D remained 200/100, and the storage-zero power/SOC audit remained exact.
No plant-mismatch stop was triggered.

Both seals contain the hash of the pre-result plan.  The plan's lifecycle
frontmatter was changed from active to completed only after the immutable core
and boundary summaries/provenance were written.

This bracket applies only to a positive step at PQ_Bus14 under this exact
model, initialization, solver, horizon, and completion definition.  The
opposite-sign Bus14 control and positive Bus15 control show that absolute
magnitude alone is not a valid universal screen.  A future bank must therefore
retain sign/location stratification and cannot simply clip every disturbance
at 1.530775 pu.

## Test-first optimization

R273 added two reusable, independently tested contracts:

1. `advance_common_completion_bracket` moves a bisection bound only when every
   registered plant agrees and returns `PLANT-MISMATCH` without moving either
   bound otherwise.
2. `build_feasibility_screen_contract` requires a complete plant matrix and
   trace hashes, rejects post-controller freezing, keeps every scenario in an
   explicit decision ledger, duplicates every rejected case into retained
   exclusions, reports the excluded fraction, and stratifies by
   location/sign.

The red tests initially failed because the feasibility-screen module did not
exist; the implementation then made the public contract pass on Windows and
WSL.  This optimization improves research validity and automation.  It does
not make the extreme R272 cases converge and does not silently remove them.

## Outcome against the pre-registered gate

| Gate | Result |
|---|---|
| three registered failures reproduced under both plants | PASS |
| four signed/location controls complete under both plants | PASS |
| completion vectors match | PASS |
| initialization, solver, M/D, zero-support, and provenance audits | PASS |
| ESD1-only failure hypothesis | REJECTED |
| disturbance-envelope hypothesis | SUPPORTED |
| primary classification | **ENVELOPE-INFEASIBLE** |
| R272 retroactively repaired | NO |
| controller-performance or Gate-2 claim | NO |

Q-0035 is closed-positive by CLM-0575.  “Positive” means that the attribution
question was answered, not that active-power authority passed.

Q-0036 is opened prospectively: generate a new signed, multi-location bank,
freeze zero-support feasibility and a nontriviality distribution before any
controller trace, then reuse the exact R272 controller/actuator contract once.
That work belongs to a separate round and seal.

## Assets

- `memory/rounds/R273/plan.md`
- `memory/rounds/R273/core_seal.json`
- `memory/rounds/R273/boundary_seal.json`
- `src/andes_rl_kundur/evaluation/storage_dae_feasibility.py`
- `src/andes_rl_kundur/evaluation/feasibility_screen.py`
- `scripts/diagnose_storage_dae_feasibility.py`
- `scripts/map_storage_dae_feasibility_boundary.py`
- `tests/test_storage_dae_diagnostics.py`
- `tests/test_storage_dae_feasibility.py`
- `results/r273_storage_dae_feasibility/storage_dae_feasibility_summary.json`
- `results/r273_storage_dae_feasibility/storage_dae_feasibility_summary.md`
- `results/r273_storage_dae_feasibility/provenance.json`
- `results/r273_storage_dae_feasibility/boundary_summary.json`
- `results/r273_storage_dae_feasibility/boundary_summary.md`
- `results/r273_storage_dae_feasibility/boundary_provenance.json`
- `memory/claims/CLM-0575.md`
- `memory/questions/Q-0035.md`
- `memory/questions/Q-0036.md`

## Verification

- core execution: 14/14 immutable rows retained, 0 trace-hash mismatches;
- boundary execution: 8/8 immutable rows retained, 0 trace-hash mismatches;
- no residual R273 evaluation process;
- focused diagnostics on Windows and WSL: 8 passed on each platform;
- full Windows suite: 405 passed, 6 skipped, 1 expected xfail;
- focused real-ANDES WSL suite including the V4 1e-9 regression: 19 passed;
- Ruff on all R273 source, runners, and tests: passed;
- dual-metric lint, repository validation, rendering, and final selector are
  rerun after lifecycle closure.

## Questions opened (this round)

- Q-0036 — can the frozen active-power controller be tested validly on a new,
  nontrivial signed/multi-location bank whose zero-support feasibility is
  frozen before controller evaluation?

## Questions closed (this round)

- Q-0035 — closed-positive by CLM-0575.  R272's registered baseline failures
  are shared envelope failures, not zero-command ESD1-only failures.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了啥**：没有再跑 PI、没有调容量或增益，也没有训练网络。我把 R272 的三条失败和四条正负号/位置对照，分别放回原始 V4 与“带 ESD1 但功率始终为零”的环境里，只看能否跑满、求解器为什么停、DAE 初值和物理约束是否一致；随后按预先写好的规则做了四轮边界二分。

**结果（一句话）**：正式结论是 **ENVELOPE-INFEASIBLE**——三条大正向 Bus14 扰动在两种环境里都失败，四条对照在两种环境里都完成，所以问题主要在扰动包络，不是“多了零指令 ESD1 就必然失败”。

**最关键的数**：14 条核心轨迹和 8 条边界轨迹哈希全部匹配。Bus14 正向步进在 `1.530775 pu` 时两边都能跑满 60 秒，在 `1.6396625 pu` 时两边都失败，区间宽 `0.1088875 pu`。储能请求、命令、实际功率全是 0，SOC 恒为 0.5，M/D 恒为 200/100。

**这不说明什么**：这个数不是通用电压稳定极限，也不能拿来证明 PI 好。负向 Bus14 的 2.1415 pu 和正向 Bus15 的 2.1086 pu 都能完成，说明位置和符号很重要；简单把所有扰动截断到 1.53 pu 会制造一个偏置、过于容易的 bank。

**做了什么优化**：新增了一个测试优先的可行性筛选契约。以后必须先让零支持系统跑完筛选并封印，所有被排除的失败仍保留、统计排除比例并按位置/符号分层；只要控制器轨迹已经出现，就拒绝再修改筛选。这能防止“看完 PI 结果再删难样本”。

**下一步只做什么**：Q-0036 应单独生成一个新的、有正负号和多位置、难度分布提前冻结的 bank；先做零支持可行性筛选，再一次性复用 R272 已冻结的 droop+PI 合同。只有这个新门槛有效且为正，才有资格讨论 Gate 2、残差学习或拓扑泛化。
