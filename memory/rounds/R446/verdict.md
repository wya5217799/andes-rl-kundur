# R446 verdict — DAE 一阶权威 B_{u,r} 在同步功率平衡点实测为零

**Status**: completed

## TL;DR

R446 用有限差分 + Schur 折叠实测 Object A 的 DAE 一阶权威通道 B_{u,r}，全部 8 个 M/D 列在平衡点精确为零（ω=1.0、f_ω=1.5e-10、g_y 条件数 1.14e6），证实咨询包命题 P3.2 的结构零预测并把 theory-audit 的"未识别"补成实测结论。乘法式 M/D 反馈在平衡点无加性一阶状态通道，主导效应是二阶（双线性 A(M,D) 调制）。

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R446.md`

## 给 PI 的话

**发生了什么**：我把之前一个悬而未决的问题做成了实测——调节每台机的惯量和阻尼，到底会不会在系统稳定时直接推动系统。我固定住平衡状态，逐个小幅拨动那些控制指令，再按标准公式算出它们对系统的直接推动力。

**这说明什么**：算出来全部是零，而且是一分不差的零。这印证了之前的判断：在稳定平衡点上，调惯量和阻尼不会直接推系统，它的作用是改变系统之后对外界扰动的响应方式。论文里原本写着"这一点还没识别"，现在能改成"已经实测确认"，把一处局限变成了贡献。

**下一步做什么**：这个测量只回答了一道题。剩下的测量和机制实验我继续一道一道做下去，赶得上截止的进论文，赶不上的留作后续。
