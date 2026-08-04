from __future__ import annotations

import numpy as np
import pytest
from scripts.run_r291_state_aware_handoff import (
    _verify_seal,
    prepare,
)

from andes_rl_kundur.evaluation.state_aware_handoff import (
    COMMON_HANDOFF,
    FIXED_3S,
    FIXED_5S,
    FULL_HANDOFF,
    HandoffSupervisor,
    classify_state_aware_handoff,
    frozen_handoff_contract,
    make_fast_controller,
    summarise_handoff_trace,
)


def _frequencies_from_error(
    common_error_hz: float,
    *,
    differential_hz: float = 0.0,
) -> np.ndarray:
    common = 60.0 - common_error_hz
    return np.asarray(
        [
            common + differential_hz / 2.0,
            common + differential_hz / 2.0,
            common - differential_hz / 2.0,
            common - differential_hz / 2.0,
        ],
        dtype=float,
    )


def _step_supervisor(
    supervisor: HandoffSupervisor,
    step: int,
    *,
    error_hz: float,
    differential_hz: float = 0.0,
    slow_gap_pu: float = 0.0,
) -> None:
    requested = np.full(4, slow_gap_pu, dtype=float)
    actual = np.zeros(4, dtype=float)
    supervisor.observe(
        step=step,
        frequencies_hz=_frequencies_from_error(
            error_hz,
            differential_hz=differential_hz,
        ),
        slow_requested_power_system_pu=requested,
        slow_actual_power_system_pu=actual,
    )


def _trace_record(
    gate: np.ndarray,
    delta_f: np.ndarray,
    *,
    forced_release: bool = False,
) -> dict[str, object]:
    traces = []
    for step, (gate_value, row) in enumerate(zip(gate, delta_f, strict=True)):
        action = [[float(0.25 * gate_value), 0.0] for _ in range(4)]
        traces.append(
            {
                "step": step,
                "t": 0.2 * (step + 1),
                "freq_hz_physical": (60.0 + row).tolist(),
                "delta_f_physical_hz": row.tolist(),
                "action_norm": action,
                "M_es": (200.0 + 600.0 * np.asarray(action)[:, 0]).tolist(),
                "D_es": [100.0] * 4,
                "bess_requested_power_system_pu": [0.0] * 4,
                "bess_commanded_power_system_pu": [0.0] * 4,
                "bess_actual_power_system_pu": [0.0] * 4,
                "bess_soc": [0.5] * 4,
                "bess_bus_voltage_pu": [1.0] * 4,
                "bess_saturation_reasons": [[], [], [], []],
                "bess_charge_energy_mwh_total": [0.0] * 4,
                "bess_discharge_energy_mwh_total": [0.0] * 4,
                "bess_constraint_violations": [],
                "handoff": {
                    "gate": float(gate_value),
                    "target_gate": float(gate_value),
                    "ready": False,
                    "forced_release": forced_release,
                    "switch_count": 0,
                },
            }
        )
    return {
        "controller": COMMON_HANDOFF,
        "completed": True,
        "tds_failed": False,
        "n_steps": len(traces),
        "requested_steps": len(traces),
        "frequency_reporting_basis": "legacy_control_hz",
        "andes_nominal_frequency_hz": 60.0,
        "traces": traces,
    }


def _effect(
    point: float,
    upper: float,
    *,
    lower: float | None = None,
) -> dict[str, object]:
    return {
        "ratio_of_means_percent": {
            "point": point,
            "percentile_95_interval": [
                point - 1.0 if lower is None else lower,
                upper,
            ],
        }
    }


def _contrast(
    endpoint_effects: dict[str, tuple[float, float]],
) -> dict[str, object]:
    return {
        "endpoints": {
            endpoint: _effect(point, upper)
            for endpoint, (point, upper) in endpoint_effects.items()
        }
    }


def _valid_summaries(*, forced_common: int = 0, forced_full: int = 0):
    base = {
        "complete_count": 24,
        "failure_count": 0,
        "constraint_violation_count": 0,
        "action_budget_pass": True,
        "storage_guard_pass": True,
        "tail_guard_pass": True,
        "forced_release_count": 0,
    }
    return {
        "slow_only": dict(base),
        FIXED_3S: dict(base),
        FIXED_5S: dict(base),
        COMMON_HANDOFF: dict(base, forced_release_count=forced_common),
        FULL_HANDOFF: dict(base, forced_release_count=forced_full),
    }


def test_frozen_contract_derives_physical_thresholds_and_budgets() -> None:
    contract = frozen_handoff_contract()
    assert contract["timing"]["control_dt_s"] == pytest.approx(0.2)
    assert contract["timing"]["minimum_on_steps"] == 5
    assert contract["timing"]["taper_steps"] == 5
    assert contract["timing"]["hard_zero_step"] == 25
    assert contract["thresholds"]["frequency_rate_resolution_hz_s"] == pytest.approx(
        0.025
    )
    assert contract["thresholds"]["recovery_product_hz2_s"] == pytest.approx(
        0.000125
    )
    assert contract["thresholds"]["slow_gap_system_pu_per_device"] == pytest.approx(
        0.072
    )
    assert contract["budgets"]["fixed_3s_action_l1_agent_s"] == pytest.approx(0.75)
    assert contract["budgets"]["max_action_l1_agent_s"] == pytest.approx(1.25)
    assert contract["budgets"]["adaptive_internal_slew_per_step"] == pytest.approx(
        0.05
    )


