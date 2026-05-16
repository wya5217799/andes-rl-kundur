"""
SAC 神经网络 — Actor (高斯策略) + Critic (Double-Q)

论文 Section IV-A: 4 层全连接, 每层 128 单元
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal

LOG_STD_MIN = -20.0
LOG_STD_MAX = 2.0
EPS = 1e-6


def build_mlp(input_dim: int, hidden_sizes: list[int], output_dim: int) -> nn.Sequential:
    """构建多层感知机."""
    layers = []
    prev = input_dim
    for h in hidden_sizes:
        layers.append(nn.Linear(prev, h))
        layers.append(nn.ReLU())
        prev = h
    layers.append(nn.Linear(prev, output_dim))
    return nn.Sequential(*layers)


class GaussianActor(nn.Module):
    """
    高斯策略网络, tanh 压缩输出.

    obs → 4×128 hidden → (mean, log_std) → tanh(sample)
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden_sizes: list[int]) -> None:
        super().__init__()
        layers = []
        prev = obs_dim
        for h in hidden_sizes:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            prev = h
        self.net = nn.Sequential(*layers)
        self.mean_head = nn.Linear(prev, action_dim)
        self.log_std_head = nn.Linear(prev, action_dim)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.net(obs)
        mean = self.mean_head(h)
        log_std = self.log_std_head(h)
        log_std = torch.clamp(log_std, LOG_STD_MIN, LOG_STD_MAX)
        return mean, log_std

    def sample(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        重参数化采样 + tanh 压缩.

        Returns
        -------
        action : Tensor, shape (..., action_dim), 范围 [-1, 1]
        log_prob : Tensor, shape (..., 1)
        """
        mean, log_std = self.forward(obs)
        std = log_std.exp()
        dist = Normal(mean, std)

        # 重参数化采样
        u = dist.rsample()
        action = torch.tanh(u)

        # log_prob 修正 tanh 压缩
        log_prob = dist.log_prob(u) - torch.log(1 - action.pow(2) + EPS)
        log_prob = log_prob.sum(dim=-1, keepdim=True)

        return action, log_prob

    def deterministic(self, obs: torch.Tensor) -> torch.Tensor:
        """确定性输出 (评估用)."""
        mean, _ = self.forward(obs)
        return torch.tanh(mean)


class QNetwork(nn.Module):
    """Q 值网络: (obs, action) → Q(s, a)."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_sizes: list[int]) -> None:
        super().__init__()
        self.net = build_mlp(obs_dim + action_dim, hidden_sizes, 1)

    def forward(self, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        x = torch.cat([obs, action], dim=-1)
        return self.net(x)


class DoubleQCritic(nn.Module):
    """Double-Q Critic: 两个独立的 Q 网络."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_sizes: list[int]) -> None:
        super().__init__()
        self.q1 = QNetwork(obs_dim, action_dim, hidden_sizes)
        self.q2 = QNetwork(obs_dim, action_dim, hidden_sizes)

    def forward(
        self, obs: torch.Tensor, action: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.q1(obs, action), self.q2(obs, action)


# ──────────────────────────────────────────────────────────────────────
# Recurrent variants (R56 — structural pivot vs hexagon ceiling)
#
# The R49–R55 six-failure hexagon (CLM-0057..0062) established that any
# memoryless deterministic policy on V4 + decentralized obs + paper-
# faithful reward collapses to a near-constant setpoint at eval. The
# R55 verdict's mechanism analysis: the only escapes from the noise-
# hijack reward channel are (1) deterministic-output reward, (2) sparse
# end-of-episode reward, or (3) recurrent policy.
#
# RecurrentActor implements escape (3): π(obs_t, h_t) is structurally
# time-varying via the LSTMCell hidden state, even when obs_t is held
# constant. Critic uses its own LSTMCell — sharing the actor's would
# create training-time gradient interference.
# ──────────────────────────────────────────────────────────────────────


HiddenState = tuple[torch.Tensor, torch.Tensor]


class RecurrentActor(nn.Module):
    """LSTMCell-based deterministic actor for TD3.

    ``forward(obs, h_prev) -> (action_tanh, h_new)``.

    The hidden state ``h = (h_cell, c_cell)`` is owned by the caller
    (train loop or eval closure) so the same network can be batched
    across sequences (training, batched h) or stepped one obs at a
    time (rollout, batch=1 h).
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim, hidden)
        self.fc_out = nn.Linear(hidden, action_dim)
        self.hidden = hidden
        self.obs_dim = obs_dim
        self.action_dim = action_dim

    def forward(
        self, obs: torch.Tensor, h_prev: HiddenState
    ) -> tuple[torch.Tensor, HiddenState]:
        h, c = self.lstm(obs, h_prev)
        a = torch.tanh(self.fc_out(h))
        return a, (h, c)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> HiddenState:
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)

    def deterministic(
        self, obs: torch.Tensor, h_prev: HiddenState
    ) -> tuple[torch.Tensor, HiddenState]:
        """Alias of forward — symmetry with GaussianActor.deterministic()."""
        return self.forward(obs, h_prev)


class RecurrentQNetwork(nn.Module):
    """Q(obs, action, h_prev) -> (q, h_new) via LSTMCell."""

    def __init__(self, obs_dim: int, action_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim + action_dim, hidden)
        self.fc_out = nn.Linear(hidden, 1)
        self.hidden = hidden
        self.input_dim = obs_dim + action_dim

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev: HiddenState,
    ) -> tuple[torch.Tensor, HiddenState]:
        x = torch.cat([obs, action], dim=-1)
        h, c = self.lstm(x, h_prev)
        q = self.fc_out(h)
        return q, (h, c)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> HiddenState:
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)


class RecurrentDoubleQCritic(nn.Module):
    """Twin Q critics with independent hidden states (R2D2 convention).

    Each Q network has its own LSTMCell + linear head. The two share
    no parameters — required for the TD3 min-Q target trick to remain
    unbiased.
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.q1 = RecurrentQNetwork(obs_dim, action_dim, hidden)
        self.q2 = RecurrentQNetwork(obs_dim, action_dim, hidden)
        self.hidden = hidden

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev: tuple[HiddenState, HiddenState],
    ) -> tuple[torch.Tensor, torch.Tensor, tuple[HiddenState, HiddenState]]:
        h1_prev, h2_prev = h_prev
        q1, h1_new = self.q1(obs, action, h1_prev)
        q2, h2_new = self.q2(obs, action, h2_prev)
        return q1, q2, (h1_new, h2_new)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> tuple[HiddenState, HiddenState]:
        return (
            self.q1.init_hidden(batch_size, device),
            self.q2.init_hidden(batch_size, device),
        )
