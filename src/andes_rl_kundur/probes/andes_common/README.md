# probes/andes_common — ANDES probe utility 决策树

> 写 ANDES env probe 之前先读这里. R10-R17 反复重写同一套 boilerplate, 抽出来这层. 重新发明 → 数字漂移 + cross-probe verdict 不可比.

**Sibling**: `probes/kundur/probe_state/` (Simulink CVS) / `probes/kundur/agent_state/` (ANDES trained policy diagnostic).

**Scope**: ANDES DAE-level introspection + zero-action 物理 trace + verdict 解析. **不**包含 trained ckpt rollout (那是 `agent_state/`).

---

## 决策树: 我该写 probe 吗?

```
要回答的问题
│
├── "ANDES 加了某 model 生效吗" (governor / AVR / PSS / ...)
│   → 用 introspect_model() 看 readable_vars 里 Algeb/State 数量
│   → 0 = 死了 (R10 IEEEG1 case), > 0 = 在 DAE 里
│
├── "改 env 参数 X 有效吗" (G4 inertia / NEW_LINE_X / VSG_M0 / ...)
│   → 写 r{NN}_X_probe.py 用 run_variant_ablation
│   → 至少 2 variant: default vs paper-faithful (R15/R16 模板)
│
├── "max_df / final_df 跟 paper Fig.6/8 比?"
│   → run_zero_action_trace + paper_constants.PAPER_FIG6
│   → 看 max_df / paper.max_abs_df_Hz, final_df / paper.final_abs_df_Hz
│
├── "H scan 看 inertia 影响"
│   → run_h_scan(env_cls, scenario, H_TEST_POINTS, paper_benchmark=...)
│   → R08/R14 模板
│
├── "训练前先 sanity"
│   → 不写新 probe. 用 r10/r17 当 regression test 跑一遍
│
└── 其他陌生问题
    → 还是先写 r{NN}_*.py probe (10 min) 再改代码 (1 hr)
    → 修代码前 audit, 永远更便宜
```

---

## 何时用哪个 helper

| 任务 | helper |
|---|---|
| 看 ANDES model 是否 DAE-active | `introspect_model(ss, "IEEEG1")` 看 kind ∈ {Algeb, State, ExtAlgeb, ExtState} |
| 找 model 的输出字段 (Pgv / Pm / vout) | `try_read_v(model, ("pout", "Pgv", ...))` |
| 单 episode zero-action 量级 | `run_zero_action_trace(env_cls, LS1_DELTA_U)` |
| H sweep 看 inertia 单调性 | `run_h_scan(env_cls, LS1_DELTA_U, H_TEST_POINTS)` |
| 多 variant 同 scenario 对比 | `run_variant_ablation({"A": {...}, "B": {...}}, ...)` |
| paper-faithful settling 时间 | `compute_settling_time(df_traj, dt=DT, final_df_target=None)` (None 自动取 traj 末值) |
| 多层 gate 分类解析 | `resolve_probe_ladder(results, [ClassificationRule(...), ...])` |

---

## 命名约定

```
scripts/research_loop/r{NN}_{topic}.py             # probe script
results/research_loop/r{NN}_{topic}.json           # probe output
quality_reports/research_loop/round_{NN}_verdict.md # human verdict
```

`{NN}` 单调递增, 不复用. `{topic}` 短描述 (`governor_wiring_forensic`, `root3_g4_inertia`, `pi_ac_residual`, ...).

---

## 标准 probe 结构 (template)

```python
"""R{NN} — {hypothesis statement, 1 句}.

Question: {要 PASS 还是 FAIL 的具体物理 / 软件 hypothesis}
Method: {1 句 描述 — zero-action / H scan / variant ablation / introspect}
Verdict matrix:
  L0_FAIL → ...
  ROOT3_FAKE → ...
  ALL_PASS → ...

Run: /home/wya/andes_venv/bin/python scripts/research_loop/r{NN}_{topic}.py
Output: results/research_loop/r{NN}_{topic}.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from probes.andes_common import (
    LS1_DELTA_U, PAPER_FIG6, H_PAPER_AREA1,
    run_zero_action_trace,
    resolve_probe_ladder, ClassificationRule,
)
from env.andes.andes_vsg_env_v3 import AndesMultiVSGEnvV3


def main() -> int:
    out = run_zero_action_trace(
        AndesMultiVSGEnvV3, LS1_DELTA_U, h_forced=H_PAPER_AREA1, n_steps=30,
    )
    out["paper_ratio"] = (out["max_df"] / PAPER_FIG6.max_abs_df_Hz) if out.get("max_df") else None

    rules = [
        ClassificationRule("PAPER_MATCH", lambda r: r.get("paper_ratio", 99) <= 1.3,
                           lambda r: f"max_df={r['max_df']:.3f} ≈ paper {PAPER_FIG6.max_abs_df_Hz}"),
        ClassificationRule("RESIDUAL", lambda r: True,
                           lambda r: f"max_df={r['max_df']:.3f}, ratio={r['paper_ratio']:.2f}× paper"),
    ]
    classification = resolve_probe_ladder(out, rules)
    out["classification"] = str(classification)
    print(classification)

    p = ROOT / "results" / "research_loop" / "r{NN}_{topic}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 反模式 (不要做)

| ❌ Don't | ✅ Do |
|---|---|
| 在 probe 里硬编码 `LS1 = {"PQ_Bus14": -2.48}` | `from probes.andes_common import LS1_DELTA_U` |
| 在 probe 里硬编码 paper 0.13 数字 | `PAPER_FIG6.max_abs_df_Hz` |
| 在 probe 里重写 30 行 zero-action loop | `run_zero_action_trace(...)` |
| 写 `if elif elif` 分类 | `resolve_probe_ladder(results, rules)` |
| 看 `info["max_df"]` 当 paper 0.13 (transient peak vs settled) | 区分 `max_df` 和 `final_df`, 跟 paper benchmark match |
| 在 probe PASS 后 直接信 governor "active" | introspect → Algeb/State count > 0 才 active |

---

## 当前 utility 状态 (2026-05-07)

| File | LOC | 上线 |
|---|---|---|
| `utils.py` (introspect_model + try_read_v + safe_get) | ~120 | R10 ✓ |
| `paper_constants.py` (LS1/2 + Fig.6/8 + Eq.12 + Kundur H) | ~95 | R10-R17 共用 ✓ |
| `tracers.py` (run_zero_action_trace + run_h_scan + ablation) | ~165 | 2026-05-07 ✓ |
| `verdict.py` (Verdict ladder resolver + 2 factory ladders) | ~140 | 2026-05-07 ✓ |
| `__init__.py` (public API export) | ~80 | 2026-05-07 ✓ |

---

## 上游导航

- 跑 probe 前先读: `docs/eng-notes/NOTES_ANDES.md` "修代码前必读" §
- ANDES 修代码前必 probe: `CLAUDE.md` "修模型前必读 NOTES" §
- Forensic 闭环: `quality_reports/handoff/2026-05-07_andes_path_closure.md` (R10-R17 RE-OPEN)
- 6-axis evaluator: `evaluation/paper_grade_axes.py`
- Paper figure 工具: `paper/figure_scripts/v4_baseline_fig6_8.py` (V4 baseline 模板)

*Generated 2026-05-07 — R10-R17 forensic 沉淀.*
