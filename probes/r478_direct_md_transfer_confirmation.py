"""Run one scratch-only unseen-profile direct-M/D confirmation in parallel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r416_headroom_expansion as R416  # noqa: E402
from probes.r478_direct_md_canary import (  # noqa: E402
    DIRECT_CANARY_ARMS,
    classify_direct_md_profile,
    normalize_system_base_direct_telemetry,
)

PROFILE_IDS = ("dev_b", "eval_a", "eval_b", "eval_c", "eval_d")
WORKERS = 12
PARAMETER_CARD = (
    ROOT
    / "paper/yang_md_decoupling_marl/working/md_parameter_card_20260824.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("physical confirmation is WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("physical confirmation requires andes_scratch.py")


def _identity_snapshot() -> dict[str, Any]:
    sources = R416._source_manifest()
    sources.update(
        {
            "r478_confirmation_probe": {
                "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "r478_classifier": {
                "path": "probes/r478_direct_md_canary.py",
                "sha256": _sha256(
                    ROOT / "probes/r478_direct_md_canary.py"
                ),
            },
            "r478_parameter_card": {
                "path": PARAMETER_CARD.relative_to(ROOT).as_posix(),
                "sha256": _sha256(PARAMETER_CARD),
            },
        }
    )
    return {
        "scientific_sources": sources,
        "installed_runtime": R416._installed_runtime(),
    }


def _profile(profile_id: str) -> dict[str, Any]:
    if profile_id not in PROFILE_IDS:
        raise ValueError(f"unregistered transfer profile: {profile_id}")
    return next(
        dict(profile)
        for profile in R416._r399_contract()["profiles"]
        if profile["profile_id"] == profile_id
    )


def registered_tasks(profile_id: str) -> list[tuple[str, dict[str, Any]]]:
    """Return the two registered arms over all six unseen scenarios."""
    profile = _profile(profile_id)
    tasks = [
        (arm_id, dict(scenario))
        for arm_id in DIRECT_CANARY_ARMS
        for scenario in profile["scenarios"]
    ]
    if len(tasks) != 12:
        raise RuntimeError(f"expected 12 registered tasks, got {len(tasks)}")
    return tasks


def _run_task(task: tuple[str, int]) -> dict[str, Any]:
    os.environ.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    profile_id, index = task
    arm_id, scenario = registered_tasks(profile_id)[index]
    record = R416._run_job(_profile(profile_id), scenario, arm_id)
    record["registered_order"] = index
    return record


def run_confirmation(profile_id: str) -> dict[str, Any]:
    """Execute, normalize, and classify the unseen direct-M/D profile."""
    _assert_wsl_scratch()
    registered_tasks(profile_id)
    pre_attempt = _identity_snapshot()
    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        raw_records = list(
            executor.map(_run_task, [(profile_id, index) for index in range(12)])
        )
    card = json.loads(PARAMETER_CARD.read_text(encoding="utf-8"))
    normalized = normalize_system_base_direct_telemetry(
        raw_records,
        parameter_card=card,
    )
    decision = classify_direct_md_profile(
        normalized,
        profile_id=profile_id,
        contract=R416._r399_contract(),
    )
    post_attempt = _identity_snapshot()
    if pre_attempt != post_attempt:
        raise RuntimeError("source/runtime identity drifted during confirmation")
    return {
        "schema_version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "round": "R478",
        "manuscript_line": "yang-md-decoupling-marl",
        "scope": "scratch_route_confirmation_not_formal_evidence",
        "profile_id": profile_id,
        "workers": WORKERS,
        "raw_records": raw_records,
        "decision": decision,
        "training_authorized": False,
        "formal_evidence": False,
        "pre_attempt": pre_attempt,
        "post_attempt": post_attempt,
        "identity_stable": True,
        "sources": {
            "confirmation_probe": _sha256(Path(__file__).resolve()),
            "classifier": _sha256(
                ROOT / "probes/r478_direct_md_canary.py"
            ),
            "r416_runner": _sha256(
                ROOT / "scripts/run_r416_headroom_expansion.py"
            ),
            "base_env": _sha256(
                ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
            ),
            "parameter_card": _sha256(PARAMETER_CARD),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILE_IDS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.out.exists() or Path(f"{args.out}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite: {args.out}")
    payload = run_confirmation(args.profile)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(args.out)
    Path(f"{args.out}.sha256").write_text(
        f"{digest}  {args.out.name}\n", encoding="ascii"
    )
    print(
        json.dumps(
            {
                "output": str(args.out),
                "sha256": digest,
                "decision": payload["decision"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
