"""TD3+LSTM with WarmH0 actor + QR distributional critic (NO AFE).

After R142 confirmed QR alone matches baseline and R124/R140 confirmed AFE
is structurally broken (CLM-0275), this variant combines:
  - WarmH0 actor (R104 / CLM-0188 universal feasibility, R96 implementation)
  - QR distributional critic (R98 / CLM-0189, validated empirically by R142)
  - **NO AFE input** (CLM-0190 falsified; AFE has zero-action sweet spot
    pathology that drags down even working QR critic)

Hypothesis: warm-h_0 actor + QR critic might exceed R72_w4 baseline 0.391
by combining orthogonal interventions (actor-side warm-up + critic-side
distributional). This is the most paper-promising plateau-breaker candidate
post-CLM-0275 falsification of AFE.

train.py launch:
    LR=1e-4 python scripts/train.py --algo td3_warmh0_qr_lstm \\
        --qr-n-quantiles 51 --episodes 75 --seed 54 \\
        --hidden-size 64 --tau 0.001 --normalize-actions \\
        --lstm-lr-warmup-eps 5 --save-dir results/r150_warmh0_qr_s54 \\
        --final-eval
"""
from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks import HiddenState
from andes_rl_kundur.agents.networks_critic_variants import (
    N_QUANTILES_DEFAULT,
    quantile_huber_loss,
)
from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor
from andes_rl_kundur.agents.td3_lstm import _detach_h
from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent


class TD3LSTMWarmH0QRAgent(TD3QRLstmAgent):
    """WarmH0 actor + QR distributional critic. Inherits QR critic +
    quantile-Huber loss + distributional update from TD3QRLstmAgent;
    only swaps actor to WarmH0 + threads obs_for_warm through init.
    """

    algo_name: str = "td3_warmh0_qr_lstm"
    is_recurrent: bool = True

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: int | Sequence[int],
        n_quantiles: int = N_QUANTILES_DEFAULT,
        **kwargs: Any,
    ) -> None:
        # Build QR plumbing via parent.
        super().__init__(
            obs_dim=obs_dim,
            action_dim=action_dim,
            hidden_sizes=hidden_sizes,
            n_quantiles=n_quantiles,
            **kwargs,
        )

        # Replace actor with WarmH0 variant; critic stays RecurrentQRDoubleQCritic
        # (scalar [obs, a] input, 51 quantile output) — no AFE.
        lr = self._target_lr
        hidden = self.hidden
        self.actor = WarmH0RecurrentActor(obs_dim, action_dim, hidden=hidden).to(self.device)
        self.actor_target = copy.deepcopy(self.actor).to(self.device)
        for p in self.actor_target.parameters():
            p.requires_grad = False
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

    # ─── Stateful rollout with warm h_0 ──────────────────────────────────

    def select_action(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
        if self._h_rollout is None:
            self._h_rollout = self.actor.init_hidden(
                1, self.device, obs_for_warm=obs_t
            )
        with torch.no_grad():
            action, h_new = self.actor(obs_t, self._h_rollout)
        self._h_rollout = h_new
        action_np = action.cpu().numpy().flatten()
        if not deterministic:
            noise = np.random.normal(0.0, self.explore_noise, size=action_np.shape)
            action_np = np.clip(action_np + noise, -1.0, 1.0)
        return action_np.astype(np.float32)

    def select_action_recurrent(
        self,
        obs: np.ndarray,
        h: HiddenState | None,
        deterministic: bool = True,
    ) -> tuple[np.ndarray, HiddenState]:
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
        if h is None:
            h = self.actor.init_hidden(1, self.device, obs_for_warm=obs_t)
        with torch.no_grad():
            action, h_new = self.actor(obs_t, h)
        action_np = action.cpu().numpy().flatten()
        if not deterministic:
            noise = np.random.normal(0.0, self.explore_noise, size=action_np.shape)
            action_np = np.clip(action_np + noise, -1.0, 1.0)
        return action_np.astype(np.float32), h_new

    # ─── Update with warm-h_0 actor + quantile-Huber critic ────────────

    def update(self) -> dict[str, Any] | None:
        """Override TD3QRLstmAgent.update to thread obs_for_warm into actor
        init_hidden. Critic part (quantile-Huber loss) preserved as-is.
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

        # Warm h_0 from first-step obs (vs zeros in base)
        obs_first = obs[:, 0]
        next_obs_first = next_obs[:, 0]

        with torch.no_grad():
            h_a = self.actor.init_hidden(B, self.device, obs_for_warm=obs_first)
            h_a_tgt = self.actor_target.init_hidden(
                B, self.device, obs_for_warm=next_obs_first,
            )
            # Critic still zero-init (matches td3_lstm_warmh0 convention)
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

        h_a = _detach_h(h_a)
        h_a_tgt = _detach_h(h_a_tgt)
        h_c1 = _detach_h(h_c1)
        h_c2 = _detach_h(h_c2)
        h_c1_tgt = _detach_h(h_c1_tgt)
        h_c2_tgt = _detach_h(h_c2_tgt)

        # Quantile-Huber critic loss (canonical sum-over-pred per Dabney 2018)
        h_c1_critic = h_c1
        h_c2_critic = h_c2
        critic_losses: list[torch.Tensor] = []
        for t in range(self.burn_in, self.burn_in + self.seq_len):
            with torch.no_grad():
                target_a_raw, h_a_tgt = self.actor_target(next_obs[:, t], h_a_tgt)
                noise = (
                    torch.randn_like(target_a_raw) * self.policy_noise
                ).clamp(-self.noise_clip, self.noise_clip)
                target_a = (target_a_raw + noise).clamp(-1.0, 1.0)

                q1_tgt_q, h_c1_tgt = self.critic_target.q1(
                    next_obs[:, t], target_a, h_c1_tgt,
                )
                q2_tgt_q, h_c2_tgt = self.critic_target.q2(
                    next_obs[:, t], target_a, h_c2_tgt,
                )
                q1_mean = q1_tgt_q.mean(dim=-1, keepdim=True)
                q2_mean = q2_tgt_q.mean(dim=-1, keepdim=True)
                use_q1 = (q1_mean <= q2_mean).to(q1_tgt_q.dtype)
                chosen_q = use_q1 * q1_tgt_q + (1.0 - use_q1) * q2_tgt_q
                y = rewards[:, t] + self.gamma * (1.0 - dones[:, t]) * chosen_q

            q1_val, h_c1_critic = self.critic.q1(
                obs[:, t], actions[:, t], h_c1_critic,
            )
            q2_val, h_c2_critic = self.critic.q2(
                obs[:, t], actions[:, t], h_c2_critic,
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

        if self._update_count % self.policy_delay == 0:
            h_a_actor = h_a
            h_c1_actor = h_c1
            actor_losses: list[torch.Tensor] = []
            for t in range(self.burn_in, self.burn_in + self.seq_len):
                a_pred, h_a_actor = self.actor(obs[:, t], h_a_actor)
                q1_q, h_c1_actor = self.critic.q1(obs[:, t], a_pred, h_c1_actor)
                actor_losses.append(-q1_q.mean())
            actor_loss = torch.stack(actor_losses).mean()
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            loss_info["actor_loss"] = actor_loss.item()

            self._soft_update(self.actor, self.actor_target)
            self._soft_update(self.critic, self.critic_target)

        return loss_info
