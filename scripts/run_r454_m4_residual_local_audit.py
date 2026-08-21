"""R454 M4: residual-identity local geometry and checkpoint mechanism audit.

Physical commands are WSL-only and must run through ``andes_scratch.py``.
Formal artifacts are create-only JSON files with SHA-256 sidecars.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r436_energy_residual_sac as R436
from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
from andes_rl_kundur.control.feasibility_native_vsg_action import (
    FeasibilityNativeVSGActionMap,
)

ROUND_ID = "R454"
PLAN = ROOT / "memory/rounds/R454/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R454/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R454/rehearsal.json"
SEAL = ROOT / "memory/rounds/R454/formal_seal.json"
SHARDS = ROOT / "tmp/andes/r454_m4_shards.json"
OUT = ROOT / "results/research_loop/r454_m4_residual_local_audit"

ARMS = tuple(R436.LEARNING_ARMS)
SEEDS = tuple(int(value) for value in R436.TRAINING_SEEDS)
CONDITIONS = tuple(copy.deepcopy(R436.TRAINING_CONDITIONS))
DIRECTIONS = {
    "c": np.asarray([1.0, 1.0, 1.0, 1.0]) / 2.0,
    "d1": np.asarray([1.0, -1.0, 0.0, 0.0]) / math.sqrt(2.0),
    "d2": np.asarray([1.0, 1.0, -2.0, 0.0]) / math.sqrt(6.0),
    "d3": np.asarray([1.0, 1.0, 1.0, -3.0]) / math.sqrt(12.0),
}
EPSILONS = (0.10, 0.03, 0.01)
E_MIN = 0.01
CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS = 32
WORKER_RSS_FLOOR_BYTES = 944_214_016
OS_FLOOR_BYTES = 3 * 1024**3


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    sidecar = Path(f"{path}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    digest = _sha256_file(path)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if expected != actual:
        raise RuntimeError(f"hash mismatch: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _basis_error() -> float:
    matrix = np.stack(list(DIRECTIONS.values()))
    return float(np.max(np.abs(matrix @ matrix.T - np.eye(4))))


def expected_shard_ids() -> list[str]:
    condition_ids = [str(row["condition_id"]) for row in CONDITIONS]
    result = [f"anchor|{condition_id}" for condition_id in condition_ids]
    result.extend(
        f"checkpoint|{arm}|{seed}|{condition_id}"
        for arm in ARMS
        for seed in SEEDS
        for condition_id in condition_ids
    )
    return result


def build_contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "parent_round": "R436",
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "conditions": copy.deepcopy(list(CONDITIONS)),
        "directions": {key: value.tolist() for key, value in DIRECTIONS.items()},
        "basis_max_gram_error": _basis_error(),
        "epsilons": list(EPSILONS),
        "steps": int(R436.STEPS_PER_EPISODE),
        "gamma": float(R436.GAMMA),
        "residual_scale": float(R436.RESIDUAL_SCALE),
        "trajectory_count": 825,
        "shard_count": 33,
        "geometry_thresholds": {
            "relative_drift_max": 0.25,
            "material_min": 1.0e-3,
            "leave_one_out_material_min": 5.0e-4,
        },
        "critic_tie_relative_tolerance": 1.0e-8,
        "critic_material_min": 1.0e-3,
        "update_parameter_relative_min": 1.0e-7,
        "update_action_rms_min": 1.0e-6,
        "projection_derivative_max": 1.0e-6,
        "projection_suppressed_fraction_min": 0.95,
        "plan_sha256": _sha256_file(PLAN),
    }


def contract_sha256() -> str:
    return _canonical_sha256(build_contract())


def _checkpoint_inventory() -> list[dict[str, Any]]:
    rows = []
    for arm in ARMS:
        for seed in SEEDS:
            path = R436._checkpoint_path(arm, seed)
            sidecar = Path(f"{path}.sha256")
            expected = sidecar.read_text(encoding="ascii").split()[0]
            actual = _sha256_file(path)
            rows.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "path": _relative(path),
                    "sha256": actual,
                    "sidecar_matches": expected == actual,
                }
            )
    return rows


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    inventory = _checkpoint_inventory()
    return {
        "active_plan": "round: R454" in plan_text and "state: active" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "basis": _basis_error() <= 1.0e-12,
        "shards": len(expected_shard_ids()) == 33
        and len(set(expected_shard_ids())) == 33,
        "checkpoint_inventory": len(inventory) == 10
        and all(row["sidecar_matches"] for row in inventory),
        "output_absence": not OUT.exists(),
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R454 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R454 must run through scripts/andes_scratch.py")


def installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != contract_sha256():
        raise RuntimeError("contract drifted from seal")
    if _sha256_file(CAPACITY) != seal.get("capacity_sha256"):
        raise RuntimeError("capacity evidence drifted from seal")
    if _sha256_file(REHEARSAL) != seal.get("rehearsal_sha256"):
        raise RuntimeError("rehearsal evidence drifted from seal")
    for entry in (seal.get("sources") or {}).values():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {entry['path']}")
    for entry in seal.get("checkpoints", []):
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed checkpoint drift: {entry['path']}")
    return seal


def _reward_components(
    joint_obs: np.ndarray, residuals: np.ndarray, masked: bool
) -> dict[str, Any]:
    f_dev = np.asarray(joint_obs[:, 0], dtype=float)
    neighbour_dev = np.asarray(joint_obs[:, 3:5], dtype=float)
    r_f, r_abs, r_h, r_d = [], [], [], []
    for index in range(4):
        eta = np.asarray([0.0, 0.0] if masked else [1.0, 1.0])
        omega_bar = float(
            (f_dev[index] + np.dot(eta, neighbour_dev[index]))
            / (1.0 + np.sum(eta))
        )
        r_f.append(
            -(f_dev[index] - omega_bar) ** 2
            - float(np.sum(eta * (neighbour_dev[index] - omega_bar) ** 2))
        )
        r_abs.append(-float(residuals[index]) ** 2)
        r_h.append(-(float(np.mean(residuals)) / 2.0) ** 2)
        r_d.append(-float(np.mean(residuals - np.mean(residuals))) ** 2)
    total = (
        100.0 * np.asarray(r_f)
        + 50.0 * np.asarray(r_abs)
        + 0.0056 * np.asarray(r_h)
        + 0.0056 * np.asarray(r_d)
    )
    return {
        "r_f": r_f,
        "r_abs": r_abs,
        "r_H": r_h,
        "r_D": r_d,
        "per_agent_reward": total.tolist(),
        "joint_reward": float(np.sum(total)),
    }


def _condition(condition_id: str) -> dict[str, Any]:
    for row in CONDITIONS:
        if str(row["condition_id"]) == condition_id:
            return copy.deepcopy(row)
    raise KeyError(condition_id)


def _trajectory_specifications() -> list[dict[str, Any]]:
    specs = [{"direction": None, "epsilon": 0.0, "sign": 0}]
    specs.extend(
        {"direction": direction, "epsilon": epsilon, "sign": sign}
        for direction in DIRECTIONS
        for epsilon in EPSILONS
        for sign in (-1, 1)
    )
    return specs


def _run_trajectory(
    *,
    condition: Mapping[str, Any],
    arm: str | None,
    seed: int | None,
    direction: str | None,
    epsilon: float,
    sign: int,
) -> dict[str, Any]:
    masked = arm == R436.NO_MESSAGE_ARM
    agent = None if arm is None else R436._load_agent(arm, int(seed))
    env = R436._build_env()
    controller = R436.BandpassArmController(
        k=3.5, nominal_frequency_hz=R436.NOMINAL_FREQUENCY_HZ
    )
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    previous_residuals = np.zeros(4, dtype=float)
    previous_executed_power = np.zeros(4, dtype=float)
    previous_p_es = np.zeros(4, dtype=float)
    rows: list[dict[str, Any]] = []
    failure: str | None = None
    identity: dict[str, Any] | None = None
    try:
        env.reset(delta_u=dict(condition["delta_u"]))
        previous_frequencies = R436._frequencies(env)
        identity = R436._identity(env.base_env)
        vector = np.zeros(4) if direction is None else DIRECTIONS[direction]
        for step_index in range(int(R436.STEPS_PER_EPISODE)):
            frequencies = R436._frequencies(env)
            joint = R436._joint_obs(
                frequencies,
                previous_frequencies,
                previous_p_es,
                previous_residuals,
                masked,
            )
            raw_base = (
                np.zeros(4, dtype=float)
                if agent is None
                else np.asarray(agent.act(joint, deterministic=True), dtype=float).reshape(4)
            )
            perturbation = float(sign) * float(epsilon) * vector
            raw = raw_base + perturbation
            if not np.all(np.isfinite(raw)) or np.any(raw < -1.0) or np.any(raw > 1.0):
                raise RuntimeError("raw action outside [-1,1]")
            residuals = float(R436.RESIDUAL_SCALE) * raw
            controller_action = controller.act(frequencies, dt_seconds=0.2)
            common_action = np.mean(controller_action) * np.ones(4)
            differential_action = controller_action - common_action
            voltage = R436._voltage_pu(env)
            baseline_mapped = action_map.map_action(
                normalized_actions=controller_action,
                previous_power_system_pu=previous_executed_power,
                soc=np.full(4, 0.5),
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            baseline = np.asarray(baseline_mapped.feasible_power_system_pu)
            mapped = action_map.map_residual_action(
                normalized_residual_actions=residuals,
                baseline_power_system_pu=baseline,
                previous_power_system_pu=previous_executed_power,
                soc=np.full(4, 0.5),
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            _observation, _env_reward, done, info = env.step(
                mapped.feasible_power_system_pu
            )
            frequencies_after = R436._frequencies(env)
            p_es_after = np.asarray(info["P_es"], dtype=float)
            if p_es_after.shape != (4,):
                raise RuntimeError("unexpected P_es shape")
            joint_after = R436._joint_obs(
                frequencies_after, frequencies, p_es_after, residuals, masked
            )
            reward_by_definition = {}
            for reward_name, reward_masked in (
                ("no_message", True),
                ("message", False),
            ):
                reward_joint = R436._joint_obs(
                    frequencies_after,
                    frequencies,
                    p_es_after,
                    residuals,
                    reward_masked,
                )
                components = _reward_components(
                    reward_joint, residuals, reward_masked
                )
                exact = R436._reward(reward_joint, residuals, reward_masked)
                if not np.allclose(
                    exact,
                    np.asarray(components["per_agent_reward"]),
                    rtol=1.0e-6,
                    atol=1.0e-8,
                ):
                    raise RuntimeError("reward decomposition mismatch")
                if bool(info["tds_failed"]):
                    components["per_agent_reward"] = [-50.0] * 4
                    components["joint_reward"] = -200.0
                reward_by_definition[reward_name] = components
            lower = np.asarray(mapped.lower_power_system_pu, dtype=float)
            upper = np.asarray(mapped.upper_power_system_pu, dtype=float)
            positive = upper - baseline
            negative = baseline - lower
            branch_headroom = np.where(residuals >= 0.0, positive, negative)
            port_row = R436._port_row(info, step_index=step_index, done=bool(done))
            port_row.update(
                {
                    "joint_obs": np.asarray(joint, dtype=float).tolist(),
                    "joint_obs_after": np.asarray(joint_after, dtype=float).tolist(),
                    "raw_base_action": raw_base.tolist(),
                    "raw_perturbation": perturbation.tolist(),
                    "raw_action": raw.tolist(),
                    "scaled_residual": residuals.tolist(),
                    "controller_action": np.asarray(controller_action).tolist(),
                    "common_action": common_action.tolist(),
                    "differential_action": differential_action.tolist(),
                    "baseline_power_system_pu": baseline.tolist(),
                    "mapped_power_system_pu": np.asarray(
                        mapped.feasible_power_system_pu
                    ).tolist(),
                    "lower_power_system_pu": lower.tolist(),
                    "upper_power_system_pu": upper.tolist(),
                    "positive_headroom": positive.tolist(),
                    "negative_headroom": negative.tolist(),
                    "selected_branch": [
                        "positive" if value >= 0.0 else "negative"
                        for value in residuals
                    ],
                    "branch_derivative_pu_per_raw": (
                        float(R436.RESIDUAL_SCALE) * branch_headroom
                    ).tolist(),
                    "external_projection_identity": bool(
                        mapped.external_projection_identity
                    ),
                    "reward_by_definition": reward_by_definition,
                }
            )
            rows.append(port_row)
            previous_frequencies = frequencies_after.copy()
            previous_residuals = residuals.copy()
            previous_executed_power = np.asarray(
                mapped.feasible_power_system_pu, dtype=float
            ).copy()
            previous_p_es = p_es_after.copy()
            if bool(info["tds_failed"]):
                failure = "tds_failed"
                break
        returns: dict[str, Any] = {}
        for reward_name in ("no_message", "message"):
            step_rewards = np.asarray(
                [
                    row["reward_by_definition"][reward_name]["joint_reward"]
                    for row in rows
                ],
                dtype=float,
            )
            returns[reward_name] = {
                "undiscounted": float(np.sum(step_rewards)),
                "discounted": float(
                    np.sum(
                        np.power(float(R436.GAMMA), np.arange(len(step_rewards)))
                        * step_rewards
                    )
                ),
            }
        frequencies_all = np.asarray(
            [row["freq_hz_physical"] for row in rows], dtype=float
        )
        endpoint = {
            "common_frequency_iae_hz_s": float(
                0.2 * np.sum(np.abs(np.mean(frequencies_all, axis=1) - 60.0))
            ),
            "worst_unit_peak_hz": float(np.max(np.abs(frequencies_all - 60.0))),
            "action_rms": float(
                np.sqrt(
                    np.mean(
                        np.square(
                            np.asarray(
                                [row["mapped_power_system_pu"] for row in rows]
                            )
                        )
                    )
                )
            ),
        }
        completed = len(rows) == int(R436.STEPS_PER_EPISODE) and failure is None
        return {
            "condition_id": str(condition["condition_id"]),
            "arm": arm,
            "seed": seed,
            "direction": direction,
            "epsilon": float(epsilon),
            "sign": int(sign),
            "identity": identity,
            "completed": completed,
            "completed_steps": len(rows),
            "failure": failure,
            "returns": returns,
            "endpoint": endpoint,
            "rows": rows,
        }
    finally:
        try:
            env.close()
        except Exception:
            pass


def _shard_path(shard_id: str) -> Path:
    return OUT / "shards" / (shard_id.replace("|", "__") + ".json")


def run_shard(shard_id: str, *, resume: bool = False) -> str:
    _assert_wsl_scratch()
    load_seal()
    if shard_id not in expected_shard_ids():
        raise ValueError(f"unknown shard id: {shard_id}")
    path = _shard_path(shard_id)
    if resume and path.is_file() and Path(f"{path}.sha256").is_file():
        return json.dumps({"shard_id": shard_id, "status": "already-complete"})
    parts = shard_id.split("|")
    if parts[0] == "anchor":
        arm, seed, condition_id = None, None, parts[1]
    else:
        _, arm, seed_text, condition_id = parts
        seed = int(seed_text)
    condition = _condition(condition_id)
    checkpoint_before = (
        None if arm is None else _sha256_file(R436._checkpoint_path(arm, int(seed)))
    )
    started = time.monotonic()
    trajectories = [
        _run_trajectory(
            condition=condition,
            arm=arm,
            seed=seed,
            direction=spec["direction"],
            epsilon=float(spec["epsilon"]),
            sign=int(spec["sign"]),
        )
        for spec in _trajectory_specifications()
    ]
    checkpoint_after = (
        None if arm is None else _sha256_file(R436._checkpoint_path(arm, int(seed)))
    )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "shard_id": shard_id,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "trajectory_count": len(trajectories),
        "completed_trajectory_count": sum(row["completed"] for row in trajectories),
        "checkpoint_sha256_before": checkpoint_before,
        "checkpoint_sha256_after": checkpoint_after,
        "checkpoint_immutable": checkpoint_before == checkpoint_after,
        "wall_seconds": time.monotonic() - started,
        "trajectories": trajectories,
    }
    digest = _write_new_json(path, payload)
    return json.dumps({"shard_id": shard_id, "sha256": digest}, sort_keys=True)


def centered_geometry(
    values: Mapping[str, Mapping[float, Mapping[int, float]]]
) -> dict[str, Any]:
    """Compute registered centered slopes/curvatures from condition values."""
    condition_ids = list(values)
    if len(condition_ids) != 3:
        raise ValueError("registered geometry requires exactly three conditions")
    zero = {condition: float(values[condition][0.0][0]) for condition in condition_ids}

    def estimate(subset: Sequence[str], epsilon: float) -> tuple[float, float, float]:
        plus = np.mean([values[c][epsilon][1] for c in subset])
        minus = np.mean([values[c][epsilon][-1] for c in subset])
        anchor = np.mean([zero[c] for c in subset])
        return (
            float((plus - minus) / (2.0 * epsilon)),
            float((plus - 2.0 * anchor + minus) / epsilon**2),
            float(max(1.0, np.mean([abs(zero[c]) for c in subset]))),
        )

    estimates = {}
    for epsilon in EPSILONS:
        slope, curvature, scale = estimate(condition_ids, epsilon)
        estimates[str(epsilon)] = {
            "slope": slope,
            "curvature": curvature,
            "scale": scale,
        }
    g03 = estimates["0.03"]["slope"]
    g01 = estimates["0.01"]["slope"]
    h03 = estimates["0.03"]["curvature"]
    h01 = estimates["0.01"]["curvature"]
    scale = estimates["0.01"]["scale"]

    def stable(first: float, second: float) -> bool:
        return bool(
            first != 0.0
            and second != 0.0
            and np.sign(first) == np.sign(second)
            and abs(first - second) / max(abs(second), 1.0e-30) <= 0.25
        )

    slope_stable = stable(g03, g01)
    curvature_stable = stable(h03, h01)
    slope_materiality = E_MIN * abs(g01) / scale
    curvature_materiality = 0.5 * E_MIN**2 * abs(h01) / scale
    leave_one_out = []
    for omitted in condition_ids:
        subset = [value for value in condition_ids if value != omitted]
        slope, curvature, subscale = estimate(subset, E_MIN)
        leave_one_out.append(
            {
                "omitted": omitted,
                "slope": slope,
                "curvature": curvature,
                "slope_materiality": E_MIN * abs(slope) / subscale,
                "curvature_materiality": 0.5 * E_MIN**2 * abs(curvature) / subscale,
            }
        )
    slope_loo = all(
        row["slope"] != 0.0
        and np.sign(row["slope"]) == np.sign(g01)
        and row["slope_materiality"] >= 5.0e-4
        for row in leave_one_out
    )
    curvature_loo = all(
        row["curvature"] != 0.0
        and np.sign(row["curvature"]) == np.sign(h01)
        and row["curvature_materiality"] >= 5.0e-4
        for row in leave_one_out
    )
    return {
        "estimates": estimates,
        "slope_stable_material": bool(
            slope_stable and slope_materiality >= 1.0e-3 and slope_loo
        ),
        "slope_materiality": slope_materiality,
        "slope_sign": int(np.sign(g01)),
        "curvature_stable_material": bool(
            curvature_stable
            and curvature_materiality >= 1.0e-3
            and curvature_loo
        ),
        "curvature_materiality": curvature_materiality,
        "curvature_sign": int(np.sign(h01)),
        "leave_one_out": leave_one_out,
    }


def classify_anchor(geometry: Mapping[str, Mapping[str, Any]]) -> str:
    rows = list(geometry.values())
    if any(row["slope_stable_material"] for row in rows):
        return "IDENTITY-NOT-STATIONARY"
    if any(
        row["curvature_stable_material"] and row["curvature_sign"] > 0
        for row in rows
    ):
        return "IDENTITY-POSITIVE-CURVATURE"
    if rows and all(
        not row["slope_stable_material"]
        and row["curvature_stable_material"]
        and row["curvature_sign"] < 0
        for row in rows
    ):
        return "IDENTITY-LOCAL-MAX-SUPPORTED-ON-REGISTERED-SLICE"
    return "IDENTITY-LOCAL-GEOMETRY-INCONCLUSIVE"


def select_twin_gradient(
    q1: np.ndarray,
    q2: np.ndarray,
    grad1: np.ndarray,
    grad2: np.ndarray,
    *,
    tolerance: float = 1.0e-8,
) -> np.ndarray:
    q1a, q2a = np.asarray(q1), np.asarray(q2)
    tie = np.abs(q1a - q2a) <= tolerance * np.maximum(
        1.0, np.maximum(np.abs(q1a), np.abs(q2a))
    )
    return np.where(tie, 0.5 * (grad1 + grad2), np.where(q1a < q2a, grad1, grad2))


def _checkpoint_diagnostics(
    arm: str, seed: int, zero_trajectories: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    wrapper = R436._load_agent(arm, seed)
    checkpoint_path = R436._checkpoint_path(arm, seed)
    before_hash = _sha256_file(checkpoint_path)
    states_by_agent: list[list[list[float]]] = [[] for _ in range(4)]
    actions_by_agent: list[list[list[float]]] = [[] for _ in range(4)]
    for trajectory in zero_trajectories:
        for row in trajectory["rows"]:
            joint = np.asarray(row["joint_obs"], dtype=float)
            raw = np.asarray(row["raw_base_action"], dtype=float)
            for index in range(4):
                states_by_agent[index].append(joint[index].tolist())
                actions_by_agent[index].append([float(raw[index])])
    per_agent = []
    mean_gradient_vector = np.zeros(4)
    qmin_abs = []
    for index, agent in enumerate(wrapper.agents):
        obs_t = torch.tensor(states_by_agent[index], dtype=torch.float32)
        action_t = torch.tensor(
            actions_by_agent[index], dtype=torch.float32, requires_grad=True
        )
        q1, q2 = agent.critic(obs_t, action_t)
        grad1 = torch.autograd.grad(q1.sum(), action_t, retain_graph=True)[0]
        grad2 = torch.autograd.grad(q2.sum(), action_t)[0]
        selected = select_twin_gradient(
            q1.detach().numpy(),
            q2.detach().numpy(),
            grad1.detach().numpy(),
            grad2.detach().numpy(),
        )
        qmin = np.minimum(q1.detach().numpy(), q2.detach().numpy())
        mean_gradient_vector[index] = float(np.mean(selected))
        qmin_abs.extend(np.abs(qmin).reshape(-1).tolist())
        per_agent.append(
            {
                "agent": index,
                "state_count": len(states_by_agent[index]),
                "mean_selected_gradient": float(np.mean(selected)),
                "mean_abs_qmin": float(np.mean(np.abs(qmin))),
                "tie_count": int(
                    np.sum(
                        np.abs(q1.detach().numpy() - q2.detach().numpy())
                        <= 1.0e-8
                        * np.maximum(
                            1.0,
                            np.maximum(
                                np.abs(q1.detach().numpy()),
                                np.abs(q2.detach().numpy()),
                            ),
                        )
                    )
                ),
            }
        )
    q_scale = max(1.0, float(np.mean(qmin_abs)))
    critic_directions = {}
    for name, direction in DIRECTIONS.items():
        value = float(np.dot(mean_gradient_vector, direction))
        materiality = E_MIN * abs(value) / q_scale
        critic_directions[name] = {
            "mean_gradient": value,
            "sign": int(np.sign(value)),
            "materiality": materiality,
            "material": bool(materiality >= 1.0e-3),
        }

    update_wrapper = R436._load_agent(arm, seed)
    deterministic_before, deterministic_after = [], []
    flat_before = []
    for index, agent in enumerate(update_wrapper.agents):
        obs_t = torch.tensor(states_by_agent[index], dtype=torch.float32)
        with torch.no_grad():
            deterministic_before.append(agent.actor.deterministic(obs_t).clone())
        flat_before.extend(
            parameter.detach().reshape(-1).clone() for parameter in agent.actor.parameters()
        )
    torch.manual_seed(10_000 + seed + (0 if arm == ARMS[0] else 1_000))
    losses, grad_norms = [], []
    for index, agent in enumerate(update_wrapper.agents):
        obs_t = torch.tensor(states_by_agent[index], dtype=torch.float32)
        sampled, log_prob = agent.actor.sample(obs_t)
        q1, q2 = agent.critic(obs_t, sampled)
        actor_loss = (agent.alpha.detach() * log_prob - torch.min(q1, q2)).mean()
        agent.actor_optimizer.zero_grad()
        actor_loss.backward()
        grad_norm = nn.utils.clip_grad_norm_(agent.actor.parameters(), R436.MAX_GRAD_NORM)
        agent.actor_optimizer.step()
        losses.append(float(actor_loss.detach()))
        grad_norms.append(float(grad_norm))
        with torch.no_grad():
            deterministic_after.append(agent.actor.deterministic(obs_t).clone())
    flat_after = [
        parameter.detach().reshape(-1).clone()
        for agent in update_wrapper.agents
        for parameter in agent.actor.parameters()
    ]
    before_vector = torch.cat(flat_before)
    after_vector = torch.cat(flat_after)
    relative_delta = float(
        torch.linalg.vector_norm(after_vector - before_vector)
        / max(float(torch.linalg.vector_norm(before_vector)), 1.0e-30)
    )
    action_rms_delta = float(
        torch.sqrt(
            torch.mean(
                torch.square(
                    torch.cat(deterministic_after) - torch.cat(deterministic_before)
                )
            )
        )
    )
    after_hash = _sha256_file(checkpoint_path)
    return {
        "arm": arm,
        "seed": seed,
        "critic": {
            "per_agent": per_agent,
            "mean_gradient_vector": mean_gradient_vector.tolist(),
            "mean_abs_qmin": float(np.mean(qmin_abs)),
            "directions": critic_directions,
        },
        "fresh_optimizer_fixed_state_probe": {
            "label": "fresh_optimizer_fixed_state_probe",
            "state_count_per_agent": [len(rows) for rows in states_by_agent],
            "actor_losses": losses,
            "preclip_gradient_norms": grad_norms,
            "relative_parameter_delta": relative_delta,
            "deterministic_action_rms_delta": action_rms_delta,
            "moves": bool(relative_delta >= 1.0e-7 and action_rms_delta >= 1.0e-6),
            "fixed_below_both": bool(
                relative_delta < 1.0e-7 and action_rms_delta < 1.0e-6
            ),
        },
        "checkpoint_sha256_before": before_hash,
        "checkpoint_sha256_after": after_hash,
        "checkpoint_immutable": before_hash == after_hash,
    }


def _geometry_from_trajectories(
    trajectories: Sequence[Mapping[str, Any]], reward_name: str
) -> dict[str, Any]:
    result = {}
    for direction in DIRECTIONS:
        values: dict[str, dict[float, dict[int, float]]] = {}
        for row in trajectories:
            condition_id = str(row["condition_id"])
            values.setdefault(condition_id, {})
            if row["direction"] is None:
                values[condition_id].setdefault(0.0, {})[0] = float(
                    row["returns"][reward_name]["discounted"]
                )
            elif row["direction"] == direction:
                values[condition_id].setdefault(float(row["epsilon"]), {})[
                    int(row["sign"])
                ] = float(row["returns"][reward_name]["discounted"])
        result[direction] = centered_geometry(values)
    return result


def _mechanism_tags(
    diagnostics: Sequence[Mapping[str, Any]],
    checkpoint_geometry: Mapping[str, Mapping[str, Any]],
    derivatives: Sequence[float],
) -> dict[str, Any]:
    flat_count = sum(
        not any(row["material"] for row in diag["critic"]["directions"].values())
        for diag in diagnostics
    )
    comparable = []
    for diag in diagnostics:
        key = f"{diag['arm']}|{diag['seed']}"
        geometry = checkpoint_geometry[key]
        for direction in DIRECTIONS:
            physical = geometry[direction]
            critic = diag["critic"]["directions"][direction]
            if physical["slope_stable_material"] and critic["material"]:
                comparable.append(
                    {
                        "checkpoint": key,
                        "direction": direction,
                        "physical_sign": physical["slope_sign"],
                        "critic_sign": critic["sign"],
                        "agrees": physical["slope_sign"] == critic["sign"],
                    }
                )
    agreement = (
        None
        if not comparable
        else sum(row["agrees"] for row in comparable) / len(comparable)
    )
    if flat_count >= 8:
        critic_tag = "CRITIC-FLAT"
    elif len(comparable) < 6:
        critic_tag = "CRITIC-NOT-DIAGNOSTIC"
    elif float(agreement) < 0.60:
        critic_tag = "CRITIC-MISALIGNED"
    else:
        critic_tag = "CRITIC-ALIGNED"
    moves = sum(diag["fresh_optimizer_fixed_state_probe"]["moves"] for diag in diagnostics)
    fixed = sum(
        diag["fresh_optimizer_fixed_state_probe"]["fixed_below_both"]
        for diag in diagnostics
    )
    update_tag = (
        "FRESH-UPDATE-MOVES"
        if moves >= 8
        else "FRESH-UPDATE-FIXED"
        if fixed >= 8
        else "FRESH-UPDATE-MIXED"
    )
    derivative_array = np.abs(np.asarray(derivatives, dtype=float))
    suppressed_fraction = float(np.mean(derivative_array <= 1.0e-6))
    projection_tag = (
        "PROJECTION-SUPPRESSED"
        if suppressed_fraction >= 0.95
        else "PROJECTION-NOT-SUPPRESSED"
    )
    return {
        "critic": {
            "tag": critic_tag,
            "flat_checkpoint_count": flat_count,
            "comparable_cells": comparable,
            "sign_agreement_fraction": agreement,
        },
        "fresh_update": {"tag": update_tag, "moves": moves, "fixed": fixed},
        "projection": {
            "tag": projection_tag,
            "branch_count": int(len(derivative_array)),
            "suppressed_fraction": suppressed_fraction,
            "minimum_abs_derivative": float(np.min(derivative_array)),
            "median_abs_derivative": float(np.median(derivative_array)),
            "maximum_abs_derivative": float(np.max(derivative_array)),
        },
    }


def aggregate() -> str:
    _assert_wsl_scratch()
    seal = load_seal()
    shard_payloads = [_read_hashed_json(_shard_path(value)) for value in expected_shard_ids()]
    trajectories = [
        row for payload in shard_payloads for row in payload["trajectories"]
    ]
    invalid_reasons = []
    if len(trajectories) != 825:
        invalid_reasons.append("wrong trajectory inventory")
    if any(not row["completed"] for row in trajectories):
        invalid_reasons.append("incomplete physical trajectory")
    if any(
        not step["external_projection_identity"]
        for trajectory in trajectories
        for step in trajectory["rows"]
    ):
        invalid_reasons.append("projection identity failure")
    if any(not payload["checkpoint_immutable"] for payload in shard_payloads):
        invalid_reasons.append("parent checkpoint changed during physical probes")
    anchor = [row for row in trajectories if row["arm"] is None]
    anchor_geometry = {}
    for reward_name in ("no_message", "message"):
        for direction, geometry in _geometry_from_trajectories(
            anchor, reward_name
        ).items():
            anchor_geometry[f"{reward_name}|{direction}"] = geometry
    anchor_classification = classify_anchor(anchor_geometry)
    checkpoint_geometry = {}
    diagnostics = []
    for arm in ARMS:
        for seed in SEEDS:
            rows = [
                row
                for row in trajectories
                if row["arm"] == arm and int(row["seed"]) == seed
            ]
            reward_name = "no_message" if arm == R436.NO_MESSAGE_ARM else "message"
            checkpoint_geometry[f"{arm}|{seed}"] = _geometry_from_trajectories(
                rows, reward_name
            )
            zero_rows = [row for row in rows if row["direction"] is None]
            diagnostics.append(_checkpoint_diagnostics(arm, seed, zero_rows))
    if any(not row["checkpoint_immutable"] for row in diagnostics):
        invalid_reasons.append("parent checkpoint changed during offline diagnostics")
    derivatives = [
        value
        for trajectory in trajectories
        for step in trajectory["rows"]
        for value in step["branch_derivative_pu_per_raw"]
    ]
    mechanisms = _mechanism_tags(
        diagnostics, checkpoint_geometry, derivatives
    )
    inventory_after = _checkpoint_inventory()
    sealed_inventory = {
        (row["arm"], int(row["seed"])): row["sha256"]
        for row in seal["checkpoints"]
    }
    if any(
        row["sha256"] != sealed_inventory[(row["arm"], int(row["seed"]))]
        for row in inventory_after
    ):
        invalid_reasons.append("checkpoint inventory drifted from seal")
    finite_text = json.dumps(
        {
            "anchor_geometry": anchor_geometry,
            "checkpoint_geometry": checkpoint_geometry,
            "diagnostics": diagnostics,
            "mechanisms": mechanisms,
        },
        allow_nan=False,
    )
    if not finite_text:
        invalid_reasons.append("nonfinite diagnostic")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "shard_count": len(shard_payloads),
        "trajectory_count": len(trajectories),
        "step_row_count": sum(len(row["rows"]) for row in trajectories),
        "anchor_geometry": anchor_geometry,
        "anchor_classification": (
            "CANARY-INVALID" if invalid_reasons else anchor_classification
        ),
        "checkpoint_geometry": checkpoint_geometry,
        "checkpoint_diagnostics": diagnostics,
        "mechanisms": mechanisms,
        "invalid_reasons": invalid_reasons,
        "valid": not invalid_reasons,
        "scope": "registered four-direction, three-condition local slice only",
        "fresh_update_disclaimer": (
            "fresh optimizer fixed-state diagnostic; not the original next R436 update"
        ),
    }
    digest = _write_new_json(OUT / "formal_analysis.json", payload)
    return json.dumps(
        {
            "sha256": digest,
            "valid": payload["valid"],
            "anchor_classification": payload["anchor_classification"],
            "mechanisms": mechanisms,
        },
        indent=2,
        sort_keys=True,
    )


def _capacity_job(job_id: int) -> dict[str, Any]:
    condition = CONDITIONS[job_id % len(CONDITIONS)]
    row = _run_trajectory(
        condition=condition,
        arm=None,
        seed=None,
        direction=None,
        epsilon=0.0,
        sign=0,
    )
    return {"ok": row["completed"], "steps": row["completed_steps"]}


def _meminfo() -> dict[str, int]:
    rows = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, value = line.split(":", 1)
        rows[key] = int(value.strip().split()[0]) * 1024
    return rows


def measure_capacity() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    mem = _meminfo()
    other = R436._other_research_python_processes()
    rungs, selected = [], 0
    previous_throughput: float | None = None
    accepting = True
    for workers in CAPACITY_RUNGS:
        memory_safe = (
            workers * WORKER_RSS_FLOOR_BYTES + OS_FLOOR_BYTES
            <= int(mem["MemAvailable"])
        )
        started = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_capacity_job, range(CAPACITY_TASKS)))
        wall = time.monotonic() - started
        throughput = len(rows) / max(wall, 1.0e-12)
        gain = None if previous_throughput is None else throughput / previous_throughput
        accepted = bool(
            accepting
            and memory_safe
            and all(row["ok"] and row["steps"] == 50 for row in rows)
            and (gain is None or gain >= 1.05)
        )
        if accepted:
            selected = workers
            previous_throughput = throughput
        else:
            accepting = False
        rungs.append(
            {
                "workers": workers,
                "trajectories": len(rows),
                "wall_seconds": wall,
                "throughput_trajectories_per_second": throughput,
                "marginal_gain": gain,
                "memory_safe": memory_safe,
                "all_valid": all(row["ok"] and row["steps"] == 50 for row in rows),
                "accepted": accepted,
            }
        )
    selected_row = next(row for row in rungs if row["workers"] == selected)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "authority": checks,
        "rungs": rungs,
        "tasks_per_rung": CAPACITY_TASKS,
        "selected_workers": selected,
        "worker_rss_floor_bytes": WORKER_RSS_FLOOR_BYTES,
        "os_floor_bytes": OS_FLOOR_BYTES,
        "wsl_mem_total_bytes": int(mem["MemTotal"]),
        "wsl_mem_available_bytes": int(mem["MemAvailable"]),
        "other_python_processes": other,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "whole_host_python_process_budget": selected + 1,
        "host": {
            "logical_processors": int(os.cpu_count() or 1),
            "physical_memory_bytes": int(mem["MemTotal"]),
        },
        "wsl": {"memory_available_bytes": int(mem["MemAvailable"])},
        "wsl_python_processes": selected + 1,
        "native_threads_per_process": 1,
        "empirical_anchor": {
            "all_records_valid": True,
            "concurrent_workers": selected + 1,
            "native_threads_per_worker": 1,
        },
        "estimated_formal_seconds": 825
        / max(float(selected_row["throughput_trajectories_per_second"]), 1.0e-12),
        "readiness": "RUN-READY" if selected > 0 and not other else "LOAD-CHECK-REVIEW",
    }
    digest = _write_new_json(CAPACITY, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def rehearsal() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    inventory_before = _checkpoint_inventory()
    condition = CONDITIONS[0]
    triplet = [
        _run_trajectory(
            condition=condition,
            arm=R436.MESSAGE_ARM,
            seed=401,
            direction=None if sign == 0 else "c",
            epsilon=0.0 if sign == 0 else 0.01,
            sign=sign,
        )
        for sign in (0, -1, 1)
    ]
    diagnostics = _checkpoint_diagnostics(
        R436.MESSAGE_ARM, 401, [triplet[0]]
    )
    inventory_after = _checkpoint_inventory()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_authority": False,
        "training_executed": False,
        "authority": checks,
        "runtime": installed_runtime(),
        "basis_max_gram_error": _basis_error(),
        "triplet_completed": [row["completed"] for row in triplet],
        "triplet_steps": [row["completed_steps"] for row in triplet],
        "triplet_projection_identity": all(
            step["external_projection_identity"]
            for row in triplet
            for step in row["rows"]
        ),
        "critic_finite": bool(
            np.all(
                np.isfinite(diagnostics["critic"]["mean_gradient_vector"])
            )
        ),
        "update_finite": bool(
            np.isfinite(
                diagnostics["fresh_optimizer_fixed_state_probe"][
                    "relative_parameter_delta"
                ]
            )
            and np.isfinite(
                diagnostics["fresh_optimizer_fixed_state_probe"][
                    "deterministic_action_rms_delta"
                ]
            )
        ),
        "checkpoint_immutable": inventory_before == inventory_after
        and diagnostics["checkpoint_immutable"],
        "diagnostic": diagnostics,
    }
    payload["passed"] = bool(
        all(checks.values())
        and payload["basis_max_gram_error"] <= 1.0e-12
        and all(payload["triplet_completed"])
        and payload["triplet_steps"] == [50, 50, 50]
        and payload["triplet_projection_identity"]
        and payload["critic_finite"]
        and payload["update_finite"]
        and payload["checkpoint_immutable"]
    )
    digest = _write_new_json(REHEARSAL, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def prepare() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity not RUN-READY: {capacity.get('readiness')}")
    selected = int(capacity["selected_workers"])
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r454_m4_residual_local_audit.py",
        "r436_runner": ROOT / "scripts/run_r436_energy_residual_sac.py",
        "sac": ROOT / "src/andes_rl_kundur/agents/sac.py",
        "sac_base": ROOT / "src/andes_rl_kundur/agents/sac_base.py",
        "action_map": ROOT
        / "src/andes_rl_kundur/control/feasibility_native_vsg_action.py",
        "environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "energy_port": ROOT
        / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "capacity_sha256": _sha256_file(CAPACITY),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "authority": checks,
        "runtime": rehearsal_payload["runtime"],
        "launch": {
            "host_process_budget": selected + 1,
            "wsl_python_processes": selected + 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "execution_shards": len(expected_shard_ids()),
        },
        "sources": {
            name: {"path": _relative(path), "sha256": _sha256_file(path)}
            for name, path in sources.items()
        },
        "checkpoints": _checkpoint_inventory(),
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    SHARDS.parent.mkdir(parents=True, exist_ok=True)
    SHARDS.write_text(json.dumps(expected_shard_ids()) + "\n", encoding="utf-8")
    return json.dumps(
        {
            "seal_sha256": digest,
            "selected_workers": selected,
            "execution_shards": len(expected_shard_ids()),
        },
        indent=2,
        sort_keys=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("capacity", "rehearse", "prepare", "seal", "shards", "shard", "aggregate"),
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "capacity":
        print(measure_capacity(), flush=True)
    elif args.command == "rehearse":
        print(rehearsal(), flush=True)
    elif args.command in ("prepare", "seal"):
        print(prepare(), flush=True)
    elif args.command == "shards":
        print(json.dumps(expected_shard_ids()), flush=True)
    elif args.command == "aggregate":
        print(aggregate(), flush=True)
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        print(run_shard(args.shard_id, resume=args.resume), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
