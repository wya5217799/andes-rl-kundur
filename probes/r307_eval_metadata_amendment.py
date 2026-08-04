#!/usr/bin/env python3
"""Create a sealed EVAL-only metadata view over immutable R307 edge traces.

The original trace records remain unchanged.  This amendment changes only the
scenario-level ``sign`` label from pulse polarity to ``paired`` and preserves
the original value as ``pulse_sign``.  Every derived record binds its source
path and SHA-256 so the view can be audited byte-for-byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SEAL = ROOT / "memory/rounds/R307/model_first_stage1_seal.json"
RUN_MANIFEST = ROOT / "results/r307_model_first_stage1/run_manifest.json"
DEFAULT_AMENDMENT_SEAL = (
    ROOT / "memory/rounds/R307/eval_metadata_amendment_seal.json"
)
DEFAULT_OUT = ROOT / "results/r307_model_first_stage1/eval_input_amended"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_new_json(path: Path, payload: object) -> str:
    path = path.resolve()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    encoded = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    path = path.resolve()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise RuntimeError(f"missing artifact or sidecar: {path}")
    digest = _sha256_file(path)
    sidecar_digest = sidecar.read_text(encoding="ascii").strip().split()[0]
    if digest != sidecar_digest:
        raise RuntimeError(f"sidecar mismatch for {path}")
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError(f"expected hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"artifact root must be an object: {path}")
    return payload, digest


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def normalize_eval_record(
    record: dict[str, Any],
    *,
    source_path: str,
    source_sha256: str,
) -> dict[str, Any]:
    """Return the exact EVAL metadata amendment without mutating ``record``."""

    if record.get("round") != "R307" or record.get("question") != "Q-0063":
        raise ValueError("amendment accepts only R307/Q-0063 records")
    if not str(record.get("coordinate", "")).startswith("edge_"):
        raise ValueError("amendment accepts only Stage-1 edge records")
    pulse_sign = record.get("sign")
    if pulse_sign not in {"positive", "negative"}:
        raise ValueError("edge record sign must be positive or negative")
    if record.get("controller") != pulse_sign:
        raise ValueError("controller must retain the pulse-sign identity")
    if len(source_sha256) != 64:
        raise ValueError("source_sha256 must be a 64-character digest")

    amended = deepcopy(record)
    amended["sign"] = "paired"
    amended["pulse_sign"] = pulse_sign
    amended["source_record"] = {
        "path": source_path,
        "sha256": source_sha256,
    }
    return amended


def prepare(original_seal_sha256: str, amendment_seal: Path) -> str:
    original, observed_original = _read_verified_json(
        ORIGINAL_SEAL, original_seal_sha256
    )
    manifest, manifest_digest = _read_verified_json(RUN_MANIFEST)
    if original.get("round") != "R307" or manifest.get("trace_count") != 27:
        raise RuntimeError("original R307 seal/manifest identity mismatch")
    contract = {
        "round": "R307",
        "kind": "eval-input-metadata-amendment",
        "original_seal": {
            "path": _path_text(ORIGINAL_SEAL),
            "sha256": observed_original,
        },
        "run_manifest": {
            "path": _path_text(RUN_MANIFEST),
            "sha256": manifest_digest,
        },
        "input_group": "edge_eval",
        "expected_record_count": 18,
        "transformation": {
            "sign": "paired",
            "pulse_sign": "copy original sign",
            "source_record": "bind original path and sha256",
            "all_other_fields": "deep-copy unchanged",
        },
        "threshold_changes": False,
        "trace_rerun": False,
        "evidence_authority_change": False,
    }
    seal = {
        "schema_version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "sources": {
            "amendment_probe": {
                "path": _path_text(Path(__file__).resolve()),
                "sha256": _sha256_file(Path(__file__).resolve()),
            }
        },
    }
    digest = _write_new_json(amendment_seal, seal)
    print(f"amendment_seal_sha256={digest}")
    return digest


def run(amendment_seal: Path, expected_sha256: str, out_dir: Path) -> None:
    seal, seal_digest = _read_verified_json(amendment_seal, expected_sha256)
    source = seal["sources"]["amendment_probe"]
    if _sha256_file(ROOT / source["path"]) != source["sha256"]:
        raise RuntimeError("sealed amendment probe source drift")
    contract = seal["contract"]
    _read_verified_json(
        ROOT / contract["original_seal"]["path"],
        contract["original_seal"]["sha256"],
    )
    manifest, _ = _read_verified_json(
        ROOT / contract["run_manifest"]["path"],
        contract["run_manifest"]["sha256"],
    )
    entries = [
        entry for entry in manifest["records"] if entry["group"] == "edge_eval"
    ]
    if len(entries) != contract["expected_record_count"]:
        raise RuntimeError("amendment edge-record count mismatch")

    outputs: list[dict[str, str]] = []
    for entry in entries:
        record, _ = _read_verified_json(ROOT / entry["path"], entry["sha256"])
        amended = normalize_eval_record(
            record,
            source_path=entry["path"],
            source_sha256=entry["sha256"],
        )
        destination = out_dir.resolve() / Path(entry["path"]).name
        digest = _write_new_json(destination, amended)
        outputs.append(
            {
                "path": _path_text(destination),
                "sha256": digest,
                "source_path": entry["path"],
                "source_sha256": entry["sha256"],
            }
        )
    manifest_path = out_dir.resolve().parent / "eval_input_amendment_manifest.json"
    manifest_digest = _write_new_json(
        manifest_path,
        {
            "schema_version": 1,
            "round": "R307",
            "created_utc": datetime.now(UTC).isoformat(),
            "amendment_seal_sha256": seal_digest,
            "record_count": len(outputs),
            "records": outputs,
            "threshold_changes": False,
            "trace_rerun": False,
        },
    )
    print(f"record_count={len(outputs)}")
    print(f"amendment_manifest_sha256={manifest_digest}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--original-seal-sha256", required=True)
    prepare_parser.add_argument(
        "--amendment-seal", type=Path, default=DEFAULT_AMENDMENT_SEAL
    )
    run_parser = commands.add_parser("run")
    run_parser.add_argument(
        "--amendment-seal", type=Path, default=DEFAULT_AMENDMENT_SEAL
    )
    run_parser.add_argument("--expected-amendment-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.original_seal_sha256, args.amendment_seal)
    else:
        run(args.amendment_seal, args.expected_amendment_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
