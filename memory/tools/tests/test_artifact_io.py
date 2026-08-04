"""Tests for immutable evidence artifact I/O."""

from __future__ import annotations

from pathlib import Path

import pytest
from memory.tools.artifact_io import (
    read_verified_json,
    verified_digest_only,
    write_new_json,
)


def test_create_only_json_round_trips_and_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"

    digest = write_new_json(path, {"value": 3})

    payload, verified = read_verified_json(path, digest)
    assert payload == {"value": 3}
    assert verified == digest
    assert verified_digest_only(path) == digest
    with pytest.raises(FileExistsError):
        write_new_json(path, {"value": 4})


def test_create_only_json_honours_an_existing_reservation(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    path.with_suffix(".json.create.lock").write_text("busy\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="reserved"):
        write_new_json(path, {"value": 3})
    assert not path.exists()
