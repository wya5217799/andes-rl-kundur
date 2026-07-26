# R274 verdict — prospective active-power authority confirmed

**Date**: 2026-07-26
**Status**: COMPLETE — AUTHORITY-POSITIVE
**Type**: prospectively screened sealed real-ANDES active-power authority gate
**Claim**: CLM-0580

## TL;DR

R274 prospectively generated a signed, four-location, three-severity 24-case
bank, ran completion-only zero-support screening before any controller trace,
and retained all 24 cases with zero exclusions.  A second immutable seal then
applied the unchanged R272 droop+PI storage controller once per case.

Both arms completed 24/24 trajectories.  Droop+PI reduced physical VSG-mean
IAE by 58.629118% and final-window common absolute frequency by 77.290429%;
both paired-bootstrap 95% intervals excluded zero and all 24 cases improved
both endpoints.  Every provenance, completion, safety, action, SOC, power,
energy, M/D, and capability guard passed.  Classification:
**AUTHORITY-POSITIVE**.

## Prospective bank and seals

- Candidate seed: `2026072603`; 24 cases; four disturbance locations; positive
  and negative signs; 8 moderate, 8 strong, and 8 edge cases.
- Generated/included mean absolute magnitude: `1.0709625` system pu; maximum:
  `1.4922` system pu.
- Zero-support screen: `24/24` complete for `300/300` steps; `0` exclusions;
  every location/sign stratum retained `3` cases.
- Controller traces at screen freeze: `0`; controller performance endpoints
  inspected during screening: `false`.
- Candidate bank SHA-256:
  `c99ca5d17b040333b0f848372918e8eb1abcb0bf46fcdebebc2ccaa86feb4193`.
- Candidate seal SHA-256:
  `77409394e1e64b51025e524bfdf5123aadee51de25f5383eadfc6a2081527709`.
- Screen summary / contract / provenance SHA-256:
  `502a74621f84978509c7504ca32be042344e29ebd550cab5a89cd91c46f0ab65`,
  `f20814908d60305706ca5bb4547a0625e8a0e3edfdbf16c88d49e050a65675da`,
  and `61f9adb61db57dfe204d6f6111deb8389d44c562bfd4fcacee81407d0cfa0054`.
- Formal bank / formal seal SHA-256:
  `9d028e8a0e990fbea6585c674b471dba4d41ea27c1e0b7ecb5d8389092b31f44`
  and `efba41ede1d748171ad62c31bbbe0bc62dffcbedcfd7d458b505df95e97132e8`.
- Frozen R272 actuator contract SHA-256:
  `220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c`.

## Formal result

| Controller | complete | failures | paired endpoints | violations |
|---|---:|---:|---:|---:|
| zero support | 24/24 | 0 | 24 | 0 |
| droop+PI | 24/24 | 0 | 24 | 0 |

| Physical endpoint | zero support | droop+PI | effect | paired-bootstrap 95% interval |
|---|---:|---:|---:|---:|
| VSG-mean IAE (Hz s) | 2.342384355 | 0.969065074 | -58.629118% | [-58.673610%, -58.581130%] |
| final-window common abs. mean (Hz) | 0.0364421214 | 0.00827584943 | -77.290429% | [-77.359432%, -77.218843%] |
| terminal common abs. frequency (Hz) | 0.0364358750 | 0.00748770635 | -79.449632% | [-79.515961%, -79.379802%] |
| worst-bus peak abs. frequency (Hz) | 0.104918859 | 0.0845759426 | -19.389189% | [-22.767419%, -15.783750%] |
| max sampled RoCoF (Hz/s) | 0.143414058 | 0.140324089 | -2.154579% | [-3.738207%, -0.336342%] |
| normalized synchronization loss | 3.20621e-5 | 3.14211e-5 | -1.999288% | [-2.970547%, -1.070239%] |

Negative effects are improvements.  Both co-primary endpoints and worst-bus
peak improved in `24/24` pairs; RoCoF improved in `18/24`; synchronization
loss improved in `23/24`.  All registered safety effects remained better than
the frozen +5% guard.

## Stratification and tail risk

- Mean per-location IAE effects range from `-58.5483%` to `-58.6685%`;
  final-window effects range from `-77.2053%` to `-77.3837%`.
- Negative/positive IAE effects are `-58.5950%` / `-58.6220%`; final-window
  effects are `-77.3965%` / `-77.1805%`.
- Moderate/strong/edge IAE effects are `-58.5308%`, `-58.5910%`, and
  `-58.7036%`; final-window effects are `-77.1965%`, `-77.2943%`, and
  `-77.3747%`.
- Upper-tail CVaR90 VSG-mean IAE changed from `3.460042149` to
  `1.428556337` Hz s; final-window CVaR90 changed from `0.053783600` to
  `0.012200066` Hz.

No location, sign, severity tier, or co-primary pair reverses the mechanism
signal.

## Physical-contract audit

- Droop+PI SOC stayed within `[0.485955719, 0.511540063]`, inside the frozen
  `[0.20, 0.80]` bounds.
- Maximum absolute requested, commanded, and actual storage powers were
  `0.314191840`, `0.314191840`, and `0.314192113` system pu, below the
  `0.36`-pu contract limit.
- Saturation reasons and registered constraint violations: `0`.
- VSG M/D had exactly one value each across all traces: `200` and `100`;
  normalized VSG M/D action remained exactly zero.
