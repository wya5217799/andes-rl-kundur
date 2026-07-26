# R275 verdict — simple sealed fast inertia adds independent value above slow droop+PI

**Date**: 2026-07-26
**Status**: CLOSED-POSITIVE
**Type**: experiment
**Wall**: ~1 h

## TL;DR

R275 is FAST-LAYER-POSITIVE: one frozen 3-s common positive-inertia pulse above
the unchanged R274 slow droop+PI/storage controller improved all four
registered fast physical endpoints across 24 sealed paired scenarios, with
every uncertainty, tail, restoration, action, storage, completion, and
provenance guard passing. The result supports a simple common/differential,
fast/slow architecture; it does not support HAWE or establish learned-control
value.

## Methodology

R275 reused the immutable 24 R274 `droop_pi` traces as the matched baseline.
The only new candidate action was frozen before its first formal trajectory:
all four normalized M actions were +0.25 for the first 15 control steps
(3.0 s), then zero; every D action was zero. The unchanged slow controller,
storage plant, scenario bank, solver, horizon, physical 60-Hz endpoint
definitions, action budgets, paired-bootstrap inference, guards, and stopping
rules were bound by formal-seal SHA-256
`fd075c29f20c56835283e620af83922df9c55d8942380e534003c70d1ae7cd52`.

Two disjoint WSL shards executed 12 real-ANDES trajectories each. Every
candidate path was unique, both stderr logs remained empty, and analysis ran
only after all 24 candidate traces existed. The first analysis invocation
used a relative `--out-dir` and stopped before writing a summary because its
path audit requires a path below the absolute repository root; the same sealed
code, traces, and hashes were then analysed with the equivalent absolute
output path. No experiment, method, artifact, threshold, or source was
changed.

## Results

Both arms completed 24/24 scenarios for 300/300 steps with zero TDS failures,
zero missing pairs, zero constraint violations, and zero storage saturation
reasons.

| Registered endpoint | R274 slow baseline mean | + frozen fast M pulse mean | Effect | Paired-bootstrap 95% interval |
|---|---:|---:|---:|---:|
| max sampled RoCoF (Hz/s) | 0.140324089 | 0.100509055 | **-28.373628%** | [-30.8504%, -25.4617%] |
| worst-bus peak (Hz) | 0.084575943 | 0.075207271 | **-11.077230%** | [-14.2936%, -7.52073%] |
| normalized synchronization loss (Hz²) | 3.142109e-05 | 3.007308e-05 | **-4.290160%** | [-6.67573%, -2.46646%] |
| first-3-s inter-area IAE (Hz s) | 0.065634647 | 0.059127155 | **-9.914721%** | [-13.1469%, -7.03780%] |
| VSG-mean IAE (Hz s) | 0.969065074 | 0.967095671 | -0.203227% | [-0.242504%, -0.161153%] |
| final-10-s common absolute error (Hz) | 0.008275849 | 0.008319568 | +0.528270% | [0.418520%, 0.630888%] |

All four fast endpoints clear the registered -2% materiality and uncertainty
rules. They include both common-frequency endpoints (RoCoF and peak) and both
differential endpoints (synchronization loss and inter-area IAE). Registered
upper-tail effects were -34.2597%, -10.9604%, -4.33965%, and -16.2372% for
RoCoF, peak, synchronization loss, and inter-area IAE; no tail guard worsened.

The slow layer remained intact. VSG-mean IAE improved slightly and the
final-window common error increased only 0.528%, well inside the frozen point
and uncertainty guards. BESS command L1, TV, charge energy, and discharge
energy effects were -0.660%, +4.765%, -0.620%, and -0.697%, all within the
+5% guard. Candidate SOC stayed within
`[0.486090666, 0.511449272]`, maximum requested/commanded/actual power stayed
below 0.314 system pu, and all 24 traces matched the exact M/D action contract.

## Interpretation and paper boundary

The coupling question exists, but the defensible version is narrower than the
historical narrative: the system has measurable short-horizon inter-area and
synchronization dynamics that remain distinct from common-frequency
restoration. They do not require HAWE to become visible, and R275 shows that a
transparent 3-s common-inertia rule already captures material fast value.

The strongest paper architecture is therefore:

1. common versus differential frequency objectives;
2. slow bounded active power for common restoration;
3. fast bounded inertia for RoCoF, peak, synchronization, and inter-area
   shaping;
4. any MARL component only as a small adaptive residual that must beat this
   simple reference.

