# R77 plan — R76 review follow-up (TDD-driven)

**Date**: 2026-05-18
**Type**: maintenance / follow-up to R76 review
**Wall**: ~30 min
**Trigger**: 用户 `/code-review-and-quality` 出 2 reviewer 报告, 然后 `/tdd 解决全部`.

## 范围

### TDD-driven (有行为变化, RED→GREEN)

1. **H1** `BaseAgent.is_recurrent` 显式声明 + `_SACBase.is_recurrent = False`
   - 删 `train.py:540` 的 `getattr(ag, "is_recurrent", False)` fallback
   - 3 new tests: `_SACBase` / `TD3Agent` / `TD3LSTMAgent` 各自 `is_recurrent` class attr
2. **H6** `paper_grade_axes.TraceScore.summary` bar width 恒等 `_SCORE_BAR_WIDTH`
   - 修 `int(score*W) + int((1-score)*W)` truncation bug (W-1 on some scores)
   - 改用 `round` 单方向凑齐: `hashes = round(...); dots = W - hashes`
   - 12 new tests: parametrize 10 个 score 值 + 端点 + half

### Non-TDD (lint / style, 零行为)

3. **F1** `eval_ensemble.py:32` 删 unused `ensemble_action` import + 删 back-compat alias
4. **F2** `train.py:_save_checkpoint` 加 `coordinator: CTDECoordinator | None` type hint
5. **F3** `paper_grade_axes.py` `os` / `sys` 移回 `__main__` block (避免 library namespace 污染)
6. **H2** `train.py:674` `l` → `loss` (E741 ambiguous)
7. **H3** `paper_grade_axes.py:393` `Optional[float]` → `float | None` (UP045)
8. **H4** `train.py` 3 处 quoted `"CTDECoordinator | None"` 删引号 (UP037)
9. **H5** `eval_all_seeds.py:135` `f"\n=== ..."` → `"\n=== ..."` (F541)

## 不动

- `paper_strict_eval.py:159` quoted `"V4Config | None"` — V4Config 未 import (避循环), 引号必需
- `paper_strict_eval.py` 已有命名常量 (R76 done)
- `_save_checkpoint` 调用站点 — 接口签名已统一

## 验证

- baseline: 191 (post-R76)
- 终态: 206 (191 + 3 is_recurrent + 12 summary)
- `pytest tests/ --timeout=60` → 206/206 pass
