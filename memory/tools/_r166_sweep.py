"""One-shot: R166 housekeeping sweep.

Closes 26 zombie rounds + 3 stale Qs identified in R166/plan.md.

- 10 rounds with plan.md → flip state to terminal (superseded/aborted/completed)
- 12 reserved-empty dirs → create minimal plan.md state=aborted
- 4 verdict-only dirs → create minimal plan.md state=completed
- 2 minimal verdicts written (R143, R149) where state=completed requires it
- 3 questions flipped to closed-*/abandoned

Ran once during R166 sweep (2026-05-19). Kept in repo as audit artifact.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

TODAY = "2026-05-19"
ROUNDS_DIR = Path(__file__).resolve().parents[1] / "rounds"
QUESTIONS_DIR = Path(__file__).resolve().parents[1] / "questions"

# Rounds with plan.md → flip state in-place (preserve body)
FLIPS_WITH_PLAN: list[tuple[str, dict]] = [
    ("R115", {"state": "superseded", "superseded_by_round": "R103",
              "superseded_note": "paper_strict_pure closed-negative by CLM-0203 (R103)"}),
    ("R118", {"state": "superseded", "superseded_by_round": "R113",
              "superseded_note": "Toggler-Line_8 ablation closed-negative by CLM-0215 (R113)"}),
    ("R119", {"state": "aborted",
              "abort_reason": "wider action bound replaced by R132 α-sweep (CLM-0218)"}),
    ("R120", {"state": "aborted",
              "abort_reason": "depended on R118; multi-seed moot after R118 superseded"}),
    ("R122", {"state": "superseded", "superseded_by_round": "R142",
              "superseded_note": "distributional critic first-train superseded by R142 QR-LSTM (CLM-0275)"}),
    ("R123", {"state": "superseded", "superseded_by_round": "R127",
              "superseded_note": "AFE critic absorbed into stacked path R127 (CLM-0234)"}),
    ("R131", {"state": "aborted",
              "abort_reason": "triple-stack queue never fired; R154 SOTA changed direction (CLM-0295)"}),
    ("R143", {"state": "completed",
              "closed_note": "QR-LSTM fixed-loss results recorded in CLM-0275"}),
    ("R144", {"state": "aborted",
              "abort_reason": "stacked QR+AFE replaced by R127 path; R154 SOTA closes ensemble direction"}),
    ("R149", {"state": "completed",
              "closed_note": "200ep over-training regression; closed-negative per plan"}),
]

# Reserved-empty dirs (no plan.md, no verdict) → minimal stub plan.md aborted
RESERVED_EMPTY_ABORT: list[tuple[str, str]] = [
    ("R138", "reserved-empty, parallel-session race during R136 sprint"),
    ("R140", "reserved-empty, parallel-session race during R141 sprint"),
    ("R146", "reserved-empty, queue-never-fired"),
    ("R147", "reserved-empty, queue-never-fired"),
    ("R148", "reserved-empty, queue-never-fired"),
    ("R155", "reserved-empty during ensemble exploration (R152-R154 sprint)"),
    ("R157", "reserved-empty (parallel session reserved but never planned)"),
    ("R159", "reserved-empty (parallel session race)"),
    ("R161", "reserved-empty (parallel session race)"),
    ("R162", "reserved-empty (parallel session race)"),
    ("R164", "reserved-empty (parallel session race)"),
    ("R167", "reserved-empty (parallel session reserved post-R165 project-complete)"),
]

# Verdict-only dirs (parallel session wrote verdict without plan) → stub plan.md completed
VERDICT_ONLY_COMPLETE: list[str] = ["R158", "R160", "R163", "R165"]


def _read_plan(round_name: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Raises if missing."""
    path = ROUNDS_DIR / round_name / "plan.md"
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def _write_plan(round_name: str, fm: dict, body: str) -> None:
    path = ROUNDS_DIR / round_name / "plan.md"
    dump = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{dump}\n---\n{body.lstrip(chr(10))}"
    if not out.endswith("\n"):
        out += "\n"
    path.write_text(out, encoding="utf-8")


