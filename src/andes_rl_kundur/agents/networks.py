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


# ──────────────────────────────────────────────────────────────────────
# Transformer variants (R82 — novel architecture vs R72_w4 LSTM plateau)
#
# R81 9-wave sweep证实 R72_w4 hyper 是 narrow local basin, single-axis
# perturbations 75 ep内全部退化. R82 走 novel architecture path: 把
# LSTMCell stateful rollout 换成 transformer-over-rolling-obs-window.
#
# 接口兼容 RecurrentActor: forward(obs, h_prev) -> (action, h_new), 但
# h 改为 (B, K, obs_dim) 滚动 obs 窗口 (而非 LSTM (h, c) 隐藏状态).
# 这样 TD3LSTMAgent 的训练 / 回溯 / replay buffer 代码 zero change,
# 仅替换 actor/critic 类即可.
#
# 设计取舍:
# - K=10 rolling window: 跟 LSTM seq_len=25 截然不同, transformer 直接
#   attention 到所有 K 个 token. 控制步 dt=0.2s 下 K=10 = 2s 历史.
# - 1 transformer encoder layer + 4 head + hidden=64: capacity 大约
#   等于 R72_w4 LSTMCell. 想 isolate "sequence modeling 范式" 影响,
#   不引入额外 capacity bias.
# - Learnable positional embedding (不是 sinusoidal): K 固定且小, 学得
#   的位置嵌入比固定 sin/cos 更 expressive on this scale.
# ──────────────────────────────────────────────────────────────────────


# Transformer h = obs window tensor (B, K, obs_dim). For critic, h = (obs_win, act_win).
TransformerHidden = torch.Tensor


def _roll_window(window: torch.Tensor, new_token: torch.Tensor) -> torch.Tensor:
    """滚动窗口: drop 最早 token, append new_token at 末尾.

    Args:
        window: (B, K, D) 当前窗口
        new_token: (B, D) 要 append 的最新 obs/act

    Returns:
        (B, K, D) 新窗口, last 位置 = new_token
    """
    rolled = torch.roll(window, shifts=-1, dims=1)
    rolled[:, -1, :] = new_token
    return rolled


class TransformerActor(nn.Module):
    """Causal-attention actor over rolling obs window of length K.

    forward(obs, h_prev) -> (action, h_new):
        - h_prev: (B, K, obs_dim) obs window (None → zero)
        - obs: (B, obs_dim) latest obs
        - h_new = roll(h_prev, obs)
        - action = MLP(TransformerEncoder(h_new)[:, -1])
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        window_k: int = 10,
        n_heads: int = 4,
        n_layers: int = 1,
    ) -> None:
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden = hidden
        self.window_k = window_k

        # Project obs to hidden dim
        self.input_proj = nn.Linear(obs_dim, hidden)
        # Learnable positional embedding (K positions)
        self.pos_embed = nn.Parameter(torch.zeros(1, window_k, hidden))
        nn.init.normal_(self.pos_embed, std=0.02)
        # Transformer encoder
        enc_layer = nn.TransformerEncoderLayer(
            d_model=hidden,
            nhead=n_heads,
            dim_feedforward=hidden * 2,
            dropout=0.0,
            activation="relu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=n_layers)
        self.fc_out = nn.Linear(hidden, action_dim)

        # Causal mask (K, K): position i attends to positions 0..i (not future).
        # 注册为 buffer 跟 device 走.
        mask = torch.triu(torch.ones(window_k, window_k), diagonal=1).bool()
        self.register_buffer("causal_mask", mask, persistent=False)

    def forward(
        self, obs: torch.Tensor, h_prev: TransformerHidden | None
    ) -> tuple[torch.Tensor, TransformerHidden]:
        if h_prev is None:
            h_prev = torch.zeros(
                obs.shape[0], self.window_k, self.obs_dim, device=obs.device
            )
        h_new = _roll_window(h_prev, obs)
        x = self.input_proj(h_new) + self.pos_embed
        x = self.encoder(x, mask=self.causal_mask)
        a = torch.tanh(self.fc_out(x[:, -1, :]))
        return a, h_new

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> TransformerHidden:
        return torch.zeros(batch_size, self.window_k, self.obs_dim, device=device)

    def deterministic(
        self, obs: torch.Tensor, h_prev: TransformerHidden | None
    ) -> tuple[torch.Tensor, TransformerHidden]:
        return self.forward(obs, h_prev)


class TransformerQNetwork(nn.Module):
    """Q(obs_win, act_win, last_obs, last_act) -> q via transformer.

    h_prev for critic = tuple(obs_win, act_win), 每个 (B, K, D_*).
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        window_k: int = 10,
        n_heads: int = 4,
        n_layers: int = 1,
    ) -> None:
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden = hidden
        self.window_k = window_k

        self.input_proj = nn.Linear(obs_dim + action_dim, hidden)
        self.pos_embed = nn.Parameter(torch.zeros(1, window_k, hidden))
        nn.init.normal_(self.pos_embed, std=0.02)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=hidden,
            nhead=n_heads,
            dim_feedforward=hidden * 2,
            dropout=0.0,
            activation="relu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=n_layers)
        self.fc_out = nn.Linear(hidden, 1)

        mask = torch.triu(torch.ones(window_k, window_k), diagonal=1).bool()
        self.register_buffer("causal_mask", mask, persistent=False)

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev: tuple[torch.Tensor, torch.Tensor] | None,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        if h_prev is None:
            obs_win = torch.zeros(
                obs.shape[0], self.window_k, self.obs_dim, device=obs.device
            )
            act_win = torch.zeros(
                obs.shape[0], self.window_k, self.action_dim, device=obs.device
            )
        else:
            obs_win, act_win = h_prev
        obs_new = _roll_window(obs_win, obs)
        act_new = _roll_window(act_win, action)
        x = torch.cat([obs_new, act_new], dim=-1)  # (B, K, obs+act)
        x = self.input_proj(x) + self.pos_embed
        x = self.encoder(x, mask=self.causal_mask)
        q = self.fc_out(x[:, -1, :])
        return q, (obs_new, act_new)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return (
            torch.zeros(batch_size, self.window_k, self.obs_dim, device=device),
            torch.zeros(batch_size, self.window_k, self.action_dim, device=device),
        )


