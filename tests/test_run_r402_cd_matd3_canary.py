"""Windows-safe tests for the R402 canary execution runner.

Binds the seal-loading path, arm factory, observation helpers, and masking
without touching ANDES.  WSL rehearse/train/evaluate/classify are covered by
the runner rehearsal itself.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

runner = importlib.import_module("run_r402_cd_matd3_canary")


def test_seal_loads_and_binds_contract():
    seal = runner.load_seal()
    assert seal["round"] == "R401"
    assert seal["contract"] == runner.build_contract()
    assert seal["launch"]["wsl_python_processes"] == 5


def test_agent_factory_returns_registered_learners():
    from andes_rl_kundur.agents.cd_matd3 import CDMATD3, YangScalarTD3

    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(scalar, YangScalarTD3)
    assert isinstance(no_message, CDMATD3)
    assert isinstance(message, CDMATD3)
    assert scalar.out_dim == 1
    assert no_message.out_dim == 2
    assert message.out_dim == 2


def test_mask_applies_only_to_no_message_arm():
    obs = np.arange(28, dtype=np.float32)
    assert np.allclose(
        runner._mask_actor_obs("cd_matd3_message", obs), obs
    )
    assert np.allclose(
        runner._mask_actor_obs("yang_scalar_td3", obs), obs
    )
    masked = runner._mask_actor_obs("cd_matd3_no_message", obs).reshape(4, 7)
    assert np.all(masked[:, 3:] == 0.0)
    assert np.all(masked[:, :3] == obs.reshape(4, 7)[:, :3])


def test_joint_obs_concatenates_rows_in_order():
    observation = {
        i: np.full(7, float(i), dtype=np.float32) for i in range(4)
    }
    joint = runner._joint_obs(observation)
    assert joint.shape == (28,)
    assert np.all(joint == np.repeat(np.arange(4, dtype=np.float32), 7))


def test_scalar_step_reward_sums_agents():
    rewards = {0: 1.0, 1: -2.0, 2: 0.5, 3: 0.25}
    assert runner._scalar_step_reward(rewards) == -0.25


def test_eval_record_path_is_a_path_not_a_tuple():
    path = runner._eval_record_path("cd_matd3_message", 401, "canary_eval_a")
    assert isinstance(path, Path)
    assert path.name == "canary_eval_a.json"
    assert "seed401" in path.parts
    det = runner._eval_record_path("local_neighbour_md_km2_kd2", None, "canary_eval_b")
    assert "deterministic" in det.parts


def test_contract_and_seal_counts_agree():
    contract = runner.build_contract()
    seal = runner.load_seal()
    assert runner.training_run_count(contract) == 9
    assert runner.evaluation_record_count(contract) == 240
    assert seal["canary_work_units"]["training_runs"] == 9
    assert seal["canary_work_units"]["evaluation_records"] == 240
    assert runner.TOTAL_INTERACTION_STEPS == 43200

