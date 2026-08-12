# R381 verdict — cascaded washout fails the development eligibility gate

**Date**: 2026-08-12
**Status**: completed — STOP-DEVELOPMENT-NO-CANDIDATE
**Type**: experiment
**Wall**: ~3.9 min formal execution

## TL;DR

R381 validly completes the registered 30-record development bank but stops
because the single second-order controller ties local settling and exceeds
both probe-cross no-harm ceilings. The evaluation bank remains untouched; no
headroom gate, retry, or training is authorized.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R381.md`

## 给 PI 的话

**发生了什么**：我们把离线看起来可行的新控制办法装到四台设备上，按事先约定的三十组情况运行。运行本身全部正常，新办法虽然让一项波动减少了约百分之八，但没有更快稳定下来，而且设备之间原本不该互相影响的程度增加了约百分之二十九到三十，所以没有及格，后面的保留测试也没有打开。

**这说明什么**：单独看一个处理环节时表现好，不等于装进实际系统后仍能同时做到改善波动和避免相互干扰。当前这一个办法已经被有效否定，但不能把它扩大成对所有协同或学习办法的否定。

**下一步做什么**：停止修改这个办法，不调参数重试，也不开始训练。现在应在两件事中做选择：如果没有一个物理上真正不同、同时仍有明确改进空间的方案，就收拢已有负面证据，尽快完成论文；只有找到这样的新方案，才值得再开一次小实验。
