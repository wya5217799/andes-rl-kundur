"""Run R303's deterministic heterogeneous-headroom projection probe.

Usage:
    python probes/r303_projection_coupling.py
    python probes/r303_projection_coupling.py --output tmp/r303.json

The probe executes no ANDES trajectory and reads no performance endpoint.  It
compares three action-geometry arms on one prospectively frozen matrix:
independent device projection, a two-phase neighbour-edge allocator, and a
centralized zero-sum box-projection oracle.  Failure is fail-closed and neural
training is never authorized inside R303.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract  # noqa: E402
from andes_rl_kundur.control.edge_relative_rocof_residual import (  # noqa: E402
    LocalEdgeRoCoFChannel,
)
from andes_rl_kundur.control.headroom_aware_edge_allocation import (  # noqa: E402
    allocate_edge_flows_with_headroom,
    project_residual_to_zero_sum_box,
)

DEFAULT_OUTPUT = ROOT / "results/r303_projection_coupling/analysis_summary.json"
ROUND = "R303"
QUESTION = "Q-0060"
DEVICE_COUNT = 4
FIXED_2KV_GAIN = 0.4884814
GRAPH_DEGREE = 2
DT_SECONDS = 0.2
EDGES = ((0, 1), (1, 2), (2, 3), (0, 3))
EDGE_PHASES = (((0, 1), (2, 3)), ((1, 2), (0, 3)))
COMMON_REQUESTS = (0.04, -0.04)
ROCOF_TEMPLATES = {
    "interarea_pos": (0.08, 0.08, -0.08, -0.08),
    "interarea_neg": (-0.08, -0.08, 0.08, 0.08),
    "node0_outlier": (0.12, -0.04, -0.04, -0.04),
    "alternating": (0.08, -0.08, 0.08, -0.08),
}
HEADROOM_TEMPLATES = {
    "homogeneous_mid": {
        "previous_power_system_pu": (0.0, 0.0, 0.0, 0.0),
        "soc": (0.5, 0.5, 0.5, 0.5),
    },
    "soc_split": {
        "previous_power_system_pu": (0.0, 0.0, 0.0, 0.0),
        "soc": (0.2, 0.8, 0.5, 0.5),
    },
    "ramp_split": {
        "previous_power_system_pu": (0.34, -0.34, 0.0, 0.0),
        "soc": (0.5, 0.5, 0.5, 0.5),
    },
    "mixed_soc_ramp": {
        "previous_power_system_pu": (0.34, -0.34, 0.06, -0.06),
        "soc": (0.21, 0.79, 0.5, 0.5),
    },
}
ZERO_TOLERANCE = 1e-12
MATERIAL_ABS_LEAKAGE_SYSTEM_PU = 0.01
MATERIAL_RELATIVE_LEAKAGE = 0.10
MIN_MATERIAL_CASE_COUNT = 2
MIN_MEDIAN_RETAINED_FRACTION = 0.50
MAX_LOCAL_OVER_ORACLE_ERROR = 1.25


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _edge_flows(filtered_rocof_hz_s: tuple[float, ...]) -> dict[tuple[int, int], float]:
    values = np.asarray(filtered_rocof_hz_s, dtype=float)
    return {
        edge: LocalEdgeRoCoFChannel(
            edge=edge,
            gain_system_pu_s_per_hz=FIXED_2KV_GAIN,
            graph_degree=GRAPH_DEGREE,
        ).flow_system_pu(values)
        for edge in EDGES
    }


def _residual_from_edge_flows(
    edge_flows: dict[tuple[int, int], float],
) -> np.ndarray:
    residual = np.zeros(DEVICE_COUNT, dtype=float)
    for (source, target), flow in edge_flows.items():
        residual[source] += flow
        residual[target] -= flow
    return residual


def _retained_fraction(executed: np.ndarray, target: np.ndarray) -> float:
    denominator = float(np.linalg.norm(target))
    return float(np.linalg.norm(executed) / denominator) if denominator else 1.0


def _zero_sum_box_kkt_residual(
    *,
    target: np.ndarray,
    projected: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    active_tolerance: float = 1e-9,
) -> float:
    at_lower = projected <= lower + active_tolerance
    at_upper = projected >= upper - active_tolerance
    free = ~(at_lower | at_upper)
    stationarity = target - projected
    lower_lambda = (
        float(np.max(stationarity[at_lower])) if np.any(at_lower) else -math.inf
    )
    upper_lambda = (
        float(np.min(stationarity[at_upper])) if np.any(at_upper) else math.inf
    )
    if np.any(free):
        multiplier = float(np.mean(stationarity[free]))
        free_residual = float(np.max(np.abs(stationarity[free] - multiplier)))
    else:
        multiplier = 0.5 * (lower_lambda + upper_lambda)
        free_residual = 0.0
    lower_violation = max(lower_lambda - multiplier, 0.0)
    upper_violation = max(multiplier - upper_lambda, 0.0)
    return max(free_residual, lower_violation, upper_violation)


def classify_projection_probe(
    *,
    guards_pass: bool,
    mechanism_case_count: int,
    material_case_count: int,
    local_valid: bool,
    local_sufficient: bool,
) -> str:
    """Apply the prospective R303 decision tree without reading endpoints."""

    if not guards_pass:
        return "INVALID-PROJECTION-PROBE"
    if mechanism_case_count == 0:
        return "PROJECTION-SEAM-PRESERVED"
    if material_case_count < MIN_MATERIAL_CASE_COUNT:
        return "PROJECTION-LEAKAGE-IMMATERIAL"
    if not local_valid:
        return "COORDINATE-REPAIR-FAILED"
    if local_sufficient:
        return "COUPLING-CLASSICALLY-CLOSED"
    return "LOCAL-CLASSICAL-GAP"


def _case(
    *,
    common_request: float,
    rocof_name: str,
    rocof: tuple[float, ...],
    headroom_name: str,
    headroom: dict[str, tuple[float, ...]],
) -> dict[str, Any]:
    contract = r272_frozen_bess_contract()
    previous = np.asarray(headroom["previous_power_system_pu"], dtype=float)
    soc = np.asarray(headroom["soc"], dtype=float)
    voltage = np.ones(DEVICE_COUNT, dtype=float)
    common_requested = np.full(DEVICE_COUNT, common_request, dtype=float)
    projection_inputs = {
        "previous_power_system_pu": previous,
        "soc": soc,
        "voltage_pu": voltage,
        "dt_seconds": DT_SECONDS,
    }
    baseline = contract.project_power(
        requested_power_system_pu=common_requested,
        **projection_inputs,
    ).commanded_power_system_pu
    lower, upper = contract.feasible_power_bounds(**projection_inputs)
    edge_flows = _edge_flows(rocof)
    target_residual = _residual_from_edge_flows(edge_flows)

    independent_command = contract.project_power(
        requested_power_system_pu=common_requested + target_residual,
        **projection_inputs,
    ).commanded_power_system_pu
    independent_residual = independent_command - baseline

    local = allocate_edge_flows_with_headroom(
        base_power_system_pu=baseline,
        requested_edge_flows_system_pu=edge_flows,
        edge_phases=EDGE_PHASES,
        lower_power_system_pu=lower,
        upper_power_system_pu=upper,
    )
    local_reprojected = contract.project_power(
        requested_power_system_pu=local.commanded_power_system_pu,
        **projection_inputs,
    ).commanded_power_system_pu

    residual_lower = lower - baseline
    residual_upper = upper - baseline
    oracle_residual = project_residual_to_zero_sum_box(
        target_residual_system_pu=target_residual,
        lower_residual_system_pu=residual_lower,
        upper_residual_system_pu=residual_upper,
    )
    oracle_command = baseline + oracle_residual
    oracle_reprojected = contract.project_power(
        requested_power_system_pu=oracle_command,
        **projection_inputs,
    ).commanded_power_system_pu

    independent_leakage = float(np.sum(independent_residual))
    half_l1_target = 0.5 * float(np.sum(np.abs(target_residual)))
    relative_leakage = (
        abs(independent_leakage) / half_l1_target if half_l1_target else 0.0
    )
    local_target_error = float(np.linalg.norm(local.residual_power_system_pu - target_residual))
    oracle_target_error = float(np.linalg.norm(oracle_residual - target_residual))
    local_valid = bool(
        abs(float(np.sum(local.residual_power_system_pu))) <= ZERO_TOLERANCE
        and np.all(local.commanded_power_system_pu >= lower - ZERO_TOLERANCE)
        and np.all(local.commanded_power_system_pu <= upper + ZERO_TOLERANCE)
        and np.max(np.abs(local_reprojected - local.commanded_power_system_pu))
        <= ZERO_TOLERANCE
    )
    oracle_kkt_residual = _zero_sum_box_kkt_residual(
        target=target_residual,
        projected=oracle_residual,
        lower=residual_lower,
        upper=residual_upper,
    )
    oracle_valid = bool(
        abs(float(np.sum(oracle_residual))) <= ZERO_TOLERANCE
        and np.all(oracle_command >= lower - ZERO_TOLERANCE)
        and np.all(oracle_command <= upper + ZERO_TOLERANCE)
        and np.max(np.abs(oracle_reprojected - oracle_command)) <= ZERO_TOLERANCE
        and oracle_kkt_residual <= 1e-9
    )
    material = bool(
        headroom_name != "homogeneous_mid"
        and abs(independent_leakage) >= MATERIAL_ABS_LEAKAGE_SYSTEM_PU
        and relative_leakage >= MATERIAL_RELATIVE_LEAKAGE
    )
    return {
        "case_id": f"c{common_request:+.2f}__{rocof_name}__{headroom_name}",
        "common_request_system_pu_per_device": common_request,
        "rocof_template": rocof_name,
        "headroom_template": headroom_name,
        "heterogeneous_headroom": headroom_name != "homogeneous_mid",
        "requested_edge_flows_system_pu": {
            f"{source}-{target}": flow
            for (source, target), flow in edge_flows.items()
        },
        "requested_residual_system_pu": target_residual.tolist(),
        "requested_residual_sum_system_pu": float(np.sum(target_residual)),
        "baseline_command_system_pu": baseline.tolist(),
        "feasible_lower_system_pu": lower.tolist(),
        "feasible_upper_system_pu": upper.tolist(),
        "independent_projection": {
            "command_system_pu": independent_command.tolist(),
            "common_leakage_system_pu": independent_leakage,
            "relative_leakage_over_half_l1": relative_leakage,
            "retained_fraction": _retained_fraction(independent_residual, target_residual),
            "target_error_l2_system_pu": float(
                np.linalg.norm(independent_residual - target_residual)
            ),
        },
        "local_edge_allocator": {
            "command_system_pu": local.commanded_power_system_pu.tolist(),
            "allocated_edge_flows_system_pu": {
                f"{source}-{target}": flow
                for (source, target), flow in local.allocated_edge_flows_system_pu.items()
            },
            "common_leakage_system_pu": float(
                np.sum(local.residual_power_system_pu)
            ),
            "retained_fraction": _retained_fraction(
                local.residual_power_system_pu,
                target_residual,
            ),
            "target_error_l2_system_pu": local_target_error,
            "valid": local_valid,
        },
        "central_zero_sum_oracle": {
            "command_system_pu": oracle_command.tolist(),
            "common_leakage_system_pu": float(np.sum(oracle_residual)),
            "retained_fraction": _retained_fraction(oracle_residual, target_residual),
            "target_error_l2_system_pu": oracle_target_error,
            "kkt_residual": oracle_kkt_residual,
            "valid": oracle_valid,
        },
        "material_leakage": material,
        "local_over_oracle_error_gate": bool(
            local_target_error
            <= MAX_LOCAL_OVER_ORACLE_ERROR * oracle_target_error + ZERO_TOLERANCE
        ),
    }


def analyze_projection_coupling() -> dict[str, Any]:
    """Execute the frozen 32-case matrix and return its fail-closed decision."""

    cases = [
        _case(
            common_request=common_request,
            rocof_name=rocof_name,
            rocof=rocof,
            headroom_name=headroom_name,
            headroom=headroom,
        )
        for common_request in COMMON_REQUESTS
        for rocof_name, rocof in ROCOF_TEMPLATES.items()
        for headroom_name, headroom in HEADROOM_TEMPLATES.items()
    ]
    heterogeneous = [case for case in cases if case["heterogeneous_headroom"]]
    mechanism_cases = [
        case
        for case in heterogeneous
        if abs(case["independent_projection"]["common_leakage_system_pu"])
        > ZERO_TOLERANCE
    ]
    material_cases = [case for case in heterogeneous if case["material_leakage"]]
    local_valid = all(case["local_edge_allocator"]["valid"] for case in cases)
    oracle_valid = all(case["central_zero_sum_oracle"]["valid"] for case in cases)
    request_zero_sum = max(
        abs(case["requested_residual_sum_system_pu"]) for case in cases
    )
    local_zero_sum = max(
        abs(case["local_edge_allocator"]["common_leakage_system_pu"])
        for case in cases
    )
    oracle_zero_sum = max(
        abs(case["central_zero_sum_oracle"]["common_leakage_system_pu"])
        for case in cases
    )
    oracle_kkt = max(
        case["central_zero_sum_oracle"]["kkt_residual"] for case in cases
    )
    retained_material = [
        case["local_edge_allocator"]["retained_fraction"] for case in material_cases
    ]
    median_retained = (
        float(np.median(retained_material)) if retained_material else 1.0
    )
    material_error_gate = all(
        case["local_over_oracle_error_gate"] for case in material_cases
    )
    local_sufficient = bool(
        local_valid
        and median_retained >= MIN_MEDIAN_RETAINED_FRACTION
        and material_error_gate
    )
    core_guards_pass = bool(
        request_zero_sum <= ZERO_TOLERANCE
        and oracle_zero_sum <= ZERO_TOLERANCE
        and oracle_valid
        and oracle_kkt <= 1e-9
    )
    classification = classify_projection_probe(
        guards_pass=core_guards_pass,
        mechanism_case_count=len(mechanism_cases),
        material_case_count=len(material_cases),
        local_valid=local_valid,
        local_sufficient=local_sufficient,
    )
    if classification == "LOCAL-CLASSICAL-GAP":
        next_step = (
            "Freeze a stronger distributed optimization comparator and neural-smoke "
            "contract in a later round; do not train from R303."
        )
    elif classification == "COORDINATE-REPAIR-FAILED":
        next_step = "Repair the deterministic coordinate-preserving allocator; training remains blocked."
    else:
        next_step = "No neural training; retain or close the deterministic mechanism at this gate."
    return {
        "schema_version": 1,
        "round": ROUND,
        "question": QUESTION,
        "classification": classification,
        "case_count": len(cases),
        "frozen_contract": {
            "fixed_2kv_gain_system_pu_s_per_hz": FIXED_2KV_GAIN,
            "graph_degree": GRAPH_DEGREE,
            "edges": [list(edge) for edge in EDGES],
            "edge_phases": [[list(edge) for edge in phase] for phase in EDGE_PHASES],
            "common_requests_system_pu_per_device": list(COMMON_REQUESTS),
            "rocof_templates_hz_s": ROCOF_TEMPLATES,
            "headroom_templates": HEADROOM_TEMPLATES,
            "dt_seconds": DT_SECONDS,
        },
        "thresholds": {
            "zero_tolerance": ZERO_TOLERANCE,
            "material_abs_leakage_system_pu": MATERIAL_ABS_LEAKAGE_SYSTEM_PU,
            "material_relative_leakage": MATERIAL_RELATIVE_LEAKAGE,
            "minimum_material_case_count": MIN_MATERIAL_CASE_COUNT,
            "minimum_median_retained_fraction": MIN_MEDIAN_RETAINED_FRACTION,
            "maximum_local_over_oracle_error": MAX_LOCAL_OVER_ORACLE_ERROR,
        },
        "aggregate": {
            "heterogeneous_case_count": len(heterogeneous),
            "mechanism_case_count": len(mechanism_cases),
            "material_case_count": len(material_cases),
            "max_independent_common_leakage_abs_system_pu": max(
                abs(case["independent_projection"]["common_leakage_system_pu"])
                for case in heterogeneous
            ),
            "max_independent_relative_leakage": max(
                case["independent_projection"]["relative_leakage_over_half_l1"]
                for case in heterogeneous
            ),
            "median_local_retained_fraction_on_material_cases": median_retained,
            "material_local_oracle_error_gate_all_pass": material_error_gate,
            "local_sufficient": local_sufficient,
        },
        "guards": {
            "requested_zero_sum_max_abs_system_pu": request_zero_sum,
            "local_zero_sum_max_abs_system_pu": local_zero_sum,
            "oracle_zero_sum_max_abs_system_pu": oracle_zero_sum,
            "oracle_kkt_residual_max": oracle_kkt,
            "local_all_valid": local_valid,
            "oracle_all_valid": oracle_valid,
            "core_all_pass": core_guards_pass,
            "all_pass": core_guards_pass,
        },
        "training_gate": {
            "authorized": False,
            "training_executed": False,
            "reason": (
                "R303 is a deterministic coordinate-coupling gate. Even a local "
                "classical gap requires a separately frozen comparator, action, "
                "information, and kill-gate round before one neural smoke."
            ),
            "next_step": next_step,
        },
        "eval_gate": {
            "status": "NOT-APPLICABLE-NO-TRACE",
            "reason": "The algebraic probe emits no ANDES trajectory; synthetic EVAL-v2 input is prohibited.",
            "future_requirement": (
                "Any compatible ANDES run must pass the R302 vector_power profile "
                "with EXTERNAL_AUTHORITY_REQUIRED retained."
            ),
        },
        "title_alignment": {
            "conference_title": (
                "Decoupling-Oriented Coordination of Paralleled VSGs With "
                "Multi-Agent Reinforcement Learning"
            ),
            "supports_decoupling_oriented_term": bool(
                core_guards_pass and local_valid
            ),
            "supports_marl_term": False,
            "actuator_matches_vsg_term": False,
            "reason": (
                "R303 audits a classical controller-interface coordinate seam on "
                "co-located GFL ESD1 active-power commands; it neither trains MARL "
                "nor actuates VSG M/D or an independent VSG P_ref."
            ),
            "eligible_for_current_icems_evidence": False,
        },
        "claim_boundary": (
            "One four-device regular communication ring and one componentwise BESS "
            "projection contract; no hard plant decoupling, MARL/neural value, pure "
            "architecture, topology generalization, stability, safety, or deployment claim."
        ),
        "sources": {
            "plan": {
                "path": "memory/rounds/R303/plan.md",
                "sha256": _sha256(ROOT / "memory/rounds/R303/plan.md"),
            },
            "allocator": {
                "path": "src/andes_rl_kundur/control/headroom_aware_edge_allocation.py",
                "sha256": _sha256(
                    ROOT
                    / "src/andes_rl_kundur/control/headroom_aware_edge_allocation.py"
                ),
            },
            "bess_contract": {
                "path": "src/andes_rl_kundur/control/active_power.py",
                "sha256": _sha256(ROOT / "src/andes_rl_kundur/control/active_power.py"),
            },
        },
        "cases": cases,
    }


def _write_json_with_sidecar(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(
            f"refusing to overwrite result or sidecar: {path}, {sidecar}"
        )
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as stream:
        stream.write(data)
    try:
        with sidecar.open("x", encoding="ascii", newline="\n") as stream:
            stream.write(f"{digest}  {path.name}\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    summary = analyze_projection_coupling()
    digest = _write_json_with_sidecar(args.output, summary)
    print(
        json.dumps(
            {
                "classification": summary["classification"],
                "training_authorized": summary["training_gate"]["authorized"],
                "output": str(args.output.resolve()),
                "sha256": digest,
            },
            indent=2,
        )
    )
    return 0 if summary["guards"]["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
