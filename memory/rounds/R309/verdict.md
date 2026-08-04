# R309 verdict — two-phase TDS canary passed

**Date**: 2026-08-03
**Status**: completed — TWO-PHASE-TDS-CANARY-PASS
**Type**: experiment
**Wall**: ~1h

## TL;DR

R309 passed every registered initialization, one-transition, dynamic residual, exit, timing, input, M/D, and structural guard on the same two traces. A fresh full Stage 1 becomes eligible in a later sealed round; no predictor, controller, or training starts here.

## Questions opened (this round)
- Q-0066 — run a fresh 27-trace Stage-1 bank under the validated two-phase solver contract.

## Questions closed (this round)
- Q-0065 — closed-positive by CLM-0755.

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

**这周干了啥**：把初始化和动态 Newton 两个数值阶段显式拆开，只在初始化成功后切一次 `1e-10` 动态容差，再跑同样的零基线和最坏边脉冲。

**结果（一句话）**：两条轨迹的 10 个 guard 全过，初始化 `test_ok=true`、exit code 全程为 0，动态 `max|g|` 最坏 `3.59e-13`，所以 solver canary 正式 PASS。

**意外**：R308 的失败不是严动态容差本身，而是把一个容差同时用于初始化验收和动态步进；解耦这两个阶段后，不改 plant、pulse、时域和 `1e-8` 门槛就能通过。

**我默认下一步做**：重新封存并从零执行完整 27 条 Stage 1，不复用 R307/R308 轨迹；继续用 EVAL 做边动作执行审计。只有 Stage 1 真通过，才考虑 predictor，仍不做控制器和训练。

**你想插一脚就说**：如果你想先把会议目标或题目进一步收窄，现在可以停在 solver-validity；否则下一步按 Q-0066 回到真正的 signed authority、耦合和分布式边动作证据。

Feed: `paper/decoupling_marl_model_first/reports/R309.md`
