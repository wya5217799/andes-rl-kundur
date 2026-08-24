"""R478 Phase 0C — seven M/D base-convention invariants (red-first).

Declared physical contract (see ``andes_rl_kundur.env.andes.md_convention``):

- controller math (M0, D0, action decode, clamps, rewards): DEVICE base;
- ANDES runtime arrays (``GENCLS.M.v`` / ``GENCLS.D.v``): SYSTEM base;
- one conversion per boundary crossing: ``x_sys = x_dev * S_n / S_b``.

V4 device card (paper Eq.12 middle): ``S_n = 200`` MVA per VSG,
``M0 = 200`` s (``H0 = 100`` s), ``D0 = 100``, system base ``S_b = 100``
MVA, so the declared runtime card is ``M = 400`` s, ``D = 200``.

These tests are the R478 INVARIANT-GATE: all seven must be green before
any corrected simulator bank runs. They execute only where real ANDES is
importable (WSL). Pre-fix expectation: all seven fail (red) because the
runtime path mixes device and system bases; after the R478 fix all seven
must be green.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _real_andes_available() -> bool:
    try:
        import andes
    except ModuleNotFoundError:
        return False
    return callable(getattr(andes, "get_case", None))


if not _real_andes_available():
    pytest.skip(
        "real ANDES is WSL-only; run M/D invariant tests under WSL",
        allow_module_level=True,
    )

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv  # noqa: E402
from andes_rl_kundur.env.andes.md_convention import (  # noqa: E402
    SYSTEM_BASE_MVA,
    device_to_system,
    system_to_device,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

VSG_SN = 200.0
M0_DEV = 200.0
D0_DEV = 100.0
M0_SYS = float(device_to_system(np.asarray([M0_DEV]), device_mva=VSG_SN)[0])
D0_SYS = float(device_to_system(np.asarray([D0_DEV]), device_mva=VSG_SN)[0])


@pytest.fixture(autouse=True)
def _isolate_andes_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep real-ANDES TDS outputs out of the repository root."""
    monkeypatch.chdir(tmp_path)


def _make_env() -> AndesMultiVSGEnvV4:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(42)
    return env


def _zero_actions(env: AndesMultiVSGEnvV4) -> dict[int, np.ndarray]:
    return {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}


def _runtime_md(env: AndesMultiVSGEnvV4) -> tuple[np.ndarray, np.ndarray]:
    m = np.asarray([env.ss.GENCLS.M.v[p] for p in env._vsg_pos], dtype=float)
    d = np.asarray([env.ss.GENCLS.D.v[p] for p in env._vsg_pos], dtype=float)
    return m, d


def test_invariant_1_zero_action_preserves_runtime_md() -> None:
    """Initialized runtime M/D must equal first-step and later-step M/D."""
    env = _make_env()
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        m0, d0 = _runtime_md(env)
        np.testing.assert_allclose(m0, M0_SYS, atol=1e-9, rtol=0)
        np.testing.assert_allclose(d0, D0_SYS, atol=1e-9, rtol=0)
        for _ in range(3):
            env.step(_zero_actions(env))
        m1, d1 = _runtime_md(env)
        np.testing.assert_allclose(m1, m0, atol=1e-9, rtol=0)
        np.testing.assert_allclose(d1, d0, atol=1e-9, rtol=0)
    finally:
        env.close()


def test_invariant_2_telemetry_equals_andes_readback() -> None:
    """Reported applied M/D must equal the ANDES readback under the declared
    telemetry base (device): info values == readback converted to device."""
    env = _make_env()
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        actions = {
            i: np.asarray([0.5, -0.25], dtype=np.float32)
            for i in range(env.N_AGENTS)
        }
        _obs, _rew, _done, info = env.step(actions)
        m, d = _runtime_md(env)
        np.testing.assert_allclose(
            info["M_es"], system_to_device(m, device_mva=VSG_SN),
            atol=1e-9, rtol=0,
        )
        np.testing.assert_allclose(
            info["D_es"], system_to_device(d, device_mva=VSG_SN),
            atol=1e-9, rtol=0,
        )
    finally:
        env.close()


