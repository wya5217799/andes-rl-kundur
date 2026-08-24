from __future__ import annotations

import numpy as np
import pytest
from probes import r478_direct_md_transfer_confirmation as DIRECT_TRANSFER
from probes import r478_energy_port_confirmation as ENERGY_CONFIRM
from probes import r478_md_semantic_gate as SEMANTIC
from probes.r478_direct_md_canary import (
    classify_direct_md_canary,
    normalize_system_base_direct_telemetry,
)

from andes_rl_kundur.evaluation.md_decoupling_headroom import build_contract


def _record(
    scenario: dict[str, object],
    *,
    arm_id: str,
    response_scale: float,
    contract: dict[str, object],
) -> dict[str, object]:
    profile = contract["profiles"][0]
    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    steps = int(contract["steps"])
    pattern = {
        "common": np.asarray([1.0, 1.0, -1.0, -1.0]),
        "differential": np.asarray([1.5, -0.5, 1.5, -0.5]),
        "localized": np.asarray([1.0, 0.0, 0.0, 0.0]),
    }[str(scenario["pair_kind"])]
    sign = 1.0 if scenario["sign"] == "positive" else -1.0
    if arm_id == "zero":
        actions = np.zeros((steps, 4, 2), dtype=float)
    else:
        agent_pattern = np.asarray([1.0, -1.0, 0.5, -0.5])
        actions = np.stack(
            [
                np.column_stack(
                    [
                        0.01 * (index + 1) * agent_pattern,
                        -0.005 * (index + 1) * agent_pattern,
                    ]
                )
                for index in range(steps)
            ]
        )
    decoder = contract["decoder"]
    delta_m = np.where(
        actions[:, :, 0] >= 0.0,
        actions[:, :, 0] * float(decoder["delta_m_positive"]),
        actions[:, :, 0] * -float(decoder["delta_m_negative"]),
    )
    delta_d = np.where(
        actions[:, :, 1] >= 0.0,
        actions[:, :, 1] * float(decoder["delta_d_positive"]),
        actions[:, :, 1] * -float(decoder["delta_d_negative"]),
    )
    rows = []
    for index in range(steps):
        rows.append(
            {
                "step_index": index,
                "time": (index + 1) * float(contract["dt_seconds"]),
                "freq_hz_physical": (
                    60.0 + sign * response_scale * pattern
                ).tolist(),
                "action_norm": actions[index].tolist(),
                "delta_M": delta_m[index].tolist(),
                "delta_D": delta_d[index].tolist(),
                "M_es": np.maximum(
                    baseline_m + delta_m[index],
                    float(decoder["m_lower_clamp"]),
                ).tolist(),
                "D_es": np.maximum(
                    baseline_d + delta_d[index],
                    float(decoder["d_lower_clamp"]),
                ).tolist(),
                "tds_failed": False,
            }
        )
    return {
        "profile_id": scenario["profile_id"],
        "split": profile["split"],
        "scenario_id": scenario["scenario_id"],
        "pair_kind": scenario["pair_kind"],
        "sign": scenario["sign"],
        "magnitude": scenario["magnitude"],
        "arm_id": arm_id,
        "identity": {
            "baseline_m0": baseline_m.tolist(),
            "baseline_d0": baseline_d.tolist(),
        },
        "initial_freq_hz_physical": [60.0] * 4,
        "steps": rows,
        "completed": True,
        "tds_failed": False,
    }


def _bank(*, candidate_scale: float) -> tuple[list[dict[str, object]], dict[str, object]]:
    contract = build_contract()
    contract["steps"] = 3
    profile = contract["profiles"][0]
    records = []
    for arm_id, scale in (
        ("zero", 1.0),
        ("local_neighbour_md_km2_kd2", candidate_scale),
    ):
        for scenario in profile["scenarios"]:
            records.append(
                _record(
                    scenario,
                    arm_id=arm_id,
                    response_scale=scale,
                    contract=contract,
                )
            )
    return records, contract


def test_direct_canary_pass_routes_only_to_energy_canary() -> None:
    records, contract = _bank(candidate_scale=0.9)

    decision = classify_direct_md_canary(records, contract=contract)

    assert decision["classification"] == "DIRECT-CANARY-PASS"
    assert decision["next_step"] == "open energy-port canary only"
    assert decision["training_authorized"] is False
    assert decision["formal_evidence"] is False


def test_direct_canary_shift_routes_only_to_direct_formal_bank() -> None:
    records, contract = _bank(candidate_scale=1.1)

    decision = classify_direct_md_canary(records, contract=contract)

    assert decision["classification"] == "DIRECT-CANARY-SHIFT"
    assert decision["checks"]["off_diagonal_ratio_at_most_0p95"] is False
    assert decision["next_step"] == (
        "stop; open direct-M/D deterministic formal bank only"
    )
    assert decision["training_authorized"] is False


def test_direct_canary_invalid_summary_stops_without_opening_formal_bank() -> None:
    records, contract = _bank(candidate_scale=0.9)
    candidate = next(
        record
        for record in records
        if record["arm_id"] == "local_neighbour_md_km2_kd2"
    )
    candidate["steps"][0]["M_es"][0] += 1.0

    decision = classify_direct_md_canary(records, contract=contract)

    assert decision["classification"] == "ANALYSIS-INVALID"
    assert decision["checks"]["summaries_valid"] is False
    assert decision["next_step"] == (
        "stop; repair canary integrity before physical inference"
    )


def _parameter_card() -> dict[str, object]:
    return {
        "system_base_mva": 100.0,
        "devices": {"vsg_1_to_4": {"sn_mva": 200.0}},
        "telemetry_base": (
            "device (info M_es/D_es); invariant: equals ANDES readback "
            "converted to device"
        ),
    }


