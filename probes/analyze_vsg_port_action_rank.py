"""Diagnose finite-horizon rank of paired VSG-owned power-port probes.

This scratch probe reuses valid physical trajectories and does not launch
ANDES.  It verifies the input hash and paired command schedules before calling
the reusable rank calculator.

Usage:
    PYTHONPATH=src python probes/analyze_vsg_port_action_rank.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

from andes_rl_kundur.evaluation.coupled_actuator_authority import (
    physical_coordinate_matrix,
)
from andes_rl_kundur.evaluation.finite_horizon_action_rank import (
    finite_horizon_action_rank,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "results/research_loop/r380_vsg_source_model_gate"
    / "formal_validation_records.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "tmp/paralleled-vsg-marl/pref-action-rank"
    / "r380_pref_action_rank.json"
)
RECORD_PATTERN = re.compile(r"^(P\d+)_control_(\d+)_(plus|minus)$")
ACTION_COUNT = 4


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_payload(path: Path) -> tuple[dict[str, object], str]:
    companion = Path(f"{path}.sha256")
    if not path.is_file() or not companion.is_file():
        raise FileNotFoundError("input JSON and companion sha256 are required")
    expected = companion.read_text(encoding="utf-8").split()[0]
    observed = _sha256(path)
    if observed != expected:
        raise ValueError("input sha256 mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input payload must be a JSON object")
    return payload, observed


def _paired_traces(
    records: list[dict[str, object]],
    *,
    point: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    indexed = {str(record.get("record_id")): record for record in records}
    plus_traces: list[np.ndarray] = []
    minus_traces: list[np.ndarray] = []
    amplitudes: list[float] = []
    record_ids: list[str] = []
    sample_times: np.ndarray | None = None

    for action in range(ACTION_COUNT):
        pair: dict[str, dict[str, object]] = {}
        for sign in ("plus", "minus"):
            record_id = f"{point}_control_{action}_{sign}"
            record = indexed.get(record_id)
            if record is None:
                raise ValueError(f"missing paired record: {record_id}")
            if record.get("kind") != "control" or record.get("failure") is not None:
                raise ValueError(f"invalid control record: {record_id}")
            guards = record.get("guards")
            if not isinstance(guards, dict) or not guards or not all(
                bool(value) for value in guards.values()
            ):
                raise ValueError(f"record guards failed: {record_id}")
            pair[sign] = record
            record_ids.append(record_id)

        plus_rows = pair["plus"].get("rows")
        minus_rows = pair["minus"].get("rows")
        if not isinstance(plus_rows, list) or not isinstance(minus_rows, list):
            raise ValueError("paired record rows are required")
        plus_commands = np.asarray(
            [row["control_system_pu"] for row in plus_rows], dtype=float
        )
        minus_commands = np.asarray(
            [row["control_system_pu"] for row in minus_rows], dtype=float
        )
        if plus_commands.shape != minus_commands.shape or plus_commands.shape[1] != 4:
            raise ValueError("paired command shapes differ")
        if not np.allclose(plus_commands, -minus_commands, atol=1e-12, rtol=0.0):
            raise ValueError("paired command schedules are not antisymmetric")
        inactive = [index for index in range(ACTION_COUNT) if index != action]
        if not np.allclose(plus_commands[:, inactive], 0.0, atol=1e-12, rtol=0.0):
            raise ValueError("one action probe changed another VSG command")
        amplitude = float(np.max(plus_commands[:, action]))
        if amplitude <= 0.0 or float(np.min(plus_commands[:, action])) < -1e-12:
            raise ValueError("positive probe schedule is malformed")

        plus_frequency = np.asarray(
            pair["plus"].get("frequency_deviation_hz"), dtype=float
        )
        minus_frequency = np.asarray(
            pair["minus"].get("frequency_deviation_hz"), dtype=float
        )
        if plus_frequency.shape != minus_frequency.shape or plus_frequency.ndim != 2:
            raise ValueError("paired frequency traces differ")
        times = np.asarray([row["time"] for row in plus_rows], dtype=float)
        minus_times = np.asarray([row["time"] for row in minus_rows], dtype=float)
        if not np.allclose(times, minus_times, atol=1e-12, rtol=0.0):
            raise ValueError("paired time grids differ")
        if sample_times is None:
            sample_times = times
        elif not np.allclose(sample_times, times, atol=1e-12, rtol=0.0):
            raise ValueError("action time grids differ")

        plus_traces.append(plus_frequency)
        minus_traces.append(minus_frequency)
        amplitudes.append(amplitude)

    assert sample_times is not None
    return (
        np.asarray(plus_traces),
        np.asarray(minus_traces),
        np.asarray(amplitudes),
        {
            "record_ids": record_ids,
            "time_start_seconds": float(sample_times[0]),
            "time_stop_seconds": float(sample_times[-1]),
            "sample_period_seconds": float(np.median(np.diff(sample_times))),
        },
    )


def analyze(path: Path) -> dict[str, object]:
    payload, input_sha256 = _verified_payload(path)
    records = payload.get("records")
    if not isinstance(records, list) or int(payload.get("record_count", -1)) != len(
        records
    ):
        raise ValueError("record inventory is invalid")
    control_ids = [
        str(record.get("record_id"))
        for record in records
        if record.get("kind") == "control"
    ]
    points = sorted(
        {match.group(1) for record_id in control_ids if (match := RECORD_PATTERN.match(record_id))}
    )
    if not points:
        raise ValueError("no paired control records found")

    point_results: dict[str, object] = {}
    for point in points:
        plus, minus, amplitudes, provenance = _paired_traces(records, point=point)
        profile = finite_horizon_action_rank(
            plus,
            minus,
            amplitudes=amplitudes,
            output_transform=physical_coordinate_matrix(),
        )
        point_results[point] = {
            "provenance": provenance,
            "profile": profile,
            "scratch_readout": {
                "all_rank_at_relative_0p1": profile["all_outputs"][
                    "relative_effective_rank"
                ]["0.1"],
                "common_rank_at_relative_0p1": profile["common_output"][
                    "relative_effective_rank"
                ]["0.1"],
                "differential_rank_at_relative_0p1": profile[
                    "differential_outputs"
                ]["relative_effective_rank"]["0.1"],
            },
        }

    return {
        "schema_version": 1,
        "classification": "SCRATCH-DIAGNOSTIC-NOT-EVIDENCE",
        "claim_boundary": (
            "Reanalysis of existing valid R380 physical pulse records only; "
            "no M/D comparison, controller value, MARL value, or new-line evidence."
        ),
        "input": {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": input_sha256,
            "source_round": payload.get("round"),
            "training_executed": payload.get("training_executed"),
        },
        "coordinate_order": ["common", "interarea", "within_area_1", "within_area_2"],
        "points": point_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = analyze(args.input.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
