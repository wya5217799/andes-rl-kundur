# andes-rl-kundur — AI navigation

## 工程原则 (load-bearing — read before any change)

三条原则按优先级排序. 跟具体任务冲突时, **原则赢**.

### 1. 代码可维护性 (maintainability)

写代码 / 文档 / claim 的时候考虑 "**6 个月后的我或别人能不能接手**":

- **不写 one-off scripts** — 同样的 housekeeping pattern 出现第二次, 升级成
  `memory/tools/<name>.py` (library + CLI), 替代 `_r166_sweep.py` 那类
  一次性脚本. 模板: `memory/tools/close_round.py` (取代 `_r166_sweep.py` /
  `_r171_sweep.py` 的统一 CLI).
- **每工具 self-documenting** — top docstring 含 motivation (解决哪个痛 /
  哪个 CLM 揭示) + usage (CLI + library API) + 失败模式. 看 docstring 就懂
  能不能用、什么时候用.
- **不依赖 cwd** — 用 `Path(__file__).resolve().parents[N]` 自找 ROOT.
- **跨平台 ASCII fallback** — Windows GBK terminal 不能显示 ✓/✗/box-drawing,
  统一用 ASCII (`[x]`, `--`). 见 `status.py`, `baselines.py`.
- **文档跟代码一起改** — 改 CLAUDE.md / `_TEMPLATE.md` 是改动的一部分,
  不是 follow-up. 2026-05-20 加 6 工具的同次改了 CLAUDE.md "Tools" section
  + 5-step creation workflow.

### 2. 鲁棒性 (robustness)

防 race / silent-failure / wrong-interpretation:

- **原子操作 (race-safe)** — multi-session 并发时, 同一资源 (round ID,
  claim ID) 必须由 OS 原语保证唯一. 模板: `reserve_round.py` (atomic
  `mkdir`) + `reserve_claim.py` (atomic `open('x')`). **永远不要手动
  挑 round/claim 号**.
- **失败优雅** — WSL 不可用, YAML 解析错, 文件读失败: return `[]` /
  `None`, 不 crash. 见 `status.py` 的 WSL fallback, `baselines.py` 的
  JSON 错处理.
- **multi-metric 双轨制 (CLM-0430 教训)** — paper-reward-ablation 类 claim
  **必须同时 cite `geo` (项目 11-axis) 和 `cum_rf` (paper Yang2023 §IV-C)**.
  两 metric 可能反方向 (R246 在 geo 上看 -28%, 在 cum_rf 上 -4.4%);
  单 metric 框架重蹈 CLM-0027 / CLM-0430 失败模式. Lint:
  `python memory/tools/dual_metric_lint.py`.
- **measured > estimated** — 比较 baseline 用 `baselines.py` 查 measured
  数据, **绝不用 cross-algo 比例外推**. 2026-05-20 session R246 verdict
  把 baseline 估成 0.327 (R204 hreg × scalar/hreg 比例), 真实 R251
  measured 是 0.266, 错估 19% 导致 paper claim "outlier" 框架错了
  10 个 round 才修 (CLM-0410 → CLM-0435).
- **预期 vs 实际配对** — 每 plan.md 写 pre-registered outcomes, 每 verdict
  对照 outcome 分类. 防止 ad-hoc post-hoc 自由解释.

### 3. 项目长期发展 (long-term sustainability)

考虑代码 / 决策 / claim 在未来 100+ rounds 后还成不成立:

- **不动 paper-cited assets without 新 round** — `paper_grade_axes.py`
  (Asset 4) 修改要新 round + 新 claim 文档化 (即使 path-only 重命名也算).
  `base_env.py` / `andes_vsg_env_v4.py` / `train.py` 改前必读
  `docs/eng-notes/NOTES_ANDES.md`. V4 bit-identical regression test
  (`tests/test_v4_env_regression.py`) 是 contract, 必须 1e-9 tol 通过.
- **不打破 ckpt 命名空间** — V5 ckpt 走 `r80+_*`, V4 走原命名. R57+ 全 SOTA
  ckpt 依赖 V4 reproducibility, 改 obs/action 维度会全 invalidate.
- **不追 plateau 已确认结构性的方向** — R86 CLM-0148/0149 已证 algo dim
  plateau structural (91 trials 共识). 突破路径在 reward shaping / env
  physics / classical baseline, 不在 algo 调参. 别再起 algo SOTA-hunt rounds.
