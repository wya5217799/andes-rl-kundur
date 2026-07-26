# R267 verdict — the slew works mechanically but the controller contract fails

**Date**: 2026-07-25
**Status**: CLOSED-NEGATIVE
**Type**: prospectively sealed real-ANDES mechanism test
**Claim**: CLM-0535

## TL;DR

R267 tested the only smoothing law allowed by Q-0029: an alpha-only symmetric
slew limiter fixed at `0.02895` per 0.2-s step from the archived 0.579-Hz
Kundur inter-area mode.  A new no-anchor bank and the full evaluation contract
were hashed before any trajectory.  All 60 trajectories were attempted.

The limiter did what it was designed to do on the 18 shared complete
scenarios: mean action-TV fell 38.52% versus the raw gate.  It nevertheless
remained 140.28% above static, its action-TV CVaR90 was 201.20% above static,
and normalized synchronization loss was 11.22% worse than static.  Two strong
positive Bus14 disturbances also caused all three controllers to fail.  The
pre-registered result is therefore **NEGATIVE**.  Q-0029 and the full
hand-designed selector/smoother family are closed.

## Prospective contract

- Controllers: static alpha=0.25, frozen raw mode gate, and the one
  slew-limited mode gate.
- Common gate parameters: `ratio_full_scale=0.05`, `alpha_cap=0.25`,
  droop `k=10`, legacy R201 checkpoint.
- Slew: first action transparent; later alpha change bounded to
  `±0.02895` per control step.
- New bank: 20 scenarios, seed `20260725`, no anchors, no exact overlap with
  R265.
- Bank SHA-256:
  `3e0cdf16758f6e3adcfeb336c891dce94340c0ee96e759783d1b5fcbcc4e2bd5`.
- Seal-manifest SHA-256:
  `4eb055838a133ecceb5817bb312f229f90d4e2f3c7cc3811515c313f627b0241`.
- V4 paper-faithful defaults, environment seed 42, 150 control steps, cyclic
  controller-order rotation.
- No rate sweep, second smoother, post-hoc row deletion, or corrected
  recurrent training.

The repository-local seal froze the plan, bank, controllers, checkpoints,
bootstrap, and evaluation-source hashes.  It establishes byte identity and
local ordering, not an independent third-party registration timestamp.

## Completion and failure evidence

| Controller | Complete | Failed/incomplete | Settled |
|---|---:|---:|---:|
| static alpha=0.25 | 18/20 | 2/20 | 18/20 |
| raw mode gate | 18/20 | 2/20 | 18/20 |
| slew mode gate | 18/20 | 2/20 | 18/20 |

The same scenarios failed for every controller:

- `random_01`: `PQ_Bus14=+2.9946`;
- `random_18`: `PQ_Bus14=+2.7000`.

Paired completion was 18 both-success, two both-failure, and zero discordant
pairs; two-sided exact McNemar `p=1`.  The runner preserved each failed trace
and did not drop it.  Consequently the planned paired bootstrap contrasts
were marked unavailable rather than being computed on a selected successful
subset.

This is a valid negative scientific result, not an infrastructure-invalid
run: bank, manifest, checkpoints and source hashes matched; all requested
runs were attempted; the failures are recorded ANDES TDS convergence
terminations.

## Descriptive mechanism dashboard

The following means use the 18 scenarios where all three controllers
completed.  They are mechanism diagnostics only because the prospective
confirmatory analysis correctly refused to drop the two failed rows.

| Controller | VSG-mean IAE | normalized sync loss | worst-bus peak | max RoCoF | action-TV | action-TV CVaR90 |
|---|---:|---:|---:|---:|---:|---:|
| static alpha=0.25 | 0.718207 | 2.64670e-05 | 0.071362 | 0.123443 | 1.640884 | 1.806772 |
| raw mode gate | 0.687314 | 2.59443e-05 | 0.070793 | 0.122660 | 6.412659 | 12.622256 |
| slew mode gate | 0.687889 | 2.94373e-05 | 0.073403 | 0.127317 | 3.942736 | 5.442008 |

Key descriptive effects:

- slew versus static VSG-mean IAE: `-4.2214%`;
- slew versus static normalized synchronization loss: `+11.2225%`;
- slew versus static mean action-TV: `+140.2812%`;
- slew versus static action-TV CVaR90: `+201.2006%`;
- slew versus raw mean action-TV: `-38.5164%`;
- raw versus static VSG-mean IAE: `-4.3015%`;
- raw versus static normalized synchronization loss: `-1.9752%`.

The rate limiter therefore fixed part of the diagnosed switching mechanism,
but the induced dynamic lag/trajectory change erased the differential-mode
benefit and left control movement far above the static reference.  This is
not a near miss on the registered contract.

