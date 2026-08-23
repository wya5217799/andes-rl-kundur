"""Static lint for detached-pipeline log/result path discipline.

Motivation:
    R476 lost its second and third training waves and the evaluation wave
    because the shard driver resolved a relative --log-dir against its
    scratch working directory while the pipeline searched for
    driver_result.json from the repository root, then exited with
    "missing first-wave driver result".  The driver half is fixed and
    regression-locked (scripts/soft_spot_shard_driver.py anchors relative
    --log-dir to the repository root; tests/test_soft_spot_shard_driver.py
    drives main() from a scratch cwd).  This lint guards the pipeline half:
    every find of driver_result.json must live under a --log-dir value the
    pipeline passes to the driver, and every --log-dir must be
    repository-relative so the anchored driver writes where the pipeline
    looks.

Usage:
    python memory/tools/detached_pipeline_lint.py            # all pipelines
    python memory/tools/detached_pipeline_lint.py --file <path>
    python memory/tools/detached_pipeline_lint.py --json

Failure modes:
    - No pipeline matches scripts/run_*_detached_pipeline.sh: exit 2
      (a restructured repo must not silently pass).
    - "${var}" interpolation in --log-dir values matches any suffix, so a
      find target differing only in the variable part passes; the lint
      catches wrong families (typos, absolute paths, scratch paths), not
      runtime variable values.
    - Lines that cannot be parsed are reported as violations, never skipped.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_GLOB = "scripts/run_*_detached_pipeline.sh"
LOG_DIR_RE = re.compile(r"--log-dir\s+[\"']?([^\"'\s]+)")
FIND_RESULT_RE = re.compile(r"find\s+([^\s]+)\s+-name\s+driver_result\.json")


def _pattern(value: str) -> str:
    """Compile a --log-dir value into a full-match regex; a "${var}" span
    becomes any suffix so wave1/wave2/wave3 find targets match a
    wave${wave} value."""
    escaped = re.escape(value)
    return re.sub(r"\\\$\\\{.*?\\\}", ".*?", escaped)


def lint_text(text: str) -> list[str]:
    """Return path-discipline violations in one pipeline script body."""
    errors: list[str] = []
    log_dirs = [match.group(1) for match in LOG_DIR_RE.finditer(text)]
    find_targets = [match.group(1) for match in FIND_RESULT_RE.finditer(text)]
    if not log_dirs:
        errors.append("no --log-dir argument found (driver logs unlocatable)")
    for value in log_dirs:
        if value.startswith("/"):
            errors.append(f"--log-dir must be repository-relative, got {value!r}")
        if "soft_spot_shard_driver" in value:
            errors.append(
                f"--log-dir points at a driver scratch tree, got {value!r}"
            )
    for target in find_targets:
        if target.startswith("/"):
            errors.append(
                f"driver_result.json find must be repository-relative, "
                f"got {target!r}"
            )
        if not any(
            re.fullmatch(_pattern(value), target) for value in log_dirs
        ):
            errors.append(
                f"find target {target!r} is not under any --log-dir value"
            )
    return errors


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default=None, help="lint one pipeline file")
    parser.add_argument("--json", action="store_true", help="machine-readable")
    args = parser.parse_args(argv)
    paths = (
        [Path(args.file)]
        if args.file is not None
        else sorted(ROOT.glob(PIPELINE_GLOB))
    )
    if not paths:
        print(f"ERROR: no pipelines matched {PIPELINE_GLOB}", file=sys.stderr)
        return 2
    report: dict[str, list[str]] = {}
    for path in paths:
        errors = lint_text(path.read_text(encoding="utf-8"))
        if errors:
            report[str(path.relative_to(ROOT))] = errors
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, errors in sorted(report.items()):
            print(f"{name}:")
            for error in errors:
                print(f"  - {error}")
        print(f"checked {len(paths)} pipeline(s), {len(report)} with violations")
    return 0 if not report else 1


if __name__ == "__main__":
    raise SystemExit(_main())
