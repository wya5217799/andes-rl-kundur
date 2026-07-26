"""R98 — TD3 with LSTM actor + quantile-regression (QR) distributional critic.

Drop-in replacement for ``TD3LSTMAgent`` (CLM-0157 priority (a)). Actor is
unchanged; only the critic's output head + training loss differ. The TD-based
critic now learns a distribution over the return (51 quantiles) instead of a
scalar mean, breaking the affine-Q pathology documented in CLM-0148-0156.

Mechanism intuition (CLM-0150 / CLM-0170):
  Scalar TD critic + bilinear LSTM first layer → critic learns ``Q(s, a) ≈
  linear in a`` (d²Q/da² ≈ 0), pushing argmax to boundary ±1. Actor ends up
  saturated (CLM-0170 bang-bang). Distributional critic forces the critic to
  fit the FULL return distribution at every (s, a) — including its spread —
  which has been shown empirically (Bellemare et al. 2017, Dabney et al. 2018)
  to produce richer action-conditional representations even when the actor is
  identical.

This agent is interface-compatible with ``BaseAgent`` Protocol:
  - ``select_action`` / ``select_action_recurrent`` — inherited unchanged
  - ``store_transition`` / ``flush_episode`` — inherited unchanged
  - ``begin_episode`` — inherited unchanged
  - ``update`` — REWRITTEN to use quantile-Huber loss instead of MSE
  - ``save`` / ``load`` — inherited (writes ``algo_name`` so loader can
    dispatch); checkpoint can be loaded with this class only.

train.py integration is NOT done in R98 (gated on R83 verdict per CLM-0157);
when ready, add ``"td3_qr_lstm": TD3QRLstmAgent`` to the dispatch table.
"""
from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks_critic_variants import (
    N_QUANTILES_DEFAULT,
    RecurrentQRDoubleQCritic,
    quantile_huber_loss,
)
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent, _detach_h


