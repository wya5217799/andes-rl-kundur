"""
SAC (Soft Actor-Critic) 智能体

每个 VSG 储能对应一个独立的 SAC agent.
- Actor: 高斯策略, tanh 压缩
- Critic: Double-Q
- 自动熵调节 (learnable α)
- 软目标网络更新
"""

import copy
import os

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import DoubleQCritic
from andes_rl_kundur.agents.sac_base import _SACBase


class SACAgent(_SACBase):
    """Per-agent SAC: own actor + own DoubleQ critic + own alpha."""

    algo_name: str = "sac"

    def __init__(
        self,
        obs_dim,
        action_dim,
        hidden_sizes,
        lr=3e-4,
        gamma=0.99,
        tau=0.005,
        buffer_size=10000,
        batch_size=256,
        device='cpu',
        alpha_min=0.005,
        alpha_max=5.0,
    ):
        super().__init__(
            obs_dim=obs_dim, action_dim=action_dim,
            hidden_sizes=hidden_sizes, lr=lr,
            buffer_size=buffer_size, batch_size=batch_size,
            device=device, alpha_min=alpha_min, alpha_max=alpha_max,
        )
        self.gamma = gamma
        self.tau = tau

        # Independent critic (CTDE variant skips these)
        self.critic = DoubleQCritic(obs_dim, action_dim, hidden_sizes).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

    def update(self) -> dict | None:
        """执行一步 SAC 更新. 返回 loss 字典."""
        if len(self.buffer) < self.batch_size:
            return None

        batch = self.buffer.sample(self.batch_size, self.device)
        obs = batch['obs']
        actions = batch['actions']
        rewards = batch['rewards']
        next_obs = batch['next_obs']
        dones = batch['dones']

        # ═══ Critic 更新 ═══
        with torch.no_grad():
            next_actions, next_log_prob = self.actor.sample(next_obs)
            q1_target, q2_target = self.critic_target(next_obs, next_actions)
            q_target = torch.min(q1_target, q2_target)
            y = rewards + self.gamma * (1 - dones) * (q_target - self.alpha * next_log_prob)

        q1, q2 = self.critic(obs, actions)
        critic_loss = F.mse_loss(q1, y) + F.mse_loss(q2, y)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        # ═══ Actor 更新 ═══
        new_actions, log_prob = self.actor.sample(obs)
        q1_new, q2_new = self.critic(obs, new_actions)
        q_new = torch.min(q1_new, q2_new)
        actor_loss = (self.alpha.detach() * log_prob - q_new).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
        self.actor_optimizer.step()

        # ═══ Alpha 更新 ═══
        alpha_loss = -(self.log_alpha * (log_prob.detach() + self.target_entropy)).mean()

        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        nn.utils.clip_grad_norm_([self.log_alpha], self.max_grad_norm)
        self.alpha_optimizer.step()
        with torch.no_grad():
            self.log_alpha.data.clamp_(self._log_alpha_min, self._log_alpha_max)

        # ═══ 软目标更新 ═══
        self._soft_update()

        return {
            'critic_loss': critic_loss.item(),
            'actor_loss': actor_loss.item(),
            'alpha_loss': alpha_loss.item(),
            'alpha': self.alpha.item(),
        }

    def _soft_update(self):
        """目标网络软更新: θ_tgt ← τ·θ + (1-τ)·θ_tgt."""
        for p, p_tgt in zip(self.critic.parameters(), self.critic_target.parameters()):
            p_tgt.data.mul_(1 - self.tau).add_(self.tau * p.data)

    def save(self, path, metadata: dict | None = None, save_buffer: bool = False):
        torch.save({
            'actor': self.actor.state_dict(),
            'critic': self.critic.state_dict(),
            'critic_target': self.critic_target.state_dict(),
            'log_alpha': self.log_alpha.data,
            'actor_opt': self.actor_optimizer.state_dict(),
            'critic_opt': self.critic_optimizer.state_dict(),
            'alpha_opt': self.alpha_optimizer.state_dict(),
            'metadata': metadata or {},
        }, path)
        if save_buffer:
            buf_path = str(path).replace('.pt', '_buffer.npz')
            self.buffer.save(buf_path)

    def load(self, path) -> dict:
        """加载 checkpoint，返回 metadata dict（无 metadata 时返回 {}）。
        若同路径存在 _buffer.npz，自动恢复 replay buffer。
        """
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.actor.load_state_dict(ckpt['actor'])
        self.critic.load_state_dict(ckpt['critic'])
        self.critic_target.load_state_dict(ckpt['critic_target'])
        self.log_alpha.data = ckpt['log_alpha']
        self.actor_optimizer.load_state_dict(ckpt['actor_opt'])
        self.critic_optimizer.load_state_dict(ckpt['critic_opt'])
        self.alpha_optimizer.load_state_dict(ckpt['alpha_opt'])
        buf_path = str(path).replace('.pt', '_buffer.npz')
        if os.path.exists(buf_path):
            self.buffer.load(buf_path)
        return ckpt.get('metadata', {})
