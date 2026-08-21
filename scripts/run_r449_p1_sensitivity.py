"""R449 — successor P1.1 sensitivity decomposition with effective D perturbation."""
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

import run_r448_p1_sensitivity as base  # noqa: E402
from memory.tools.artifact_io import write_new_json  # noqa: E402

OUT = ROOT / "results" / "research_loop" / "r449_p1_sensitivity"
FORMAL = OUT / "formal_analysis.json"
ROUND = "R449"


def _source_model(m_scale: float = 1.0, d_scale: float = 1.0):
    from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import AndesVSGEnergyPortFixedStateSource
    from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import derive_vsg_energy_port_input_bridge
    from andes_rl_kundur.evaluation.vsg_energy_port_source_model import construct_vsg_energy_port_source_model

    env = base._build_env(m_scale=m_scale, d_scale=d_scale)
    try:
        env.reset(delta_u={})
        source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            env, pq_load_ids=base.LOAD_IDS, source_fingerprint=ROUND
        )
        bridges = tuple(
            derive_vsg_energy_port_input_bridge(
                binding=source.binding, source=source, step_system_pu=step
            )
            for step in base.FD_STEPS
        )
        result = construct_vsg_energy_port_source_model(
            snapshot=source.descriptor_snapshot, bridges=bridges
        )
        if result.sampled_model is None:
            raise RuntimeError(f"source model failed: {result.error}")
        return result.sampled_model
    finally:
        env.close()


def _derivatives():
    nominal = _source_model()
    m_plus = _source_model(m_scale=1.0 + base.DELTA)
    m_minus = _source_model(m_scale=1.0 - base.DELTA)
    d_plus = _source_model(d_scale=1.0 + base.DELTA)
    d_minus = _source_model(d_scale=1.0 - base.DELTA)
    d_m = (m_plus.state_matrix - m_minus.state_matrix) / (2.0 * base.DELTA)
    d_d = (d_plus.state_matrix - d_minus.state_matrix) / (2.0 * base.DELTA)
    return nominal, d_m, d_d


def _classify(candidate: float, reference: float, derivative_max_abs: float) -> tuple[str, float | None]:
    if (
        derivative_max_abs <= 1.0e-12
        or not np.isfinite(candidate)
        or not np.isfinite(reference)
        or candidate == 0.0
        or reference == 0.0
    ):
        return "CANARY-INVALID", None
    ratio = max(abs(candidate), abs(reference)) / min(abs(candidate), abs(reference))
    if ratio <= 3.0:
        return "MIXED", float(ratio)
    verdict = "CANDIDATE-DOMINANT" if abs(candidate) > abs(reference) else "REFERENCE-DOMINANT"
    return verdict, float(ratio)


def rehearse() -> int:
    if FORMAL.exists() or FORMAL.with_suffix(FORMAL.suffix + ".sha256").exists():
        raise FileExistsError(f"formal output already exists: {FORMAL}")
    nominal = _source_model()
    d_plus = _source_model(d_scale=1.0 + base.DELTA)
    d_minus = _source_model(d_scale=1.0 - base.DELTA)
    d_d = (d_plus.state_matrix - d_minus.state_matrix) / (2.0 * base.DELTA)
    d_max = float(np.max(np.abs(d_d)))
    if nominal.state_matrix.shape != d_plus.state_matrix.shape or d_max <= 1.0e-12:
        raise RuntimeError(f"ineffective D perturbation: max_abs={d_max}")
    print(json.dumps({
        "rehearse_ok": True,
        "round": ROUND,
        "state_dim": int(nominal.state_matrix.shape[0]),
        "d_logD_state_matrix_max_abs": d_max,
        "formal_output_absent": True,
    }, indent=2))
    return 0


def analyse() -> int:
    nominal, d_m, d_d = _derivatives()
    headroom = base._headroom()
    a_k, b_k, c_k = base._bandpass_closed_loop(nominal, headroom)
    a_l, b_l, c_l = base._local_pi_closed_loop(nominal, headroom)
    frequencies = 2 * np.pi * np.linspace(0.05, 2.0, 400)
    band = [i for i, value in enumerate(frequencies) if 0.3 <= value / (2 * np.pi) <= 0.5]

    results: dict[str, dict[str, float | str | None]] = {}
    verdicts: dict[str, str] = {}
    for rho_name, derivative in (("logM", d_m), ("logD", d_d)):
        num_k, den_k = base._term(a_k, b_k, c_k, derivative, base.DT, frequencies, band)
        num_l, den_l = base._term(a_l, b_l, c_l, derivative, base.DT, frequencies, band)
        candidate = 2.0 * num_k / den_k if den_k > 0.0 else float("nan")
        reference = -2.0 * num_l / den_l if den_l > 0.0 else float("nan")
        derivative_max_abs = float(np.max(np.abs(derivative)))
        verdict, dominance_ratio = _classify(candidate, reference, derivative_max_abs)
        verdicts[rho_name] = verdict
        results[rho_name] = {
            "candidate_term": float(candidate) if np.isfinite(candidate) else None,
            "reference_term": float(reference) if np.isfinite(reference) else None,
            "dominance_ratio": dominance_ratio,
            "d_state_matrix_max_abs": derivative_max_abs,
            "verdict": verdict,
        }

    payload = {
        "schema_version": 1,
        "round": ROUND,
        "delta": base.DELTA,
        "rho": "log-perturbation of M and D",
        "results": results,
        "verdicts": verdicts,
    }
    digest = write_new_json(FORMAL, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"sha256={digest}")
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
