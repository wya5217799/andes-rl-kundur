# R413 verdict — A2 拓扑变体鲁棒性：十个稳健变体全部通过

**Date**: 2026-08-17
**Status**: in-progress
**Type**: experiment
**Wall**: ~2h (含 R412 abort 后的重跑)

## TL;DR

R413 (soft-spot A2 successor) ran the frozen 12-variant topology bank: the
K=3.5 bandpass passes the frozen thresholds and all guards on all 10
EIG-sound variants, the two VSG-tie outage variants fail the EIG hard gate
and are excluded, and the nominal base case reproduces the R408 endpoints
within 7e-7 relative.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R413.md`

## 给 PI 的话

**发生了什么**：我把那台表现最好的控制器放到了十二种电网接线变体上检
验——基准接线、六种线路停运、五种线路阻抗变化。每个变体先做稳定性核
查再计成绩。中途第一次执行有两类变体让计算程序直接崩溃，我按纪律终止
了那一轮，把记录失败的程序路径修好，重新完整跑了一遍。

**这说明什么**：在十种通过稳定性核查的接线变体上，这台控制器全部达
标，最好和最差的差距很小，说明它在开发数据上的成绩不是某一套接线碰巧
给的。另外两种停掉单条源端联络线的变体本身就无法稳定运行，按规则记为
接线不合格、不计入成绩。基准接线的成绩与历史记录几乎完全一致，说明两
次执行环境可靠。

**下一步做什么**：继续计划的下一项——用三块从未见过的条件组合（新扰
动位置与强度、两组转动惯量与阻尼的偏移）再检验这台控制器。之后若时间
允许，扩充确定性规则池看是否还能找到额外余量；最后把三块新证据按门禁
写进论文正文。
