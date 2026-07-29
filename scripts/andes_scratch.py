"""Run an ANDES-facing Python entrypoint outside the repository root.

Motivation:
    ANDES writes ``kundur_full_out.*`` and eigenvalue scratch files to the
    process working directory. Running maintained entrypoints through this
    adapter keeps those files in one preserved, ignored scratch tree without
    changing protected environment or evaluation code.

Usage:
    python scripts/andes_scratch.py scripts/eval_no_control.py
    python scripts/andes_scratch.py scripts/train.py --episodes 75 --seed 49
    python scripts/andes_scratch.py --scratch-root D:\\scratch scripts/eval_ddic.py

Failure modes:
    A missing script exits 2. The child process exit status is propagated.
    Scratch directories are retained for inspection and are never deleted.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=ROOT / "tmp" / "andes",
        help="parent directory for preserved per-run working directories",
    )
    parser.add_argument("script", type=Path, help="Python entrypoint to execute")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="arguments for the entrypoint")
    return parser


def _run_directory(parent: Path, script: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = parent / f"{script.stem}-{stamp}-{os.getpid()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    script = args.script if args.script.is_absolute() else ROOT / args.script
    script = script.resolve()
    if not script.is_file():
        print(f"ERROR: script not found: {script}", file=sys.stderr)
        return 2
    scratch_root = (
        args.scratch_root
        if args.scratch_root.is_absolute()
        else ROOT / args.scratch_root
    ).resolve()
    run_dir = _run_directory(scratch_root, script)
    print(f"SCRATCH_DIR={run_dir}", flush=True)
    completed = subprocess.run(
        [sys.executable, str(script), *args.args],
        cwd=run_dir,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
