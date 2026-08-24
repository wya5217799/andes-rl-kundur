"""Offline regression for partial M/D application on a failed TDS substep."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from andes_rl_kundur.env.andes.base_env import AndesBaseEnv


class _Array:
    def __init__(self, values: list[float]) -> None:
        self.v = np.asarray(values, dtype=float)


class _Gencls:
    def __init__(self) -> None:
        self.M = _Array([400.0])
        self.D = _Array([200.0])
        self.history = {"M": [], "D": []}

    def set(self, name: str, _idx: str, value: float, *, attr: str) -> None:
        assert attr == "v"
        getattr(self, name).v[0] = value
        self.history[name].append(float(value))


class _Tds:
    def __init__(self, dae: SimpleNamespace, *, fail_at: int | None = 3) -> None:
        self.config = SimpleNamespace(tf=0.0)
        self.busted = False
        self._dae = dae
        self._calls = 0
        self._fail_at = fail_at

    def run(self) -> None:
        self._calls += 1
        if self._fail_at is None or self._calls < self._fail_at:
            self._dae.t = self.config.tf


class _PublicStepEnv(AndesBaseEnv):
    N_AGENTS = 1
    COMM_ADJ = {0: []}
    VSG_M0 = 200.0
    VSG_D0 = 100.0
    DM_MIN = -200.0
    DM_MAX = 600.0
    DD_MIN = -200.0
    DD_MAX = 600.0
    M_MIN_PHYSICAL = 20.0
    D_MIN_PHYSICAL = 10.0

    def _build_system(self):
        raise AssertionError("not used by this public-step regression")

    def _apply_disturbance(self, delta_u=None, **kwargs):
        raise AssertionError("not used by this public-step regression")

    def _get_vsg_omega(self):
        return np.ones(1)

    def _get_vsg_power(self):
        return np.zeros(1)

    def _compute_omega_dot(self, omega, power):
        return np.zeros(1)

    def _build_obs(self, omega=None, omega_dot=None, P_es=None):
        return {0: np.zeros(1)}

    def _compute_rewards(self, omega, omega_dot, delta_M, delta_D):
        return {0: 0.0}, 0.0, 0.0, 0.0


def test_failed_substep_reports_and_carries_runtime_readback() -> None:
    env = _PublicStepEnv(random_disturbance=False, comm_fail_prob=0.0)
    dae = SimpleNamespace(t=0.0)
    env.ss = SimpleNamespace(GENCLS=_Gencls(), dae=dae)
    env.ss.TDS = _Tds(dae)
    env.vsg_idx = ["vsg-1"]
    env._vsg_pos = [0]
    env._prev_M = np.asarray([400.0])
    env._prev_D = np.asarray([200.0])
    env._prev_delta_M = np.zeros(1)
    env._prev_delta_D = np.zeros(1)
    env._prev_omega = np.ones(1)

    _obs, _rewards, done, info = env.step({0: np.asarray([1.0, 0.0])})

    # The third write reaches alpha=0.6, then the fake solver stalls.
    np.testing.assert_allclose(env.ss.GENCLS.M.v, [1120.0])
    np.testing.assert_allclose(env._prev_M, env.ss.GENCLS.M.v)
    np.testing.assert_allclose(info["M_es"], [560.0])
    np.testing.assert_allclose(info["M_target_es"], [800.0])
    assert info["tds_failed"] is True
    assert done is True


def test_public_step_applies_linear_system_base_slew_at_every_substep() -> None:
    env = _PublicStepEnv(random_disturbance=False, comm_fail_prob=0.0)
    dae = SimpleNamespace(t=0.0)
    gencls = _Gencls()
    env.ss = SimpleNamespace(GENCLS=gencls, dae=dae)
    env.ss.TDS = _Tds(dae, fail_at=None)
    env.vsg_idx = ["vsg-1"]
    env._vsg_pos = [0]
    env._prev_M = np.asarray([400.0])
    env._prev_D = np.asarray([200.0])
    env._prev_delta_M = np.zeros(1)
    env._prev_delta_D = np.zeros(1)
    env._prev_omega = np.ones(1)

    _obs, _rewards, _done, info = env.step({0: np.asarray([1.0, 1.0])})

    np.testing.assert_allclose(gencls.history["M"], [640, 880, 1120, 1360, 1600])
    np.testing.assert_allclose(gencls.history["D"], [440, 680, 920, 1160, 1400])
    np.testing.assert_allclose(info["M_es"], [800.0])
    np.testing.assert_allclose(info["D_es"], [700.0])
    assert info["tds_failed"] is False
