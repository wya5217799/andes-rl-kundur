# R114 verdict — ABANDONED (driver falsified before launch)

**Date**: 2026-05-19
**Status**: ABANDONED — zero compute, zero ckpt, zero WSL slot consumed
**Type**: meta (round closed without experiment)
**Wall**: ~5 min (plan rewrite + audit reconciliation)

## TL;DR

R114 was planned (2026-05-19 morning) to retrain td3_lstm s54 with
`DISABLE_TOGGLER=1` and test whether removing the unintended Line_8
trip at t=2 s breaks the 91-round 0.391 plateau (CLM-0144). Before
WSL slot freed up, R113 (CLM-0215) measured the Toggler effect
directly at the physics level: **+0.9 % average max_df** — not the
30 %+ that would justify a retrain attempt. R114's decision rule
becomes degenerate; the round is abandoned without expending compute.

## What was done

- Reviewed CLM-0215 result against R114's gate thresholds
- Rewrote `R114/plan.md` to mark status ABANDONED + document the
  falsified hypothesis chain
- WSL slot reserved for R114 returns to the pool

## What was NOT done

- No training launched (`results/r114_stdout.log` is 0 bytes, never wrote)
- No `results/r114_toggler_off_s54/` directory created
- No claim emitted (the round produced no new knowledge beyond
  what CLM-0215 already gave)

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none — Q-0025 was closed by CLM-0215 @ R113, before R114 existed)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog): plateau still mysterious. Toggler ruled
  out by R113; warm-h_0 ruled out by R112 (CLM-0204); paper_strict_pure
  ruled out by R103 (CLM-0203); 91-round hyper-grid surveyed by R57-R82.
  Remaining candidates: classical-baseline strengthening (Q-0023
  magnitude-PI), reward perturbation in narrow band ([[CLM-0203]] §4),
  obs augmentation (R83 area-mean exists, untrained at scale).

## 给 PI 的话

**这周干了啥**: 收到全面审查命令. 审完发现 R114 这一轮已经被同一天稍早出的 CLM-0215 (Toggler 净效果 +0.9%) 把 driver hypothesis 提前 falsify 了 — plan 的判定门槛 (geo ≥ 0.45) 在 物理层 < 1% 的扰动差里**不可能**达到. 训练 25 min wall + 1 个 ckpt slot 换不到新信息, 直接 abandon, 不消耗 compute. R114 stdout log 是 0 字节, 没真启动过.

**结果（一句话）**: R114 关闭, **零 compute / 零 ckpt / 零 WSL slot 消耗**, WSL slot 归还 R102 (magnitude-PI grid, Q-0023 还 open, 是 ROI 最高的下一步).

**意外**: (1) R114 plan 和 R113 verdict 同一天写的, 写 plan 的 session 没看到 R113 的 CLM-0215 — 典型 parallel-session race condition. STATE.md 当时不知道 Q-0025 已经被关掉. **render.py 应该跑得更勤**, 不然 plan 会基于 stale oracle 起飞. (2) 91-round 平台原因排查现状: Toggler 排除 (R113), warm-h_0 排除 (R112), paper_strict_pure 排除 (R103), 91-round hyper-grid 已 survey (R57-R82). 剩下的 plateau 候选: classical-baseline 加强 (Q-0023 magnitude-PI), 窄带 reward perturbation (CLM-0203 §4 paper_faithful × PHI_ABS ∈ {25,50,100}), obs 改造 (R83 area-mean infra 在但没大规模 train). 已无明显单点突破候选.

**我默认下一步做**: (1) R114 verdict 本文写完 — 完成. (2) 启动 R102 verdict (从 r102_summary.json W1 数据写出 — Q-0023 magnitude-PI grid 至少 W1 应该已经够回答). (3) 再渲染 STATE.md (这次 R114 abandoned + Q-0022/Q-0024 关闭都进 oracle). (4) 默认沉默继续干, 完全不消耗 ANDES.

**你想插一脚就说**: (a) 想我直接写 R102 verdict 把 Q-0023 close 掉 — 30 min, ROI 高 (现在唯一一个 open 又有部分数据的 Q); (b) 想我重启 R114 但 reframe 成 eval-only (R72_w4 SOTA ckpt 在 Toggler-OFF env 上跑一遍, 3 min wall, 量化"训练-eval 分布漂移"成本) — 信息量比 retrain 小但更便宜; (c) 想我开始写 paper Sec.IV-D 的 "mechanism story" 草稿 (9 个 mechanism CLM 整合, 加 CLM-0204/0215 两个 critical 负面结果作为 "为什么 91-round 都败" 的 anchor) — 60 min, paper-side 工作. **我推荐 (a)**.

## Cross-references

- CLM-0094 R72_w4 SOTA (geo 0.391)
- CLM-0144 91-round algo plateau
- **CLM-0215** (R113 Toggler ablation, this round's executioner)
- CLM-0194 (R110 Toggler audit finding — discovered but not the dominant residual)
- Q-0025 closed-negative @ R113
- memory/rounds/R114/plan.md (rewritten as ABANDONED)
