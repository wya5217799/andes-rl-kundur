# R350 verdict - residual headroom does not authorize training

**Date**: 2026-08-06
**Status**: completed - NO-TRAINING
**Type**: create-only analysis
**Wall**: <1h

## TL;DR

R350 validly finds only a small nominal outcome-seeing residual direction;
the registered materiality, mismatch, and neighbour-local gates do not pass,
so Q-0091 closes negative and neither a physical residual probe nor neural
training is authorized.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0091 closed-negative by CLM-0915 for the registered residual formulation
  and intended edge-local information path.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/decoupling_marl_model_first/reports/R350.md`

## 给 PI 的话

**发生了什么**：基础控制工作后，我们先计算理想情况下还能改善多少，再检查只看相邻两端当时的信息能不能找到同样有效的动作。理想情况下，两个关键误差还能分别缩小约百分之二和百分之五点一；但只用相邻信息时，第一个只缩小约百分之零点一四，第二个反而增大约百分之十四点一，加入已有偏差后也没有改善。

**这说明什么**：基础控制之后确实还剩一点理想空间，但目前能看到的信息不足以把这点空间稳定变成实际改进，完整要求没有通过。现在直接开始学习，目标不清楚，而且有把原本很小的误差放大的风险。

**下一步做什么**：停止当前训练路线，把基础控制作为这条论文线现阶段最可靠的结果。若仍要保留学习方向，必须先另做一轮不训练的研究，重新检查可见信息和改进目标；只有新的实物检验通过后才重新考虑训练，否则转向整理现有论文证据。
