"""Directed tests for the detached-pipeline path-discipline lint.

Covers the R476 failure shape: a pipeline that searches for
driver_result.json somewhere the driver never writes, plus the
repository-relative --log-dir invariant the anchored driver relies on.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "memory" / "tools"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import detached_pipeline_lint as lint  # noqa: E402

_OK_PIPELINE = """\
repo="/mnt/e/Projects/andes-rl-kundur"
cd "${repo}"
for wave in 1 2 3; do
  python scripts/soft_spot_shard_driver.py \\
    --shards tmp/andes/wave${wave}_shards.json \\
    --log-dir "tmp/andes/train_logs/wave${wave}"
done
first="$(find tmp/andes/train_logs/wave1 -name driver_result.json | tail -n 1)"
"""


def test_ok_pipeline_passes() -> None:
    assert lint.lint_text(_OK_PIPELINE) == []


def test_absolute_log_dir_rejected() -> None:
    text = _OK_PIPELINE.replace(
        '"tmp/andes/train_logs/wave${wave}"',
        '"/mnt/e/scratch/train_logs/wave${wave}"',
    )
    errors = lint.lint_text(text)
    assert any("repository-relative" in error for error in errors)


def test_scratch_tree_log_dir_rejected() -> None:
    text = _OK_PIPELINE.replace(
        '"tmp/andes/train_logs/wave${wave}"',
        '"tmp/andes/soft_spot_shard_driver-abc/tmp/andes/logs"',
    )
    errors = lint.lint_text(text)
    assert any("scratch tree" in error for error in errors)


def test_find_outside_log_dir_rejected() -> None:
    text = _OK_PIPELINE.replace(
        "find tmp/andes/train_logs/wave1",
        "find tmp/andes/trian_logs/wave1",
    )
    errors = lint.lint_text(text)
    assert any("not under any --log-dir" in error for error in errors)


def test_missing_log_dir_with_driver_rejected() -> None:
    text = (
        "repo=/mnt/e/Projects/andes-rl-kundur\ncd repo\n"
        "python scripts/soft_spot_shard_driver.py --shards tmp/andes/shards.json\n"
    )
    assert lint.lint_text(text) == ["no --log-dir argument found (driver logs unlocatable)"]


def test_transport_only_pipeline_without_driver_is_exempt() -> None:
    # Single-command WSL wrapper: no shard driver and no driver_result.json
    # search, so the --log-dir requirement is vacuous (R481 pattern).
    text = "repo=/mnt/e/Projects/andes-rl-kundur\ncd repo\npython scripts/runner.py execute\n"
    assert lint.lint_text(text) == []


def test_real_pipelines_pass() -> None:
    paths = sorted(ROOT.glob(lint.PIPELINE_GLOB))
    assert paths, "no real pipelines matched (lint would exit 2)"
    for path in paths:
        errors = lint.lint_text(path.read_text(encoding="utf-8"))
        assert errors == [], f"{path}: {errors}"
