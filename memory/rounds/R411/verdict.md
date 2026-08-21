# R411 verdict — A1 探针幅度阶梯：判负稳健，比值幅度敏感

**Date**: 2026-08-17
**Status**: in-progress
**Type**: experiment
**Wall**: ~1.5h

## TL;DR

R411 (soft-spot A1) ran the 0.5-1.5 probe-amplitude ladder over the R410
frozen checkpoints: CANARY-FAIL at all five amplitudes with the 1.0 anchor
bit-identical to R410, endpoint-ratio magnitudes amplitude-sensitive, and
the negative message increment sign-stable in its operating range.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R411.md`

## 给 PI 的话

**发生了什么**：我把扰动的大小从基准值的一半到一点五倍之间拉开几档，
用同一批已经训练好的控制策略重新跑完全部轨迹。每一档都判负，都通不过
物理护栏；与基准档位的重算逐位一致，连一个字节的偏差都没有。

**这说明什么**：论文的核心定性结论在扰动强度大约三倍的变化范围内站得
住，不依赖当初选的网格；"通信不帮忙、反而更差"的结论在主要区间内方向
稳定，在最严重的档位差得最多（将近八成）。但具体倍数会随扰动强度漂
移，所以论文里的精确数字必须声明是在登记档位下测得的，不能当作与强
度无关的常数。

**下一步做什么**：继续同一计划的下一项——让这台表现最好的控制器在十
余种线路停运与线路阻抗变化下接受检验，每个变体都要先通过稳定性核查再
计成绩。之后是新数据块和规则池扩充两项。训练类的高成本实验留给会后扩
展，不在本夜启动。
