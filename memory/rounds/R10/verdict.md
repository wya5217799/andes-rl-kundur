# R10 — Governor Wiring Forensic (verdict)

> ⚠⚠⚠ **DT-BUG CAVEAT (2026-05-07 后发现)** ⚠⚠⚠
> 本 verdict 内全部 trace 数字 (max_df, final_df, settling) 是在 **0.6s/step** DT bug 下测的, paper-faithful 是 0.2s/step. 实际 30 step trace 跑了 18s 而不是 6s.
> **L1/L2/L3 layer pass/fail 结论仍有效** (DAE-active heuristic 跟 DT 无关), 但**绝对量级数字 paper 比对全部 invalid**, 必须用修后 base_env (`current_t = float(self.ss.dae.t)`) 重测才能 anchor paper.
> 修法: `env/andes/base_env.py` step() 内 `current_t = self.ss.dae.t` → `current_t = float(self.ss.dae.t)`. 一行改动.
> 重测命令: 修后跑 `scripts/research_loop/r10_governor_wiring_forensic.py` 重新生成 results JSON.


**Date**: 2026-05-07
**Phase**: ANDES path closure follow-up — Root #2 deep-dive forensic
**Wall**: ~15 min (script + 2 runs + introspection)
**Status**: ⚠ **Root #2 升级 — IEEEG1 整个模型未被 ANDES DAE 激活, 不只是 Pgv→Pm 链路断**
**Trigger**: 用户提"针对不同方向最小可行性验证并行" 原则, 选 C (双轨), ANDES 轨跑方向 1 governor wiring forensic
**Probe script**: `scripts/research_loop/r10_governor_wiring_forensic.py`
**Output**: `results/research_loop/r10_governor_wiring_forensic.json`

---

## TL;DR (1 段)

R08 finding (V3 governor 没生效) 升级: 不仅 Pgv→Pm 链路断, IEEEG1 **整个模型在 ANDES DAE 里就是死的**. 静态 `_build_system` 里 `IEEEG1.add()` 添加成功 (n=4, syn=[1,2,3,4] 跟 GENROU.idx=[1,2,3,4] 完美对齐), 但 introspection 显示 IEEEG1 **0 个 Algeb / State 字段**, 只有 NumParam (常数) + IdxParam (拓扑映射). 对比 GENROU 有 Id/Iq/Pe/Qe 全套 Algeb. 即 IEEEG1 被加进 `ss` 后 `ss.setup()` 在 `except: pass` 里被吞掉, **fatal error 丢失**, IEEEG1 没 integrate 进 ANDES DAE solver. V2 vs V3 GENROU.Pm 轨迹**完全相同到小数点后 13 位** (差 = 0.0, 不是 ~0), max_df 也完全相同 (0.5580468747419118 = 0.5580468747419118). 修法仍是 ANDES 重 build (先 add 模型再 setup, 不是 setup 后再 add), 但**修了也不能 reach paper**因为 Root #3 平台 2× 残差仍在.

---

## 4-Layer Forensic Probe Design

| Layer | 测什么 | PASS 含义 |
|---|---|---|
| L1 静态 | IEEEG1.syn 是否对齐 GENROU.idx | 拓扑链路字段对 |
| L2 动态 | IEEEG1 内部 .v 字段 (pout/Pgv/Pmech/tm) 是否随时间变化 | governor 内部状态被 solve |
| L3 动态 | GENROU.Pm.v 是否随 disturbance 移动 | governor 的 effort 进了 swing equation |
| L4 比对 | V3 (gov on) GENROU.Pm 轨迹 vs V2 (no gov) Pm 轨迹差异 | governor 实质改了机械功率输入 |
| L0 比对 | V3 max_df vs V2 max_df 差异百分比 | governor 的物理可见效果 |

---

## 实测结果

```
=== R10 Governor Wiring Forensic (LS1 PQ_Bus14 -2.48 sys_pu, H=6.5, no SAC) ===

[L1 静态]
  V3 ieeeg1_n         = 4
  V3 ieeeg1_syn       = [1, 2, 3, 4]
  V3 genrou_idx       = [1, 2, 3, 4]
  V3 L1_pass          = True ✓

[L2/L3/L4 动态, 30 step LS1 zero-action]
  V2 max_df          = 0.5580468747419118
  V3 max_df          = 0.5580468747419118     ← 完全相同 (小数点后 13 位)
  V2 pm_max_dev      = 0.6354524601075688
  V3 pm_max_dev      = 0.6354524601075688     ← 完全相同
  V3 pgv_attr_used   = None                    ← IEEEG1 没有任何可读 .v 字段
  V3 L2_pass         = None (Pgv 字段不存在)
  V3 L3_pass         = True (Pm 移动)
  L4_pass            = False (V3-V2 Pm dev diff = 0.0)
  L0 max_df gov effect = 0.0%
```

### IEEEG1 introspection (V3, dim=4)

```
24 readable_vars 全部是 NumParam / IdxParam / FlagValue:
  K, K1, K2, K3, K4, K5, K6, K7, K8 (NumParam, governor gain coefficients)
  PMAX, PMIN (NumParam, output limits)
  T1-T7, Tn (NumParam, time constants)
  UC, UO (NumParam, valve rate limits)
  syn (IdxParam, [1,2,3,4] 对应 GENROU)
  u (NumParam, on/off flag)
  wref0 (NumParam, speed reference)
  zsyn2 (FlagValue)

❌ 0 个 Algeb (代数变量)
❌ 0 个 State (状态变量)
❌ 0 个 ExtAlgeb / ExtState (外部链接变量, 即 vout 接 GENROU.Pm 的链路)
```

