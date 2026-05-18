# R78 verdict — eval pipeline 统一 + train auto-eval (paper §IV-C + 11-axis 默认 on) + final_eval TDD harden

**Date**: 2026-05-18
**Status**: **closed-positive** (11 phases done; 221/221 pytest pass)
**Type**: infrastructure
**Wall**: ~1.5h

## TL;DR

> 用户问 "评估代码杂乱吗，需要整理吗" → "整理, 训练完后不要遗漏 paper 测试 + 六轴测试".
> R78 把 paper-metric (cum_rf §IV-C) + 6-axis geo 收敛到一个 helper
> (`evaluation/summary.py:score_trace_files`), 4 个 eval entry + `train.py`
> 都强制经过它. `train.py --final-eval` 默认 on, 训练结束自动跑.
> 5 个 R-driver 归档. 紧接着 `/tdd` 把 `--final-eval` 私有函数提到 library
> (`evaluation/final_eval.py:pick_final_eval_suffix` + `run_final_eval`)
> 用 DI 注入 score_seed, 8 个 test pin "失败不杀进程" 安全契约 + 4 路 suffix
> 优先级. 221/221 pass (R77 206 + 7 summary + 8 final_eval).

## Methodology

### Phase 1 — Archive 6 round-driver

`git mv` 5 个 `_r{58,69,70,75}_*.py` + 1 个 `_r58_eval_all.sh` 到
`scripts/_archive/round_scripts/`. 与 R01-R36 惯例对齐.

更新 3 个 current claim 的 provenance 路径 (CLM-0071 / CLM-0132 / CLM-0134) 指向归档位置.

更新 3 个 library docstring 中的 path 提示 (`paper_strict_eval.py` /
`ensemble.py` / `aggregation.py`) 标记 archived 状态.

### Phase 2 — 删 `_ensemble_action_fn` alias

R77 verdict 写"删 alias"但 git diff 显示只删了 `ensemble_action` 未用 import,
alias `_ensemble_action_fn = build_ensemble_action_fn` 还在 `eval_ensemble.py:37-39`.
R78 真的删了 + 重写 `tests/test_eval_ensemble_recurrent.py` 用
`from andes_rl_kundur.evaluation.ensemble import build_ensemble_action_fn`
(library 直接导, 不再 `sys.path.insert(0, scripts/)`).

### Phase 3 — `evaluation/summary.py` 单一 helper

新文件 `src/andes_rl_kundur/evaluation/summary.py`:
- `score_trace_files(trace_paths, *, label, is_ddic=True) -> dict`
  - 输入: `{scenario_name: trace_json_path}`
  - 输出 6-key dict: `LS1` / `LS2` / `geo` / `cum_rf` / `cum_rf_LS1` / `cum_rf_LS2`
  - 内部调 `evaluate_trace` + `compute_global_cum_rf` + `floor_geo_mean`
  - PAPER 字典外的 scenario 静默忽略; 空输入 → 全 None (JSON-ready)
- `format_headline(summary) -> str` — 单行 CLI headline (geo + cum_rf, LS1/LS2 拆分)

设计取舍: 读 path (不读 in-memory dict), 因为 `evaluate_trace` 本来就读
文件 + 自动查 sibling `no_control_*.json` 做 axis 8. eval 脚本反正都要
落盘 trace, 直接传 path 最自然.

### Phase 4 — `score_seed` 提升到 library

新文件 `src/andes_rl_kundur/evaluation/score_seed.py` (从 `scripts/score_run.py:score_seed`
搬迁, 逻辑零变化, 仅减少 inline import 并加 `TYPE_CHECKING` V4Config 类型).

`scripts/score_run.py` 改为 `from andes_rl_kundur.evaluation.score_seed import score_seed`
(re-export). `aggregate_scores` 留在 script (CLI-only 用途).

动机: `scripts/train.py` 之前要 `from score_run import score_seed`, 依赖 sys.path[0]
是 scripts/ 的 Python 默认行为, 脆弱. 现在 train.py 直接 `from andes_rl_kundur.evaluation.score_seed`,
clean.

### Phase 5 — 4 个 eval entry 强制 dual-eval (默认)

- `eval_ddic.py`: 跑完 LS1+LS2 → 调 `score_trace_files` → 写 `<label>_summary.json` + headline print. `--no-score` 逃生口.
- `eval_ensemble.py`: 同上.
- `eval_all_seeds.py`: 重写 ranking — 从 `paper_ratio` (max_df 单一维度) 切换到 `geo` (六轴几何平均). 每行同时带 `cum_rf` + `geo` + `LS1/LS2 max_df` (sanity-check). `summary.json` ranking 按 `geo` 降序.
- `score_run.py`: 已在 Phase 4 间接重构 (score_seed 调 summary helper).
- `eval_no_control.py`: 不动 (基线产 trace, axes 6-11 不适用).

