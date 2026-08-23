# R477 verdict — U2 row-permuted-placebo confirmatory completed: effect NOT_ESTABLISHED at 10% bar

**Date**: 2026-08-23
**Status**: completed
**Type**: experiment
**Wall**: ~7h

## TL;DR

R477 completed the U2 row-permuted-placebo confirmatory: all 48 cells finished (16 R476 wave-1 shards carried over by verified hardlinks + 32 fresh), all integrity and optimization gates pass, and neither the actor nor the critic factor establishes an effect above the 10% materiality bar under the direct Holm-controlled test — classifier MATERIAL-EFFECT-NOT-ESTABLISHED, bounded to "not established above 10%", never "no effect".

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0112 remains open (information-level margin program); neither solved nor closed here.

Feed: `paper/yang_md_decoupling_marl/reports/R477.md`

## 给 PI 的话

**发生了什么**：把上一轮中途停止的实验接续完成——上一轮已经跑完的训练成果逐份核验后原样接入,其余全部重新训练,最后对所有单元做了统一评估。全部跑完,数据完整、验证通过。

**这说明什么**：事先定好的判定标准是"真实邻居信息相对置换对照的改善必须超过 10% 才算建立效果"。结果两个端口都没过这条线(一个方向略降,另一个有提升但幅度不足),所以正式结论是"未建立超过 10% 的效果"。这**不等于**"没有效果"——这次种子组数偏少,统计能力只够可靠地检出比较大的效果,所以结论只说到"没达到 10% 这条线",不能说得更重。

**下一步做什么**：这条实验线到此收尾,不再安排新的训练轮次;结论以"未建立"的限定表述进入论文。若将来想下更强的结论,需要另立更大规模的实验设计。
