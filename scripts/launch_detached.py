"""Launch a long-running WSL pipeline detached from the harness session.

Motivation (R474/R475, 2026-08-23): launching ANDES training as a WSL
background process from Windows failed repeatedly — ``wsl.exe bash -lc '...
setsid nohup ... &'`` returns immediately, and WSL then terminates the
instance (killing the background job) because no foreground process keeps it
alive. The reliable pattern discovered in R475 is to hold the WSL instance
with a long-lived foreground watcher that owns the pipeline:

    python scripts/launch_detached.py scripts/run_r475_detached_pipeline.sh

which starts ``wsl.exe -d Ubuntu bash <script>`` with a keep-alive guard:
the watcher foreground process stays attached to the WSL console and reaps
the pipeline's exit status, so the instance survives until the pipeline
completes. Logs go to ``tmp/andes/<name>_detached_{stdout,stderr}.log``.

This is the maintained replacement for ad-hoc ``*.launch.ps1`` files (which
were written per round, never generalized, and silently failed when the WSL
instance had no other foreground holder).

Usage::

    python scripts/launch_detached.py scripts/run_r475_detached_pipeline.sh
    python scripts/launch_detached.py --wsl Ubuntu --keepalive 300 scripts/run_r475_detached_pipeline.sh

Failure modes:
- ``--check-wsl`` runs ``wsl -d <distro> true`` first; exit 2 if WSL is
  unavailable.
- The watcher blocks until the pipeline finishes; run it as a harness
  background job (``run_in_background: true``) and let the completion
  notification drive the round's next phase.
- If the harness session dies, the watcher dies and WSL may terminate the
  instance; do NOT rely on this tool to survive a session kill. For that,
  use an OS-level service (schtasks/nssm) — out of scope here.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="bash pipeline script under scripts/")
    parser.add_argument("--wsl", default="Ubuntu", help="WSL distro name")
    parser.add_argument("--keepalive", type=int, default=0,
                        help="seconds for an extra keep-alive sleep after the pipeline exits (default 0)")
    parser.add_argument("--check-wsl", action="store_true",
                        help="verify `wsl -d <distro> true` before launching")
    args = parser.parse_args()

    script = args.script if args.script.is_absolute() else ROOT / args.script
    if not script.is_file():
        print(f"pipeline script not found: {script}", file=sys.stderr)
        return 2
    if args.check_wsl:
        probe = subprocess.run(["wsl.exe", "-d", args.wsl, "true"], capture_output=True)
        if probe.returncode != 0:
            print(f"WSL distro {args.wsl} unavailable (wsl -d {args.wsl} true failed)", file=sys.stderr)
            return 2
    name = script.stem
    stdout = ROOT / "tmp" / "andes" / f"{name}_detached_stdout.log"
    stderr = ROOT / "tmp" / "andes" / f"{name}_detached_stderr.log"
    stdout.parent.mkdir(parents=True, exist_ok=True)
    print(f"launching {script} via wsl -d {args.wsl}; logs: {stdout} / {stderr}")
    # Foreground watcher: keep the WSL instance alive until the pipeline
    # finishes, then optionally hold it a little longer (grace for flush).
    with stdout.open("wb") as out, stderr.open("wb") as err:
        code = subprocess.call(
            ["wsl.exe", "-d", args.wsl, "bash", str(script)],
            stdout=out, stderr=err,
        )
    if args.keepalive and code == 0:
        subprocess.call(["wsl.exe", "-d", args.wsl, "bash", "-lc", f"sleep {args.keepalive}"])
    print(f"pipeline exit code: {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())