### Phase 6 — `train.py --final-eval` 默认 on

- 加 `--final-eval / --no-final-eval` (BooleanOptionalAction, default True).
- 训练 loop + `_save_checkpoint(actor_tag="final")` 之后:
  1. `_pick_final_eval_suffix(save_dir, eval_tracked)` 优先级 `best_eval` > `best` > `final` (R61 Q-0007 路径优先).
  2. `score_seed(save_dir, label=f"final_eval_{save_dir.name}", out_dir=save_dir/"final_eval", suffix=suffix, config=env_config)`.
  3. 写 `<save_dir>/final_eval_summary.json` + 打印 `format_headline`.
  4. **try/except 包**: 失败 → dump 到 `<save_dir>/final_eval_error.txt`, 训练 ckpt 完整保留, 不杀进程.
- ANDES single-session 安全: 训练 loop 每轮 `env.close()`, eval `run_scenario` 自己 build+close.

### Phase 7 — Tests

`tests/test_score_trace_files.py` (新, 7 个 test):
- `test_score_trace_files_dual_eval`: 用 PRE_REFACTOR baseline fixtures, 验 6 key 全 non-None + LS1=0.114101 / LS2=0.077035 bit-identical pre-refactor regression
- `test_score_trace_files_one_scenario_only`: 单 scenario → 另一边 None
- `test_score_trace_files_empty`: 空输入 → 全 None
- `test_score_trace_files_unknown_scenario_ignored`: PAPER 外 scenario 静默丢
- `test_format_headline_handles_full_summary`: headline 包含 geo / cum_rf / LS1 / LS2
- `test_format_headline_handles_none`: None → `--` 占位
- `test_summary_json_serializable`: dict 通过 `json.dumps/loads` 守恒

`tests/test_eval_ensemble_recurrent.py`: 3 个 test 全部改 import `build_ensemble_action_fn`, 删 `sys.path.insert(0, scripts/)` hack.

### Phase 8 — TDD harden `--final-eval` 契约

R78 Phase 6 加的 `train.py:_pick_final_eval_suffix` + `_run_final_eval` 两
私有函数零测试 — 跟 R77 verdict 写"删 alias 但实际没删"是同类风险.
用户 `/tdd` 后, RED→GREEN 8 cycle 把行为契约 pin 死:

| # | 契约 | 函数 |
|---|------|------|
| 1 | `best_eval` 在 + `eval_tracked=True` → 优先选 `"best_eval"` | `pick_final_eval_suffix` |
| 2 | `best_eval` 在但 `eval_tracked=False` → 跳过, 返 `"best"` | `pick_final_eval_suffix` |
| 3 | 只有 `best.pt` → `"best"` (任 `eval_tracked` 值) | `pick_final_eval_suffix` |
| 4 | 只有 `final.pt` → `"final"` (短训练 fallback) | `pick_final_eval_suffix` |
| 5 | 无 ckpt → `None` skip 信号 (不 FileNotFoundError) | `pick_final_eval_suffix` |
| 6 | Happy: ckpt 在 + score_seed 成功 → 写 summary.json + 返 dict | `run_final_eval` |
| 7 | **Load-bearing 安全**: score_seed 抛 → 写 error.txt, 返 `None`, **不外抛** | `run_final_eval` |
| 8 | 无 ckpt skip path: 不调 score_seed, 不写任何 sidecar | `run_final_eval` |

为了让 #6-#8 可测, `run_final_eval` 接 `score_seed_fn` 参数做 DI (default
绑实际 `score_seed`, 测试注入 stub). 测试不需要 ANDES / actor state_dict /
TDS — 全用 `tmp_path` + 空 `agent_i_<suffix>.pt` + stub callable.

Refactor (post-GREEN): `train.py` 删两个 `_` 私有函数, 加薄 `_emit_final_eval`
shim 只管 CLI 打印 (split: 库管逻辑+IO, script 管 human-readable output).

## Verification

- baseline (post-R77): 206 tests
- post Phase 7 (summary): 213 (+7)
- 终态 post Phase 8 (final_eval): **221/221 pass** (+8), 110s wall via WSL `pytest tests/ --timeout=120`
- 6-axis 数值守恒: paper_grade_axes regression `LS1=0.114101 / LS2=0.077035` bit-identical 通过
- V4 env regression 2/2 (1e-9 tolerance) 通过
- `validate.py`: 137 claims / 13 questions / 64 warnings (all pre-existing legacy refs)

