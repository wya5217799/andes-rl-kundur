"""
CTDE (Centralized Training, Decentralized Execution) SAC.

Architecture
------------
* N decentralized actors — each agent observes only its own obs (obs_dim).
* 1 shared centralized DoubleQCritic — input = concat(all obs, all actions)
  = obs_dim * N + action_dim * N.  Output = scalar Q.
* 1 per-agent alpha (entropy coeff) — tuned against individual log_prob.

Training update (CTDECoordinator.update)
-----------------------------------------
1. Sample the same batch index set across all agents' replay buffers.
2. Concat all obs/actions  →  centralized critic input.
3. Compute centralized Bellman target using centralized critic_target.
4. Update shared critic with combined critic_loss.
5. For each agent i: update actor_i with shared critic evaluated at
   (concat all obs, concat all actors' sampled actions — agents j≠i use
    no-grad samples from their current actors).
6. Update per-agent alpha.
7. Soft-update shared critic_target.

Execution (decentralized)
--------------------------
Each SACAgentCTDE.select_action(obs_i) uses only obs_i → unchanged from SACAgent.

Compatibility
-------------
* save/load per agent: saves actor + log_alpha + optimizers (critic NOT saved per agent).
* CTDECoordinator.save_critic / load_critic: saves shared critic separately.
* Existing SACAgent code is completely unmodified.
"""

from __future__ import annotations

import copy
import math
import os
from typing import List, Optional, Dict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import GaussianActor, DoubleQCritic
from andes_rl_kundur.agents.replay_buffer import ReplayBuffer


