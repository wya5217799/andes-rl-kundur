"""Evaluate the pre-registered R270 scheduled-basis library oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.attainable_oracle import (  # noqa: E402
    CANDIDATE_SPECS,
    ScheduledBasisResidualController,
    candidate_contract,
)
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.evaluation.physical_endpoints import (  # noqa: E402
    summarise_physical_trace,
)
from andes_rl_kundur.evaluation.residual_objective import (  # noqa: E402
    ResidualObjectiveConfig,
    summarise_frequency_objective,
)

K_DROOP = 10.0
AMPLITUDE = 0.25
ACTIVE_STEPS = 15
ENV_SEED = 42
STEPS = 150
MATERIALITY_PERCENT = 2.0
MIN_NON_DROOP_SELECTIONS = 4
SCENARIOS = tuple(
    {
        "name": f"dev_{load.lower()}_{'pos' if magnitude > 0 else 'neg'}_1p5",
        "delta_u": {load: magnitude},
    }
    for load in ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
    for magnitude in (-1.5, 1.5)
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{path}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _source_paths() -> dict[str, Path]:
    return {
        "memory/rounds/R270/plan.md": ROOT / "memory" / "rounds" / "R270" / "plan.md",
        "scripts/eval_attainable_oracle.py": Path(__file__),
        "src/andes_rl_kundur/evaluation/attainable_oracle.py": (
            ROOT
            / "src"
            / "andes_rl_kundur"
            / "evaluation"
            / "attainable_oracle.py"
        ),
        "src/andes_rl_kundur/evaluation/paper_path.py": (
            ROOT / "src" / "andes_rl_kundur" / "evaluation" / "paper_path.py"
        ),
        "src/andes_rl_kundur/evaluation/physical_endpoints.py": (
            ROOT
            / "src"
            / "andes_rl_kundur"
            / "evaluation"
            / "physical_endpoints.py"
        ),
        "src/andes_rl_kundur/evaluation/residual_objective.py": (
            ROOT
            / "src"
            / "andes_rl_kundur"
            / "evaluation"
            / "residual_objective.py"
        ),
    }


def _baseline_paths(baseline_root: Path) -> dict[str, Path]:
    paths = {
        scenario["name"]: baseline_root / scenario["name"] / "droop_k10.json"
        for scenario in SCENARIOS
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing R268 droop traces: {missing}")
    return paths


def _provenance(baseline_root: Path) -> dict[str, Any]:
    baseline_paths = _baseline_paths(baseline_root)
    return {
        "experiment": "r270_attainable_oracle",
        "contract": candidate_contract(
            amplitude=AMPLITUDE,
            active_steps=ACTIVE_STEPS,
            k_droop=K_DROOP,
        ),
        "scenarios": list(SCENARIOS),
        "environment": {
            "version": "v4",
            "paper_faithful": True,
            "seed": ENV_SEED,
            "steps": STEPS,
            "real_andes_required": True,
        },
        "decision": {
            "materiality_percent_each_co_primary": MATERIALITY_PERCENT,
            "minimum_non_droop_selections": MIN_NON_DROOP_SELECTIONS,
            "safety_ratio_max": 1.05,
            "action_ratio_max": 1.25,
            "selection": (
                "minimum common+differential normalized physical score "
                "among per-scenario eligible candidates; otherwise droop"
            ),
        },
        "requested_candidate_trajectories": (
            len(SCENARIOS) * len(CANDIDATE_SPECS)
        ),
        "baseline_sha256": {
            scenario: sha256_file(path)
            for scenario, path in baseline_paths.items()
        },
        "source_sha256": {
            relative: sha256_file(path)
            for relative, path in _source_paths().items()
        },
    }


def _verify_provenance(
    provenance: dict[str, Any],
    *,
    baseline_root: Path,
) -> None:
    expected_contract = candidate_contract(
        amplitude=AMPLITUDE,
        active_steps=ACTIVE_STEPS,
        k_droop=K_DROOP,
    )
    if provenance.get("contract") != expected_contract:
        raise ValueError("candidate contract drift")
    if provenance.get("requested_candidate_trajectories") != 64:
        raise ValueError("candidate trajectory budget drift")
    for relative, expected in provenance["source_sha256"].items():
        actual = sha256_file(ROOT / relative)
        if actual != expected:
            raise ValueError(f"source drift: {relative}")
    for scenario, expected in provenance["baseline_sha256"].items():
        path = baseline_root / scenario / "droop_k10.json"
        if sha256_file(path) != expected:
            raise ValueError(f"baseline drift: {scenario}")


def _rotated_specs(scenario_index: int) -> tuple[Any, ...]:
    shift = scenario_index % len(CANDIDATE_SPECS)
    return CANDIDATE_SPECS[shift:] + CANDIDATE_SPECS[:shift]


def _load_baseline(path: Path, scenario: str) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "controller": "droop_k10",
        "scenario": scenario,
        "completed": True,
        "tds_failed": False,
        "n_steps": STEPS,
        "requested_steps": STEPS,
    }
    drift = {
        key: {"expected": value, "actual": record.get(key)}
        for key, value in expected.items()
        if record.get(key) != value
    }
    if drift:
        raise ValueError(f"R268 baseline contract drift for {scenario}: {drift}")
    return record


def _frequency_score(record: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    traces = record["traces"]
    delta_f = np.asarray(
        [step["delta_f_physical_hz"] for step in traces],
        dtype=float,
    )
    time = np.asarray([step["t"] for step in traces], dtype=float)
    summary = summarise_frequency_objective(
        delta_f,
        sample_interval_s=float(np.median(np.diff(time))),
        config=ResidualObjectiveConfig(),
    )
    return float(summary["frequency_scalar_mean"]), summary


def _eligibility_reasons(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if (
        candidate.get("completed") is not True
        or candidate.get("tds_failed") is True
        or candidate.get("n_steps") != STEPS
    ):
        return ["failed_or_incomplete"]
    physical = summarise_physical_trace(candidate)
    reference = summarise_physical_trace(baseline)
    if physical["settling_time_s"] is None:
        reasons.append("not_settled")
    for endpoint in ("vsg_mean_iae_hz_s", "normalized_sync_loss_hz2"):
        if float(physical[endpoint]) > float(reference[endpoint]) + 1e-15:
            reasons.append(f"{endpoint}_worse")
    for endpoint in ("worst_bus_peak_abs_hz", "max_abs_rocof_hz_s"):
        if float(physical[endpoint]) > 1.05 * float(reference[endpoint]):
            reasons.append(f"{endpoint}_over_5pct")
    for endpoint in ("action_l1_agent_s", "action_total_variation"):
        if float(physical[endpoint]) > 1.25 * float(reference[endpoint]):
            reasons.append(f"{endpoint}_over_25pct")
    if float(physical["action_saturation_fraction"]) > float(
        reference["action_saturation_fraction"]
    ) + 1e-15:
        reasons.append("saturation_higher")
    return reasons


def _endpoint_subset(record: dict[str, Any]) -> dict[str, Any]:
    physical = summarise_physical_trace(record)
    keys = (
        "vsg_mean_iae_hz_s",
        "normalized_sync_loss_hz2",
        "worst_bus_peak_abs_hz",
        "max_abs_rocof_hz_s",
        "settling_time_s",
        "action_l1_agent_s",
        "action_total_variation",
        "action_saturation_fraction",
    )
    return {key: physical[key] for key in keys}


def _percent(candidate: float, baseline: float) -> float:
    return 100.0 * (candidate / baseline - 1.0)


def _analyse(
    records: list[dict[str, Any]],
    *,
    baseline_root: Path,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    _verify_provenance(provenance, baseline_root=baseline_root)
    if len(records) != 64:
        raise ValueError(f"expected exactly 64 candidate records, got {len(records)}")

    by_scenario_candidate = {
        (record["scenario"], record["controller"]): record for record in records
    }
    if len(by_scenario_candidate) != 64:
        raise ValueError("duplicate or missing scenario/candidate record")

    baseline_paths = _baseline_paths(baseline_root)
    scenario_results: list[dict[str, Any]] = []
    chosen_records: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []
    non_droop_count = 0

    for scenario in SCENARIOS:
        name = scenario["name"]
        baseline = _load_baseline(baseline_paths[name], name)
        baseline_records.append(baseline)
        baseline_score, baseline_frequency = _frequency_score(baseline)
        candidates: list[dict[str, Any]] = []
        for order, spec in enumerate(CANDIDATE_SPECS):
            record = by_scenario_candidate[(name, spec.name)]
            reasons = _eligibility_reasons(record, baseline)
            if record.get("completed") is True and record.get("tds_failed") is not True:
                score, frequency = _frequency_score(record)
                endpoints = _endpoint_subset(record)
            else:
                score, frequency, endpoints = None, None, None
            candidates.append(
                {
                    "candidate": spec.name,
                    "library_order": order,
                    "eligible": not reasons,
                    "ineligibility_reasons": reasons,
                    "frequency_score": score,
                    "frequency_objective": frequency,
                    "endpoints": endpoints,
                    "completed": record.get("completed"),
                    "tds_failed": record.get("tds_failed"),
                    "n_steps": record.get("n_steps"),
                    "cum_rf_total": record.get("cum_rf_total"),
                    "telemetry": record.get("scheduled_basis_telemetry"),
                }
            )

        eligible = [
            row
            for row in candidates
            if row["eligible"]
            and row["frequency_score"] is not None
            and float(row["frequency_score"]) < baseline_score - 1e-12
        ]
        if eligible:
            selected = min(
                eligible,
                key=lambda row: (
                    float(row["frequency_score"]),
                    int(row["library_order"]),
                ),
            )
            selected_name = str(selected["candidate"])
            chosen = by_scenario_candidate[(name, selected_name)]
            non_droop_count += 1
        else:
            selected_name = "droop_k10"
            chosen = baseline
        chosen_records.append(chosen)
        scenario_results.append(
            {
                "scenario": name,
                "baseline_sha256": provenance["baseline_sha256"][name],
                "baseline": {
                    "frequency_score": baseline_score,
                    "frequency_objective": baseline_frequency,
                    "endpoints": _endpoint_subset(baseline),
                    "cum_rf_total": baseline["cum_rf_total"],
                },
                "candidates": candidates,
                "selected": selected_name,
                "selected_frequency_score": (
                    baseline_score
                    if selected_name == "droop_k10"
                    else next(
                        float(row["frequency_score"])
                        for row in candidates
                        if row["candidate"] == selected_name
                    )
                ),
            }
        )

    endpoint_keys = (
        "vsg_mean_iae_hz_s",
        "normalized_sync_loss_hz2",
        "worst_bus_peak_abs_hz",
        "max_abs_rocof_hz_s",
        "action_l1_agent_s",
        "action_total_variation",
        "action_saturation_fraction",
    )
    baseline_endpoints = [_endpoint_subset(record) for record in baseline_records]
    chosen_endpoints = [_endpoint_subset(record) for record in chosen_records]
    aggregate = {
        "droop_k10": {
            key: float(np.mean([row[key] for row in baseline_endpoints]))
            for key in endpoint_keys
        },
        "library_oracle": {
            key: float(np.mean([row[key] for row in chosen_endpoints]))
            for key in endpoint_keys
        },
    }
    effects = {
        key: _percent(
            aggregate["library_oracle"][key],
            aggregate["droop_k10"][key],
        )
        if aggregate["droop_k10"][key] != 0.0
        else None
        for key in endpoint_keys
    }
    baseline_cum_rf = float(np.mean([record["cum_rf_total"] for record in baseline_records]))
    chosen_cum_rf = float(np.mean([record["cum_rf_total"] for record in chosen_records]))
    effects["cum_rf_total_absolute_delta"] = chosen_cum_rf - baseline_cum_rf

    selected_all_complete = all(
        record.get("completed") is True
        and record.get("tds_failed") is not True
        and record.get("n_steps") == STEPS
        for record in chosen_records
    )
    selected_all_settled = all(
        endpoint["settling_time_s"] is not None for endpoint in chosen_endpoints
    )
    selected_all_eligible = all(
        result["selected"] == "droop_k10"
        or next(
            row["eligible"]
            for row in result["candidates"]
            if row["candidate"] == result["selected"]
        )
        for result in scenario_results
    )
    guards = {
        "exactly_64_candidate_trajectories": len(records) == 64,
        "baseline_and_source_hashes_match": True,
        "selected_all_complete": selected_all_complete,
        "selected_all_settled": selected_all_settled,
        "selected_all_eligibility_guards_pass": selected_all_eligible,
        "non_droop_selected_at_least_4_of_8": (
            non_droop_count >= MIN_NON_DROOP_SELECTIONS
        ),
        "mean_iae_improves_at_least_2pct": (
            effects["vsg_mean_iae_hz_s"] is not None
            and effects["vsg_mean_iae_hz_s"] <= -MATERIALITY_PERCENT
        ),
        "mean_sync_improves_at_least_2pct": (
            effects["normalized_sync_loss_hz2"] is not None
            and effects["normalized_sync_loss_hz2"] <= -MATERIALITY_PERCENT
        ),
    }
    material = all(guards.values())

    candidate_summary: dict[str, Any] = {}
    for spec in CANDIDATE_SPECS:
        rows = [
            by_scenario_candidate[(scenario["name"], spec.name)]
            for scenario in SCENARIOS
        ]
        complete = [
            row
            for row in rows
            if row.get("completed") is True
            and row.get("tds_failed") is not True
            and row.get("n_steps") == STEPS
        ]
        candidate_summary[spec.name] = {
            "complete_count": len(complete),
            "eligible_scenario_count": sum(
                next(
                    row["eligible"]
                    for row in scenario_result["candidates"]
                    if row["candidate"] == spec.name
                )
                for scenario_result in scenario_results
            ),
            "selected_scenario_count": sum(
                result["selected"] == spec.name for result in scenario_results
            ),
            "complete_endpoint_means": (
                {
                    key: float(
                        np.mean(
                            [_endpoint_subset(record)[key] for record in complete]
                        )
                    )
                    for key in endpoint_keys
                }
                if complete
                else None
            ),
        }

    return {
        "experiment": "r270_attainable_oracle",
        "classification": (
            "MATERIAL-MARGIN" if material else "NO-MATERIAL-MARGIN"
        ),
        "development_library_oracle_only": True,
        "deployable_controller": False,
        "provenance_sha256": sha256_file(
            Path(provenance["_provenance_path"])
        ),
        "scenario_results": scenario_results,
        "candidate_summary": candidate_summary,
        "selection_counts": {
            "non_droop": non_droop_count,
            "droop": len(SCENARIOS) - non_droop_count,
            "by_controller": {
                name: sum(result["selected"] == name for result in scenario_results)
                for name in ("droop_k10", *[spec.name for spec in CANDIDATE_SPECS])
            },
        },
        "aggregate_means": aggregate,
        "library_oracle_minus_droop_effects_percent": effects,
        "cum_rf_total_means": {
            "droop_k10": baseline_cum_rf,
            "library_oracle": chosen_cum_rf,
        },
        "gate": guards,
    }


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    effects = summary["library_oracle_minus_droop_effects_percent"]
    lines = [
        "# R270 attainable library-oracle summary",
        "",
        f"- Classification: **{summary['classification']}**",
        "- Evidence: development library oracle; not a deployable controller.",
        (
            "- Non-droop selections: "
            f"{summary['selection_counts']['non_droop']}/8."
        ),
        "",
        "## Aggregate effects",
        "",
        "| Endpoint | Library oracle minus droop |",
        "|---|---:|",
    ]
    for endpoint in (
        "vsg_mean_iae_hz_s",
        "normalized_sync_loss_hz2",
        "worst_bus_peak_abs_hz",
        "max_abs_rocof_hz_s",
        "action_l1_agent_s",
        "action_total_variation",
        "action_saturation_fraction",
    ):
        value = effects[endpoint]
        lines.append(
            f"| {endpoint} | "
            f"{'unavailable' if value is None else f'{value:+.6f}%'} |"
        )
    lines.extend(
        [
            "",
            "## Selected controller by scenario",
            "",
            "| Scenario | Selected |",
            "|---|---|",
        ]
    )
    for row in summary["scenario_results"]:
        lines.append(f"| {row['scenario']} | {row['selected']} |")
    temporary = Path(f"{path}.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_smoke(out_dir: Path) -> None:
    if out_dir.exists():
        raise FileExistsError(f"refusing to reuse smoke output: {out_dir}")
    out_dir.mkdir(parents=True)
    scenario = SCENARIOS[0]
    spec = CANDIDATE_SPECS[0]
    controller = ScheduledBasisResidualController(
        spec,
        amplitude=AMPLITUDE,
        active_steps=ACTIVE_STEPS,
        k_droop=K_DROOP,
    )
    record = run_scenario(
        scenario["name"],
        scenario["delta_u"],
        action_fn=controller,
        label=spec.name,
        seed=ENV_SEED,
        steps=10,
        extra_keys={
            "experiment": "r270_attainable_oracle_smoke",
            "scheduled_basis_telemetry_pending": True,
        },
    )
    record["scheduled_basis_telemetry"] = controller.telemetry()
    _write_json_atomic(out_dir / "smoke_trace.json", record)
    print(
        f"[smoke] completed={record['completed']} n={record['n_steps']} "
        f"tds_failed={record['tds_failed']}"
    )


def _run_formal(
    *,
    baseline_root: Path,
    out_dir: Path,
    resume: bool,
) -> None:
    provenance_path = out_dir / "provenance.json"
    if out_dir.exists() and not resume:
        raise FileExistsError(f"refusing to reuse output directory: {out_dir}")
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
        provenance = _provenance(baseline_root)
        _write_json_atomic(provenance_path, provenance)
    else:
        if (out_dir / "attainable_oracle_summary.json").exists():
            raise FileExistsError("formal summary already exists; refusing to rerun")
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    _verify_provenance(provenance, baseline_root=baseline_root)

    records: list[dict[str, Any]] = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        ordered = _rotated_specs(scenario_index)
        print(
            f"[scenario {scenario_index + 1:02d}/{len(SCENARIOS)}] "
            f"{scenario['name']} order={','.join(spec.name for spec in ordered)}",
            flush=True,
        )
        for run_index, spec in enumerate(ordered):
            path = out_dir / "traces" / scenario["name"] / f"{spec.name}.json"
            if path.exists():
                if not resume:
                    raise FileExistsError(f"unexpected existing trace: {path}")
                record = json.loads(path.read_text(encoding="utf-8"))
                print(
                    f"  [resume {run_index + 1}/8] {spec.name} "
                    f"completed={record.get('completed')}",
                    flush=True,
                )
            else:
                print(f"  [run {run_index + 1}/8] {spec.name}", flush=True)
                controller = ScheduledBasisResidualController(
                    spec,
                    amplitude=AMPLITUDE,
                    active_steps=ACTIVE_STEPS,
                    k_droop=K_DROOP,
                )
                record = run_scenario(
                    scenario["name"],
                    scenario["delta_u"],
                    action_fn=controller,
                    label=spec.name,
                    seed=ENV_SEED,
                    steps=STEPS,
                    extra_keys={
                        "experiment": "r270_attainable_oracle",
                        "scenario_index": scenario_index,
                        "candidate_order": [item.name for item in ordered],
                        "amplitude": AMPLITUDE,
                        "active_steps": ACTIVE_STEPS,
                        "k_droop": K_DROOP,
                    },
                )
                record["scheduled_basis_telemetry"] = controller.telemetry()
                _write_json_atomic(path, record)
                print(
                    f"    -> completed={record['completed']} "
                    f"n={record['n_steps']} tds_failed={record['tds_failed']}",
                    flush=True,
                )
            records.append(record)

    provenance_for_analysis = dict(provenance)
    provenance_for_analysis["_provenance_path"] = str(provenance_path)
    summary = _analyse(
        records,
        baseline_root=baseline_root,
        provenance=provenance_for_analysis,
    )
    _write_json_atomic(out_dir / "attainable_oracle_summary.json", summary)
    _write_summary(out_dir / "attainable_oracle_summary.md", summary)
    print(f"[oracle] classification={summary['classification']}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-root",
        type=Path,
        default=(
            ROOT / "results" / "r268_residual_pilot_eval" / "traces"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results" / "r270_attainable_oracle",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        if args.resume:
            raise ValueError("--smoke and --resume are mutually exclusive")
        _run_smoke(args.out_dir)
    else:
        _run_formal(
            baseline_root=args.baseline_root,
            out_dir=args.out_dir,
            resume=args.resume,
        )


if __name__ == "__main__":
    main()
