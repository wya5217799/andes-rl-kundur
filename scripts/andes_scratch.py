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
    A missing script exits 2. On WSL/POSIX the launcher replaces itself with
    the target, so the target exit status is the launcher exit status and one
    shard uses exactly one Python process. Windows preserves the subprocess
    fallback used by local launcher tests and non-ANDES utilities.
    Scratch directories are retained for inspection and are never deleted.
    Known repository input/output path flags keep repository-root-relative
    semantics even though the child working directory changes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SINGLE_REPOSITORY_PATH_FLAGS = {
    "--ckpt-dir",
    "--out-dir",
    "--resume",
    "--save-dir",
    "--warmstart-shared",
}
_MULTI_REPOSITORY_PATH_FLAGS = {"--ckpt-dirs"}
_REPOSITORY_PATH_DEFAULTS = {
    "train.py": ("--save-dir", "results/v4_train"),
}


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


def _repository_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return str(path.resolve())


def _anchor_repository_path_arguments(values: list[str]) -> list[str]:
    """Preserve maintained entrypoints' historical repository-path semantics."""

    anchored: list[str] = []
    index = 0
    while index < len(values):
        value = values[index]
        name, separator, inline_value = value.partition("=")
        if separator and name in (
            _SINGLE_REPOSITORY_PATH_FLAGS | _MULTI_REPOSITORY_PATH_FLAGS
        ):
            anchored.append(f"{name}={_repository_path(inline_value)}")
            index += 1
            continue
        anchored.append(value)
        if value in _SINGLE_REPOSITORY_PATH_FLAGS and index + 1 < len(values):
            index += 1
            anchored.append(_repository_path(values[index]))
        elif value in _MULTI_REPOSITORY_PATH_FLAGS:
            index += 1
            while index < len(values) and not values[index].startswith("-"):
                anchored.append(_repository_path(values[index]))
                index += 1
            continue
        index += 1
    return anchored


def _add_repository_path_defaults(script: Path, values: list[str]) -> list[str]:
    default = _REPOSITORY_PATH_DEFAULTS.get(script.name)
    if default is None:
        return values
    flag, value = default
    if any(item == flag or item.startswith(f"{flag}=") for item in values):
        return values
    return [*values, flag, value]


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
    child_args = _add_repository_path_defaults(script, args.args)
    command = [
        sys.executable,
        str(script),
        *_anchor_repository_path_arguments(child_args),
    ]
    if os.name == "posix":
        os.chdir(run_dir)
        os.execv(sys.executable, command)
        raise RuntimeError("os.execv returned unexpectedly")
    completed = subprocess.run(command, cwd=run_dir, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
