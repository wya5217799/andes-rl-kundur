---
round: R80
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R80 Plan — V5 env REGCA1 plant 升级 + 阶梯实验

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: handoff `2026-05-18 R79 launch + REGCA1 audit` + grill 11 轮 (本次对话)
**ADRs**: ADR-0004 (V5 paper-deviation framing) + ADR-0005 (ANDES-only)

---

## TL;DR

V4 plant 把 G4 (Bus 11) 和 W2 (Bus 8) 用 GENROU+H=0 / GENCLS M=0.1 假风机近似。
本轮新建 V5 env 把两个 plant 风机一起换成 ANDES REGCA1 (+REECA1 if needed)，
与 V4 并存。**Framing 是 ANDES 侧 plant 颗粒度工程升级，paper-deviation**。
按 C3→C2→C1→C4 阶梯实验，每阶段有 stopping rule。

---

## 立论 (grill 共识)

paper Sec.II line 259-263 显式声明 "this paper mainly studies the relatively
slow dynamics of the electromechanical transient. Therefore, the dynamics of
the inner loop can be neglected." → REGCA1 (带 PE current 内环 + LVRT + 限幅)
**比 GENCLS M=0.1 离 paper Sec.II 声明更远**。"REGCA1 = paper-faithful"
立论作废。

paper Sec.IV-A 关于风机模型的全部信息 = "wind farm with same capacity" +
"100 MW wind farm at bus 8"，**未指定** dynamic model。"对齐 paper 风机"
无文字支撑。

所以 V5 framing = ANDES 工程升级 (ADR-0004)，不假装 paper-faithful。

---

## 阶梯实验 + Stopping Rules

```
Phase 0 (probe, ~15 min, Windows-side write + WSL python run)
  ├─ scripts/r80_regca1_wire_check.py
  ├─ load kundur_full.xlsx → add REGCA1 @ Bus 8 + Bus 11
  ├─ try ss.PFlow.run() + ss.TDS.run() 1 step
  ├─ output: probes/r80_regca1_wire_check.json
  └─ GATE A:
     ├─ pflow + 1-step TDS PASS → 进 Phase 1
     ├─ FAIL → 写 CLM "ANDES REGCA1 不可用 on Kundur", 关 R80

Phase 1 (V5 scaffold, ~半天, Windows-side write + WSL pytest)
  ├─ src/andes_rl_kundur/env/andes/v5_config.py (复制 V4Config + REGCA1 toggle)
  ├─ src/andes_rl_kundur/env/andes/andes_vsg_env_v5.py (override _build_system)
  ├─ tests/test_v5_env_regression.py (新 baseline JSON for V5)
  └─ GATE B:
     ├─ tests/test_v4_env_regression.py 必须 1e-9 仍 PASS → 进 Phase A
     ├─ FAIL (V4 被无意污染) → revert V5 文件, 关 R80, 写 CLM "scaffold 破 V4"

Phase A (zero-action sanity, ~30 min)
  ├─ probes/r80_v5_zero_action.py
  ├─ V5 env + zero action + LS1/LS2 anchor 扰动
  ├─ record max_df / final_df / settling / cum_rf / Δ vs V4 zero-action
  └─ NO HARD GATE — paper 沉默 framing 下无标准
     ├─ max_df 落入 [0.20, 0.30] (V4 物理上限附近) → 预期, 继续 Phase B
     ├─ max_df < 0.20 → 意外低 (signal!), 继续 Phase B
     ├─ max_df > 0.30 → REGCA1 让 plant 更激进, 仍继续 Phase B (有 signal)
     └─ DIVERGE → 退回 Phase 1 检查 wire

Phase B ⭐ KEY GATE (C3 cross-eval, ~半天)
  ├─ scripts/r80_v5_cross_eval.py
  ├─ 拿 V4-trained SOTA ckpt (R75 / R57 / R72) 直接在 V5 plant 上 eval
  ├─ run paper_grade_axes ranker on output JSON
  └─ GATE C:
     ├─ 6-axis ≥ V4 baseline + 0.05 (plant 升级有杠杆) → 进 Phase C
     ├─ 6-axis ∈ [V4 - 0.05, V4 + 0.05] → C4 negative finding 收尾,
     │   写 CLM "V5 plant 升级对 V4-trained agent 无显著 transfer 影响"
     │   关 R80
     └─ 6-axis < V4 - 0.05 → V5 plant 让 V4 ckpt 更差 (有信号但反向),
         仍进 Phase C 看重训能否补回

Phase C (C2 1-seed smoke train, ~1-2 day wall, WSL python train)
  ├─ V5 env + R75 hyper (LSTM tau=0.001 warmup=20) + 1 seed (s59)
  ├─ 75 ep smoke (paper 的 500 ep 完整训练太贵, 先小)
  ├─ output: results/r80_v5_smoke_s59/
  └─ GATE D:
     ├─ attractor > V4 multi-seed attractor 0.137 → 进 Phase D (C1)
     ├─ ≤ 0.137 但 ≥ 0.10 → C4 negative finding (V5 没破 plateau)
     └─ < 0.10 → C4 negative finding (V5 更差), 关 R80

Phase D (C1 multi-seed, ~3-5 day, 只在 Phase C 触发, 可能分到 R81+)
  └─ V5 + 5 seed × 500 ep → 试图 main result. 不在本轮 commit, 看 Phase C 信号
```

---

## 资产保护契约 (硬约束)

不动:
- `src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py`
- `src/andes_rl_kundur/env/andes/v4_config.py`
- `src/andes_rl_kundur/env/andes/base_env.py`
- `src/andes_rl_kundur/env/andes/andes_vsg_env_v{1,2,3}.py`
- `src/andes_rl_kundur/evaluation/paper_grade_axes.py` (Asset 4)
- `tests/test_v4_env_regression.py` (Phase 1 GATE B 监控)
- `results/r57_*`, `r68_*`, `r72_*`, `r75_*`, `r79_*`
- WSL R79 训练进程 (handoff 标注 PID 388, ~01:00 完成)

新建:
- `docs/adr/0004-v5-env-regca1-plant-paper-deviation.md` ✅
- `docs/adr/0005-andes-only-drop-simulink-1to1.md` ✅
- `src/andes_rl_kundur/env/andes/v5_config.py`
- `src/andes_rl_kundur/env/andes/andes_vsg_env_v5.py`
- `tests/test_v5_env_regression.py`
- `scripts/r80_regca1_wire_check.py`
- `scripts/r80_v5_cross_eval.py`
- `probes/r80_regca1_wire_check.json`
- `probes/r80_v5_zero_action.json`
- `results/r80_v5_smoke_s59/` (Phase C trigger)

---

## Questions opened (this round, anticipated)

- Q-pending: "REGCA1 in ANDES 需要 REECA1 配套吗" — Phase 0 答
- Q-pending: "G4+W2 一起升级后 V4-trained agent transfer 能力" — Phase B 答
- Q-pending: "V5 attractor 是否突破 V4 plateau 0.137" — Phase C 答 (or 留给 R81+)

## Claim 候选 (按阶梯结果)

- CLM-NEW (Phase 0 NO-GO): "ANDES REGCA1 不可在 Kundur 直接 wire" — type=finding, trust=V
- CLM-NEW (Phase B C4): "V5 plant 升级对 V4-trained agent transfer 无显著影响" — finding, V
- CLM-NEW (Phase C C2): "V5 plant 升级后 1-seed attractor = X vs V4 0.137" — finding, V
- CLM-NEW (Phase C C1 trigger): "V5 plant 突破 V4 plateau, 启动 R81 multi-seed" — decision, S
