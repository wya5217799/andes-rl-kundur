# R280 verdict — float32-aware correction of R279

**Status**: COMPLETED — `AUDIT-CORRECTION-VALID`
**Corrected R279 decision**: `CENTRALIZED-EXPLANATION-SUFFICIENT`
**Claim**: CLM-0610
**Question**: Q-0041

## TL;DR

R279 的 192 条轨迹没坏。坏的是审计容差：float32 动作只允许 1e-9
误差，5 条合法轨迹被误判。R280 用预先冻结的一 ULP 规则复核原数据，
5 项恰好转为通过，其余完全不变。纠正后：集中式 TD3 有稳定价值，
共享 MARL 也比 q=0 好，但明显不如集中式 TD3。

## Diagnosis

- Frozen limit: `q_slew_max=0.25`.
- Old tolerance: `1e-9`.
- Registered corrected tolerance:
  `spacing(float32(0.25)) = 2.9802322387695312e-08`.
- Maximum observed excess: `7.450580596923828e-09`.
- False-to-true audits: exactly 5.
- Verified immutable traces: 192 / 192.
- New ANDES trajectories: 0.
- Other audit changes: 0.

Root cause: audit dtype/tolerance mismatch. The controller projects and stores
`q` as float32, while the old post-hoc audit treated a float64 difference as
if it had exact-real arithmetic and used a smaller-than-ULP tolerance.

## Corrected measured result

| Endpoint | Centralized vs q=0 | Shared vs q=0 | Shared vs centralized |
|---|---:|---:|---:|
| `normalized_sync_loss_hz2` | `-24.345456% [-31.500633%, -17.481533%]` | `-16.793845% [-24.733569%, -5.811277%]` | `+9.981702% [+1.039179%, +26.128993%]` |
| `fast_inter_area_iae_hz_s` | `-17.040674% [-24.595353%, -8.959552%]` | `-9.540768% [-17.191624%, -0.602962%]` | `+9.040461% [+3.088095%, +19.538872%]` |

All three paired seeds favored centralized over shared on both co-primary
endpoints. The causal comparator did not clear both materiality gates.

## Interpretation

可以写进论文：学习型标量差分惯量分配在三新种子、全新 24 场景上有
稳定收益。不能写：MARL 是收益来源、MARL 优于集中式、HAWE 有额外收益、
零和动作等于动态解耦、可去中心化部署。

最诚实主线：共享 MARL 是一个有效方案，但 matched centralized TD3 更强；
因此论文贡献是控制角色解耦、严格可识别性比较和学习型差分分配证据，
不是“必须多智能体”。

## Questions opened (this round)

- None.

## Questions closed (this round)

- Q-0041 — `closed-positive` by CLM-0610 as
  `CENTRALIZED-EXPLANATION-SUFFICIENT`.

## Questions advanced (this round, status unchanged)

- None.

## Verification

- Correction summary SHA-256:
  `4d27cdf0bfacdc49ac1a361909b15e95398d55c63f91e680c482fbac86531f91`
- Correction provenance SHA-256:
  `11e208947bed1867bbeb64756eed938e2d052bc8f82b8f235ba650247f67af6e`
- Parent formal summary SHA-256:
  `6cf7a8afbd26c7e31d4a11cc7d81c3f92010227a90f8ab654031ea24f9bf2ab1`
- Parent formal provenance SHA-256:
  `79fed8934245b2317be82a35ddee6539ae433831be9345cb45433464e2d4b6fd`
- Red/green regression: 1 failed before fix; 4 passed after fix.
- Focused classification/audit tests: 8 passed.
- WSL Ruff: passed.
- Full WSL suite: attempted, but the command hit the 124-s tool timeout
  without a result; no pytest process remained. It is not reported as passed.

## 给 PI 的话

**这周干了啥**：我没有重跑实验，也没有挑种子。我把 R279 唯一的 `INVALID` 原因缩成一个 float32 容差错误，再用原封存的 192 条轨迹重做审计。

**结果（一句话）**：纠正后是 `CENTRALIZED-EXPLANATION-SUFFICIENT`：集中式 TD3 相对 q=0 改善同步损失 24.35%、区域间 IAE 17.04%；共享 MARL 也有 16.79% 和 9.54% 改善，但比集中式差约 10% 和 9%。

**意外**：好消息是学习收益真实、跨三种子和全新扰动成立；坏消息是收益不是 MARL 特有，三个种子全部显示集中式 actor 更强。HAWE 和幸运 seed 49 都不再需要。

**我默认下一步做**：停止新增实验，开始按这个证据改 ICEMS 论文。保留解耦导向问题和现有标题作为默认，但删除 MARL 必要性、动态解耦证明和 HAWE 增益，突出 matched baseline、三种子、fresh bank 和动态响应图。

**你想插一脚就说**：如果你更想保住“MARL 很强”的叙事，需要换研究问题和重新做新实验；默认不走这条慢路，先把当前论文诚实、快速地完成。
