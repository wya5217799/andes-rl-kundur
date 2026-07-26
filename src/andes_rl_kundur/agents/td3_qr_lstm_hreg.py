"""TD3 + QR distributional critic + LSTM + hidden-norm reg (R183+).

Stacks the two project SOTA-driving ingredients:
- R142/R143 td3_qr_lstm: 51-quantile distributional critic
- R174 td3_lstm_hreg λ_h=0.002: actor hidden-state norm L2 penalty

The actor loss is:

    L_actor = -E[Q(s, a)]  +  λ_h * mean_t ||h_actor(t)||_2^2 / H

where Q is the mean of the 51 quantiles (same as TD3QRLstmAgent.update).

This class subclasses TD3QRLstmAgent (which itself subclasses TD3LSTMAgent),
overriding update() to add the hreg term to the actor loss. All other
training mechanics inherited verbatim.
"""
from __future__ import annotations

from typing import Any

import torch

from andes_rl_kundur.agents.td3_lstm import _detach_h
from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent


class TD3QRLstmHRegAgent(TD3QRLstmAgent):
    """TD3 + QR + LSTM + actor hidden-norm regulariser (stacked R142+R174)."""

    algo_name: str = "td3_qr_lstm_hreg"

    def __init__(self, *args: Any, h_norm_reg_lambda: float = 0.002,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if h_norm_reg_lambda < 0:
            raise ValueError("h_norm_reg_lambda must be non-negative")
        self.h_norm_reg_lambda = float(h_norm_reg_lambda)

    def update(self) -> dict[str, Any] | None:
        # Replicates TD3QRLstmAgent.update() with hreg term added to actor loss.
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

        # ─── Burn-in (no grad) — same as parent ──────────────────────
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
            _, h_a_tgt = self.actor_target(obs[:, self.burn_in], h_a_tgt)

        h_a = _detach_h(h_a)
        h_a_tgt = _detach_h(h_a_tgt)
        h_c1 = _detach_h(h_c1)
        h_c2 = _detach_h(h_c2)
        h_c1_tgt = _detach_h(h_c1_tgt)
        h_c2_tgt = _detach_h(h_c2_tgt)

        # ─── Critic QR-Huber loss — inherit parent's logic directly ─
        # We replicate the parent's critic roll because we need access
        # to h_a inside the actor update; can't simply call super().
        from andes_rl_kundur.agents.networks_critic_variants import (
            quantile_huber_loss,
        )

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
                # Take element-wise min of the two quantile distributions
                q_tgt_quantiles = torch.min(q1_tgt_quantiles, q2_tgt_quantiles)
                y_quantiles = rewards[:, t] + self.gamma * (
                    1.0 - dones[:, t]
                ) * q_tgt_quantiles

            q1_quantiles, h_c1_critic = self.critic.q1(
                obs[:, t], actions[:, t], h_c1_critic
            )
            q2_quantiles, h_c2_critic = self.critic.q2(
                obs[:, t], actions[:, t], h_c2_critic
            )
            l1 = quantile_huber_loss(q1_quantiles, y_quantiles)
            l2 = quantile_huber_loss(q2_quantiles, y_quantiles)
            critic_losses.append(l1 + l2)

        critic_loss = torch.stack(critic_losses).mean()
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        loss_info: dict[str, Any] = {"critic_loss": critic_loss.item()}

        # ─── Actor update — Q-mean from quantiles + hreg term ────────
        if self._update_count % self.policy_delay == 0:
            h_a_actor = h_a
            h_c1_actor = h_c1
            actor_q_losses: list[torch.Tensor] = []
            h_norms_sq: list[torch.Tensor] = []
            for t in range(self.burn_in, self.burn_in + self.seq_len):
                a_pred, h_a_actor = self.actor(obs[:, t], h_a_actor)
                if isinstance(h_a_actor, tuple):
                    h_norms_sq.append((h_a_actor[0] ** 2).sum(dim=-1).mean())
                else:
                    h_norms_sq.append((h_a_actor ** 2).sum(dim=-1).mean())
                q1_quantiles, h_c1_actor = self.critic.q1(
                    obs[:, t], a_pred, h_c1_actor
                )
                actor_q_losses.append(-q1_quantiles.mean())

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
