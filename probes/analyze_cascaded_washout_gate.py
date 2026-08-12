"""Run the scratch-only offline gate for one second-order washout candidate.

Usage::

    python probes/analyze_cascaded_washout_gate.py \
        --output tmp/paralleled-vsg-marl/second-order-washout/offline_gate.json

The candidate is fixed prospectively: 0.2 s sampling, 0.05 Hz corner, two
identical washout stages.  The probe does not sweep parameters or execute
ANDES.  A passing result only qualifies the mechanism for a later prospective
physical contract; it is not manuscript evidence.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.control.cascaded_washout import CascadedWashout


DT_SECONDS = 0.2
CORNER_HZ = 0.05
MODE_HZ = 0.4
MODE_GAIN_FLOOR = 0.90
STEP_ENERGY_RATIO_CEILING = 0.85
FIRST_ORDER_ALPHA = 0.90


def _filter_response(values: np.ndarray, *, alpha: float) -> np.ndarray:
    filter_ = CascadedWashout(device_count=1, alpha=alpha)
    return np.asarray([filter_.step([value])[0] for value in values])


def _first_order_response(values: np.ndarray, *, alpha: float) -> np.ndarray:
    state = 0.0
    previous = 0.0
    response = []
    for value in values:
        state = alpha * (state + float(value) - previous)
        previous = float(value)
        response.append(state)
    return np.asarray(response)


def analyze() -> dict[str, object]:
    alpha = math.exp(-2.0 * math.pi * CORNER_HZ * DT_SECONDS)

    time = np.arange(0.0, 80.0, DT_SECONDS)
    mode_input = np.sin(2.0 * math.pi * MODE_HZ * time)
    mode_output = _filter_response(mode_input, alpha=alpha)
    steady = time >= 40.0
    mode_gain = float(
        np.sqrt(np.mean(mode_output[steady] ** 2))
        / np.sqrt(np.mean(mode_input[steady] ** 2))
    )

    sustained_input = np.ones(50, dtype=float)
    candidate_step = _filter_response(sustained_input, alpha=alpha)
    first_order_step = _first_order_response(
        sustained_input,
        alpha=FIRST_ORDER_ALPHA,
    )
    candidate_energy = float(np.sum(candidate_step**2) * DT_SECONDS)
    first_order_energy = float(np.sum(first_order_step**2) * DT_SECONDS)
    energy_ratio = candidate_energy / first_order_energy

    long_step = _filter_response(np.ones(300, dtype=float), alpha=alpha)
    terminal_abs = float(abs(long_step[-1]))
    checks = {
        "mode_gain": mode_gain >= MODE_GAIN_FLOOR,
        "step_energy": energy_ratio <= STEP_ENERGY_RATIO_CEILING,
        "asymptotic_rejection": terminal_abs <= 1.0e-6,
    }
    passed = all(checks.values())
    return {
        "schema_version": 1,
        "classification": "scratch-offline-design-gate",
        "candidate": {
            "mechanism": "two-identical-first-order-washouts-in-series",
            "sample_period_seconds": DT_SECONDS,
            "corner_hz": CORNER_HZ,
            "target_mode_hz": MODE_HZ,
            "alpha": alpha,
            "selection": "single-prospective-candidate-no-sweep",
        },
        "acceptance": {
            "mode_gain_floor": MODE_GAIN_FLOOR,
            "ten_second_step_energy_ratio_ceiling_vs_first_order_alpha_0p9": (
                STEP_ENERGY_RATIO_CEILING
            ),
            "sixty_second_terminal_abs_ceiling": 1.0e-6,
        },
        "observed": {
            "mode_gain": mode_gain,
            "candidate_ten_second_step_energy": candidate_energy,
            "first_order_ten_second_step_energy": first_order_energy,
            "step_energy_ratio": energy_ratio,
            "sixty_second_terminal_abs": terminal_abs,
        },
        "checks": checks,
        "decision": (
            "PASS-OFFLINE-SEPARATION"
            if passed
            else "STOP-OFFLINE-NO-SEPARATION"
        ),
        "authority": (
            "implementation qualification only; no ANDES, training, claim, "
            "or physical-run authority"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["decision"] == "PASS-OFFLINE-SEPARATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