class SACAgentCTDE:
    """Decentralized actor with per-agent alpha; critic is shared via CTDECoordinator."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes,
        lr: float = 3e-4,
        buffer_size: int = 10000,
        batch_size: int = 256,
        device: str = 'cpu',
        alpha_min: float = 0.005,
        alpha_max: float = 5.0,
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.batch_size = batch_size
        self.device = device

        # Decentralized actor only — no per-agent critic
        self.actor = GaussianActor(obs_dim, action_dim, hidden_sizes).to(device)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

        # Per-agent entropy coeff
        self.target_entropy = -float(action_dim)
        self.log_alpha = torch.zeros(1, requires_grad=True, device=device)
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=lr)
        self._log_alpha_min = math.log(alpha_min)
        self._log_alpha_max = math.log(alpha_max)

        # Individual replay buffer (same interface as SACAgent)
        self.buffer = ReplayBuffer(obs_dim, action_dim, capacity=buffer_size)

        self.max_grad_norm = 1.0

    @property
    def alpha(self):
        return self.log_alpha.exp()

    def select_action(self, obs, deterministic: bool = False):
        """Decentralized execution: uses only own obs."""
        obs_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        with torch.no_grad():
            if deterministic:
                action = self.actor.deterministic(obs_t)
            else:
                action, _ = self.actor.sample(obs_t)
        return action.cpu().numpy().flatten()

    def store_transition(self, obs, action, reward, next_obs, done):
        self.buffer.add(obs, action, reward, next_obs, done)

    def save(self, path, metadata: Optional[Dict] = None, save_buffer: bool = False):
        """Save actor + alpha (critic is saved separately by CTDECoordinator)."""
        torch.save({
            'actor': self.actor.state_dict(),
            'log_alpha': self.log_alpha.data,
            'actor_opt': self.actor_optimizer.state_dict(),
            'alpha_opt': self.alpha_optimizer.state_dict(),
            'metadata': metadata or {},
            'ctde': True,
        }, path)
        if save_buffer:
            buf_path = str(path).replace('.pt', '_buffer.npz')
            self.buffer.save(buf_path)

    def load(self, path) -> Dict:
        """Load actor + alpha. Returns metadata dict."""
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.actor.load_state_dict(ckpt['actor'])
        self.log_alpha.data = ckpt['log_alpha']
        self.actor_optimizer.load_state_dict(ckpt['actor_opt'])
        self.alpha_optimizer.load_state_dict(ckpt['alpha_opt'])
        buf_path = str(path).replace('.pt', '_buffer.npz')
        if os.path.exists(buf_path):
            self.buffer.load(buf_path)
        return ckpt.get('metadata', {})

    def load_actor_only(self, path) -> Dict:
        """Load actor weights from a standard SACAgent checkpoint (for warmstart)."""
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.actor.load_state_dict(ckpt['actor'])
        # try actor optimizer if compatible
        try:
            self.actor_optimizer.load_state_dict(ckpt['actor_opt'])
        except Exception:
            pass
        # load alpha if present
        if 'log_alpha' in ckpt:
            self.log_alpha.data = ckpt['log_alpha']
        buf_path = str(path).replace('.pt', '_buffer.npz')
        if os.path.exists(buf_path):
            self.buffer.load(buf_path)
        return ckpt.get('metadata', {})


class CTDECoordinator:
    """
    Holds the shared centralized critic and coordinates joint updates.

    Parameters
    ----------
    n_agents : int
    obs_dim : int  — per-agent obs dimension
    action_dim : int  — per-agent action dimension
    hidden_sizes : list[int]
    lr : float
    gamma : float
    tau : float  — soft-update coefficient
    batch_size : int
    device : str
    """

    def __init__(
        self,
        n_agents: int,
        obs_dim: int,
        action_dim: int,
        hidden_sizes,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        batch_size: int = 256,
        device: str = 'cpu',
    ):
        self.n_agents = n_agents
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.device = device

        central_obs_dim = obs_dim * n_agents
        central_act_dim = action_dim * n_agents

        self.critic = DoubleQCritic(central_obs_dim, central_act_dim, hidden_sizes).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)
        for p in self.critic_target.parameters():
            p.requires_grad = False

        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        self.max_grad_norm = 1.0

    def _can_update(self, agents: List[SACAgentCTDE]) -> bool:
        """All agents must have enough data."""
        return all(len(a.buffer) >= self.batch_size for a in agents)

    def update(self, agents: List[SACAgentCTDE]) -> Optional[Dict]:
        """
        One joint CTDE update step.

        Returns dict with losses, or None if buffers not ready.
        """
        if not self._can_update(agents):
            return None

        n = self.n_agents
        bs = self.batch_size

        # ── Sample same indices across agents ──
        # Use the minimum buffer size to ensure valid indices for all agents
        min_size = min(len(a.buffer) for a in agents)
        idx = np.random.randint(0, min_size, size=bs)

        def _gather(buf: ReplayBuffer, key: str):
            arr = getattr(buf, key)[:buf.size]
            return torch.FloatTensor(arr[idx]).to(self.device)

        # Gather per-agent data at shared indices
        obs_list = [_gather(a.buffer, 'obs') for a in agents]        # [N, B, obs_dim]
        act_list = [_gather(a.buffer, 'actions') for a in agents]    # [N, B, act_dim]
        next_obs_list = [_gather(a.buffer, 'next_obs') for a in agents]

        # rewards and dones: use agent 0's values as environment-wide signal
        # (per-agent rewards summed for centralized value estimate)
        rewards_list = [_gather(a.buffer, 'rewards') for a in agents]
        dones_list   = [_gather(a.buffer, 'dones') for a in agents]

        # Cooperative MARL contract: team value = sum of individual rewards.
        # This is valid here because all agents share the same global frequency
        # objective. If per-agent rewards become heterogeneous (e.g. local-only
        # shaping), this sum must be revisited — the centralized Q would no
        # longer represent the team's joint return correctly.
        #
        # NOTE: _gather returns [B, 1] tensors (ReplayBuffer stores rewards/dones
        # as 2D (capacity, 1) arrays for sac.py Bellman compatibility). No
        # .unsqueeze(1) needed — the trailing dim is already present.
        rewards = torch.stack(rewards_list, dim=0).sum(dim=0)  # [B, 1]
        dones   = dones_list[0]                                  # [B, 1]

        # Centralized obs/actions tensors
        obs_cat      = torch.cat(obs_list, dim=-1)       # [B, obs_dim*N]
        act_cat      = torch.cat(act_list, dim=-1)       # [B, act_dim*N]
        next_obs_cat = torch.cat(next_obs_list, dim=-1)  # [B, obs_dim*N]

        # ═══ Centralized Critic update ═══
        with torch.no_grad():
            # Next actions from each agent's actor
            next_act_list = []
            next_logp_sum = torch.zeros(bs, 1, device=self.device)
            for i, agent in enumerate(agents):
                na, nlp = agent.actor.sample(next_obs_list[i])
                next_act_list.append(na)
                next_logp_sum = next_logp_sum + nlp

            next_act_cat = torch.cat(next_act_list, dim=-1)
            q1_t, q2_t = self.critic_target(next_obs_cat, next_act_cat)
            q_target = torch.min(q1_t, q2_t)

            # Use mean alpha across agents for entropy correction
            mean_alpha = sum(a.alpha for a in agents) / n
            y = rewards + self.gamma * (1 - dones) * (q_target - mean_alpha * next_logp_sum)

        q1, q2 = self.critic(obs_cat, act_cat)
        critic_loss = F.mse_loss(q1, y) + F.mse_loss(q2, y)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        # ═══ Per-agent Actor + Alpha updates ═══
        actor_losses = []
        alpha_losses = []

        for i, agent in enumerate(agents):
            # Sample new action for agent i from its actor
            new_act_i, log_prob_i = agent.actor.sample(obs_list[i])

            # Build full action tensor: agents j≠i use no-grad samples
            new_act_all = []
            for j, agent_j in enumerate(agents):
                if j == i:
                    new_act_all.append(new_act_i)
                else:
                    with torch.no_grad():
                        na_j, _ = agent_j.actor.sample(obs_list[j])
                    new_act_all.append(na_j)
            new_act_cat = torch.cat(new_act_all, dim=-1)

            q1_new, q2_new = self.critic(obs_cat, new_act_cat)
            q_new = torch.min(q1_new, q2_new)
            actor_loss_i = (agent.alpha.detach() * log_prob_i - q_new).mean()

            agent.actor_optimizer.zero_grad()
            actor_loss_i.backward()
            nn.utils.clip_grad_norm_(agent.actor.parameters(), agent.max_grad_norm)
            agent.actor_optimizer.step()
            actor_losses.append(actor_loss_i.item())

            # Alpha update for agent i
            alpha_loss_i = -(agent.log_alpha * (log_prob_i.detach() + agent.target_entropy)).mean()
            agent.alpha_optimizer.zero_grad()
            alpha_loss_i.backward()
            nn.utils.clip_grad_norm_([agent.log_alpha], agent.max_grad_norm)
            agent.alpha_optimizer.step()
            with torch.no_grad():
                agent.log_alpha.data.clamp_(agent._log_alpha_min, agent._log_alpha_max)
            alpha_losses.append(alpha_loss_i.item())

        # ═══ Soft-update centralized critic target ═══
        for p, p_tgt in zip(self.critic.parameters(), self.critic_target.parameters()):
            p_tgt.data.mul_(1 - self.tau).add_(self.tau * p.data)

        return {
            'critic_loss': critic_loss.item(),
            'actor_loss': float(np.mean(actor_losses)),
            'alpha_loss': float(np.mean(alpha_losses)),
            'alpha': float(np.mean([a.alpha.item() for a in agents])),
        }

    def save_critic(self, path):
        """Save shared centralized critic to disk."""
        torch.save({
            'critic': self.critic.state_dict(),
            'critic_target': self.critic_target.state_dict(),
            'critic_opt': self.critic_optimizer.state_dict(),
        }, path)

    def load_critic(self, path):
        """Load shared centralized critic from disk."""
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.critic.load_state_dict(ckpt['critic'])
        self.critic_target.load_state_dict(ckpt['critic_target'])
        self.critic_optimizer.load_state_dict(ckpt['critic_opt'])
