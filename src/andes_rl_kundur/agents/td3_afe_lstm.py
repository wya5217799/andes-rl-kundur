"""R98 — TD3 with LSTM actor + action-feature-engineered critic (CLM-0157(b)).

Min-viable-diff fix for the affine-Q pathology (CLM-0150). The actor and the
critic *backbone* are unchanged; only the critic's **input feature**
construction differs:

  base:  critic eats ``[obs, action]``               (obs_dim + A)
  AFE:   critic eats ``[obs, a, a², |a|, sign(a)]``  (obs_dim + 4A)

This lets the bilinear LSTM-cell first layer express concave-around-interior
preference without architectural change — the ``a²`` block alone breaks the
"d²Q/da² ≈ 0" pathology CLM-0150 documented, because the critic now has a
linear pathway to a quadratic feature. ``|a|`` + ``sign(a)`` add saturation-
magnitude awareness without sign-coupling.

Interface-compatible with ``BaseAgent`` Protocol. Update loop, save, load are
all inherited unchanged — the AFE Q network has the same forward signature
``(obs, action, h_prev) → (q, h_new)`` and the same scalar Q output as
``RecurrentQNetwork``, so ``TD3LSTMAgent.update()`` works bit-for-bit.

train.py integration is deferred (CLM-0157 gate on R83 verdict). When ready,
add ``"td3_afe_lstm": TD3AfeLstmAgent`` to the dispatch table.
"""
from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks_critic_variants import (
    RecurrentAfeDoubleQCritic,
)
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent


class TD3AfeLstmAgent(TD3LSTMAgent):
    """TD3-LSTM with action-feature-engineered critic input.

    Only ``__init__`` is overridden — the AFE critic is wired in place of
    the standard ``RecurrentDoubleQCritic``. Everything else (actor, buffer,
    update loop, warmup, save / load) is inherited unchanged.
    """

    algo_name: str = "td3_afe_lstm"

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: int | Sequence[int],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            obs_dim=obs_dim,
            action_dim=action_dim,
            hidden_sizes=hidden_sizes,
            **kwargs,
        )

        # Replace the critic with the AFE variant. Reuse hidden + lr that
        # the base __init__ chose, so warmup ramp logic in the base class
        # continues to work without further changes.
        lr = self._target_lr
        hidden = self.hidden

        self.critic = RecurrentAfeDoubleQCritic(
            obs_dim, action_dim, hidden=hidden
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

    def save(
        self,
        path: str,
        metadata: dict | None = None,
        save_buffer: bool = False,
    ) -> None:
        """Save with ``algo: "td3_afe_lstm"`` for checkpoint_loader dispatch.

        Loading a base TD3LSTMAgent ckpt with this class fails loudly via
        critic shape mismatch (input dim 7+2 vs 7+8) — class confusion is
        not silent.
        """
        torch.save(
            {
                "actor": self.actor.state_dict(),
                "actor_target": self.actor_target.state_dict(),
                "critic": self.critic.state_dict(),
                "critic_target": self.critic_target.state_dict(),
                "actor_opt": self.actor_optimizer.state_dict(),
                "critic_opt": self.critic_optimizer.state_dict(),
                "metadata": metadata or {},
                "algo": self.algo_name,
                "hparams": {
                    "obs_dim": self.obs_dim,
                    "action_dim": self.action_dim,
                    "hidden": self.hidden,
                    "seq_len": self.seq_len,
                    "burn_in": self.burn_in,
                },
            },
            path,
        )
        if save_buffer:
            pass
