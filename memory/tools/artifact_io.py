"""Race-safe helpers for immutable JSON evidence artifacts.

Motivation: evidence adapters repeatedly need canonical hashing, verified
reads, digest-only protected reads, and create-only JSON plus sidecars. Keeping
the pattern here prevents each round from reimplementing a racy exists-then-
write sequence.

Usage: import the helpers from a round adapter. Writers acquire an exclusive
same-directory reservation and use exclusive file creation. A failure never
overwrites an existing artifact; an interrupted new write may leave a partial
create-only file that must be inspected rather than silently retried.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(payload: object) -> bytes:
    """Serialize one payload deterministically for hashing or replay checks."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def payload_sha256(payload: object) -> str:
    """Return the SHA-256 of canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash one file without interpreting its contents."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new_json(path: Path, payload: object) -> str:
    """Exclusively create canonical evidence JSON and its SHA-256 sidecar."""

    sidecar = path.with_suffix(path.suffix + ".sha256")
    reservation = path.with_suffix(path.suffix + ".create.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with reservation.open("x", encoding="utf-8") as handle:
            handle.write("exclusive-create reservation\n")
    except FileExistsError as exc:
        raise FileExistsError(f"create-only artifact is reserved: {path}") from exc
    try:
        if path.exists() or sidecar.exists():
            raise FileExistsError(f"create-only artifact already exists: {path}")
        text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        digest = sha256_file(path)
        with sidecar.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{digest}  {path.name}\n")
        return digest
    finally:
        reservation.unlink(missing_ok=True)


def read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Read an object JSON only after file, sidecar, and optional hash agree."""

    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"JSON artifact or sidecar is missing: {path}")
    digest = sha256_file(path)
    recorded = sidecar.read_text(encoding="utf-8").split()[0]
    if digest != recorded or (expected_sha256 is not None and digest != expected_sha256):
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON artifact is not an object: {path}")
    return payload, digest


def verified_digest_only(path: Path) -> str:
    """Verify a sidecar while never parsing or interpreting the payload."""

    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"protected artifact or sidecar is missing: {path}")
    digest = sha256_file(path)
    if sidecar.read_text(encoding="utf-8").split()[0] != digest:
        raise RuntimeError(f"hash mismatch for protected artifact: {path}")
    return digest
