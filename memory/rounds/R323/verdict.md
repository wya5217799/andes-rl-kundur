---
round: R323
---
# R323 verdict - platform causality blocked and model fidelity qualified

**Date**: 2026-08-03
**Status**: completed - MODEL-FIDELITY-QUALIFIED
**Type**: official-source and installed-source decision audit
**Wall**: ~1h

## TL;DR

R323 blocks direct attribution of the model-only R321/R322 failures to ANDES,
finds no contradiction in the checked interface semantics, and requires one
parameter-provenance and time-step-convergence gate before Q-0078.

## Questions opened (this round)
- Q-0079 - bind material plant/execution parameters to sources or explicit
  assumptions and test frozen open-loop pulse convergence across time steps.

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0078 - remains open but is conditional on Q-0079; no controller candidate
  is formed in R323.

Feed: `paper/decoupling_marl_model_first/reports/R323.md`

## 给 PI 的话

**发生了什么**：我们按官方说明和实际安装内容核对了计算平台、单位、正负方向和充放电过程，并重跑了能够发现这些错位的现有检查。没有发现单位、方向或充放电写反。前两次失败也没有直接调用电网仿真，因此不能把失败归咎于平台不够精细。

**这说明什么**：当前平台确实不负责非常快速的设备内部过程，但一次处理许多量只是计算方式，不等于天生算不准。现在更可信的风险是，若干关键数字为什么这样取还没有完整依据，最快变化是否算得足够细也没有验证。因此数学建模不能说已经错了，也不能说已经完全可靠。

**下一步做什么**：先暂停设计新的控制办法，把每个关键数字的来源补齐，再用同一个小扰动比较逐步加细后的计算结果。相邻两次结果都在事先规定的差距内，才回到控制设计；否则先重建并复查模型。本次范围内的检查都通过，但整套工程检查仍被另外两份旧论文文件不同步挡住，我没有跨范围改动它们。论文题目不变，暂时不训练多个控制单元。
