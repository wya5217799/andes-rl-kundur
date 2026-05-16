"""TD3 with LSTM recurrent actor and critic (R56 — structural pivot).

Background
----------
R49–R55 closed the cheap+medium-cost lever space against the
0.334/0.365/0.351 production triangle. Six independent attacks
(obs aug, anti-smoothness W=1, SAC, time-in-obs, warmstart-shared,
anti-smoothness W=10) all failed with the same eval-time pathology:
the per-agent deterministic action collapses to a near-constant
setpoint. The R55 verdict's mechanism analysis: the only escapes from
the noise-hijack reward channel are (1) deterministic-output reward,
(2) sparse end-of-episode reward, or (3) a recurrent policy class.

This module implements escape (3): ``π(obs_t, h_t)`` is structurally
time-varying via the LSTMCell hidden state, even when ``obs_t`` is
constant. The critic is also recurrent (R2D2 convention) — twin Q
networks with independent hidden states.

Algorithm (per-update)
----------------------
1. Sample a batch of ``B`` sequences of length ``T = burn_in + seq_len``
   from a :class:`SequenceReplayBuffer`.
2. Burn-in: roll all 6 LSTM modules (actor, target_actor, q1, q2,
   target_q1, target_q2) for ``burn_in`` steps under ``no_grad`` to
   produce warmed hidden states; detach the outputs.
3. Critic loss: roll for ``seq_len`` steps, computing the TD3 target
   ``y = r + γ(1-d) min(Q1_tgt, Q2_tgt)`` using a noise-clipped target
   action. Backprop to both critic networks.
4. (Every ``policy_delay`` updates) Actor loss: re-roll critic Q1 using
   the actor's CURRENT output instead of the logged action; backprop
   the ``-Q1(s, π(s,h))`` deterministic-policy-gradient signal.
5. Polyak update of both target networks.

Interface
---------
* :meth:`select_action(obs, deterministic)` is stateful — uses an
  internal rollout hidden state that the caller advances by calling
  it once per env step. Reset via :meth:`begin_episode`.
* :meth:`select_action_recurrent(obs, h, deterministic)` is stateless
  — for eval scripts that want to manage their own hidden state.
* :meth:`store_transition(obs, action, reward, next_obs, done)`
  accumulates the in-progress episode and flushes to the replay
  buffer when ``done`` is true.
"""
from __future__ import annotations

import copy
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import (
    HiddenState,
    RecurrentActor,
    RecurrentDoubleQCritic,
)
from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer


def _detach_h(h: HiddenState) -> HiddenState:
    return (h[0].detach(), h[1].detach())


