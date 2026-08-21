# R454 verdict — 零残差主要是目标函数偏好，不是控制能力消失

**Date**: 2026-08-20
**Status**: completed
**Type**: experiment
**Wall**: ~0.5h

## TL;DR

M4 判定为 `IDENTITY-LOCAL-MAX-SUPPORTED-ON-REGISTERED-SLICE`：在登记的
局部方向上，现有奖励函数明确偏好零残差；投影没有压掉动作，更新也没有冻结，
但保存的 critic 梯度只在 4/7 个可比较单元中与真实回报方向一致。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R454.md`

## 给 PI 的话

**发生了什么**：我们围绕“完全不加额外学习控制量”这个点，向四个独立方向做了正负小扰动。所有方向上，奖励都会下降；同时控制接口仍有充足动作余量，保存的网络也能继续更新，并不是动作被系统吃掉或网络彻底卡死。

**这说明什么**：之前学到的额外控制量接近零，主要不能解释成“算法发现了物理上最优的控制”。更直接的解释是，奖励函数对额外动作本身罚得很重，天然把策略推回原有控制器；此外，价值网络对改善方向的判断只有很弱、很临界的一致性，也存在实现层面的质量问题。

**下一步做什么**：继续检查约束乘子为什么长期顶在上限，以及两个评价目标是否需要分别校准价值网络；这些检查必须使用相同数据和预先固定的对照，不能靠重新调参来制造成功结果。
