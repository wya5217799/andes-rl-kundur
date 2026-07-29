# CONTEXT — andes-rl-kundur

**Purpose:** canonical domain glossary for this repo.
**Glossary last updated:** 2026-05-19 (R80–R86).
**Navigation role clarified:** 2026-07-29.

This file captures terms and decisions that are not derivable from the code
alone. For research-state facts (numerical results, round verdicts, claims),
see `memory/STATE.md`. For research-process rules, see `CLAUDE.md`. Accepted
architecture decisions live as individual records in `docs/adr/`.

---

## Glossary

### `paper path`
The end-to-end execution flow that produces the paper's headline numbers:
`train.py` (V4 env, SAC agent) → checkpoint → `eval_no_control.py` +
`eval_ddic.py` → JSON traces → `paper_grade_axes.py` → 6-axis geo-mean.
Any file outside this flow is research scaffolding, not load-bearing for
the paper.

### `V4 env`
`andes_vsg_env_v4.py`. The paper-path canonical env. Paper-faithful:
H₀=100, Eq.14 strict, φ_d rescaled to 0.0056 (lower clamp from R18–R19).
V1/V2/V3 are historical ancestors. **Plant 风机近似**: G4 @ Bus 11 用
GENROU + `ZERO_G4_INERTIA=True` (H=0 退化为风机), W2 @ Bus 8 用
GENCLS M=0.1。两者都是 paper Sec.II "neglect inner loop" 声明下的
合法近似。**R57+ 全部 SOTA ckpt 依赖 V4 bit-identical reproducibility**;
不动 V4 / V4Config / base_env / paper_grade_axes.py。

### `V5 env`
`andes_vsg_env_v5.py` (R80 起新增, ADR-0004)。与 V4 并存。G4 + W2
plant 风机近似升级为 ANDES REGCA1 (+REECA1 if needed)。Framing 是
**ANDES 侧 plant 颗粒度工程升级, paper-deviation** — 不是 "更 paper-faithful"
(paper Sec.II 显式 "neglect inner loop", REGCA1 反方向; paper Sec.IV-A
风机模型沉默, "对齐" 无据)。Contribution path 阶梯 C3→C2→C1, 按结果定。
新 ckpt 走 `r80+_*` namespace, 不污染 V4 ckpt 区。

### `paper 风机沉默`
paper Yang2023 Sec.IV-A 关于风电场模型的全部信息: "Generator 4...
replaced by a wind farm with the same capacity" + "100 MW wind farm
connected to bus 8"。**未指定** Type 3/4 / GFL/GFM / WECC trio /
inertia emulation / 控制策略。任何 "对齐 paper 风机" 的论述都缺乏 paper
文字支撑 (R80 grill 阶段 cross-reference 全文确认)。残留 2× max_df 残差
(R08 实测 0.266 vs paper 0.13) 归因主要在 paper 未给的 line/load/SBASE/solver,
不是风机模型 — 见 ADR-0004 / ADR-0005。

### `Asset 4 / ranker`
`paper_grade_axes.py`. Paper-cited. Computes the 6-axis geometric mean
that produces the paper headline. Locked at v4.0 (post-r30/N1c fix).
**Logical changes require a new round + claim per `CLAUDE.md`.**
Physical relocation (path-only change) also requires a documenting
round — see R37 entry below.

### `HAWE`
Heterogeneous Actor Weighted Ensemble. Inference-time combination of
actor outputs from independently-trained checkpoints. No retraining.
Reproducible recovery of 99.3% of R21's lucky-basin score (0.439 vs 0.444).
Paper's Asset 5.

### `lucky basin`
A point in policy space that achieves anomalously high 6-axis score
(>0.40) but cannot be reached by re-running training from a different
seed. R21's V4_h50_s49 (0.444) is the canonical example. R23–R27's
22 ckpts all stalled ≤ 0.22.

### `multi-seed attractor`
The 6-axis score that SAC reliably converges to under V4 + paper-faithful
reward: ~0.137 ± 0.005, regardless of H₀ ∈ {40,70,100,200} or seed.
The "real" performance ceiling of SAC on this problem, modulo lucky basins.

### `claim` / `question` / `round` / `ledger`
Four-entity research memory system (active oracle since R39):
- **Claim** (`memory/claims/CLM-NNNN.md`): atomic, append-only, citable
  finding / decision / correction.
- **Question** (`memory/questions/Q-NNNN.md`): the forward-action unit.
  An open research uncertainty that a future round may address. Status
  is one of `open` / `in-flight` / `closed-positive` / `closed-negative`
  / `abandoned`. Closure cites a closing claim + round.
- **Round** (`memory/rounds/RNN/`): plan.md + verdict.md, bundles an
  experiment or infrastructure change. Verdict has 3 mandatory
  Q-sections (opened / closed / advanced) and — for R≥59 — a
  mandatory `## 给 PI 的话` section (see `PI 简报` below, ADR-0003).