def test_direct_canary_normalizes_legacy_system_telemetry_once() -> None:
    records, contract = _bank(candidate_scale=0.9)
    raw_system = []
    for record in records:
        copied = dict(record)
        copied["steps"] = [dict(step) for step in record["steps"]]
        for step in copied["steps"]:
            step["M_es"] = (2.0 * np.asarray(step["M_es"])).tolist()
            step["D_es"] = (2.0 * np.asarray(step["D_es"])).tolist()
        raw_system.append(copied)

    normalized = normalize_system_base_direct_telemetry(
        raw_system,
        parameter_card=_parameter_card(),
    )
    decision = classify_direct_md_canary(normalized, contract=contract)

    assert decision["classification"] == "DIRECT-CANARY-PASS"
    assert normalized[0]["telemetry_normalization"]["scale"] == 0.5
    assert "telemetry_normalization" not in raw_system[0]
    with pytest.raises(ValueError, match="already telemetry-normalized"):
        normalize_system_base_direct_telemetry(
            normalized,
            parameter_card=_parameter_card(),
        )


class _Array:
    def __init__(self, values: list[float]) -> None:
        self.v = np.asarray(values, dtype=float)


class _SemanticEnv:
    N_AGENTS = 4
    N_SUBSTEPS = 5
    VSG_SN = 200.0
    M0 = np.full(4, 200.0)
    D0 = np.full(4, 100.0)
    DM_MAX = 600.0
    DM_MIN = -200.0
    DD_MAX = 600.0
    DD_MIN = -200.0

    def __init__(self, **_kwargs: object) -> None:
        self._vsg_pos = list(range(4))
        self.ss = type("System", (), {})()
        self.ss.GENCLS = type("Gencls", (), {})()
        self.ss.GENCLS.M = _Array([400.0] * 4)
        self.ss.GENCLS.D = _Array([200.0] * 4)

    def seed(self, _seed: int) -> None:
        pass

    def reset(self, **_kwargs: object) -> dict[int, np.ndarray]:
        self.ss.GENCLS.M.v[:] = 400.0
        self.ss.GENCLS.D.v[:] = 200.0
        return {actor: np.zeros(1) for actor in range(self.N_AGENTS)}

    def step(self, _actions: dict[int, np.ndarray]):
        m_device = np.full(4, 500.0)
        d_device = np.full(4, 50.0)
        self.ss.GENCLS.M.v[:] = 2.0 * m_device
        self.ss.GENCLS.D.v[:] = 2.0 * d_device
        return {}, {}, False, {
            "M_es": m_device,
            "D_es": d_device,
            "M_target_es": m_device,
            "D_target_es": d_device,
            "tds_failed": False,
        }

    def close(self) -> None:
        pass


def test_semantic_gate_executes_all_registered_components(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SEMANTIC,
        "run_zero_action_bank",
        lambda _env_class: {
            "ls1": {"n_steps": 30, "max_df": 1.0, "final_df": 0.1,
                    "traj": {"M_es": [[200.0] * 4], "D_es": [[100.0] * 4]}},
            "ls2": {"n_steps": 30, "max_df": 1.1, "final_df": 0.2,
                    "traj": {"M_es": [[200.0] * 4], "D_es": [[100.0] * 4]}},
        },
    )

    parameter_card = {
        "system_base_mva": 100.0,
        "devices": {
            "vsg_1_to_4": {
                "sn_mva": 200.0,
                "m_device_s": 200.0,
                "d_device": 100.0,
            }
        },
        "action_map": {"positive_slope": 600.0, "negative_slope": 200.0},
        "clamps": {"m_min_device": 20.0, "d_min_device": 10.0},
        "slew": {"n_substeps": 5},
    }
    decision = SEMANTIC.run_semantic_gate(
        _SemanticEnv,
        parameter_card=parameter_card,
    )

    assert decision["classification"] == "SEMANTIC-GATE-PASS"
    assert all(decision["checks"].values())
    assert decision["results"]["nonzero_readback"]["substeps"] == 5
    assert decision["results"]["reset_repeatability"]["checks"] == {
        "m_first_reset_matches_frozen_card": True,
        "d_first_reset_matches_frozen_card": True,
        "m_second_reset_restores_frozen_card": True,
        "d_second_reset_restores_frozen_card": True,
    }


def test_energy_confirmation_freezes_one_30_job_block() -> None:
    jobs = ENERGY_CONFIRM.registered_jobs()

    assert len(jobs) == 30
    assert {job["arm_id"] for job in jobs} == {
        "zero_feedback",
        "local_feasibility_native",
        "bandpass_k3p5",
    }
    assert {job["experiment_kind"] for job in jobs} == {
        "probe",
        "disturbance",
    }
    assert ENERGY_CONFIRM.WORKERS == 16
    with pytest.raises(RuntimeError, match="WSL/POSIX-only"):
        ENERGY_CONFIRM.run_confirmation()


def test_direct_transfer_freezes_one_unseen_12_job_profile() -> None:
    tasks = DIRECT_TRANSFER.registered_tasks("eval_a")

    assert len(tasks) == 12
    assert {arm_id for arm_id, _scenario in tasks} == {
        "zero",
        "local_neighbour_md_km2_kd2",
    }
    assert {scenario["profile_id"] for _arm, scenario in tasks} == {"eval_a"}
    assert DIRECT_TRANSFER.WORKERS == 12
    with pytest.raises(ValueError, match="unregistered transfer profile"):
        DIRECT_TRANSFER.registered_tasks("not_a_profile")
    with pytest.raises(RuntimeError, match="WSL/POSIX-only"):
        DIRECT_TRANSFER.run_confirmation("eval_a")
