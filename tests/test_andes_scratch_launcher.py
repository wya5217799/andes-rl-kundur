from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "scripts" / "andes_scratch.py"


def test_launcher_runs_script_inside_preserved_scratch_directory(
    tmp_path: Path,
) -> None:
    script = tmp_path / "write_artifact.py"
    script.write_text(
        "from pathlib import Path\n"
        "Path('artifact.txt').write_text('created', encoding='utf-8')\n"
        "print(Path.cwd())\n",
        encoding="utf-8",
    )
    scratch_root = tmp_path / "scratch"

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--scratch-root",
            str(scratch_root),
            str(script),
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_dirs = list(scratch_root.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "artifact.txt").read_text(encoding="utf-8") == "created"
    assert not (tmp_path / "artifact.txt").exists()
    assert f"SCRATCH_DIR={run_dirs[0]}" in result.stdout


def test_launcher_propagates_child_exit_status(tmp_path: Path) -> None:
    script = tmp_path / "fail.py"
    script.write_text("raise SystemExit(7)\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--scratch-root",
            str(tmp_path / "scratch"),
            str(script),
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 7


@pytest.mark.skipif(shutil.which("wsl.exe") is None, reason="WSL is unavailable")
def test_wsl_launcher_replaces_itself_instead_of_holding_a_wrapper_process(
    tmp_path: Path,
) -> None:
    script = tmp_path / "record_parent.py"
    script.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "raw = Path(f'/proc/{os.getppid()}/cmdline').read_bytes()\n"
        "print('PARENT_CMD=' + raw.replace(b'\\x00', b' ').decode(), flush=True)\n",
        encoding="utf-8",
    )

    def wsl_path(path: Path) -> str:
        resolved = path.resolve()
        drive = resolved.drive.rstrip(":").lower()
        tail = resolved.as_posix().split(":", maxsplit=1)[1].lstrip("/")
        return f"/mnt/{drive}/{tail}"

    result = subprocess.run(
        [
            "wsl.exe",
            "/home/wya/andes_venv/bin/python",
            wsl_path(LAUNCHER),
            "--scratch-root",
            wsl_path(tmp_path / "scratch"),
            wsl_path(script),
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    parent_line = next(
        line for line in result.stdout.splitlines() if line.startswith("PARENT_CMD=")
    )
    assert "andes_scratch.py" not in parent_line


def test_launcher_anchors_repository_path_arguments_before_changing_cwd(
    tmp_path: Path,
) -> None:
    script = tmp_path / "record_args.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "Path('args.json').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n",
        encoding="utf-8",
    )
    scratch_root = tmp_path / "scratch"

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--scratch-root",
            str(scratch_root),
            str(script),
            "--resume",
            "results/input",
            "--warmstart-shared",
            "results/shared/actor.pt",
            "--save-dir=results/output",
            "--ckpt-dirs",
            "results/a",
            "results/b",
            "--suffixes",
            "best",
            "final",
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_dir = next(scratch_root.iterdir())
    child_args = json.loads((run_dir / "args.json").read_text(encoding="utf-8"))
    assert child_args == [
        "--resume",
        str(REPO_ROOT / "results" / "input"),
        "--warmstart-shared",
        str(REPO_ROOT / "results" / "shared" / "actor.pt"),
        f"--save-dir={REPO_ROOT / 'results' / 'output'}",
        "--ckpt-dirs",
        str(REPO_ROOT / "results" / "a"),
        str(REPO_ROOT / "results" / "b"),
        "--suffixes",
        "best",
        "final",
    ]


def test_launcher_anchors_train_default_save_directory(tmp_path: Path) -> None:
    script = tmp_path / "train.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "Path('args.json').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n",
        encoding="utf-8",
    )
    scratch_root = tmp_path / "scratch"

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--scratch-root",
            str(scratch_root),
            str(script),
            "--episodes",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_dir = next(scratch_root.iterdir())
    child_args = json.loads((run_dir / "args.json").read_text(encoding="utf-8"))
    assert child_args == [
        "--episodes",
        "1",
        "--save-dir",
        str(REPO_ROOT / "results" / "v4_train"),
    ]
