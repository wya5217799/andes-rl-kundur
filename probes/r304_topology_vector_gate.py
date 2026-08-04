"""Pure R304 static topology-information gate for zero-sum VSG inertia.

This module has no ANDES dependency.  It validates a prospectively frozen
three-topology by seven-action eigenvalue matrix, tracks one inter-area branch,
and applies the fail-closed training decision.  Static oracle headroom is an
information-value upper bound, not a deployable centralized controller result.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.topology_status import (  # noqa: E402
    R304_TOPOLOGY_OPENED_LINE,
)

TOPOLOGY_ORDER = tuple(R304_TOPOLOGY_OPENED_LINE)
OPENED_LINES = dict(R304_TOPOLOGY_OPENED_LINE)
ACTION_LIBRARY: dict[str, tuple[float, float, float, float]] = {
    "q0": (350.0, 350.0, 350.0, 350.0),
    "e01_pos": (275.0, 425.0, 350.0, 350.0),
    "e01_neg": (425.0, 275.0, 350.0, 350.0),
    "e12_pos": (350.0, 275.0, 425.0, 350.0),
    "e12_neg": (350.0, 425.0, 275.0, 350.0),
    "e23_pos": (350.0, 350.0, 275.0, 425.0),
    "e23_neg": (350.0, 350.0, 425.0, 275.0),
}
REQUIRED_CELL_GUARDS = (
    "pflow_converged",
    "g4_zeroed",
    "total_m_pass",
    "action_value_pass",
    "opened_line_pass",
    "bus_count_pass",
    "vsg_count_pass",
    "initialization_pass",
    "tds_test_ok",
    "system_exit_zero",
    "residual_pass",
    "eig_run_pass",
    "spectrum_finite",
    "spectrum_pass",
)
DEFAULT_THRESHOLDS = {
    "within_cosine_min": 0.90,
    "within_frequency_delta_max_hz": 0.05,
    "cross_topology_cosine_min": 0.80,
    "cross_topology_frequency_delta_max_hz": 0.10,
    "headroom_max_min_percent": 5.0,
    "headroom_mean_min_percent": 2.0,
    "distinct_oracle_actions_min": 2,
}


def merge_conjugate_pairs(
    modes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge numerically identical conjugate entries before branch selection."""
    ordered = sorted(modes, key=lambda row: (row["freq_hz"], row["real"]))
    merged: list[dict[str, Any]] = []
    for source in ordered:
        mode = dict(source)
        mode["p_machines"] = dict(source["p_machines"])
        if (
            merged
            and abs(float(mode["freq_hz"]) - float(merged[-1]["freq_hz"])) < 1e-9
            and abs(float(mode["real"]) - float(merged[-1]["real"])) < 1e-9
        ):
            previous = merged[-1]
            for key, value in mode["p_machines"].items():
                previous["p_machines"][key] = (
                    float(previous["p_machines"][key]) + float(value)
                ) / 2.0
            previous["damping_ratio"] = (
                float(previous["damping_ratio"]) + float(mode["damping_ratio"])
            ) / 2.0
        else:
            merged.append(mode)
    return merged


def identify_interarea(
    modes: Sequence[Mapping[str, Any]],
    *,
    area1_keys: Sequence[str],
    area2_keys: Sequence[str],
) -> dict[str, Any] | None:
    """Select maximum absolute two-area omega-participation contrast."""
    best: Mapping[str, Any] | None = None
    best_score = -1.0
    for mode in modes:
        participation = mode["p_machines"]
        score = abs(
            sum(float(participation.get(key, 0.0)) for key in area1_keys)
            - sum(float(participation.get(key, 0.0)) for key in area2_keys)
        )
        if score > best_score:
            best = mode
            best_score = score
    if best is None:
        return None
    keys = sorted(best["p_machines"])
    return {
        "freq_hz": float(best["freq_hz"]),
        "damping_ratio": float(best["damping_ratio"]),
        "area_contrast": best_score,
        "p_vector": [float(best["p_machines"][key]) for key in keys],
        "p_keys": keys,
    }


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_values = tuple(float(value) for value in left)
    right_values = tuple(float(value) for value in right)
    if len(left_values) != len(right_values) or not left_values:
        return float("nan")
    numerator = sum(
        a * b for a, b in zip(left_values, right_values, strict=True)
    )
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0.0 or right_norm == 0.0:
        return float("nan")
    return numerator / (left_norm * right_norm)