def test_prepare_seals_fresh_bank_before_any_trace(tmp_path) -> None:
    seal = tmp_path / "formal_seal.json"
    out = tmp_path / "results"
    prepare(seal, out)
    digest = seal.with_name("formal_seal.json.sha256").read_text(
        encoding="ascii"
    ).split()[0]

    payload = _verify_seal(seal, digest)

    assert payload["execution"]["formal_trace_count_at_freeze"] == 0
    assert payload["formal_bank"]["scenario_count"] == 24
    assert payload["freshness"]["exact_delta_u_overlap_count"] == 0
    assert not (out / "traces").exists()


def test_fixed_duration_controllers_are_exact_and_common() -> None:
    fixed_3s = make_fast_controller(FIXED_3S)
    fixed_5s = make_fast_controller(FIXED_5S)

    values_3s = [
        float(fixed_3s.actions(step=step, n_agents=4)[0][0])
        for step in range(27)
    ]
    values_5s = [
        float(fixed_5s.actions(step=step, n_agents=4)[0][0])
        for step in range(27)
    ]

    assert values_3s[:15] == pytest.approx([0.25] * 15)
    assert values_3s[15:] == pytest.approx([0.0] * 12)
    assert values_5s[:25] == pytest.approx([0.25] * 25)
    assert values_5s[25:] == pytest.approx([0.0] * 2)
    assert all(
        np.allclose(
            fixed_5s.actions(step=step, n_agents=4)[agent],
            np.asarray([values_5s[step], 0.0], dtype=np.float32),
        )
        for step in range(27)
        for agent in range(4)
    )


def test_common_gate_waits_minimum_on_then_tapers_without_internal_jump() -> None:
    supervisor = HandoffSupervisor(mode="common")
    gates = []
    # A decreasing positive error is a recovery phase. Minimum-on plus
    # confirmation dwell must elapse before the target changes.
    for step, error in enumerate(np.linspace(0.12, 0.01, 14)):
        gates.append(supervisor.gate)
        _step_supervisor(supervisor, step, error_hz=float(error))

    assert gates[:7] == pytest.approx([1.0] * 7)
    internal_slew = np.abs(np.diff(np.asarray(gates, dtype=float) * 0.25))
    assert np.max(internal_slew) <= 0.05 + 1e-12
    assert gates[-1] == pytest.approx(0.0)
    telemetry = supervisor.telemetry()
    assert telemetry["forced_release"] is False
    assert telemetry["release_time_s"] is not None
    assert telemetry["switch_count"] == 1


def test_full_gate_waits_for_differential_and_slow_takeover() -> None:
    common = HandoffSupervisor(mode="common")
    full = HandoffSupervisor(mode="full")
    for step, error in enumerate(np.linspace(0.12, 0.04, 10)):
        _step_supervisor(common, step, error_hz=float(error))
        _step_supervisor(
            full,
            step,
            error_hz=float(error),
            differential_hz=0.08,
            slow_gap_pu=0.09,
        )

    assert common.gate < 1.0
    assert full.gate == pytest.approx(1.0)
    assert full.telemetry()["ready"] is False

    for step in range(10, 14):
        _step_supervisor(
            full,
            step,
            error_hz=0.03 - 0.002 * (step - 10),
            differential_hz=0.02,
            slow_gap_pu=0.02,
        )
    assert full.gate < 1.0


def test_unready_gate_forces_taper_and_is_zero_at_five_seconds() -> None:
    supervisor = HandoffSupervisor(mode="full")
    gates = []
    for step in range(25):
        gates.append(supervisor.gate)
        _step_supervisor(
            supervisor,
            step,
            error_hz=0.2,
            differential_hz=0.2,
            slow_gap_pu=0.2,
        )

    assert gates[19] == pytest.approx(1.0)
    assert gates[20:25] == pytest.approx([0.8, 0.6, 0.4, 0.2, 0.0])
    assert supervisor.gate == pytest.approx(0.0)
    assert supervisor.telemetry()["forced_release"] is True


def test_summary_uses_control_relative_three_to_ten_second_window() -> None:
    gate = np.zeros(60, dtype=float)
    delta = np.zeros((60, 4), dtype=float)
    delta[15:50] = np.asarray([0.1, -0.2, 0.05, -0.05])
    record = _trace_record(gate, delta)

    summary = summarise_handoff_trace(record)

    assert summary["post_3_to_10s_worst_bus_iae_hz_s"] == pytest.approx(
        35 * 0.2 * 0.2
    )
    assert summary["post_3_to_10s_common_secondary_peak_abs_hz"] == pytest.approx(
        0.025
    )
    assert summary["post_window_start_step"] == 15
    assert summary["post_window_stop_step"] == 50
    assert summary["forced_release"] is False
    assert summary["adaptive_internal_max_slew_per_step"] == pytest.approx(0.0)


