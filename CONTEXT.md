# CONTEXT — andes-rl-kundur

**Purpose:** canonical domain glossary for this repo.
**Glossary last updated:** 2026-08-12.
**Navigation role clarified:** 2026-07-29.

This file captures terms and decisions that are not derivable from the code
alone. For research-state facts (numerical results, round verdicts, claims),
see `memory/STATE.md`. For research-process rules, see `CLAUDE.md`. Accepted
architecture decisions live as individual records in `docs/adr/`.

---

## Glossary

### `title-goal line`
The one active manuscript line whose plant object, agent identity, action,
training semantics, and evaluation are jointly designed to support every term
in a fixed title.  An old line is not made title-compatible by renaming its
actors or combining its claims with another line.

### `Yang-compatible successor line`
A fresh title-goal line that preserves Yang-style one-VSG-one-actor ownership,
direct inertia/droop actions, and local-plus-neighbour execution while changing
one prospectively declared benchmark or learning question. Historical code may
be revalidated; historical checkpoints, values, claims, and prose do not move.

### `decoupling-oriented` (fixed conference title)
A physical input-output claim: common/differential cross-response and
disturbance-driven inter-VSG differential motion improve with common-mode
no-harm. A coordinate transform, reward increase, or P/Q terminology is not
this claim.

### `evidence line`
A frozen manuscript line retained for its bounded claims, negative results,
implementation assets, and methodological lessons.  It is not selectable for
new execution and cannot supply headline evidence to a successor line.

### `implementation reuse` / `evidence transfer`
Implementation reuse adapts code, contracts, probes, or evaluation plumbing
and revalidates them prospectively on a new object.  Evidence transfer moves
old checkpoints, result values, claims, or manuscript language into a new
line.  The former is allowed by the new line's gates; the latter is forbidden.

### `Project Learning Registry`
The non-authoritative `learning/` asset that maps transferable foundations
needed to understand this repository. It is a learning graph, not a project
glossary, source index, evidence ledger, or learner-progress record.

### `Foundation Atom`
A precise, transferable STEM or research-method concept selected because this
repository uses it. Project-local names remain Context terms and point to
Foundation Atoms through `used-in` relations and repository anchors.

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
  R59 onward, the top section is lifted from the newest briefing. Legacy
  rounds render `## 给 PI 的简报（最新一轮）`; R317+ renders the identifier-free
  `## 给你的研究汇报` without glossary injection. Followed
  by the legacy 6 sections (headlines / in-flight / open Qs / recently
  closed / latest round / stats) plus `## 历史简报` at the bottom.
  Reads claims + questions + rounds + `memory/glossary.yml`.
- `memory/handoffs/` is **out of schema** — informal session-end
  scratchpad, not read by `validate.py` or `render.py`. See
  `memory/handoffs/README.md`.
Full design rationale: `memory/rounds/R39/plan.md`.

### `PI 简报` / 人话汇报层
The mandatory `## 给 PI 的话` section in each post-R59 verdict. ADR-0003
introduced it; ADR-0011 replaces its forward format from R317 onward with
three reader questions:

1. **发生了什么** — the problem and the change, in complete natural Chinese
2. **这说明什么** — what passed, what it supports, and what remains unknown
3. **下一步做什么** — the default next action and the condition for stopping

This is a separate reader-facing layer, not a shortened technical report. It
contains no English abbreviation, repository ID, filename, code name, or
obvious specialist term. A number remains only when it directly communicates
improvement, deterioration, or pass/fail. Exact terminology and data stay in
the feed, claim, results, and technical verdict skeleton. `render.py` lifts
the latest briefing into STATE.md.

### `术语速查` / glossary inline-annotation (legacy briefing support)
`memory/glossary.yml` maps project jargon to ≤ 30-char definitions.
`render.py` annotates each term on **first occurrence per legacy briefing**
as `term(definition)`; subsequent uses bare. Goal: PI never hits an
unexplained acronym in the briefing. ASCII-word lookarounds make the
match Chinese-safe (`用LSTM时` matches `LSTM`). New R317+ briefings reject
such terms before rendering; the glossary remains for immutable history.

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
a historical mis-install; do not use. Formal concurrency has no fixed process
count: every new evidence round measures and freezes a whole-host budget, pins
native numerical threads to one, and includes capacity reserved by other
executing manuscript lines. R23's contention failure remains a reason for the
capacity probe, not a permanent three-process ceiling.

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

Frozen 2026-05-19 migration snapshot (AD-01 … AD-14), preserved for audit in
`_legacy/CONTEXT_AD01-AD14.md`. Not current decision authority; current
decisions live in `docs/adr/`.

---

## What this CONTEXT.md is not

- Not a status report — see `memory/STATE.md` for current numerical claims.
- Not a how-to — see `CLAUDE.md` for research-process rules and
  `docs/eng-notes/NOTES_ANDES.md` for ANDES engineering notes.
- Not a changelog — see git log + `memory/rounds/` for history.
- Not an audit trail — see `_legacy/CONTEXT.md` (frozen 2026-05-08).