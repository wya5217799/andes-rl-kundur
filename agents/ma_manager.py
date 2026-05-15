"""
多智能体管理器 — 协调 N 个独立 SAC 智能体.
"""
from __future__ import annotations

import os

import numpy as np

from agents.sac import SACAgent


class MultiAgentManager:
    """管理 N 个独立 SAC agent."""

    def __init__(
        self,
        n_agents: int,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: list[int],
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 10000,
        batch_size: int = 256,
        device: str = 'cpu',
    ) -> None:
        self.n_agents = n_agents
        self.agents = []
        for _ in range(n_agents):
            agent = SACAgent(
                obs_dim=obs_dim,
                action_dim=action_dim,
                hidden_sizes=hidden_sizes,
                lr=lr, gamma=gamma, tau=tau,
                buffer_size=buffer_size,
                batch_size=batch_size,
                device=device,
            )
            self.agents.append(agent)

    def select_actions(
        self,
        obs_dict: dict[int, np.ndarray],
        deterministic: bool = False,
    ) -> dict[int, np.ndarray]:
        actions = {}
        for i in range(self.n_agents):
            actions[i] = self.agents[i].select_action(obs_dict[i], deterministic)
        return actions

    def store_transitions(
        self,
        obs: dict[int, np.ndarray],
        actions: dict[int, np.ndarray],
        rewards: dict[int, float],
        next_obs: dict[int, np.ndarray],
        done: bool,
    ) -> None:
        for i in range(self.n_agents):
            self.agents[i].store_transition(
                obs[i], actions[i], rewards[i], next_obs[i], done
            )

    def update(self) -> list[dict | None]:
        """更新所有 agent. 返回各 agent 的 loss 字典列表."""
        losses = []
        for i in range(self.n_agents):
            loss = self.agents[i].update()
            losses.append(loss)
        return losses

    def clear_buffers(self) -> None:
        """清空所有 agent 的回放缓冲区 (Algorithm 1 line 16)."""
        for agent in self.agents:
            agent.buffer.clear()

    def save(self, dir_path: str) -> None:
        os.makedirs(dir_path, exist_ok=True)
        for i in range(self.n_agents):
            path = os.path.join(dir_path, f'agent_{i}.pt')
            self.agents[i].save(path)

    def load(self, dir_path: str) -> None:
        for i in range(self.n_agents):
            path = os.path.join(dir_path, f'agent_{i}.pt')
            self.agents[i].load(path)