R275 does not show that MARL, HAWE, adaptive damping, topology
generalisation, stability certification, EMT, HIL, deployment, or a unified
GFM-BESS improves on the classical reference. In particular, HAWE should be
reduced to a historical/negative ablation, not presented as the source of the
measured fast-layer effect.

## Assets and provenance

- `memory/rounds/R275/plan.md`
- `memory/rounds/R275/formal_seal.json`
- `results/r275_fast_md_authority/formal_traces/`
- `results/r275_fast_md_authority/fast_md_authority_summary.json`
- `results/r275_fast_md_authority/fast_md_authority_summary.md`
- `results/r275_fast_md_authority/provenance.json`
- `results/r275_fast_md_authority/logs/`
- `src/andes_rl_kundur/evaluation/fast_md_authority.py`
- `scripts/eval_fast_md_authority.py`
- `tests/test_fast_md_authority.py`
- `memory/claims/CLM-0585.md`

The summary SHA-256 is
`30a1cc6ee7da0759236b9119ffcee706716432bd57b6ed988a42fafc4dc3d29d`;
the provenance SHA-256 is
`681ba69d959a1e943724468c66a20b51b9775d12a5733d13a744399351f8f99d`.

## Verification

- Formal candidate trajectories: 24/24 complete, 300/300 steps, zero TDS
  failures; both shard stderr logs are empty.
- Immutable R274 baseline pairs: 24/24 verified by recorded trace hash.
- Candidate action audits: 24/24 pass every exact amplitude, duration, slew,
  L1, TV, M/D range, and saturation check.
- Completion, storage, SOC, power, energy, restoration, tail, and provenance
  guards: all pass.
- Focused Windows R275 tests: 6 passed, 1 WSL-only skipped.
- Ruff on all three R275 implementation/test files: passed.
- R275 preflight: no warnings or blocks; one informational baseline-name
  heuristic notice only.
- Final Windows suite: 416 passed, 7 skipped, 1 expected xfail.
- Final WSL focused real-ANDES/V4 suite: 27 passed; only existing ANDES
  ComplexWarnings were emitted.
- Final dual-metric lint and ledger validation passed; validation retained 22
  historical missing-path warnings and introduced no new warning.

## Questions opened (this round)

- Q-0038 — determine whether one corrected, memoryless, parameter-shared,
  bounded differential MARL residual adds incremental value over the strong
  sealed R274+R275 simple controller. HAWE, ensemble selection, LSTM, damping
  actions, and best-seed headlines are forbidden.
- Q-0039 — run first as the upstream Gate 3 prerequisite: add only the missing
  fast-only arm, reuse the 72 immutable R274/R275 traces, and test the
  four-arm fast/slow interaction with three WSL shards. Q-0038 remains blocked
  until this non-additivity gate and the subsequent learning-gap diagnosis.

## Questions closed (this round)

- Q-0037 — closed-positive by CLM-0585 with the registered
  FAST-LAYER-POSITIVE classification.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了什么**：没有训练 AI，也没有调 HAWE。我把上一轮已经验证的慢有功 droop+PI 完全固定，只额外加了一条事先封存的简单规则：四台 VSG 在扰动开始后的 3 秒内统一增加惯量，然后恢复原值；用 24 个新场景逐一配对验证。

**结果（一句话）**：结论是 **FAST-LAYER-POSITIVE**；RoCoF 降 28.37%，最坏母线峰值降 11.08%，同步损失降 4.29%，前三秒区域间振荡累计量降 9.91%，24/24 全部完成且安全、能量、尾部风险和统计区间门槛全部通过。

**意外**：真正有效的东西比旧故事简单得多。过去把亮点归给 HAWE 或复杂多智能体并不可靠；同一条透明的 3 秒惯量规则已经同时改善共同频率风险和区域间耦合，而且没有破坏慢层恢复。

**我默认下一步做**：保留“解耦”主线，但把它定义成“共同/差异模态 + 快/慢执行器”的物理解耦。HAWE 只保留为负面对照。若标题继续写 MARL，下一步只训练一个共享、无 LSTM、受限幅和速率约束的很小差模残差，并必须直接打赢这条简单规则；打不赢就删除 MARL 贡献。

**你想插一脚就说**：你可以决定论文是否一定保留 MARL 作为贡献；如果保持沉默，我会按最保守路线推进——不改标题、不发邮件，但绝不再用幸运种子或 HAWE 包装结果。
