"""R292 vector-residual execution, physical endpoints, and action audits."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import numpy as np

from andes_rl_kundur.control.vector_inertia_residual import (
    r292_vector_residual_contract,
)
from andes_rl_kundur.env.andes.distributed_residual_env import (
    DistributedVectorResidualEnv,
)
from andes_rl_kundur.evaluation.fast_md_authority import (
    summarise_fast_md_trace,
)
from andes_rl_kundur.evaluation.topology_status import (
    r304_topology_label_matches_opened_line,
)


class VectorResidualController(Protocol):
    def select_edge_actions(
        self,
        observations: Mapping[int, np.ndarray],
        *,
        deterministic: bool = True,
    ) -> np.ndarray: ...


class ZeroVectorController:
    """Deterministic q0 comparator in the frozen three-edge action space."""

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
            raise ValueError("q0 is deterministic")
        return np.zeros(3, dtype=np.float32)


def attach_vector_inertia_execution_contract(
    record: Mapping[str, Any],
    *,
    execution_metadata: Mapping[str, Any],
    guards: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach the complete root contract consumed by EVAL-v2 vector_inertia."""
    required_text = (
        "round",
        "question",
        "experiment",
        "seal_sha256",
        "topology_inventory_sha256",
        "topology",
        "opened_line",
        "location",
        "sign",
        "severity",
    )
    missing = [
        key
        for key in required_text
        if not isinstance(execution_metadata.get(key), str)
        or not str(execution_metadata[key]).strip()
    ]
    if missing:
        raise ValueError(f"missing vector-inertia execution metadata: {missing}")
    if not r304_topology_label_matches_opened_line(
        execution_metadata["topology"],
        execution_metadata["opened_line"],
    ):
        raise ValueError("topology label/opened-line mapping mismatch")
    topology_status = execution_metadata.get("topology_status")
    if not isinstance(topology_status, Mapping):
        raise ValueError("topology_status must be a mapping")
    if topology_status.get("topology") != execution_metadata["topology"]:
        raise ValueError("topology_status topology mismatch")
    if topology_status.get("opened_line") != execution_metadata["opened_line"]:
        raise ValueError("topology_status opened-line mismatch")
    if not isinstance(guards, Mapping):
        raise ValueError("run guards must be a mapping")
    config = record.get("controller_config")
    if not isinstance(config, Mapping) or not isinstance(
        config.get("architecture"),
        str,
    ):
        raise ValueError("vector-inertia records require a declared architecture")

    output = dict(record)
    output.update(
        {
            key: execution_metadata[key]
            for key in required_text
        }
    )
    output["topology_status"] = dict(topology_status)
    output["guards"] = dict(guards)
    output["controller_config"] = {
        **dict(config),
        "vector_inertia": r292_vector_residual_contract().telemetry(),
    }
    return output


def _trace_row(step: int, info: Mapping[str, Any], nominal_hz: float) -> dict[str, Any]:
    frequency = np.asarray(info["freq_hz_physical"], dtype=float)
    return {
        "step": step,
        "t": float(info["time"]),
        "freq_hz_physical": frequency.tolist(),
        "delta_f_physical_hz": (frequency - nominal_hz).tolist(),
        "action_norm": np.asarray(
            info["r292_executed_md_action_norm"], dtype=float
        ).tolist(),
        "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
        "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
        "r292_raw_edge_action": np.asarray(
            info["r292_raw_edge_action"], dtype=float
        ).tolist(),
        "r292_edge_flow_norm": np.asarray(
            info["r292_edge_flow_norm"], dtype=float
        ).tolist(),
        "r292_node_residual_norm": np.asarray(
            info["r292_node_residual_norm"], dtype=float
        ).tolist(),
        "r292_physical_m_residual": np.asarray(
            info["r292_physical_m_residual"], dtype=float
        ).tolist(),
        "r292_physical_m_residual_sum": float(
            info["r292_physical_m_residual_sum"]
        ),
        "vsg_common_m_model_units": np.asarray(
            info["vsg_common_m_model_units"], dtype=float
        ).tolist(),
        "vsg_requested_m_model_units": np.asarray(
            info["vsg_requested_m_model_units"], dtype=float
        ).tolist(),
        "vsg_commanded_m_model_units": np.asarray(
            info["vsg_commanded_m_model_units"], dtype=float
        ).tolist(),
        "vsg_actual_m_model_units": np.asarray(
            info["vsg_actual_m_model_units"], dtype=float
        ).tolist(),
        "vsg_actual_d_model_units": np.asarray(
            info["vsg_actual_d_model_units"], dtype=float
        ).tolist(),
        "bess_requested_power_system_pu": np.asarray(
            info["bess_requested_power_system_pu"], dtype=float
        ).tolist(),
        "bess_commanded_power_system_pu": np.asarray(
            info["bess_commanded_power_system_pu"], dtype=float
        ).tolist(),
        "bess_actual_power_system_pu": np.asarray(
            info["bess_actual_power_system_pu"], dtype=float
        ).tolist(),
        "bess_soc": np.asarray(info["bess_soc"], dtype=float).tolist(),
        "bess_bus_voltage_pu": np.asarray(
            info["bess_bus_voltage_pu"], dtype=float
        ).tolist(),
        "bess_saturation_reasons": info["bess_saturation_reasons"],
        "bess_charge_energy_mwh_total": np.asarray(
            info["bess_charge_energy_mwh_total"], dtype=float
        ).tolist(),
        "bess_discharge_energy_mwh_total": np.asarray(
            info["bess_discharge_energy_mwh_total"], dtype=float
        ).tolist(),
        "bess_constraint_violations": info["bess_constraint_violations"],
    }