def flip_existing_plan(round_name: str, updates: dict) -> None:
    fm, body = _read_plan(round_name)
    fm.update(updates)
    fm["closed"] = TODAY
    _write_plan(round_name, fm, body)
    print(f"FLIP  {round_name}: state={updates['state']}")


def write_stub_aborted(round_name: str, reason: str) -> None:
    round_dir = ROUNDS_DIR / round_name
    round_dir.mkdir(exist_ok=True)
    fm = {
        "round": round_name,
        "state": "aborted",
        "opened": TODAY,
        "closed": TODAY,
        "supersedes_rounds": [],
        "superseded_by_round": None,
        "abort_reason": reason,
        "superseded_note": None,
    }
    body = (
        f"# {round_name} plan — aborted (R166 sweep)\n\n"
        f"**Status**: ABORTED\n\n"
        f"## Reason\n\n{reason}\n\n"
        f"## Audit\n\nCreated by `memory/tools/_r166_sweep.py` during R166 "
        f"housekeeping ({TODAY}). See R166 plan + verdict for context.\n"
    )
    _write_plan(round_name, fm, body)
    print(f"STUB  {round_name}: aborted ({reason[:50]}...)")


def write_stub_completed(round_name: str) -> None:
    """Verdict-only dir: write minimal plan.md state=completed pointing at
    the existing verdict.md so validate.py's terminal-fields rule is met."""
    round_dir = ROUNDS_DIR / round_name
    # find verdict file (may be `verdict.md` or `*verdict*.md`)
    verdict = round_dir / "verdict.md"
    if not verdict.exists():
        cand = sorted(round_dir.glob("*verdict*.md"))
        if cand:
            verdict = cand[0]
    fm = {
        "round": round_name,
        "state": "completed",
        "opened": TODAY,
        "closed": TODAY,
        "supersedes_rounds": [],
        "superseded_by_round": None,
        "abort_reason": None,
        "superseded_note": None,
    }
    body = (
        f"# {round_name} plan — completed (R166 retro-stub)\n\n"
        f"**Status**: COMPLETED (verdict written first by parallel session)\n\n"
        f"## Note\n\nThis plan.md was retro-added by R166 sweep to satisfy "
        f"the new state-machine schema. The work was recorded directly in "
        f"`{verdict.name}` by a parallel session; see that file for full "
        f"context.\n"
    )
    _write_plan(round_name, fm, body)
    print(f"COMPL {round_name}: retro-stub for parallel-session verdict")


def write_minimal_verdict(round_name: str, body_text: str) -> None:
    """For state=completed rounds that lack verdict.md, write a minimal one
    with the 3 mandatory Q-sections + PI briefing per ADR-0003."""
    path = ROUNDS_DIR / round_name / "verdict.md"
    if path.exists():
        print(f"SKIP-V {round_name}: verdict.md already exists")
        return
    path.write_text(body_text, encoding="utf-8")
    print(f"VRDCT {round_name}: minimal verdict written")


R143_VERDICT = """# R143 verdict — td3_qr_lstm s54 FIXED-loss training, results in CLM-0275

**Date**: 2026-05-19
**Status**: COMPLETED (results jointly recorded with R142 in CLM-0275)
**Wall**: ~15 min ANDES wave

## TL;DR

R143 trained td3_qr_lstm at s54 with the quantile-Huber loss magnitude
fix applied (vs R142's buggy form). Geo result = 0.3843, essentially
identical to R142's 0.3845. Both became ingredient constituents of the
R154 4-way ensemble (CLM-0295).

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none — CLM-0275 closes Q-0019 distributional-critic question)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

R143 是 R142 的 fixed-loss 复跑，证明 quantile-Huber 的 bug fix 不影响
最终 geo 表现（0.3843 vs 0.3845）。两个 ckpt 后来都成为 R154 SOTA
4-way ensemble 的 constituent。R166 sweep 时补写本 verdict，把这个
round 从 in-flight 翻成 completed。

(Retro-written by R166 sweep 2026-05-19.)
"""

