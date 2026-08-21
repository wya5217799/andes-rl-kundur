"""R419 zero-out feature ablation (plan-registered execution amendment).

P1 literature implication 3 requires recording whether the trained policy
actually uses the added previous-executed-action feature.  This probe
re-evaluates the nine sealed R419 checkpoints with the actor-input
previous-action slots zeroed (the projector state and the executed-action
path are unchanged), recomputes the endpoints with the frozen estimators,
and compares them with the sealed full-feature evaluation records.

Usage (WSL, through the scratch launcher):
  python scripts/andes_scratch.py probes/r419_prev_action_ablation.py
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r419_slew_state_bundle as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import augment_joint_obs_np  # noqa: E402
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)

OUT = ROOT / "results/research_loop/r419_slew_state_bundle"

_ENDPOINTS = ("off_diagonal_response_energy", "disturbance_differential_energy")


def _evaluate_ablation(arm_id: str, seed: int) -> dict[str, Any]:
    contract = runner.build_contract()
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    checkpoint = OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
    agent = runner._agent_for(arm_id, "cpu")
    agent.load(checkpoint)
    projector = runner.PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    per_profile: dict[str, dict[str, float]] = {}
    for profile in evaluation:
        env = runner._build_env(profile)
        records = []
        try:
            for scenario in profile["scenarios"]:
                observation = env.reset(delta_u=dict(scenario["delta_u"]))
                projector.reset()
                initial_frequency = (
                    np.asarray(env._get_vsg_omega(), dtype=float)
                    * float(contract["physical_nominal_frequency_hz"])
                ).tolist()
                identity = {
                    "n_agents": int(env.N_AGENTS),
                    "vsg_idx": [str(value) for value in env.vsg_idx],
                    "vsg_buses": [
                        int(env.ss.GENCLS.bus.v[position])
                        for position in env._vsg_pos
                    ],
                    "obs_dim": int(env.OBS_DIM),
                    "baseline_m0": [
                        float(value) for value in profile["baseline_m0"]
                    ],
                    "baseline_d0": [
                        float(value) for value in profile["baseline_d0"]
                    ],
                    "control_nominal_frequency_hz": float(env.FN),
                    "physical_nominal_frequency_hz": float(
                        env.andes_nominal_frequency_hz
                    ),
                }
                rows = []
                failure = None
                for _step_index in range(int(contract["steps"])):
                    joint = runner._joint_obs(observation)
                    # zero-out ablation: the actor never sees the previous
                    # executed action; the projector keeps its true state.
                    augmented = augment_joint_obs_np(
                        joint, np.zeros((4, 2), dtype=np.float32)
                    )
                    raw = agent.act(augmented, deterministic=True)
                    action = projector.project(raw)
                    action_dict = {
                        actor: np.asarray(action[actor], dtype=np.float32)
                        for actor in range(4)
                    }
                    observation, _reward, done, info = env.step(action_dict)
                    actual_m = np.asarray(
                        [env.ss.GENCLS.M.v[position] for position in env._vsg_pos],
                        dtype=float,
                    )
                    actual_d = np.asarray(
                        [env.ss.GENCLS.D.v[position] for position in env._vsg_pos],
                        dtype=float,
                    )
                    rows.append(
                        {
                            "step_index": _step_index,
                            "time": float(info["time"]),
                            "action_norm": action.astype(float).tolist(),
                            "freq_hz_physical": np.asarray(
                                info["freq_hz_physical"], dtype=float
                            ).tolist(),
                            "M_es": actual_m.tolist(),
                            "D_es": actual_d.tolist(),
                            "delta_M": np.asarray(
                                info["delta_M"], dtype=float
                            ).tolist(),
                            "delta_D": np.asarray(
                                info["delta_D"], dtype=float
                            ).tolist(),
                            "tds_failed": bool(info["tds_failed"]),
                            "done": bool(done),
                        }
                    )
                    if info["tds_failed"]:
                        failure = "TDS failed"
                        break
                records.append(
                    {
                        "profile_id": str(profile["profile_id"]),
                        "split": str(profile["split"]),
                        "scenario_id": str(scenario["scenario_id"]),
                        "pair_kind": str(scenario["pair_kind"]),
                        "sign": str(scenario["sign"]),
                        "magnitude": float(scenario["magnitude"]),
                        "delta_u": dict(scenario["delta_u"]),
                        "arm_id": arm_id,
                        "training_seed": int(seed),
                        "checkpoint_sha256": runner._sha256_file(checkpoint),
                        "identity": identity,
                        "initial_freq_hz_physical": initial_frequency,
                        "steps": rows,
                        "completed_steps": len(rows),
                        "completed": failure is None
                        and len(rows) == int(contract["steps"]),
                        "tds_failed": failure is not None
                        or any(bool(row["tds_failed"]) for row in rows),
                        "failure": failure,
                        "reward_used_for_gate": False,
                        "training_executed": True,
                    }
                )
        finally:
            try:
                env.close()
            except Exception:
                pass
        summary = summarise_profile(records, contract=contract)
        per_profile[str(profile["profile_id"])] = {
            endpoint: float(summary[endpoint]) for endpoint in _ENDPOINTS
        }
    return {
        "arm_id": arm_id,
        "training_seed": int(seed),
        "checkpoint_sha256": runner._sha256_file(checkpoint),
        "ablation_endpoints": {
            endpoint: float(
                sum(per_profile[p][endpoint] for p in per_profile)
            )
            for endpoint in _ENDPOINTS
        },
    }


def _full_endpoints(arm_id: str, seed: int) -> dict[str, float]:
    contract = runner.build_contract()
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    totals = {endpoint: 0.0 for endpoint in _ENDPOINTS}
    for profile in evaluation:
        path = runner._eval_record_path(
            arm_id, seed, str(profile["profile_id"])
        )
        payload = runner._read_hashed_json(path)
        summary = summarise_profile(payload["records"], contract=contract)
        for endpoint in _ENDPOINTS:
            totals[endpoint] += float(summary[endpoint])
    return totals


def main() -> int:
    contract = runner.build_contract()
    rows = []
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            ablation = _evaluate_ablation(str(arm_id), int(seed))
            full = _full_endpoints(str(arm_id), int(seed))
            gaps = {
                endpoint: (
                    ablation["ablation_endpoints"][endpoint] - full[endpoint]
                )
                / full[endpoint]
                if full[endpoint] > 0.0
                else float("inf")
                for endpoint in _ENDPOINTS
            }
            rows.append(
                {
                    "arm_id": str(arm_id),
                    "training_seed": int(seed),
                    "full_endpoints": full,
                    "ablation_endpoints": ablation["ablation_endpoints"],
                    "relative_gap": gaps,
                }
            )
    payload = {
        "schema_version": 1,
        "round": "R419",
        "role": "plan_registered_analysis_amendment_zero_out_ablation",
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": runner._sha256_file(runner.SEAL),
        "ablation_rows": rows,
    }
    digest = runner._write_new_json(OUT / "prev_action_ablation.json", payload)
    print(f"R419 prev-action ablation: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
