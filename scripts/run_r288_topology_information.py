#!/usr/bin/env python3
"""Stable CLI for the sealed R288 topology-information value experiment.

Run through ``scripts/andes_scratch.py`` with the WSL ANDES interpreter.
``prepare`` performs only structural inspection and q0 power flows, then
freezes the topology inventory and seal. ``run`` creates the 4x7 EIG matrix.
``analyse`` applies the already-tested pure decision contract.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "probes" / "r288_topology_information.py"
ROUND_ID = "R288"
QUESTION_ID = "Q-0047"
DEFAULT_SEAL = ROOT / "memory" / "rounds" / ROUND_ID / "topology_information_seal.json"
DEFAULT_OUT = ROOT / "results" / "r288_topology_information"


def _load_probe() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_r288_topology_probe", PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load R288 probe: {PROBE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    prepare.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)

    run = commands.add_parser("run")
    run.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run.add_argument("--expected-seal-sha256", required=True)
    run.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)

    analyse = commands.add_parser("analyse")
    analyse.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse.add_argument("--expected-seal-sha256", required=True)
    analyse.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    probe = _load_probe()
    if args.command == "prepare":
        probe.prepare(args.seal, args.out_dir)
    elif args.command == "run":
        probe.run(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        probe.analyse(args.seal, args.expected_seal_sha256, args.out_dir)


if __name__ == "__main__":
    main()
