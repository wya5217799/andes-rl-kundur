"""Windows-safe tests for immediate-refill shard scheduling."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import adaptive_shard_driver as driver  # noqa: E402, I001


_FAKE_RUNNER = """\
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

out = Path(os.environ["ADAPTIVE_FAKE_OUT"])
out.mkdir(parents=True, exist_ok=True)
sid = sys.argv[2]
start = datetime.now(timezone.utc).timestamp()
time.sleep(float(os.environ.get("ADAPTIVE_SLEEP_" + sid, "0.01")))
end = datetime.now(timezone.utc).timestamp()
(out / (sid + ".json")).write_text(json.dumps({"start": start, "end": end}))
if os.environ.get("ADAPTIVE_FAIL") == sid:
    raise SystemExit(3)
"""


def test_dynamic_refill_starts_next_job_before_straggler_finishes(tmp_path: Path) -> None:
    runner = tmp_path / "fake.py"
    runner.write_text(_FAKE_RUNNER, encoding="utf-8")
    out = tmp_path / "out"
    old = {
        name: os.environ.get(name)
        for name in ("ADAPTIVE_FAKE_OUT", "ADAPTIVE_SLEEP_slow", "ADAPTIVE_SLEEP_fast")
    }
    os.environ["ADAPTIVE_FAKE_OUT"] = str(out)
    os.environ["ADAPTIVE_SLEEP_slow"] = "0.8"
    os.environ["ADAPTIVE_SLEEP_fast"] = "0.05"
    try:
        payload = driver.drive_dynamic(
            runner,
            ["slow", "fast", "next"],
            workers=2,
            round_id="R999",
            log_dir=tmp_path / "logs",
            poll_seconds=0.01,
            state_path=tmp_path / "logs" / "queue_state.json",
        )
    finally:
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    slow = json.loads((out / "slow.json").read_text())
    next_job = json.loads((out / "next.json").read_text())
    assert next_job["start"] < slow["end"]
    assert payload["max_active_observed"] == 2
    assert payload["failed"] == []
    assert payload["not_launched"] == []
    state = json.loads((tmp_path / "logs" / "queue_state.json").read_text())
    assert state["pending"] == []
    assert state["active"] == {}
    assert state["completion_order"] == payload["completion_order"]


def test_failure_stops_new_admission(tmp_path: Path) -> None:
    runner = tmp_path / "fake.py"
    runner.write_text(_FAKE_RUNNER, encoding="utf-8")
    out = tmp_path / "out"
    old_out = os.environ.get("ADAPTIVE_FAKE_OUT")
    old_fail = os.environ.get("ADAPTIVE_FAIL")
    old_slow = os.environ.get("ADAPTIVE_SLEEP_slow")
    os.environ["ADAPTIVE_FAKE_OUT"] = str(out)
    os.environ["ADAPTIVE_FAIL"] = "bad"
    os.environ["ADAPTIVE_SLEEP_slow"] = "0.5"
    try:
        payload = driver.drive_dynamic(
            runner,
            ["bad", "slow", "never"],
            workers=2,
            round_id="R999",
            log_dir=tmp_path / "logs",
            poll_seconds=0.01,
        )
    finally:
        if old_out is None:
            os.environ.pop("ADAPTIVE_FAKE_OUT", None)
        else:
            os.environ["ADAPTIVE_FAKE_OUT"] = old_out
        if old_fail is None:
            os.environ.pop("ADAPTIVE_FAIL", None)
        else:
            os.environ["ADAPTIVE_FAIL"] = old_fail
        if old_slow is None:
            os.environ.pop("ADAPTIVE_SLEEP_slow", None)
        else:
            os.environ["ADAPTIVE_SLEEP_slow"] = old_slow
    assert payload["failed"] == ["bad"]
    assert payload["not_launched"] == ["never"]
    assert payload["admission_halted"] is True


def test_duplicate_shards_are_rejected(tmp_path: Path) -> None:
    runner = tmp_path / "fake.py"
    runner.write_text(_FAKE_RUNNER, encoding="utf-8")
    try:
        driver.drive_dynamic(
            runner,
            ["same", "same"],
            workers=2,
            round_id="R999",
            log_dir=tmp_path / "logs",
        )
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate shard ids should fail closed")


def test_worker_count_above_rehearsed_cap_is_rejected(tmp_path: Path) -> None:
    runner = tmp_path / "fake.py"
    runner.write_text(_FAKE_RUNNER, encoding="utf-8")
    try:
        driver.drive_dynamic(
            runner,
            ["one"],
            workers=17,
            round_id="R999",
            log_dir=tmp_path / "logs",
        )
    except ValueError as exc:
        assert "rehearsed cap" in str(exc)
    else:
        raise AssertionError("unsafe worker count should fail closed")


def test_runner_args_are_forwarded_before_shard_command(tmp_path: Path) -> None:
    runner = tmp_path / "fake.py"
    runner.write_text(
        """\
import json
import os
import sys
from pathlib import Path
Path(os.environ["ADAPTIVE_ARG_OUT"]).write_text(json.dumps(sys.argv[1:]))
""",
        encoding="utf-8",
    )
    output = tmp_path / "args.json"
    old = os.environ.get("ADAPTIVE_ARG_OUT")
    os.environ["ADAPTIVE_ARG_OUT"] = str(output)
    try:
        payload = driver.drive_dynamic(
            runner,
            ["one"],
            runner_args=("--config", "future.json"),
            workers=1,
            round_id="R999",
            log_dir=tmp_path / "logs",
            poll_seconds=0.01,
        )
    finally:
        if old is None:
            os.environ.pop("ADAPTIVE_ARG_OUT", None)
        else:
            os.environ["ADAPTIVE_ARG_OUT"] = old
    assert json.loads(output.read_text()) == [
        "--config",
        "future.json",
        "shard",
        "one",
    ]
    assert payload["runner_args"] == ["--config", "future.json"]