R149_VERDICT = """# R149 verdict — td3_qr_lstm s54 200ep horizon = over-training regression

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE (longer horizon hurts; R72_w4 0.391 unbeaten)

## TL;DR

R149 tested whether extending the training horizon from R72_w4's
75-episode budget to 200 episodes would let the QR-LSTM critic
discover a better policy. Result: over-training regression — geo
drops below R72_w4 baseline. The R149 plan.md self-declared this
closed-negative; R166 sweep retro-writes the verdict in canonical form.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none — null result on horizon-extension hypothesis; no Q was open
  for this specific question)

## Questions advanced (this round, status unchanged)

- Q-0014 (algorithm-side breakthrough) — R149 contributes another
  negative datapoint against single-algorithm interventions

## 给 PI 的话

R149 试了"训久一点能不能突破 plateau"，结论是不行（200ep 反而比
75ep 差）。这进一步坐实 R57-R154 的 plateau finding：单算法路径已经
exhausted，集成是唯一突破口（CLM-0280, CLM-0295）。R166 sweep 时补
verdict 把这轮正式 closed-negative。

(Retro-written by R166 sweep 2026-05-19.)
"""


def close_question(q_id: str, new_status: str, closed_by: str, note: str) -> None:
    """Flip an open Question to closed/abandoned with audit fields."""
    path = QUESTIONS_DIR / f"{q_id}.md"
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        print(f"FAIL-Q {q_id}: no frontmatter")
        return
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    fm["status"] = new_status
    fm["closed_round"] = "R166"
    fm["closed_by"] = closed_by
    fm["closed_date"] = TODAY
    fm["closed_note"] = note
    dump = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{dump}\n---\n{body.lstrip(chr(10))}"
    if not out.endswith("\n"):
        out += "\n"
    path.write_text(out, encoding="utf-8")
    print(f"Q-CLOSE {q_id}: {new_status} by {closed_by}")


def main() -> int:
    print("=== Phase B1: flip plan-having zombies ===")
    for name, updates in FLIPS_WITH_PLAN:
        flip_existing_plan(name, updates)

    print("\n=== Phase B2: stub reserved-empty as aborted ===")
    for name, reason in RESERVED_EMPTY_ABORT:
        write_stub_aborted(name, reason)

    print("\n=== Phase B3: stub verdict-only as completed ===")
    for name in VERDICT_ONLY_COMPLETE:
        write_stub_completed(name)

    print("\n=== Phase B4: minimal verdicts for completed rounds ===")
    write_minimal_verdict("R143", R143_VERDICT)
    write_minimal_verdict("R149", R149_VERDICT)

    print("\n=== Phase B5: close stale questions ===")
    # Q-0014 asked whether algorithm-side could break the plateau. CLM-0295
    # answers YES (via ensemble, +5.4%). closed-positive is correct — the
    # question is answered affirmatively; the conditional ("only via
    # ensemble, not via single algo") is captured in closed_note.
    close_question("Q-0014", "closed-positive", "CLM-0295",
                   "R154 ensemble (CLM-0295) gives positive answer conditional "
                   "on the mechanism: single-algo cannot break plateau, but "
                   "cross-algo same-seed ensemble does (+5.4%).")
    close_question("Q-0017", "abandoned", "CLM-0144",
                   "TransformerActor 路线 R82 后未跟进; CLM-0144 documents "
                   "deterministic-eval collapse; deprioritised in favour of "
                   "ensemble path (R154 SOTA).")
    close_question("Q-0019", "closed-negative", "CLM-0275",
                   "R142 td3_qr_lstm trained at s54 = geo 0.3845, essentially "
                   "matches R72_w4 baseline 0.3908. Distributional QR critic "
                   "does NOT break the monotone-Q pathology — same plateau.")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
