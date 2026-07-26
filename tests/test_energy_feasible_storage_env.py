import platform

import numpy as np
import pytest

IS_WSL = platform.system() == "Linux" and "microsoft" in platform.release().lower()
if not IS_WSL:
    pytest.skip(
        "real ANDES integration runs only in WSL",
        allow_module_level=True,
    )

from andes_rl_kundur.env.andes.andes_vsg_storage_env import (  # noqa: E402
    AndesMultiVSGEnvV4Storage,
)


def test_storage_env_zero_command_has_no_hidden_power_or_energy_drift():
    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    env.reset(delta_u={"PQ_Bus14": -1.5})
    zero_md = {index: np.zeros(2, dtype=float) for index in range(env.N_AGENTS)}

    _, _, _, info = env.step(
        zero_md,
        bess_power_request_pu=np.zeros(env.N_AGENTS, dtype=float),
    )

    assert info["bess_requested_power_system_pu"] == pytest.approx([0.0] * 4)
    assert info["bess_commanded_power_system_pu"] == pytest.approx([0.0] * 4)
    assert info["bess_actual_power_system_pu"] == pytest.approx([0.0] * 4, abs=1e-9)
    assert info["bess_soc"] == pytest.approx([0.5] * 4, abs=1e-9)
    assert info["bess_constraint_violations"] == []
    assert info["M_es"] == pytest.approx([200.0] * 4)
    assert info["D_es"] == pytest.approx([100.0] * 4)


def test_storage_env_power_sign_matches_soc_direction_and_system_base_units():
    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    zero_md = {index: np.zeros(2, dtype=float) for index in range(env.N_AGENTS)}

    env.reset(delta_u={"PQ_Bus14": 1.5})
    _, _, _, discharge = env.step(
        zero_md,
        bess_power_request_pu=np.full(env.N_AGENTS, 0.36),
    )
    env.reset(delta_u={"PQ_Bus14": -1.5})
    _, _, _, charge = env.step(
        zero_md,
        bess_power_request_pu=np.full(env.N_AGENTS, -0.36),
    )

    assert discharge["bess_commanded_power_system_pu"] == pytest.approx([0.072] * 4)
    assert np.all(discharge["bess_actual_power_system_pu"] > 0.0)
    assert np.all(discharge["bess_soc"] < 0.5)
    assert charge["bess_commanded_power_system_pu"] == pytest.approx([-0.072] * 4)
    assert np.all(charge["bess_actual_power_system_pu"] < 0.0)
    assert np.all(charge["bess_soc"] > 0.5)


def test_zero_support_baseline_matches_candidate_dae_before_control_is_enabled():
    baseline = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    candidate = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    disturbance = {"PQ_Bus14": -1.5}
    baseline.reset(delta_u=disturbance)
    candidate.reset(delta_u=disturbance)
    zero_md = {index: np.zeros(2, dtype=float) for index in range(baseline.N_AGENTS)}

    _, _, _, baseline_info = baseline.step(
        zero_md,
        bess_power_request_pu=np.zeros(baseline.N_AGENTS),
    )
    _, _, _, candidate_info = candidate.step(
        zero_md,
        bess_power_request_pu=np.zeros(candidate.N_AGENTS),
    )

    assert candidate_info["freq_hz_physical"] == pytest.approx(
        baseline_info["freq_hz_physical"],
        abs=1e-9,
    )
