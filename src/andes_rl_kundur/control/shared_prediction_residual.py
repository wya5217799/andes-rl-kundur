"""Frozen R341-model shared-prediction message generation for edge actors.

The module owns the causal generation of DMPC-style shared prediction
messages: for one verified R352 zero/local trace, it advances the frozen
R341 separate-input disturbance-augmented estimator over causal pre-action
samples and returns, for every reconstructible causal instant, the open-loop
four-step frequency-deviation prediction of each node.  It owns no simulator,
experiment split, oracle, or research classification; every parameter is
frozen and tuning-free.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.model_first_distributed_edge import (
    LocalEdgeObservation,
)
from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputEstimatorDesign,
    SeparateInputRealization,
    advance_separate_input_estimate,
    synthesize_separate_input_estimator,
)
from andes_rl_kundur.control.neighbour_causal_residual import (
    OBSERVATION_DIMENSION,
    observation_vector,
)
from andes_rl_kundur.control.neighbour_message_residual import (
    ONE_HOP_NEIGHBOUR_MESSAGES,
)
from andes_rl_kundur.env.andes.model_first_contract import (
    weighted_common_differential_transform,
)
from andes_rl_kundur.evaluation.model_first_physical_bridge import (
    frequency_coordinate_trace,
)

PREDICTION_STEPS = 4
DISTURBANCE_SCALE = 0.05
MEASUREMENT_FRACTION = 0.01
SHARED_PREDICTION_OBSERVATION_DIMENSION = (
    OBSERVATION_DIMENSION + 2 * PREDICTION_STEPS
)


@dataclass(frozen=True)
class SharedPredictionMessage:
    """Four-step causal open-loop frequency-deviation prediction (Hz)."""

    node_id: int
    values_hz: np.ndarray

    def __post_init__(self) -> None:
        if int(self.node_id) < 0 or int(self.node_id) > 3:
            raise ValueError("node_id must lie in the frozen four-node plant")
        values = np.asarray(self.values_hz, dtype=float)
        if values.shape != (PREDICTION_STEPS,) or not np.all(np.isfinite(values)):
            raise ValueError("prediction message must contain four finite values")


@dataclass(frozen=True)
class SharedPredictionObservation:
    """The complete deployed input of one shared-prediction edge actor."""

    edge: tuple[int, int]
    observation: LocalEdgeObservation
    source_neighbour_prediction: SharedPredictionMessage
    target_neighbour_prediction: SharedPredictionMessage

    def __post_init__(self) -> None:
        edge = tuple(int(value) for value in self.edge)
        if edge not in ONE_HOP_NEIGHBOUR_MESSAGES:
            raise ValueError("edge must be one of the frozen action edges")
        source_id, target_id = ONE_HOP_NEIGHBOUR_MESSAGES[edge]
        if (
            self.source_neighbour_prediction.node_id,
            self.target_neighbour_prediction.node_id,
        ) != (source_id, target_id):
            raise ValueError("predictions do not match the frozen neighbour table")


def shared_prediction_observation_vector(
    item: SharedPredictionObservation,
) -> np.ndarray:
    """Return the ordered twenty-three-field shared-prediction vector."""

    vector = np.concatenate(
        (
            observation_vector(item.observation),
            np.asarray(item.source_neighbour_prediction.values_hz, dtype=float),
            np.asarray(item.target_neighbour_prediction.values_hz, dtype=float),
        )
    )
    if (
        vector.shape != (SHARED_PREDICTION_OBSERVATION_DIMENSION,)
        or not np.all(np.isfinite(vector))
    ):
        raise ValueError(
            "shared-prediction observation vector must contain twenty-three finite values"
        )
    return vector


def _prediction_matrix(
    design: SeparateInputEstimatorDesign,
    *,
    state: np.ndarray,
    future_control: np.ndarray,
    steps: int,
) -> np.ndarray:
    """Open-loop transition with frozen future residual control and disturbance."""

    steps = int(steps)
    if steps < 1:
        raise ValueError("prediction horizon must be positive")
    transition = np.asarray(design.transition_matrix, dtype=float)
    control = np.asarray(design.control_matrix, dtype=float)
    measurement = np.asarray(design.measurement_matrix, dtype=float)
    order = transition.shape[0]
    if state.shape != (order,) or not np.all(np.isfinite(state)):
        raise ValueError("state estimate has invalid shape or values")
    if future_control.shape != (4,) or not np.all(np.isfinite(future_control)):
        raise ValueError("future control must contain four finite values")
    predicted_states: list[np.ndarray] = []
    current = np.asarray(state, dtype=float).copy()
    for _ in range(steps):
        current = transition @ current + control @ future_control
        predicted_states.append(current)
    outputs = np.vstack([measurement @ item for item in predicted_states])
    if outputs.shape != (steps, 4) or not np.all(np.isfinite(outputs)):
        raise ValueError("open-loop prediction returned invalid outputs")
    return outputs


def generate_shared_predictions(
    *,
    model: SeparateInputRealization,
    output_scales: Sequence[float],
    frequency_hz_after_action: object,
    commanded_node_power_after_action: object,
    achieved_node_power_after_action: object,
    inertia_system: object,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
    startup_zero_steps: int,
    prediction_steps: int = PREDICTION_STEPS,
    control_basis_inverse: object | None = None,
) -> dict[int, np.ndarray]:
    """Return per-node causal prediction traces for one frozen point model.

    The estimator is advanced only over causal pre-action samples: for every
    reconstructible instant ``k`` (``startup_zero_steps <= k < horizon``) the
    returned row ``k`` uses observations ``0..k-1`` and predicts
    ``k+1..k+prediction_steps``.  The first ``startup_zero_steps`` rows are
    all-zero because complete pre-action history is not reconstructible there.

    ``control_basis_inverse`` maps achieved node power to the frozen control
    coordinates; when omitted, the identity map is used (four node powers are
    treated as four independent control coordinates).
    """

    frequency = np.asarray(frequency_hz_after_action, dtype=float)
    commanded = np.asarray(commanded_node_power_after_action, dtype=float)
    achieved = np.asarray(achieved_node_power_after_action, dtype=float)
    horizon = frequency.shape[0]
    if (
        frequency.shape != (horizon, 4)
        or commanded.shape != (horizon, 4)
        or achieved.shape != (horizon, 4)
        or not all(
            np.all(np.isfinite(item)) for item in (frequency, commanded, achieved)
        )
    ):
        raise ValueError("trace arrays must share one finite four-column horizon")
    nominal = float(nominal_frequency_hz)
    sample_period = float(sample_period_seconds)
    startup = int(startup_zero_steps)
    steps = int(prediction_steps)
    if not np.isfinite(nominal) or nominal <= 0.0:
        raise ValueError("nominal_frequency_hz must be positive and finite")
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")
    if startup < 2 or startup >= horizon:
        raise ValueError("at least two startup rows must precede predictions")
    if steps < 1 or steps > horizon:
        raise ValueError("prediction horizon must lie within the trace horizon")

    scales = np.asarray(output_scales, dtype=float)
    if scales.shape != (4,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("output_scales must contain four positive finite values")
    design = synthesize_separate_input_estimator(
        model,
        output_scales=scales,
        disturbance_scale=DISTURBANCE_SCALE,
        measurement_fraction=MEASUREMENT_FRACTION,
    )
    coordinates = frequency_coordinate_trace(
        frequency,
        reference_frequency_hz=np.full(4, float(nominal)),
        inertia_system=inertia_system,
        physical_nominal_frequency_hz=float(nominal),
    )
    if control_basis_inverse is None:
        inverse_basis = np.eye(4)
    else:
        inverse_basis = np.asarray(control_basis_inverse, dtype=float)
        if inverse_basis.shape != (4, 4) or not np.all(np.isfinite(inverse_basis)):
            raise ValueError("control_basis_inverse must be a finite four-by-four matrix")

    predictions: dict[int, list[np.ndarray]] = {node: [] for node in range(4)}
    prior = np.zeros(design.transition_matrix.shape[0])
    for step in range(horizon):
        if step < startup:
            for node in range(4):
                predictions[node].append(np.zeros(steps))
            continue
        delivered = coordinates[step - 1]
        executed = inverse_basis @ achieved[step - 1]
        estimate = advance_separate_input_estimate(
            design,
            prior_estimate=prior,
            previous_delivered_output=delivered,
            previous_executed_control=executed,
        )
        prior = estimate.predicted_estimate.copy()
        future_control = inverse_basis @ commanded[step - 1]
        outputs = _prediction_matrix(
            design,
            state=estimate.predicted_estimate,
            future_control=future_control,
            steps=steps,
        )
        inverse = weighted_common_differential_transform(inertia_system).inverse
        per_unit = (inverse @ outputs.T).T
        frequency_deviation_hz = per_unit * float(nominal)
        for node in range(4):
            predictions[node].append(frequency_deviation_hz[:, node].copy())
    return {node: np.vstack(rows) for node, rows in predictions.items()}