def run_vector_controller_scenario(
    controller: VectorResidualController,
    *,
    controller_name: str,
    controller_config: Mapping[str, Any],
    scenario_name: str,
    delta_u: Mapping[str, float],
    seed: int,
    steps: int,
    phase: str,
    evidence_hashes: Mapping[str, str],
    execution_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one deterministic controller on nominal or declared-outage V4."""
    if steps < 2:
        raise ValueError("vector-residual trajectories require at least two steps")
    if execution_metadata is not None:
        attach_vector_inertia_execution_contract(
            {"controller_config": dict(controller_config)},
            execution_metadata=execution_metadata,
            guards={},
        )
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    if execution_metadata is None:
        base_env = AndesMultiVSGEnvV4Storage(
            random_disturbance=False,
            comm_fail_prob=0.0,
        )
    else:
        from andes_rl_kundur.evaluation.topology_status import apply_line_outage

        opened_line = str(execution_metadata.get("opened_line", ""))
        if not opened_line:
            raise ValueError("execution_metadata.opened_line is required")

        class _TopologyConditionedStorageEnv(AndesMultiVSGEnvV4Storage):
            def _build_system(self):
                system = super()._build_system()
                if hasattr(system, "Toggler") and system.Toggler.n > 0:
                    for toggler_idx in list(system.Toggler.idx.v):
                        system.Toggler.set("u", toggler_idx, 0.0, attr="v")
                if opened_line != "none":
                    apply_line_outage(system, opened_line)
                return system

        base_env = _TopologyConditionedStorageEnv(
            random_disturbance=False,
            comm_fail_prob=0.0,
        )
    env = DistributedVectorResidualEnv(base_env)
    reset = getattr(controller, "reset", None)
    if callable(reset):
        reset()
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_hz = 60.0
    runtime_guards: dict[str, Any] | None = None
    bound_execution_metadata: dict[str, Any] | None = None
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        observation = env.reset(delta_u=dict(delta_u))
        nominal_hz = float(env.base_env.andes_nominal_frequency_hz)
        if execution_metadata is not None:
            opened_line = str(execution_metadata["opened_line"])
            line_status = {
                str(idx): float(value)
                for idx, value in zip(
                    env.base_env.ss.Line.idx.v,
                    env.base_env.ss.Line.u.v,
                    strict=True,
                )
            }
            controlled_lines = ("Line_0", "Line_9")
            expected_opened = set() if opened_line == "none" else {opened_line}
            opened_line_pass = bool(
                opened_line == "none" or opened_line in controlled_lines
            ) and all(
                line_idx in line_status
                and line_status[line_idx]
                == (0.0 if line_idx in expected_opened else 1.0)
                for line_idx in controlled_lines
            )
            toggler_disabled = bool(
                not hasattr(env.base_env.ss, "Toggler")
                or env.base_env.ss.Toggler.n == 0
                or all(float(value) == 0.0 for value in env.base_env.ss.Toggler.u.v)
            )
            declared_status = execution_metadata.get("topology_status")
            if not isinstance(declared_status, Mapping):
                raise ValueError("execution_metadata.topology_status is required")
            runtime_status = {
                **dict(declared_status),
                "opened_line_pass": opened_line_pass,
                "runtime_line_status": line_status,
                "default_toggler_disabled": toggler_disabled,
                "passed": bool(
                    declared_status.get("passed") is True
                    and opened_line_pass
                    and toggler_disabled
                ),
            }
            bound_execution_metadata = {
                **dict(execution_metadata),
                "topology_status": runtime_status,
            }
        for step in range(steps):
            raw = np.asarray(
                controller.select_edge_actions(
                    observation,
                    deterministic=True,
                ),
                dtype=np.float32,
            )
            observation, _rewards, done, info = env.step(raw)
            if info.get("tds_failed"):
                tds_failed = True
                break
            traces.append(_trace_row(step, info, nominal_hz))
            if done:
                break
        system = env.base_env.ss
        runtime_guards = {
            "completed": not tds_failed and len(traces) == steps,
            "tds_test_ok": system.TDS.test_ok is True,
            "system_exit_code": int(system.exit_code),
            "finite_telemetry": bool(
                traces
                and all(
                    np.all(np.isfinite(np.asarray(row[field], dtype=float)))
                    for row in traces
                    for field in (
                        "freq_hz_physical",
                        "vsg_requested_m_model_units",
                        "vsg_commanded_m_model_units",
                        "vsg_actual_m_model_units",
                        "vsg_actual_d_model_units",
                    )
                )
            ),
        }
    finally:
        env.close()
    record = {
        "schema_version": 1,
        "round": "R292",
        "question": "Q-0049",
        "experiment": "r292_true_distributed_vector_comparison",
        "phase": phase,
        "controller": controller_name,
        "scenario": scenario_name,
        "delta_u": dict(delta_u),
        "env_version": "v4_plus_independent_esd1",
        "control_nominal_frequency_hz": float(env.base_env.FN),
        "andes_nominal_frequency_hz": nominal_hz,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": steps,
        "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": not tds_failed and len(traces) == steps,
        "traces": traces,
        "controller_config": {
            **dict(controller_config),
            "vector_residual": r292_vector_residual_contract().telemetry(),
        },
        "evidence_hashes": dict(evidence_hashes),
        "seed": seed,
    }
    if execution_metadata is None:
        return record
    if runtime_guards is None:
        raise RuntimeError("vector-inertia run guards were not captured")
    if bound_execution_metadata is None:
        raise RuntimeError("vector-inertia topology metadata was not runtime-bound")
    return attach_vector_inertia_execution_contract(
        record,
        execution_metadata=bound_execution_metadata,
        guards=runtime_guards,
    )


def summarise_vector_trace(
    record: dict[str, Any],
    *,
    final_window_steps: int = 50,
    fast_window_steps: int = 15,
) -> dict[str, Any]:
    summary = summarise_fast_md_trace(
        record,
        final_window_steps=final_window_steps,
        fast_window_steps=fast_window_steps,
    )
    traces = record["traces"]
    edge = np.asarray(
        [row["r292_edge_flow_norm"] for row in traces], dtype=float
    )
    node = np.asarray(
        [row["r292_node_residual_norm"] for row in traces], dtype=float
    )
    physical_sum = np.asarray(
        [row["r292_physical_m_residual_sum"] for row in traces], dtype=float
    )
    edge_delta = np.diff(
        np.concatenate([np.zeros((1, 3), dtype=float), edge], axis=0),
        axis=0,
    )
    node_delta = np.diff(
        np.concatenate([np.zeros((1, 4), dtype=float), node], axis=0),
        axis=0,
    )
    summary.update(
        {
            "r292_max_abs_edge": float(np.max(np.abs(edge))),
            "r292_max_abs_edge_slew": float(np.max(np.abs(edge_delta))),
            "r292_edge_total_variation": float(np.sum(np.abs(edge_delta))),
            "r292_max_abs_node_residual": float(np.max(np.abs(node))),
            "r292_max_abs_node_slew": float(np.max(np.abs(node_delta))),
            "r292_max_abs_node_residual_sum": float(
                np.max(np.abs(np.sum(node, axis=1)))
            ),
            "r292_max_abs_physical_m_residual_sum": float(
                np.max(np.abs(physical_sum))
            ),
            "r292_post_window_max_abs_edge": float(
                np.max(np.abs(edge[fast_window_steps:]))
                if len(edge) > fast_window_steps
                else 0.0
            ),
        }
    )
    return summary


def _float32_tolerance(limit: float) -> float:
    return float(np.spacing(np.float32(limit)))


def audit_vector_action(summary: Mapping[str, Any]) -> dict[str, bool]:
    contract = r292_vector_residual_contract()
    physical_tolerance = float(
        contract.agent_count
        * np.spacing(
            np.float32(
                contract.baseline_m
                + contract.dm_max
                * (contract.common_amplitude + contract.node_residual_max)
            )
        )
    )
    return {
        "edge_magnitude": bool(
            float(summary["r292_max_abs_edge"])
            <= contract.edge_flow_max + _float32_tolerance(contract.edge_flow_max)
        ),
        "edge_slew": bool(
            float(summary["r292_max_abs_edge_slew"])
            <= contract.edge_slew_max + _float32_tolerance(contract.edge_slew_max)
        ),
        "node_magnitude": bool(
            float(summary["r292_max_abs_node_residual"])
            <= contract.node_residual_max
            + _float32_tolerance(contract.node_residual_max)
        ),
        "node_slew": bool(
            float(summary["r292_max_abs_node_slew"])
            <= contract.node_slew_max + _float32_tolerance(contract.node_slew_max)
        ),
        "normalized_zero_sum": bool(
            float(summary["r292_max_abs_node_residual_sum"]) <= 1e-7
        ),
        "physical_zero_sum": bool(
            float(summary["r292_max_abs_physical_m_residual_sum"])
            <= physical_tolerance
        ),
        "post_window_zero": bool(
            float(summary["r292_post_window_max_abs_edge"]) <= 1e-9
        ),
        "d_action_zero": bool(float(summary["max_abs_d_action_norm"]) <= 1e-9),
        "m_action_range": bool(
            float(summary["max_abs_m_action_norm"]) <= 0.5 + 1e-9
            and float(summary["min_m"]) >= 200.0 - 1e-8
            and float(summary["max_m"]) <= 500.0 + 1e-8
        ),
    }
