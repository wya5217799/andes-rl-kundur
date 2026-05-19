---
round: R76
state: active
opened: '2026-05-18'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R76 plan — train.py + paper_grade_axes 命名清理 + 8 个 round driver 归档

**Date**: 2026-05-18
**Type**: maintenance / refactor (logic-preserving)
**Wall**: ~1.5hr (review + apply + tests)
**Trigger**: 用户 `/code-simplification` "全做" 触发. R75 已完成 floor_geo_mean
+ ensemble.py + 死赋值 refactor; 本 round 收尾剩余清单.

## 范围

### Batch C — train.py 简化
1. **T2**: SAC update buffer-check 两分支合并 (short-circuit `is_recurrent or len(buf) >= bs`)
2. **T3**: 4 处 ckpt save (best_reward / best_eval / periodic / final) → 抽 `_save_checkpoint` helper

### Batch D — magic number 命名 / 死代码
- `paper_grade_axes.py`:
  - `_MIN_DT_S = 1e-6` (`_settling_time` 用)
  - `_SCORE_BAR_WIDTH = 20` (`TraceScore.summary` 用)
  - `_NO_CTRL_PREFIXES` 提模块级 (消 `__main__` 与 `_load_no_ctrl_max_df` 4-tuple 重复)
  - `__main__` 内 `import sys, os` 移顶部
- `paper_strict_eval.py`:
  - `_TDS_FAILURE_PENALTY = -1.0`
  - `_ALL_FAILED_SENTINEL = -1e6`
  - `_MIN_MAG_PU = 0.1` (取代裸 `0.1` magic)
- `_r70_eval_matrix.py`: `DRIFT_THRESHOLD = 0.2` (取代 `0.2` 漂移阈值)
- `eval_ensemble.py`:
  - `assert` 改 `parser.error()` (CLI 校验; `-O` 不会跳过)
  - `with open() as f: json.dump(...)` → `out_p.write_text(json.dumps(...), encoding="utf-8")` 与其他 eval 风格一致
  - 双 zip 循环合并 (print + load 同 pair 一次走完)
  - 删 unused `Callable` import
- `eval_all_seeds.py`: `EVAL_SEED = 42` 常量化

### Batch E — 8 个旧 round driver 归档 (AD-02)
移到 `scripts/_archive/round_scripts/`:
- `_r44_eval_no_control_g4preserved.py` (Q-0001 闭, `paper_path.zero_action_fn` 替代)
- `_r51_score_sac_h64.py` (SAC h=64 已被 LSTM 超)
- `_r56_score_lstm.py` (无 warmup ckpts 过时)
- `_r57_beta_hawe_lstm.py` / `_r57_beta_hawe_lstm_warmup.py` (warmup5 pool 过时, `_r75_ensemble_eval.py` 是现代版)
- `_r57_score_lstm_warmup.py` (warmup5 family 封存)
- `_r60_no_control_paper_metric.py` (Q-0009 闭)
- `_r61_sac_hawe_paper_metric.py` (CLM-0078 封存; 内含 `_ensemble_action_fn` 副本 — 以 `evaluation.ensemble` 为准)

**KEEP**: `_r58_paper_strict_eval.py` (被 `_r58_eval_all.sh` 调用; CLI 比 `score_run.py` 全)

## 验证

- Baseline: 191 tests (R75 commit 9d8d653 后)
- 每 batch 改完跑 pytest tests/
- 终态: 191 全过 + `_r75_ensemble_eval.py` import smoke 通过

## 不动

- `paper_grade_axes.py` 算法 / 阈值 / 权重 / aggregation 顺序 / 公式
- V4 env 任何参数
- ranker v3.1 输出数值
- `eval_no_control.py` / `eval_ddic.py` (已干净)
- R75 已 refactor 的 floor_geo_mean / ensemble.py (本 round 不重复做)

## 不做新研究 / 不动 6-axis

按 AD-14, paper-cited 改 logic 需要新 round + 数值 verify. 本 round 只动:
- magic number 命名 (`_MIN_DT_S`, `_SCORE_BAR_WIDTH`, `_NO_CTRL_PREFIXES`) — 算式 verbatim 不变
- import 整理 — 运行时无差异
- `__main__` 内 `_NO_CTRL_PREFIXES` 移模块级 — 行为不变

所有 25 个 paper_grade_axes ranker test 通过 → 6-axis 值守恒.
