"""R435 multiplier-floor learner: frozen CDMATD3 + a floor on the dual variable.

The R432 diagnostics (CLM-1320) showed the lagrange multiplier decaying from
~0.97 to ~0.0 in 4/6 runs while the per-episode common cost never
systematically improved, giving the bounded hypothesis: "the budget
mechanism stops pressing early in training, so nothing drives the
common-frequency cost down".  R435 tests that hypothesis causally with ONE
single factor: the frozen dual update keeps its exact formula, but the
multiplier is clipped at a pre-registered floor (never decays below it), so
the mechanism keeps pressing at its starting level for the whole run.

The frozen ``cd_matd3.py`` file is byte-unchanged; this module only
subclasses it (R419 lesson: learner seams live in separate modules, never
in the sealed learner file).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.agents.cd_matd3 import CDMATD3


class LagrangeFloorMixin:
    """Frozen dual update with the R435 floor: ``clip(updated, floor, max)``.

    The only semantic change vs the frozen ``lagrange_step`` is the lower
    clip bound (0.0 -> ``lagrange_floor``); the violation signal
    ``step * (episode_common_cost - budget)`` and the upper clip are
    verbatim.  The actor loss weighting ``q1[:,0] + lagrange * q1[:,1]``
    is untouched, so the multiplier can never fully relax.
    """

    def __init__(self, lagrange_floor: float = 1.0, **kwargs: Any) -> None:
        self._lagrange_floor = float(lagrange_floor)
        super().__init__(**kwargs)

    def lagrange_step(
        self,
        episode_common_cost: float,
        budget: float,
        step: float,
        maximum: float,
    ) -> float:
        """Frozen dual update; the multiplier never decays below the floor."""

        updated = self.lagrange + float(step) * (
            float(episode_common_cost) - float(budget)
        )
        self._lagrange = float(
            np.clip(updated, float(self._lagrange_floor), float(maximum))
        )
        return self.lagrange


class FlooredCDMATD3(LagrangeFloorMixin, CDMATD3):
    """The frozen CDMATD3 learner with the R435 multiplier floor."""