class MultiLayerRecurrentActor(nn.Module):
    """nn.LSTM (multi-layer) actor — R82-W2 depth variant of RecurrentActor.

    forward(obs, h_prev) -> (action, h_new):
        - h_prev = (h, c) tuple, each shape (num_layers, B, hidden)
        - obs (B, obs_dim) wrapped as (B, 1, obs_dim) sequence step
    """

    def __init__(
        self, obs_dim: int, action_dim: int, hidden: int = 64, num_layers: int = 2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(obs_dim, hidden, num_layers=num_layers, batch_first=True)
        self.fc_out = nn.Linear(hidden, action_dim)
        self.hidden = hidden
        self.num_layers = num_layers
        self.obs_dim = obs_dim
        self.action_dim = action_dim

    def forward(self, obs: torch.Tensor, h_prev: HiddenState) -> tuple[torch.Tensor, HiddenState]:
        x = obs.unsqueeze(1)  # (B, 1, D)
        out, h_new = self.lstm(x, h_prev)
        a = torch.tanh(self.fc_out(out.squeeze(1)))
        return a, h_new

    def init_hidden(self, batch_size: int, device: str | torch.device = "cpu") -> HiddenState:
        h = torch.zeros(self.num_layers, batch_size, self.hidden, device=device)
        c = torch.zeros(self.num_layers, batch_size, self.hidden, device=device)
        return (h, c)

    def deterministic(self, obs: torch.Tensor, h_prev: HiddenState) -> tuple[torch.Tensor, HiddenState]:
        return self.forward(obs, h_prev)


class MultiLayerRecurrentQNetwork(nn.Module):
    """nn.LSTM (multi-layer) Q-network."""

    def __init__(
        self, obs_dim: int, action_dim: int, hidden: int = 64, num_layers: int = 2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(obs_dim + action_dim, hidden, num_layers=num_layers, batch_first=True)
        self.fc_out = nn.Linear(hidden, 1)
        self.hidden = hidden
        self.num_layers = num_layers

    def forward(
        self, obs: torch.Tensor, action: torch.Tensor, h_prev: HiddenState,
    ) -> tuple[torch.Tensor, HiddenState]:
        x = torch.cat([obs, action], dim=-1).unsqueeze(1)  # (B, 1, obs+act)
        out, h_new = self.lstm(x, h_prev)
        q = self.fc_out(out.squeeze(1))
        return q, h_new

    def init_hidden(self, batch_size: int, device: str | torch.device = "cpu") -> HiddenState:
        h = torch.zeros(self.num_layers, batch_size, self.hidden, device=device)
        c = torch.zeros(self.num_layers, batch_size, self.hidden, device=device)
        return (h, c)


class MultiLayerRecurrentDoubleQCritic(nn.Module):
    """Twin multi-layer LSTM Q critics."""

    def __init__(
        self, obs_dim: int, action_dim: int, hidden: int = 64, num_layers: int = 2,
    ) -> None:
        super().__init__()
        self.q1 = MultiLayerRecurrentQNetwork(obs_dim, action_dim, hidden, num_layers)
        self.q2 = MultiLayerRecurrentQNetwork(obs_dim, action_dim, hidden, num_layers)
        self.hidden = hidden
        self.num_layers = num_layers

    def forward(
        self, obs: torch.Tensor, action: torch.Tensor,
        h_prev: tuple[HiddenState, HiddenState],
    ) -> tuple[torch.Tensor, torch.Tensor, tuple[HiddenState, HiddenState]]:
        h1_prev, h2_prev = h_prev
        q1, h1_new = self.q1(obs, action, h1_prev)
        q2, h2_new = self.q2(obs, action, h2_prev)
        return q1, q2, (h1_new, h2_new)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu",
    ) -> tuple[HiddenState, HiddenState]:
        return (
            self.q1.init_hidden(batch_size, device),
            self.q2.init_hidden(batch_size, device),
        )


class TransformerDoubleQCritic(nn.Module):
    """Twin Q critics with independent transformer encoders + obs/act windows.

    HiddenState 类型 = (q1_h, q2_h), 每个是 (obs_win, act_win) tuple.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        window_k: int = 10,
        n_heads: int = 4,
        n_layers: int = 1,
    ) -> None:
        super().__init__()
        self.q1 = TransformerQNetwork(obs_dim, action_dim, hidden, window_k, n_heads, n_layers)
        self.q2 = TransformerQNetwork(obs_dim, action_dim, hidden, window_k, n_heads, n_layers)
        self.hidden = hidden
        self.window_k = window_k

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev,
    ):
        h1_prev, h2_prev = h_prev if h_prev is not None else (None, None)
        q1, h1_new = self.q1(obs, action, h1_prev)
        q2, h2_new = self.q2(obs, action, h2_prev)
        return q1, q2, (h1_new, h2_new)

    def init_hidden(self, batch_size: int, device: str | torch.device = "cpu"):
        return (
            self.q1.init_hidden(batch_size, device),
            self.q2.init_hidden(batch_size, device),
        )
