# R400 verdict — same-line CD-MATD3 training-route amendment

**Date**: 2026-08-15
**Status**: completed
**Type**: decision

## TL;DR

R400 prospectively amends the existing fixed-title line without reclassifying
R399.  CD-MATD3 remains the only proposed learner; the only next eligible
evidence action is a separately frozen three-seed development canary, while
R400 itself runs no learner or simulator.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R400.md`

## 给 PI 的话

**发生了什么**：我们已经把最初商量的方案正式写回这篇论文的路线中。每台设备仍由自己的学习程序调节两个参数，改进方法保持不变，强常规办法改为正式对手，不再用来提前取消训练。本轮只完成路线修订，没有运行仿真或训练。

**这说明什么**：后续工作不会再换题、换控制对象或临时寻找别的学习方法。论文要回答的仍是同一个问题：加入整体变化和设备间差异的协调目标后，这套学习程序能否比原始学习办法和强常规办法表现更好。

**下一步做什么**：下一轮只做小规模训练，分别比较基础学习办法、没有邻居信息的改进办法和使用邻居信息的完整办法。结果有一致的正面方向才扩大测试；如果失败，就停止这个改进方法，不再临时换算法补救。
