# R85 verdict — Classical PI / Droop baseline (paper-mandatory comparison)

**Date**: 2026-05-19
**Status**: in-progress
**Type**: experiment (eval-only, zero training, zero ANDES env mutation)
**Wall**: TBD

## TL;DR

R85 补 paper-mandatory 的 classical baseline (distributed frequency droop + 4D
distributed PI), 在跟 R72_w4 SOTA 完全相同的 setup (V4 paper-faithful, LS1+LS2,
seed=42, steps=150) 下报 11-axis geo. 这是 R57-R82 共 91 round 中 0 次跑过的
对比 — paper reviewer 必问 "RL vs classical PI/Droop"; 不补这一块 paper claim
站不住. 跟 R83 obs-space training + R84 critic-forensics 完全正交 (R85 是 eval
only, 单 ANDES WSL slot).

<!-- numbers filled in by W4 after W1+W2+W3 land -->

## Methodology

R85 plan (`memory/rounds/R85/plan.md`) 设计 4 wave sequential, 全部 eval-only:

- **W1 droop**: K_droop ∈ {0.5, 1, 2, 5, 10, 20, 50} (7 K × 2 scen = 14 eval)
- **W2 PI coarse**: 4D grid Kp_M / Ki_M / Kp_D / Ki_D ∈ {1, 5, 20} × {0, 5, 20}
  × {1, 5, 20} × {0, 5, 20} = 3⁴ = 81 combo × 2 scen = 162 eval
- **W3 PI fine**: local refine ±1 step around W2 best (~16 combo × 2 scen)
- **W4 close**: verdict + 3 claims + PI chat brief

Controllers (`scripts/r85_classical_baseline.py`):

- **DroopController**: `ΔD_norm[i] = clip(K_droop * |obs[i][1]|, 0, 1)`,
  `ΔM_norm = 0`. Memoryless, 1 gain.
- **PIController**: 4 instance, 每 ESS 1 个, integral state per agent reset
  on step==0. `err = obs[i][1]` (normalized Δω). `ΔM = clip(-Kp_M*err - Ki_M*∫err, -1, 1)`,
  same for ΔD with separate gains. 无 anti-windup (episode 50 step × DT=0.2 = 10s
  integral 不爆).

Action decode path identical to RL agent (`base_env.step` line 332-333,
ΔM_norm × DM_MAX or × -DM_MIN by sign; same for ΔD) — apples-to-apples.

Eval pipeline reuse `evaluation/paper_path.run_scenario` (V4 env, seed=42,
steps=150) + `evaluation/summary.score_trace_files` (11-axis geo via
`paper_grade_axes.PAPER` + cum_rf via `paper_strict_eval.compute_global_cum_rf`).
Sibling `no_control_<scen>.json` 自动用 `zero_action_fn` 复算 (axis 8 reference).

## Results

<!-- W1 -->
### Droop scan (W1)

TBD

<!-- W2 -->
### PI 4D coarse grid (W2)

TBD

<!-- W3 -->
### PI fine refine (W3)

TBD

### Headline comparison

TBD

## Verification

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (R85 0 mutation 在 V4 / V4Config / base_env)
- R72_w4 SOTA ckpt **read-only** (R85 不 load 任何 ckpt — classical 是 pure stateless / scalar-integral)
- 同样 seed=42 + steps=150 + V4Config.paper_faithful() 跟 CLM-0094 / R80 cross-eval setup 1:1
- 同样 `score_trace_files(is_ddic=True)` 路径 → 11-axis geo 数字直接跟 0.391 比

## Infrastructure changes

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py / 任何 ckpt / 任何 test.

新建:
- `scripts/r85_classical_baseline.py` — 单 entry, 含 DroopController + PIController + scan_droop + scan_pi + headline writer
- `results/r85_classical_baseline/` — output namespace (scan_droop/k*, scan_pi/kpM*..., summary JSON)
- `memory/rounds/R85/{plan.md, verdict.md}` — round bundle
- `memory/claims/CLM-0151/0152/0153.md` — droop best / PI best / RL advantage (3 finding claims)

## Cross-references

- CLM-0094 / R72_w4_lstm_tau001_warmup5_s54 — RL SOTA baseline (geo=0.391, R85 比对参照)
- CLM-0144 — 91-round algo plateau (R85 is paper-completeness gap, not algorithm sweep)
- R30 no_control baseline — LS1+LS2 eval geo=0.104 (R85 floor reference)
- R80 cross-eval — same V4 paper-faithful eval pattern, 直接复用 SCENARIOS / score_trace_files
- ADR-0001 (src layout) / ADR-0002 (V4 SSOT)

## Questions opened (this round)

TBD (likely none — R85 is paper-completeness gap closure, not exploration)

## Questions closed (this round)

- (none — R85 不直接关任何已 open Q)

## Questions advanced (this round, status unchanged)

- **Q-0014** (open, algorithm exploration backlog) — R85 给出 classical floor,
  refines what "突破 plateau" 的真实门槛是 (相对于 classical 的 RL advantage,
  而不只是 0.391 这个 absolute number).

## 给 PI 的话

TBD — W4 fill in after results land.
