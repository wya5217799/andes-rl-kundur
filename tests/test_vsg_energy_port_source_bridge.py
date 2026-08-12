from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
    VSGEnergyPortSourceBinding,
    derive_vsg_energy_port_input_bridge,
)


class _RestoringLinearResidualSource:
    def __init__(self, binding: VSGEnergyPortSourceBinding) -> None:
        self.binding = binding
        self.clean = True

    def evaluate_fixed_residual(
        self,
        *,
        vsg_tm0_delta_system_pu: np.ndarray,
        pq_active_power_delta_system_pu: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        if not self.clean:
            raise RuntimeError("source must be restored between evaluations")
        self.clean = False
        control = np.asarray(vsg_tm0_delta_system_pu, dtype=float)
        disturbance = np.asarray(pq_active_power_delta_system_pu, dtype=float)
        disturbance_output = np.zeros(4, dtype=float)
        disturbance_output[:3] = disturbance
        return (
            control + 2.0 * disturbance_output,
            -control + 3.0 * disturbance_output,
        )

    def restore(self) -> None:
        self.clean = True


def _binding() -> VSGEnergyPortSourceBinding:
    return VSGEnergyPortSourceBinding(
        vsg_port_ids=("VSG_1", "VSG_2", "VSG_3", "VSG_4"),
        pq_load_ids=("PQ_0", "PQ_1", "PQ_Bus14"),
        sampled_omega_pu=np.asarray([0.5, 1.0, 2.0, 4.0]),
        source_fingerprint="synthetic-source-sha256",
    )


def test_source_bridge_derives_separate_power_and_load_input_columns() -> None:
    binding = _binding()
    source = _RestoringLinearResidualSource(binding)

    bridge = derive_vsg_energy_port_input_bridge(
        binding=binding,
        source=source,
        step_system_pu=1.0e-6,
    )

    expected_power_to_tm0 = np.diag([2.0, 1.0, 0.5, 0.25])
    np.testing.assert_allclose(bridge.power_to_tm0_jacobian, expected_power_to_tm0)
    np.testing.assert_allclose(bridge.control.f_input, expected_power_to_tm0)
    np.testing.assert_allclose(bridge.control.g_input, -expected_power_to_tm0)
    expected_disturbance = np.asarray(
        [
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 2.0],
            [0.0, 0.0, 0.0],
        ]
    )
    np.testing.assert_allclose(bridge.disturbance.f_input, expected_disturbance)
    np.testing.assert_allclose(bridge.disturbance.g_input, 1.5 * expected_disturbance)
    np.testing.assert_allclose(
        bridge.joint_f_input,
        np.hstack((expected_power_to_tm0, expected_disturbance)),
    )
    assert bridge.provenance.source_fingerprint == "synthetic-source-sha256"
    assert source.clean


def test_source_bridge_rejects_a_callback_bound_to_different_devices() -> None:
    expected = _binding()
    actual = VSGEnergyPortSourceBinding(
        vsg_port_ids=("VSG_A", "VSG_B", "VSG_C", "VSG_D"),
        pq_load_ids=expected.pq_load_ids,
        sampled_omega_pu=expected.sampled_omega_pu,
        source_fingerprint=expected.source_fingerprint,
    )

    with pytest.raises(ValueError, match="source binding"):
        derive_vsg_energy_port_input_bridge(
            binding=expected,
            source=_RestoringLinearResidualSource(actual),
            step_system_pu=1.0e-6,
        )


@pytest.mark.parametrize(
    ("vsg_port_ids", "pq_load_ids"),
    [
        (
            ("VSG_1", "VSG_1", "VSG_3", "VSG_4"),
            ("PQ_0", "PQ_1", "PQ_Bus14"),
        ),
        (
            ("VSG_1", "VSG_2", "VSG_3", "VSG_4"),
            ("PQ_0", "PQ_1", "PQ_1"),
        ),
        (
            ("VSG_1", "VSG_2", "VSG_3"),
            ("PQ_0", "PQ_1", "PQ_Bus14"),
        ),
        (
            ("VSG_1", "VSG_2", "VSG_3", "VSG_4"),
            ("PQ_0", "PQ_1", ""),
        ),
    ],
)
def test_source_binding_requires_four_distinct_vsg_and_load_identities(
    vsg_port_ids: tuple[str, ...],
    pq_load_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="four distinct VSG and three distinct PQ"):
        VSGEnergyPortSourceBinding(
            vsg_port_ids=vsg_port_ids,
            pq_load_ids=pq_load_ids,
            sampled_omega_pu=np.ones(4),
            source_fingerprint="synthetic-source-sha256",
        )


@pytest.mark.parametrize(
    (
        "source_fingerprint",
        "port_semantics",
        "legacy_md_action_enabled",
        "nominal_frequency_hz",
        "sample_period_seconds",
        "message",
    ),
    [
        (
            "",
            "VSG-owned sampled pref/tm0 port; no ESD1",
            False,
            60.0,
            0.2,
            "source_fingerprint",
        ),
        ("source", "ESD1 Pext0", False, 60.0, 0.2, "port_semantics"),
        (
            "source",
            "VSG-owned sampled pref/tm0 port; no ESD1",
            True,
            60.0,
            0.2,
            "legacy_md_action_enabled",
        ),
        (
            "source",
            "VSG-owned sampled pref/tm0 port; no ESD1",
            False,
            50.0,
            0.2,
            "nominal_frequency_hz",
        ),
        (
            "source",
            "VSG-owned sampled pref/tm0 port; no ESD1",
            False,
            60.0,
            0.1,
            "sample_period_seconds",
        ),
    ],
)
def test_source_binding_rejects_a_different_physical_object(
    source_fingerprint: str,
    port_semantics: str,
    legacy_md_action_enabled: bool,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        VSGEnergyPortSourceBinding(
            vsg_port_ids=("VSG_1", "VSG_2", "VSG_3", "VSG_4"),
            pq_load_ids=("PQ_0", "PQ_1", "PQ_Bus14"),
            sampled_omega_pu=np.ones(4),
            source_fingerprint=source_fingerprint,
            port_semantics=port_semantics,
            legacy_md_action_enabled=legacy_md_action_enabled,
            nominal_frequency_hz=nominal_frequency_hz,
            sample_period_seconds=sample_period_seconds,
        )
