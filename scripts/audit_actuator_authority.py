"""Audit equation-level and terminal-trace actuator authority for R271."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


ACTIVE_STEPS = 15
TERMINAL_STEPS = 25
MATERIALITY_PERCENT = 2.0
CONTROLLERS = ("common_M_pos", "common_D_pos", "common_D_neg")


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


def _sample_interval(record: dict[str, Any]) -> float:
    time = np.asarray([step["t"] for step in record["traces"]], dtype=float)
    intervals = np.diff(time)
    if time.size < 2 or np.any(~np.isfinite(intervals)) or np.any(intervals <= 0):
        raise ValueError("trace time must be finite and strictly increasing")
    return float(np.median(intervals))


def window_metrics(
    record: dict[str, Any],
    *,
    start: int,
    stop: int,
) -> dict[str, float | int]:
    """Return transparent physical mode and power metrics for one trace window."""

    traces = record.get("traces")
    if (
        record.get("completed") is not True
        or record.get("tds_failed") is True
        or not isinstance(traces, list)
        or len(traces) != 150
    ):
        raise ValueError("window audit requires a completed 150-step trace")
    selected = traces[start:stop]
    if not selected:
        raise ValueError("window selects no trace steps")
    delta_f = np.asarray(
        [step["delta_f_physical_hz"] for step in selected],
        dtype=float,
    )
    power = np.asarray([step["delta_P_es"] for step in selected], dtype=float)
    if (
        delta_f.ndim != 2
        or power.shape != delta_f.shape
        or not np.all(np.isfinite(delta_f))
        or not np.all(np.isfinite(power))
    ):
        raise ValueError("window requires finite rectangular frequency and power")
    common = np.mean(delta_f, axis=1)
    differential = delta_f - common[:, None]
    dt = _sample_interval(record)
    return {
        "n_steps": len(selected),
        "common_abs_mean_hz": float(np.mean(np.abs(common))),
        "common_iae_hz_s": float(np.sum(np.abs(common)) * dt),
        "differential_mse_hz2": float(np.mean(np.square(differential))),
        "worst_bus_peak_abs_hz": float(np.max(np.abs(delta_f))),
        "terminal_common_abs_hz": float(abs(common[-1])),
        "terminal_differential_mse_hz2": float(
            np.mean(np.square(differential[-1]))
        ),
        "vsg_power_mean_pu": float(np.mean(power)),
        "vsg_power_abs_mean_pu": float(np.mean(np.abs(power))),
    }


def percent_effect(candidate: float, baseline: float) -> float | None:
    if not np.isfinite(candidate) or not np.isfinite(baseline):
        raise ValueError("percent effect requires finite values")
    if baseline == 0.0:
        return None
    return 100.0 * (candidate / baseline - 1.0)


def _aggregate_window_effects(
    candidate_records: list[dict[str, Any]],
    baseline_records: list[dict[str, Any]],
    *,
    start: int,
    stop: int,
) -> dict[str, Any]:
    if len(candidate_records) != len(baseline_records) or not candidate_records:
        raise ValueError("candidate and baseline records must be paired and non-empty")
    candidate = [
        window_metrics(record, start=start, stop=stop)
        for record in candidate_records
    ]
    baseline = [
        window_metrics(record, start=start, stop=stop)
        for record in baseline_records
    ]
    metric_names = (
        "common_abs_mean_hz",
        "common_iae_hz_s",
        "differential_mse_hz2",
        "worst_bus_peak_abs_hz",
        "terminal_common_abs_hz",
        "terminal_differential_mse_hz2",
        "vsg_power_mean_pu",
        "vsg_power_abs_mean_pu",
    )
    candidate_means = {
        key: float(np.mean([row[key] for row in candidate]))
        for key in metric_names
    }
    baseline_means = {
        key: float(np.mean([row[key] for row in baseline]))
        for key in metric_names
    }
    effects = {
        key: percent_effect(candidate_means[key], baseline_means[key])
        for key in metric_names
    }
    return {
        "candidate_means": candidate_means,
        "baseline_means": baseline_means,
        "candidate_minus_baseline_percent": effects,
    }


def _source_audit() -> dict[str, Any]:
    base_path = ROOT / "src" / "andes_rl_kundur" / "env" / "andes" / "base_env.py"
    v4_path = (
        ROOT
        / "src"
        / "andes_rl_kundur"
        / "env"
        / "andes"
        / "andes_vsg_env_v4.py"
    )
    base_source = base_path.read_text(encoding="utf-8")
    v4_source = v4_path.read_text(encoding="utf-8")
    step_source = base_source[
        base_source.index("    def step(self, actions):") :
        base_source.index("    # ─── GENCLS 状态读取", base_source.index("    def step"))
    ]

    andes = importlib.import_module("andes")
    genbase = importlib.import_module("andes.models.synchronous.genbase")
    gencls = importlib.import_module("andes.models.synchronous.gencls")
    genbase_path = Path(genbase.__file__).resolve()
    gencls_path = Path(gencls.__file__).resolve()
    genbase_source = genbase_path.read_text(encoding="utf-8")
    gencls_source = gencls_path.read_text(encoding="utf-8")

    storage_state_pattern = re.compile(
        r"\b(soc|state_of_charge|energy_state|energy_capacity)\b",
        re.IGNORECASE,
    )
    guards = {
        "environment_action_is_delta_m_delta_d_only": (
            "actions[i] = [ΔM_norm, ΔD_norm]" in step_source
            and "shape (2,)" in step_source
        ),
        "step_sets_only_gencls_m_and_d": (
            'self.ss.GENCLS.set("M"' in step_source
            and 'self.ss.GENCLS.set("D"' in step_source
            and 'self.ss.GENCLS.set("tm"' not in step_source
            and 'self.ss.GENCLS.set("pref"' not in step_source
            and 'self.ss.GENCLS.set("p0"' not in step_source
        ),
        "measured_p_es_reads_electrical_output": (
            "self.ss.GENCLS.Pe.v[pos]" in base_source
        ),
        "andes_speed_equation_has_m_as_time_constant": (
            "e_str='ue * (tm - te - D * (omega - 1))'" in genbase_source
            and "t_const=self.M" in genbase_source
        ),
        "andes_fallback_power_setpoint_is_fixed_tm0": (
            "_setpoints = {'pref': 'tm0', 'vref': 'vf0'}" in genbase_source
            and "e_str='tm0 - tm'" in genbase_source
        ),
        "vsgs_are_pv_plus_gencls_proxies": (
            'ss.add("PV"' in v4_source
            and 'ss.add("GENCLS"' in v4_source
            and '"p0":   0.5' in v4_source
        ),
        "governors_attach_to_genrou_not_vsg_gencls": (
            "for syn_idx in ss.GENROU.idx.v:" in v4_source
            and "ss.IEEEG1.add" in v4_source
        ),
        "no_storage_energy_state_in_active_v4_path": (
            storage_state_pattern.search(base_source) is None
            and storage_state_pattern.search(v4_source) is None
        ),
        "m_absent_from_equilibrium_balance": (
            "tm - te - D * (omega - 1)" in genbase_source
        ),
        "gencls_adds_no_secondary_power_state": (
            "class GENCLSModel" in gencls_source
            and "State(" not in gencls_source
            and "pref" not in gencls_source
        ),
    }
    return {
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "equilibrium_interpretation": (
            "At domega/dt=0, M drops out: tm-te-D*(omega-1)=0. "
            "Finite D is proportional speed-error torque; exact zero error "
            "under nonzero sustained imbalance requires a changed power "
            "setpoint or an integral/secondary mechanism."
        ),
        "source_sha256": {
            "src/andes_rl_kundur/env/andes/base_env.py": sha256_file(base_path),
            "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py": sha256_file(
                v4_path
            ),
            str(genbase_path): sha256_file(genbase_path),
            str(gencls_path): sha256_file(gencls_path),
        },
        "installed_andes_paths": {
            "genbase": str(genbase_path),
            "gencls": str(gencls_path),
        },
        "guards": guards,
        "all_pass": all(guards.values()),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _trace_audit(
    *,
    r268_trace_root: Path,
    r270_trace_root: Path,
    r270_summary_path: Path,
) -> dict[str, Any]:
    summary = _load_json(r270_summary_path)
    scenarios = [row["scenario"] for row in summary["scenario_results"]]
    if len(scenarios) != 8:
        raise ValueError("R270 summary must contain exactly 8 scenarios")

    baseline_records: list[dict[str, Any]] = []
    selected_records: list[dict[str, Any]] = []
    controller_records: dict[str, list[dict[str, Any]]] = {
        name: [] for name in CONTROLLERS
    }
    parameter_checks: list[bool] = []
    per_scenario: list[dict[str, Any]] = []

    selections = {
        row["scenario"]: row["selected"] for row in summary["scenario_results"]
    }
    for scenario in scenarios:
        baseline = _load_json(r268_trace_root / scenario / "droop_k10.json")
        selected_name = selections[scenario]
        selected = (
            baseline
            if selected_name == "droop_k10"
            else _load_json(r270_trace_root / scenario / f"{selected_name}.json")
        )
        baseline_records.append(baseline)
        selected_records.append(selected)
        loaded: dict[str, dict[str, Any]] = {}
        for controller in CONTROLLERS:
            record = _load_json(r270_trace_root / scenario / f"{controller}.json")
            controller_records[controller].append(record)
            loaded[controller] = record

        common_m = loaded["common_M_pos"]["traces"]
        active_m = np.asarray([step["M_es"] for step in common_m[:ACTIVE_STEPS]])
        post_m = np.asarray([step["M_es"] for step in common_m[ACTIVE_STEPS:]])
        parameter_checks.append(
            bool(
                np.allclose(active_m, 350.0, rtol=0.0, atol=1e-9)
                and np.allclose(post_m, 200.0, rtol=0.0, atol=1e-9)
            )
        )
        per_scenario.append(
            {
                "scenario": scenario,
                "selected": selected_name,
                "common_M_pos_parameter": {
                    "active_M_unique": np.unique(
                        np.round(active_m, decimals=9)
                    ).tolist(),
                    "post_window_M_unique": np.unique(
                        np.round(post_m, decimals=9)
                    ).tolist(),
                },
                "selected_terminal": window_metrics(
                    selected,
                    start=-TERMINAL_STEPS,
                    stop=150,
                ),
                "droop_terminal": window_metrics(
                    baseline,
                    start=-TERMINAL_STEPS,
                    stop=150,
                ),
            }
        )

    selected_active = _aggregate_window_effects(
        selected_records,
        baseline_records,
        start=0,
        stop=ACTIVE_STEPS,
    )
    selected_terminal = _aggregate_window_effects(
        selected_records,
        baseline_records,
        start=-TERMINAL_STEPS,
        stop=150,
    )
    controllers: dict[str, Any] = {}
    for controller, records in controller_records.items():
        controllers[controller] = {
            "active_window": _aggregate_window_effects(
                records,
                baseline_records,
                start=0,
                stop=ACTIVE_STEPS,
            ),
            "terminal_window": _aggregate_window_effects(
                records,
                baseline_records,
                start=-TERMINAL_STEPS,
                stop=150,
            ),
        }

    full_effects = summary["library_oracle_minus_droop_effects_percent"]
    terminal_common_effect = selected_terminal[
        "candidate_minus_baseline_percent"
    ]["common_abs_mean_hz"]
    terminal_sample_effect = selected_terminal[
        "candidate_minus_baseline_percent"
    ]["terminal_common_abs_hz"]
    guards = {
        "r270_full_iae_materiality_still_fails": (
            float(full_effects["vsg_mean_iae_hz_s"]) > -MATERIALITY_PERCENT
        ),
        "r270_differential_or_safety_gain_is_material": (
            float(full_effects["normalized_sync_loss_hz2"])
            <= -MATERIALITY_PERCENT
            or float(full_effects["max_abs_rocof_hz_s"])
            <= -MATERIALITY_PERCENT
        ),
        "selected_terminal_common_window_below_2pct_materiality": (
            terminal_common_effect is not None
            and terminal_common_effect > -MATERIALITY_PERCENT
        ),
        "selected_terminal_common_sample_below_2pct_materiality": (
            terminal_sample_effect is not None
            and terminal_sample_effect > -MATERIALITY_PERCENT
        ),
        "scheduled_common_m_returns_exactly_to_baseline": all(
            parameter_checks
        ),
        "all_expected_traces_present": (
            len(baseline_records) == 8
            and len(selected_records) == 8
            and all(len(records) == 8 for records in controller_records.values())
        ),
    }
    return {
        "windows": {
            "active": [0, ACTIVE_STEPS],
            "terminal": [-TERMINAL_STEPS, 150],
            "sample_interval_s": 0.2,
        },
        "r270_full_horizon_effects_percent": full_effects,
        "selected_oracle": {
            "active_window": selected_active,
            "terminal_window": selected_terminal,
        },
        "fixed_controllers": controllers,
        "per_scenario": per_scenario,
        "guards": guards,
        "all_pass": all(guards.values()),
    }


def _audit(
    *,
    r268_trace_root: Path,
    r270_trace_root: Path,
    r270_summary_path: Path,
) -> dict[str, Any]:
    source = _source_audit()
    trace = _trace_audit(
        r268_trace_root=r268_trace_root,
        r270_trace_root=r270_trace_root,
        r270_summary_path=r270_summary_path,
    )
    gates = {
        "source_and_equilibrium_checks_pass": source["all_pass"],
        "existing_trace_checks_pass": trace["all_pass"],
    }
    return {
        "experiment": "r271_actuator_authority_audit",
        "classification": (
            "MODEL-CORRECTION-REQUIRED"
            if all(gates.values())
            else "EXISTING-AUTHORITY"
        ),
        "development_structural_evidence_only": True,
        "new_andes_trajectories": 0,
        "new_training_runs": 0,
        "materiality_percent": MATERIALITY_PERCENT,
        "source_audit": source,
        "trace_audit": trace,
        "gate": gates,
        "audit_source_sha256": sha256_file(Path(__file__)),
        "input_sha256": {
            "r270_summary": sha256_file(r270_summary_path),
        },
    }


def _write_markdown(path: Path, audit: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    source = audit["source_audit"]
    trace = audit["trace_audit"]
    full = trace["r270_full_horizon_effects_percent"]
    terminal = trace["selected_oracle"]["terminal_window"][
        "candidate_minus_baseline_percent"
    ]
    lines = [
        "# R271 actuator-authority audit",
        "",
        f"- Classification: **{audit['classification']}**",
        "- New ANDES trajectories: 0",
        "- New training runs: 0",
        f"- ANDES version: `{source['andes_version']}`",
        f"- Source/equilibrium checks: {sum(source['guards'].values())}/{len(source['guards'])}",
        f"- Existing-trace checks: {sum(trace['guards'].values())}/{len(trace['guards'])}",
        "",
        "## Key mode separation",
        "",
        "| Quantity | Effect vs droop |",
        "|---|---:|",
        f"| full-horizon IAE | {full['vsg_mean_iae_hz_s']:+.6f}% |",
        (
            "| full-horizon synchronization loss | "
            f"{full['normalized_sync_loss_hz2']:+.6f}% |"
        ),
        (
            "| terminal-window common absolute mean | "
            f"{terminal['common_abs_mean_hz']:+.6f}% |"
        ),
        (
            "| terminal-sample common absolute frequency | "
            f"{terminal['terminal_common_abs_hz']:+.6f}% |"
        ),
        (
            "| terminal-window differential MSE | "
            f"{terminal['differential_mse_hz2']:+.6f}% |"
        ),
        "",
        "## Structural result",
        "",
        source["equilibrium_interpretation"],
    ]
    temporary = Path(f"{path}.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--r268-trace-root",
        type=Path,
        default=ROOT / "results" / "r268_residual_pilot_eval" / "traces",
    )
    parser.add_argument(
        "--r270-trace-root",
        type=Path,
        default=ROOT / "results" / "r270_attainable_oracle" / "traces",
    )
    parser.add_argument(
        "--r270-summary",
        type=Path,
        default=(
            ROOT
            / "results"
            / "r270_attainable_oracle"
            / "attainable_oracle_summary.json"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results" / "r271_actuator_authority_audit",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.out_dir.exists():
        raise FileExistsError(f"refusing to reuse output directory: {args.out_dir}")
    audit = _audit(
        r268_trace_root=args.r268_trace_root,
        r270_trace_root=args.r270_trace_root,
        r270_summary_path=args.r270_summary,
    )
    args.out_dir.mkdir(parents=True)
    _write_json_atomic(args.out_dir / "actuator_authority_audit.json", audit)
    _write_markdown(args.out_dir / "actuator_authority_audit.md", audit)
    print(f"[actuator-audit] classification={audit['classification']}")
    print(
        "[actuator-audit] source="
        f"{sum(audit['source_audit']['guards'].values())}/"
        f"{len(audit['source_audit']['guards'])} "
        "trace="
        f"{sum(audit['trace_audit']['guards'].values())}/"
        f"{len(audit['trace_audit']['guards'])}"
    )


if __name__ == "__main__":
    main()
