"""Audit the R269 residual objective on synthetic cases and R268 traces."""

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

from andes_rl_kundur.evaluation.physical_endpoints import (  # noqa: E402
    summarise_physical_trace,
)
from andes_rl_kundur.evaluation.residual_objective import (  # noqa: E402
    ResidualObjectiveConfig,
    frequency_mode_terms,
    residual_action_terms,
    summarise_frequency_objective,
    summarise_residual_objective,
)

K_DROOP = 10.0
RESIDUAL_SCALE = 0.10
CONTROLLERS = ("droop_k10", "residual_td3_s49_b0p10")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_interval(record: dict[str, Any]) -> float:
    time = np.asarray([step["t"] for step in record["traces"]], dtype=float)
    intervals = np.diff(time)
    if time.size < 2 or np.any(~np.isfinite(intervals)) or np.any(intervals <= 0):
        raise ValueError("trace time must be finite and strictly increasing")
    return float(np.median(intervals))


def _frequency_summary(
    record: dict[str, Any],
    config: ResidualObjectiveConfig,
) -> dict[str, float | int]:
    values = np.asarray(
        [step["delta_f_physical_hz"] for step in record["traces"]],
        dtype=float,
    )
    return summarise_frequency_objective(
        values,
        sample_interval_s=_sample_interval(record),
        config=config,
    )


def _reconstruct_residual_actions(
    record: dict[str, Any],
    *,
    k_droop: float,
    residual_scale: float,
) -> tuple[np.ndarray, float]:
    """Recover steps 1..N-1 raw residuals from the immutable R268 trace.

    The action at step ``t`` used the observation returned by step ``t-1``.
    V4 observation slot 1 is ``delta_f_legacy_hz * 2*pi / 3``.  Step zero is
    intentionally excluded because the reset observation was not recorded.
    R268 telemetry establishes that no executed component was clipped.
    """

    if residual_scale <= 0.0:
        raise ValueError("residual_scale must be positive for reconstruction")
    traces = record["traces"]
    executed = np.asarray(
        [step["action_norm"] for step in traces],
        dtype=float,
    )
    previous_legacy_delta_f = np.asarray(
        [step["delta_f_es"] for step in traces[:-1]],
        dtype=float,
    )
    if executed.ndim != 3 or executed.shape[1:] != (4, 2):
        raise ValueError("R268 executed actions must have shape [time, 4, 2]")
    if previous_legacy_delta_f.shape != (executed.shape[0] - 1, 4):
        raise ValueError("R268 legacy frequency trace shape is inconsistent")

    prior = np.zeros_like(executed[1:])
    prior[:, :, 1] = np.clip(
        k_droop * np.abs(previous_legacy_delta_f * (2.0 * np.pi) / 3.0),
        0.0,
        1.0,
    )
    residual = (executed[1:] - prior) / residual_scale
    reconstructed = np.clip(
        prior + residual_scale * residual,
        -1.0,
        1.0,
    )
    max_error = float(np.max(np.abs(reconstructed - executed[1:])))
    return residual, max_error


