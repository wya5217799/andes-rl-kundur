"""Evaluate the R268 bounded-droop residual pilot on fixed development cases."""

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

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.hybrid import (  # noqa: E402
    bounded_droop_residual_action_fn,
    proportional_damping_action_fn,
)
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.evaluation.physical_endpoints import (  # noqa: E402
    summarise_physical_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    binomial_rate_summary,
    empirical_upper_tail,
)


K_DROOP = 10.0
RESIDUAL_SCALE = 0.10
ENV_SEED = 42
STEPS = 150
CONTROLLERS = ("droop_k10", "residual_td3_s49_b0p10")
ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "normalized_sync_loss_hz2",
    "worst_bus_peak_abs_hz",
    "max_abs_rocof_hz_s",
    "action_l1_agent_s",
    "action_total_variation",
    "action_saturation_fraction",
)
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


def _load_contract(ckpt_dir: Path) -> tuple[dict[str, Any], str]:
    path = ckpt_dir / "controller_contract.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "mode": "bounded_droop_residual",
        "algo": "td3",
        "seed": 49,
        "k_droop": K_DROOP,
        "residual_scale": RESIDUAL_SCALE,
        "actor_output": "normalized_residual",
        "environment_input": "normalized_executed_action",
    }
    drift = {
        key: {"expected": value, "actual": payload.get(key)}
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if drift:
        raise ValueError(f"controller contract drift: {drift}")
    for relative, expected_hash in payload.get("source_sha256", {}).items():
        actual = sha256_file(ROOT / relative)
        if actual != expected_hash:
            raise ValueError(f"training source drift for {relative}")
    return payload, sha256_file(path)


def _checkpoint_hashes(ckpt_dir: Path) -> dict[str, str]:
    return {
        f"agent_{i}_final.pt": sha256_file(ckpt_dir / f"agent_{i}_final.pt")
        for i in range(4)
    }


def _reload_is_deterministic(ckpt_dir: Path) -> bool:
    first = load_agents(ckpt_dir, suffix="final", hidden_sizes=(64, 64, 64, 64))
    second = load_agents(ckpt_dir, suffix="final", hidden_sizes=(64, 64, 64, 64))
    obs = {
        i: np.array([0.25, (-1.0) ** i * 0.03, 0.0, 0.0, 0.0, 0.0, 0.0])
        for i in range(4)
    }
    first_fn = bounded_droop_residual_action_fn(
        deterministic_actor_action_fn(first),
        k_droop=K_DROOP,
        residual_scale=RESIDUAL_SCALE,
    )
    second_fn = bounded_droop_residual_action_fn(
        deterministic_actor_action_fn(second),
        k_droop=K_DROOP,
        residual_scale=RESIDUAL_SCALE,
    )
    a = first_fn(0, obs, 4)
    b = second_fn(0, obs, 4)
    return all(np.array_equal(a[i], b[i]) for i in range(4))


def _rotated_order(index: int) -> tuple[str, ...]:
    shift = index % len(CONTROLLERS)
    return CONTROLLERS[shift:] + CONTROLLERS[:shift]


def _run(ckpt_dir: Path, out_dir: Path) -> None:
    if out_dir.exists():
        raise FileExistsError(f"refusing to reuse pilot output directory: {out_dir}")
    contract, contract_hash = _load_contract(ckpt_dir)
    checkpoint_hashes = _checkpoint_hashes(ckpt_dir)
    reload_deterministic = _reload_is_deterministic(ckpt_dir)
    if not reload_deterministic:
        raise RuntimeError("checkpoint reload did not reproduce deterministic action")

    agents = load_agents(
        ckpt_dir,
        suffix="final",
        hidden_sizes=(64, 64, 64, 64),
    )
    residual_controller = bounded_droop_residual_action_fn(
        deterministic_actor_action_fn(agents),
        k_droop=K_DROOP,
        residual_scale=RESIDUAL_SCALE,
    )
    action_functions = {
        "droop_k10": proportional_damping_action_fn(K_DROOP),
        "residual_td3_s49_b0p10": residual_controller,
    }

    out_dir.mkdir(parents=True)
    trace_records: list[dict[str, Any]] = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        order = _rotated_order(scenario_index)
        print(
            f"[scenario {scenario_index + 1:02d}/{len(SCENARIOS)}] "
            f"{scenario['name']} {scenario['delta_u']} order={','.join(order)}",
            flush=True,
        )
        for run_index, controller in enumerate(order):
            print(f"  [run {run_index + 1}/2] {controller}", flush=True)
            record = run_scenario(
                scenario["name"],
                scenario["delta_u"],
                action_fn=action_functions[controller],
                label=controller,
                seed=ENV_SEED,
                steps=STEPS,
                extra_keys={
                    "experiment": "r268_bounded_residual_pilot",
                    "scenario_index": scenario_index,
                    "controller_order": list(order),
                    "controller_contract_sha256": contract_hash,
                    "checkpoint_sha256": checkpoint_hashes,
                },
            )
            if controller == "residual_td3_s49_b0p10":
                record["residual_telemetry"] = residual_controller.telemetry()
            trace_path = out_dir / "traces" / scenario["name"] / f"{controller}.json"
            _write_json_atomic(trace_path, record)
            trace_records.append(record)
            print(
                f"    -> completed={record['completed']} "
                f"n={record['n_steps']} peak={record.get('physical_max_df')}",
                flush=True,
            )

    summary = _analyse(
        trace_records,
        contract=contract,
        contract_hash=contract_hash,
        checkpoint_hashes=checkpoint_hashes,
        reload_deterministic=reload_deterministic,
    )
    _write_json_atomic(out_dir / "pilot_summary.json", summary)
    _write_summary(out_dir / "pilot_summary.md", summary)
    print(f"[pilot] classification={summary['pilot_gate']['classification']}", flush=True)


def _analyse(
    records: list[dict[str, Any]],
    *,
    contract: dict[str, Any],
    contract_hash: str,
    checkpoint_hashes: dict[str, str],
    reload_deterministic: bool,
) -> dict[str, Any]:
    expected = len(SCENARIOS) * len(CONTROLLERS)
    if len(records) != expected:
        raise ValueError(f"expected {expected} traces, got {len(records)}")
    by_controller: dict[str, list[dict[str, Any]]] = {
        controller: [] for controller in CONTROLLERS
    }
    for record in records:
        by_controller[record["controller"]].append(record)

    summaries: dict[str, Any] = {}
    endpoint_rows: dict[str, dict[str, dict[str, float]]] = {}
    for controller in CONTROLLERS:
        rows = by_controller[controller]
        complete = [
            row
            for row in rows
            if row.get("completed") is True
            and row.get("tds_failed") is not True
            and row.get("n_steps") == STEPS
        ]
        endpoint_rows[controller] = {
            row["scenario"]: {
                key: float(value)
                for key, value in summarise_physical_trace(row).items()
                if key in ENDPOINTS and value is not None
            }
            for row in complete
        }
        distributions = {
            endpoint: empirical_upper_tail(
                {
                    scenario: values[endpoint]
                    for scenario, values in endpoint_rows[controller].items()
                }
            )
            for endpoint in ENDPOINTS
            if complete
        }
        settled = sum(
            summarise_physical_trace(row)["settling_time_s"] is not None
            for row in complete
        )
        failures = len(rows) - len(complete)
        summaries[controller] = {
            "complete_count": len(complete),
            "failure": binomial_rate_summary(failures, len(rows)),
            "settling": binomial_rate_summary(settled, len(rows)),
            "failed_or_incomplete_scenarios": [
                row["scenario"] for row in rows if row not in complete
            ],
            "endpoints": distributions,
        }

    all_complete = all(
        summaries[controller]["complete_count"] == len(SCENARIOS)
        for controller in CONTROLLERS
    )
    effects: dict[str, float | None] = {}
    if all_complete:
        residual = summaries["residual_td3_s49_b0p10"]["endpoints"]
        droop = summaries["droop_k10"]["endpoints"]
        for endpoint in ENDPOINTS:
            reference = droop[endpoint]["mean"]
            effects[endpoint] = (
                100.0 * (residual[endpoint]["mean"] / reference - 1.0)
                if reference != 0.0
                else None
            )
        safety_mean = all(
            effects[endpoint] is not None and effects[endpoint] <= 5.0
            for endpoint in ("worst_bus_peak_abs_hz", "max_abs_rocof_hz_s")
        )
        safety_worst = all(
            summaries["residual_td3_s49_b0p10"]["endpoints"][endpoint]["maximum"]
            <= 1.05 * summaries["droop_k10"]["endpoints"][endpoint]["maximum"]
            for endpoint in ("worst_bus_peak_abs_hz", "max_abs_rocof_hz_s")
        )
        action_mean = (
            effects["action_total_variation"] is not None
            and effects["action_total_variation"] <= 25.0
        )
        action_worst = (
            summaries["residual_td3_s49_b0p10"]["endpoints"][
                "action_total_variation"
            ]["maximum"]
            <= 1.25
            * summaries["droop_k10"]["endpoints"]["action_total_variation"]["maximum"]
        )
        saturation = (
            summaries["residual_td3_s49_b0p10"]["endpoints"][
                "action_saturation_fraction"
            ]["mean"]
            <= summaries["droop_k10"]["endpoints"]["action_saturation_fraction"]["mean"]
        )
    else:
        effects = {endpoint: None for endpoint in ENDPOINTS}
        safety_mean = safety_worst = action_mean = action_worst = saturation = False

    residual_failures = summaries["residual_td3_s49_b0p10"]["failure"]["count"]
    droop_failures = summaries["droop_k10"]["failure"]["count"]
    residual_settled = summaries["residual_td3_s49_b0p10"]["settling"]["count"]
    droop_settled = summaries["droop_k10"]["settling"]["count"]
    co_primary = all(
        effects[endpoint] is not None and effects[endpoint] < 0.0
        for endpoint in ("vsg_mean_iae_hz_s", "normalized_sync_loss_hz2")
    )
    guards = {
        "all_16_complete": all_complete,
        "both_co_primary_means_improve": co_primary,
        "residual_failure_not_higher": residual_failures <= droop_failures,
        "settling_not_lower": residual_settled >= droop_settled,
        "safety_mean_within_5pct": safety_mean,
        "safety_worst_within_5pct": safety_worst,
        "action_tv_mean_within_25pct": action_mean,
        "action_tv_worst_within_25pct": action_worst,
        "saturation_not_higher": saturation,
        "checkpoint_reload_exact": reload_deterministic,
    }
    classification = "GO" if all(guards.values()) else "NO-GO"
    return {
        "experiment": "r268_bounded_residual_pilot",
        "development_evidence_only": True,
        "scenarios": list(SCENARIOS),
        "controller_contract": contract,
        "controller_contract_sha256": contract_hash,
        "checkpoint_sha256": checkpoint_hashes,
        "evaluation_source_sha256": {
            "scripts/eval_bounded_residual_pilot.py": sha256_file(Path(__file__)),
            "src/andes_rl_kundur/evaluation/hybrid.py": sha256_file(
                ROOT / "src" / "andes_rl_kundur" / "evaluation" / "hybrid.py"
            ),
            "src/andes_rl_kundur/evaluation/physical_endpoints.py": sha256_file(
                ROOT
                / "src"
                / "andes_rl_kundur"
                / "evaluation"
                / "physical_endpoints.py"
            ),
        },
        "controllers": summaries,
        "residual_minus_droop_mean_percent": effects,
        "pilot_gate": {
            "classification": classification,
            "guards": guards,
            "reason": (
                "all prospective pilot gates passed"
                if classification == "GO"
                else "one or more physical, completion, safety, action, or reload gates failed"
            ),
        },
    }


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    gate = summary["pilot_gate"]
    lines = [
        "# R268 bounded residual pilot summary",
        "",
        f"- Classification: **{gate['classification']}**",
        f"- Reason: {gate['reason']}",
        "- Evidence level: development pilot; no interval or population claim.",
        "",
        "## Controller completion",
        "",
        "| Controller | Complete | Fail/incomplete | Settled |",
        "|---|---:|---:|---:|",
    ]
    for controller in CONTROLLERS:
        row = summary["controllers"][controller]
        lines.append(
            f"| {controller} | {row['complete_count']}/8 | "
            f"{row['failure']['count']}/8 | {row['settling']['count']}/8 |"
        )
    lines.extend(
        [
            "",
            "## Residual minus droop mean effects",
            "",
            "| Endpoint | Effect % |",
            "|---|---:|",
        ]
    )
    for endpoint, effect in summary["residual_minus_droop_mean_percent"].items():
        value = "unavailable" if effect is None else f"{effect:.6f}"
        lines.append(f"| {endpoint} | {value} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _run(args.ckpt_dir, args.out_dir)


if __name__ == "__main__":
    main()
