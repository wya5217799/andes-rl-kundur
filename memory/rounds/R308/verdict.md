# R308 verdict — strict dynamic residuals but invalid initialization

**Date**: 2026-08-03
**Status**: completed — INVALID-TDS-CANARY
**Type**: experiment
**Wall**: ~1h

## TL;DR

R308 is INVALID-TDS-CANARY. The one frozen strict Newton tolerance drove both sampled dynamic traces far below the unchanged algebraic-residual gate, but it also made ANDES reject TDS initialization and retain exit code 1. No Stage 1, controller, or training gate opens.

## Questions opened (this round)
- Q-0065 — test one explicit default-initialization to strict-dynamic solver transition on the same two traces.

## Questions closed (this round)
- Q-0064 — closed-negative by CLM-0750; the one-global-tolerance canary did not pass execution validity.

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

**这周干了啥**：把 R307 的求解器问题压缩成两条轨迹，只试了一个提前封存的 `1e-10` Newton 容差，并跑了独立 eval。

**结果（一句话）**：动态阶段的 `max|g|` 最坏降到 `3.59e-13`，但同一个严容差让两条轨迹的 TDS 初始化都失败、exit code 都是 1，所以正式结论仍是 INVALID。

**意外**：问题已经进一步解耦——动态 Newton 精度能满足 `1e-8` 门槛，失败发生在更早的初始化验收；不能因为后段残差漂亮就把它算成有效证据。

**我默认下一步做**：保持 plant、pulse、时域、`1e-10` 动态容差和 `1e-8` 残差门槛不变，只把初始化默认容差与控制后动态容差显式分开，再跑同样两条 canary；仍不跑完整 Stage 1，不做控制器和训练。

**你想插一脚就说**：如果你希望现在就停止 solver 路线，或先把会议题目改成不含 `Decoupling-Oriented` / `Multi-Agent Reinforcement Learning` 的保守占位名，可以改方向；否则我按 Q-0065 继续这一个小门。

Feed: `paper/decoupling_marl_model_first/reports/R308.md`
