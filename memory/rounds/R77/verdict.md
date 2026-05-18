# R77 verdict — R76 review follow-up (TDD: H1 is_recurrent + H6 bar-width + 7 lint)

**Date**: 2026-05-18
**Status**: **closed-positive** (2 TDD cycles + 7 lint fixes; 206/206 pytest pass)
**Type**: maintenance follow-up
**Wall**: ~30 min

## TL;DR

> R76 review (2 reviewer agents) 找 2 个 R76-引入 + 6 个 pre-existing nit.
> 用户 `/tdd 解决全部`. 走 2 个 TDD cycle (RED→GREEN→refactor) + 7 个 lint
> 直接改. 15 new tests (3 is_recurrent + 12 summary bar). 206/206 pass.

---

## Phase 1 — TDD-1: H1 `is_recurrent` 显式契约

### RED

3 个 fail 的 test:
- `_SACBase.is_recurrent is False` → `AttributeError`
- `TD3Agent.is_recurrent is False` → `AttributeError`
- (`TD3LSTMAgent.is_recurrent is True` — 已 PASS, pin contract from other side)

### GREEN

- `src/andes_rl_kundur/agents/sac_base.py`: 加 `is_recurrent: bool = False` class attr
- `src/andes_rl_kundur/agents/base_agent.py`: BaseAgent Protocol 加 `is_recurrent: bool` 声明 + docstring

### Refactor

- `scripts/train.py:540` 删 `getattr(ag, "is_recurrent", False)` → `ag.is_recurrent`

### Test

`pytest tests/test_sac_shared_base.py -k is_recurrent` → 3/3 pass.

---

## Phase 2 — TDD-2: H6 `summary` bar width

### RED

`tests/test_paper_grade_axes_summary.py` — 12 个 test (parametrize 10 个 score
值 + 端点 + half). 3 fail:
- `score=0.333` bar width = 19 != 20
- `score=0.875` bar width = 19 != 20
- `score=0.999` bar width = 19 != 20

根因: `int(score*20) + int((1-score)*20)` 当两个 fractional 部分都 < 0.5 时
两个 `int()` 都向下截断, 总宽度 19. 偶发 W-1.

### GREEN

`paper_grade_axes.py:175` 改为 `round` 单方向凑齐:
```python
hashes = round(a.score * _SCORE_BAR_WIDTH)
bar = "#" * hashes + "." * (_SCORE_BAR_WIDTH - hashes)
```

### Test

`pytest tests/test_paper_grade_axes_summary.py` → 12/12 pass.

⚠️ 这是 print 格式 fix, 非 6-axis 数值变化. paper_grade_axes ranker test 25/25 仍通过.

---

## Phase 3 — 7 个 lint / style 直接改

| # | 文件 | 改 |
|---|------|------|
| F1 | `scripts/eval_ensemble.py:30-33` | 删 unused `ensemble_action` import + 删 back-compat alias `_ensemble_action_fn = build_ensemble_action_fn` |
| F2 | `scripts/train.py:554` | `_save_checkpoint(coordinator)` 加 `CTDECoordinator \| None` 类型 |
| F3 | `paper_grade_axes.py:75-76` | `os` / `sys` import 移回 `if __name__ == "__main__":` block (避 library 用户拉无关 import) |
| H2 | `train.py:674` | `[l for l in ...]` → `[loss for loss in ...]` (E741) |
| H3 | `paper_grade_axes.py:393` | `Optional[float]` → `float \| None` (UP045) |
| H4 | `train.py:267, 353, 514` | 3 处 quoted `"CTDECoordinator \| None"` 删引号 (UP037) |
| H5 | `eval_all_seeds.py:135` | `f"\n=== ..."` 删 `f` (F541) |

### 不动

- `paper_strict_eval.py:159` quoted `"V4Config | None"` — V4Config 未 import (避循环), 引号必需
- `_NO_CTRL_PREFIXES` tuple vs frozenset — tuple 配合 `startswith(tuple)` API 正确

## Verification

- baseline (post-R76): 191 tests
- 终态: **206/206 pass** (191 + 3 is_recurrent + 12 summary)
- `pytest tests/ --timeout=60` → 206 passed in 110s
- paper_grade_axes 25/25 ranker test 仍通过 → 6-axis 数值守恒
- v4_env_regression 2/2 (1e-9 tolerance) 仍通过 → V4 env 不变

## New claims this round

- **CLM-0136** (decision/S) — R77 R76-review follow-up: 2 TDD cycle (H1 `is_recurrent` 契约 + H6 summary bar width) + 7 lint 直接改; +15 tests; 206/206 pass; 零行为变化 (paper_grade_axes 25/25 + v4_env_regression 2/2 守恒).

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round)

(none)

## 给 PI 的话

**这周干了啥**: R76 commit 后用户调 `/code-review-and-quality` 两 reviewer agent
独立 review, 出 2 个 R76-引入 + 6 个 pre-existing nit. 用户 `/tdd 解决全部`. 走
2 个完整 TDD cycle (RED→GREEN→refactor) + 7 个 lint 直接改.

**结果（一句话）**: (1) **H1 `is_recurrent` 改契约**: `BaseAgent` Protocol +
`_SACBase` 加显式 `is_recurrent: bool = False` 默认, `train.py` 训练循环里删 `getattr(...)`
fallback 直接读 `ag.is_recurrent` (3 new test pin); (2) **H6 `summary` bar
width fix**: paper_grade_axes 的 ASCII bar 之前用 `int+int` 偶尔得 W-1, 改用
`round` 单方向凑齐到 `_SCORE_BAR_WIDTH=20` 恒等 (12 new parametrize test, 纯
print 格式不动 6-axis 数值); (3) **7 个 lint 直接改**: 删 unused import + 加 type hint
+ 移 `__main__`-only import 回去 + `l→loss` + `Optional→|None` + 删 quoted
forward-ref + 删空 f-string 前缀; (4) **206/206 pytest pass** (191+15), 6-axis
数值守恒, V4 env 1e-9 regression 通过.

**意外**: (1) **bar width bug 是 pre-existing**(R76 review 才发现, 一直默默错了),
未受影响是因为 ASCII print 不被 test 检查, 也没有人 grep 解析 bar 字符串; (2)
**`paper_strict_eval.py:159` quoted `"V4Config | None"` 不能去引号** — V4Config
未 import (避循环), runtime 解析需要它在 namespace, 引号是 PEP 563 的合法用法
而非 ruff UP037 误报; (3) **R76 commit msg 已承认 import-os 顶部污染**, 但
review 出来后立刻修, 没必要硬抗.

**我默认下一步**: R77 commit + push. 真要"继续挤"剩选项:
(a) **直接 paper draft** (R76/R77 均推荐, refactor ROI 已耗尽);
(b) `_r58_eval_all.sh` 改 `score_run.py` 后再归档 `_r58_paper_strict_eval.py`;
(c) `paper_grade_axes.py` 内 5 处 inline geo-mean 也改 `floor_geo_mean` (paper-cited, 要 bit-identical verify).

**你想插一脚**: commit R77 + 进 paper draft?