class TD3QRLstmAgent(TD3LSTMAgent):
    """TD3-LSTM with quantile-regression distributional critic head.

    Differences from ``TD3LSTMAgent``:
      - critic is ``RecurrentQRDoubleQCritic`` (twin LSTMCell + 51-quantile head)
      - critic loss is ``quantile_huber_loss`` instead of MSE
      - TD3 min-Q target trick uses scalar mean-of-quantiles comparator
      - actor loss uses ``mean(q1_quantiles)`` (== scalar Q proxy)
      - checkpoint stores ``algo: "td3_qr_lstm"`` + ``n_quantiles`` hparam
    """

    algo_name: str = "td3_qr_lstm"

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: int | Sequence[int],
        n_quantiles: int = N_QUANTILES_DEFAULT,
        **kwargs: Any,
    ) -> None:
        # Initialise the base class for everything actor / buffer / warmup-
        # related, then *replace* the critic + critic_target + critic_optimizer
        # with the quantile-regression variant. lr is the same on both
        # optimizers so warmup ramp logic in the base class still works.
        super().__init__(
            obs_dim=obs_dim,
            action_dim=action_dim,
            hidden_sizes=hidden_sizes,
            **kwargs,
        )

        self.n_quantiles = int(n_quantiles)

        # Replace scalar-Q critic with QR critic. Use the same ``hidden`` and
        # same lr as the base class chose.
        lr = self._target_lr
        # Determine hidden from base init (single int)
        hidden = self.hidden

        self.critic = RecurrentQRDoubleQCritic(
            obs_dim, action_dim, hidden=hidden, n_quantiles=self.n_quantiles
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

    # ─── Gradient update (quantile-Huber) ──────────────────────────────────

    def update(self) -> dict[str, Any] | None:
        """Override base ``update`` to use quantile-Huber critic loss.

        Structurally mirrors :meth:`TD3LSTMAgent.update` — burn-in,
        critic roll, delayed actor roll — but at each TD step:

          - target quantiles ``y = r + γ(1-d) target_q_chosen`` are computed
            from the *target* critic's quantile vector for the smoothed
            target action; min-Q is decided by the scalar-mean comparator
          - current critic outputs (q1_quantiles, q2_quantiles) and the
            loss is ``quantile_huber_loss(q_i, y)`` for i ∈ {1, 2}
          - actor loss = ``-mean(q1_quantiles)`` over the actor's
            current-policy action

        Returns the same dict shape as the base agent: ``{"critic_loss": …}``
        (and ``"actor_loss": …`` when the policy_delay fires).
        """
        batch = self.buffer.sample(self.batch_size, self.device)
        if batch is None:
            return None

        if not self._this_episode_seen_update:
            self._episode_count += 1
            self._this_episode_seen_update = True
        self._apply_lr_warmup()
        self._update_count += 1

        obs = batch["obs"]
        actions = batch["actions"]
        rewards = batch["rewards"]
        next_obs = batch["next_obs"]
        dones = batch["dones"]
        B = obs.shape[0]

        # ─── Burn-in ─────────────────────────────────────────────────
        with torch.no_grad():
            h_a = self.actor.init_hidden(B, self.device)
            h_a_tgt = self.actor_target.init_hidden(B, self.device)
            h_c1 = self.critic.q1.init_hidden(B, self.device)
            h_c2 = self.critic.q2.init_hidden(B, self.device)
            h_c1_tgt = self.critic_target.q1.init_hidden(B, self.device)
            h_c2_tgt = self.critic_target.q2.init_hidden(B, self.device)
            for t in range(self.burn_in):
                _, h_a = self.actor(obs[:, t], h_a)
                _, h_a_tgt = self.actor_target(obs[:, t], h_a_tgt)
                _, h_c1 = self.critic.q1(obs[:, t], actions[:, t], h_c1)
                _, h_c2 = self.critic.q2(obs[:, t], actions[:, t], h_c2)
                _, h_c1_tgt = self.critic_target.q1(
                    obs[:, t], actions[:, t], h_c1_tgt
                )
                _, h_c2_tgt = self.critic_target.q2(
                    obs[:, t], actions[:, t], h_c2_tgt
                )
            _, h_a_tgt = self.actor_target(obs[:, self.burn_in], h_a_tgt)

        h_a = _detach_h(h_a)
        h_a_tgt = _detach_h(h_a_tgt)
        h_c1 = _detach_h(h_c1)
        h_c2 = _detach_h(h_c2)
        h_c1_tgt = _detach_h(h_c1_tgt)
        h_c2_tgt = _detach_h(h_c2_tgt)

        # ─── Critic roll (quantile-Huber) ─────────────────────────────
        h_c1_critic = h_c1
        h_c2_critic = h_c2
        critic_losses: list[torch.Tensor] = []
        for t in range(self.burn_in, self.burn_in + self.seq_len):
            with torch.no_grad():
                _, h_c1_tgt = self.critic_target.q1(
                    obs[:, t], actions[:, t], h_c1_tgt
                )
                _, h_c2_tgt = self.critic_target.q2(
                    obs[:, t], actions[:, t], h_c2_tgt
                )
                target_a_raw, h_a_tgt = self.actor_target(next_obs[:, t], h_a_tgt)
                noise = (
                    torch.randn_like(target_a_raw) * self.policy_noise
                ).clamp(-self.noise_clip, self.noise_clip)
                target_a = (target_a_raw + noise).clamp(-1.0, 1.0)

                q1_tgt_quantiles, _ = self.critic_target.q1(
                    next_obs[:, t], target_a, h_c1_tgt
                )
                q2_tgt_quantiles, _ = self.critic_target.q2(
                    next_obs[:, t], target_a, h_c2_tgt
                )
                # Scalar-mean comparator for min-Q selection (TD3 spirit)
                q1_mean = q1_tgt_quantiles.mean(dim=-1, keepdim=True)  # (B, 1)
                q2_mean = q2_tgt_quantiles.mean(dim=-1, keepdim=True)
                # Use the QUANTILES of whichever critic has the lower mean —
                # avoids the over-estimation bias the TD3 trick targets, while
                # preserving the distributional information for the loss.
                use_q1 = (q1_mean <= q2_mean).to(q1_tgt_quantiles.dtype)
                chosen_quantiles = (
                    use_q1 * q1_tgt_quantiles + (1.0 - use_q1) * q2_tgt_quantiles
                )  # (B, N)
                # y = r + γ(1-d) chosen_quantiles, broadcasts r/d over N
                y = (
                    rewards[:, t]
                    + self.gamma * (1.0 - dones[:, t]) * chosen_quantiles
                )  # (B, N)

            q1_val, h_c1_critic = self.critic.q1(
                obs[:, t], actions[:, t], h_c1_critic
            )
            q2_val, h_c2_critic = self.critic.q2(
                obs[:, t], actions[:, t], h_c2_critic
            )
            critic_losses.append(
                quantile_huber_loss(q1_val, y) + quantile_huber_loss(q2_val, y)
            )

        critic_loss = torch.stack(critic_losses).mean()
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        loss_info: dict[str, Any] = {"critic_loss": critic_loss.item()}

        # ─── Delayed actor update (mean-Q proxy) ─────────────────────
        if self._update_count % self.policy_delay == 0:
            h_a_actor = h_a
            h_c1_actor = h_c1
            actor_losses: list[torch.Tensor] = []
            for t in range(self.burn_in, self.burn_in + self.seq_len):
                a_pred, h_a_actor = self.actor(obs[:, t], h_a_actor)
                q1_quantiles, h_c1_actor = self.critic.q1(
                    obs[:, t], a_pred, h_c1_actor
                )
                # actor maximises E[Q] = mean of quantiles
                actor_losses.append(-q1_quantiles.mean())
            actor_loss = torch.stack(actor_losses).mean()
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            loss_info["actor_loss"] = actor_loss.item()

            self._soft_update(self.actor, self.actor_target)
            self._soft_update(self.critic, self.critic_target)

        return loss_info

    # ─── Persistence override (adds n_quantiles to hparams) ──────────────

    def save(
        self,
        path: str,
        metadata: dict | None = None,
        save_buffer: bool = False,
    ) -> None:
        """Save with ``algo: "td3_qr_lstm"`` + ``n_quantiles`` in hparams.

        Other fields identical to base ``save``. Loading via
        ``TD3QRLstmAgent.load(path)`` works directly; loading a base-class
        ckpt with this class will fail because critic shape differs (51 vs 1
        output dim) — that's intentional, the class mismatch is loud.
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
                    "n_quantiles": self.n_quantiles,
                },
            },
            path,
        )
        if save_buffer:
            pass
