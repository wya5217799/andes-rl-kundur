from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
