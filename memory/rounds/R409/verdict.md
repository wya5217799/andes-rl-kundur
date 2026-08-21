# R409 verdict — held-out gate for the R408 candidate: HELDOUT-PASS

**Date**: 2026-08-15
**Status**: completed — HELDOUT-PASS
**Type**: experiment
**Wall**: ~2 min formal execution (30 held-out records, 8 workers)

## TL;DR

R409 validly completes all 30 held-out records with zero guard errors and
finds the frozen 0.4 Hz ring-edge bandpass at K=3.5 passing both frozen
endpoints on the unseen evaluation bank (r_d 0.938218, r_cross 0.793730,
strict cross gate passing), confirming that the R408 constructive Q-entry
candidate generalizes to held-out data.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R409.md`

## 给 PI 的话

**发生了什么**：按上一轮预注册的规则，我们把上一轮找到的那个控制方案（强度三点五的带通阻尼环节）拿到一组从未用过的检验数据上复验，一共三十条完整仿真记录。结果两个核心指标全部达标（差异能量为基准的九成四，交叉串扰为七成九），所有保护与有效性检查全部通过。

**这说明什么**：上一轮的结果不是"碰巧在这批数据上有效"——在全新的数据上同样达标，说明这个控制方案真的把问题解决了。至此，整个求解任务的目标已经达成：我们找到了一个确定性的、只用本机与两个邻居信息的控制办法，能在同一套及格线下同时压低两个核心指标，并且通过了未见数据的检验。

**下一步做什么**：按线路既定约定，这个已验证的结果现在具备进入论文正文的资格，但论文层面怎么用、投哪里，需要由你（线路负责人）单独决定；同时线路导航与资产登记已全部更新完毕。

## 技术路径

- 下一动作: owner 决定论文/title 使用（非学习路线已验证候选）。
- 归档: r409_heldout_gate 四件套, 均已 sha256。
- 后续 scratch: 无（V2 问题集已闭环; MARL 路线保持关闭）。
