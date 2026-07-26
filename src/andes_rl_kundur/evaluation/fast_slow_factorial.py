"""R276 four-arm fast/slow factorial evaluation primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.fast_md_authority import (
    FAST_ENDPOINTS,
    SLOW_ENDPOINTS,
    FrozenCommonInertiaPulse,
    frozen_fast_md_contract,
)

ZERO_ARM = "zero"
SLOW_ARM = "slow"
FAST_ARM = "fast"
COMBINED_ARM = "combined"
ARMS = (ZERO_ARM, SLOW_ARM, FAST_ARM, COMBINED_ARM)
ENDPOINTS = (*FAST_ENDPOINTS, *SLOW_ENDPOINTS)


def run_fast_only_scenario(
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    seed: int = 42,
    steps: int = 300,
) -> dict[str, Any]:
    """Run the R276 fast-only arm on the identical zero-support storage DAE."""
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    fast_controller = FrozenCommonInertiaPulse()
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_frequency_hz = 60.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        obs = env.reset(delta_u=delta_u)
        nominal_frequency_hz = float(env.andes_nominal_frequency_hz)
        zero_power = np.zeros(env.bess_contract.device_count, dtype=float)
        for step in range(steps):
            md_actions = fast_controller(step, obs, env.N_AGENTS)
            obs, _, done, info = env.step(
                md_actions,
                bess_power_request_pu=zero_power,
            )
            if info.get("tds_failed"):
                tds_failed = True
                break
            physical_frequency = np.asarray(
                info["freq_hz_physical"],
                dtype=float,
            )
            traces.append(
                {
                    "step": step,
                    "t": float(info["time"]),
                    "freq_hz_physical": physical_frequency.tolist(),
                    "delta_f_physical_hz": (
                        physical_frequency - nominal_frequency_hz
                    ).tolist(),
                    "action_norm": [
                        np.asarray(md_actions[index], dtype=float).tolist()
                        for index in range(env.N_AGENTS)
                    ],
                    "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
                    "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
                    "bess_requested_power_system_pu": np.asarray(
                        info["bess_requested_power_system_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_commanded_power_system_pu": np.asarray(
                        info["bess_commanded_power_system_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_actual_power_system_pu": np.asarray(
                        info["bess_actual_power_system_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_soc": np.asarray(info["bess_soc"], dtype=float).tolist(),
                    "bess_bus_voltage_pu": np.asarray(
                        info["bess_bus_voltage_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_saturation_reasons": info["bess_saturation_reasons"],
                    "bess_charge_energy_mwh_total": np.asarray(
                        info["bess_charge_energy_mwh_total"],
                        dtype=float,
                    ).tolist(),
                    "bess_discharge_energy_mwh_total": np.asarray(
                        info["bess_discharge_energy_mwh_total"],
                        dtype=float,
                    ).tolist(),
                    "bess_constraint_violations": info[
                        "bess_constraint_violations"
                    ],
                }
            )
            if done:
                break
    finally:
        env.close()

    return {
        "experiment": "r276_fast_slow_factorial",
        "controller": FAST_ARM,
        "scenario": scenario_name,
        "delta_u": dict(delta_u),
        "env_version": "v4_plus_independent_esd1",
        "control_nominal_frequency_hz": float(env.FN),
        "andes_nominal_frequency_hz": nominal_frequency_hz,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": steps,
        "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": not tds_failed and len(traces) == steps,
        "traces": traces,
        "controller_config": {
            "bess_active_power_request": "zero",
            "fast_md": frozen_fast_md_contract(),
        },
        "seed": seed,
    }


def _finite_arm_arrays(
    endpoints_by_arm: Mapping[str, Mapping[str, Sequence[float]]],
) -> tuple[dict[str, dict[str, np.ndarray]], int]:
    if set(endpoints_by_arm) != set(ARMS):
        raise ValueError(f"factorial requires exactly the arms {ARMS}")
    common_endpoints = set.intersection(
        *(set(endpoints_by_arm[arm]) for arm in ARMS)
    )
    if not common_endpoints:
        raise ValueError("factorial arms have no common endpoint")
    arrays: dict[str, dict[str, np.ndarray]] = {arm: {} for arm in ARMS}
    sizes: set[int] = set()
    for arm in ARMS:
        for endpoint in common_endpoints:
            values = np.asarray(endpoints_by_arm[arm][endpoint], dtype=float)
            if (
                values.ndim != 1
                or values.size == 0
                or not np.all(np.isfinite(values))
            ):
                raise ValueError(f"{arm}/{endpoint} requires finite 1-D values")
            arrays[arm][endpoint] = values
            sizes.add(int(values.size))
    if len(sizes) != 1:
        raise ValueError("all factorial arms/endpoints require equal sample size")
    return arrays, sizes.pop()


def factorial_bootstrap(
    endpoints_by_arm: Mapping[str, Mapping[str, Sequence[float]]],
    *,
    seed: int,
    n_resamples: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Estimate the paired 2x2 interaction and combined-vs-best-single effect."""
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    arrays, sample_size = _finite_arm_arrays(endpoints_by_arm)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, sample_size, size=(n_resamples, sample_size))
    alpha = (1.0 - confidence) / 2.0
    quantiles = [alpha, 1.0 - alpha]
    results: dict[str, Any] = {}
    for endpoint in sorted(set.intersection(*(set(arrays[a]) for a in ARMS))):
        zero = arrays[ZERO_ARM][endpoint]
        slow = arrays[SLOW_ARM][endpoint]
        fast = arrays[FAST_ARM][endpoint]
        combined = arrays[COMBINED_ARM][endpoint]
        interaction_values = combined - slow - fast + zero
        interaction_boot = np.mean(interaction_values[indices], axis=1)
        zero_boot = np.mean(zero[indices], axis=1)
        zero_mean = float(np.mean(zero))
        if np.isclose(zero_mean, 0.0, rtol=0.0, atol=1e-15) or np.any(
            np.isclose(zero_boot, 0.0, rtol=0.0, atol=1e-15)
        ):
            raise ValueError(f"zero-arm reference is zero for {endpoint}")
        interaction_percent_boot = 100.0 * interaction_boot / zero_boot

        best_single = np.minimum(slow, fast)
        combined_boot = np.mean(combined[indices], axis=1)
        best_boot = np.mean(best_single[indices], axis=1)
        if np.any(np.isclose(best_boot, 0.0, rtol=0.0, atol=1e-15)):
            raise ValueError(f"best-single reference is zero for {endpoint}")
        relative_boot = 100.0 * (combined_boot / best_boot - 1.0)
        relative_point = 100.0 * (
            float(np.mean(combined)) / float(np.mean(best_single)) - 1.0
        )
        results[endpoint] = {
            "direction": "negative_is_beneficial",
            "interaction": {
                "formula": "combined - slow - fast + zero",
                "absolute_point": float(np.mean(interaction_values)),
                "absolute_percentile_95_interval": np.quantile(
                    interaction_boot,
                    quantiles,
                ).tolist(),
                "percent_of_zero_point": float(
                    100.0 * np.mean(interaction_values) / zero_mean
                ),
                "percent_of_zero_percentile_95_interval": np.quantile(
                    interaction_percent_boot,
                    quantiles,
                ).tolist(),
                "paired_values": interaction_values.tolist(),
            },
            "combined_minus_best_single": {
                "best_single_definition": "per-scenario min(slow, fast)",
                "absolute_mean_difference": {
                    "point": float(np.mean(combined - best_single)),
                    "percentile_95_interval": np.quantile(
                        combined_boot - best_boot,
                        quantiles,
                    ).tolist(),
                },
                "ratio_of_means_percent": {
                    "point": float(relative_point),
                    "percentile_95_interval": np.quantile(
                        relative_boot,
                        quantiles,
                    ).tolist(),
                },
                "paired_differences": (combined - best_single).tolist(),
            },
            "best_single_values": best_single.tolist(),
            "arm_means": {
                arm: float(np.mean(arrays[arm][endpoint]))
                for arm in ARMS
            },
        }
    return {
        "seed": seed,
        "n_resamples": n_resamples,
        "confidence": confidence,
        "sample_size": sample_size,
        "shared_index_resampling": True,
        "endpoints": results,
    }