def _training_gate(classification: str) -> dict[str, Any]:
    if classification == "STATIC-TOPOLOGY-VALUE-EVAL-READY":
        next_step = "R305_MATCHED_CLASSICAL_INFORMATION_GATE"
    elif classification == "STATIC-TOPOLOGY-VALUE-EVAL-NOT-READY":
        next_step = "REPAIR_VECTOR_INERTIA_EVAL_ONLY"
    else:
        next_step = "STOP"
    return {
        "authorized": False,
        "training_executed": False,
        "next_step": next_step,
    }


def _invalid_result(
    *,
    integrity_failures: list[str],
    branch_failures: list[str],
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    classification = "INVALID-TOPOLOGY-GATE"
    return {
        "classification": classification,
        "integrity_failures": integrity_failures,
        "branch_failures": branch_failures,
        "thresholds": dict(thresholds),
        "training_gate": _training_gate(classification),
        "title_alignment": _title_alignment(),
    }


def _title_alignment() -> dict[str, Any]:
    return {
        "supports_zero_sum_common_differential_decoupling": True,
        "supports_static_topology_information_value_only": True,
        "supports_distributed_agent_comparison": False,
        "supports_topology_generalization": False,
        "strict_local_topology_discovery_supported": False,
        "claim_ceiling": (
            "configuration-conditioned static VSG inertia-allocation headroom "
            "on nominal, Line_0-out, and Line_9-out variants"
        ),
    }


def analyze_topology_vector_gate(
    matrix: Mapping[str, Any],
    *,
    eval_ready: bool,
    thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Validate the 21-cell matrix and apply the preregistered R304 gate."""
    limits = {**DEFAULT_THRESHOLDS, **dict(thresholds or {})}
    topologies = tuple(str(value) for value in matrix.get("topologies", ()))
    actions = tuple(str(value) for value in matrix.get("actions", ()))
    raw_cells = matrix.get("cells")
    integrity_failures: list[str] = []
    if topologies != TOPOLOGY_ORDER:
        integrity_failures.append("topology order does not match the frozen contract")
    if actions != tuple(ACTION_LIBRARY):
        integrity_failures.append("action order does not match the frozen contract")
    if not isinstance(raw_cells, Sequence) or isinstance(raw_cells, (str, bytes)):
        integrity_failures.append("cells must be a sequence")
        return _invalid_result(
            integrity_failures=integrity_failures,
            branch_failures=[],
            thresholds=limits,
        )

    cells: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell in raw_cells:
        if not isinstance(cell, Mapping):
            integrity_failures.append("every cell must be an object")
            continue
        key = (str(cell.get("topology")), str(cell.get("action")))
        if key in cells:
            integrity_failures.append(f"duplicate cell {key[0]}/{key[1]}")
        cells[key] = cell
    expected_keys = {
        (topology, action)
        for topology in TOPOLOGY_ORDER
        for action in ACTION_LIBRARY
    }
    missing = sorted(expected_keys - set(cells))
    extra = sorted(set(cells) - expected_keys)
    if missing:
        integrity_failures.append(f"missing cells: {missing}")
    if extra:
        integrity_failures.append(f"unexpected cells: {extra}")

    for topology, action in sorted(expected_keys & set(cells)):
        cell = cells[(topology, action)]
        if cell.get("opened_line") != OPENED_LINES[topology]:
            integrity_failures.append(f"{topology}/{action} opened-line drift")
        guards = cell.get("guards")
        if not isinstance(guards, Mapping):
            integrity_failures.append(f"{topology}/{action} missing guards")
        else:
            for guard in REQUIRED_CELL_GUARDS:
                if guards.get(guard) is not True:
                    integrity_failures.append(
                        f"{topology}/{action} guard failed: {guard}"
                    )
        try:
            observed_m = tuple(float(value) for value in cell["m_vector"])
        except (KeyError, TypeError, ValueError):
            observed_m = ()
        if len(observed_m) != 4 or any(
            abs(observed - expected) > 1e-9
            for observed, expected in zip(
                observed_m,
                ACTION_LIBRARY[action],
                strict=False,
            )
        ):
            integrity_failures.append(f"{topology}/{action} M vector drift")
        identified = cell.get("identified")
        if not isinstance(identified, Mapping):
            integrity_failures.append(f"{topology}/{action} missing identified mode")
            continue
        try:
            damping = float(identified["damping_ratio"])
            frequency = float(identified["freq_hz"])
            vector = tuple(float(value) for value in identified["p_vector"])
        except (KeyError, TypeError, ValueError):
            integrity_failures.append(f"{topology}/{action} malformed identified mode")
            continue
        if (
            not math.isfinite(damping)
            or damping <= 0.0
            or not math.isfinite(frequency)
            or not vector
            or not all(math.isfinite(value) for value in vector)
        ):
            integrity_failures.append(
                f"{topology}/{action} nonfinite or nonpositive mode"
            )
    if integrity_failures:
        return _invalid_result(
            integrity_failures=integrity_failures,
            branch_failures=[],
            thresholds=limits,
        )

    branch_failures: list[str] = []
    nominal_q0 = cells[("nominal", "q0")]["identified"]
    for topology in TOPOLOGY_ORDER:
        q0 = cells[(topology, "q0")]["identified"]
        if topology != "nominal":
            cosine = cosine_similarity(nominal_q0["p_vector"], q0["p_vector"])
            frequency_delta = abs(
                float(nominal_q0["freq_hz"]) - float(q0["freq_hz"])
            )
            if (
                not math.isfinite(cosine)
                or cosine < limits["cross_topology_cosine_min"]
                or frequency_delta >= limits["cross_topology_frequency_delta_max_hz"]
            ):
                branch_failures.append(
                    f"{topology}/q0 cross branch: cos={cosine}, df={frequency_delta}"
                )
        for action in ACTION_LIBRARY:
            identified = cells[(topology, action)]["identified"]
            cosine = cosine_similarity(q0["p_vector"], identified["p_vector"])
            frequency_delta = abs(
                float(q0["freq_hz"]) - float(identified["freq_hz"])
            )
            if (
                not math.isfinite(cosine)
                or cosine < limits["within_cosine_min"]
                or frequency_delta >= limits["within_frequency_delta_max_hz"]
            ):
                branch_failures.append(
                    f"{topology}/{action} within branch: cos={cosine}, df={frequency_delta}"
                )
    if branch_failures:
        return _invalid_result(
            integrity_failures=[],
            branch_failures=branch_failures,
            thresholds=limits,
        )

    damping = {
        topology: {
            action: float(cells[(topology, action)]["identified"]["damping_ratio"])
            for action in ACTION_LIBRARY
        }
        for topology in TOPOLOGY_ORDER
    }
    ratios = {
        topology: {
            action: value / values["q0"] for action, value in values.items()
        }
        for topology, values in damping.items()
    }
    action_order = tuple(ACTION_LIBRARY)
    oracle: dict[str, dict[str, Any]] = {}
    for topology in TOPOLOGY_ORDER:
        action = max(
            action_order,
            key=lambda name: (
                damping[topology][name],
                -action_order.index(name),
            ),
        )
        oracle[topology] = {
            "action": action,
            "damping_ratio": damping[topology][action],
        }
    robust_action = max(
        action_order,
        key=lambda name: (
            min(ratios[topology][name] for topology in TOPOLOGY_ORDER),
            -action_order.index(name),
        ),
    )
    headroom = {
        topology: 100.0
        * (
            float(oracle[topology]["damping_ratio"])
            - damping[topology][robust_action]
        )
        / abs(damping[topology][robust_action])
        for topology in TOPOLOGY_ORDER
    }
    mean_headroom = sum(headroom.values()) / len(headroom)
    max_headroom = max(headroom.values())
    distinct_oracles = len({str(row["action"]) for row in oracle.values()})
    material = bool(
        distinct_oracles >= int(limits["distinct_oracle_actions_min"])
        and max_headroom >= limits["headroom_max_min_percent"]
        and mean_headroom >= limits["headroom_mean_min_percent"]
    )
    if not material:
        classification = "NO-STATIC-TOPOLOGY-VALUE"
    elif eval_ready:
        classification = "STATIC-TOPOLOGY-VALUE-EVAL-READY"
    else:
        classification = "STATIC-TOPOLOGY-VALUE-EVAL-NOT-READY"
    return {
        "classification": classification,
        "integrity_failures": [],
        "branch_failures": [],
        "thresholds": limits,
        "damping_ratios": damping,
        "zeta_ratios": ratios,
        "oracle": oracle,
        "robust_fixed": {
            "action": robust_action,
            "worst_case_ratio": min(
                ratios[topology][robust_action] for topology in TOPOLOGY_ORDER
            ),
        },
        "headroom_percent": headroom,
        "mean_headroom_percent": mean_headroom,
        "max_headroom_percent": max_headroom,
        "distinct_oracle_actions": distinct_oracles,
        "eval_ready": bool(eval_ready),
        "training_gate": _training_gate(classification),
        "title_alignment": _title_alignment(),
    }
