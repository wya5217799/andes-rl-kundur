# R365 verdict — per-VSG object and action-authority gate

**Date**: 2026-08-12
**Status**: completed
**Type**: evidence
**Wall**: ~2h

## TL;DR

The sealed eight-arm V4 intervention returns
`PER-VSG-OBJECT-GATE-PASS`: all four physical proxy units map one-to-one to
runtime actors, the complete M/D action map is independently addressable, the
declared no-delay local-neighbour information reconstructs exactly, the
registered mismatch has an above-noise differential transient, and each actor
has network-transmitted parameter authority.  Q-0101 closes positive under
CLM-0975, but the 50/60-Hz normalization and storage-feasibility contracts must
be resolved before a deterministic controller comparison; training remains
unauthorized.

## Questions opened (this round)
- Q-0101 (per-VSG object, information, differential-dynamics, and action-authority gate)

## Questions closed (this round)
- Q-0101 closed-positive by CLM-0975 (all registered prerequisite gates pass on the sealed V4 proxy)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R365.md`

## Technical disposition

- The active fixed-title line advances from object gating to a unit/actuator
  contract and strong deterministic-baseline design gate.
- Direct per-VSG M/D MARL remains the selected learning architecture, but no
  training becomes eligible until the next deterministic and learning-question
  gates pass.
- Controller performance, decoupling improvement, coordination value, MARL
  value, stability, safety, robustness, topology generalization, storage
  feasibility, and hardware validity remain untested.

## 给 PI 的话

**发生了什么**：四台设备现在确实分别对应四个控制主体，每台设备的两个参数都能被单独改变；每个主体看到的也确实只是自己和相邻设备在当前时刻的信息。人为制造设备参数和扰动分布不一致后，设备之间出现了明显的不同步动态；单独改变任意一台设备，也都会通过网络影响其他设备。

**这说明什么**：新路线最基础的实验对象终于成立了，过去“训练对象和论文对象不是同一个东西”的问题在这一关没有重现。但这只证明对象和控制接口可用，还没有证明任何控制方法更好，也没有证明设备的能量约束、长期安全或实际硬件可行。

**下一步做什么**：先统一仿真系统与控制输入采用的频率尺度，并明确这篇文章只研究参数调节还是还要加入储能能量限制。随后建立一个权限完全一致的强确定性对照；只有对照完成后仍存在清楚、可检验的学习问题，才允许开始训练。