def classify_fast_slow_factorial(
    *,
    factorial: dict[str, Any] | None,
    provenance_guard_pass: bool,
    completion_guard_pass: bool,
    action_storage_guard_pass: bool,
    tail_guard_pass: bool,
) -> dict[str, Any]:
    """Apply the prospectively registered R276 four-way gate."""
    guards = {
        "provenance_guard_pass": provenance_guard_pass,
        "completion_guard_pass": completion_guard_pass,
        "action_storage_guard_pass": action_storage_guard_pass,
        "tail_guard_pass": tail_guard_pass,
    }
    if factorial is None or not all(
        (
            provenance_guard_pass,
            completion_guard_pass,
            action_storage_guard_pass,
        )
    ):
        return {
            "classification": "INVALID",
            "reason": (
                "factorial evidence is unavailable"
                if factorial is None
                else "one or more provenance, completion, action, or storage guards failed"
            ),
            "guards": guards,
            "endpoint_decisions": {},
            "joint_clear_endpoints": [],
        }

    endpoint_decisions: dict[str, Any] = {}
    for endpoint in ENDPOINTS:
        evidence = factorial["endpoints"][endpoint]
        interaction = evidence["interaction"]
        best = evidence["combined_minus_best_single"]["ratio_of_means_percent"]
        interaction_clear = (
            float(interaction["percent_of_zero_point"]) <= -2.0
            and float(interaction["absolute_percentile_95_interval"][1]) < 0.0
        )
        best_clear = (
            float(best["point"]) <= -2.0
            and float(best["percentile_95_interval"][1]) < 0.0
        )
        no_harm = (
            float(interaction["percent_of_zero_point"]) <= 5.0
            and float(best["point"]) <= 5.0
        )
        endpoint_decisions[endpoint] = {
            "interaction_material": interaction_clear,
            "combined_beats_best_single": best_clear,
            "joint_clear": interaction_clear and best_clear,
            "no_harm": no_harm,
            "interaction_percent_of_zero": float(
                interaction["percent_of_zero_point"]
            ),
            "combined_vs_best_single_percent": float(best["point"]),
        }

    joint_clear = {
        endpoint
        for endpoint, decision in endpoint_decisions.items()
        if decision["joint_clear"]
    }
    no_harm = all(decision["no_harm"] for decision in endpoint_decisions.values())
    fast_clear = bool(joint_clear & set(FAST_ENDPOINTS))
    slow_clear = bool(joint_clear & set(SLOW_ENDPOINTS))
    guards.update(
        {
            "registered_endpoint_no_harm": no_harm,
            "fast_joint_endpoint_clear": fast_clear,
            "slow_joint_endpoint_clear": slow_clear,
        }
    )

    if not no_harm:
        classification = "ADDITIVE-ONLY"
        reason = "a registered endpoint exceeds the frozen +5% no-harm bound"
    elif fast_clear and slow_clear and tail_guard_pass:
        classification = "NONADDITIVE-POSITIVE"
        reason = "fast and slow endpoints both clear interaction and best-single gates"
    elif joint_clear and tail_guard_pass:
        classification = "NONADDITIVE-PARTIAL"
        reason = "only a subset clears both interaction and best-single gates"
    else:
        classification = "ADDITIVE-ONLY"
        reason = "no guarded material non-additive margin survives the joint gate"

    return {
        "classification": classification,
        "reason": reason,
        "guards": guards,
        "endpoint_decisions": endpoint_decisions,
        "joint_clear_endpoints": sorted(joint_clear),
    }
