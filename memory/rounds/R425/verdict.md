# R425 verdict — 符号修正重测:动作压力红线首次松动(36→12)、约束被权重上限截断;限幅锁死解除、通信对比解开为约零;估价发散仍在

**Date**: 2026-08-18
**Status**: completed
**Type**: experiment
**Wall**: ~3.2h（训练 9 组 ~2.5h + 评估/分类 ~0.7h）

## TL;DR

R425 fixed the R424 reward-sign defect (CLM-1285) and retested the guard-aligned constraints with true penalty semantics on the verbatim R424/R419 bundle: the pre-registered key contrast is met — both action-stress guards move 36 -> 12 failed blocks (24/36 blocks now pass each guard), the first guard-level action-stress movement in the five-round family, confirming the sign defect as the explanation of the previous null; CANARY-FAIL holds because no arm passes all guards. The dual still saturates at the 10.0 ceiling in 6/6 runs but the RMS residuals collapse from 38.3-90.8x to 1.1-10.1x, the bang-bang collapse resolves (saturation fraction 0.90 -> 0.13, execution mismatch 0.366 -> 0.006), the message contrast unmasks to -1.94% / -2.36%, the endpoints sit at 2.7477 / 2.1127 versus the R419 base 0.6954 / 0.7104, the no-harm profile reverts (36/14/36 versus R424's 12/14/24), and the critic divergence persists (Q4/Q1 4.65-6.29, threshold 3 not met); the scalar arm stays byte-identical to R419.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R425.md`

## 给 PI 的话

**发生了什么**：上一轮实现时把一个正负号装反了，本该惩罚动作过大过猛的两个约束项，变成了动作越猛奖励越大，所以那次实验白跑。这一轮只改正了这个符号，其余原样重跑。结果出现了整个系列五轮以来的第一次松动：动作压力类的红线从三十六块全部失败降到十二块失败，二十四块首次过关；训练里的动作压力读数比上一轮缩小了约十倍。但两个约束的调节权重一上来就顶到上限，没有继续加力的空间，所以离全部过关还差一截。

**这说明什么**：约束机制本身是有效的，之前测不出来确实是符号装反造成的，不是机制无效。但它的效力被权重上限卡住了——权重封顶后约束就推不动了，动作压力只是缩小而没有清零。副作用也真实存在：动作变温和之后，频率类的红线全线回到系列常规水平，端点指标退步到基准的约二点七倍；通信带来的改进重新可测，但测出来基本是零。此外估价网络数值持续膨胀的老毛病只是略有缓解，没有止住。

**下一步做什么**：默认动作是修估价网络的目标值尺度，这是预注册清单里的下一项，也是当前最直接的病灶。同时可以准备一个小型的权重上限与调节步长扫描，看约束能否在不顶上限的情况下把动作压力真正压到过关。另有一组把随机起点从三个扩到五个的平行实验正在收尾，若您希望先看结论在更多起点下是否稳定，可以等它落地后再定。