## Outcome against the pre-registered gate

| Gate | Result |
|---|---|
| all 60 traces complete | **FAIL** — 54 complete, six common failures |
| both slew-vs-static co-primary directions improve | **FAIL** — sync loss worsened descriptively |
| at least one co-primary interval clears zero | unavailable by design after failures |
| slew failure not higher than static | PASS — equal 2/20 |
| safety CVaR90 no worse than +5% | PASS descriptively |
| safety bank-worst no worse than +10% | PASS descriptively |
| settling success not lower | PASS — equal 18/20 |
| action-TV CVaR90 no worse than +25% vs static | **FAIL** — +201.20% |
| slew mean action-TV below raw | mechanism signal only — -38.52%, but confirmatory contrast unavailable |

Classification: **NEGATIVE**.

## Feasibility interpretation

1. **The code path is feasible.**  The project can implement, seal, reload,
   and evaluate a dynamic stateful selector with real ANDES and immutable
   traces.
2. **The hand-designed selector thesis is not feasible in its tested form.**
   Two consecutive sealed rounds show the same pattern: a small physical
   opportunity exists, but controller movement or dynamic coupling defeats
   deployability.
3. **The experiment domain needs an explicit feasible envelope.**  Two Bus14
   disturbances failed identically for static, raw and slew.  Future
   algorithm-specific safety inference must distinguish reference-infeasible
   disturbances from residual-induced failures without deleting sealed rows.
4. **The next mechanism remains worth testing.**  A bounded learned residual
   around droop is scientifically distinct because its residual is trained
   under the same composition used at evaluation, rather than post-processing
   a legacy policy with a hand-designed selector.
5. **No publication-level claim is available.**  Evidence remains one
   modified Kundur topology, one legacy checkpoint family, small sealed banks,
   no multi-seed corrected residual, no stability certificate, and no
   topology or simulator transfer.

## Assets

- `memory/rounds/R267/plan.md`
- `memory/rounds/R267/scenario_bank.json`
- `memory/rounds/R267/scenario_bank.json.sha256`
- `memory/rounds/R267/scenario_bank.manifest.json`
- `memory/rounds/R267/evaluate.stdout.log`
- `memory/rounds/R267/evaluate.stderr.log`
- `results/r267_q0029_slew_replication/provenance.json`
- `results/r267_q0029_slew_replication/traces/`
- `results/r267_q0029_slew_replication/sealed_gate_replication_summary.json`
- `results/r267_q0029_slew_replication/sealed_gate_replication_summary.md`
- `src/andes_rl_kundur/evaluation/hybrid.py`
- `src/andes_rl_kundur/evaluation/sealed_bank.py`
- `scripts/eval_sealed_gate_replication.py`
- `memory/claims/CLM-0535.md`

## Verification

- focused hybrid/sealed-bank tests: 28 passed;
- full Windows tests before sealing: 344 passed, 3 skipped, 1 expected xfail;
- round preflight before sealing: clean;
- final dual-metric lint: 272 claims passed;
- memory validation: 272 claims, 30 questions, and 24 notes passed with 22
  pre-existing missing-provenance warnings plus one expected keyword-overlap
  heuristic warning for newly opened Q-0030;
- STATE render: passed.

## Questions opened (this round)

- Q-0030 — corrected, training/deployment-consistent bounded residual around a
  droop prior, beginning with a subtractive feasibility pilot.

## Questions closed (this round)

- Q-0029 — closed-negative by CLM-0535; the one permitted smoother reduced
  raw switching variation but failed the physical/action contract.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了啥**：只测了一个提前冻结的 alpha 对称限速器；新建并哈希 20 个无 anchor 扰动，再把 static、raw gate、slew gate 共 60 条真实 ANDES 轨迹全部跑完，没有扫 rate，也没有删失败场景。

**结果（一句话）**：slew 相对 raw 确实把成功场景的平均 action-TV 降了 `38.52%`，但相对 static 仍高 `140.28%`、TV 尾部高 `201.20%`，同步损失还差 `11.22%`，所以按预注册规则是负结果。

**意外**：两个正向 Bus14 扰动让三种控制器一起失败；这更像当前扰动域/ANDES 可行边界，而不是 slew 独有失稳，但“全部完成”门槛仍然必须判失败。

**我默认下一步做**：关闭 hand-designed gate/smoother 整个家族，不再调阈值或第二个平滑器；复用现有 V4、agent 和评估代码，先做训练/部署完全一致的 memoryless bounded residual around droop 最小可行性实验。

**你想插一脚就说**：你可以否决 residual 的物理 prior、残差幅值来源或 reference-feasible envelope；否则我会先用小 pilot kill gate，只有通过才花算力跑多 seed 和新 sealed bank。