- **STATE.md** (`memory/STATE.md`): auto-rendered active oracle. From
  R59 onward, top section is `## 给 PI 的简报（最新一轮）` (lifted
  from the newest R≥59 verdict, with glossary annotation). Followed
  by the legacy 6 sections (headlines / in-flight / open Qs / recently
  closed / latest round / stats) plus `## 历史简报` at the bottom.
  Reads claims + questions + rounds + `memory/glossary.yml`.
- `memory/handoffs/` is **out of schema** — informal session-end
  scratchpad, not read by `validate.py` or `render.py`. See
  `memory/handoffs/README.md`.
Full design rationale: `memory/rounds/R39/plan.md`.

### `PI 简报` / briefing layer
The fourth mandatory section of `memory/rounds/RNN/verdict.md` (for
R≥59), titled `## 给 PI 的话`. Written for the user as research
partner, not as sign-off authority. Five fixed sub-segments:

1. **这周干了啥** — 1–2 sentences of context
2. **结果（一句话）** — headline number / outcome
3. **意外** — surprising finding / risk flag — the participation hook
4. **我默认下一步做** — agent's intended default action
5. **你想插一脚就说** — explicit invitation; silence = default proceeds

Soft cap ≤ 30 lines (validator warns, does not block). `render.py`
lifts the latest one to STATE.md's `## 给 PI 的简报（最新一轮）`.
Designed in ADR-0003 (2026-05-17).

### `术语速查` / glossary inline-annotation
`memory/glossary.yml` maps project jargon to ≤ 30-char definitions.
`render.py` annotates each term on **first occurrence per briefing**
as `term(definition)`; subsequent uses bare. Goal: PI never hits an
unexplained acronym in the briefing. ASCII-word lookarounds make the
match Chinese-safe (`用LSTM时` matches `LSTM`).

### `AI 自治 vs PI 参与`
Operational principle (R59 / ADR-0003). AI agents retain autonomous
decision-making on technical choices (training configs, code refactors,
eval scripts). The PI exercises **participation, not approval**, via
the briefing's `你想插一脚就说` segment. Silence = AI default proceeds;
explicit pushback = redirect. Distinct from a sign-off model where PI
silence blocks.

### `WSL-only` (ANDES)
ANDES (the power system DAE simulator) is installed inside WSL only:
`/home/wya/andes_venv/bin/python`. Any Windows-side `andes` install is
a historical mis-install; do not use. Hard limit: ≤3 parallel ANDES
Python processes (R23 finding — TDS internal stiffness mis-judges
under contention).

### `paper-cited / paper-grade / paper-faithful-modified / paper-strict-pure / paper-strict-rescaled`
Five different concepts (term-split via ADR-0002, R58):

- **paper-cited**: file or checkpoint is directly referenced from the
  paper's reproducibility appendix. Cannot be deleted/moved without
  new round. Currently: `paper_grade_axes.py`, contents of
  `results/whitelist/`.
- **paper-grade**: code that passes the 6-axis evaluation framework
  (Asset 4). Not the same as paper-cited.
- **paper-faithful-modified** *(was: `paper-faithful` until R58)*:
  topology + obs + action space match paper, but the V4 reward adds
  a non-paper `PHI_ABS=50` term and rescales `PHI_H/D` to `0.0056`
  for ANDES numerical stability. Eval uses project-invented 6-axis.
  V4 env is paper-faithful-modified; V1–V3 are not.
- **paper-strict-pure** *(new, R58)*: paper Eq.14 reward exactly
  (`PHI_ABS=0, PHI_H=PHI_D=1.0`); paper Sec.IV-C global cum-rf eval.
  Used to empirically verify the R18 verdict's PHI-divergence claim.
  Accessed via `V4Config.paper_strict_pure()`.
- **paper-strict-rescaled** *(new, R58)*: `PHI_ABS=0` (no non-paper
  term) but `PHI_H/D=0.0056` retained from R18; paper Sec.IV-C eval.
  Isolates the question "does the algorithm ranking depend on
  PHI_ABS, or on the H/D rescale?". Accessed via
  `V4Config.paper_strict_rescaled()`.

ADR-0002 documents the rationale for the term split.

---

## Legacy architecture decision index

The AD-01 … AD-14 block below is a preserved 2026-05-19 migration snapshot,
not the current decision authority. It may describe paths that were later
changed or never completed. Current decisions live in `docs/adr/`; a
contradiction requires a new ADR that explicitly supersedes the old one.

Status legend: ✅ decided, ⏳ pending, ⛔ rejected.

### AD-01 — V4 env self-contained, V1/V2/V3/NE39 to `_legacy/`  ✅
V4 currently inherits via V1 → V2 → V3 → V4. Reading V4 requires
reading all four. Decision: merge the inheritance chain into a single
`AndesMultiVSGEnvV4` class containing all needed attributes/methods.
Move V1/V2/V3, `andes_ne_env.py`, `andes_ne_regca1_env.py` to
`_legacy/env/andes/`. NE39 envs were never completed (M₀<20 → TDS
divergence; REGCA1 → 6 algebraic+state var DAE bloat).

