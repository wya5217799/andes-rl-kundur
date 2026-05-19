# R166 verdict — Research workflow asymmetry fix + 26-round housekeeping sweep

**Date**: 2026-05-19
**Status**: COMPLETED
**Type**: meta / infrastructure
**Wall**: ~2 hr (design + TDD + sweep)

## TL;DR

Closed the asymmetric open/close cost in the round-lifecycle workflow.
Added a 5-state machine (active / queued / completed / superseded /
aborted) on `RNNN/plan.md` frontmatter, with validate.py enforcement
and render.py state-aware grouping. Swept 26 zombie rounds (16 known
+ 10 discovered mid-sweep from parallel session) and closed 3 stale
questions. Full design + sweep recorded in [[CLM-0316]].

## Why this matters

STATE.md was lying to us. The `## In-Flight` section showed 11 rounds
"in progress" but only 1 was actually being worked on (R156); the
other 10 had been superseded, aborted, or queued-but-never-fired
weeks ago. The same root cause was creating new zombies even mid-
session — while writing this round's design, a parallel session
reserved R158-R167 and only populated 4 of them. Without the fix,
this drift compounds every week.

## What changed

**Tooling (Phase A):**
- `memory/tools/validate.py` — 3 new hard rules + 2 soft warnings
  for the round state machine
- `memory/tools/render.py` — STATE.md `## In-Flight` replaced by
  `## 在跑` + `## 排队` + optional `## ⚠️ 疑似 stale`
- `memory/tools/reserve_round.py` — new plan-stub writes YAML
  frontmatter with `state: active` + `opened: <today>` by default
- `memory/tools/_backfill_round_state.py` — one-shot, backfilled
  119 legacy plan.md files with state/opened derived from git log
- 14 new pytest cases (116 total pass)

**Sweep (Phase B), executed by `_r166_sweep.py`:**
- 10 rounds with plan.md flipped to terminal state
- 12 reserved-empty dirs stubbed as `aborted`
- 4 verdict-only dirs (parallel session, no plan.md) stubbed as
  `completed`
- 2 minimal verdicts retro-written (R143, R149)
- R21's non-canonical verdict filename renamed to `verdict.md` and
  retrofitted with 3 Q-section placeholders
- 3 stale Qs closed (Q-0014 positive, Q-0017 abandoned, Q-0019 negative)

## Numbers after sweep

- `validate.py`: all R166-introduced rules pass cleanly
- STATE.md `## 在跑`: 1 round (R156, the one truly active per
  parallel session)
- STATE.md `## 排队`: 0 rounds
- STATE.md `## ⚠️ 疑似 stale`: 0 rounds (everything backfilled with
  recent dates; staleness kicks in 14 d forward)
- Open Qs: 6 (was 9; 3 closed)
- Round count: 145 → 145 + R166 = 146 (no dirs removed, all flipped)

## Questions opened (this round)

(none — meta/infra round, no new research question raised)

## Questions closed (this round)

- Q-0014 closed-positive by CLM-0295 (algorithm-side breakthrough: yes
  via cross-algo ensemble, no via single algo)
- Q-0017 abandoned by CLM-0144 (Transformer route deprioritised after
  R82; deterministic-eval collapse known)
- Q-0019 closed-negative by CLM-0275 (distributional QR critic matches
  baseline, does not break monotone-Q pathology)

## Questions advanced (this round, status unchanged)

- (none directly — meta round does not move research Qs)

## 给 PI 的话

R166 是 meta round — 修了 ledger 系统自己的 asymmetric open/close
cost。问题: `reserve_round.py` 开一个 round 一行命令秒完成,但关一个
需要写完整 `verdict.md`(3 Q-sections + PI briefing),所以被 supersede
/废弃/排队的 round 永远漂着。STATE.md `## In-Flight` 显示 11 个"在跑",
真活的就 R156 一个;并行 session 还在我做 design 时又新开了 R158-R167,
4 个写 verdict 6 个空。

修法: 5-state 机器(active/queued/completed/superseded/aborted)写到
`plan.md` YAML frontmatter,terminal 状态各有自己的轻量退出路径,不要
求全套 verdict 仪式。validate.py 加 5 条规则(3 hard 2 soft),render.py
把"在跑/排队/⚠️ 疑似 stale"分开展示。

清扫了 26 zombie round + 3 stale Q。STATE.md 现在 `## 在跑` 只有 R156
一个,准了。

往前看: 你之前提的"研究是不是 PROJECT COMPLETE"(R163/R165 verdict 说
是) — 现在 ledger 状态干净了, paper writing 阶段不会被假"in-flight"
误导去重跑实验。CLM-0316 是这一轮的决策 anchor。

下一步默认: 沉默 = 我等你下达写 paper 指令(已经 R165 verdict 说
PROJECT COMPLETE)。

## Risks / open issues

- 6 pre-existing CLM errors (CLM-0256/0269/0300/0305/0310/0315) about
  missing `metric.kind` are out of scope for R166. They were emitted
  by parallel sessions without following the F5 audit rule. Should
  be filed as a follow-up housekeeping item.
- Backfilled `opened` dates default to first git-touch, which is mostly
  2026-05-17 to 2026-05-19. Staleness warnings will start firing in
  ~2 weeks for any round still active. That's the intended forcing
  function.

## Cross-references

- [[CLM-0316]] — main decision anchor for R166
- ADR-0003 — PI briefing contract (unchanged; still required for
  state=completed)
- `memory/rounds/R166/plan.md` — full design spec (4 sections,
  user-approved 2026-05-19)
- `memory/tools/_r166_sweep.py` — sweep script (audit artifact)
