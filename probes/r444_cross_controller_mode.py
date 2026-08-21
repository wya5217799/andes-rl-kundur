"""Cross-controller active-mode consistency check for R444 (read-only).

Motivation
----------
The C.8 prediction ("signed-pair odd response O(eps^2) rather than cubic")
assumes two same-bias controllers share one fixed active-mode sequence at
each amplitude.  The sealed R444 analysis verified each controller's
saturation/limiter signature is internally consistent across the fitted
ladder, but never asserted law and zero-action carry the SAME signature at
the same amplitude.  This probe closes that gap as a read-only derived
view: it reads the sealed records, compares per-step saturation/limiter
signatures between the two controllers per (profile, pair_kind, scale,
sign), and writes a create-only hashed JSON.

Usage
-----
    python probes/r444_cross_controller_mode.py results/research_loop/r444_signed_probe_order

Failure modes
-------------
Missing/incomplete records raise ValueError; no writes except the single
create-only output JSON plus its .sha256 sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "probes"))

import r444_signed_probe_order as order  # noqa: E402

SCALE_COUNT = order.SCALE_COUNT
CONTROLLERS = (order.CONTROLLER_LAW, order.CONTROLLER_ZERO)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_json(path: Path, payload: dict[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _signatures(
    results_root: Path,
    controller: str,
    profile_id: str,
    pair_kind: str,
    k: int,
) -> dict[str, tuple[tuple[int, ...], tuple[int, ...]]]:
    block = results_root / "eval" / controller / f"k{k}" / f"{profile_id}.json"
    records = order.load_records(block)
    out: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    for sign in ("positive", "negative"):
        scenario_id = f"{profile_id}_{pair_kind}_{sign}"
        out[sign] = order.mode_signature(records[scenario_id])
    return out


def run_check(results_root: Path) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    mismatched_cells = 0
    for profile_id in sorted(
        {
            path.stem
            for path in (results_root / "eval" / CONTROLLERS[0] / "k0").glob("*.json")
            if path.name.endswith(".json")
        }
    ):
        for pair_kind in order.PAIR_KINDS:
            per_scale: list[dict[str, Any]] = []
            for k in range(SCALE_COUNT):
                law = _signatures(results_root, "law", profile_id, pair_kind, k)
                zero = _signatures(results_root, "zero", profile_id, pair_kind, k)
                identical = law == zero
                if not identical:
                    mismatched_cells += 1
                per_scale.append(
                    {
                        "scale": k,
                        "law_saturation": law["positive"][0] == law["negative"][0],
                        "zero_saturation": zero["positive"][0] == zero["negative"][0],
                        "law_sig": {
                            "saturation": list(law["positive"][0]),
                            "limiter": list(law["positive"][1]),
                        },
                        "zero_sig": {
                            "saturation": list(zero["positive"][0]),
                            "limiter": list(zero["positive"][1]),
                        },
                        "cross_controller_identical": identical,
                    }
                )
            blocks.append(
                {
                    "profile_id": profile_id,
                    "pair_kind": pair_kind,
                    "per_scale": per_scale,
                    "cross_controller_identical_all_scales": all(
                        cell["cross_controller_identical"] for cell in per_scale
                    ),
                }
            )
    total_cells = len(blocks) * SCALE_COUNT
    return {
        "schema_version": 1,
        "round": "R444",
        "read_only_inputs": "results/research_loop/r444_signed_probe_order/eval/*",
        "checks": "per-step saturation/limiter signature equality between law "
        "and zero-action at the same (profile, pair_kind, scale, sign)",
        "blocks": blocks,
        "summary": {
            "total_cells": total_cells,
            "cross_controller_identical_cells": total_cells - mismatched_cells,
            "mismatched_cells": mismatched_cells,
            "verdict": (
                "CROSS-CONTROLLER-MODE-IDENTICAL"
                if mismatched_cells == 0
                else "CROSS-CONTROLLER-MODE-DIFFERS"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results_root", type=Path)
    args = parser.parse_args(argv)
    payload = run_check(args.results_root)
    out = args.results_root / "cross_controller_mode.json"
    digest = _write_new_json(out, payload)
    print(out)
    print(payload["summary"])
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
