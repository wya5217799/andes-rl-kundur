# R269 verdict — objective audit catches a false premise and blocks retraining

**Date**: 2026-07-25
**Status**: CLOSED-NEGATIVE
**Type**: offline objective-validity and correction audit
**Claims**: CLM-0545, CLM-0550

## TL;DR

R269 froze one four-term physical/residual loss and audited it with synthetic
counterexamples plus all 16 immutable R268 trajectories, without new ANDES or
training.  The candidate arithmetic passed all 11 synthetic and all nine
archived-trace checks, but the pre-registered source diagnosis failed:
R268 actually trained with `phi_abs=50.0`, not zero.  The overall prospective
verdict is therefore **FAIL**; no second training run is authorized, and the
R268 NO-GO measurements remain valid while their earlier objective-blindness
explanation is corrected.

## Frozen candidate

The audited lower-is-better per-step loss was the unweighted sum of:

1. `abs(mean(delta_f_physical_hz)) / 0.05`;
2. `mean((delta_f_physical_hz - mean)^2) / 0.05^2`;
3. `mean_agent(sum_component(abs(raw_residual))) / 2`;
4. `mean_agent(sum_component(abs(raw_residual_t - raw_residual_t-1))) / 4`.

The four terms are dimensionless.  Their normalizers were frozen in the plan
from the existing 0.05-Hz settling band and the exact L1 ranges of a
two-component residual in `[-1,1]`; no R268 effect was used to tune a weight.

## Audit result

| Audit group | Passed | Result |
|---|---:|---|
| source diagnosis | 6/7 | **FAIL** |
| synthetic sign/unit checks | 11/11 | PASS |
| archived trajectory checks | 9/9 | PASS |
| overall pre-registered gate | — | **FAIL** |

The failed source check is exact and material:

- `results/r268_residual_td3_s49/training_log.json` records
  `env_config.phi_abs=50.0`;
- it also records `phi_f=100.0`, `phi_h=0.0056`, `phi_d=0.0056`, and
  `r_avg_scope=global`;
- `base_env.py` applies `self.PHI_ABS * r_abs`, so R268 did contain an
  absolute/local frequency-error term.

Therefore the prior assertion that R268 omitted common/absolute restoration
from training is false.  The candidate objective still gives cleaner
mode-separated and residual-specific accounting, but passing its arithmetic
checks cannot rescue a pre-registered audit whose causal premise failed.

## Synthetic evidence

All planned semantic counterexamples passed:

- uniform `+0.05 Hz` produced common `1`, differential `0`;
- `[+0.05,-0.05,+0.05,-0.05] Hz` produced common `0`, differential `1`;
- zero residual produced zero effort and movement;
- opposing residuals were charged despite zero fleet mean;
- constant residual had zero inter-step movement and a sign switch had
  positive movement;
- non-finite, wrongly shaped, and out-of-bound inputs were rejected.

These are implementation-validity results only.  They do not show that the
candidate reward would train a better controller.

## Archived R268 reproduction

The audit independently reproduced the registered physical directions:

| Quantity | Droop mean | Residual mean | Residual minus droop |
|---|---:|---:|---:|
| VSG-mean IAE (Hz s) | 0.939839673 | 0.940730228 | +0.094756% |
| normalized sync loss (Hz²) | 1.370730e-05 | 1.371779e-05 | +0.076495% |
| frozen two-frequency-term scalar | 0.632042703 | 0.632640601 | +0.094598% |
| old `cum_rf_total` | -0.001427844 | -0.001428936 | -1.09223e-06 absolute |

- common endpoint identity maximum error: exactly `0`;
- differential endpoint identity maximum error: `6.78e-21`;
- paired direction ordering preserved in all eight scenarios for both modes;
- common improved in 2/8 and differential in 3/8, matching R268;
- reconstructed raw residual maximum magnitude: `0.358765`;
- executed-action reconstruction maximum absolute error: `3.47e-18`;
- defined droop residual effort/variation: zero.

Thus the R268 numerical NO-GO is not affected by the diagnosis correction.

## Correction to R268

CLM-0550 supersedes CLM-0540.  The corrected interpretation is:

1. the exact memoryless TD3/k10/beta0.10 residual still fails its prospective
   co-primary mechanism gate;