def test_invariant_3_device_system_device_round_trip_lossless() -> None:
    """Device card -> system runtime -> device report must be lossless."""
    env = _make_env()
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        m, d = _runtime_md(env)
        np.testing.assert_allclose(
            system_to_device(m, device_mva=VSG_SN), M0_DEV, atol=1e-9, rtol=0
        )
        np.testing.assert_allclose(
            system_to_device(d, device_mva=VSG_SN), D0_DEV, atol=1e-9, rtol=0
        )
        actions = {
            i: np.asarray([1.0, 0.0], dtype=np.float32)
            for i in range(env.N_AGENTS)
        }
        _obs, _rew, _done, _info = env.step(actions)
        m, d = _runtime_md(env)
        expected_m_dev = max(M0_DEV + env.DM_MAX, env.M_MIN_PHYSICAL)
        np.testing.assert_allclose(
            system_to_device(m, device_mva=VSG_SN),
            expected_m_dev,
            atol=1e-9,
            rtol=0,
        )
        np.testing.assert_allclose(
            system_to_device(d, device_mva=VSG_SN), D0_DEV, atol=1e-9, rtol=0
        )
    finally:
        env.close()


def test_invariant_4_heterogeneous_card_preserved() -> None:
    """All four device identities and per-device weights must be preserved."""
    env = _make_env()
    hetero = np.asarray([100.0, 90.0, 80.0, 70.0])
    expected = device_to_system(hetero, device_mva=VSG_SN)
    try:
        env.D0_HETEROGENEOUS = hetero.copy()
        env.reset(delta_u=SCENARIOS["load_step_1"])
        _m, d = _runtime_md(env)
        np.testing.assert_allclose(d, expected, atol=1e-9, rtol=0)
        for _ in range(2):
            env.step(_zero_actions(env))
        _m2, d2 = _runtime_md(env)
        np.testing.assert_allclose(d2, expected, atol=1e-9, rtol=0)
        assert len(np.unique(np.round(d2, 12))) == 4
    finally:
        env.close()


def test_invariant_5_nonzero_action_branches_clamps_and_slew() -> None:
    """Both decoder branches, both clamps, and the substep slew must have correct units."""
    env = _make_env()
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        env.step(
            {i: np.asarray([1.0, 1.0], dtype=np.float32) for i in range(env.N_AGENTS)}
        )
        m, d = _runtime_md(env)
        np.testing.assert_allclose(
            m,
            device_to_system(
                np.full(4, M0_DEV + env.DM_MAX), device_mva=VSG_SN
            ),
            atol=1e-9,
            rtol=0,
        )
        np.testing.assert_allclose(
            d,
            device_to_system(
                np.full(4, D0_DEV + env.DD_MAX), device_mva=VSG_SN
            ),
            atol=1e-9,
            rtol=0,
        )
        env.step(
            {i: np.asarray([-1.0, -1.0], dtype=np.float32) for i in range(env.N_AGENTS)}
        )
        m, d = _runtime_md(env)
        np.testing.assert_allclose(
            m,
            device_to_system(
                np.full(
                    4, max(M0_DEV + env.DM_MIN, env.M_MIN_PHYSICAL)
                ),
                device_mva=VSG_SN,
            ),
            atol=1e-9,
            rtol=0,
        )
        np.testing.assert_allclose(
            d,
            device_to_system(
                np.full(
                    4, max(D0_DEV + env.DD_MIN, env.D_MIN_PHYSICAL)
                ),
                device_mva=VSG_SN,
            ),
            atol=1e-9,
            rtol=0,
        )
    finally:
        env.close()


def test_invariant_6_energy_port_zero_power_keeps_slow_channel() -> None:
    """Energy-port steps must never alter the M/D slow parameter channel."""
    base = _make_env()
    env = AndesVSGEnergyPortEnv(base_env=base)
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        m0, d0 = _runtime_md(base)
        env.step(np.zeros(4, dtype=np.float64))
        m1, d1 = _runtime_md(base)
        np.testing.assert_allclose(m1, m0, atol=1e-9, rtol=0)
        np.testing.assert_allclose(d1, d0, atol=1e-9, rtol=0)
        env.step(np.asarray([0.1, -0.1, 0.05, 0.0], dtype=np.float64))
        m2, d2 = _runtime_md(base)
        np.testing.assert_allclose(m2, m0, atol=1e-9, rtol=0)
        np.testing.assert_allclose(d2, d0, atol=1e-9, rtol=0)
    finally:
        base.close()


def test_invariant_7_reset_repeatability() -> None:
    """Repeated reset must reproduce the same runtime card."""
    env = _make_env()
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        m0, d0 = _runtime_md(env)
        env.reset(delta_u=SCENARIOS["load_step_1"])
        m1, d1 = _runtime_md(env)
        np.testing.assert_array_equal(m1, m0)
        np.testing.assert_array_equal(d1, d0)
        np.testing.assert_allclose(m1, M0_SYS, atol=1e-9, rtol=0)
        np.testing.assert_allclose(d1, D0_SYS, atol=1e-9, rtol=0)
    finally:
        env.close()
