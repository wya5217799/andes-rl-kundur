"""R125 — Stacked TD3+LSTM with QR distributional critic + AFE input.

Combines R98 CLM-0157(a) [td3_qr_lstm] + (b) [td3_afe_lstm] into one agent.
Critic input: ``[obs, a, a², |a|, sign(a)]`` (AFE); critic output: 51 quantiles
(QR). Actor backbone unchanged.

Rationale: AFE gives the critic *input* a direct pathway to quadratic /
|·| / sign(·) action features (CLM-0150 d²Q/da² ≈ 0 fix); QR gives the
critic *output* a full return distribution (CLM-0148 affine-Q fix). The
two interventions act at orthogonal points in the network so they should
compose cleanly. If single-axis prototypes (R122 / R123 / R124) only
partly break the plateau, R125 + tests whether the stacked fix is
additive.

Interface compatible with ``BaseAgent`` Protocol; ``train.py`` can dispatch
via ``--algo td3_qr_afe_lstm`` after a 5-line elif branch (R125+).
"""
from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks_critic_variants import (
    N_QUANTILES_DEFAULT,
    RecurrentQRAfeDoubleQCritic,
)
from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent


class TD3QRAfeLstmAgent(TD3QRLstmAgent):
    """Stacked QR + AFE critic. Inherits all QR training plumbing
    (quantile-Huber loss, distributional update) from ``TD3QRLstmAgent``;
    only the critic class is swapped to the QR+AFE variant which expands
    the action input internally.
    """

    algo_name: str = "td3_qr_afe_lstm"

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: int | Sequence[int],
        n_quantiles: int = N_QUANTILES_DEFAULT,
        **kwargs: Any,
    ) -> None:
        # super().__init__ wires QR critic; we then swap to QR+AFE critic.
        super().__init__(
            obs_dim=obs_dim,
            action_dim=action_dim,
            hidden_sizes=hidden_sizes,
            n_quantiles=n_quantiles,
            **kwargs,
        )

        lr = self._target_lr
        hidden = self.hidden

        # Replace with QR+AFE variant
        self.critic = RecurrentQRAfeDoubleQCritic(
            obs_dim, action_dim, hidden=hidden, n_quantiles=self.n_quantiles
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
        """Save with ``algo: "td3_qr_afe_lstm"`` + ``n_quantiles`` hparam."""
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
                    "n_quantiles": self.n_quantiles,
                },
            },
            path,
        )
        if save_buffer:
            pass
