# R401 verdict — Gate A three-seed canary contract frozen and sealed

**Date**: 2026-08-15
**Status**: completed
**Type**: decision

## TL;DR

R401 freezes and seals the complete Gate A three-seed development canary
contract and the measured host capacity budget, without running any training
or evaluation. The successor round may now execute exactly the three
registered learning arms on seeds 401/402/403 under that seal.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R401.md`

## 给 PI 的话

**发生了什么**：这一轮把下次小规模训练需要的一切条件提前写死并封存：训练
场景、全新考核场景、每台设备的动作范围、步长、奖励计算公式、训练总量、
模型规模、失败重启规则，以及判定成败的标准，全部变成不可更改的正式契约。
同时在真实计算环境里实测了并行上限，确认了安全的同时工作进程数量，并据此
估算了完成全部训练和考核所需的时间。本轮没有训练任何模型，也没有使用任何
历史训练结果。

**这说明什么**：训练路线已经从头到尾固定，下一次运行只能按契约训练三种
配置、每种三套随机起点，不能再临时更换方法或放宽标准。契约同时写明：如果
这次小规模训练不达标，这个改进方法就到此为止，不做任何补救式替换；只有
出现一致的正面方向，才允许进入更大规模的正式对比。

**下一步做什么**：下一轮按封存的契约执行这次小规模训练和考核，全部用全新
的考核场景给出结论。通过小规模验证后，再单独冻结一轮更大规模、更多随机
起点的正式对比；任何一步失败都按契约停止，不靠调整标准硬凑。

