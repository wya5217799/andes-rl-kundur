# R417 verdict — 反馈环：K=4.0 广度表（轻惯量块差 0.06% 未达线）

**Date**: 2026-08-17
**Status**: in-progress
**Type**: experiment
**Wall**: ~1h

## TL;DR

R417 ran the second disclosed gain K=4.0 on the three A4 unseen blocks:
it passes the conditions and stiff blocks and improves the relaxed block
from r_d 0.9712 to 0.9506, still exceeding the 0.95 ceiling by 0.06%
with every guard passing; both disclosed gains share that block as their
boundary.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R417.md`

## 给 PI 的话

**发生了什么**：我把这台控制器另一个早已公开的更强参数档位，拿到昨晚
三块没见过的新条件上首次检验，并且文献调研确认了这种做法是站得住的
（前提是参数档位在数据评分前就已公开，我们满足）。三块结果全部如实
保留，包括没过的那一块。

**这说明什么**：更强的那一档把"惯量调低、阻尼调高"那块从超线约百分之
二改善到只差万分之六——所有安全与执行检查都通过，纯粹是差分指标差一
丝没进线。这说明该块是这台固定参数控制器两个公开档位的共同边界，不是
某一档的偶然失误；也说明继续换参数档位去试就会变成在测试数据上挑参
数，按纪律这三块从此关闭。

**下一步做什么**：反馈环进入最大的一步——按文献确认的修复方案（把
"上一拍实际执行的动作"补进学习输入、让目标计算与实际执行同一套语义）
重新训练九个固定预算的学习组，约需七小时，看学习方案能不能第一次通过
物理护栏；结果无论翻不翻都按预注册分支处理并更新论文。
