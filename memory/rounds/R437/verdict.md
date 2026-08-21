# R437 verdict — a4_md_relaxed 失败块谱诊断: 通道失配假设被否证

**Date**: 2026-08-19
**Status**: completed
**Type**: analysis
**Wall**: ~1h

## TL;DR

R437 对 R415 失败块做离线谱诊断，0.4Hz 带通通道失配假设被否证（失败块峰值 0.449Hz 仍在 0.3-0.5Hz 窗口内，窗口能量 58.7% 高于通过块），r_d 失败机制未被定位。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R437.md`

## 给 PI 的话

**发生了什么**：能量端口控制器在"惯性变软"的扰动场景下没能达到既定指标，我们怀疑是控制器的滤波通道和该场景的主要振荡频率错开了，于是对上次实验保存下来的全部数据做了频谱分析来验证这个猜测。

**这说明什么**：分析结果否定了这个猜测——失败场景的主要振荡频率并没有跑出滤波通道的范围，反而比通过的场景更靠近通道中心。也就是说，这个场景失败的原因不在"通道和频率错位"，我们还没找到真正的机制，但它至少排除了一条主要嫌疑。

**下一步做什么**：这个失败仍然作为论文里如实记录的边界保留，不再为它专门追加新实验；精力转回主线补充实验（在成功的控制结构上让机器自己学习）。
