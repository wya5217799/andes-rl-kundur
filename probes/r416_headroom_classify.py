"""R416 analysis probe (plan-registered execution amendment).

The sealed runner's ``classify`` step mis-read the R399
``formal_analysis.json`` shape (its ``classification`` field is a string,
not an object), so the analysis step is executed here instead: the 22-arm
sealed records are read read-only, the frozen ``classify_bank`` is applied
to the expanded 21-law contract, and the nine-law anchor compares against
the R399 top-level ``selected_deterministic_arm`` and ``oracle_gate``
values.  No trajectory is re-run; the classifier, thresholds, guards, and
oracle semantics are unchanged.

Usage (WSL, through the scratch launcher):
  python scripts/andes_scratch.py probes/r416_headroom_classify.py
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r416_headroom_expansion as runner  # noqa: E402
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    build_contract as _r399_contract,
    classify_bank,
)
from andes_rl_kundur.evaluation.soft_spot_headroom_expansion import (  # noqa: E402
    original_nine_ids,
)

OUT = ROOT / "results/research_loop/r416_headroom_expansion"
R399_OUT = ROOT / "results/research_loop/r399_md_decoupling_headroom"


def _nine_law_anchor(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    nine = set(original_nine_ids())
    r399_contract = _r399_contract()
    subset = [
        dict(row)
        for row in summaries
        if str(row["arm_id"]) in nine or str(row["arm_id"]) == "zero"
    ]
    r416_nine = classify_bank(subset, contract=r399_contract)
    r399 = runner._read_hashed_json(R399_OUT / "formal_analysis.json")
    deviations: dict[str, float] = {}
    deviations["classification_equal"] = 0.0 if (
        str(r416_nine.get("classification")) == str(r399.get("classification"))
    ) else 1.0
    deviations["selected_deterministic_arm_equal"] = 0.0 if (
        str(r416_nine.get("selected_deterministic_arm"))
        == str(r399.get("selected_deterministic_arm"))
    ) else 1.0
    r416_oracle = r416_nine.get("oracle_gate", {}) or {}
    r399_oracle = r399.get("oracle_gate", {}) or {}
    for name in ("off_diagonal_improvement", "differential_improvement"):
        left = float(r416_oracle.get(name, float("nan")))
        right = float(r399_oracle.get(name, float("nan")))
        denominator = max(abs(left), abs(right), 1.0e-30)
        deviations[name] = abs(left - right) / denominator
    verdict = (
        "NINE-LAW-ANCHOR-REPRODUCED"
        if all(value <= runner.ANCHOR_TOLERANCE_RELATIVE for value in deviations.values())
        else "NINE-LAW-ANCHOR-DRIFT"
    )
    return {
        "verdict": verdict,
        "deviations": deviations,
        "r416_nine_law_classification": str(r416_nine.get("classification")),
        "r399_classification": str(r399.get("classification")),
        "r416_nine_law_selected": str(r416_nine.get("selected_deterministic_arm")),
        "r399_selected": str(r399.get("selected_deterministic_arm")),
    }


def main() -> int:
    contract = runner.build_contract()
    summaries = runner._collect_summaries()
    classification = classify_bank(summaries, contract=contract)
    anchor = _nine_law_anchor(summaries)
    analysis = {
        "schema_version": 1,
        "round": "R416",
        "manuscript_line": "yang-md-decoupling-marl",
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": runner._sha256_file(runner.SEAL),
        "analysis_amendment": (
            "plan-registered analysis-step amendment: the sealed runner's "
            "classify mis-read the R399 formal_analysis.json shape; this "
            "probe applies the same frozen classify_bank and the registered "
            "nine-law anchor on the sealed records without re-running any "
            "trajectory"
        ),
        "classification": classification,
        "nine_law_anchor": anchor,
        "reward_used_for_gate": False,
        "training_executed": False,
    }
    analysis_path = OUT / "formal_analysis.json"
    digest = runner._write_new_json(analysis_path, analysis)
    manifest_payload = {
        "schema_version": 1,
        "round": "R416",
        "analysis_sha256": digest,
        "analysis_amendment": analysis["analysis_amendment"],
        "input_artifacts": [
            {
                "path": runner._relative(path),
                "sha256": runner._sha256_file(path),
            }
            for path in sorted(OUT.rglob("*.json"))
            if path.name not in {"formal_analysis.json", "formal_manifest.json"}
        ],
        "arm_count": len(contract["arm_ids"]),
    }
    runner._write_new_json(OUT / "formal_manifest.json", manifest_payload)
    print(f"R416 formal analysis (amendment probe): {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
