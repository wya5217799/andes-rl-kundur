import platform

import pytest

IS_WSL = platform.system() == "Linux" and "microsoft" in platform.release().lower()
if not IS_WSL:
    pytest.skip(
        "real ANDES differential integration runs only in WSL",
        allow_module_level=True,
    )

from andes_rl_kundur.evaluation.storage_dae_feasibility import (  # noqa: E402
    run_zero_support_feasibility_scenario,
)


def test_r273_random00_zero_support_differential_feedback_loop():
    disturbance = {"PQ_Bus14": 2.2}
    original = run_zero_support_feasibility_scenario(
        "random_00",
        disturbance,
        plant="original_v4",
        steps=10,
    )
    storage = run_zero_support_feasibility_scenario(
        "random_00",
        disturbance,
        plant="storage_zero",
        steps=10,
    )

    assert original["completed"] is False
    assert original["successful_steps"] == 6
    assert original["attempted_steps"] == 7
    assert original["tds_failed"] is True
    assert original["setup_succeeded"] is True
    assert original["initial_dae"]["finite"] is True
    assert original["initial_dae"]["n"] > 0
    assert original["initial_dae"]["m"] > 0
    assert any(
        "Time step reduced to zero" in message
        for message in original["solver_messages"]
    )

    assert storage["completed"] is False
    assert storage["successful_steps"] == 6
    assert storage["attempted_steps"] == 7
    assert storage["tds_failed"] is True
    assert storage["setup_succeeded"] is True
    assert storage["initial_dae"]["finite"] is True
    assert storage["bess_zero_support_audit"]["max_abs_requested_power"] == 0.0
    assert storage["bess_zero_support_audit"]["max_abs_commanded_power"] == 0.0
    assert storage["bess_zero_support_audit"]["max_abs_actual_power"] < 1e-9