- Mean charge/discharge energy was `0.425006` / `0.605377` MWh total; mean
  storage command L1 was `9.259337` device-pu-s and saturation fraction was
  zero.
- Independent recomputation found no missing or mismatched screen/formal trace
  hashes; summary and provenance hashes match their recorded values.

## Test-first correction before sealing

R274 added five prospective-screen unit tests before candidate generation.  A
red test exposed that the first assessment implementation could overwrite and
accept an `original_v4` row as if it were `storage_zero`; the implementation
was corrected to reject wrong-plant evidence before either immutable seal was
created.  Full and focused regression suites passed before the first screen.

## Outcome and boundary

All frozen materiality, uncertainty, completion, provenance, safety, and
physical-contract gates pass.  Q-0036 closes positive by CLM-0580 and Gate 2
may open.

The result validates common-frequency-restoration authority for the hybrid
PV+GENCLS VSG proxy plus independent grid-following ESD1 storage layer.  It
does not validate a unified physical GFM-BESS, learning, topology
generalisation, formal stability, EMT, cross-simulator transfer, HIL, or
deployment.  Those remain separate gates.

## Assets

- `memory/rounds/R274/plan.md`
- `memory/rounds/R274/candidate_bank.json`
- `memory/rounds/R274/candidate_seal.json`
- `memory/rounds/R274/formal_seal.json`
- `src/andes_rl_kundur/evaluation/prospective_authority.py`
- `scripts/eval_prospective_active_power_authority.py`
- `tests/test_prospective_authority.py`
- `results/r274_prospective_active_power_authority/screen_summary.json`
- `results/r274_prospective_active_power_authority/feasibility_screen_contract.json`
- `results/r274_prospective_active_power_authority/formal_bank.json`
- `results/r274_prospective_active_power_authority/active_power_authority_summary.json`
- `results/r274_prospective_active_power_authority/provenance.json`
- `memory/claims/CLM-0580.md`

## Verification

- Zero-support screen: 24/24 traces, one real-ANDES process, zero stderr.
- Formal droop+PI: 24/24 traces, one real-ANDES process, zero stderr.
- Independent screen/formal trace hash audit: zero mismatches.
- Pre-seal Windows full suite: 410 passed, 6 skipped, 1 expected xfail.
- Pre-seal WSL focused real-ANDES/V4 suite: 16 passed.
- Ruff and dual-metric lint passed before the first seal.
- Final Windows full suite: 410 passed, 6 skipped, 1 expected xfail.
- Final WSL focused real-ANDES/V4 suite: 15 passed; only existing ANDES
  ComplexWarnings were emitted.
- Final Ruff and dual-metric lint passed; validation passed with 23 historical
  path/heuristic warnings and no errors; rendering completed.
- Final selector: Q-0037 ready in `P1_residual_mechanism`, with no active
  round.

## Questions opened (this round)

- Q-0037 — under the validated slow controller, test whether one frozen
  bounded fast M/D law adds independent RoCoF, peak, synchronization, or
  inter-area value.  No learning is authorized.

## Questions closed (this round)

- Q-0036 — closed-positive by CLM-0580 with the registered
  AUTHORITY-POSITIVE classification.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了什么**：先生成一套全新的 24 个扰动场景，强制覆盖四个负荷位置、正负两个方向和三档强度；在任何控制器轨迹出现前，只让“储能功率恒为零”的同结构系统把每个场景跑满 60 秒，冻结可行性和哈希。24 个全部通过后，才用另一个正式封印让 R272 已冻结的 droop+PI 储能控制器各跑一次。全程没有训练 AI，也没有调整 M/D、储能容量、PI 增益、场景或判定门槛。

**一句话结果**：正式结论是 **AUTHORITY-POSITIVE**。这次不是失败实验；它证明在这套提前冻结的新场景库上，受功率和能量约束的储能有功通道确实能把全系统共同频率拉回额定值附近。

**最关键的数字**：零支持和 droop+PI 都是 24/24 跑满。频率偏差的全程累计量降低 58.63%，最后 10 秒的共同频差降低 77.29%，而且 24/24 个场景两项都改善；最坏母线峰值降低 19.39%，RoCoF 降低 2.15%。SOC 只在 0.486–0.512，功率最高约 0.314 pu，低于 0.36 pu 上限，零限幅、零约束违规，M/D 始终固定 200/100。

**这说明什么**：以前的问题不是“AI 算法没调好”，而是 VSG 的 M/D 本身没有持续补充能量的权力。现在新增并验证的是一个独立的储能慢有功模块；它负责长期把共同频率恢复回来。原 VSG 的 M/D 快层仍负责惯性、阻尼、RoCoF、峰值和同步，但本轮没有让它动作。

**仍然不说明什么**：当前是 `PV+GENCLS VSG 代理 + 独立 GFL ESD1 储能` 的混合验证，不是统一物理 GFM-BESS；也还没有证明拓扑泛化、稳定性证书、EMT、HIL 或 AI 优于经典控制。

**下一步只做什么**：单独进入 Gate 2，在完全相同的 droop+PI 慢有功控制下，比较“固定 M/D=200/100”和“一条提前冻结、受幅值/速率约束的快速 M/D 规律”，只问它是否还能独立改善 RoCoF、峰值、同步和区域间振荡。Gate 2 仍不训练 AI；如果快层没有独立价值，就删除双层故事，只保留已经验证的慢有功层。