## New claims this round

- **CLM-0137** (decision/S) — R78 eval pipeline 整理 + `train.py --final-eval` 默认 on + final_eval TDD harden. SSOT: `evaluation/summary.py:score_trace_files`. `score_seed` + `pick_final_eval_suffix` + `run_final_eval` 全升 library (DI on score_seed_fn). 6 个 R-driver 归档. 221/221 pass.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**: 你问"评估代码乱不乱要不要整"+"训完不要漏 paper 测试和六轴",
我做了一轮 eval pipeline 收口. 现在 4 个 eval 入口 (ddic / ensemble / all_seeds / score_run)
+ train.py 训练结束都强制走同一个 helper, 输出永远是 `paper §IV-C cum_rf + 11-axis geo`
六字段 summary. 5 个 round driver + 1 个 .sh 归档. 紧接着你 `/tdd`, 8 个 RED→GREEN
cycle 把 `--final-eval` 的 4 路 suffix 优先级 + "失败不杀进程" 安全契约 pin 死,
顺手把 train.py 两个私有函数提到 library 让契约可测.

**结果（一句话）**: (1) **新增 `evaluation/summary.py`** 是 dual-eval 的 SSOT, 库级
helper `score_trace_files` 输入 trace JSON path dict, 输出 6 字段 (`LS1` / `LS2` / `geo` /
`cum_rf` / `cum_rf_LS1` / `cum_rf_LS2`); (2) **`score_seed` 提到 library** (`evaluation/score_seed.py`)
方便 train.py 直接调; (3) **`train.py --final-eval` 默认 on**, 训练结束自动跑 LS1+LS2,
失败 dump `final_eval_error.txt` 不杀 ckpt; (4) **`eval_all_seeds.py` ranking 从 `paper_ratio`
切到 `geo`** (六轴几何平均, 项目标准排序), `max_df` 留做 sanity 列; (5) **删 `eval_ensemble.py`
的 `_ensemble_action_fn` alias** (R77 verdict 误述已删, 实际未删), 测试改 import
`build_ensemble_action_fn` from library; (6) **TDD harden**: `pick_final_eval_suffix` +
`run_final_eval` 提到 `evaluation/final_eval.py`, `run_final_eval` 接 `score_seed_fn` 做 DI;
8 个 test 锁 4 路 suffix 优先级 + happy/fail/skip 三路;
(7) **221/221 pytest pass** (206 + 7 summary + 8 final_eval), 6-axis
bit-identical regression (`LS1=0.114101 / LS2=0.077035`) 通过, V4 env 1e-9 regression 通过.

**意外**: (1) **R77 verdict 写"删 alias"但 git diff 只删了未用 import**, alias 真身一直在,
导致 R77 的 "F1 完成" 半真不假 — 本轮真的处理; (2) **`eval_all_seeds.py` 之前用 trace 里的
`cum_rf_total` 排序**, 那是 local r_f (mean over agents), 不是 paper §IV-C global. 历史 ranking
不能直接 cite paper. R78 切到正确的 global `cum_rf` 后, ranking 序可能变, 旧 paper-draft 引用要
重核. **以前的实验结论不变**, 但写论文时 paper-metric 数字得用 R78 这条路径; (3) **`score_seed` 之前
在 `scripts/`**, train.py 想调要靠 Python 默认 sys.path[0]=scripts/ 的脆弱行为, 提到 library 后干净了;
(4) **TDD harden 让一个潜在故事浮出**: R78 Phase 6 加的 `_run_final_eval` 原版本如果实际 score_seed
抛 ValueError (不是 RuntimeError) 也能被 catch 吗? 当时只写了 `except Exception as e`, 测试
pin 死 `Exception` 父类 catch 之后, 这个保证就是契约的一部分了 — 未来谁改成 `except RuntimeError`
会立刻被 test #7 RED. 这是 R77 类型 "verdict 写删了实际没删" 的根本预防.

**我默认下一步**: R78 commit + push (现在测试已经 pin 死契约, commit 比 R77 干净一档).
然后真的进 paper draft. 候选挤优先级:
(a) **paper draft** (推荐 — refactor + TDD 已经三轮, ROI 到顶);
(b) 仍可挤的: 一次 mini 10-ep 训练实跑验 final-eval 端到端 (TDD 已 pin 契约,
    但 ANDES TDS+真 actor 路径没经过 — 集成 smoke 1 次即可);
(c) `paper_grade_axes.py` 内 5 处 inline geo-mean 也改 `floor_geo_mean` (paper-cited, 风险/收益比低, 留给最后).

**你想插一脚就说**: 是 commit + paper 还是先 (b) smoke 验证?
