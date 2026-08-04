# R318 verdict - rejection localized to delayed poles

**Date**: 2026-08-03
**Status**: completed - POLE-ONLY-REJECTION
**Type**: analysis
**Wall**: ~1h

## TL;DR

R318 validly shows that every frozen scalar in both R317 arms fails the unchanged one-sample augmented-pole ceiling before governor evaluation; only one augmented observer-based offline repair becomes eligible.

## Questions opened (this round)
- Q-0074 - synthesize and reject one observer-based quadratic regulator directly on the delayed augmented realization.

## Questions closed (this round)
- Q-0073 - closed-positive by CLM-0800.

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/decoupling_marl_model_first/reports/R318.md`

## 给 PI 的话

**发生了什么**：我们逐个检查了上次被淘汰的所有方案。结果发现，连力度最小的方案都会让变化越来越难收住，设备限制还没来得及起作用。

**这说明什么**：问题不在于尝试次数不够，也不在于限制太严，而在于旧办法没有把信息晚一步到达这件事直接算进设计。继续缩小力度或放宽限制都没有意义。

**下一步做什么**：下一步换成一种从一开始就把信息晚一步到达和系统当时的变化一起考虑的新办法，仍然先在电脑里考试。通过之前不做真实仿真，也不训练智能控制系统。
