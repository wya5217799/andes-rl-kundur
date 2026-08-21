"""R428 C1-SAC: exact Yang-2022 TPWRS MADRL-SAC interface (per agent).

The soft-spot program's C1-SAC item (owner-ordered 2026-08-18): reproduce
the SAC interface of Yang et al., TPWRS 2022 (DOI 10.1109/TPWRS.2022.3221439)
EXACTLY, on the matched harness bundle.  Interface facts come from the
repository's authoritative paper-facts document
``docs/paper/kd_4agent_paper_facts.md`` (Eq. 19-23, Algorithm 1, Table I,
sections 12/13 reconciliation notes).

Per agent (network parameters fully independent — distributed, not CTDE):

- actor pi: Gaussian + tanh squash, 4 hidden layers x 128 (paper Sec.IV-A);
- critic Q: SINGLE Q network (paper Alg.1 line 4, singular), 4 x 128;
- value V + soft target V_bar (paper Eq.21 uses V_theta_bar), 4 x 128;
- auto alpha (paper Eq.23), H_bar = -2 (declared), alpha in [0.005, 5.0]
  (declared), all learning rates 3e-4, gamma 0.99, batch 256, per-agent
  replay buffer 10000, soft update tau = 5e-3 (declared from [48]
  Haarnoja 2018), NO gradient clipping (paper silent — exact).

Frozen loss formulas (semantic gate; the R428 plan declares them verbatim):

    critic (Eq.21):  J_Q = 0.5 * MSE( Q(s,a), r + gamma*(1-d)*V_bar(s') )
    actor  (Eq.22):  J_pi = mean( alpha.detach * log pi(a|s) - Q(s,a) )
    alpha  (Eq.23):  J(alpha) = mean( -alpha * log pi - alpha * H_bar ),
                     alpha = exp(log_alpha), H_bar = -2
    value  (declared reconciliation, [48] Haarnoja 2018):
                     J_V = 0.5 * MSE( V(s), [Q(s,a) - log pi(a|s)].detach )
    soft update:     V_bar <- (1-tau)*V_bar + tau*V

Declared reconciliations (paper-internal contradictions, facts doc 12.A /
section 13): the Algorithm-1 line-16 buffer clear contradicts Table I
(buffer 10000, batch 256) — standard replay WITHOUT clearing; one gradient
step per environment step per agent; tau, alpha range, H_bar, and the V
loss are unstated in the paper and taken from [48].

This module is a NEW file: the historical ``sac.py`` / ``sac_base.py`` /
``sac_ctde.py`` (R41-R51 era) stay byte-untouched.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import GaussianActor, QNetwork, build_mlp
from andes_rl_kundur.agents.replay_buffer import ReplayBuffer

YANG_SAC_HIDDEN = (128, 128, 128, 128)  # paper Sec.IV-A: 4 layers x 128
YANG_SAC_LR = 3.0e-4  # paper Table I (actor/critic/alpha identical)
YANG_SAC_GAMMA = 0.99  # paper Table I
YANG_SAC_TAU = 5.0e-3  # declared reconciliation ([48] Haarnoja 2018)
YANG_SAC_BUFFER_SIZE = 10000  # paper Table I
YANG_SAC_BATCH_SIZE = 256  # paper Table I
YANG_SAC_TARGET_ENTROPY = -2.0  # declared: H_bar = -dim(action)
YANG_SAC_ALPHA_MIN = 0.005  # declared bound
YANG_SAC_ALPHA_MAX = 5.0  # declared bound
YANG_SAC_CHECKPOINT_SCHEMA = 1


class YangExactSACAgent:
    """One per-agent exact Yang SAC: own actor/critic/value/alpha/buffer."""

    def __init__(
        self,
        obs_dim: int = 7,
        action_dim: int = 2,
        device: str = "cpu",
    ) -> None:
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.device = torch.device(device)
        self.gamma = float(YANG_SAC_GAMMA)
        self.tau = float(YANG_SAC_TAU)
        self.batch_size = int(YANG_SAC_BATCH_SIZE)
        self.target_entropy = float(YANG_SAC_TARGET_ENTROPY)
        self.actor = GaussianActor(
            self.obs_dim, self.action_dim, list(YANG_SAC_HIDDEN)
        ).to(self.device)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=YANG_SAC_LR)
        self.critic = QNetwork(
            self.obs_dim, self.action_dim, list(YANG_SAC_HIDDEN)
        ).to(self.device)
        self.critic_optimizer = optim.Adam(
            self.critic.parameters(), lr=YANG_SAC_LR
        )
        self.value = build_mlp(
            self.obs_dim, list(YANG_SAC_HIDDEN), 1
        ).to(self.device)
        self.value_target = copy.deepcopy(self.value).to(self.device)
        for parameters in self.value_target.parameters():
            parameters.requires_grad = False
        self.value_optimizer = optim.Adam(self.value.parameters(), lr=YANG_SAC_LR)
        self.log_alpha = torch.zeros(1, requires_grad=True, device=self.device)
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=YANG_SAC_LR)
        self._log_alpha_min = float(np.log(YANG_SAC_ALPHA_MIN))
        self._log_alpha_max = float(np.log(YANG_SAC_ALPHA_MAX))
        self.buffer = ReplayBuffer(
            self.obs_dim, self.action_dim, capacity=YANG_SAC_BUFFER_SIZE
        )
        self._update_count = 0

    @property
    def alpha(self) -> float:
        return float(self.log_alpha.detach().exp().cpu())

    def select_action(
        self, obs: np.ndarray, deterministic: bool = False
    ) -> np.ndarray:
        """Return one action from the policy (sample, or tanh(mean) at eval)."""
        row = torch.FloatTensor(np.asarray(obs, dtype=np.float32)).unsqueeze(0)
        row = row.to(self.device)
        with torch.no_grad():
            if deterministic:
                action = self.actor.deterministic(row)
            else:
                action, _log_prob = self.actor.sample(row)
        return action.cpu().numpy().flatten().astype(np.float32)

    def store_transition(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.add(
            np.asarray(obs, dtype=np.float32),
            np.asarray(action, dtype=np.float32),
            float(reward),
            np.asarray(next_obs, dtype=np.float32),
            bool(done),
        )

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        obs = batch["obs"]
        actions = batch["actions"]
        rewards = batch["rewards"]
        next_obs = batch["next_obs"]
        dones = batch["dones"]

        # Critic (Eq.21): single Q against the V_bar target.
        with torch.no_grad():
            v_next = self.value_target(next_obs)
            y = rewards + self.gamma * (1.0 - dones) * v_next
        q = self.critic(obs, actions)
        critic_loss = 0.5 * F.mse_loss(q, y)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # Actor (Eq.22): alpha.detach * log pi - Q.
        new_actions, log_prob = self.actor.sample(obs)
        q_new = self.critic(obs, new_actions)
        actor_loss = (self.log_alpha.detach().exp() * log_prob - q_new).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        # Alpha (Eq.23): -alpha * log pi - alpha * H_bar.
        alpha_loss = -(
            self.log_alpha * (log_prob.detach() + self.target_entropy)
        ).mean()
        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        self.alpha_optimizer.step()
        with torch.no_grad():
            self.log_alpha.data.clamp_(
                self._log_alpha_min, self._log_alpha_max
            )

        # Value (declared reconciliation, [48]): V(s) vs [Q - log pi].
        with torch.no_grad():
            v_target_value = q_new.detach() - log_prob.detach()
        v = self.value(obs)
        value_loss = 0.5 * F.mse_loss(v, v_target_value)
        self.value_optimizer.zero_grad()
        value_loss.backward()
        self.value_optimizer.step()

        # Soft target update: V_bar <- (1-tau) V_bar + tau V.
        for target_param, param in zip(
            self.value_target.parameters(), self.value.parameters()
        ):
            target_param.data.mul_(1.0 - self.tau)
            target_param.data.add_(self.tau * param.data)

        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss": float(actor_loss.detach().cpu()),
            "alpha_loss": float(alpha_loss.detach().cpu()),
            "value_loss": float(value_loss.detach().cpu()),
            "alpha": self.alpha,
            "mean_log_prob": float(log_prob.detach().mean().cpu()),
        }

    def save(self, path: str | Path) -> None:
        torch.save(
            {
                "schema_version": YANG_SAC_CHECKPOINT_SCHEMA,
                "obs_dim": self.obs_dim,
                "action_dim": self.action_dim,
                "actor": self.actor.state_dict(),
                "critic": self.critic.state_dict(),
                "value": self.value.state_dict(),
                "value_target": self.value_target.state_dict(),
                "log_alpha": self.log_alpha.detach().cpu(),
                "update_count": self._update_count,
            },
            str(path),
        )

    def load(self, path: str | Path) -> None:
        payload = torch.load(str(path), map_location=self.device)
        if (
            payload.get("schema_version") != YANG_SAC_CHECKPOINT_SCHEMA
            or payload.get("obs_dim") != self.obs_dim
            or payload.get("action_dim") != self.action_dim
        ):
            raise ValueError("incompatible yang-exact-sac checkpoint payload")
        self.actor.load_state_dict(payload["actor"])
        self.critic.load_state_dict(payload["critic"])
        self.value.load_state_dict(payload["value"])
        self.value_target.load_state_dict(payload["value_target"])
        self.log_alpha.data = payload["log_alpha"].to(self.device)
        self._update_count = int(payload.get("update_count", 0))
