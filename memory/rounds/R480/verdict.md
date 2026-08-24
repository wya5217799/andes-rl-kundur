# R480 verdict — corrected-card H-sensitivity formal bank (R479 resume) completed: OPEN-LOOP-H-SENSITIVE

**Date**: 2026-08-25
**Status**: completed
**Type**: experiment
**Wall**: ~10min (launch + 6 cells + classify/verify)

## TL;DR

R480 re-executed the sealed six-cell zero-action H-sensitivity bank (rule-mandated resume of the interrupted R479 attempt) with all six traces hash-verified and classified OPEN-LOOP-H-SENSITIVE: 6 s peaks move +89.8-92.9% at H0=10 s and -34.3 to -34.6% at H0=300 s versus the H0=100 s anchor, and the high-inertia transient peaks after the 6 s window (30 s peaks 0.1018/0.0767 Hz).

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0112 remains open; neither solved nor closed here.

Feed: `paper/yang_md_decoupling_marl/reports/R480.md`

## 给 PI 的话

**发生了什么**：把上次刚启动就被打断的正式小检验按原样重跑了一遍。六个格子全部跑完,数据核验全部通过,正式判定为"惯性敏感"。

**这说明什么**：系统的裸响应确实随惯性参数大幅变化——惯性调小,频率波动峰值约翻倍;惯性调大,峰值约降三分之一,而且高惯性档的波峰出现在标准六秒观察窗之外,六秒窗口看不见它。也就是说,现有基准设定是敏感的:论文必须加长观察窗,任何"对各档惯性都稳"的说法都必须先在三个档位上重跑真实控制器才成立。

**下一步做什么**：后继路线已定——放弃能量端口的正面结论，先重验论文主线的直接惯量/阻尼实验；这份惯性敏感性结论作为参数设定假设进入重验预案。控制器在三档惯性上的重跑仍保持关闭，等主线门槛过完再定。
