# R76 verdict — train.py helper + magic number 命名 + 8 个 round driver 归档

**Date**: 2026-05-18
**Status**: **closed-positive** (logic-preserving cleanup; 191 tests bit-identical pass)
**Type**: maintenance / refactor
**Wall**: ~1.5hr (review + apply + tests)

## TL;DR

> R75 (commit 799f1ac) 已完成 floor_geo_mean refactor + 死赋值删除. R76 收尾
> 剩余 simplification 清单: train.py 抽 `_save_checkpoint` helper (4 处重复
> save → 1 函数), buffer-check 两分支合并; `paper_grade_axes.py` / `paper_strict_eval.py`
> magic number 命名 (`_MIN_DT_S`, `_SCORE_BAR_WIDTH`, `_NO_CTRL_PREFIXES`,
> `_TDS_FAILURE_PENALTY` 等); 8 个旧 round driver 移 `scripts/_archive/round_scripts/`.
>
> **零行为变化**. 191/191 pytest pass (含 25 个 paper_grade_axes ranker test).
> 6-axis 值守恒.

---

## Phase 0 — Trigger

用户调 `/code-simplification` 全 repo review + "全做". 4 路 review agents 输出 punch
list. 上 session R75 已实施 Batch A (死赋值/死键/dup-import) + Batch B (floor_geo_mean
+ ensemble.py refactor). 本 round 接 Batch C + D + E.

## Phase 1 — train.py 简化 (Batch C)

### T2 — buffer-check 两分支合并

before:
```python
if getattr(agents[i], "is_recurrent", False):
    loss_info = agents[i].update()
elif len(agents[i].buffer) >= batch_size:
    loss_info = agents[i].update()
else:
    loss_info = None
```

after:
```python
ag = agents[i]
if getattr(ag, "is_recurrent", False) or len(ag.buffer) >= batch_size:
    loss_info = ag.update()
else:
    loss_info = None
```

Short-circuit OR 保证 recurrent agent 不去算 `len(ag.buffer)`. 行为等价.

### T3 — `_save_checkpoint` helper 抽取

4 处 save (on_best_reward / on_best_eval / periodic ep%100 / final) 全部 `for i in range(N): agents[i].save(...)` + `if coordinator is not None: coordinator.save_critic(...)`. 抽:

```python
def _save_checkpoint(agents, coordinator, save_dir, actor_tag, critic_filename):
    for i, ag in enumerate(agents):
        ag.save(os.path.join(save_dir, f"agent_{i}_{actor_tag}.pt"))
    if coordinator is not None:
        coordinator.save_critic(os.path.join(save_dir, critic_filename))
```

注: final ctde critic 保留 bare `"ctde_critic.pt"` (无 tag) — 历史兼容.

净改动: train.py -10 行.

## Phase 2 — magic number 命名 + 死代码 (Batch D)

### paper_grade_axes.py (paper-cited, logic-preserving)

- `_MIN_DT_S = 1e-6` — 取代 `_settling_time` 内裸 `1e-6`
- `_SCORE_BAR_WIDTH = 20` — 取代 `TraceScore.summary` ASCII bar 宽度
- `_NO_CTRL_PREFIXES = (...)` — 提模块级, 消除 `__main__` block 与 `_load_no_ctrl_max_df` 4-tuple 重复 (两处之前各定义一遍)
- `__main__` block 内 `import sys, os` 移到文件顶部 import 区

⚠️ **所有 25 个 paper_grade_axes ranker test pass**. 算式 verbatim 不变. 数值守恒.

### paper_strict_eval.py

- `_TDS_FAILURE_PENALTY = -1.0` — 取代 `cum_rfs.append(-1.0)` 裸值
- `_ALL_FAILED_SENTINEL = -1e6` — 取代 `return -1e6` 裸值
- `_MIN_MAG_PU = 0.1` — 取代 `if abs(mag) >= 0.1` rejection-sample 裸阈值

### _r70_eval_matrix.py

- `DRIFT_THRESHOLD = 0.2` — 取代两处 `v3_geo < 0.2` / `>= 0.2` 漂移判断

### eval_ensemble.py

- `assert` → `parser.error()` (CLI 校验不应受 `python -O` 影响)
- `with open() as f: json.dump(...)` → `out_p.write_text(json.dumps(...), encoding="utf-8")` (与其他 eval script 风格一致, 加 encoding 显式)
- 双 zip 循环合并 (print + load 同 pair 一次走完)
- 删 unused `from collections.abc import Callable`

### eval_all_seeds.py

- `EVAL_SEED = 42` 常量化 (与 score_run.py / eval_ddic.py 默认对齐)

## Phase 3 — 8 个旧 round driver 归档 (Batch E)

`git mv scripts/_r{XX}_*.py scripts/_archive/round_scripts/`:

| File | 关闭原因 | 替代 |
|------|---------|------|
| `_r44_eval_no_control_g4preserved.py` | Q-0001 闭 | `paper_path.zero_action_fn` + `V4Config(zero_g4_inertia=False)` |
| `_r51_score_sac_h64.py` | SAC h=64 被 LSTM 超 | `score_run.py` |
| `_r56_score_lstm.py` | 无 warmup ckpts 过时 | `score_run.py` |
| `_r57_beta_hawe_lstm.py` | warmup5 pool 过时 | `_r75_ensemble_eval.py` (现代版) |
| `_r57_beta_hawe_lstm_warmup.py` | 同上 | 同上 |
| `_r57_score_lstm_warmup.py` | warmup5 family 封存 | `score_run.py` |
| `_r60_no_control_paper_metric.py` | Q-0009 闭 | `paper_path` + `paper_strict_eval` |
| `_r61_sac_hawe_paper_metric.py` | CLM-0078 封存 | `_r75_ensemble_eval.py` + `evaluation.ensemble` |

**KEEP**: `_r58_paper_strict_eval.py` — 被 `_r58_eval_all.sh` 调用, CLI (`--n-scen`, `--scen-seed`, `--trace-out-dir`) 比 `score_run.py` 全.

**归档 note**: `_r61` 内含 `_ensemble_action_fn` 副本 (本地拷贝, 非 import). 归档后副本随脚本走, 当前权威以 `andes_rl_kundur.evaluation.ensemble.build_ensemble_action_fn` 为准.

## Verification

- baseline (HEAD R75 + handoff): 191 tests
- 终态: 191/191 pass (`pytest tests/ --timeout=60`, ~104s)
- import smoke: train.py / score_run.py / _r69 / _r70_eval_matrix / _r75_ensemble_eval / eval_ensemble 全 import OK
- paper_grade_axes 25/25 + paper_strict 12/12 + score_run 7/7 + aggregation 7/7 + paper_path 4/4 + ensemble_recurrent 3/3 = 58/58 关键模块 test pass
- v4_env_regression 2/2 (1e-9 tolerance) pass — V4 env 数值守恒

## New claims this round

- **CLM-0134** (decision/S) — R76 logic-preserving cleanup pass: train.py 抽 `_save_checkpoint` helper + buffer-check 合并; `paper_grade_axes.py` / `paper_strict_eval.py` magic number 命名; `_r70_eval_matrix` `DRIFT_THRESHOLD` 常量; `eval_ensemble` CLI 校验改 `parser.error()` + 统一 write_text; `eval_all_seeds` `EVAL_SEED` 常量. 191/191 tests bit-identical pass.
- **CLM-0135** (decision/S) — 8 个旧 round driver 归档进 `scripts/_archive/round_scripts/` (AD-02). 全部已被现代工具替代或封存. `_r58_paper_strict_eval.py` 保留 (`_r58_eval_all.sh` 直接调用).

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round)

(none)

## 给 PI 的话

**这周干了啥**: 用户调 `/code-simplification` 全 repo review + "全做". 4 路 review
agents 出 punch list. 发现 R75 已经做了 Batch A/B (floor_geo_mean refactor +
死赋值删除). R76 收尾剩余: train.py 抽 `_save_checkpoint` helper(把训练入口里
保存检查点的重复代码合并成一个函数) + 4 处 magic number 命名 + 8 个旧 round
driver 归档.

**结果（一句话）**: (1) **train.py 净 -10 行** (4 处 ckpt save 重复 → 1 个 helper);
(2) **paper_grade_axes(论文引用的 6 轴评分器, 不能改逻辑)** 加 3 个命名常量
(`_MIN_DT_S` / `_SCORE_BAR_WIDTH` / `_NO_CTRL_PREFIXES`), 算式 verbatim 不变, 25
个 ranker test 全过; (3) **8 个旧 _r* 移 `_archive/round_scripts/`**, 当前 paper-path
入口只剩 `score_run.py` / `eval_no_control.py` / `eval_ddic.py` / `eval_all_seeds.py`
/ `eval_ensemble.py` + 4 个仍在用的 `_r{69,70,75}_*.py`; (4) **191/191 tests pass**,
零行为变化, V4 env 1e-9 regression 通过.

**意外**: (1) **R75 上 session 已经做了一半工作** — 我 review 后准备 apply 才
发现 HEAD 已有 `floor_geo_mean` / `ensemble.py` / 死赋值删除. Batch A+B 全是空
操作 (git diff 空). 教训: 进 batch 前先 `git diff HEAD~3..HEAD --stat` 看最近改
动. (2) **paper_grade_axes 之前 `_NO_CTRL_PREFIXES` 在 `__main__` 和
`_load_no_ctrl_max_df` 各定义一遍**, 现在统一到模块级, 之后改前缀只改一处.

**我默认下一步**: R76 commit + render STATE.md. 真要"继续挤"剩选项:
(a) **直接 paper draft** (我推荐, R75 verdict 已说"continue-sweep ROI ~zero");
(b) `paper_grade_axes.py` 内 5 处 inline geo-mean 也可改 `floor_geo_mean` (paper-cited 要 verify 数值); (c) `_r58_eval_all.sh` 改用 `score_run.py` 后 `_r58_paper_strict_eval.py` 也可归档.

**你想插一脚**: commit R76 + 进 paper draft? OR 继续挤?
