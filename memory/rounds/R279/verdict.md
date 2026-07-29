# R279 verdict — reviewer-driven MARL identifiability

**Status**: COMPLETED — `INVALID`
**Claim**: CLM-0605
**Question**: Q-0041

## TL;DR

one or more formal validity or guard contracts failed. The prospective analysis used every frozen seed and fresh-bank case, with no seed or checkpoint selection.

## Measured result

| Endpoint | Causal vs q=0 | Shared vs q=0 | Shared vs causal | Shared vs centralized |
|---|---:|---:|---:|---:|
| `normalized_sync_loss_hz2` | `+0.028350% [-0.262495%, +0.432047%]` | `-16.793845% [-24.733569%, -5.811277%]` | `-16.817428% [-24.644610%, -6.158116%]` | `+9.981702% [+1.039179%, +26.128993%]` |
| `fast_inter_area_iae_hz_s` | `-0.094403% [-0.194508%, +0.026507%]` | `-9.540768% [-17.191624%, -0.602962%]` | `-9.455291% [-17.071924%, -0.570696%]` | `+9.040461% [+3.088095%, +19.538872%]` |

Completed trajectories: 192 / 192. Classification: `INVALID`.

## Interpretation

The experiment distinguishes physical feedback value, centralized learned value, and parameter-sharing-specific value under one matched action and information contract. R278 remains a historical `PILOT-NO-GO`; R279 does not rescue or relabel it.

## Questions opened (this round)

- None.

## Questions closed (this round)

- Q-0041 — `closed-partial` by CLM-0605 as `INVALID`.

## Questions advanced (this round, status unchanged)

- None.

## Verification

- Formal summary SHA-256: `6cf7a8afbd26c7e31d4a11cc7d81c3f92010227a90f8ab654031ea24f9bf2ab1`
- Formal provenance SHA-256: `79fed8934245b2317be82a35ddee6539ae433831be9345cb45433464e2d4b6fd`
- Formal seal SHA-256: `05a120983c7cfa92e07d7868a7da09d4718743451aae2d899c3fbe10bf988916`
- Fresh formal bank SHA-256: `10f774e899218d7e4a3adea2b62cdef8c21b71daef33e73bae094d4c4c8b2b54`

## 给 PI 的话

**这一轮干了什么**：我没有继续挑幸运种子，而是把简单因果反馈、几乎同参数量的集中式 TD3、参数共享 TD3 放进同一个冻结实验里；三种新种子全部保留，控制器冻结后才生成并筛选全新的扰动库。

**结果（一句话）**：正式分类是 **INVALID**。共享 TD3 相对 q=0 的同步损失结果为 -16.793845% [-24.733569%, -5.811277%]，前三秒区域间 IAE 为 -9.540768% [-17.191624%, -0.602962%]；判定理由是：one or more formal validity or guard contracts failed。

**这意味着什么**：这轮回答的是‘过去看到的提升到底是不是 MARL 特有’。无论结果正负，都不能再用 seed 49 或 HAWE 包装结论；必须以因果基线、集中式基线和三种子 fresh-bank 证据为准。

**默认下一步**：先停实验，保持论文文件不动。下一次只根据这个正式分类调整论文叙事和图表，不再改奖励、网络、动作幅值或基线来补救结果。
