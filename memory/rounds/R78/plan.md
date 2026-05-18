# R78 plan — eval pipeline 整理 + 训练完成自动跑论文+六轴

**Date**: 2026-05-18
**Type**: infrastructure
**Wall**: ~1h
**Trigger**: 用户 `对agent的评估代码杂乱吗，需要整理吗` → `整理，我希望以后训练完成评估的时候，把必要的测试论文测试六轴测试都做了，不要遗漏`

## 范围

### 问题诊断

1. **遗漏风险**: 4 个 eval 入口里只有 `score_run.py` 做 dual-eval (paper §IV-C cum_rf + 11-axis geo). `eval_ddic.py`/`eval_ensemble.py`/`eval_no_control.py` 只产 trace, 跑完后**必须**手工再跑 score_run 才有 canonical metric. `eval_all_seeds.py` 用的是 trace 里的 `cum_rf_total` (local r_f), **不是** paper §IV-C 的 global cum_rf.
2. **train.py 训练结束没有自动 eval** (只有 `--eval-every-n-eps` 探针, 默认关闭).
3. **5 个 R-driver 还在 `scripts/` 根**: `_r58/69/70/75_*.py`. 与 R01-R36 归档惯例不一致 (后者已在 `_archive/round_scripts/`).
4. **R77 verdict 误述**: F1 实际只删了 `ensemble_action` 未用 import, `_ensemble_action_fn = build_ensemble_action_fn` alias 仍在 `eval_ensemble.py:39`, 测试 `test_eval_ensemble_recurrent.py` 还在 import 它.

### 范围决策 (用户锁定)

- **训练完成后自动跑 eval**: 加 `--final-eval` flag, **默认 on**.
- **R-driver 归档**: 5 个 `_r{58,69,70,75}_*.py` → `scripts/_archive/round_scripts/`.

## 执行步骤

### Phase 1 — Archive (无行为变化)

1. `git mv scripts/_r58_paper_strict_eval.py scripts/_archive/round_scripts/`
2. `git mv scripts/_r69_rerank_11axis.py scripts/_archive/round_scripts/`
3. `git mv scripts/_r70_eval_matrix.py scripts/_archive/round_scripts/`
4. `git mv scripts/_r70_plot_best_agent.py scripts/_archive/round_scripts/`
5. `git mv scripts/_r75_ensemble_eval.py scripts/_archive/round_scripts/`

### Phase 2 — 删 alias + 修测试

6. `scripts/eval_ensemble.py`: 删 `_ensemble_action_fn = build_ensemble_action_fn` (行 37-39) + 删头部 comment.
7. `tests/test_eval_ensemble_recurrent.py`: `from eval_ensemble import _ensemble_action_fn` → `from andes_rl_kundur.evaluation.ensemble import build_ensemble_action_fn`; 删 `sys.path.insert(0, str(ROOT / "scripts"))` hack.

### Phase 3 — Dual-eval helper (核心)

8. 新增 `src/andes_rl_kundur/evaluation/summary.py`:
   - `score_trace_files(trace_paths: dict[str, Path], *, label, is_ddic=True) -> dict`
     - 输入: `{scenario_name: trace_json_path}` (LS1 / LS2 锚 only)
     - 输出: `{"LS1": float|None, "LS2": float|None, "geo": float|None, "cum_rf": float|None, "cum_rf_LS1": float|None, "cum_rf_LS2": float|None}`
     - 复用: `paper_grade_axes.evaluate_trace` + `paper_strict_eval.compute_global_cum_rf` + `aggregation.floor_geo_mean`
     - 不在 `score_run` 里抽 — `score_run.score_seed` 是端到端 (load → run → score); 这个 helper 只做 score 部分, 不依赖 actors / ANDES.

9. `src/andes_rl_kundur/evaluation/__init__.py`: 不动 (helper 通过 fully-qualified import 调用, 不污染包顶层).

### Phase 4 — score_run 复用 helper (logic-preserving)

10. `scripts/score_run.py:score_seed`: 把现有的 `for scen in SCENARIOS: ... evaluate_trace + compute_global_cum_rf` 循环替换为 `score_trace_files(...)`. 输出键完全保持. 端到端 bit-identical.

### Phase 5 — eval entries dual-eval (默认 on)