def _sign(value: float, *, tolerance: float = 1e-12) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def _synthetic_checks(config: ResidualObjectiveConfig) -> dict[str, Any]:
    uniform = frequency_mode_terms([0.05] * 4, config=config)
    split = frequency_mode_terms(
        [0.05, -0.05, 0.05, -0.05],
        config=config,
    )
    zeros = np.zeros((4, 2), dtype=float)
    opposing = np.asarray(
        [[1.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [-1.0, 0.0]],
        dtype=float,
    )
    constant = residual_action_terms(
        opposing,
        previous_residual_actions=opposing,
        config=config,
    )
    switched = residual_action_terms(
        -opposing,
        previous_residual_actions=opposing,
        config=config,
    )
    zero_terms = residual_action_terms(zeros, config=config)

    rejection_checks: dict[str, bool] = {}
    invalid_cases = {
        "reject_nonfinite_frequency": lambda: frequency_mode_terms(
            [0.0, float("nan")],
            config=config,
        ),
        "reject_wrong_residual_shape": lambda: residual_action_terms(
            [0.0, 0.0],
            config=config,
        ),
        "reject_out_of_bound_residual": lambda: residual_action_terms(
            [[1.01, 0.0], [0.0, 0.0]],
            config=config,
        ),
    }
    for name, call in invalid_cases.items():
        try:
            call()
        except ValueError:
            rejection_checks[name] = True
        else:
            rejection_checks[name] = False

    guards = {
        "uniform_common_is_one": bool(np.isclose(uniform["common"], 1.0)),
        "uniform_differential_is_zero": bool(
            np.isclose(uniform["differential"], 0.0)
        ),
        "split_common_is_zero": bool(np.isclose(split["common"], 0.0)),
        "split_differential_is_one": bool(
            np.isclose(split["differential"], 1.0)
        ),
        "zero_residual_cost_is_zero": bool(
            np.isclose(zero_terms["residual_effort"], 0.0)
            and np.isclose(zero_terms["residual_variation"], 0.0)
        ),
        "opposing_residual_is_charged": bool(
            residual_action_terms(opposing, config=config)["residual_effort"] > 0.0
            and np.allclose(np.mean(opposing, axis=0), 0.0)
        ),
        "constant_residual_variation_is_zero": bool(
            np.isclose(constant["residual_variation"], 0.0)
        ),
        "sign_switch_variation_is_positive": bool(
            switched["residual_variation"] > 0.0
        ),
        **rejection_checks,
    }
    return {
        "values": {
            "uniform": uniform,
            "zero_mean_split": split,
            "zero_residual": zero_terms,
            "opposing_constant": constant,
            "opposing_sign_switch": switched,
        },
        "guards": guards,
        "all_pass": all(guards.values()),
    }


def _source_diagnosis(
    training_log: dict[str, Any],
    *,
    base_env_path: Path,
    adapter_path: Path,
) -> dict[str, Any]:
    env_config = training_log["env_config"]
    base_source = base_env_path.read_text(encoding="utf-8")
    adapter_source = adapter_path.read_text(encoding="utf-8")

    base = np.asarray([0.02, -0.01, 0.03, -0.04], dtype=float)
    shifted = base + 0.20

    def legacy_sync(values: np.ndarray) -> float:
        return float(np.mean(np.square(values - np.mean(values))))

    opposing = np.asarray(
        [[1.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [-1.0, 0.0]],
        dtype=float,
    )
    old_average_then_square = float(np.sum(np.square(np.mean(opposing, axis=0))))
    guards = {
        "r268_phi_abs_is_zero": float(env_config["phi_abs"]) == 0.0,
        "r268_action_average_scope_is_global": env_config["r_avg_scope"] == "global",
        "legacy_sync_is_uniform_shift_invariant": bool(
            np.isclose(legacy_sync(base), legacy_sync(shifted))
        ),
        "old_average_penalty_allows_opposing_cancellation": bool(
            np.isclose(old_average_then_square, 0.0)
        ),
        "base_reward_contains_phi_abs_gate": "self.PHI_ABS * r_abs" in base_source,
        "base_reward_uses_global_action_average": (
            "global_ah_avg" in base_source and "global_ad_avg" in base_source
        ),
        "adapter_delegates_base_rewards_unchanged": (
            "next_obs, rewards, done, info = self._env.step(executed)"
            in adapter_source
            and "return next_obs, rewards, done, enriched" in adapter_source
        ),
    }
    return {
        "r268_env_config": {
            "phi_abs": float(env_config["phi_abs"]),
            "r_avg_scope": env_config["r_avg_scope"],
            "phi_f": float(env_config["phi_f"]),
            "phi_h": float(env_config["phi_h"]),
            "phi_d": float(env_config["phi_d"]),
        },
        "legacy_sync_base": legacy_sync(base),
        "legacy_sync_uniform_shifted": legacy_sync(shifted),
        "old_opposing_average_then_square": old_average_then_square,
        "guards": guards,
        "all_pass": all(guards.values()),
    }


def _audit_archived_traces(
    trace_root: Path,
    *,
    config: ResidualObjectiveConfig,
) -> dict[str, Any]:
    scenario_dirs = sorted(path for path in trace_root.iterdir() if path.is_dir())
    if len(scenario_dirs) != 8:
        raise ValueError(f"expected 8 R268 scenario directories, got {len(scenario_dirs)}")

    scenario_rows: list[dict[str, Any]] = []
    common_identity_errors: list[float] = []
    differential_identity_errors: list[float] = []
    common_order_checks: list[bool] = []
    differential_order_checks: list[bool] = []
    residual_bound_values: list[float] = []
    reconstruction_errors: list[float] = []
    means: dict[str, dict[str, list[float]]] = {
        controller: {
            "vsg_mean_iae_hz_s": [],
            "normalized_sync_loss_hz2": [],
            "frequency_scalar_mean": [],
            "cum_rf_total": [],
        }
        for controller in CONTROLLERS
    }

    for scenario_dir in scenario_dirs:
        controller_rows: dict[str, Any] = {}
        records: dict[str, dict[str, Any]] = {}
        for controller in CONTROLLERS:
            path = scenario_dir / f"{controller}.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            records[controller] = record
            physical = summarise_physical_trace(record)
            frequency = _frequency_summary(record, config)
            common_identity_errors.append(
                abs(
                    float(frequency["vsg_mean_iae_hz_s"])
                    - float(physical["vsg_mean_iae_hz_s"])
                )
            )
            differential_identity_errors.append(
                abs(
                    float(frequency["normalized_sync_loss_hz2"])
                    - float(physical["normalized_sync_loss_hz2"])
                )
            )
            for key in means[controller]:
                if key == "cum_rf_total":
                    means[controller][key].append(float(record[key]))
                else:
                    means[controller][key].append(float(frequency[key]))
            controller_rows[controller] = {
                "physical": {
                    "vsg_mean_iae_hz_s": physical["vsg_mean_iae_hz_s"],
                    "normalized_sync_loss_hz2": physical[
                        "normalized_sync_loss_hz2"
                    ],
                },
                "frequency_objective": frequency,
                "cum_rf_total": float(record["cum_rf_total"]),
            }

        droop_physical = controller_rows["droop_k10"]["physical"]
        residual_physical = controller_rows["residual_td3_s49_b0p10"]["physical"]
        droop_frequency = controller_rows["droop_k10"]["frequency_objective"]
        residual_frequency = controller_rows["residual_td3_s49_b0p10"][
            "frequency_objective"
        ]
        common_order_checks.append(
            _sign(
                float(residual_physical["vsg_mean_iae_hz_s"])
                - float(droop_physical["vsg_mean_iae_hz_s"])
            )
            == _sign(
                float(residual_frequency["common_normalized_mean"])
                - float(droop_frequency["common_normalized_mean"])
            )
        )
        differential_order_checks.append(
            _sign(
                float(residual_physical["normalized_sync_loss_hz2"])
                - float(droop_physical["normalized_sync_loss_hz2"])
            )
            == _sign(
                float(residual_frequency["differential_normalized_mean"])
                - float(droop_frequency["differential_normalized_mean"])
            )
        )

        residual_record = records["residual_td3_s49_b0p10"]
        if (
            float(
                residual_record["residual_telemetry"][
                    "executed_clipped_component_fraction"
                ]
            )
            != 0.0
        ):
            raise ValueError("R268 residual reconstruction requires zero execution clipping")
        residual_actions, reconstruction_error = _reconstruct_residual_actions(
            residual_record,
            k_droop=K_DROOP,
            residual_scale=RESIDUAL_SCALE,
        )
        residual_bound_values.extend(np.abs(residual_actions).ravel().tolist())
        reconstruction_errors.append(reconstruction_error)
        residual_summary = summarise_residual_objective(
            residual_actions,
            config=config,
        )
        zero_summary = summarise_residual_objective(
            np.zeros_like(residual_actions),
            config=config,
        )
        controller_rows["residual_td3_s49_b0p10"][
            "reconstructed_residual_objective_steps_1_to_149"
        ] = residual_summary
        controller_rows["droop_k10"][
            "defined_zero_residual_objective_steps_1_to_149"
        ] = zero_summary
        scenario_rows.append(
            {
                "scenario": scenario_dir.name,
                "controllers": controller_rows,
                "residual_reconstruction": {
                    "raw_abs_max": float(np.max(np.abs(residual_actions))),
                    "executed_max_abs_error": reconstruction_error,
                    "step_zero_excluded": True,
                },
            }
        )

    aggregate: dict[str, Any] = {}
    for controller, values_by_metric in means.items():
        aggregate[controller] = {
            key: float(np.mean(values))
            for key, values in values_by_metric.items()
        }

    effects: dict[str, float] = {}
    for key in (
        "vsg_mean_iae_hz_s",
        "normalized_sync_loss_hz2",
        "frequency_scalar_mean",
    ):
        reference = aggregate["droop_k10"][key]
        effects[key] = (
            100.0
            * (
                aggregate["residual_td3_s49_b0p10"][key]
                / reference
                - 1.0
            )
        )
    effects["cum_rf_total_absolute_delta"] = (
        aggregate["residual_td3_s49_b0p10"]["cum_rf_total"]
        - aggregate["droop_k10"]["cum_rf_total"]
    )

    max_common_error = max(common_identity_errors)
    max_differential_error = max(differential_identity_errors)
    max_raw_abs = max(residual_bound_values)
    max_reconstruction_error = max(reconstruction_errors)
    guards = {
        "all_16_traces_present_and_complete": all(
            row["controllers"][controller]["frequency_objective"]["n_steps"] == 150
            for row in scenario_rows
            for controller in CONTROLLERS
        ),
        "common_identity_exact": max_common_error <= 1e-12,
        "differential_identity_exact": max_differential_error <= 1e-12,
        "common_pair_order_preserved_all_8": all(common_order_checks),
        "differential_pair_order_preserved_all_8": all(
            differential_order_checks
        ),
        "reconstructed_residual_within_bounds": max_raw_abs <= 1.0 + 1e-7,
        "executed_action_reconstruction_within_1e_5": (
            max_reconstruction_error <= 1e-5
        ),
        "droop_residual_cost_is_zero": all(
            np.isclose(
                row["controllers"]["droop_k10"][
                    "defined_zero_residual_objective_steps_1_to_149"
                ]["residual_scalar_mean"],
                0.0,
            )
            for row in scenario_rows
        ),
        "r268_both_physical_mean_directions_remain_worse": (
            effects["vsg_mean_iae_hz_s"] > 0.0
            and effects["normalized_sync_loss_hz2"] > 0.0
        ),
    }
    return {
        "scenarios": scenario_rows,
        "aggregate_means": aggregate,
        "residual_minus_droop_effects_percent": effects,
        "identity_and_reconstruction": {
            "max_common_endpoint_abs_error": max_common_error,
            "max_differential_endpoint_abs_error": max_differential_error,
            "max_reconstructed_raw_residual_abs": max_raw_abs,
            "max_executed_action_reconstruction_abs_error": (
                max_reconstruction_error
            ),
            "common_pair_improve_count": sum(
                float(
                    row["controllers"]["residual_td3_s49_b0p10"]["physical"][
                        "vsg_mean_iae_hz_s"
                    ]
                )
                < float(
                    row["controllers"]["droop_k10"]["physical"][
                        "vsg_mean_iae_hz_s"
                    ]
                )
                for row in scenario_rows
            ),
            "differential_pair_improve_count": sum(
                float(
                    row["controllers"]["residual_td3_s49_b0p10"]["physical"][
                        "normalized_sync_loss_hz2"
                    ]
                )
                < float(
                    row["controllers"]["droop_k10"]["physical"][
                        "normalized_sync_loss_hz2"
                    ]
                )
                for row in scenario_rows
            ),
        },
        "guards": guards,
        "all_pass": all(guards.values()),
    }


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


def _write_markdown_atomic(path: Path, audit: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    source = audit["source_diagnosis"]
    synthetic = audit["synthetic_checks"]
    archived = audit["archived_trace_checks"]
    effects = archived["residual_minus_droop_effects_percent"]
    identity = archived["identity_and_reconstruction"]
    lines = [
        "# R269 residual objective audit",
        "",
        f"- Classification: **{audit['classification']}**",
        "- Evidence: synthetic checks plus immutable R268 traces; no new ANDES or training.",
        f"- R268 PHI_ABS: `{source['r268_env_config']['phi_abs']}`",
        f"- Source checks: {sum(source['guards'].values())}/{len(source['guards'])}",
        f"- Synthetic checks: {sum(synthetic['guards'].values())}/{len(synthetic['guards'])}",
        f"- Archived checks: {sum(archived['guards'].values())}/{len(archived['guards'])}",
        "",
        "## R268 physical direction reproduction",
        "",
        "| Quantity | Residual minus droop |",
        "|---|---:|",
        f"| VSG-mean IAE | {effects['vsg_mean_iae_hz_s']:+.6f}% |",
        (
            "| normalized synchronization loss | "
            f"{effects['normalized_sync_loss_hz2']:+.6f}% |"
        ),
        f"| fixed physical scalar | {effects['frequency_scalar_mean']:+.6f}% |",
        (
            "| old cum_rf mean absolute delta | "
            f"{effects['cum_rf_total_absolute_delta']:+.9g} |"
        ),
        "",
        "## Identity and reconstruction",
        "",
        (
            "- Maximum common-endpoint identity error: "
            f"`{identity['max_common_endpoint_abs_error']:.3g}`."
        ),
        (
            "- Maximum differential-endpoint identity error: "
            f"`{identity['max_differential_endpoint_abs_error']:.3g}`."
        ),
        (
            "- Maximum reconstructed raw residual magnitude: "
            f"`{identity['max_reconstructed_raw_residual_abs']:.6f}`."
        ),
        (
            "- Maximum executed-action reconstruction error: "
            f"`{identity['max_executed_action_reconstruction_abs_error']:.3g}`."
        ),
        (
            "- Paired improvement counts: common "
            f"{identity['common_pair_improve_count']}/8, differential "
            f"{identity['differential_pair_improve_count']}/8."
        ),
    ]
    temporary = Path(f"{path}.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def _audit(
    *,
    trace_root: Path,
    training_log_path: Path,
) -> dict[str, Any]:
    config = ResidualObjectiveConfig()
    training_log = json.loads(training_log_path.read_text(encoding="utf-8"))
    base_env_path = ROOT / "src" / "andes_rl_kundur" / "env" / "andes" / "base_env.py"
    adapter_path = (
        ROOT / "src" / "andes_rl_kundur" / "env" / "andes" / "residual_adapter.py"
    )
    source = _source_diagnosis(
        training_log,
        base_env_path=base_env_path,
        adapter_path=adapter_path,
    )
    synthetic = _synthetic_checks(config)
    archived = _audit_archived_traces(trace_root, config=config)
    guards = {
        "source_diagnosis_pass": source["all_pass"],
        "synthetic_checks_pass": synthetic["all_pass"],
        "archived_trace_checks_pass": archived["all_pass"],
    }
    classification = "PASS" if all(guards.values()) else "FAIL"
    return {
        "experiment": "r269_residual_objective_audit",
        "classification": classification,
        "development_evidence_only": True,
        "new_andes_trajectories": 0,
        "new_training_runs": 0,
        "objective_contract": {
            "terms": {
                "common": "abs(mean(delta_f_physical_hz)) / 0.05",
                "differential": (
                    "mean((delta_f_physical_hz - mean)^2) / 0.05^2"
                ),
                "residual_effort": "mean_agent(sum_component(abs(r))) / 2",
                "residual_variation": (
                    "mean_agent(sum_component(abs(r-r_prev))) / 4"
                ),
            },
            "scalar": "unweighted sum of the four dimensionless terms",
            "first_step_variation": 0.0,
            "config": config.to_dict(),
        },
        "source_sha256": {
            "scripts/audit_residual_objective.py": sha256_file(Path(__file__)),
            "src/andes_rl_kundur/evaluation/residual_objective.py": sha256_file(
                ROOT
                / "src"
                / "andes_rl_kundur"
                / "evaluation"
                / "residual_objective.py"
            ),
            "src/andes_rl_kundur/evaluation/physical_endpoints.py": sha256_file(
                ROOT
                / "src"
                / "andes_rl_kundur"
                / "evaluation"
                / "physical_endpoints.py"
            ),
            "src/andes_rl_kundur/env/andes/base_env.py": sha256_file(
                base_env_path
            ),
            "src/andes_rl_kundur/env/andes/residual_adapter.py": sha256_file(
                adapter_path
            ),
            "r268_training_log.json": sha256_file(training_log_path),
        },
        "source_diagnosis": source,
        "synthetic_checks": synthetic,
        "archived_trace_checks": archived,
        "gate": guards,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-root",
        type=Path,
        default=ROOT / "results" / "r268_residual_pilot_eval" / "traces",
    )
    parser.add_argument(
        "--training-log",
        type=Path,
        default=ROOT / "results" / "r268_residual_td3_s49" / "training_log.json",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results" / "r269_objective_audit",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.out_dir.exists():
        raise FileExistsError(f"refusing to reuse output directory: {args.out_dir}")
    audit = _audit(
        trace_root=args.trace_root,
        training_log_path=args.training_log,
    )
    args.out_dir.mkdir(parents=True)
    _write_json_atomic(args.out_dir / "objective_audit.json", audit)
    _write_markdown_atomic(args.out_dir / "objective_audit.md", audit)
    print(f"[objective-audit] classification={audit['classification']}")
    print(
        "[objective-audit] source="
        f"{sum(audit['source_diagnosis']['guards'].values())}/"
        f"{len(audit['source_diagnosis']['guards'])} "
        "synthetic="
        f"{sum(audit['synthetic_checks']['guards'].values())}/"
        f"{len(audit['synthetic_checks']['guards'])} "
        "archived="
        f"{sum(audit['archived_trace_checks']['guards'].values())}/"
        f"{len(audit['archived_trace_checks']['guards'])}"
    )


if __name__ == "__main__":
    main()
