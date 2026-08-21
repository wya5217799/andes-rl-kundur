"""Classify a retained learner-run failure from hashed training manifests.

Usage:
  python probes/training_manifest_forensics.py \
    --manifest path/to/arm-a/manifest.json \
    --manifest path/to/arm-b/manifest.json \
    --output memory/rounds/RNN/failure_analysis.json

The probe is read-only with respect to inputs and create-only for its output.
It distinguishes a nonfinite learner value from a diagnostic sentinel that a
runner accidentally treated as a failure.  It never authorizes a retry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def analyse_manifests(manifests: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return a bounded common-cause classification for retained attempts."""

    arms = []
    sentinel_only = True
    for manifest in manifests:
        updates = list(manifest.get("update_diagnostics", []))
        finite_critic = bool(updates) and all(
            math.isfinite(float(row["critic_loss"])) for row in updates
        )
        actor_values = [float(row["actor_loss_mean"]) for row in updates]
        actor_sentinel = bool(actor_values) and all(
            math.isnan(value) for value in actor_values
        )
        no_physical_failure = int(manifest.get("tds_failed_episodes", -1)) == 0
        expected_reason = (
            manifest.get("invalid_reason") == "nonfinite learner diagnostic"
        )
        arm_sentinel_only = (
            finite_critic
            and actor_sentinel
            and no_physical_failure
            and expected_reason
        )
        sentinel_only = sentinel_only and arm_sentinel_only
        arms.append(
            {
                "arm_id": manifest.get("arm_id"),
                "interaction_steps": manifest.get("interaction_steps"),
                "finite_critic_loss": finite_critic,
                "actor_loss_is_nan_sentinel": actor_sentinel,
                "tds_failed_episodes": manifest.get("tds_failed_episodes"),
                "final_checkpoint_present": bool(
                    manifest.get("final_checkpoint_sha256")
                ),
            }
        )
    return {
        "classification": "SCRATCH-INVALID",
        "cause": (
            "diagnostic-sentinel-misclassified"
            if manifests and sentinel_only
            else "learner-or-runner-failure-unresolved"
        ),
        "retry_authorized": False,
        "algorithm_efficacy_tested": False,
        "arms": arms,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_hashed(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed input: {path}")
    if sidecar.read_text(encoding="ascii").split()[0] != _sha256(path):
        raise RuntimeError(f"hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest root must be an object: {path}")
    return payload


def _write_new(path: Path, payload: Mapping[str, Any]) -> str:
    sidecar = Path(f"{path}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    digest = _sha256(path)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    paths = [Path(value).resolve() for value in args.manifest]
    payload = analyse_manifests([_read_hashed(path) for path in paths])
    payload["inputs"] = [
        {"path": str(path), "sha256": _sha256(path)} for path in paths
    ]
    digest = _write_new(Path(args.output).resolve(), payload)
    print(f"failure analysis: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