### GENROU introspection (对照, dim=4)

```
top readable_vars 包含完整 Algeb 集:
  Id, Iq (Algeb, 同步坐标系电流)
  Pe, Qe (Algeb, 电磁有功/无功)
  Pm (Algeb, 机械功率) ← 应被 IEEEG1 vout 驱动
  M, D (NumParam, 惯量 / 阻尼)
  ...
```

---

## Verdict: Root #2 升级诊断

### R08 原诊断 (handoff 2026-05-07 §Root #2)
> "ANDES IEEEG1 模型默认 syn= 字段不自动 wire 到 GENROU 的 Pm input, 需手动设."

### R10 修正 / 升级
**不只是 Pgv→Pm 没接, 而是 IEEEG1 整个模型在 DAE 里没激活**:
1. L1 PASS → `IEEEG1.add(syn=...)` 静态执行成功, idx 对齐
2. **L2 字段缺失** → IEEEG1 在 `ss` 里只有 NumParam, 没有 Algeb/State, 即 **ANDES 没把 IEEEG1 编译进 DAE 方程组**
3. **L3 PASS 但 L4 FAIL** → GENROU.Pm 移动是 GENCLS swing equation 自带的反应 (V2 也有, V2 没 governor), 不是 IEEEG1 给的
4. **V2/V3 Pm 轨迹完全相同** (差 = 0.0 而不是 ~0) → **IEEEG1 在 TDS 里就是个被 ANDES 完全无视的孤立对象**

### 根因猜测
`env/andes/andes_vsg_env_v3.py::_build_system`:
```python
ss = super()._build_system()  # ← V2 base 已 ss.setup(), DAE 已 compile
for syn_idx in ss.GENROU.idx.v:
    ss.IEEEG1.add(idx=..., syn=syn_idx)
    ss.EXST1.add(idx=..., syn=syn_idx)
try:
    ss.setup()                # ← 重 setup 在已 setup 的 ss 上抛 fatal
except Exception:
    pass                       # ← 吞掉, 但 IEEEG1 没 compile 进 DAE
```

ANDES 不允许 `setup()` 后再 `.add()` 新模型. 必须 add 顺序 = `add → setup` 一次性, 不能 add → setup → add → setup.

### 修法 (若未来重启 ANDES path, 仍不推荐)
1. 不在 V2 base 里调 `ss.setup()`, 改成 build_after_addons 钩子模式
2. 或 V3 自己 `ss = andes.System()` 重头 build, 一次性 add GENROU + IEEEG1 + EXST1 再 `ss.setup()`
3. 或用 ANDES 提供的 `.alter()` 接口 (如果有)

**但**: 修对了 governor 后, R08 Root #3 平台 2× 残差 (H=300 paper 上限 max_df 仍 2× paper) 仍在, 仍不能 reach paper Fig.7/9 视觉对齐. ANDES path closure decision 不变.

---

## 价值

### 即时价值 (verdict-level)
1. **R08 Root #2 从"猜测"升级为"实测确认 + 更深诊断"**: handoff 文档需更新 Root #2 描述
2. **paper Appendix B 学术诚实材料**: cross-platform validation negative finding 现在有 hard evidence (introspection 数据 + 完全相同的轨迹), 不是定性描述
3. **R03 smoke probe 局限暴露**: R03 只验 "no crash", **报 PASS 不代表生效**. 这是 R08 已识别的 lesson, R10 forensic probe 给出可复用的 forensic 模板
4. **eval/probe 方法论 lesson 锁定**: "model 加进 ss" ≠ "model 在 DAE 里 active". 通用判据 = `model_introspect()` 看是否有 Algeb/State 字段, 不能只看 `model.n` 和 `model.idx`

### 复用候选
- `introspect_model(ss, model_name)` + `_try_read_v(model, attr_candidates)` 两个函数是 **任何 "ANDES 加了模型生效了吗" 问题的通用工具**, 应提到 utility 层
- 适用范围: IEEEG1, EXST1, ESST3A, TGOV1, AVR, PSS, DC line, 任何 ANDES TurbineGov / Exciter / Stabilizer 模型

---

## 下一步 / 决策点

R10 verdict 已锁, 三选一:
- **A** R10 留独立 script (verdict 已拿到), 不复用 — 最小可行性 ✓
- **B** 重构成 `probes/kundur/andes_model_state/` 跟 agent_state 平级 (~30 min): 5 phase L0-L4, ProbeThresholds + REPORT.md
- **C** 中间方案: 把 `introspect_model` + `_try_read_v` 提到 `probes/andes_common/utils.py` (~10 min), R10 留 script 引用 utility, 后续 r11+ 复用

推荐 **C** — verdict 已锁不需要 framework, 但 introspection utility 通用价值高.

ANDES path closure 决策 **不变**. R10 是 closure 后的 root cause 闭环, 不是重启 ANDES.

---

## 文件 / 引用

- 探针: `scripts/research_loop/r10_governor_wiring_forensic.py`
- 输出: `results/research_loop/r10_governor_wiring_forensic.json`
- 上游 finding: `quality_reports/research_loop/round_08_verdict.md` §2 Finding 3 (governor wiring)
- ANDES closure 文档 (待更新): `quality_reports/handoff/2026-05-07_andes_path_closure.md` §Root #2
- R03 smoke probe (对照): `scripts/research_loop/r03_governor_wire_probe.py`

---

*Generated 2026-05-07, verdict locked from r10_governor_wiring_forensic.json.*


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
