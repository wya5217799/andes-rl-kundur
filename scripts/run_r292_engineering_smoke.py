#!/usr/bin/env python3
"""Run the non-performance R292 engineering gate on the real ANDES stack."""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.vector_residual_td3 import (  # noqa: E402
    CentralVectorTD3,
    DistributedEdgeTD3,
)
from andes_rl_kundur.control.vector_inertia_residual import (  # noqa: E402
    r292_vector_residual_contract,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    load_scenario_bank,
    sha256_bytes,
)
from andes_rl_kundur.evaluation.vector_residual import (  # noqa: E402
    ZeroVectorController,
    run_vector_controller_scenario,
)

BANK = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
DEFAULT_OUT = ROOT / "results/r292_engineering_smoke/smoke.json"


class WorkedVectorController:
    def __init__(self, raw_edge: list[float]) -> None:
        self.raw_edge = np.asarray(raw_edge, dtype=np.float32)

    def reset(self) -> None:
        return None

    def select_edge_actions(
        self,
        observations: Mapping[int, np.ndarray],
        *,
        deterministic: bool = True,
    ) -> np.ndarray:
        del observations
        if not deterministic:
            raise ValueError("worked engineering controller is deterministic")
        return self.raw_edge.copy()


def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite engineering smoke: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _agent_gate(agent: DistributedEdgeTD3, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    for index in range(8):
        observation = rng.normal(size=20).astype(np.float32)
        next_observation = rng.normal(size=20).astype(np.float32)
        agent.store(
            observation,
            rng.uniform(-1.0, 1.0, size=3).astype(np.float32),
            -float(index),
            next_observation,
            index == 7,
        )
    first = agent.update()
    second = agent.update()
    if first is None or second is None:
        raise RuntimeError("finite-update gate did not update")
    losses = [*first.values(), *second.values()]
    if not np.all(np.isfinite(np.asarray(losses, dtype=float))):
        raise RuntimeError("finite-update gate produced non-finite loss")
    observation = {
        index: rng.normal(size=5).astype(np.float32) for index in range(4)
    }
    before = agent.select_edge_actions(observation, deterministic=True)
    with tempfile.TemporaryDirectory(prefix="r292-checkpoint-") as directory:
        checkpoint = Path(directory) / "checkpoint.pt"
        agent.save(checkpoint, metadata={"round": "R292", "gate": True})
        restored = agent.__class__()
        metadata = restored.load(checkpoint)
        after = restored.select_edge_actions(observation, deterministic=True)
    if metadata != {"round": "R292", "gate": True} or not np.array_equal(
        before, after
    ):
        raise RuntimeError("checkpoint round-trip gate failed")
    return {
        "algo": agent.algo_name,
        "actor_parameter_count": sum(
            parameter.numel() for parameter in agent.actor.parameters()
        ),
        "losses_finite": True,
        "checkpoint_roundtrip_bit_identical": True,
        "policy_probe": before.tolist(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    bank, bank_hash = load_scenario_bank(BANK)
    scenario = bank["scenarios"][0]
    controllers = {
        "q0": ZeroVectorController(),
        "worked_forward": WorkedVectorController([1.0, -1.0, 0.5]),
        "worked_reverse": WorkedVectorController([-1.0, 0.5, 1.0]),
    }
    contract = r292_vector_residual_contract()
    rows = []
    for name, controller in controllers.items():
        record = run_vector_controller_scenario(
            controller,
            controller_name=name,
            controller_config={"engineering_only": True},
            scenario_name=scenario["name"],
            delta_u=scenario["delta_u"],
            seed=42,
            steps=3,
            phase="r292-engineering-smoke",
            evidence_hashes={"development_bank": bank_hash},
        )
        if not record["completed"] or record["tds_failed"]:
            raise RuntimeError(f"real ANDES smoke failed for {name}")
        edge = np.asarray(
            [row["r292_edge_flow_norm"] for row in record["traces"]], dtype=float
        )
        node = np.asarray(
            [row["r292_node_residual_norm"] for row in record["traces"]], dtype=float
        )
        action = np.asarray(
            [row["action_norm"] for row in record["traces"]], dtype=float
        )
        delta = np.diff(
            np.concatenate([np.zeros((1, 3), dtype=float), edge], axis=0),
            axis=0,
        )
        frequency = np.asarray(
            [row["freq_hz_physical"] for row in record["traces"]], dtype=float
        )
        checks = {
            "frequency_schema_3x4_finite": bool(
                frequency.shape == (3, 4) and np.all(np.isfinite(frequency))
            ),
            "edge_magnitude": bool(
                np.max(np.abs(edge)) <= contract.edge_flow_max + 1e-7
            ),
            "edge_slew": bool(
                np.max(np.abs(delta)) <= contract.edge_slew_max + 1e-7
            ),
            "node_magnitude": bool(
                np.max(np.abs(node)) <= contract.node_residual_max + 1e-7
            ),
            "zero_sum": bool(np.max(np.abs(np.sum(node, axis=1))) <= 1e-7),
            "d_zero": bool(np.max(np.abs(action[:, :, 1])) <= 1e-9),
        }
        if not all(checks.values()):
            raise RuntimeError(f"real ANDES smoke contract failed for {name}: {checks}")
        rows.append(
            {
                "controller": name,
                "completed": True,
                "n_steps": record["n_steps"],
                "checks": checks,
            }
        )
    torch.manual_seed(292)
    agent_rows = [
        _agent_gate(
            DistributedEdgeTD3(batch_size=4, buffer_size=32, policy_delay=2),
            292,
        ),
        _agent_gate(
            CentralVectorTD3(batch_size=4, buffer_size=32, policy_delay=2),
            293,
        ),
    ]
    payload = {
        "schema_version": 1,
        "round": "R292",
        "question": "Q-0049",
        "phase": "engineering-stability-gate",
        "performance_endpoints_inspected": False,
        "development_scenario": scenario["name"],
        "development_bank_sha256": bank_hash,
        "real_andes_rows": rows,
        "agent_rows": agent_rows,
        "actor_capacity": {
            "distributed_edge": agent_rows[0]["actor_parameter_count"],
            "central_vector": agent_rows[1]["actor_parameter_count"],
        },
        "all_pass": True,
    }
    digest = _write_new(args.out, payload)
    print(f"[R292 engineering gate] PASS sha256={digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