def test_classifier_requires_timing_value_not_only_fixed3_gain() -> None:
    primary = {
        "common_vs_fixed3": _contrast(
            {
                "post_iae": (-8.0, -3.0),
                "secondary_peak": (-6.0, -1.0),
            }
        ),
        # Worse than fixed5 and no effort contrast: duration confound remains.
        "common_vs_fixed5": _contrast(
            {
                "post_iae": (4.0, 6.0),
                "secondary_peak": (3.0, 5.0),
                "action_l1": (-5.0, 1.0),
            }
        ),
        "full_vs_fixed3": _contrast(
            {
                "post_iae": (-1.0, 1.0),
                "secondary_peak": (-1.0, 1.0),
            }
        ),
        "full_vs_fixed5": _contrast(
            {
                "post_iae": (4.0, 6.0),
                "secondary_peak": (4.0, 6.0),
                "action_l1": (-5.0, 1.0),
            }
        ),
        "full_vs_common": _contrast(
            {
                "post_iae": (1.0, 2.0),
                "secondary_peak": (1.0, 2.0),
            }
        ),
        "fixed5_vs_fixed3": _contrast(
            {
                "post_iae": (-5.0, -1.0),
                "secondary_peak": (-4.0, -1.0),
            }
        ),
    }
    decision = classify_state_aware_handoff(
        controller_summaries=_valid_summaries(),
        contrasts=primary,
        provenance_hashes_match=True,
        guard_no_harm={
            "common_vs_fixed3": True,
            "common_vs_fixed5": False,
            "full_vs_fixed3": True,
            "full_vs_fixed5": False,
            "full_vs_common": True,
        },
    )
    assert decision["classification"] == "FIXED-DURATION-ONLY"
    assert decision["common_timing_gate"] is False


def test_classifier_selects_common_and_deletes_unhelpful_full_state() -> None:
    primary = {
        "common_vs_fixed3": _contrast(
            {
                "post_iae": (-8.0, -3.0),
                "secondary_peak": (-6.0, -1.0),
            }
        ),
        "common_vs_fixed5": _contrast(
            {
                "post_iae": (0.5, 1.5),
                "secondary_peak": (0.2, 1.0),
                "action_l1": (-20.0, -12.0),
            }
        ),
        "full_vs_fixed3": _contrast(
            {
                "post_iae": (-7.0, -2.0),
                "secondary_peak": (-5.0, -1.0),
            }
        ),
        "full_vs_fixed5": _contrast(
            {
                "post_iae": (0.5, 1.5),
                "secondary_peak": (0.5, 1.5),
                "action_l1": (-15.0, -8.0),
            }
        ),
        "full_vs_common": _contrast(
            {
                "post_iae": (0.5, 1.5),
                "secondary_peak": (0.5, 1.5),
            }
        ),
        "fixed5_vs_fixed3": _contrast(
            {
                "post_iae": (-4.0, -1.0),
                "secondary_peak": (-4.0, -1.0),
            }
        ),
    }
    decision = classify_state_aware_handoff(
        controller_summaries=_valid_summaries(),
        contrasts=primary,
        provenance_hashes_match=True,
        guard_no_harm={
            "common_vs_fixed3": True,
            "common_vs_fixed5": True,
            "full_vs_fixed3": True,
            "full_vs_fixed5": True,
            "full_vs_common": True,
        },
    )
    assert decision["classification"] == "HANDOFF-POSITIVE-COMMON"
    assert decision["common_timing_gate"] is True
    assert decision["full_incremental_gate"] is False
    assert decision["recommended_state_set"] == "common_only"


def test_classifier_invalidates_forced_release_even_with_good_means() -> None:
    primary = {
        name: _contrast(
            {
                "post_iae": (-10.0, -5.0),
                "secondary_peak": (-10.0, -5.0),
                "action_l1": (-20.0, -10.0),
            }
        )
        for name in (
            "common_vs_fixed3",
            "common_vs_fixed5",
            "full_vs_fixed3",
            "full_vs_fixed5",
            "full_vs_common",
            "fixed5_vs_fixed3",
        )
    }
    decision = classify_state_aware_handoff(
        controller_summaries=_valid_summaries(forced_common=1),
        contrasts=primary,
        provenance_hashes_match=True,
        guard_no_harm={
            "common_vs_fixed3": True,
            "common_vs_fixed5": True,
            "full_vs_fixed3": True,
            "full_vs_fixed5": True,
            "full_vs_common": True,
        },
    )
    assert decision["classification"] == "HANDOFF-PARTIAL"
    assert decision["guards"]["common_zero_forced_release"] is False
