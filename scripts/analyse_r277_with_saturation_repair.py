"""Analyse sealed R277 traces with one explicit summary-schema repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import eval_learning_gap_oracle as sealed_runner  # noqa: E402

from andes_rl_kundur.evaluation.learning_gap_analysis_repair import (  # noqa: E402
    summarise_learning_gap_trace_with_saturation_count,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_canonical(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def analyse(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
) -> None:
    sealed_runner.summarise_learning_gap_trace = (
        summarise_learning_gap_trace_with_saturation_count
    )
    sealed_runner.analyse(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
        out_dir=out_dir,
    )

    repair_module = (
        SRC
        / "andes_rl_kundur"
        / "evaluation"
        / "learning_gap_analysis_repair.py"
    )
    repair_script = Path(__file__).resolve()
    summary_path = out_dir / "learning_gap_oracle_summary.json"
    provenance_path = out_dir / "provenance.json"
    _write_new_canonical(
        out_dir / "analysis_integrity_repair.json",
        {
            "schema_version": 1,
            "round": "R277",
            "reason": (
                "The sealed R275-derived summariser omitted "
                "bess_saturation_reason_count required by the R277 selector."
            ),
            "scope": (
                "Count non-empty bess_saturation_reasons already present in "
                "each immutable trace; no trace, endpoint, guard, threshold, "
                "bootstrap, or selection rule changed."
            ),
            "formal_manifest": {
                "path": str(manifest_path),
                "sha256": expected_manifest_sha256,
            },
            "repair_sources": {
                str(repair_script.relative_to(ROOT)): _sha256(repair_script),
                str(repair_module.relative_to(ROOT)): _sha256(repair_module),
            },
            "outputs": {
                str(summary_path.relative_to(ROOT)): _sha256(summary_path),
                str(provenance_path.relative_to(ROOT)): _sha256(provenance_path),
            },
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    analyse(
        manifest_path=args.manifest.resolve(),
        expected_manifest_sha256=args.expected_manifest_sha256,
        out_dir=args.out_dir.resolve(),
    )


if __name__ == "__main__":
    main()
