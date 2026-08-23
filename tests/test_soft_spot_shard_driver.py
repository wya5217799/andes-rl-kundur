"""Directed tests for the shared soft-spot eval-shard driver.

Windows-safe: wave partitioning plus a real end-to-end drive over a fake
runner (no ANDES import).  The fake runner writes one file per shard id
into a directory named by an environment variable, so the driver's
launcher/argv plumbing is exercised exactly as the WSL rounds use it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import soft_spot_shard_driver as driver  # noqa: E402


def test_waves_partition() -> None:
    assert driver.waves(["a", "b", "c", "d", "e"], 2) == [
        ["a", "b"],
        ["c", "d"],
        ["e"],
    ]
    assert driver.waves([], 4) == []
    with pytest.raises(ValueError):
        driver.waves(["a"], 0)


_FAKE_RUNNER = """\
import os
import sys
from pathlib import Path

out = Path(os.environ["FAKE_SHARD_OUT"])
out.mkdir(parents=True, exist_ok=True)
assert sys.argv[1] == "shard", sys.argv
sid = sys.argv[2]
if os.environ.get("FAKE_FAIL") == sid:
    raise SystemExit(3)
(out / (sid.replace("|", "_") + ".ok")).write_text("ok", encoding="utf-8")
"""


def _write_fake_runner(tmp_path: Path) -> Path:
    runner = tmp_path / "fake_runner.py"
    runner.write_text(_FAKE_RUNNER, encoding="utf-8")
    return runner


def test_drive_all_ok(tmp_path: Path) -> None:
    runner = _write_fake_runner(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    previous = os.environ.get("FAKE_SHARD_OUT")
    previous_fail = os.environ.get("FAKE_FAIL")
    os.environ["FAKE_SHARD_OUT"] = str(out_dir)
    os.environ.pop("FAKE_FAIL", None)
    try:
        payload = driver.drive(
            runner,
            ["arm|s1|a1", "arm|s2|a1"],
            workers=1,
            round_id="R999",
            log_dir=tmp_path / "logs",
            resume=False,
        )
    finally:
        if previous is None:
            os.environ.pop("FAKE_SHARD_OUT", None)
        else:
            os.environ["FAKE_SHARD_OUT"] = previous
        if previous_fail is None:
            os.environ.pop("FAKE_FAIL", None)
        else:
            os.environ["FAKE_FAIL"] = previous_fail
    assert payload["failed"] == []
    assert payload["shard_count"] == 2
    assert (out_dir / "arm_s1_a1.ok").is_file()
    assert (out_dir / "arm_s2_a1.ok").is_file()
    assert (tmp_path / "logs" / "arm_s1_a1.log").is_file()
    assert (tmp_path / "logs" / "arm_s2_a1.log").is_file()
    for shard_id in ("arm|s1|a1", "arm|s2|a1"):
        assert payload["results"][shard_id]["exit_code"] == 0


def test_drive_reports_failure(tmp_path: Path) -> None:
    runner = _write_fake_runner(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    previous = os.environ.get("FAKE_SHARD_OUT")
    previous_fail = os.environ.get("FAKE_FAIL")
    os.environ["FAKE_SHARD_OUT"] = str(out_dir)
    os.environ["FAKE_FAIL"] = "arm|s2|a1"
    try:
        payload = driver.drive(
            runner,
            ["arm|s1|a1", "arm|s2|a1", "arm|s3|a1"],
            workers=2,
            round_id="R999",
            log_dir=tmp_path / "logs",
            resume=False,
        )
    finally:
        if previous is None:
            os.environ.pop("FAKE_SHARD_OUT", None)
        else:
            os.environ["FAKE_SHARD_OUT"] = previous
        if previous_fail is None:
            os.environ.pop("FAKE_FAIL", None)
        else:
            os.environ["FAKE_FAIL"] = previous_fail
    assert payload["failed"] == ["arm|s2|a1"]
    assert payload["results"]["arm|s2|a1"]["exit_code"] == 3
    assert (out_dir / "arm_s1_a1.ok").is_file()
    assert (out_dir / "arm_s3_a1.ok").is_file()
    assert not (out_dir / "arm_s2_a1.ok").exists()


def test_driver_result_records_runner_hash(tmp_path: Path) -> None:
    runner = _write_fake_runner(tmp_path)
    payload = driver.drive(
        runner,
        [],
        workers=1,
        round_id="R999",
        log_dir=tmp_path / "logs",
        resume=False,
    )
    assert payload["failed"] == []
    assert payload["runner_sha256"] == driver._sha256_file(runner)


def test_main_relative_log_dir_anchors_to_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R476 regression: the driver runs with a scratch working directory
    (andes_scratch launcher), so a relative --log-dir must anchor to the
    repository root — otherwise driver_result.json lands under the scratch
    tree and a detached pipeline looking from the repository root exits."""
    repo = tmp_path / "repo"
    scratch = tmp_path / "scratch"
    (repo / "scripts").mkdir(parents=True)
    (repo / "tmp" / "andes").mkdir(parents=True)
    scratch.mkdir()
    (repo / "scripts" / "fake_runner.py").write_text(
        _FAKE_RUNNER, encoding="utf-8"
    )
    (repo / "tmp" / "andes" / "shards.json").write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(driver, "ROOT", repo)
    monkeypatch.chdir(scratch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "soft_spot_shard_driver.py",
            "--runner", "scripts/fake_runner.py",
            "--shards", "tmp/andes/shards.json",
            "--workers", "1",
            "--round", "R999",
            "--log-dir", "tmp/andes/logs",
        ],
    )
    assert driver.main() == 0
    results = list((repo / "tmp" / "andes" / "logs").rglob("driver_result.json"))
    assert len(results) == 1
    payload = json.loads(results[0].read_text(encoding="utf-8"))
    assert payload["shard_count"] == 0
    assert not list(scratch.rglob("driver_result.json"))


def test_log_root_anchors_relative_values(tmp_path: Path) -> None:
    assert driver._log_root(None) == ROOT / "tmp" / "andes"
    assert driver._log_root("tmp/andes/logs") == ROOT / "tmp/andes/logs"
    assert driver._log_root(tmp_path / "x") == tmp_path / "x"
