"""One-shot: R171 cleanup sweep.

Closes:
- R168/R169/R170 reserved-empty (parallel-session race during R171 design)
- R144/R147/R167 orphans (eval results exist but my R166 sweep misclassified
  R144/R167 as aborted; R147 was never closed)
- R156/R157 (eval results, documented in CLM-0300/0310 but rounds themselves
  never closed)
- Q-0014 flip: closed-positive → closed-partial (R171 Gap 3)
- Q-0023 close: closed-positive by CLM-0256 (mag-PI matches droop)

Kept in repo as audit artifact (one-shot).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
TODAY = "2026-05-19"
BASE = Path(__file__).resolve().parents[1]
ROUNDS = BASE / "rounds"
QUESTIONS = BASE / "questions"


def _read(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def _write(path: Path, fm: dict, body: str) -> None:
    dump = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{dump}\n---\n{body.lstrip(chr(10))}"
    if not out.endswith("\n"):
        out += "\n"
    path.write_text(out, encoding="utf-8")


def stub_aborted(name: str, reason: str) -> None:
    rd = ROUNDS / name
    rd.mkdir(exist_ok=True)
    fm = {
        "round": name, "state": "aborted", "opened": TODAY, "closed": TODAY,
        "supersedes_rounds": [], "superseded_by_round": None,
        "abort_reason": reason, "superseded_note": None,
    }
    body = (
        f"# {name} plan — aborted (R171 sweep)\n\n"
        f"**Status**: ABORTED\n\n## Reason\n\n{reason}\n\n"
        f"## Audit\n\nCreated by `memory/tools/_r171_sweep.py` during R171 "
        f"gap-fix sweep ({TODAY}).\n"
    )
    _write(rd / "plan.md", fm, body)
    print(f"STUB-A {name}")


def stub_completed_from_result(name: str, geo: float, note: str) -> None:
    """For a round whose plan.md exists but state is wrong (was marked
    aborted in R166 sweep but actually has eval result), flip to
    completed and write a minimal verdict."""
    plan = ROUNDS / name / "plan.md"
    if plan.exists():
        fm, body = _read(plan)
        fm["state"] = "completed"
        fm["closed"] = TODAY
        fm["abort_reason"] = None  # supersede the wrong R166 reason
        fm["superseded_note"] = (
            f"R166 sweep wrongly marked aborted; R171 Gap 1 detection "
            f"surfaced eval result (geo={geo:.4f}). Flipped to completed."
        )
        _write(plan, fm, body)
        print(f"FLIP-C {name}: state=completed (geo={geo:.4f})")
    else:
        # No plan: write stub
        fm = {
            "round": name, "state": "completed", "opened": TODAY, "closed": TODAY,
            "supersedes_rounds": [], "superseded_by_round": None,
            "abort_reason": None, "superseded_note": None,
        }
        body = (
            f"# {name} plan — completed (R171 retro-stub)\n\n"
            f"Created retroactively by R171 sweep: this round had eval "
            f"output (geo={geo:.4f}) but no plan/verdict. See verdict.md.\n"
        )
        _write(plan, fm, body)
        print(f"STUB-C {name}: state=completed (geo={geo:.4f})")

    verdict = ROUNDS / name / "verdict.md"
    if not verdict.exists():
        verdict.write_text(
            f"# {name} verdict — retro from R171 sweep\n\n"
            f"**Date**: {TODAY}\n**Status**: CLOSED-NEGATIVE (geo={geo:.4f}, "
            f"below R72_w4 baseline 0.391)\n\n"
            f"## TL;DR\n\n{note}\n\n"
            f"## Questions opened (this round)\n\n(none)\n\n"
            f"## Questions closed (this round)\n\n(none)\n\n"
            f"## Questions advanced (this round)\n\n"
            f"- Q-0014 (algorithm-side breakthrough) — contributes another "
            f"negative datapoint against single-algorithm interventions\n\n"
            f"## 给 PI 的话\n\n"
            f"R171 sweep 时通过 Gap 1 (results-orphan detection) 发现 "
            f"{name} 有 eval 结果 (geo={geo:.4f}) 但 ledger 里没记。"
            f"补 verdict 把这轮正式 closed-negative。结果是另一个 plateau "
            f"negative datapoint, 没改变 R154 SOTA(当前最好水平) 0.4119 主结论。\n\n"
            f"(Retro-written by R171 sweep {TODAY}.)\n",
            encoding="utf-8",
        )
        print(f"VRDCT  {name}: retro verdict written")


def update_question(qid: str, **fields) -> None:
    """Merge fields into Q frontmatter."""
    path = QUESTIONS / f"{qid}.md"
    fm, body = _read(path)
    fm.update(fields)
    _write(path, fm, body)
    print(f"Q-FLIP {qid}: {fields.get('status')}")


def main() -> int:
    print("=== Phase B1: parallel-race empty dirs ===")
    for name in ("R168", "R169", "R170"):
        stub_aborted(name, "reserved-empty during R171 design sprint (parallel session race)")

    print("\n=== Phase B2: results-orphans surfaced by Gap 1 ===")
    stub_completed_from_result(
        "R144", 0.0100,
        "R144 stacked QR+AFE actor at s54 — geo=0.0100 collapse "
        "(LS1=0, LS2=0). R166 sweep originally marked aborted but "
        "training had completed with COLLAPSE result; R171 Gap 1 "
        "detection (results-orphan rule) caught the misclassification."
    )
    stub_completed_from_result(
        "R147", 0.0100,
        "R147 QR-AFE revisit at s54 — geo=0.0100 collapse, same pattern "
        "as R144. R166 sweep marked aborted reserved-empty but eval "
        "summary exists. Flipped to closed-negative by R171."
    )
    stub_completed_from_result(
        "R167", 0.0502,
        "R167 td3+LSTM h32 at s54 — geo=0.0502 partial collapse "
        "(LS1=0, LS2=0.252). Smaller hidden size (h32 vs canonical h64) "
        "breaks training. R166 sweep marked aborted reserved-empty but "
        "eval summary exists."
    )

    # R156/R157 are referenced by CLM-0300 (R158 round) but their own
    # rounds were never closed. Flip them to state=superseded by R158.
    print("\n=== Phase B3: R156/R157 superseded by R158 (CLM-0300 documents) ===")
    for name in ("R156", "R157"):
        plan = ROUNDS / name / "plan.md"
        fm, body = _read(plan)
        fm["state"] = "superseded"
        fm["closed"] = TODAY
        fm["superseded_by_round"] = "R158"
        fm["superseded_note"] = (
            "Sub-experiment documented in CLM-0300 (R158 ensemble exhaustion "
            "study). R171 Gap 1 audit revealed R156/R157 had eval results but "
            "no own-round closure."
        )
        _write(plan, fm, body)
        print(f"FLIP-S {name}: superseded by R158")

    print("\n=== Phase B4: R171 Gap 3 — flip Q-0014 to closed-partial ===")
    # Currently closed-positive (forced by old enum); the truer status is
    # closed-partial because the answer is conditional (yes via ensemble,
    # no via single-algo). Need explicit closed_note already set in R166.
    update_question(
        "Q-0014", status="closed-partial",
        closed_note=(
            "R154 ensemble (CLM-0295) gives conditional answer: "
            "single-algo cannot break plateau, but cross-algo same-seed "
            "ensemble does (+5.4%). R171 Gap 3 enables closed-partial."
        ),
    )

    print("\n=== Phase B5: R171 Gap 2 — close Q-0023 by CLM-0256 ===")
    # Q-0023: Magnitude-PI variant — match droop ~0.20 or break >0.30?
    # CLM-0256 (R133) answers: mag-PI geo=0.2602, matches droop level
    # but does NOT break plateau. Closed-positive (match droop confirmed).
    update_question(
        "Q-0023", status="closed-positive",
        closed_round="R171", closed_by="CLM-0256",
        closed_date=TODAY,
        closed_note=(
            "CLM-0256 (R133) D5-fair re-eval: magnitude-PI geo=0.2602 — "
            "matches droop level (~0.20) but does NOT break >0.30. Answer "
            "= 'matches droop'. R171 Gap 2 Q-supersession heuristic "
            "surfaced this as already-answered."
        ),
    )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
