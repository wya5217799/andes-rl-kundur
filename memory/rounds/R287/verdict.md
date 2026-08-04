# R287 verdict - Q-0046 weak-corridor boundary extension

**Date**: 2026-07-30
**Status**: SURVIVES (valid, 192/192, all guards pass)
**Type**: experiment
**Wall**: ~4h including reboot recovery
**Question**: Q-0046 -> closed-positive by CLM-0650

## TL;DR

Frozen centralized TD3 survives the declared Line_4/5/6 corridor scaling
through k=3.0 on both registered endpoints, with 192/192 complete traces and
all guards passing. Full interpretation and evidence pointers are in
`paper/sci_upgrade_survey/reports/R287.md`.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0046 -> closed-positive by CLM-0650 (`SURVIVES`).

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：把 R286 留下的弱联络线边界继续往外推，但没有重训、没有换控制器、没有挑种子。仍用同一组 24 个封存场景和 q0 加三个集中式 TD3 种子，只把 Line_4/5/6 的电阻、电抗倍率从此前最高 2 倍扩到 2.5 倍和 3 倍，共完成 192 条 ANDES 时域轨迹。

**结果（一句话）**：结果是 `SURVIVES`；在 3 倍走廊阻抗下，同步损失仍改善 19.43% [13.14%, 24.51%]，前三秒区域间 IAE 仍改善 16.85% [9.46%, 23.60%]，分别保留当前名义增益的 79.8% 和 98.9%，而且全部守卫通过。

**意外**：两类收益衰减不同。同步损失收益随走廊继续变弱而明显下降，但快速区域间端点几乎保持不变；这说明我们测到了“仍然存活但开始分化”的边界形状，还没有测到真正的塌缩点。四个扰动位置在 3 倍阻抗下仍全部保持双位数改善，但位置分组只有每组 6 个场景，只能描述，不能称显著。

**我默认下一步停**：关闭 Q-0046 和 R287，不再自动扩大 k、不换第二条走廊、不做弱网重训，也不进入 LaTeX。实验事实只进入 R287 feed、CLM-0650 和必要账本；后续若写 C2，只能使用“单一 Kundur 拓扑、声明式走廊阻抗代理、冻结集中式控制器在 k<=3 范围内存活”的有界表述。

**你想插一脚就说**：如果你认为审稿人一定会追问塌缩点、真实 SCR、故障/保护或第二走廊，需要另开问题并重新预注册；沉默则按当前授权停在实验和 feed，不继续制造文档或实验。

---
Feed: `paper/sci_upgrade_survey/reports/R287.md`; data:
`results/r287_weak_grid_stress/`; claim: CLM-0650.
