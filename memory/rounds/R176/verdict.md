# R176 verdict — Gap 5-10 fixes (full ledger system hardening)

**Date**: 2026-05-19
**Status**: COMPLETED
**Type**: meta / infrastructure
**Wall**: ~75 min (6 gaps, all TDD where applicable)

## TL;DR

Closed the final 6 ledger-system gaps (G5-G10) in one round, completing
the R166→R171→R176 hardening trilogy. Now: git pre-commit hook blocks
bad commits, reusable `close_round.py` CLI replaces one-shot sweep
scripts, soft warnings down from 78 → 49 (-37%), `reserve_round.py
--gc` cleans empty dirs, stale thresholds tightened to project cadence,
research-claim-into-meta-round contract enforced.

Decision anchor: [[CLM-0335]]. 138/138 tests pass, 0 validate errors.

## What changed (6 gap fixes)

| Gap | Approach | Tests added |
|-----|----------|-------------|
| **G5** pre-commit hook | append validate.py to `scripts/githooks/pre-commit` | (smoke-tested) |
| **G6** close_round.py CLI | new module + 3 subcommands + atomic write | 6 |
| **G7** soft-warn cleanup | `TLDR_CUTOFF=59`, `PI_BRIEFING_LINE_CAP 30→40`, decimal-warn R50+ only | — (covered by existing) |
| **G8** reserve_round.py --gc | new function + CLI flag, dogfooded on R173/R174/R175 | 3 |
| **G9** stale thresholds | 14d→3d active, 7d→2d queued | (existing tests updated) |
| **G10** claim into meta round | new warn rule | 3 |

Total: +12 tests, 138 pass.

## Concrete impact on this repo

**Before R176:**
- 78 soft warnings (mix of real and noise)
- ~3 unresolved structural smells (no GC, no commit gate, one-shot sweep scripts)
- Stale thresholds useless (would fire ~400 round-cycles later)

**After R176:**
- 49 warnings (TL;DR/PI/decimal noise gone; remaining are real hints
  or specific data errors)
- 0 errors (maintained from R171)
- All structural smells addressed
- 1 new G10 finding: CLM-0325 (R170 research) emitted into R171 (meta)
  — surfaced for future fix but not blocking R176

## Gaps still NOT addressed

R166 R171 R176 cover 10 gaps. None of the remaining "TODO" items rise
to gap level — they're either out of scope (e.g. wholesale TL;DR
retrofit on R01-R38) or genuinely awaiting evidence (e.g. whether the
4 Q-supersession suggestions are real or false-positive).

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — pure infrastructure, no research Q movement)

## 给 PI 的话

🛠️ **R176 = R166+R171 后最后一轮 ledger 硬化**. 修了 6 个 gap (G5-G10),
全部 TDD。138 tests 全过, 0 errors, soft warns 78→49 (-37%).

具体: (1) `scripts/githooks/pre-commit` 加 validate.py 拦坏 commit;
(2) `memory/tools/close_round.py` reusable CLI (subcmd
`superseded|aborted|completed`, atomic write) 替代每次手写 sweep 脚本;
(3) TL;DR + PI-briefing-length + decimal-noise 三类历史 warn 加 cutoff
退役; (4) `reserve_round.py --gc` 扫 >60min 空 dir 自动 abort, 第一次
跑就清了 R173/R174/R175 (并行 race 残留); (5) stale 阈值 14d→3d / 7d→2d
匹配项目 ~30 rounds/day 节奏; (6) 新 G10 rule 抓 "research claim 写到
meta round"(就是 CLM-0325 在 R171 那种 dual-identity 违规, 现在 validate
会喊).

CLM-0335 是决策 anchor。

**R166+R171+R176 三轮加起来**: ledger 从"有 zombie / 算盘乱 / 噪音淹没"
变成"validate.py 拦门, 静态/动态规则齐全, 噪音降到只剩真信号, parallel
race 自动清"。这套基础设施现在足以支撑 paper writing 阶段而不再出现
"实验做了没记"或"open Q 早就答了没关"的 silent failure。

**R172 训练同时在后台跑** (Q-0020 transient-phase reweighting at s54),
training ckpts (4 best.pt) 已 dumped @ 12:29, 还在 eval 阶段。R176 不依赖
R172 结果。等 R172 出 final_eval_summary.json 后单独 close R172 round。

下一步默认: R176 commit 完, 等 R172 训练 + eval 完, 然后 close R172。
沉默 = wait + monitor。

## Cross-references

- [[CLM-0335]] — R176 decision anchor
- [[CLM-0330]] — R171 decision (parent)
- [[CLM-0316]] — R166 decision (grandparent)
- R166/verdict.md, R171/verdict.md — parent verdicts in the hardening trilogy
