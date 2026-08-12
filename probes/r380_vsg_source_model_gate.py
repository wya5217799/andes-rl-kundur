"""Pure bank, metric, and first-failure classifier for the R380 model gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.model_first_input_bridge import SampledInputModel

POINTS = ("P0", "P1")
CONTROL_AMPLITUDE = 0.01
LOAD_AMPLITUDE = 0.02
STEPS = 125
PULSE_START = 5
PULSE_STOP = 10
EXPECTED_CASE_SHA256 = (
    "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
)


def record_guards(
    *,
    rows: Sequence[Mapping[str, Any]],
    expected_inputs: np.ndarray,
    point: str,
    identity: Mapping[str, Any],
    load_baseline: np.ndarray,
    seal_sha256: str,
    runtime: Mapping[str, Any],
    failure: str | None,
    contract: Mapping[str, Any],
) -> dict[str, bool]:
    """Apply every preregistered per-record validity guard before metrics."""

    tolerance = float(contract["numeric_atol"])
    steps = int(contract["validation"]["steps_per_record"])
    completed = len(rows) == steps and failure is None
    finite = completed and all(
        np.all(np.isfinite(np.asarray(row[key], dtype=float)))
        for row in rows
        for key in (
            "control_system_pu",
            "disturbance_system_pu",
            "requested_power_system_pu",
            "commanded_power_system_pu",
            "sampled_omega_pu",
            "baseline_pref_system_pu",
            "pref_written_system_pu",
            "pref_readback_system_pu",
            "torque_readback_system_pu",
            "achieved_power_system_pu",
            "load_readback_system_pu",
            "omega",
            "freq_hz_physical",
            "P_es",
            "delta_M",
            "delta_D",
            "md_action_norm",
        )
    )
    guard_names = (
        "record_complete",
        "identity_and_units",
        "input_profile_and_sign",
        "request_command_and_projection",
        "pref_tm0_and_power_readback",
        "legacy_md_zero",
        "load_feasibility_and_readback",
        "event_timing",
        "pflow_tds_and_finite",
        "source_case_and_seal_hash",
    )
    if not completed:
        return dict.fromkeys(guard_names, False)

    controls = np.asarray([row["control_system_pu"] for row in rows], dtype=float)
    disturbances = np.asarray(
        [row["disturbance_system_pu"] for row in rows], dtype=float
    )
    requested = np.asarray(
        [row["requested_power_system_pu"] for row in rows], dtype=float
    )
    commanded = np.asarray(
        [row["commanded_power_system_pu"] for row in rows], dtype=float
    )
    sampled = np.asarray([row["sampled_omega_pu"] for row in rows], dtype=float)
    baseline_pref = np.asarray(
        [row["baseline_pref_system_pu"] for row in rows], dtype=float
    )
    written = np.asarray(
        [row["pref_written_system_pu"] for row in rows], dtype=float
    )
    readback = np.asarray(
        [row["pref_readback_system_pu"] for row in rows], dtype=float
    )
    torque = np.asarray(
        [row["torque_readback_system_pu"] for row in rows], dtype=float
    )
    omega = np.asarray([row["omega"] for row in rows], dtype=float)
    achieved = np.asarray(
        [row["achieved_power_system_pu"] for row in rows], dtype=float
    )
    expected_written = baseline_pref + commanded / sampled
    expected_achieved = (torque - baseline_pref) * 0.5 * (sampled + omega)
    load_readback = np.asarray(
        [row["load_readback_system_pu"] for row in rows], dtype=float
    )
    times = np.asarray([row["time"] for row in rows], dtype=float)
    expected_loads = list(contract["disturbance_inputs"])
    expected_baseline = np.asarray(
        [
            contract["declared_load_baselines_system_pu"][name]
            for name in expected_loads
        ],
        dtype=float,
    )
    identity_pass = (
        identity.get("vsg_idx") == list(contract["control_inputs"])
        and identity.get("vsg_buses") == [12, 16, 14, 15]
        and identity.get("pq_load_ids") == expected_loads
        and identity.get("point") == point
        and np.isclose(
            float(identity.get("pq_bus15_p0_system_pu", float("nan"))),
            float(contract["points"][point]["pq_bus15_p0_system_pu"]),
            atol=tolerance,
            rtol=0.0,
        )
        and identity.get("pflow_converged") is True
        and identity.get("tds_test_ok") is True
        and identity.get("exit_code") == 0
        and np.allclose(
            load_baseline,
            expected_baseline,
            atol=tolerance,
            rtol=0.0,
        )
    )
    return {
        "record_complete": True,
        "identity_and_units": bool(identity_pass),
        "input_profile_and_sign": bool(
            np.array_equal(controls, expected_inputs[:, :4])
            and np.array_equal(disturbances, expected_inputs[:, 4:])
        ),
        "request_command_and_projection": bool(
            np.allclose(requested, controls, atol=0.0, rtol=0.0)
            and np.allclose(commanded, controls, atol=tolerance, rtol=0.0)
            and all(not any(row["saturation_reasons"]) for row in rows)
        ),
        "pref_tm0_and_power_readback": bool(
            np.allclose(written, expected_written, atol=tolerance, rtol=0.0)
            and np.allclose(readback, written, atol=tolerance, rtol=0.0)
            and np.allclose(torque, written, atol=tolerance, rtol=0.0)
            and np.allclose(achieved, expected_achieved, atol=tolerance, rtol=0.0)
        ),
        "legacy_md_zero": bool(
            all(
                np.allclose(row["delta_M"], 0.0, atol=0.0, rtol=0.0)
                and np.allclose(row["delta_D"], 0.0, atol=0.0, rtol=0.0)
                and np.allclose(row["md_action_norm"], 0.0, atol=0.0, rtol=0.0)
                for row in rows
            )
        ),
        "load_feasibility_and_readback": bool(
            np.all(load_readback >= 0.0)
            and np.allclose(
                load_readback,
                load_baseline[np.newaxis, :] + disturbances,
                atol=tolerance,
                rtol=0.0,
            )
        ),
        "event_timing": bool(
            np.allclose(
                np.diff(times),
                float(contract["sample_period_seconds"]),
                atol=1.0e-10,
                rtol=0.0,
            )
        ),
        "pflow_tds_and_finite": bool(
            finite and all(row["tds_failed"] is False for row in rows)
        ),
        "source_case_and_seal_hash": bool(
            identity.get("seal_sha256") == seal_sha256
            and identity.get("case_sha256") == runtime.get("case_sha256")
            and identity.get("andes_version") == runtime.get("andes_version")
            and len(seal_sha256) == 64
            and runtime.get("case_sha256") == EXPECTED_CASE_SHA256
            and runtime.get("andes_version") == "2.0.0"
        ),
    }


def _record(
    *,
    point: str,
    suffix: str,
    kind: str,
    control: Sequence[float],
    disturbance: Sequence[float],
) -> dict[str, object]:
    return {
        "record_id": f"{point}_{suffix}",
        "point": point,
        "kind": kind,
        "control_system_pu": [float(value) for value in control],
        "disturbance_system_pu": [float(value) for value in disturbance],
        "steps": STEPS,
        "pulse_start": PULSE_START,
        "pulse_stop": PULSE_STOP,
    }


def record_specs() -> tuple[dict[str, object], ...]:
    """Return the exact 36-record prospective validation bank."""

    rows: list[dict[str, object]] = []
    for point in POINTS:
        for repeat in range(2):
            rows.append(
                _record(
                    point=point,
                    suffix=f"zero_{repeat}",
                    kind="zero",
                    control=np.zeros(4),
                    disturbance=np.zeros(3),
                )
            )
        for channel in range(4):
            for sign_name, sign in (("plus", 1.0), ("minus", -1.0)):
                control = np.zeros(4)
                control[channel] = sign * CONTROL_AMPLITUDE
                rows.append(
                    _record(
                        point=point,
                        suffix=f"control_{channel}_{sign_name}",
                        kind="control",
                        control=control,
                        disturbance=np.zeros(3),
                    )
                )
        for channel in range(3):
            for sign_name, sign in (("plus", 1.0), ("minus", -1.0)):
                disturbance = np.zeros(3)
                disturbance[channel] = sign * LOAD_AMPLITUDE
                rows.append(
                    _record(
                        point=point,
                        suffix=f"load_{channel}_{sign_name}",
                        kind="load",
                        control=np.zeros(4),
                        disturbance=disturbance,
                    )
                )
        rows.append(
            _record(
                point=point,
                suffix="combined_plus",
                kind="combined",
                control=(CONTROL_AMPLITUDE, 0.0, 0.0, 0.0),
                disturbance=(0.0, LOAD_AMPLITUDE, 0.0),
            )
        )
        rows.append(
            _record(
                point=point,
                suffix="combined_minus",
                kind="combined",
                control=(0.0, 0.0, 0.0, -CONTROL_AMPLITUDE),
                disturbance=(0.0, 0.0, -LOAD_AMPLITUDE),
            )
        )
    return tuple(rows)


def input_sequence(spec: Mapping[str, object]) -> np.ndarray:
    """Expand one registered rectangular pulse into four-plus-three inputs."""

    if (
        int(spec.get("steps", -1)) != STEPS
        or int(spec.get("pulse_start", -1)) != PULSE_START
        or int(spec.get("pulse_stop", -1)) != PULSE_STOP
    ):
        raise ValueError("R380 pulse timing drift")
    control = np.asarray(spec.get("control_system_pu"), dtype=float)
    disturbance = np.asarray(spec.get("disturbance_system_pu"), dtype=float)
    if (
        control.shape != (4,)
        or disturbance.shape != (3,)
        or not np.all(np.isfinite(control))
        or not np.all(np.isfinite(disturbance))
    ):
        raise ValueError("R380 input vectors must contain four control and three load values")
    sequence = np.zeros((STEPS, 7), dtype=float)
    sequence[PULSE_START:PULSE_STOP, :4] = control
    sequence[PULSE_START:PULSE_STOP, 4:] = disturbance
    return sequence


def _simulate(model: SampledInputModel, inputs: np.ndarray) -> np.ndarray:
    state = np.zeros(model.state_matrix.shape[0], dtype=float)
    outputs = np.zeros((inputs.shape[0], 4), dtype=float)
    for step, value in enumerate(inputs):
        outputs[step] = model.output_matrix @ state + model.feedthrough_matrix @ value
        state = model.state_matrix @ state + model.input_matrix @ value
    return outputs


def trajectory_metrics(prediction: object, truth: object) -> dict[str, float | bool]:
    """Return the two preregistered per-record worst-vector errors."""

    predicted = np.asarray(prediction, dtype=float)
    observed = np.asarray(truth, dtype=float)
    if (
        predicted.shape != observed.shape
        or predicted.shape != (STEPS, 4)
        or not np.all(np.isfinite(predicted))
        or not np.all(np.isfinite(observed))
    ):
        raise ValueError("R380 prediction and truth must be finite 125-by-4 arrays")
    error = predicted - observed
    squared_truth = float(np.sum(np.square(observed)))
    nrmse = float(np.sqrt(np.sum(np.square(error)) / max(squared_truth, 1.0e-24)))
    peak_residual = float(
        np.max(np.linalg.norm(error, axis=1))
        / max(float(np.max(np.linalg.norm(observed, axis=1))), 1.0e-12)
    )
    return {
        "nrmse": nrmse,
        "peak_vector_residual": peak_residual,
        "pass": nrmse <= 0.15 and peak_residual <= 0.20,
    }


def classify_r380(
    *,
    validity_pass: bool,
    construction_pass: bool,
    metrics: Sequence[Mapping[str, object]],
) -> str:
    """Apply the frozen first-applicable R380 outcome tree."""

    if not validity_pass:
        return "INVALID-OBJECT-OR-PORT"
    if not construction_pass:
        return "STOP-SOURCE-MODEL"
    control = [row for row in metrics if row.get("kind") == "control"]
    if not control or not all(row.get("pass") is True for row in control):
        return "STOP-MODEL-FIDELITY"
    other = [row for row in metrics if row.get("kind") in {"load", "combined"}]
    if not other or not all(row.get("pass") is True for row in other):
        return "QUALIFY-DIAGNOSTIC-ONLY"
    return "ALLOW-MODEL-BASED-DESIGN"


def analyse_validation_records(
    *,
    models: Mapping[str, SampledInputModel],
    records: Sequence[Mapping[str, Any]],
    construction_pass: bool,
) -> dict[str, object]:
    """Validate the exact bank, then compute model errors if guards permit."""

    specs = record_specs()
    expected = {str(row["record_id"]): row for row in specs}
    actual = {str(row.get("record_id")): row for row in records}
    inventory_pass = len(actual) == len(records) and set(actual) == set(expected)
    guards_pass = inventory_pass and all(
        isinstance(row.get("guards"), Mapping)
        and bool(row["guards"])
        and all(value is True for value in row["guards"].values())
        for row in records
    )
    output_shapes_pass = inventory_pass and all(
        np.asarray(row.get("frequency_deviation_hz"), dtype=float).shape == (STEPS, 4)
        and np.all(np.isfinite(row.get("frequency_deviation_hz")))
        for row in records
    )
    model_inventory_pass = set(models) == set(POINTS)
    zero_repeat_maximum = float("inf")
    if inventory_pass and output_shapes_pass:
        zero_repeat_maximum = max(
            float(
                np.max(
                    np.abs(
                        np.asarray(actual[f"{point}_zero_1"]["frequency_deviation_hz"])
                        - np.asarray(
                            actual[f"{point}_zero_0"]["frequency_deviation_hz"]
                        )
                    )
                )
            )
            for point in POINTS
        )
    zero_repeat_pass = zero_repeat_maximum <= 1.0e-9
    validity_pass = bool(
        inventory_pass
        and guards_pass
        and output_shapes_pass
        and model_inventory_pass
        and zero_repeat_pass
    )
    checks = {
        "record_inventory": inventory_pass,
        "all_record_guards": guards_pass,
        "output_shapes_and_finite_values": output_shapes_pass,
        "point_model_inventory": model_inventory_pass,
        "zero_repeatability": zero_repeat_pass,
    }
    if not validity_pass or not construction_pass:
        classification = classify_r380(
            validity_pass=validity_pass,
            construction_pass=construction_pass,
            metrics=[],
        )
        return {
            "classification": classification,
            "validity_pass": validity_pass,
            "construction_pass": construction_pass,
            "checks": checks,
            "zero_repeat_maximum_hz": zero_repeat_maximum,
            "record_metrics": {},
        }

    metrics: dict[str, dict[str, object]] = {}
    for record_id, spec in expected.items():
        if spec["kind"] == "zero":
            continue
        point = str(spec["point"])
        baseline = np.asarray(
            actual[f"{point}_zero_0"]["frequency_deviation_hz"],
            dtype=float,
        )
        truth = np.asarray(actual[record_id]["frequency_deviation_hz"], dtype=float) - baseline
        row = trajectory_metrics(
            _simulate(models[point], input_sequence(spec)),
            truth,
        )
        metrics[record_id] = {"kind": spec["kind"], **row}
    classification = classify_r380(
        validity_pass=True,
        construction_pass=True,
        metrics=list(metrics.values()),
    )
    return {
        "classification": classification,
        "validity_pass": True,
        "construction_pass": True,
        "checks": checks,
        "zero_repeat_maximum_hz": zero_repeat_maximum,
        "record_metrics": metrics,
        "training_authorized": False,
        "physical_controller_authorized": False,
    }