2. the implementation, completion, safety, action, and reload evidence still
   passes;
3. the residual was not trained under a reward with `PHI_ABS=0`; its effective
   value was `50.0`;
4. the single pilot does not uniquely locate the failure in reward,
   optimization, observation, residual parameterization, or plant control
   authority;
5. another learned-controller run is not justified until a controller-agnostic
   attainable-gain audit establishes that the current inertia/damping
   actuation has a meaningful margin above droop.

## Feasibility interpretation

- **Software/platform feasibility remains positive.**  The audit consumed
  immutable traces, reproduced endpoint identities, reconstructed residual
  actions, and caught a claim-level configuration error.
- **The reward-repair hypothesis is rejected as stated.**  It was built on an
  incorrect effective configuration.
- **The learned residual direction is paused on this environment.**  A clean
  objective implementation alone is not evidence of attainable benefit.
- **The next useful experiment is plant-level, not algorithm-level.**  Measure
  an oracle or upper-bound improvement margin for admissible inertia/damping
  schedules over droop.  If that margin is negligible, further AI search has
  no defensible target; if it is material, the remaining problem is
  observability/optimization rather than actuation.
- No topology, stability, cross-simulator, or publication claim is made.

## Assets

- `memory/rounds/R269/plan.md`
- `src/andes_rl_kundur/evaluation/residual_objective.py`
- `scripts/audit_residual_objective.py`
- `tests/test_residual_objective.py`
- `results/r269_objective_audit/objective_audit.json`
- `results/r269_objective_audit/objective_audit.md`
- `results/r268_residual_td3_s49/training_log.json`
- `results/r268_residual_pilot_eval/traces/`
- `memory/claims/CLM-0545.md`
- `memory/claims/CLM-0550.md`

The audit JSON SHA-256 is
`f7b6c1a780cd286e7a9d3c56a066235b964f272864f1717e874cbdd04f3b2825`.

## Verification

- R269 preflight: clean, one informational no-concrete-baseline notice;
- focused objective/physical/adapter tests: 22 passed;
- Ruff on the three new files: passed after two style-only repairs;
- full Windows suite: 366 passed, 3 skipped, one expected xfail;
- formal offline audit: 6/7 source, 11/11 synthetic, 9/9 archived;
- no new ANDES trajectory and no controller training were run.

## Questions opened (this round)

- Q-0032 — determine whether the current VSG inertia/damping actuation admits
  a nontrivial controller-agnostic improvement margin above droop before any
  further learned policy.

## Questions closed (this round)

- Q-0031 — closed-negative by CLM-0545 because the pre-registered source
  premise failed (`phi_abs` was 50.0, not zero); no retraining is authorized.

## Questions advanced (this round, status unchanged)

- Q-0030 remains closed-negative, but its closing claim is corrected from
  superseded CLM-0540 to CLM-0550.  The measured NO-GO is unchanged.

## 给 PI 的话

**这轮干了啥**：没有再跑 ANDES 或训练。我把一个物理共模/差模 + residual 幅值/变化的四项 loss 先冻结，再用合成反例和 R268 全部 16 条旧轨迹做离线审计。

**结果（一句话）**：候选公式的 11/11 合成检查和 9/9 轨迹检查都通过，但总判定仍是 **FAIL**，因为我先前写错了关键配置——R268 实际 `phi_abs=50.0`，不是 0；所以不能用“训练没看共模频差”解释失败，也不允许据此重训。

**意外**：这是好用的负结果。它没有推翻 R268 的数值 NO-GO（IAE 仍差 `0.0948%`、同步损失仍差 `0.0765%`），但推翻了错误的因果故事；项目的可追溯审计确实在阻止我们把一个方便的解释写成事实。

**我默认下一步做**：暂停 learned residual 和 reward 调参，先做 controller-agnostic 的“可达到增益上界”实验：给当前惯量/阻尼执行器一个低维、知道扰动的 oracle，看看它相对 droop 到底有没有实质物理改进空间。

**你想插一脚就说**：如果你认为“oracle 也赢不了就停 AI 控制”过于严格，可以指定你接受的最小改进幅度；否则我会先验证控制对象有无可学空间，再谈网络、拓扑和安全。
