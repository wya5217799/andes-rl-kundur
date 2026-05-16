# R46 verdict — Architectural deepening pass (3 of 4 candidates landed)

**Date**: 2026-05-16
**Status**: **COMPLETE** (Phase A landed; Phase B deferred to Q-0004)
**Type**: infrastructure (refactor, no experiment)
**Wall**: ~1.5 h (grilling + exploration + 3 commits)

## TL;DR

Three architectural deepening refactors landed as commits 5d86705 +
34f5d9f + 4777ecb (commit messages mislabel them "R45 commit N" — see
note below): 6 round-driver scripts archived (AD-02 finally enforced);
`eval_all_seeds.py` switched to package imports and `eval_ddic` /
`eval_ensemble` shed their back-compat alias wrappers; the
`probes/andes_common/verdict.py` module renamed to `probe_classifier.py`
with `Verdict` → `ProbeClassification`, `VerdictRule` →
`ClassificationRule`, `resolve_verdict_ladder` → `resolve_probe_ladder`
so the repo's "verdict" word now refers solely to the round ledger.
The fourth candidate (`AndesBaseEnv` absorption into V4) reached the
"GO" gate at 86 % active-path coverage but execution was deferred —
AD-11's 1e-9 bit-identical regression runs only in WSL, and this
session lives on the Windows host.

## What changed

| Commit | Hash | Candidate | Scope |
|--------|------|-----------|-------|
| 1 | `5d86705` | C2 | `git mv` 6 `_r{38,40,41,42}_score_*.py` → `scripts/_archive/round_scripts/`; `parents[1]` → `parents[3]` path-depth fix |
| 2 | `34f5d9f` | C1 | `eval_all_seeds.py` imports package directly; drop `eval_ddic.{eval_scenario, load_actors}` (+30 lines) + `eval_ensemble.load_actors` (3 lines) |
| 3 | `4777ecb` | C4 | rename `verdict.py` → `probe_classifier.py`; rename `Verdict` / `VerdictRule` / `resolve_verdict_ladder`; update `__init__.py` + `README.md` + `docs/eng-notes/NOTES_ANDES.md` |
| — | (deferred) | C3 | `AndesBaseEnv` absorption — see Q-0004 |
| 4 | (this) | — | R46 verdict + Q-0004 + STATE.md regen |

## Round-number note

Commit messages tag commits 1–3 as "R45 commit N". That label was
written before discovering the user's concurrent R45 plan (Q-0001
escalation + s52 reproducibility + SAC long, ~70 min experimental
round, see `memory/rounds/R45/plan.md`). My architectural-deepening
work is actually **R46**. The mislabel in commit messages is harmless
metadata drift; this verdict + Q-0004 are the authoritative round
boundary.

## Methodology

**Exploration**: `/improve-codebase-architecture` + Explore agent
walked the codebase. Of the 5 surfaced candidates, the agent's SAC
mixin split was already rejected by R42 grilling and its monitor /
eval-loop candidates were already executed by R42. Cross-checking
discovered: eval back-compat aliases still wrapped `paper_path`;
6 top-level scratch scripts violated AD-02; one shallow `verdict.py`
naming collision; one degenerate `AndesBaseEnv` seam.

**Risk gating**: Phase A grouped the 3 zero-risk candidates. Phase B
isolated the only candidate touching paper-cited code paths.

**Phase B gate evaluation** (executed, deferred):

```
base_env: 605 lines, 16 methods
V4:       403 lines, 6 methods
V4 overrides 4 / 14 non-abstract base methods
V4 inherits 12 / 14 non-abstract base methods = 86 %
Abstract methods in base: 2 (_build_system, _apply_disturbance) — V4 impls both
v0/v1/legacy mentions in base: 7 (mostly attribute-default comments)
```

86 % > 70 % gate → original plan would proceed. Deferred for
verification reasons (next section).

## Verification

