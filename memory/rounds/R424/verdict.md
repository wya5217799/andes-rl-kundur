# R424 verdict — 护栏对齐约束轮:约束项符号装反(实现缺陷)、对偶饱和、演员锁死满格动作;消息对比被限幅掩盖

**Date**: 2026-08-17
**Status**: completed
**Type**: experiment
**Wall**: ~2.5h（训练 9 组 ~2h + 评估/分类 ~0.5h）

## TL;DR

R424 added guard-aligned action constraints to the CD actor objective on the unpenalized R419 base, but the sealed learner enters the constraint terms inside the actor-loss negation — gradient descent maximizes the action-energy and TV statistics (gradient probe inner product −97.6 versus the penalty direction), so the dual self-reinforces to the 10.0 ceiling (all 240 retained values; RMS residuals 38.3–90.8x) and both CD actors pin ~90% of action components at the actuator bounds (saturation-budget guard 0->24): CANARY-FAIL with action-stress guards 36/36 unchanged (pre-registered criterion not met) is therefore the implementation-layer manifestation of the R423 constraint-hierarchy diagnosis, not a test of the mechanism as designed. The bang-bang policy yields the family's best common no-harm profile (common-frequency 36->12, RoCoF 22->14, worst-peak 35->24) and drains the common multiplier to 0 in 6/6, while the endpoints regress to 2.3419/1.7751 (R419: 0.6954/0.7104), the message increment collapses to 0.0000 with bit-identical arms (eval files pairwise distinct; slew clip masks the contrast — no verdict on communication value), the critic divergence persists (Q4/Q1 5.98-9.61, threshold 3 not met), and the scalar arm stays byte-identical to R419 (3/3).

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R424.md`

## 给 PI 的话

**发生了什么**：我把动作压力红线的统计量直接写进了训练目标——给动作幅度和动作变化量各配了一个会自动调节大小的权重，其余全部不动，重跑了九个固定预算的学习组，全部完整有效，对照组逐字节一致。结果：安全红线还是没有翻盘，动作压力类红线依旧全部失败；两个学习组的动作很快冲满输出上限然后钉死不动。查原始数据和代码后发现，这次失败不是机制无效，而是实现时把权重的正负号装反了：本该惩罚动作过大的项，变成了违反越多奖励越大，权重自己越涨越高，把动作一路推向满格。

**这说明什么**：这轮真正的结论是——约束机制根本没有按设计跑起来，所以"约束救不了动作压力"这个结论不能下，得等符号改正后重测才算数。但意外收获是真实的：满格动作恰好把频率类红线压到了整个系列最好水平，代价是把之前从未出问题的饱和预算红线打穿、端点明显退步；另外两臂行为完全重合是限幅造成的掩盖，不能解读成通信没有价值。估价网络仍在持续高估，这是当前要修的第一病灶。

**下一步做什么**：下一步先做符号改正后的重测，只改这一个地方，用更短的训练预算加更密的诊断探针来跑，验证约束机制的真实效果；之后再按预注册的选项修估价网络的目标值尺度。两个改动都不大，可以按您定的原则快速推进。
