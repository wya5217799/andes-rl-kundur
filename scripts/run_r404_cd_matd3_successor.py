"""Science-identical R404 correction wrapper for the R403 dev gate.

Only the diagnostic sentinel and rehearsal depth change.  The complete R403
scientific development contract is imported unchanged and re-sealed before the
single create-only attempt.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r403_cd_matd3_successor as base
from andes_rl_kundur.evaluation.cd_matd3_successor import contract_sha256

ROUND_ID = "R404"
PLAN = ROOT / "memory/rounds/R404/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R404/rehearsal.json"
SEAL = ROOT / "memory/rounds/R404/development_seal.json"
OUT = ROOT / "tmp/r404_cd_matd3_successor"
PARENT_SEAL = ROOT / "memory/rounds/R403/development_seal.json"
PARENT_CONTRACT_SHA256 = (
    "dad9b0e5775982c67c478acb178ccfc1befc05ea081c3aed5aea95309b5bae02"
)


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r404_cd_matd3_successor.py",
        "corrected_learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "learner_tests": ROOT / "tests/test_cd_matd3_successor.py",
        "scientific_gate": ROOT
        / "src/andes_rl_kundur/evaluation/cd_matd3_successor.py",
        "gate_tests": ROOT / "tests/test_cd_matd3_successor_gate.py",
        "parent_adapter": ROOT / "scripts/run_r403_cd_matd3_successor.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT
        / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing R404 sources: {missing}")
    return {
        name: {"path": base._relative(path), "sha256": base._sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_valid() -> bool:
    try:
        parent = base._read_hashed_json(PARENT_SEAL)
    except (FileNotFoundError, RuntimeError, ValueError):
        return False
    return (
        parent.get("round") == "R403"
        and parent.get("contract_sha256") == PARENT_CONTRACT_SHA256
        and contract_sha256(base.build_successor_contract())
        == PARENT_CONTRACT_SHA256
    )


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and ROUND_ID in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "parent_hash": _parent_valid(),
        "output_absence": not OUT.exists(),
    }


def _configure_parent_adapter() -> None:
    base.ROUND_ID = ROUND_ID
    base.PLAN = PLAN
    base.LINE = LINE
    base.REHEARSAL = REHEARSAL
    base.SEAL = SEAL
    base.OUT = OUT
    base._source_manifest = _source_manifest
    base._authority_checks = _authority_checks


def deep_diagnostic_rehearsal() -> dict[str, Any]:
    """Cross the registered batch/update seam and require strict JSON."""

    agent = base._repaired_agent()
    batch_size = int(agent.batch_size)
    observation = np.zeros(28, dtype=np.float32)
    action = np.zeros(8, dtype=np.float32)
    reward = np.array([-0.5, -0.2], dtype=np.float32)
    for _ in range(batch_size):
        agent.store(observation, action, reward, observation, False)
    critic_only = agent.update()
    actor_update = agent.update()
    if critic_only is None or actor_update is None:
        raise RuntimeError("registered update seam did not return diagnostics")
    if critic_only.get("policy_updated") != 0.0:
        raise RuntimeError("critic-only update state is not explicit")
    if actor_update.get("policy_updated") != 1.0:
        raise RuntimeError("actor-update state is not explicit")
    for row in (critic_only, actor_update):
        if not all(np.isfinite(float(value)) for value in row.values()):
            raise RuntimeError("nonfinite diagnostic survived correction")
    payload = {
        "batch_size": batch_size,
        "critic_only": critic_only,
        "actor_update": actor_update,
    }
    json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return payload


def rehearse() -> str:
    _configure_parent_adapter()
    diagnostics = deep_diagnostic_rehearsal()
    digest = base.rehearse()
    payload = base._read_hashed_json(REHEARSAL)
    if payload.get("checks", {}).get("parent_hash") is not True:
        raise RuntimeError("rehearsal did not bind the R403 parent contract")
    if diagnostics["critic_only"]["policy_updated"] != 0.0:
        raise RuntimeError("deep diagnostic rehearsal drifted")
    return digest


def seal() -> str:
    """Seal the unchanged parent contract plus corrected diagnostic sources."""

    _configure_parent_adapter()
    base._assert_wsl_scratch()
    rehearsal_payload = base._read_hashed_json(REHEARSAL)
    checks = _authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"R404 seal checks failed: {checks}")
    sources = _source_manifest()
    runtime = base._installed_runtime()
    contract = base.build_successor_contract()
    if rehearsal_payload.get("sources") != sources:
        raise RuntimeError("source drift after R404 rehearsal")
    if rehearsal_payload.get("installed_runtime") != runtime:
        raise RuntimeError("runtime drift after R404 rehearsal")
    if rehearsal_payload.get("contract") != contract:
        raise RuntimeError("scientific contract drift after R404 rehearsal")
    parent = base._read_hashed_json(PARENT_SEAL)
    return base._write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": contract_sha256(contract),
            "parent": {
                "path": base._relative(PARENT_SEAL),
                "sha256": base._sha256_file(PARENT_SEAL),
                "contract_sha256": parent["contract_sha256"],
            },
            "sources": sources,
            "installed_runtime": runtime,
            "r402_checkpoint": {
                "path": base._relative(base.R402_CHECKPOINT),
                "sha256": base._sha256_file(base.R402_CHECKPOINT),
            },
            "rehearsal_sha256": base._sha256_file(REHEARSAL),
            "launch": {
                "host_process_budget": 9,
                "wsl_python_processes": 2,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "output_root": base._relative(OUT),
        },
    )


def run() -> str:
    _configure_parent_adapter()
    return base.run()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rehearse", "seal", "run"))
    command = parser.parse_args().command
    if command == "rehearse":
        print(f"R404 rehearsal: {rehearse()}", flush=True)
    elif command == "seal":
        print(f"R404 development seal: {seal()}", flush=True)
    else:
        print(f"R404 development decision: {run()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
