"""R478 Yang-line M/D base-semantic gate.

This question-specific probe executes exactly four registered components:
two zero-action disturbances, one bounded nonzero control step with five ANDES
substeps and target/readback checks, and one repeated-reset check. It returns a
non-claim-bearing classification for the R478 rehearsal/report writer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from andes_rl_kundur.env.andes.md_convention import system_to_device
from andes_rl_kundur.probes.andes_common.paper_constants import LS1_DELTA_U
from andes_rl_kundur.probes.md_revalidation import (
    run_zero_action_bank,
    summarize_zero_action_bank,
)

NONZERO_ACTION = (0.5, -0.25)
REQUIRED_SUBSTEPS = 5


def _card_values(parameter_card: Mapping[str, Any]) -> dict[str, float]:
    device = parameter_card["devices"]["vsg_1_to_4"]
    action_map = parameter_card["action_map"]
    clamps = parameter_card["clamps"]
    return {
        "system_base_mva": float(parameter_card["system_base_mva"]),
        "device_mva": float(device["sn_mva"]),
        "m0_device": float(device["m_device_s"]),
        "d0_device": float(device["d_device"]),
        "positive_slope": float(action_map["positive_slope"]),
        "negative_slope": float(action_map["negative_slope"]),
        "m_min_device": float(clamps["m_min_device"]),
        "d_min_device": float(clamps["d_min_device"]),
        "n_substeps": int(parameter_card["slew"]["n_substeps"]),
    }


def _runtime_device_md(
    env: Any, *, parameter_card: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    values = _card_values(parameter_card)
    runtime_m = np.asarray(
        [env.ss.GENCLS.M.v[position] for position in env._vsg_pos],
        dtype=float,
    )
    runtime_d = np.asarray(
        [env.ss.GENCLS.D.v[position] for position in env._vsg_pos],
        dtype=float,
    )
    return (
        system_to_device(
            runtime_m,
            device_mva=values["device_mva"],
            system_mva=values["system_base_mva"],
        ),
        system_to_device(
            runtime_d,
            device_mva=values["device_mva"],
            system_mva=values["system_base_mva"],
        ),
    )


def _nonzero_readback(
    env_class: type, *, parameter_card: Mapping[str, Any]
) -> dict[str, Any]:
    values = _card_values(parameter_card)
    env = env_class(random_disturbance=False, comm_fail_prob=0.0)
    try:
        env.seed(42)
        env.reset(delta_u=LS1_DELTA_U)
        if int(env.N_SUBSTEPS) != int(values["n_substeps"]):
            raise RuntimeError(
                f"semantic gate requires {values['n_substeps']} substeps, "
                f"got {env.N_SUBSTEPS}"
            )
        actions = {
            actor: np.asarray(NONZERO_ACTION, dtype=np.float32)
            for actor in range(env.N_AGENTS)
        }
        _observation, _reward, _done, info = env.step(actions)
        runtime_m_dev, runtime_d_dev = _runtime_device_md(
            env, parameter_card=parameter_card
        )
        reported_m = np.asarray(info["M_es"], dtype=float)
        reported_d = np.asarray(info["D_es"], dtype=float)
        target_m = np.asarray(info["M_target_es"], dtype=float)
        target_d = np.asarray(info["D_target_es"], dtype=float)
        expected_delta_m = NONZERO_ACTION[0] * values["positive_slope"]
        expected_delta_d = NONZERO_ACTION[1] * values["negative_slope"]
        expected_m = np.full(
            env.N_AGENTS,
            max(
                values["m0_device"] + expected_delta_m,
                values["m_min_device"],
            ),
        )
        expected_d = np.full(
            env.N_AGENTS,
            max(
                values["d0_device"] + expected_delta_d,
                values["d_min_device"],
            ),
        )
        checks = {
            "five_substeps": int(env.N_SUBSTEPS) == REQUIRED_SUBSTEPS,
            "environment_card_matches_frozen_card": bool(
                np.allclose(np.asarray(env.M0, dtype=float), values["m0_device"])
                and np.allclose(np.asarray(env.D0, dtype=float), values["d0_device"])
                and float(env.VSG_SN) == values["device_mva"]
                and float(env.DM_MAX) == values["positive_slope"]
                and float(-env.DM_MIN) == values["negative_slope"]
                and float(env.DD_MAX) == values["positive_slope"]
                and float(-env.DD_MIN) == values["negative_slope"]
            ),
            "tds_ok": info.get("tds_failed") is False,
            "m_runtime_readback_matches_report": bool(
                np.allclose(runtime_m_dev, reported_m, atol=1.0e-9, rtol=0.0)
            ),
            "d_runtime_readback_matches_report": bool(
                np.allclose(runtime_d_dev, reported_d, atol=1.0e-9, rtol=0.0)
            ),
            "m_target_matches_independent_card_calculation": bool(
                np.allclose(target_m, expected_m, atol=1.0e-9, rtol=0.0)
            ),
            "d_target_matches_independent_card_calculation": bool(
                np.allclose(target_d, expected_d, atol=1.0e-9, rtol=0.0)
            ),
            "m_applied_matches_independent_target": bool(
                np.allclose(reported_m, expected_m, atol=1.0e-9, rtol=0.0)
            ),
            "d_applied_matches_independent_target": bool(
                np.allclose(reported_d, expected_d, atol=1.0e-9, rtol=0.0)
            ),
        }
        return {
            "checks": checks,
            "action": list(NONZERO_ACTION),
            "substeps": int(env.N_SUBSTEPS),
            "M_es": reported_m.tolist(),
            "D_es": reported_d.tolist(),
            "M_target_es": target_m.tolist(),
            "D_target_es": target_d.tolist(),
        }
    finally:
        env.close()


def _reset_repeatability(
    env_class: type, *, parameter_card: Mapping[str, Any]
) -> dict[str, Any]:
    values = _card_values(parameter_card)
    env = env_class(random_disturbance=False, comm_fail_prob=0.0)
    try:
        env.seed(42)
        env.reset(delta_u=LS1_DELTA_U)
        first_m, first_d = _runtime_device_md(
            env, parameter_card=parameter_card
        )
        for position in env._vsg_pos:
            env.ss.GENCLS.M.v[position] += 123.0
            env.ss.GENCLS.D.v[position] += 57.0
        env.reset(delta_u=LS1_DELTA_U)
        second_m, second_d = _runtime_device_md(
            env, parameter_card=parameter_card
        )
        expected_m = np.full(env.N_AGENTS, values["m0_device"])
        expected_d = np.full(env.N_AGENTS, values["d0_device"])
        checks = {
            "m_first_reset_matches_frozen_card": bool(
                np.allclose(first_m, expected_m, atol=1.0e-9, rtol=0.0)
            ),
            "d_first_reset_matches_frozen_card": bool(
                np.allclose(first_d, expected_d, atol=1.0e-9, rtol=0.0)
            ),
            "m_second_reset_restores_frozen_card": bool(
                np.allclose(second_m, expected_m, atol=1.0e-9, rtol=0.0)
            ),
            "d_second_reset_restores_frozen_card": bool(
                np.allclose(second_d, expected_d, atol=1.0e-9, rtol=0.0)
            ),
        }
        return {
            "checks": checks,
            "M_es_first": first_m.tolist(),
            "D_es_first": first_d.tolist(),
            "M_es_second": second_m.tolist(),
            "D_es_second": second_d.tolist(),
        }
    finally:
        env.close()


def run_semantic_gate(
    env_class: type, *, parameter_card: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute all registered semantic components and classify fail-closed."""
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    try:
        results["zero_action"] = summarize_zero_action_bank(
            run_zero_action_bank(env_class)
        )
    except Exception as exc:  # retained as gate evidence
        errors["zero_action"] = f"{type(exc).__name__}: {exc}"
    try:
        results["nonzero_readback"] = _nonzero_readback(
            env_class, parameter_card=parameter_card
        )
    except Exception as exc:  # retained as gate evidence
        errors["nonzero_readback"] = f"{type(exc).__name__}: {exc}"
    try:
        results["reset_repeatability"] = _reset_repeatability(
            env_class, parameter_card=parameter_card
        )
    except Exception as exc:  # retained as gate evidence
        errors["reset_repeatability"] = f"{type(exc).__name__}: {exc}"

    values = _card_values(parameter_card)
    zero_action = results.get("zero_action", {})
    zero_baseline_matches = set(zero_action) == {"ls1", "ls2"} and all(
        np.allclose(
            np.asarray(summary["M_es_first"], dtype=float),
            values["m0_device"],
            atol=1.0e-9,
            rtol=0.0,
        )
        and np.allclose(
            np.asarray(summary["D_es_first"], dtype=float),
            values["d0_device"],
            atol=1.0e-9,
            rtol=0.0,
        )
        for summary in zero_action.values()
    )
    component_checks = {
        "two_zero_action_disturbances": (
            set(zero_action) == {"ls1", "ls2"}
        ),
        "zero_action_matches_frozen_card": zero_baseline_matches,
        "nonzero_five_substep_readback": bool(
            results.get("nonzero_readback", {}).get("checks")
        )
        and all(results["nonzero_readback"]["checks"].values()),
        "reset_repeatability": bool(
            results.get("reset_repeatability", {}).get("checks")
        )
        and all(results["reset_repeatability"]["checks"].values()),
        "no_component_exception": not errors,
    }
    passed = all(component_checks.values())
    return {
        "schema_version": 1,
        "round": "R478",
        "manuscript_line": "yang-md-decoupling-marl",
        "classification": "SEMANTIC-GATE-PASS" if passed else "SEMANTIC-GATE-FAIL",
        "checks": component_checks,
        "errors": errors,
        "results": results,
        "formal_evidence": False,
        "training_authorized": False,
    }
