# R441 verdict — R439 时变 headroom 守卫补全: GUARD-VIOLATED (action-stress)

**Date**: 2026-08-20
**Status**: completed
**Type**: experiment
**Wall**: ~10 min (capacity ladder + 4 shards + aggregate)

## TL;DR

R441 补全 R439 no-harm 守卫: 4 个评估 profile 全部 GUARD-VIOLATED
(action-stress 违反, common-mode 干净)。R439 winner (常数 (3,3) 增益)
复现 r_d +6~14% / r_cross +7.6~12% 改善且 common-mode 无害全过, 但
action RMS +28~34%、action total variation +10~17% 超 +10% 预算。
时变 headroom 是 endpoint-only、带动作代价, CLM-1355 的 no-harm 需收窄。

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R441.md`

## 给 PI 的话

**发生了什么**：上一轮我们得到一个结果，说换一种控制方式，能让电网在受到干扰后，两个关键指标都变得更好。但我复查发现，上一轮只看了"指标有没有变好"，漏掉了"这么做的代价大不大"。这一轮我把上一轮挑出来的方案重新跑了一遍，这次把代价也算进去一起看。

**这说明什么**：好消息是，指标确实变好，而且对电网本身没有造成额外的坏影响——波动的幅度、峰值和变化速度都在允许范围里，有的还更好了。坏消息是，这些方案全都是靠"更用力"来达到效果的，控制力度比原来大了三成左右，动作变化的频繁程度也大了一成半上下，都超过了我们事先定下的"最多大百分之十"的底线。所以上一轮的结论要改得更准：改进是真的，但不是白拿的，是用更大的控制力度换来的。

**下一步做什么**：这一轮作为一个有边界的结论收尾归档，结论写进论文的证据链，同时把上一轮结论里的说法改成"指标改进、但控制力度超预算"的准确表述。如果后面想要一个"指标改进而且不超预算"的方案，需要另起一轮，专门去找控制力度更小的候选。
