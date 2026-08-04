# R294 verdict — model-first coupled distributed control

**Date**: 2026-08-02
**Status**: MODEL-FIRST-DISTRIBUTED-BASELINE-VALIDATED-PARTIAL
**Type**: experiment
**Claim**: CLM-0680
**Question**: Q-0051 -> closed-partial

## TL;DR

R294 rejects hard decoupling and the coarse static LPV, identifies active
power as the primary tested actuator, and validates both centralized vector PI
and explicit neighbour-local DAPI against scalar equal-sharing PI. The two
vector formulations have no joint winner, and predictive MPC plus neural
incremental value remain unvalidated.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0051 -> closed-partial by CLM-0680.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：先用完整 ANDES DAE 检查建模假设，而不是继续猜网络结构；依次完成静态模型/耦合检查、M/D/P 权限图、20 条快速选参、36 条冻结比较，以及发布审核发现问题后补做的 12 条显式本地 agent 执行等价验证。

**结果（一句话）**：硬解耦和粗粒度静态 LPV 都没有过门；在同一固定 Kundur 系统的未参与选参工况上，集中式向量 PI 与邻居 DAPI 都明显优于标量等分 PI 的两个差模端点并通过公共/物理守卫，但 DAPI 相对集中式在同步损失上更好、在快速区间 IAE 上更差，因此没有总体胜者。

**意外**：第一次发布审核发现，原 DAPI 虽然数学上只用邻居信息，代码却还是一个对象一次接收四个频率；这不足以叫真正去中心化执行。补成四个独立本地状态对象后，12 个场景的请求功率、执行功率、频率、SOC 和端点与封存结果逐点完全一致，才把这个“一眼硬伤”补上。

**我默认下一步停**：关闭 Q-0051 和 R294，不继续扫增益、不把 208 条权限实验用于反复调参，也不自动训练神经网络。现在最强可用对象是“完整 DAE 验证真值 + 耦合感知有功向量控制 + 显式邻居 DAPI 强基线”；预测 LPV/MPC 和神经增量价值必须另开前瞻问题。

**你想插一脚就说**：若仍要追会议论文的 MARL 标题，下一轮必须只检验神经残差是否在相同局部信息、独立动作、约束和评估银行下超过这条 DAPI 基线；如果不要求 MARL，新结果本身更适合写成有界的模型选择与分布式经典控制结论。

Feed: `results/r294_model_validation/FEED.md`
