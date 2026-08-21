# R458 verdict — 开发集选出的分段方案在两个固定评估对象上守卫全清

**Date**: 2026-08-21  
**Status**: completed  
**Type**: experiment  
**Wall**: ~7.5h formal（开发分片 ~7.4h，评估分片 ~0.5min，不含离线吸收审计）

## TL;DR

有效分类为 `GUARD-CLEAN-TRANSFER`。冻结的 350 条 direct-M/D 分段方案只在
dev_a/dev_b 上选出唯一 priority-1 winner `k3_112`；同一 winner 在固定
eval_b/eval_c 守卫全清，在 eval_a 因 TV、eval_d 因差模改善不足而失败。
该结果只建立 2/4 固定 profiles 的 finite-bank witness，不是 transfer
probability、topology generalization、learner success 或稳定/安全证书。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R458.md`

## 给 PI 的话

**发生了什么**：我们只用两组开发条件，从三百五十条预先固定的惯性和阻尼分段方案中选出唯一一条两组都达标的方案，再把同一条方案原样放到四组固定评估条件中各检查一次。结果有两组全部达标，另外两组没有达标：一组动作变化过大，另一组频率差异改善只有百分之四点八五，低于百分之五的门槛。

**这说明什么**：此前“先看评估结果再挑方案”的偏差已经被消除。现在可以确认，这个有限方案集合里确实存在一条能从开发条件转到部分固定评估条件、同时兼顾频率改善和动作代价的方案。但四组只通过两组不能解释为百分之五十的普遍成功率，也不能说明它能适应新网络、能被学习方法找到，或已经证明稳定与安全。

**下一步做什么**：保留两组失败作为论文边界，不重新挑方案、不改门槛，也不围绕这次结果继续调参。接下来把外部数学解答逐条按“已证明、带条件可用、仍缺数据、必须补实验”归档，只把能够独立复算且不夸大范围的结论写入论文；缺少完整模型和二阶数据的问题留作后续工作。