11. `scripts/eval_ddic.py`: 跑完所有 scenario, 调 `score_trace_files`, 写 `<out-dir>/<label>_summary.json`. 打印 headline `[V4 ddic eval] geo=0.xxxx cum_rf=-x.xxxx`.
12. `scripts/eval_ensemble.py`: 同上 — 跑完后调 `score_trace_files`, 写 summary, 打印 headline.
13. `scripts/eval_all_seeds.py`: 把现有 `paper_ratio` ranking 换成 dual-eval. 每个 seed 调 `score_trace_files` → 写入 `eval_v4_summary.json` 的 ranking 列 (新增 `geo` / `cum_rf` 列, 按 `geo` 降序排). 保留 `max_df` 列做 sanity-check.

### Phase 6 — train.py auto-eval (`--final-eval`, 默认 on)

14. `scripts/train.py`:
    - `--final-eval / --no-final-eval` flag, default `True`.
    - 训练 loop 结束 + `_save_checkpoint(actor_tag="final")` 之后:
      - `from andes_rl_kundur.evaluation.summary import score_trace_files` 等.
      - 选 ckpt suffix: `"best_eval"` if `eval-every-n-eps>0` and exists, else `"best"` if exists, else `"final"`.
      - 调 `score_run.score_seed(save_dir, label=f"final_eval_{basename}", out_dir=save_dir / "final_eval", suffix=suffix, config=env_config)`.
      - 写 `<save_dir>/final_eval_summary.json`, 打印 headline (geo + cum_rf).
    - **try/except**: eval 失败不杀训练 — log 错误, 写 `final_eval_error.txt`, 继续退出.
    - **ANDES 注意**: training loop 已 `env.close()`. 最后一轮 env close 在 `for ep` 循环里; eval 的 `run_scenario` 自己 build + close, 安全.

### Phase 7 — Tests

15. `tests/test_score_trace_records.py` (新):
    - `test_score_trace_files_dual_eval`: 喂 2 个 fixture trace (LS1+LS2), 验 6 个 key 都有数值, geo > 0, cum_rf < 0.
    - `test_score_trace_files_missing_scenario`: 喂 1 个 scenario, 验另一个键是 None.
    - `test_score_trace_files_empty`: 空 dict 输入 → 所有键 None.
16. 验 `tests/test_eval_ensemble_recurrent.py` 在改 import 后仍 3/3 pass.

### Phase 8 — Verify

17. `python memory/tools/validate.py`
18. `python -m pytest tests/ --timeout=60`
19. `python memory/tools/render.py`

### Phase 9 — Memory

20. `memory/claims/CLM-0137.md`: decision/S, eval pipeline 统一 + train auto-eval contract.
21. `memory/rounds/R78/verdict.md` (本目录, Q-sections + PI 话).

## 不动

- `paper_grade_axes.py` (paper-cited, AD-14 锁定; 5 处 inline geo-mean 留给未来 round).
- `score_run.score_seed` 接口签名 (logic-preserving refactor only).
- `EVAL_SEED=42` / `STEPS=150` 各 entry 自己的常量 (R76 review 已 OK; 本轮不动).
- `eval_no_control.py` (基线产 trace, axes 6-11 不适用, 没有 score 意义).
- ANDES session 单例约束 (paper_path 已有 try/finally close).

## 风险

- **R1 (high)**: `eval_all_seeds.py` ranking 从 `paper_ratio` (max_df) 切到 `geo` 是行为变化. 历史脚本 / paper draft 可能依赖 max_df 顺序. **缓解**: 保留 `max_df` 列, 新加 `geo` / `cum_rf` 列, 按 `geo` 排序. 在 verdict 里注明对比。
- **R2 (mid)**: train.py 加 final-eval 会在每次训练后多花 ~30-60s (LS1+LS2 各 ~15s). **缓解**: `--no-final-eval` 可关.
- **R3 (low)**: ANDES session 在 train 末尾跑 eval — 训练 env 已 close, eval `run_scenario` 自己 build, 不冲突. 但 R66 Q-0010 fix 提示了类似 bug. 验证: 跑一次完整 mini-train (10 ep) 看 final-eval 是否成功.

## 验证标准

- 206 (R77 baseline) + 3 (new score_trace_files tests) = 209 pytest pass.
- `python -c "from andes_rl_kundur.evaluation.summary import score_trace_files"` 成功.
- `validate.py` 全过 (claims + questions + verdict Q-sections + 给 PI 的话).
