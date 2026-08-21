"""R450 — same-bank zero-delay endpoint plus command-break complex loop."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r440_robustness_expansion as r440  # noqa: E402
import run_r448_p1_sensitivity as response  # noqa: E402
import run_r449_p1_sensitivity as source  # noqa: E402
from memory.tools.artifact_io import write_new_json  # noqa: E402

ROUND = "R450"
OUT = ROOT / "results/research_loop/r450_p2_delay_loop"
FORMAL = OUT / "formal_analysis.json"
PARENT_DELAY = {
    1: ROOT / "results/research_loop/r440_robustness_expansion/delay/delay_1.json",
    2: ROOT / "results/research_loop/r440_robustness_expansion/delay/delay_2.json",
}
DELAYS = (0, 1, 2)
CURVE_TOL = 0.10


def delayed_response(loop: np.ndarray, plant_disturbance: np.ndarray, z: complex, delay: int) -> np.ndarray:
    identity = np.eye(loop.shape[0], dtype=complex)
    return np.linalg.solve(identity + (z ** (-delay)) * loop, plant_disturbance)


def _linear_loop() -> dict:
    model = source._source_model()
    headroom = response._headroom()
    a_d = model.state_matrix
    b_control = model.input_matrix[:, :4] @ np.diag(headroom)
    b_disturbance = model.input_matrix[:, 4:]
    c_frequency = model.output_matrix
    incidence = __import__(
        "andes_rl_kundur.control.ring_bandpass_damping",
        fromlist=["ring_incidence", "prewarped_bandpass_coefficients"],
    )
    ring = incidence.ring_incidence(response.N_AGENTS)
    numerator, denominator = incidence.prewarped_bandpass_coefficients(**response.BANDPASS_COEF)
    a_local, b_local, c_local = response._local_pi_closed_loop(model, headroom)
    frequencies_hz = np.linspace(0.05, 2.0, 400)
    band_rows: list[dict] = []
    energies = {delay: 0.0 for delay in DELAYS}
    local_energy = 0.0
    min_return = {delay: float("inf") for delay in DELAYS}
    for frequency_hz in frequencies_hz:
        omega = 2.0 * np.pi * float(frequency_hz) * response.DT
        z = np.exp(1j * omega)
        plant_control = c_frequency @ np.linalg.solve(z * np.eye(a_d.shape[0]) - a_d, b_control)
        plant_disturbance = c_frequency @ np.linalg.solve(z * np.eye(a_d.shape[0]) - a_d, b_disturbance)
        z_inv = 1.0 / z
        filt = (
            numerator[0] + numerator[1] * z_inv + numerator[2] * z_inv**2
        ) / (1.0 + denominator[1] * z_inv + denominator[2] * z_inv**2)
        controller = ring @ (filt * np.eye(ring.shape[1])) @ ring.T
        loop = plant_control @ controller
        local = c_local @ np.linalg.solve(z * np.eye(a_local.shape[0]) - a_local, b_local)
        if 0.3 <= frequency_hz <= 0.5:
            local_diff = response.T_D @ local
            local_energy += float(np.real(np.vdot(local_diff, local_diff)))
            row = {
                "frequency_hz": float(frequency_hz),
                "L0_real": np.real(loop).tolist(),
                "L0_imag": np.imag(loop).tolist(),
            }
            for delay in DELAYS:
                candidate = delayed_response(loop, plant_disturbance, z, delay)
                candidate_diff = response.T_D @ candidate
                energies[delay] += float(np.real(np.vdot(candidate_diff, candidate_diff)))
                sigma = np.linalg.svd(np.eye(4) + z ** (-delay) * loop, compute_uv=False)
                min_return[delay] = min(min_return[delay], float(np.min(sigma)))
            band_rows.append(row)
    ratios = {delay: energies[delay] / local_energy for delay in DELAYS}
    return {
        "loop_break": "normalized bandpass output before 0.072 pu power mapping; inject u, read controller frequency-deviation y",
        "sample_period_seconds": response.DT,
        "feedback_sign": "u=-K(z)y",
        "formula": "L0=PcK; Gn=[I+z^-n L0]^-1 Pd",
        "band_hz": [0.3, 0.5],
        "band_rows": band_rows,
        "predicted_r_d": {str(k): float(v) for k, v in ratios.items()},
        "min_return_difference_sigma": {str(k): float(v) for k, v in min_return.items()},
    }


def _ratio(entry: dict) -> dict:
    return r440._ratio_from_summaries(entry["bandpass_k3p5"], entry["local_feasibility_native"])


def _parent_delays() -> dict[int, dict]:
    return {delay: r440._read_hashed_json(path) for delay, path in PARENT_DELAY.items()}


def _run_zero_delay() -> tuple[dict, dict]:
    contract = r440.build_contract()
    records = [
        r440._run_job(job, contract=contract, delay_steps=0)
        for arm_id in ("zero_feedback", "local_feasibility_native", "bandpass_k3p5")
        for job in r440._block_jobs(arm_id, contract)
    ]
    invalid = [
        record for record in records
        if record.get("tds_failed") or record.get("completed_steps") != int(contract["steps"])
    ]
    if invalid:
        raise RuntimeError(f"zero-delay record validity failed: {len(invalid)} records")
    summaries = r440._summarize_block(records, contract)
    return summaries, {"record_count": len(records), "invalid_count": 0, "steps_per_record": int(contract["steps"])}


def _classify(linear: dict, nonlinear: dict[str, dict]) -> dict:
    predicted = {int(k): float(v) for k, v in linear["predicted_r_d"].items()}
    observed = {int(k): float(v["ratios"]["r_d"]) for k, v in nonlinear.items()}
    seam_error = abs(predicted[0] - observed[0]) / observed[0]
    comparisons = {}
    valid = seam_error <= CURVE_TOL and all(
        float(linear["min_return_difference_sigma"][str(delay)]) > 1.0e-8
        for delay in DELAYS
    )
    for delay in (1, 2):
        q_linear = predicted[delay] / predicted[0]
        q_nonlinear = observed[delay] / observed[0]
        relative_error = abs(q_linear - q_nonlinear) / q_nonlinear
        same_direction = (q_linear - 1.0) * (q_nonlinear - 1.0) > 0.0
        comparisons[str(delay)] = {
            "q_linear": q_linear,
            "q_nonlinear": q_nonlinear,
            "relative_error": relative_error,
            "same_direction": bool(same_direction),
            "passes": bool(same_direction and relative_error <= CURVE_TOL),
        }
    if not valid:
        verdict = "CANARY-INVALID"
    elif all(row["passes"] for row in comparisons.values()):
        verdict = "PHASE-DELAY-CONSISTENT"
    else:
        verdict = "PHASE-DELAY-REFUTED"
    boundary = (
        "BETWEEN-0-AND-1-SAMPLE-ENDPOINT-BOUNDARY"
        if observed[0] <= r440.DIFFERENTIAL_RATIO_MAX < observed[1]
        else "NO-BETWEEN-0-AND-1-BOUNDARY"
    )
    return {
        "verdict": verdict,
        "endpoint_boundary": boundary,
        "linear_nonlinear_zero_delay_relative_error": seam_error,
        "comparisons": comparisons,
    }


def rehearse() -> int:
    if FORMAL.exists() or FORMAL.with_suffix(FORMAL.suffix + ".sha256").exists():
        raise FileExistsError(f"formal output exists: {FORMAL}")
    parents = _parent_delays()
    contract = r440.build_contract()
    job = r440._block_jobs("bandpass_k3p5", contract)[0]
    record = r440._run_job(job, contract=contract, delay_steps=0)
    linear = _linear_loop()
    if record.get("tds_failed") or record.get("completed_steps") != int(contract["steps"]):
        raise RuntimeError("zero-delay rehearsal record invalid")
    print(json.dumps({
        "rehearse_ok": True,
        "round": ROUND,
        "parent_delays": sorted(parents),
        "record_steps": int(record["completed_steps"]),
        "loop_shape": [4, 4],
        "linear_r_d_0": linear["predicted_r_d"]["0"],
        "formal_output_absent": True,
    }, indent=2))
    return 0


def analyse() -> int:
    parents = _parent_delays()
    zero_summaries, validity = _run_zero_delay()
    nonlinear = {
        "0": {"ratios": _ratio(zero_summaries), "source": ROUND, **validity},
        "1": {"ratios": _ratio(parents[1]), "source": "R440/delay_1.json"},
        "2": {"ratios": _ratio(parents[2]), "source": "R440/delay_2.json"},
    }
    linear = _linear_loop()
    classification = _classify(linear, nonlinear)
    payload = {
        "schema_version": 1,
        "round": ROUND,
        "parent_contract_sha256": r440.contract_sha256(r440.build_contract()),
        "nonlinear": nonlinear,
        "linear_loop": linear,
        "classification": classification,
    }
    digest = write_new_json(FORMAL, payload)
    print(json.dumps({
        "round": ROUND,
        "nonlinear_r_d": {k: v["ratios"]["r_d"] for k, v in nonlinear.items()},
        "predicted_r_d": linear["predicted_r_d"],
        "classification": classification,
        "sha256": digest,
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("rehearse", "analyse"))
    args = parser.parse_args(argv)
    try:
        return rehearse() if args.mode == "rehearse" else analyse()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
