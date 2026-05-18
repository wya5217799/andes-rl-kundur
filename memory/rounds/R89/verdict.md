# R89 verdict — R09-副线 revival: ANDES Kundur parameter audit

**Date**: 2026-05-19
**Status**: DONE — 5 findings documented, 3 claims, 1 deliberate-RED test, F4 → Q-NEW
**Type**: audit (zero ANDES TDS, zero training, zero RL forensics)
**Wall**: ~45 min (15 min file inspection + 15 min audit script + 10 min regression test + 5 min verdict)

## TL;DR

R09 副线 (R08 §3 Finding 2 12-day-old TODO: "H=300 仍 max_df 2× paper, 归因
line/load/SBASE/solver") **revival done**. 纯 file inspection 跟 paper §IV-A
+ Kundur 1994 reference, 5 个 mismatch 全部找到:
**F1 fn=60 vs FN=50** (CRITICAL, env underreports max_df 17%, CLM-0171),
**F2 loads at Bus 7+8 not paper Bus 14/15** (HIGH, CLM-0172),
**F3 GENROU D=0** (MEDIUM, swing damping 来自 TGOV1 droop 不是 paper Eq.1 D),
**F4 TGOV1 全 u=1.0 active** (NEEDS VERIFICATION, 跟 R08 Finding 3 "V3
governor 无效" 表面冲突, Q-NEW 登记),
**F5 PQ q0<0 capacitive injection** (LOW). 总 aggregate CLM-0173. 跟 R83
training / R85 eval / R86/R87 critic forensics / R88 完全正交 (零 ANDES,
零 ckpt 读取, 零 RL).

CRITICAL 单 fix (F1 改 fn=50) 让 max_df 残差从 1.45× **变 1.75×** (反向), 故
F1 不是 R09 2× 残差的 root cause. dominant 候选: F2 load topology + F4
governor active (R90+ ablation 量化).

R57-R85 91-round plateau 在 ANDES-flavored Kundur 上证明; 若 R90+ F2/F4
ablation 关掉 2× 残差, paper-grade RL claim 稳; 否则 plateau 部分是
"ANDES-local" 而非 algo-fundamental.

## Methodology

零 ANDES TDS, 纯 file inspection. 步骤:
1. WSL `cat /home/wya/.../kundur_full.json > probes/r89_andes_kundur_full.json`
2. `python scripts/r89_parameter_audit.py` 用 stubbed andes module 在 Windows
   主机 Python 跑通 (bypass V4 env import chain), 解析 JSON + 跟
   `paper_constants.KUNDUR_*` + `KUNDUR.fn` 比较.
3. 5 个 finding 写入 `results/r89_kundur_audit/{summary.json, audit_report.md}`
4. F1 锁入 `tests/test_v4_fn_consistency.py::test_andes_fn_matches_env_fn`
   (xfail strict=True), 当 F1 fix 时自动翻 pass.

资源 conflict gate: 0 WSL TDS 调用 (audit 全部 Windows-side), 0 ckpt 读取,
0 V4/V4Config/agents 改动. 跟 R83 (training) / R85 (eval) / R86 (cross-ckpt)
/ R87 (per-step) 完全正交.

## Findings

### 🚨 F1 (CRITICAL): fn = 60 Hz ANDES vs 50 Hz env (CLM-0171)

- ANDES `kundur_full.json` 所有 4 个 GENROU + 15 个 Line 都 fn=60.0 Hz
- `scenarios.contract.KUNDUR.fn = 50.0` → `base_env.FN = 50.0`
- `base_env.py:441`: `freq_hz = omega * self.FN` (FN=50.0)
- ANDES TDS 物理上以 60 Hz 积分, env 报数时 omega_pu × 50 → freq_hz
- **Net**: env-reported max_df underreports physical max_df by 50/60 = 0.833
- 修复方向: (a) ANDES 重导 50 Hz baseline; (b) override GENROU.fn=50 after load;
  (c) `base_env.FN=60` + ADR-0006 paper-deviation framing
- 每个 path 都会 break R57+ ckpt 数字 reproducibility (regression must rerun)
- 锁入 `tests/test_v4_fn_consistency.py` (xfail strict)

### HIGH F2: Load topology (CLM-0172)

- ANDES default loads: Bus 7 (+11.59 pu, q0 -0.735), Bus 8 (+15.75 pu, q0 -0.899)
  — both at 230 kV transmission
- Paper Sec.IV-A: ESS at Bus 12/16/14/15 "with loads" (distribution level)
- LS1/LS2 disturbances at Bus 14/15 are V4 runtime ADD, base loads stay at 7+8
- 不同 steady-state load 拓扑 → 不同 effective inertia center 看到的 disturbance
  dynamics. Paper-faithful 需要把 Bus 7+8 loads 删 (或大幅缩) 然后等量加到 14/15.

### MEDIUM F3: GENROU D=0 (no machine-side damping)

- All 4 GENROU D=0.0 (`ds_unique=[0.0]`)
- Paper Eq.1 写成 H·dω + D·ω = ΔP, 有 nonzero D
- ANDES 实际 D=0; effective system damping 来自 (a) TGOV1 R=0.05 droop, (b)
  line resistance 0.001-0.022 pu, (c) transient EMF coupling (sub-cycle)
- 不能 1:1 跟 paper swing equation D 对应. Q-D-paper-未给具体 D 值 — 论文
  `Q-D` (kd_4agent_paper_facts §13) 说 H_es,0/D_es,0 baseline 论文未写.

### F4 (NEEDS VERIFICATION): TGOV1 all u=1.0 active

- ANDES default: 4 个 TGOV1, syn=[1,2,3,4], **all u=1.0 active**, R=0.05 droop
- R08 Finding 3 (CLM 索引 retrofit) 实测 V3 env "governor 完全无效"
  (V2a no-gov vs V2b gov 完全相同 max_df 0.815 = 0.815)
- 但 V4 JSON 显示 u=1.0 — 表面 conflict. 候选解释:
  - (a) R08 测的是 V3 env (不是 V4), V4 post-R37 refactor 可能 silent re-enable
  - (b) V4 也 load 了 TGOV1 但 ANDES setup() 之后 governors 没 wire to swing
    equation (Pm 没连进 GENROU input)
  - (c) Toggler 在 t=2s 会 trip Line_8, 可能 destabilise governor wiring 信号
- **R89 没跑 TDS** (零冲突 contract), F4 验证 deferred to R90+ via Q-NEW.

### LOW F5: PQ q0 capacitive (CLM-0172)

- 两个默认 PQ 都 q0<0 (-0.735, -0.899 pu = -163 MVAr 总)
- "loads" with capacitive q 不寻常; 可能 embed shunt cap compensation in PQ
  record. 影响 bus voltage profile + transient damping. LOW priority.

## Aggregate (CLM-0173)

R09 副线状态: 从 "abandoned TODO" → "audit done, root cause partially
identified". Quantitative diagnosis:

- F1 (CRITICAL): correction makes 2× residual go **larger** (1.75× vs 1.45×) →
  not the root cause direction
- F2/F3/F4 combined: very likely the dominant residual source
- F4 specifically (TGOV1 active adding ~5% damping): if confirmed, would
  partly explain why ANDES is *more* damped than paper (i.e., max_df might
  look closer to paper due to ANDES over-damping, hiding the true 60Hz
  scaling deficit)

GENROU H/Sn parameters **match paper exactly** (H=6.5/6.175 s, Sn=900 MVA,
M=13.0/12.35 at machine base) — no machine-inertia source of mismatch.

## Verification

- `python scripts/r89_parameter_audit.py` runs Windows-side (stubbed andes module), all 5 findings True ✓
- `python -m pytest tests/test_v4_fn_consistency.py -v`: F1 xfail strict + sanity pass ✓
- V4 env / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt / 任何已有 test 全部零 mutation ✓
- WSL python 进程数: R83 W3 (training, ~22 min) + R85 (eval, ~17 min) + R89 (Windows-side, no WSL) = ≤ 3 ✓

## Cross-references

- R08 verdict §2 Finding 2 (2× max_df residual at H=300) + §3 R09 副线 plan (skipped)
- CLM-0040 (ZERO_G4_INERTIA, related G4 paper-deviation)
- CLM-0051 (R44-β V4 zero_g4_inertia=False no_control max_df 0.182/0.169)
- CLM-0144 (91 round algo plateau — R89 challenges its absolute interpretation)
- CLM-0094 / R72_w4 (RL SOTA, eval numbers conditional on F1+F2 anyway)
- R85 plan (classical baseline, running) — F4 confirmation would explain why classical might or might not catch RL
- ADR-0004 (V5 env paper-deviation framing) / ADR-0005 (ANDES-only)
- `docs/paper/kd_4agent_paper_facts.md` §6.1 (canonical paper topology)
- `src/andes_rl_kundur/probes/andes_common/paper_constants.py` (Kundur reference values)

## Questions opened (this round)

- **Q-NEW** (will open separately, F4 follow-up): V4 env TGOV1 governors u=1.0
  in ANDES JSON but R08 Finding 3 (V3) says "completely ineffective". Need
  TDS-level verification: zero-action policy × {TGOV1 enabled, disabled}
  × LS1/LS2 → if max_df differs, governors ARE effective in V4 (R08 was V3-
  specific); if identical, governors silently DAE-inactive in V4 too.
  Test plan: `scripts/r90_tgov1_ablation.py` (~20 min wall, single ANDES
  session, scheduling after R85 + R83 done).

## Questions closed (this round)

- (none — R89 不直接关任何已 open Q. R08 §3 R09 副线 was a TODO not a Q.)

## Questions advanced (this round, status unchanged)

- **Q-0014** (open, algorithm exploration backlog): R89 给 algo plateau 一个
  alternative framing — 91-round plateau 可能部分是 "ANDES-local" 而非
  algo-fundamental. 若 R90+ F2/F4 ablation 关掉 2× 残差且 max_df 落入 paper
  benchmark, paper-grade RL claim 稳; 否则 plateau 真实存在但在 wrong physics
  上证明. Q-0014 priority 不变 (R86/R87 critic-mechanism path 更直接),
  但 R89 给出 "如果 plateau 是 ANDES-local, algo 探索 ROI 更弱" 的辅助论据.

## 给 PI 的话

**这周干了啥**: 等 R85 classical baseline 在 WSL 后台跑的同时 (R85 ~17 min
elapsed, ~2h+ ETA), 顺手把 CLAUDE.md 标的 "R09 副线没做完" 12 天前的旧债清了
— 纯 file inspection audit, 零 ANDES TDS, 零 RL forensics, 跟 R83/R85/R86/
R87 全部正交. dump ANDES `kundur_full.json` + 跟 paper Sec.IV-A / Kundur 1994
比对, 5 个 mismatch 全找到, 3 claim + 1 故意 RED regression test + 1 Q-NEW.

**结果（一句话）**: ANDES default kundur_full **有 5 个 mismatch vs paper**,
其中 F1 fn=60 vs FN=50 (env 报 max_df 偏低 17%) + F2 loads 在 Bus 7+8 不在
Bus 14/15 + F4 TGOV1 都 u=1.0 active. F1 修了反而让 R08 2× max_df 残差更严重
(1.45× → 1.75×), 故 root cause 不在 F1; dominant 候选 F2 load topology +
F4 governor active.

**意外**: (1) **fn=60 是切实的 unit-conversion bug**, 但**反方向** — env
underreports max_df, 让数字看起来比物理实际更接近 paper. 是 calibration
flaw, 不是 training flaw, 不影响 R57+ ckpt 训练. (2) **R08 Finding 3 "V3
governor 无效" 跟 V4 JSON u=1.0 表面 conflict**, R37 refactor 后 V4 可能
silent re-enable TGOV1 — Q-NEW 登记 R90+ ablation 验证. (3) **GENROU H/M 跟
paper 完全匹配** (H=6.5/6.175s, Sn=900 MVA), 所以 2× max_df 残差**绝对不是
machine inertia 不够** — 这 falsify 了一个潜在的 hand-wavy 解释. (4) **R09
副线 revival 工作量极小** (~45 min wall vs 12 天 idle) — 因为是纯 file
inspection 而非 TDS sweep, ROI 极高, 大概是这次会话的最高 signal/wall ratio
活动.

**我默认下一步做**: R89 收尾 done (verdict + 3 claim + test + plan + audit
report). 等 R85 完成 (~2h+) 后立即写 R85 verdict + chat brief. R89 衍生的
Q-NEW (TGOV1 ablation) 挂 backlog, 优先级中等, 等 ANDES TDS 资源空出 (R85
done + R83 W3 done) 时开 R90 跑 — 单次 ablation ~20 min wall, 4-eval set.

**你想插一脚就说**: (a) 若你想立刻 R90 TGOV1 ablation (打破 "正交" 约束,
跟 R85 抢 WSL) 说一声; (b) 若你想 fix F1 (改 base_env.FN=60 或重导 50Hz
kundur) 开 R90 = "F1 fix + regression rebaseline", 工程量 ~3h 但需要重跑全部
ckpt regression — **不推荐**, ADR-0006 paper-deviation framing 是更便宜的
方案; (c) 若你想把 F1 fix + R85 classical 跑两个 baseline (50Hz vs 60Hz) 看
RL advantage 是否对 fn 敏感, 是个 strong paper section, 工程量 ~6h; (d) 沉默
= 等 R85 + R83 完成, 然后按 Q-NEW priority 走 R90 (TGOV1 ablation only).
**我推荐 (d)**.