- **教训 codify 进 infra, 不靠 "下次记得"** — session 出失败 → 写
  validator / linter / 工具防再犯. 例: CLM-0430 dual-metric 失败 → 写
  `dual_metric_lint.py` + `_TEMPLATE.md` policy comment; baseline-估错
  失败 → 写 `baselines.py` + CLAUDE.md "use measured not estimated"
  step. **memory/handoffs/ 里的笔记不算 codify** — 只有进 `memory/tools/`
  + CLAUDE.md 才算.
- **plan-first for non-trivial 改动** — 跨多 file / 跨 layer / 改 contract
  的工作, 先 plan 后写. 单文件 typo / 单 verdict 补 claim 不需要.

### 工程原则 → 现有 infra 映射

| 原则 | 工具 / 文件 |
|------|--------|
| 可维护性 (one-off → library) | `memory/tools/close_round.py`, `reserve_round.py`, `reserve_claim.py` |
| 鲁棒性 (race-safe) | `reserve_round.py` (atomic mkdir), `reserve_claim.py` (atomic `open('x')`) |
| 鲁棒性 (re-entry safe — R256 followup) | `reserve_round.py --strict-no-active` / `--list-active` (state-based active-rounds preflight; prevents post-context-compression duplicate work) |
| 鲁棒性 (dual-metric) | `dual_metric_lint.py`, `_TEMPLATE.md` policy block, CLAUDE.md step 4 |
| 鲁棒性 (measured baseline) | `baselines.py --match`, CLAUDE.md step 3 |
| 鲁棒性 (operational visibility) | `status.py` |
| 鲁棒性 (plan-time check) | `round_preflight.py` (catches R244/R246/CLM-0430 class failures BEFORE launch) |
| 长期发展 (V4 regression) | `tests/test_v4_env_regression.py` (1e-9 tol contract) |
| 长期发展 (claim audit trail) | `validate.py` (4 rules + back-edges), `render.py` (STATE.md oracle) |

## Read first

- `CONTEXT.md` — glossary (incl. V4/V5/paper-faithful split) + 14 architecture decisions (AD-01 … AD-14)
- `docs/adr/0001-src-layout.md` — long-form rationale for the src layout
- `docs/adr/0002-paper-strict-vs-paper-faithful.md` — 5-term paper-X split (R58)
- `docs/adr/0003-pi-briefing-layer.md` — PI briefing contract (R≥59 mandatory)
- `docs/adr/0004-v5-env-regca1-plant-paper-deviation.md` — V5 REGCA1 plant framing as paper-deviation (R80)
- `docs/adr/0005-andes-only-drop-simulink-1to1.md` — ANDES-only, no Simulink 1:1 chase (R80)
- `memory/STATE.md` — auto-rendered active oracle (headlines / in-flight /
  open Qs / recently closed / latest round)