### AD-02 — `scripts/research_loop/` round + experiment scripts archived  ✅
Of ~41 scripts, only the `eval_v4_*` family is on the paper path
(`eval_v4_no_control.py`, `eval_v4_ddic.py`, `eval_v4_all_seeds.py`,
`eval_v4_ensemble.py`). All `r01_*`–`r36_*` round drivers and
`experiment_*.py` move to `scripts/research_loop/_archive/round_scripts/`.
Research-value preservation is already handled by `memory/rounds/*/verdict.md`.

### AD-03 — Training entry rewritten as `scenarios/kundur/train.py`  ✅
Current state: `train_andes.py` (21 KB, broken `from env.andes_vsg_env import`
that only works via monkey-patch from `train_andes_v4.py` shim) +
`train_andes_warmstart.py` (12.6 KB copy-paste fork). Decision:
clean rewrite as `scenarios/kundur/train.py` accepting all flags including
`--resume <ckpt>` (warmstart is a flag, not a separate file). Old files
move to `_legacy/scenarios/kundur/`.

### AD-04 — `SCENARIOS` dict consolidated  ✅
Currently redefined in 7 eval scripts. Single source of truth is
`probes/andes_common/paper_constants.py`. All eval scripts switch to
`from probes.andes_common.paper_constants import SCENARIOS`.

### AD-05 — `config.py` V1 dead params removed  ✅
Delete `DH_MIN/DH_MAX/DD_MIN/DD_MAX/H_ES0/D_ES0` (V1-era, inconsistent
with V4). Keep `HIDDEN_SIZES/LR/GAMMA/BUFFER_SIZE/BATCH_SIZE` (still in
active use by eval scripts).

### AD-06 — `monitor.py` and `ma_manager.py` resolved by reference graph  ⏳
Both files' status is uncertain (`monitor.py` has broken import to
non-existent `utils/training_callback.py`; `ma_manager.py` may be a
no-op wrapper). Decision: scan reference graph as the first executable
step. Each file is either deleted (no live references) or fixed
(repair import / merge functionality).

### AD-07 — `agents/` gets BaseAgent abstraction  ✅
Define `agents/base_agent.py` with `BaseAgent` abstract class
(`act`/`update`/`save`/`load`). `SACAgent` inherits. `train.py` accepts
`--algo sac` (default) and routes to the right class. Reserved capacity
for future TD3/PPO without rewriting train loop.

### AD-08 — `infra/` abstraction conditional on monitor outcome  ⏳
If `monitor.py` is alive, abstract it (and callback/logger) into
`src/andes_rl_kundur/infra/`. If dead, skip this layer. Decision
deferred to AD-06 outcome.

### AD-09 — `src/andes_rl_kundur/` Python package layout  ✅
Adopt standard src-layout. Package name `andes_rl_kundur` (matches
repo). Library code under `src/andes_rl_kundur/`. Entry scripts under
top-level `scripts/`. Add `pyproject.toml`. All internal imports gain
`andes_rl_kundur.` prefix.

### AD-10 — `artifacts/` for frozen products  ✅
Move `paper/` (IEEE manuscript) and `dissertation/` (UNNC FYP) under
`artifacts/`. `memory/`, `results/`, `docs/`, `_legacy/` stay at root.

### AD-11 — Verification by JSON bit-identical comparison  ✅
Before refactor: run `eval_v4_no_control` and one `eval_v4_ddic` on a
known checkpoint, save output JSONs.
After each phase: re-run, diff JSONs. Tolerance: bit-identical (or
< 1e-6 float drift). Sediment the comparison as
`tests/test_regression.py`.

### AD-12 — Two-phase execution  ✅
Phase 1 (logical cleanup): all changes in AD-01..AD-08 done in-place
(no directory moves). Verify with AD-11. Commit boundary.
Phase 2 (physical reorg): AD-09, AD-10. Verify with AD-11. Commit
boundary. Documentation updates (AD-13) happen after phase 2.

### AD-13 — Feature branch `refactor/clean-arch-2026-05-16`  ✅
All work on this branch. Merge to main only after both phases pass
verification.

### AD-14 — R37 round records the refactor  ✅
`paper_grade_axes.py` relocates to `src/andes_rl_kundur/evaluation/`.
This is a path change, not a logic change. Open R37 with verdict
containing the `git diff` proving logic is byte-identical. Issue a new
claim (`CLM-00XX`) documenting "ranker physical relocation, v4.0
unchanged."

---

## What this CONTEXT.md is not

- Not a status report — see `memory/STATE.md` for current numerical claims.
- Not a how-to — see `CLAUDE.md` for research-process rules and
  `scenarios/kundur/NOTES_ANDES.md` for ANDES engineering notes.
- Not a changelog — see git log + `memory/rounds/` for history.
- Not an audit trail — see `_legacy/CONTEXT.md` (frozen 2026-05-08).