class TD3LSTMAgent:
    """TD3 with recurrent LSTMCell actor and twin critic.

    Satisfies the :class:`BaseAgent` Protocol structurally
    (``select_action`` / ``store_transition`` / ``update`` /
    ``save`` / ``load``), so the training loop can swap it in via
    ``--algo td3_lstm`` without further branching beyond episode
    bookkeeping for the recurrent rollout.
    """

    algo_name: str = "td3_lstm"
    is_recurrent: bool = True

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes,
        lr: float = 1e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 200,
        batch_size: int = 32,
        device: str = "cpu",
        policy_noise: float = 0.2,
        noise_clip: float = 0.5,
        explore_noise: float = 0.1,
        policy_delay: int = 2,
        seq_len: int = 25,
        burn_in: int = 5,
        max_grad_norm: float = 10.0,
    ) -> None:
        # ``hidden_sizes`` is accepted as a list for API symmetry with
        # the MLP agents; only the first element is used (LSTMCell is a
        # single-layer cell).
        if hasattr(hidden_sizes, "__len__") and len(hidden_sizes) > 0:
            hidden = int(hidden_sizes[0])
        else:
            hidden = int(hidden_sizes)

        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden = hidden
        self.batch_size = batch_size
        self.device = device

        self.gamma = gamma
        self.tau = tau
        self.policy_noise = policy_noise
        self.noise_clip = noise_clip
        self.explore_noise = explore_noise
        self.policy_delay = policy_delay
        self.seq_len = seq_len
        self.burn_in = burn_in
        self.max_grad_norm = max_grad_norm

        # Actor + target actor
        self.actor = RecurrentActor(obs_dim, action_dim, hidden=hidden).to(device)
        self.actor_target = copy.deepcopy(self.actor).to(device)
        for p in self.actor_target.parameters():
            p.requires_grad = False
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

        # Twin critics + target
        self.critic = RecurrentDoubleQCritic(obs_dim, action_dim, hidden=hidden).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

        # Sequence replay buffer (per-episode storage)
        self.buffer = SequenceReplayBuffer(
            obs_dim=obs_dim,
            action_dim=action_dim,
            seq_len=seq_len,
            burn_in=burn_in,
            capacity_episodes=buffer_size,
        )

        # Stateful rollout bookkeeping
        self._h_rollout: HiddenState | None = None
        self._current_episode: list = []
        self._update_count = 0

    # ─── Stateful rollout interface ─────────────────────────────────

    def begin_episode(self) -> None:
        """Reset the per-rollout hidden state and the in-progress
        episode transition buffer. Call once per training/eval episode
        BEFORE the first ``select_action`` of that episode."""
        self._h_rollout = None
        self._current_episode = []

    def select_action(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        """Stateful: advances internal hidden state by one step.

        Mirrors :class:`TD3Agent.select_action` so the training loop
        treats both agents the same. Exploration noise (when
        ``deterministic=False``) is added externally — does NOT enter
        the LSTM hidden state.
        """
        if self._h_rollout is None:
            self._h_rollout = self.actor.init_hidden(1, self.device)
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
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
        """Stateless variant: caller manages hidden state.

        Used by eval scripts that need to reset ``h`` at scenario
        boundaries (see :mod:`andes_rl_kundur.evaluation.paper_path`).
        """
        if h is None:
            h = self.actor.init_hidden(1, self.device)
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
        with torch.no_grad():
            action, h_new = self.actor(obs_t, h)
        action_np = action.cpu().numpy().flatten()
        if not deterministic:
            noise = np.random.normal(0.0, self.explore_noise, size=action_np.shape)
            action_np = np.clip(action_np + noise, -1.0, 1.0)
        return action_np.astype(np.float32), h_new

    def store_transition(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        """Append to the in-progress episode. On ``done=True``, flush
        the episode into the replay buffer."""
        self._current_episode.append(
            (obs, action, float(reward), next_obs, bool(done))
        )
        if done:
            self.buffer.add_episode(self._current_episode)
            self._current_episode = []

    def flush_episode(self) -> None:
        """Force-flush the in-progress episode (e.g., on training
        interrupt where ``done`` was never observed)."""
        if self._current_episode:
            self.buffer.add_episode(self._current_episode)
            self._current_episode = []

    # ─── Gradient update ────────────────────────────────────────────

    def update(self) -> dict[str, Any] | None:
        batch = self.buffer.sample(self.batch_size, self.device)
        if batch is None:
            return None

        self._update_count += 1

        obs = batch["obs"]            # (B, T, obs_dim)
        actions = batch["actions"]    # (B, T, action_dim)
        rewards = batch["rewards"]    # (B, T, 1)
        next_obs = batch["next_obs"]  # (B, T, obs_dim)
        dones = batch["dones"]        # (B, T, 1)
        B = obs.shape[0]

        # ─── Burn-in (no grad) — warm all 6 LSTM hidden states ────
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

        # ─── Critic loss roll ─────────────────────────────────────
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

        # ─── Delayed actor update ─────────────────────────────────
        if self._update_count % self.policy_delay == 0:
            # Fresh roll using the same burn-in hidden states. The
            # critic params are NOT in the actor optimizer; their
            # gradients are computed but discarded.
            h_a_actor = h_a
            h_c1_actor = h_c1
            actor_losses: list[torch.Tensor] = []
            for t in range(self.burn_in, self.burn_in + self.seq_len):
                a_pred, h_a_actor = self.actor(obs[:, t], h_a_actor)
                q1_val, h_c1_actor = self.critic.q1(
                    obs[:, t], a_pred, h_c1_actor
                )
                actor_losses.append(-q1_val.mean())
            actor_loss = torch.stack(actor_losses).mean()
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            loss_info["actor_loss"] = actor_loss.item()

            self._soft_update(self.actor, self.actor_target)
            self._soft_update(self.critic, self.critic_target)

        return loss_info

    def _soft_update(self, src: torch.nn.Module, tgt: torch.nn.Module) -> None:
        for p, p_tgt in zip(src.parameters(), tgt.parameters()):
            p_tgt.data.mul_(1.0 - self.tau).add_(self.tau * p.data)

    # ─── Persistence ────────────────────────────────────────────────

    def save(
        self,
        path: str,
        metadata: dict | None = None,
        save_buffer: bool = False,
    ) -> None:
        torch.save(
            {
                "actor": self.actor.state_dict(),
                "actor_target": self.actor_target.state_dict(),
                "critic": self.critic.state_dict(),
                "critic_target": self.critic_target.state_dict(),
                "actor_opt": self.actor_optimizer.state_dict(),
                "critic_opt": self.critic_optimizer.state_dict(),
                "metadata": metadata or {},
                "algo": "td3_lstm",
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
            # Sequence buffer save deferred — not needed for the R56 sweep
            # (no resume-from-buffer workflow). Add when first required.
            pass

    def load(self, path: str) -> dict:
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.actor.load_state_dict(ckpt["actor"])
        if "actor_target" in ckpt:
            self.actor_target.load_state_dict(ckpt["actor_target"])
        if "critic" in ckpt:
            self.critic.load_state_dict(ckpt["critic"])
            self.critic_target.load_state_dict(ckpt["critic_target"])
            self.critic_optimizer.load_state_dict(ckpt["critic_opt"])
        self.actor_optimizer.load_state_dict(ckpt["actor_opt"])
        return ckpt.get("metadata", {})
