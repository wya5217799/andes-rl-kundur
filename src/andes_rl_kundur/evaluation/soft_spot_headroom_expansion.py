"""Frozen A3 headroom-expansion contract for the soft-spot program (R416).

Extends the R399 finite nine-law family in one registered step: a densified
local-neighbour gain grid (five inertia gains x four damping gains = 20
laws, containing the original nine) plus one PI-type signed
proportional-integral frequency law (21 candidates in total).  The frozen
R399 profiles, estimators, thresholds, guards, and the outcome-seeing
oracle semantics are consumed verbatim; ``md_decoupling_headroom.
classify_bank`` is reused unchanged with this contract, so the oracle
headroom delta is measured over the expanded family on the same four
evaluation profiles.

The nine original laws serve as the identity anchor: their re-evaluated
summaries must reproduce the R399 records bit-identically.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.per_vsg_md import (
    LocalMDActionProjector,
    LocalNeighbourMDContract,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (
    build_contract as _r399_contract,
)

ROUND_ID = "R416"

# Densified grid: the original gains {0.5, 1.0, 2.0} extended by 1.5 and 3.0
# on the inertia axis and 1.5 on the damping axis.
EXTENDED_INERTIA_GAINS = (0.5, 1.0, 1.5, 2.0, 3.0)
EXTENDED_DAMPING_GAINS = (0.5, 1.0, 1.5, 2.0)

PI_ARM_ID = "pi_frequency_md"
PI_KP_M = 1.0
PI_KI_M = 0.4
PI_KP_D = 1.0
PI_KI_D = 0.4
PI_INTEGRAL_CLIP = 2.0
PI_SLEW_LIMIT = 0.25


class PiFrequencyMDController:
    """Frozen PI-type law: signed proportional-integral frequency feedback.

    Per VSG, in the adapted observation's own scaled frequency units
    (``df`` = adapted slot 1, ``dt`` = 0.2 s):

        u^M_i = tanh(-kp_m * df_i - ki_m * I_i),
        u^D_i = tanh(-kp_d * df_i - ki_d * I_i),
        I_i   <- clip(I_i + df_i * dt, -clip, +clip),

    with the registered per-agent slew projector.  Both targets share the
    same PI signal; this is one law, not a tuned grid.
    """

    architecture = "per_vsg_signed_pi_frequency_feedback"

    def __init__(self) -> None:
        self.projectors = tuple(
            LocalMDActionProjector(action_slew_limit=PI_SLEW_LIMIT)
            for _ in range(4)
        )
        self.integrals = np.zeros(4, dtype=np.float64)

    def reset(self) -> None:
        for projector in self.projectors:
            projector.reset()
        self.integrals = np.zeros(4, dtype=np.float64)

    def act(self, observations: Mapping[int, Sequence[float] | np.ndarray]) -> np.ndarray:
        if set(observations) != set(range(4)):
            raise ValueError("observations must contain exactly actors 0..3")
        actions = []
        for actor in range(4):
            row = np.asarray(observations[actor], dtype=np.float64)
            if row.shape != (7,) or not np.all(np.isfinite(row)):
                raise ValueError("each observation must be a finite 7-row")
            frequency = float(row[1])
            self.integrals[actor] = float(
                np.clip(
                    self.integrals[actor] + frequency * 0.2,
                    -PI_INTEGRAL_CLIP,
                    PI_INTEGRAL_CLIP,
                )
            )
            signal = -PI_KP_M * frequency - PI_KI_M * self.integrals[actor]
            target = np.asarray(
                [
                    np.tanh(signal),
                    np.tanh(-PI_KP_D * frequency - PI_KI_D * self.integrals[actor]),
                ],
                dtype=np.float32,
            )
            actions.append(self.projectors[actor].project(target))
        return np.stack(actions).astype(np.float32)


def extended_candidate_ids() -> list[str]:
    """The frozen 21 candidate ids: 20 grid laws + the PI law."""
    return [
        LocalNeighbourMDContract(
            inertia_gain=inertia, damping_gain=damping
        ).name
        for inertia in EXTENDED_INERTIA_GAINS
        for damping in EXTENDED_DAMPING_GAINS
    ] + [PI_ARM_ID]


def original_nine_ids() -> list[str]:
    return [row.name for row in local_neighbour_md_candidates()]


def build_contract() -> dict[str, Any]:
    """R399 contract verbatim with the expanded frozen candidate family."""
    contract = copy.deepcopy(_r399_contract())
    contract["round"] = ROUND_ID
    contract["candidate_arm_ids"] = extended_candidate_ids()
    contract["arm_ids"] = ["zero", *extended_candidate_ids()]
    contract["expansion"] = {
        "extended_inertia_gains": list(EXTENDED_INERTIA_GAINS),
        "extended_damping_gains": list(EXTENDED_DAMPING_GAINS),
        "pi_law": {
            "arm_id": PI_ARM_ID,
            "kp_m": PI_KP_M,
            "ki_m": PI_KI_M,
            "kp_d": PI_KP_D,
            "ki_d": PI_KI_D,
            "integral_clip": PI_INTEGRAL_CLIP,
            "slew_limit": PI_SLEW_LIMIT,
            "dt_seconds": 0.2,
        },
        "original_nine_ids": original_nine_ids(),
    }
    return contract


def controller_for(arm_id: str) -> Any:
    """Resolve one arm to its frozen runtime controller (None for zero)."""
    if arm_id == "zero":
        return None
    if arm_id == PI_ARM_ID:
        return PiFrequencyMDController()
    prefix = "local_neighbour_md_km"
    if not arm_id.startswith(prefix):
        raise ValueError(f"unknown arm: {arm_id}")
    tail = arm_id[len(prefix):]
    inertia_text, separator, damping_text = tail.partition("_kd")
    if not separator:
        raise ValueError(f"unknown arm: {arm_id}")
    try:
        inertia = float(inertia_text.replace("p", "."))
        damping = float(damping_text.replace("p", "."))
    except ValueError as exc:
        raise ValueError(f"unknown arm: {arm_id}") from exc
    contract = LocalNeighbourMDContract(
        inertia_gain=inertia, damping_gain=damping
    )
    from andes_rl_kundur.control.per_vsg_md import LocalNeighbourMDExecution

    return LocalNeighbourMDExecution(contract)


__all__ = [
    "PI_ARM_ID",
    "build_contract",
    "controller_for",
    "extended_candidate_ids",
    "original_nine_ids",
]
