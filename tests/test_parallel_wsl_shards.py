from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run_parallel_wsl_shards.py"


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", maxsplit=1)[1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def test_dry_run_reports_three_unique_workers_and_global_progress(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--worker-script",
            "scripts/run_r293_formal.py",
            "--shard-count",
            "3",
            "--global-task-count",
            "264",
            "--log-dir",
            str(tmp_path / "logs"),
            "--dry-run",
            "--",
            "run",
            "--expected-manifest-sha256",
            "abc123",
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    plan = json.loads(result.stdout)
    assert plan["worker_count"] == 3
    assert plan["wsl_python_process_budget"] == 3
    assert plan["global_task_count"] == 264
    assert [worker["shard_index"] for worker in plan["workers"]] == [0, 1, 2]
    for worker in plan["workers"]:
        command = worker["command"]
        assert command.count("scripts/andes_scratch.py") == 1
        assert command[-4:] == [
            "--shard-index",
            str(worker["shard_index"]),
            "--shard-count",
            "3",
        ]


@pytest.mark.skipif(
    os.name != "nt" or shutil.which("wsl.exe") is None,
    reason="Windows WSL integration is unavailable",
)
def test_three_workers_reach_a_shared_barrier_concurrently(tmp_path: Path) -> None:
    worker = tmp_path / "barrier_worker.py"
    worker.write_text(
        "import argparse, time\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--barrier-dir', type=Path, required=True)\n"
        "p.add_argument('--shard-index', type=int, required=True)\n"
        "p.add_argument('--shard-count', type=int, required=True)\n"
        "a = p.parse_args()\n"
        "a.barrier_dir.mkdir(parents=True, exist_ok=True)\n"
        "(a.barrier_dir / f'started_{a.shard_index}').write_text('started')\n"
        "deadline = time.monotonic() + 8.0\n"
        "while len(list(a.barrier_dir.glob('started_*'))) < a.shard_count:\n"
        "    if time.monotonic() >= deadline:\n"
        "        raise SystemExit(9)\n"
        "    time.sleep(0.05)\n",
        encoding="utf-8",
    )
    barrier = tmp_path / "barrier"
    logs = tmp_path / "logs"

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--worker-script",
            str(worker),
            "--shard-count",
            "3",
            "--global-task-count",
            "3",
            "--log-dir",
            str(logs),
            "--poll-seconds",
            "0.05",
            "--",
            "--barrier-dir",
            _wsl_path(barrier),
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in barrier.glob("started_*")) == [
        "started_0",
        "started_1",
        "started_2",
    ]
    assert sorted(path.name for path in logs.glob("shard_*.log")) == [
        "shard_0.log",
        "shard_1.log",
        "shard_2.log",
    ]


@pytest.mark.skipif(
    os.name != "nt" or shutil.which("wsl.exe") is None,
    reason="Windows WSL integration is unavailable",
)
def test_global_progress_counts_unique_outputs_from_all_workers(tmp_path: Path) -> None:
    worker = tmp_path / "output_worker.py"
    worker.write_text(
        "import argparse, json\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--trace-dir', type=Path, required=True)\n"
        "p.add_argument('--shard-index', type=int, required=True)\n"
        "p.add_argument('--shard-count', type=int, required=True)\n"
        "a = p.parse_args()\n"
        "a.trace_dir.mkdir(parents=True, exist_ok=True)\n"
        "target = a.trace_dir / f'trace_{a.shard_index}.json'\n"
        "target.write_text(json.dumps({'shard': a.shard_index}))\n",
        encoding="utf-8",
    )
    traces = tmp_path / "traces"
    logs = tmp_path / "logs"

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--worker-script",
            str(worker),
            "--shard-count",
            "3",
            "--global-task-count",
            "3",
            "--log-dir",
            str(logs),
            "--trace-dir",
            str(traces),
            "--poll-seconds",
            "0.05",
            "--",
            "--trace-dir",
            _wsl_path(traces),
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[global 3/3]" in result.stdout
    assert sorted(path.name for path in traces.glob("*.json")) == [
        "trace_0.json",
        "trace_1.json",
        "trace_2.json",
    ]
