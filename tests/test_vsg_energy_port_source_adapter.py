from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
    AndesVSGEnergyPortFixedStateSource,
)


class _FakeSynGen:
    def __init__(self) -> None:
        self.values = {name: 1.0 + index for index, name in enumerate(_VSG_IDS)}

    def get_pref(self, _system: object, index: str) -> float:
        return self.values[index]

    def set_pref(self, _system: object, index: str, value: float) -> None:
        self.values[index] = float(value)


class _FakePQ:
    def __init__(self) -> None:
        self.idx = SimpleNamespace(v=np.asarray(_PQ_IDS, dtype=object))
        self.Ppf = SimpleNamespace(v=np.asarray([11.59, 15.75, 2.48]))

    def idx2uid(self, name: str) -> int:
        return _PQ_IDS.index(name)

    def set(self, parameter: str, name: str, value: float, *, attr: str) -> None:
        assert parameter == "Ppf"
        assert attr == "v"
        self.Ppf.v[self.idx2uid(name)] = float(value)


class _FakeTDS:
    def __init__(self, system: _FakeSystem) -> None:
        self._system = system
        self.test_ok = True
        self.config = SimpleNamespace(tol=1.0e-6)
        self.residual_bias = 0.0

    def fg_update(self, *, models: object) -> None:
        assert models == ("pflow", "tds")
        control = np.asarray(
            [self._system.SynGen.values[name] for name in _VSG_IDS]
        ) - np.arange(1.0, 5.0)
        disturbance = self._system.PQ.Ppf.v - np.asarray([11.59, 15.75, 2.48])
        padded = np.pad(disturbance, (0, 1))
        self._system.dae.f[:] = control + 2.0 * padded + self.residual_bias
        self._system.dae.g[:] = -control + 3.0 * padded + self.residual_bias

class _FakeEIG:
    x_name = ["omega VSG_1", "omega VSG_2", "omega VSG_3", "omega VSG_4"]

    def __init__(self) -> None:
        self.matrix = -np.eye(4)

    def calc_As(self, *, dense: bool) -> np.ndarray:
        assert dense
        return self.matrix.copy()


class _FakeSystem:
    def __init__(self) -> None:
        self.dae = SimpleNamespace(
            x=np.zeros(4),
            y=np.zeros(4),
            z=np.zeros(1),
            f=np.zeros(4),
            g=np.zeros(4),
            Tf=np.ones(4),
            fx=-np.eye(4),
            fy=np.zeros((4, 4)),
            gx=np.zeros((4, 4)),
            gy=np.eye(4),
            x_name=list(_FakeEIG.x_name),
            y_name=[f"algebraic {index}" for index in range(4)],
        )
        self.SynGen = _FakeSynGen()
        self.PQ = _FakePQ()
        self.GENCLS = SimpleNamespace(omega=SimpleNamespace(a=np.arange(4)))
        self.ESD1 = SimpleNamespace(n=0)
        self.exist = SimpleNamespace(pflow_tds=("pflow", "tds"))
        self.PFlow = SimpleNamespace(converged=True)
        self.exit_code = 0
        self.EIG = _FakeEIG()
        self.TDS = _FakeTDS(self)
        self.jacobian_updated = False

    def j_update(self, *, models: object, info: str) -> None:
        assert models == ("pflow", "tds")
        assert info
        self.jacobian_updated = True


_VSG_IDS = ("VSG_1", "VSG_2", "VSG_3", "VSG_4")
_PQ_IDS = ("PQ_0", "PQ_1", "PQ_Bus14")


def _initialized_env() -> SimpleNamespace:
    system = _FakeSystem()
    base_env = SimpleNamespace(
        ss=system,
        DT=0.2,
        vsg_idx=list(_VSG_IDS),
        _vsg_pos=np.arange(4),
    )
    return SimpleNamespace(
        base_env=base_env,
        _baseline_pref_system_pu=np.arange(1.0, 5.0),
        _vsg_indices=lambda: _VSG_IDS,
        _vsg_vector=lambda name: np.ones(4) if name == "omega" else None,
    )


def test_live_source_evaluates_literal_ports_and_restores_the_fixed_point() -> None:
    source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
        _initialized_env(),
        pq_load_ids=_PQ_IDS,
        source_fingerprint="installed-source-and-case-sha256",
    )

    f_value, g_value = source.evaluate_fixed_residual(
        vsg_tm0_delta_system_pu=np.asarray([0.1, 0.0, 0.0, -0.2]),
        pq_active_power_delta_system_pu=np.asarray([0.0, 0.3, -0.1]),
    )

    np.testing.assert_allclose(f_value, [0.1, 0.6, -0.2, -0.2])
    np.testing.assert_allclose(g_value, [-0.1, 0.9, -0.3, 0.2])
    source.restore()
    np.testing.assert_allclose(source.system.dae.f, np.zeros(4))
    np.testing.assert_allclose(source.system.dae.g, np.zeros(4))
    np.testing.assert_allclose(
        [source.system.SynGen.values[name] for name in _VSG_IDS],
        np.arange(1.0, 5.0),
    )
    np.testing.assert_allclose(source.system.PQ.Ppf.v, [11.59, 15.75, 2.48])

    snapshot = source.descriptor_snapshot
    assert source.system.jacobian_updated is True
    assert snapshot.state_names == _FakeEIG.x_name
    assert snapshot.eig_state_names == _FakeEIG.x_name
    np.testing.assert_allclose(snapshot.frequency_output_map, 60.0 * np.eye(4))


def test_live_source_rejects_a_negative_physical_load() -> None:
    source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
        _initialized_env(),
        pq_load_ids=_PQ_IDS,
        source_fingerprint="installed-source-and-case-sha256",
    )

    with pytest.raises(ValueError, match="negative physical load"):
        source.evaluate_fixed_residual(
            vsg_tm0_delta_system_pu=np.zeros(4),
            pq_active_power_delta_system_pu=np.asarray([-20.0, 0.0, 0.0]),
        )


def test_live_source_rejects_invalid_initialization_residual() -> None:
    environment = _initialized_env()
    environment.base_env.ss.TDS.residual_bias = 1.0e-3

    with pytest.raises(RuntimeError, match="initialization residual"):
        AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            environment,
            pq_load_ids=_PQ_IDS,
            source_fingerprint="installed-source-and-case-sha256",
        )


def test_live_source_rejects_positive_real_eigenvalue() -> None:
    environment = _initialized_env()
    environment.base_env.ss.EIG.matrix[0, 0] = 0.1

    with pytest.raises(RuntimeError, match="positive-real"):
        AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            environment,
            pq_load_ids=_PQ_IDS,
            source_fingerprint="installed-source-and-case-sha256",
        )
