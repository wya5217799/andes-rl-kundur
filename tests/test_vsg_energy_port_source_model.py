from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
    AndesVSGEnergyPortDescriptorSnapshot,
)
from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
    VSGEnergyPortSourceBinding,
    derive_vsg_energy_port_input_bridge,
)
from andes_rl_kundur.evaluation.vsg_energy_port_source_model import (
    construct_vsg_energy_port_source_model,
)


class _LinearSource:
    def __init__(self, binding: VSGEnergyPortSourceBinding, *, scale: float = 1.0):
        self.binding = binding
        self.scale = scale

    def evaluate_fixed_residual(
        self,
        *,
        vsg_tm0_delta_system_pu: np.ndarray,
        pq_active_power_delta_system_pu: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        disturbance = np.pad(pq_active_power_delta_system_pu, (0, 1))
        return self.scale * vsg_tm0_delta_system_pu + disturbance, np.zeros(4)

    def restore(self) -> None:
        return None


def _binding() -> VSGEnergyPortSourceBinding:
    return VSGEnergyPortSourceBinding(
        vsg_port_ids=("VSG_1", "VSG_2", "VSG_3", "VSG_4"),
        pq_load_ids=("PQ_0", "PQ_1", "PQ_Bus14"),
        sampled_omega_pu=np.ones(4),
        source_fingerprint="synthetic-source",
    )


def _snapshot() -> AndesVSGEnergyPortDescriptorSnapshot:
    return AndesVSGEnergyPortDescriptorSnapshot(
        time_constants=np.ones(4),
        f_x=-np.eye(4),
        f_y=np.zeros((4, 4)),
        g_x=np.zeros((4, 4)),
        g_y=np.eye(4),
        state_names=[f"omega VSG_{index}" for index in range(1, 5)],
        algebraic_names=[f"algebraic {index}" for index in range(4)],
        eig_state_matrix=-np.eye(4),
        eig_state_names=[f"omega VSG_{index}" for index in range(1, 5)],
        frequency_output_map=60.0 * np.eye(4),
        omega_state_addresses=np.arange(4),
        equilibrium_x=np.zeros(4),
        equilibrium_y=np.zeros(4),
        equilibrium_z=np.zeros(1),
        equilibrium_f=np.zeros(4),
        equilibrium_g=np.zeros(4),
        initialization_residual_tolerance=1.0e-6,
        initialization_max_abs_f=0.0,
        initialization_max_abs_g=0.0,
        eig_eigenvalues=-np.ones(4, dtype=complex),
        positive_real_tolerance=1.0e-7,
        positive_real_count=0,
    )


def _bridges(*, smallest_scale: float = 1.0):
    binding = _binding()
    return tuple(
        derive_vsg_energy_port_input_bridge(
            binding=binding,
            source=_LinearSource(
                binding,
                scale=smallest_scale if step == 1.0e-6 else 1.0,
            ),
            step_system_pu=step,
        )
        for step in (1.0e-4, 1.0e-5, 1.0e-6)
    )


def test_source_model_constructs_a_rank_four_end_of_hold_realization() -> None:
    result = construct_vsg_energy_port_source_model(
        snapshot=_snapshot(),
        bridges=_bridges(),
    )

    assert result.passed
    assert result.error is None
    assert result.metrics["control_markov_rank"] == 4
    assert result.sampled_model is not None
    assert result.sampled_model.input_matrix.shape == (4, 7)
    np.testing.assert_allclose(result.sampled_model.state_matrix, np.exp(-0.2) * np.eye(4))
    np.testing.assert_allclose(
        result.sampled_model.output_matrix,
        60.0 * np.exp(-0.2) * np.eye(4),
    )


def test_source_model_stops_before_reduction_when_derivatives_do_not_converge() -> None:
    result = construct_vsg_energy_port_source_model(
        snapshot=_snapshot(),
        bridges=_bridges(smallest_scale=1.1),
    )

    assert not result.passed
    assert result.sampled_model is None
    assert result.error == "finite-difference input columns did not converge"


def test_source_model_name_mismatch_failure_metrics_are_json_serializable() -> None:
    snapshot = _snapshot()
    snapshot = AndesVSGEnergyPortDescriptorSnapshot(
        **{
            **snapshot.__dict__,
            "eig_state_names": ["wrong state"] * 4,
        }
    )

    result = construct_vsg_energy_port_source_model(
        snapshot=snapshot,
        bridges=_bridges(),
    )

    assert not result.passed
    assert result.error == "descriptor model did not reconcile with installed ANDES"
    assert result.metrics["state_matrix_relative_frobenius_error"] is None
    assert result.metrics["state_matrix_maximum_absolute_error"] is None
