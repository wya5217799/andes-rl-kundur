# R436 verdict — 能量端口锚定残差学习: 无学习增量

**Date**: 2026-08-19
**Status**: completed
**Type**: experiment
**Wall**: ~8h (训练 2.8h + 评估 3x 重跑)

## TL;DR

R436 在已验证的能量端口对象上第一次测学习器（锚定残差 SAC），nominal
锚 bit-identical 复现，两学习臂在全部 10 变体达标但从未超越确定性基线，
分类 NO-LEARNING-INCREMENT。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R436.md`

## 给 PI 的话

**发生了什么**：按计划做了整条线最重要的一次实验——在已经验证有效的
控制结构上，让四台机组各自用强化学习去学"在成熟控制基础上还能补多少"，
并把消息互通的有无也做了对照。训练和全部评估都完成了，结果非常干净。

**这说明什么**：机器学出来的行为几乎完全贴着那个成熟的控制方案走，
十个不同的网络场景下全部及格，但没有一个场景学出了比成熟方案更好的
结果，消息互通也没有带来差别。也就是说：在这套系统上，"让机器学习在
成功结构上再补一刀"这条路，实测没有增量价值——这是把论文里"学习无用"
的结论从失败结构扩展到了成功结构，负结果彻底封顶。

**下一步做什么**：这一环收尾归档；按计划继续剩下的实验环（消息通道
拆解、时变对照、鲁棒性扩展），全部跑完后把结论整合进论文。
