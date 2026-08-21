"""R423 value-estimation repair subclasses for the CD-MATD3 learner family.

The R423 single factor (bounded literature menu
``paper/yang_md_decoupling_marl/working/r423_value_estimation_repair_deep_research_2026-08-17.md``,
P3): the CD-arm critic update path gains a frozen gradient clip
(``torch.nn.utils.clip_grad_norm_``, ``max_norm`` = 1.0) applied between
``loss.backward()`` and the critic optimizer step.  Everything else — the
reward seam, the actor update, the Lagrange machinery, the scalar learner —
stays verbatim from the sealed R422 bundle.

These classes live in this separate module so the sealed learner file
(``andes_rl_kundur/agents/cd_matd3.py``) never drifts from the
R419/R420/R422 seals.  Import them here, never from cd_matd3.
"""

from __future__ import annotations

from collections.abc import Mapping

import torch
import torch.nn.functional as F

from andes_rl_kundur.agents.cd_matd3 import SlewAwareCDMATD3

CRITIC_GRAD_CLIP_MAX_NORM = 1.0  # frozen R423 repair hyperparameter


class ClippedCriticSlewAwareCDMATD3(SlewAwareCDMATD3):
    """CD arm with the frozen R423 repair: critic gradient clipping.

    The override replicates the sealed base ``_critic_update`` computation
    verbatim and inserts exactly one frozen change — the gradient clip —
    between backward and step.  The actor update, the Lagrange step, the
    reward seam, and every other hyperparameter are inherited unchanged.
    """

    def _critic_update(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        with torch.no_grad():
            next_actions = self._target_actions(batch)
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(q1_next, q2_next)
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        loss.backward()
        # R423 single factor: frozen critic gradient clip (see module
        # docstring and the R423 plan frozen protocol).
        torch.nn.utils.clip_grad_norm_(
            self.critic.parameters(), CRITIC_GRAD_CLIP_MAX_NORM
        )
        self.critic_optimizer.step()
        return loss.detach()
