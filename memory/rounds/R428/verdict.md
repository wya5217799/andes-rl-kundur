# R428 verdict — C1-SAC 精确复现:参照论文的 SAC 接口在本物理环境坍缩(数值发散 + 策略熵坍缩 + 动作超速),银行无效;标量对照臂字节不变,失败在接口不在测试台

**Date**: 2026-08-18
**Status**: completed
**Type**: experiment
**Wall**: ~3.2h（训练 9 组 ~2.2h + 评估/分类 ~1h；含 Tier-1 与阶梯）

## TL;DR

R428 reproduced the exact Yang-2022 TPWRS SAC interface (per-agent single-critic + V-bar target + auto-alpha, 4x128, no slew projection, reward Eq.14-18 rebuilt from the obs row with phi=[100,1,1]) on the matched harness bundle and measured a bounded negative result: the paper-strict reward diverges the value scale (critic loss ~1e8), saturates alpha at its 5.0 ceiling, collapses the policy entropy (mean log pi +10.36 to +10.90), and the unslewed actions violate the actuator slew guard in every eval block, so the classification is CANARY-INVALID; the scalar arm stays byte-identical to R419, confirming the harness is drift-free and the failure belongs to the SAC interface, whose endpoints land at 5.22/4.90 times the deterministic reference — worse than the repaired CD family (~2.5x).

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R428.md`

## 给 PI 的话

**发生了什么**：按您的开门指令，把参照论文的算法原样复现到我们自己的测试台上跑了一遍，只对照、不改任何调参。结果它在我们这套物理环境上练崩了：价值网络数值涨到约一亿量级，熵调节参数顶到上限，策略收缩成几乎一动不动的死板输出，最后因为它一步动作变化超过机器允许的速率，判定整个结果库无效。对照用的标量臂和之前完全一致，说明不是测试台出了问题，而是这套算法接口本身在我们这里站不住。

**这说明什么**：我们把"参照论文的基线只是工程近似"这句保留话，变成了同一测试台上的直接对比——它自己的算法接口在我们这套物理上连一个有效的控制器都练不出来，比我们修好的那套差了一倍以上，而且它默认没有动作速率限制，这是它在这里失败的机制根因。这个结论是事先登记过的预期风险，现在是被测实的不利结果，不是意外翻车；我们也没有擅自去调参救它。

**下一步做什么**：这条复现线到此为止，结论已经拿到，不需要再动。回到主线：剩下的缺口是频率恢复——几台机器步调不一致、频率峰值超限这两类红线仍在每一块里失败，这是当前唯一没攻克的环节，默认下一步朝这个方向做。若您想看现在的结论在更多随机起点下稳不稳，也可以先做五起点扩展再定。
