"""TD3 + LSTMCell + hidden-state-norm regularisation (R100/R93+).

Subclass of TD3LSTMAgent that adds an L2 penalty on the actor LSTM's
hidden state during the actor-update roll. Motivated by R93-W0b
(CLM-0181: LSTM h drifts to ||h||≈5 in 50 steps regardless of obs)
and R93-W2 (CLM-0182: cell-input gate spectral radius 1.54 > 1.0).

The added loss term per actor update is:

    L_hreg = h_norm_reg_lambda * mean_t( ||h_a_actor(t)||_2² )

where the mean is over the actor-update rollout window (seq_len
steps post burn-in). Larger lambda forces the actor LSTM to keep
its hidden norm bounded, breaking the bang-bang attractor.

The class shares all training mechanics with TD3LSTMAgent except
for the actor-loss term and the loss bookkeeping. Replay buffer,
critic update, target soft-update, burn-in, and lr warmup are
unchanged.
"""
from __future__ import annotations

from typing import Any

import torch

from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent, _detach_h


class TD3LSTMHRegAgent(TD3LSTMAgent):
    """TD3 + LSTMCell + actor hidden-norm regulariser."""

    algo_name: str = "td3_lstm_hreg"

    def __init__(self, *args: Any, h_norm_reg_lambda: float = 0.01, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if h_norm_reg_lambda < 0:
            raise ValueError("h_norm_reg_lambda must be non-negative")
        self.h_norm_reg_lambda = float(h_norm_reg_lambda)

    def update(self) -> dict[str, Any] | None:
        # Identical to TD3LSTMAgent.update() up to the actor-loss roll.
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
                _, h_c1_tgt = self.critic_target.q1(obs[:, t], actions[:, t], h_c1_tgt)
                _, h_c2_tgt = self.critic_target.q2(obs[:, t], actions[:, t], h_c2_tgt)

        h_a = _detach_h(h_a)
        h_a_tgt = _detach_h(h_a_tgt)
        h_c1 = _detach_h(h_c1)
        h_c2 = _detach_h(h_c2)
        h_c1_tgt = _detach_h(h_c1_tgt)
        h_c2_tgt = _detach_h(h_c2_tgt)

        # ─── Critic loss roll (unchanged) ─────────────────────────
        h_c1_critic = h_c1
        h_c2_critic = h_c2
        critic_losses: list[torch.Tensor] = []
        from torch.nn import functional as F   # noqa: N813
        for t in range(self.burn_in, self.burn_in + self.seq_len):
            with torch.no_grad():
                target_a_raw, h_a_tgt = self.actor_target(next_obs[:, t], h_a_tgt)
                noise = (
                    torch.randn_like(target_a_raw) * self.policy_noise
                ).clamp(-self.noise_clip, self.noise_clip)
                target_a = (target_a_raw + noise).clamp(-1.0, 1.0)
                q1_tgt_val, h_c1_tgt = self.critic_target.q1(
                    next_obs[:, t], target_a, h_c1_tgt
                )
                q2_tgt_val, h_c2_tgt = self.critic_target.q2(
                    next_obs[:, t], target_a, h_c2_tgt
                )
                q_tgt = torch.min(q1_tgt_val, q2_tgt_val)
                y = rewards[:, t] + self.gamma * (1.0 - dones[:, t]) * q_tgt

            q1_val, h_c1_critic = self.critic.q1(
                obs[:, t], actions[:, t], h_c1_critic
            )
            q2_val, h_c2_critic = self.critic.q2(
                obs[:, t], actions[:, t], h_c2_critic
            )
            critic_losses.append(F.mse_loss(q1_val, y) + F.mse_loss(q2_val, y))

        critic_loss = torch.stack(critic_losses).mean()
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        loss_info: dict[str, Any] = {"critic_loss": critic_loss.item()}

        # ─── Actor loss roll WITH hidden-norm regulariser ─────────
        if self._update_count % self.policy_delay == 0:
            h_a_actor = h_a
            h_c1_actor = h_c1
            actor_q_losses: list[torch.Tensor] = []
            h_norms_sq: list[torch.Tensor] = []
            for t in range(self.burn_in, self.burn_in + self.seq_len):
                a_pred, h_a_actor = self.actor(obs[:, t], h_a_actor)
                # h_a_actor is (h_tensor, c_tensor) for nn.LSTMCell-based RecurrentActor.
                # Penalise hidden state h (not cell state c).
                if isinstance(h_a_actor, tuple):
                    h_norms_sq.append((h_a_actor[0] ** 2).sum(dim=-1).mean())
                else:
                    h_norms_sq.append((h_a_actor ** 2).sum(dim=-1).mean())
                q1_val, h_c1_actor = self.critic.q1(
                    obs[:, t], a_pred, h_c1_actor
                )
                actor_q_losses.append(-q1_val.mean())

            actor_q_loss = torch.stack(actor_q_losses).mean()
            h_reg_loss = torch.stack(h_norms_sq).mean()
            actor_loss = actor_q_loss + self.h_norm_reg_lambda * h_reg_loss

            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            loss_info["actor_loss"] = actor_loss.item()
            loss_info["actor_q_loss"] = actor_q_loss.item()
            loss_info["h_reg_loss"] = h_reg_loss.item()
            loss_info["h_norm_mean"] = float(h_reg_loss.detach().sqrt().item())

            self._soft_update(self.actor, self.actor_target)
            self._soft_update(self.critic, self.critic_target)

        return loss_info