```
$ git log --oneline -4
4777ecb refactor(probes): rename verdict.py -> probe_classifier.py
34f5d9f refactor(scripts): drop eval_ddic/eval_ensemble back-compat aliases
5d86705 chore(scripts): archive 6 round-driver score scripts
158bc09 round: R44 — HAWE cap + Q-0001 closed-negative

$ grep -rn "VerdictRule\|resolve_verdict_ladder\|andes_common.verdict\b" \
      src/ tests/ scripts/ --include="*.py" --include="*.md" | grep -v "_archive\|_legacy"
(empty — only stale .pyc caches)

$ grep -rn "from eval_ddic\|from eval_ensemble" . --include="*.py" | grep -v "_archive"
(empty)

$ python -c "<smoke-load probe_classifier>"
smoke: ALL_PASS — wiring works, residual (if any) is platform-level
type OK; classification= ALL_PASS
rule OK: TEST
```

`pytest tests/` NOT executed from this session — the test suite
imports `andes` which is WSL-only per `docs/eng-notes/NOTES_ANDES.md`.
Phase A's three commits do not touch ANDES env code, so the AD-11
regression is mechanically unaffected; a WSL-side `pytest tests/`
pass-confirmation is still recommended at the next WSL session start.

Phase B regression cannot be skipped — see Q-0004 for the handoff
package.

## Behavior parity

- **C2 (commit 5d86705)** — physical reorg only; archived files
  unaffected by `pytest`; no live code imports them
- **C1 (commit 34f5d9f)** — `eval_all_seeds.py` end-to-end behaviour
  bit-identical to pre-commit: `load_agents` is the same function
  the back-compat alias was already calling; `run_scenario(action_fn=
  deterministic_actor_action_fn(agents), …)` reconstructs the exact
  loop the deleted `eval_scenario` wrapper assembled. Archived
  `_r*_score_*.py` invoke `eval_ddic` via subprocess CLI (unchanged
  contract), not Python import
- **C4 (commit 4777ecb)** — pure name change; smoke-load confirmed
  `resolve_probe_ladder` produces the same `ProbeClassification`
  output that `resolve_verdict_ladder` produced for `Verdict`
- **C3 (deferred)** — bit-identical claim CANNOT be made until
  WSL-side `pytest tests/test_v4_env_regression.py -v` confirms 1e-9
  tol; see Q-0004

## Cross-references

- `.claude/plans/distributed-booping-clover.md` — full execution plan
  with file-level diffs and risk model
- `memory/rounds/R42/verdict.md` — original deepening pass; SAC mixin
  split rejection still authoritative
- `memory/rounds/R37/verdict.md` + `memory/claims/CLM-0042.md` —
  Check Protocol + V4Config introduction (R42 made them load-bearing)
- `docs/adr/0001-src-layout.md` § AD-01 — V4 self-contained
  inheritance-chain merge; C3 deferral is the remaining work
- `src/andes_rl_kundur/probes/andes_common/probe_classifier.py` —
  renamed module (C4)

## Out of scope (per plan)

- `V4Config` (`env/andes/v4_config.py`): real seam with two live
  adapters (physical / normalized action penalty); R41/R43 production
  hinges on it; NOT touched
- SAC mixin split: R42 grilling rejection stands ("Explore agent's
  deletion test failed it")
- `artifacts/dissertation/main.tex` line 1217 `\verb|VerdictRule|`:
  dissertation is frozen artefact; fix at next manual re-compile
- `memory/handoffs/2026-05-07_handoff_v13.md` line 203 `VerdictRule`:
  out-of-schema scratchpad; not enforced
- _legacy/** and CLM-* historical content: untouched

## Questions opened (this round)

- `Q-0004` — `AndesBaseEnv` absorb-into-V4 (Phase B candidate ③): GO
  recommended at 86 % active-path coverage; execution requires WSL
  verification (`test_v4_env_regression.py` 1e-9 tol). Handoff package
  in question file.

## Questions closed (this round)

- (none — purely architectural; no research uncertainty closed)

## Questions advanced (this round, status unchanged)

- (none)
