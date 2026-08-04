# R306 verdict — model-first Stage-0 implementation pass

**Date**: 2026-08-03
**Status**: STAGE0-PASS
**Type**: experiment
**Claim**: CLM-0740
**Question**: Q-0062 -> closed-positive

## TL;DR

The prospectively sealed physical-60-Hz model-first canary passed all 14
implementation guards across five zero-input samples. Q-0062 closes positive,
but Stage 1, controller comparison, and training remain unauthorized.

## Questions opened (this round)

- Q-0062: can the separate model-first seam pass the frozen Stage-0 contract
  without changing legacy V4?

## Questions closed (this round)

- Q-0062 -> closed-positive by CLM-0740: one sealed five-step canary passed all
  registered implementation-validity guards.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：把新论文的模型合同真正落到一条独立的 ANDES 执行路径上，修掉 50/60 Hz、M/D 基准混写、作用矩阵符号和 ESD1 内部读回这些前门问题；历史 V4 没动。

**结果（一句话）**：封存后的 5 步零输入 canary 一次通过 14/14 个守卫，最大 DAE 残差为 2.884e-9，四台 VSG 的实际 M/D 始终精确为系统基准 400/200，功率与 SOC 都无暗漂移。

**意外**：原来的基准混写不是纸面洁癖——旧路径确实会把 setup 后的 400 惯量在首个零动作步写回 200；新路径通过“有功探针期间完全不写 M/D”把这个混淆切断了。

**我默认下一步做**：按本轮停止条件停在 Stage 0，不训练。若继续这条论文线，下一轮只能先封存 Stage 1 的正负有功脉冲，验证真实命令—内部限幅—实际出力—SOC 的符号、带宽和局部线性。

**你想插一脚就说**：如果你想先审代码接口、调整 Stage 1 的三个工作点或收紧物理门槛，现在正是改“下一轮合同”的时点；不能回头改本轮已封存的阈值和结果。

Feed: `paper/decoupling_marl_model_first/reports/R306.md`
