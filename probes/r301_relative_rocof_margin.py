#!/usr/bin/env python3
"""Create R301's model-gate result from retained, hash-verified inputs.

Usage:
    python probes/r301_relative_rocof_margin.py preview
    python probes/r301_relative_rocof_margin.py write

``preview`` prints the prospective payload without writing. ``write`` creates
the JSON and SHA-256 sidecar exactly once.  The fixed-anchor calculation is a
local small-signal diagnostic and is never labelled a stability certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.relative_rocof_margin import (  # noqa: E402
    continuous_rocof_transfer,
    esd_active_power_input_matrix,
    frequency_output_matrix,
    graph_coordinate_audit,
    held_path_transfer,
    ideal_swing_routh_margin,
    sampled_closed_loop_matrix,
    sampled_mode_summary,
    sampled_rocof_transfer,
)


ROUND_ID = "R301"
QUESTION_ID = "Q-0058"
SAMPLE_PERIOD_S = 0.2
FILTER_TIME_CONSTANT_S = 0.2
ACTUATOR_TIME_CONSTANT_S = 0.02
ANCHOR_MODE_HZ = 1.1352719219086884
TARGET_BAND_HZ = (0.2, 1.5)
BASE_GAIN = 0.24424071249620005
TOTAL_2KV_GAIN = 2.0 * BASE_GAIN
RING = {0: (1, 3), 1: (0, 2), 2: (1, 3), 3: (0, 2)}
AREA_1_KEYS = ("genrou1", "genrou2", "vsg12", "vsg16")
AREA_2_KEYS = ("genrou3", "genrou4", "vsg14", "vsg15")
VOLTAGE_ENVELOPE_PU = (0.95, 1.0, 1.05)

FIXED_ANCHOR = (
    ROOT
    / "results/r294_model_validation/stage_a/records/16__fixed_lti_anchor.json"
)
R300_SUMMARY = ROOT / "results/r300_fixed_2kv_formal/formal_summary.json"
R300_SEAL = ROOT / "memory/rounds/R300/fixed_2kv_formal_seal.json"
PLAN = ROOT / "memory/rounds/R301/plan.md"
MODULE = ROOT / "src/andes_rl_kundur/evaluation/relative_rocof_margin.py"
OUTPUT = ROOT / "results/r301_relative_rocof_margin/analysis_summary.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty input: {path}")
    if not sidecar.is_file() or sidecar.stat().st_size == 0:
        raise RuntimeError(f"missing or empty sidecar: {sidecar}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = sha256_file(path)
    if expected != observed:
        raise RuntimeError(f"input sidecar mismatch: {path}")
    return observed


def source_entry(path: Path, *, require_sidecar: bool = False) -> dict[str, str]:
    digest = verify_sidecar(path) if require_sidecar else sha256_file(path)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest}


def complex_record(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "magnitude": float(abs(value)),
        "phase_degrees": float(math.degrees(math.atan2(value.imag, value.real))),
    }


def frequency_audit() -> dict[str, object]:
    target_frequency = np.linspace(TARGET_BAND_HZ[0], TARGET_BAND_HZ[1], 1301)
    nyquist_hz = 0.5 / SAMPLE_PERIOD_S
    full_frequency = np.linspace(1e-6, nyquist_hz - 1e-6, 25000)
    digital_target = [
        sampled_rocof_transfer(
            frequency,
            sample_period_s=SAMPLE_PERIOD_S,
            filter_time_constant_s=FILTER_TIME_CONSTANT_S,
        )
        for frequency in target_frequency
    ]
    held_target = [
        held_path_transfer(
            frequency,
            sample_period_s=SAMPLE_PERIOD_S,
            filter_time_constant_s=FILTER_TIME_CONSTANT_S,
            actuator_time_constant_s=ACTUATOR_TIME_CONSTANT_S,
        )
        for frequency in target_frequency
    ]
    held_full = [
        held_path_transfer(
            frequency,
            sample_period_s=SAMPLE_PERIOD_S,
            filter_time_constant_s=FILTER_TIME_CONSTANT_S,
            actuator_time_constant_s=ACTUATOR_TIME_CONSTANT_S,
        )
        for frequency in full_frequency
    ]
    crossing = None
    for left, right, left_value, right_value in zip(
        full_frequency[:-1],
        full_frequency[1:],
        held_full[:-1],
        held_full[1:],
        strict=True,
    ):
        if left_value.real >= 0.0 and right_value.real < 0.0:
            fraction = left_value.real / (left_value.real - right_value.real)
            crossing = float(left + fraction * (right - left))
            break
    digital_anchor = sampled_rocof_transfer(
        ANCHOR_MODE_HZ,
        sample_period_s=SAMPLE_PERIOD_S,
        filter_time_constant_s=FILTER_TIME_CONSTANT_S,
    )
    continuous_anchor = continuous_rocof_transfer(
        ANCHOR_MODE_HZ,
        filter_time_constant_s=FILTER_TIME_CONSTANT_S,
    )
    held_anchor = held_path_transfer(
        ANCHOR_MODE_HZ,
        sample_period_s=SAMPLE_PERIOD_S,
        filter_time_constant_s=FILTER_TIME_CONSTANT_S,
        actuator_time_constant_s=ACTUATOR_TIME_CONSTANT_S,
    )
    return {
        "sample_period_s": SAMPLE_PERIOD_S,
        "filter_time_constant_s": FILTER_TIME_CONSTANT_S,
        "actuator_time_constant_s": ACTUATOR_TIME_CONSTANT_S,
        "nyquist_hz": nyquist_hz,
        "target_band_hz": list(TARGET_BAND_HZ),
        "digital_filter_target_min_real": float(
            min(value.real for value in digital_target)
        ),
        "held_path_target_min_real": float(min(value.real for value in held_target)),
        "held_path_first_real_zero_crossing_hz": crossing,
        "anchor_mode_hz": ANCHOR_MODE_HZ,
        "digital_anchor": complex_record(digital_anchor),
        "continuous_anchor": complex_record(continuous_anchor),
        "held_anchor": complex_record(held_anchor),
        "anchor_dynamic_over_static_sync": {
            "kv": float(BASE_GAIN * abs(digital_anchor)),
            "2kv": float(TOTAL_2KV_GAIN * abs(digital_anchor)),
        },
    }


def fixed_anchor_audit(graph_laplacian: np.ndarray) -> dict[str, object]:
    record = json.loads(FIXED_ANCHOR.read_text(encoding="utf-8"))
    plant = np.asarray(record["state_matrix"], dtype=float)
    output = frequency_output_matrix(
        plant.shape[0],
        record["vsg_omega_state_indices"],
        nominal_frequency_hz=60.0,
    )
    cases: list[dict[str, object]] = []
    for voltage in VOLTAGE_ENVELOPE_PU:
        plant_input = esd_active_power_input_matrix(
            record["state_names"],
            device_count=4,
            active_current_lag_seconds=ACTUATOR_TIME_CONSTANT_S,
            sensed_voltage_pu=voltage,
        )
        for label, gain in (
            ("no_relative_rocof", 0.0),
            ("kv", BASE_GAIN),
            ("2kv", TOTAL_2KV_GAIN),
        ):
            closed_loop = sampled_closed_loop_matrix(
                plant,
                plant_input,
                output,
                graph_laplacian,
                sample_period_s=SAMPLE_PERIOD_S,
                filter_time_constant_s=FILTER_TIME_CONSTANT_S,
                kp_system_pu_per_hz=2.0,
                ki_system_pu_per_hz_s=0.2,
                sync_gain_system_pu_per_hz=1.0,
                consensus_gain_per_s=1.0,
                relative_rocof_gain_system_pu_s_per_hz=gain,
            )
            cases.append(
                {
                    "sensed_voltage_pu": voltage,
                    "gain_label": label,
                    "total_relative_rocof_gain_system_pu_s_per_hz": gain,
                    **sampled_mode_summary(
                        closed_loop,
                        sample_period_s=SAMPLE_PERIOD_S,
                        machine_state_indices=record["machine_state_indices"],
                        area_1_keys=AREA_1_KEYS,
                        area_2_keys=AREA_2_KEYS,
                        frequency_band_hz=TARGET_BAND_HZ,
                    ),
                }
            )
    two_kv = [case for case in cases if case["gain_label"] == "2kv"]
    return {
        "authority": "local fixed-anchor sampled small-signal diagnostic only",
        "input_model": (
            "ANDES ESD1 unsaturated equilibrium relation "
            "tip*d(Ipout_y)/dt=Pext/vp-Ipout_y with explicit 0.95--1.05 pu voltage envelope"
        ),
        "case_count": len(cases),
        "cases": cases,
        "two_kv_unstable_count_max": int(
            max(int(case["unstable_count"]) for case in two_kv)
        ),
    }


def build_payload() -> dict[str, Any]:
    graph = graph_coordinate_audit(RING, device_count=4)
    frequency = frequency_audit()
    fixed_anchor = fixed_anchor_audit(np.asarray(graph["laplacian"], dtype=float))
    ideal_example = ideal_swing_routh_margin(
        inertia=1.0,
        damping=1.0,
        synchronizing_stiffness=1.0,
        filter_time_constant_s=FILTER_TIME_CONSTANT_S,
        graph_eigenvalue=1.0,
        residual_gain=TOTAL_2KV_GAIN,
    )
    separation_pass = bool(
        float(graph["symmetry_max_abs"]) <= 1e-15
        and float(graph["common_kernel_max_abs"]) <= 1e-15
        and min(float(value) for value in graph["differential_eigenvalues"]) > 0.0
    )
    frequency_pass = bool(
        float(frequency["digital_filter_target_min_real"]) > 0.0
        and float(frequency["held_path_target_min_real"]) > 0.0
    )
    fixed_anchor_pass = fixed_anchor["two_kv_unstable_count_max"] == 0
    balanced_or_stronger = (
        float(frequency["anchor_dynamic_over_static_sync"]["2kv"]) >= 1.0
    )
    if not separation_pass:
        classification = "INVALID-CONTROLLER-SEPARATION"
    elif not frequency_pass or not fixed_anchor_pass:
        classification = "MODEL-NO-GO"
    elif bool(ideal_example["routh_margin_gain_slope"] > 0.0) and balanced_or_stronger:
        classification = "2KV-SUFFICIENT-NO-BLIND-ESCALATION"
    else:
        classification = "ONE-NONLINEAR-PROBE-AUTHORIZED"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "relative_rocof_model_gate",
        "classification": classification,
        "sources": {
            "plan": source_entry(PLAN),
            "probe": source_entry(Path(__file__).resolve()),
            "pure_module": source_entry(MODULE),
            "r294_fixed_anchor": source_entry(FIXED_ANCHOR, require_sidecar=True),
            "r300_formal_summary": source_entry(R300_SUMMARY, require_sidecar=True),
            "r300_formal_seal": source_entry(R300_SEAL, require_sidecar=True),
        },
        "graph_coordinate_audit": graph,
        "frequency_audit": frequency,
        "ideal_modal_result": {
            "characteristic_polynomial": (
                "tau*M*s^3+(M+tau*D+Kv*lambda)*s^2+(D+tau*Ks)*s+Ks"
            ),
            "routh_margin_identity": (
                "D*(M+tau*D+tau^2*Ks)+Kv*lambda*(D+tau*Ks)"
            ),
            "finite_nonnegative_gain_ceiling_from_ideal_model": False,
            "unit_parameter_check": ideal_example,
        },
        "fixed_anchor_audit": fixed_anchor,
        "gates": {
            "controller_separation_pass": separation_pass,
            "target_band_positive_real_pass": frequency_pass,
            "fixed_anchor_2kv_no_new_unstable_mode_pass": fixed_anchor_pass,
            "two_kv_anchor_dynamic_branch_not_weaker_than_static_sync": (
                balanced_or_stronger
            ),
        },
        "next_action": {
            "nonlinear_higher_gain_probe_authorized": (
                classification == "ONE-NONLINEAR-PROBE-AUTHORIZED"
            ),
            "selected_candidate": None,
            "reason": (
                "the ideal model is monotone dissipative but supplies no finite optimum; "
                "2Kv already makes the implemented anchor dynamic branch stronger than "
                "the static synchronization branch, so a higher gain would be outcome-driven"
            ),
        },
        "claim_boundary": (
            "controller-interface common/differential separation and one local sampled "
            "small-signal diagnostic only; no hard plant decoupling, nonlinear/robust "
            "stability certificate, delay robustness, MARL, neural, topology, safety, "
            "EMT-HIL, or deployment claim"
        ),
    }


def write_new(path: Path, payload: dict[str, Any]) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preview", "write"))
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build_payload()
    if args.command == "preview":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    digest = write_new(args.output, payload)
    print(f"classification={payload['classification']}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
