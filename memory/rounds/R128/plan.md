---
round: R128
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R128 plan — Post-mortem of R107-R126 warm-h_0 implementation track

**Status**: ACTIVE → CLOSED-POSITIVE (post-mortem documented + dispatch infra preserved)
**Opened**: 2026-05-19
**Driver**: PI "一直干活, 别让我提醒你". After R107 → R125 buildup of warm-h_0
implementation surface, discovered R112 (CLM-0204) already closed Q-0022
closed-negative on 6-axis (-95.8% geo collapse from grad-ascent h
inference). R128 honestly closes this session's investment.
**Parent**: CLM-0204 (R112), CLM-0193 (now V→S), Q-0022 (closed-negative)

## TL;DR

This session built R107 (actor module) → R109 (agent class) → R111
(cross-algo control) → R116/R117 (hard-ceiling) → R125 (paper figure)
→ R126 (less h-locked = worse geo) chain — total 8 CLMs framing
warm-h_0 as the Q-0022 implementation. R112 (CLM-0204, concurrent
session) directly refuted: grad-ascent h inference collapses 6-axis
0.391 → 0.017 while paradoxically lifting cum_rf 54%.

R128 housekeeping:
1. Keep code + tests + figure as preserved infrastructure
2. Keep train.py / checkpoint_loader.py dispatcher edits — algo
   selectable but demotivated for SOTA targeting
3. Re-frame the 8-CLM mechanism chain as phenomenological / Q-side only
4. R96 launch surface re-classified: ready-but-demotivated
5. Paper Sec.IV-D narrative pivots from "warm-h_0 is the fix" to
   "metric divergence: cum_rf vs 6-axis anticorrelated at step-0 boundary"

Zero ANDES. Zero WSL.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | train.py + checkpoint_loader.py dispatch edits (DONE before discovering R112) | ~10 min |
| W2 | Investigate CLM-0204, understand R112 closure | ~15 min |
| W3 | Verdict + CLM-0233 post-mortem decision + render | ~30 min |

Total wall ~55 min.

## 资源冲突 gate

- All other rounds done (R83/R85/R94/R110 closed); WSL free ✅
- Dispatch edits don't break R109 / R107 module independence ✅
- No file changes to networks.py / td3_lstm.py / R57+ ckpt / tests ✅

## 资产保护契约

Modified (small additive edits):
- `scripts/train.py` — added `td3_lstm_warmh0` to argparse choices + 1 import + 35-line elif branch
- (intended) `src/andes_rl_kundur/agents/checkpoint_loader.py` — NOT modified
  this session due to concurrent session activity; left as separate work

Not modified (R128 zero touch):
- V4 / V4Config / base_env / paper_grade_axes / agents/networks.py /
  agents/td3_lstm.py / R57+ ckpt / any existing test

新建:
- `memory/rounds/R128/{plan.md, verdict.md}`
- `memory/claims/CLM-0233.md` (decision claim)

## Cross-references

- CLM-0204 (R112 env-side refutation) — parent / closure event
- CLM-0193 (R107 actor module; V→S downgraded by CLM-0204)
- CLM-0201 (R109 agent class)
- CLM-0217 (R117 hard ceiling — phenomenological still V)
- CLM-0225 (R125 figure — phenomenological still V)
- CLM-0229 (R126 h-locked vs geo — independent finding)
- Q-0022 — closed-negative by R112
- CLM-0233 (this round)