- Open `memory/questions/Q-*.md` files — what to address next
- `memory/handoffs/README.md` if you wonder why session-end notes are
  not in `STATE.md` (they're non-schema scratchpad, not oracle input)

## Repository layout (post 2026-05-16 refactor)

```
andes-rl-kundur/
├── src/andes_rl_kundur/      Python package (library code)
│   ├── agents/               SAC + SAC_CTDE + TD3 + TD3-LSTM/LSTM2 +
│   │                         TD3-Transformer (R82) + BaseAgent Protocol
│   ├── env/andes/            V4 (paper-faithful) + V5 (REGCA1 plant, R80) +
│   │                         base_env (shared obs/action + R83 area-mean aug)
│   ├── evaluation/           paper_grade_axes (Asset 4, paper-cited)
│   ├── probes/               andes_common reuse layer
│   ├── scenarios/contract.py KUNDUR domain constants
│   ├── utils/monitor.py      TrainingMonitor diagnostics
│   └── config.py             SAC hyperparameters
├── scripts/                  Runnable entry points
│   ├── train.py
│   ├── eval_no_control.py
│   ├── eval_ddic.py
│   ├── eval_ensemble.py
│   ├── eval_all_seeds.py
│   ├── score_run.py          Paper-grade ranker entry (R72+)
│   ├── r8x_*.py              Active round drivers (R80–R86; archive after R≥10 stale)
│   └── _archive/             Frozen round drivers (R01..R36, R60..R79 later)
├── probes/                   Round-level probe JSONs (r80+_*.json)
├── tests/                    pytest regression tests
├── artifacts/                Frozen outputs (paper_r77/, dissertation/)
├── memory/                   Claim ledger + rounds + handoffs
├── docs/                     ADRs (0001..0005), engineering notes, design specs
├── results/                  Gitignored except whitelist/
├── _legacy/                  Frozen ancestors of refactored modules
└── pyproject.toml            Package metadata + tool config
```

## Memory subsystem (active oracle, R39+)

Four schema-managed entity kinds + one scratchpad + two tools. The oracle
(`STATE.md`) reads claims + questions + rounds; it does **not** read
handoffs. Full design: `memory/rounds/R39/plan.md`.

### Entities at a glance

| Kind | Where | Purpose | Tooling |
|------|-------|---------|---------|
| **Claim** (`CLM-NNNN`) | `memory/claims/` | Atomic, citable: a finding, decision, or correction | `validate.py` enforces 4 rules + 2 warnings |
| **Question** (`Q-NNNN`) | `memory/questions/` | Forward-action unit: an open uncertainty the next round may address | `validate.py` enforces 3 rules; `render.py` surfaces open Qs |
| **Round** (`RNN/`) | `memory/rounds/` | Bundles plan + verdict for one investigation; verdict opens/closes Qs | `validate.py` enforces 3 mandatory Q-sections in `verdict.md` |
| **STATE.md** | `memory/STATE.md` | Auto-rendered 6-section oracle (headlines / in-flight / open Qs / recently closed / latest round / stats) | Regenerated by `render.py` |
| **Handoff** (out of schema) | `memory/handoffs/` | Session-end scratchpad; not validated, not rendered | See `memory/handoffs/README.md` |

### When to write a new claim

After producing any of:
- A new numerical result you might cite
  (`type: finding`, trust V/S/T)
- A correction or replacement of a prior number
  (`type: correction, trust: V, supersedes: [...]`)
- A research-direction pivot
  (`type: decision, trust: S`)

`validate.py` enforces:
- `decision` → `trust: S` (decisions are choices, not measurable facts)
- `correction` → `trust: V` (replacement must itself be verified)
- `finding` → `V / S / T` all allowed

### When to open a Question

When a round's verdict notes a follow-up that future work should
address but didn't (e.g. CLM-0040 "future round can investigate
G4 inertia" became `Q-0001`). Statuses: `open`, `in-flight`,
`closed-positive`, `closed-negative`, `abandoned`. Closed Qs must
have `closed_round` (existing dir) and `closed_by` (existing claim id).

### Round verdict contract

`memory/rounds/RNN/verdict.md` must contain (mandatory, enforced):
- `## Questions opened (this round)`
- `## Questions closed (this round)`
- `## Questions advanced (this round, status unchanged)`
- `## 给 PI 的话` **(R≥59 only — ADR-0003)**

Recommended (warning if missing): `## TL;DR` + `**Status**:` line.
Briefing soft cap ≤ 30 non-blank lines (warning above; not blocking).
Template at `memory/rounds/_TEMPLATE_VERDICT.md`. Forward-going rounds
should use it. Legacy R01..R38 verdicts have retrofit placeholders for
the 3 mandatory Q-sections; R01..R58 are exempt from the PI briefing
section.

### Agent chat-delivery contract (ADR-0003)

When you close a round (i.e. write `verdict.md`), you **MUST** paste
the body of `## 给 PI 的话` verbatim into the active chat as your
closing turn. Pointing at the file ("see verdict.md", "rendered to
STATE.md", "check the briefing") is **not** compliant.

Why: the PI is a research partner, not a sign-off authority. They
get participation by hearing the briefing in conversation, not by
context-switching to read a file. STATE.md is archival backup.

Format:

> 我已经把简报写进 verdict.md，下面是 `## 给 PI 的话` 全文：
>
> [briefing body verbatim]

This contract is text-only — no tooling detects violations. If you
skip the chat-delivery step, the user loses research-story continuity
even though the file system looks correct.

### Tools

Validation / rendering (run before commits, after closures):

- `python memory/tools/validate.py [--fix]` — claim/question schema +
  Q-section presence in every verdict. `--fix` auto-writes
  `superseded_by` back-edges + flips status.
- `python memory/tools/render.py` — regenerate `memory/STATE.md`.
- `python memory/tools/dual_metric_lint.py [--claim CLM-NNNN]` —
  **CLM-0430 audit guardrail**: fails (exit 1) when a paper-reward-
  ablation claim cites `geo` without `cum_rf`. Run after any
  paper-Eq.14 / gauge-invariance / phi_abs claim.

Atomic ID minting (race-safe vs parallel sessions):

- `python memory/tools/reserve_round.py [--write-plan-stub] [--gc] [--list-active] [--strict-no-active] [--no-warn-active]` —
  next R-number; `--gc` sweeps zombie reserved-empty dirs.
  **R256 followup (2026-05-20)**: atomic mkdir prevents *concurrent*
  duplicate reservation but NOT *re-entry* duplicate work after
  context compression (a post-compression agent that forgot it
  already reserved R<N> in a prior turn will happily spawn R<N+1>
  duplicating work). The state-based pre-flight is the second
  layer of defence:
  - `--list-active` — print rounds with `state: active` + no
    verdict.md, exit without reserving. Run this FIRST in
    autonomous loops or after context compression to detect
    in-flight rounds you may have forgotten.
  - `--strict-no-active` — refuse to reserve (exit 1) if any
    active round exists. Use in autonomous-loop scripts to harden
    against the re-entry failure mode.
  - default — WARN to stderr (not stdout, so `| xargs` scripts
    still parse the N correctly) and proceed. `--no-warn-active`
    silences if intentional.
  - Stale-active detection: a round whose plan.md says
    `state: active` but has a verdict.md is treated as logically
    closed (the verdict is the operational truth). Backfills
    legacy R01-R49 plan-metadata gap without forcing a retrofit.
  Tests: `tests/test_reserve_round.py` (30 cases, pins atomic
  mkdir + active-detection + GC contract).
- `python memory/tools/reserve_claim.py [--stride 5] [--round RNNN] [--type finding]` —
  next CLM-NNNN (CLM-0430 follow-up; replaces error-prone manual
  `ls memory/claims/ | tail` + increment-by-5).

Operational dashboard / lookups:

- `python memory/tools/status.py` — what is training (WSL `ps`),
  what is `state: active` without summary, what's recently scored
  (dual-metric). Replaces ad-hoc polling.
- `python memory/tools/baselines.py [--filter REGEX] [--sort geo|cum_rf] [--match REF_RUN]` —
  scan `results/*/final_eval_summary.json` for measured baselines.
  Use `--match <reference_run>` to find runs with identical
  `env_config` fingerprint. **Use this instead of estimating
  baselines from cross-algo ratios** (which gave R246 the wrong
  -28% framing; true was -11.9% per CLM-0435 anchor).
- `python memory/tools/round_preflight.py R<N> [--latest] [--json]` —
  **plan-time checklist** for a new round. Catches the three
  flow failures the 2026-05-20 session burned compute on:
  (1) plan cites superseded CLM (e.g. CLM-0101 superseded by
  CLM-0108 — R244 SAC plan referenced the older one);
  (2) plan compares to unmeasured baseline / mentions "estimated"
  (R246 estimated-baseline failure → BLOCK exit);
  (3) reward-ablation plan only mentions `geo` not `cum_rf`
  (R242/R246 single-metric framing → BLOCK exit). Also surfaces
  relevant prior CLMs (prior-art INFO). Exit codes:
  0 = clean / INFO-only, 1 = WARN-only, 2 = BLOCK present.
- `python memory/tools/query.py --tag TAG | --best METRIC_NAME` —
  claim ledger lookup.
- `python memory/tools/close_round.py RNN superseded|aborted|completed` —
  housekeeping CLI for closing rounds without ad-hoc scripts.

### Creating a new round / claim

0. **Preflight the plan BEFORE launching training**:
   `python memory/tools/round_preflight.py R<N>`
   Exit code 2 = BLOCK (fix before launch); exit 1 = WARN
   (review before launch); exit 0 = OK. Encodes the 3 failure
   modes from the 2026-05-20 session: superseded-CLM citation,
   estimated baseline, single-metric reward-ablation plan. Costs
   ~50ms; saves ~15 min/round of compute that would have produced
   an unusable verdict.

1. Reserve the round number atomically:
   `python memory/tools/reserve_round.py --strict-no-active`
   (Or `--list-active` first if you want to inspect.) Atomic
   mkdir creates `memory/rounds/R<N>/` and returns N.
   **Never pick a round number by hand** — parallel sessions will
   race. **In autonomous loops or after context compression**, the
   `--strict-no-active` flag refuses to spawn a new round if any
   in-flight round exists (R256 duplicate-work followup, 2026-05-20).
   If `--strict-no-active` exits 1, list the active rounds with
   `--list-active`, decide whether to (a) resume the existing
   round (close it properly first) or (b) explicitly start fresh
   via plain `reserve_round.py` (default mode warns but proceeds).

2. Reserve the claim ID(s) atomically:
   `python memory/tools/reserve_claim.py --round R<N>`
   Writes a minimal stub at `memory/claims/CLM-NNNN.md` that you fill
   in. Don't pick CLM numbers manually — they collide.

3. Look up baselines via `memory/tools/baselines.py`, not by
   estimation. If you can't find a measured baseline for the config
   you need to compare against, **run that baseline** before
   interpreting an ablation result. The 2026-05-20 session burned
   ~10 rounds on a "scalar seed-sensitivity" framing that turned out
   to be a baseline-estimation artifact (CLM-0410 → CLM-0435).

4. **For every paper-reward-ablation claim, cite both metrics**:
   `geo` (project 11-axis v3.1, sanity-check) AND `cum_rf` (paper
   Yang2023 §IV-C, paper-comparable). The two can disagree — the
   2026-05-20 session shipped 7 single-metric claims that needed
   wholesale qualification when the dual-metric audit landed
   (CLM-0430). Run `dual_metric_lint.py` before commit.

5. If the round produces a number whose paper-grade scoring you want
   to reuse, drive it through `python scripts/score_run.py ...`.
   Smart defaults: with a single `--ckpt-dirs` arg, `--label` and
   `--out-dir` are auto-derived from the dir name (CLM-0430 audit
   follow-up).

## Code conventions

### ANDES = WSL only

See `docs/eng-notes/NOTES_ANDES.md`. Windows-side ANDES installs are
historical mis-installs; do not use them.

### Modifying the env

Read `docs/eng-notes/NOTES_ANDES.md` before changing any
`src/andes_rl_kundur/env/andes/*` or `scripts/train.py`. The
`AndesMultiVSGEnvV4` class is paper-faithful and silent-inheritance
bug fixed (R37 / CLM-0040: `ZERO_G4_INERTIA = True` is now explicit).

**V4 vs V5 (R80+)**: V5 (`andes_vsg_env_v5.py`) is a V4 subclass that
swaps plant 风机 (GENROU+ZERO_INERTIA hack / GENCLS) for industry-
standard REGCA1+REECA1. V5 is **paper-deviation** by design (paper
Sec.II "neglect inner loop" → REGCA1 反方向; paper Sec.IV-A 风机
silent → "对齐 paper" 无据). See ADR-0004. V5 ckpt 走 `r80+_*`
namespace, 不污染 V4 ckpt 区. R57+ 全部 SOTA ckpt 依赖 V4
bit-identical reproducibility, 修 V4 / V4Config / base_env /
paper_grade_axes 必须新 round 文档化.

**R83 obs aug**: `base_env` 现支持 area-mean freq obs augmentation
(2 dim) via `V4Config.OBS_AREA_MEAN_FREQ_AUG`. 互斥已解除 (slot
layout 改成绝对索引). 默认关闭 — 开启会改变 obs_dim, 与历史 ckpt 不兼容.

### Modifying paper_grade_axes.py

Asset 4 is paper-cited. Any change requires a new round + new claim
documenting the ranker version. Even a path-only relocation is logged
(R37 recorded the 2026-05-16 move to `src/andes_rl_kundur/evaluation/`).

## Agent skills

### Issue tracker

Issues live in GitHub Issues for this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses default label vocabulary (needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Active research rules

- Caveman Chinese for verdict/plan files (per user preference, see
  `_legacy/CONTEXT.md` style)
- Single ANDES session at a time on Windows (16C/32T workstation), max
  3 parallel WSL python processes
- **Default model env: `andes_vsg_env_v4`** (paper-faithful H₀=100,
  ZERO_G4_INERTIA=True for reproducibility of paper numbers). V5 is
  opt-in for plant-deviation experiments only.
- **No Simulink 1:1 chase** (ADR-0005): R08–R17 forensic 120 min 0
  root cause 已证回报为零. ANDES = single platform of record.
- **V5 ckpt namespace separation**: V5 ckpt 走 `r80+_*`, 不与 V4 ckpt 混.
  Cross-eval 用 `r80_v5_cross_eval.py` 三 plant (V4 / V5_w2_only /
  V5_gencls_fall) 一起跑.
- Regression: `tests/test_v4_env_regression.py` must stay green at
  1e-9 tolerance against the PRE_REFACTOR baseline JSONs
- **Plateau status (R86)**: critic Q is monotone along action axis +
  argmax 在 boundary ±1 (CLM-0148/0149 universal N=6). R57–R82 共
  91 算法侧 trial plateau 已确认结构性, 不是 hyper 调参问题. 突破
  路径在 reward shaping / env physics / classical baseline 补强 (R85),
  不在 algo dim.
- **Novel architecture status (R82)**: TD3-Transformer / TD3-LSTM2 在
  75 ep budget 下均 ≤ R72_w4 baseline (CLM-0144/0145). Transformer
  deterministic-eval collapse 是 known issue.
