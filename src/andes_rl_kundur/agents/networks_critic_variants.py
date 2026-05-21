"""R98 — Recurrent critic variants for plateau-mechanism intervention.

Two minimal-diff critic head variants targeting CLM-0157 priorities (a) and (b):

1. ``RecurrentQRDoubleQCritic`` — quantile-regression critic head (51 quantiles
   per Q network) for QR-DQN-style distributional critic training. CLM-0157(a),
   strongest theoretical mechanism break against the R72_w4 critic affine-Q
   pathology documented in CLM-0148-0156.

2. ``RecurrentAfeDoubleQCritic`` — action-feature-engineered critic input.
   Critic eats ``[obs, a, a², |a|, sign(a)]`` instead of ``[obs, a]``, giving
   the bilinear LSTM-cell first-layer feature expressivity for concave-around-
   interior preference without architectural change. CLM-0157(b), min-viable-diff.

Both critic variants are drop-in replacements for ``networks.RecurrentDoubleQCritic``
EXCEPT QR returns a quantile vector (B, N_QUANTILES) instead of scalar (B, 1).
AFE preserves the scalar-Q interface bit-for-bit (only the internal input shape
changes), so ``TD3LSTMAgent``'s update() works unchanged with AFE.

Reference: Dabney, Will, et al. "Distributional reinforcement learning with
quantile regression." AAAI 2018 §4 (quantile-Huber loss).
"""
from __future__ import annotations

import torch
import torch.nn as nn

from andes_rl_kundur.agents.networks import HiddenState

# QR-DQN canonical (Dabney et al. 2018 Table 1)
N_QUANTILES_DEFAULT = 51


# ─── Distributional (QR) critic ───────────────────────────────────────────


class RecurrentQRQNetwork(nn.Module):
    """Quantile-regression Q network. Same recurrent backbone as
    ``RecurrentQNetwork``, only the output head differs: instead of a
    scalar Q, it emits ``n_quantiles`` quantile estimates of the return
    distribution.

    Forward returns ``(quantiles: (B, N), h_new)`` where N = ``n_quantiles``.
    The ``scalar_q`` proxy (used by the actor loss and by the TD3 min-Q
    target trick) is ``quantiles.mean(dim=-1, keepdim=True)``; helper
    accessor ``mean_q`` provided.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        n_quantiles: int = N_QUANTILES_DEFAULT,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim + action_dim, hidden)
        self.fc_out = nn.Linear(hidden, n_quantiles)
        self.hidden = hidden
        self.input_dim = obs_dim + action_dim
        self.n_quantiles = n_quantiles

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev: HiddenState,
    ) -> tuple[torch.Tensor, HiddenState]:
        x = torch.cat([obs, action], dim=-1)
        h, c = self.lstm(x, h_prev)
        quantiles = self.fc_out(h)  # (B, N)
        return quantiles, (h, c)

    def mean_q(self, quantiles: torch.Tensor) -> torch.Tensor:
        """Scalar Q proxy = expected value of the quantile distribution."""
        return quantiles.mean(dim=-1, keepdim=True)  # (B, 1)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> HiddenState:
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)


class RecurrentQRDoubleQCritic(nn.Module):
    """Twin QR-Q critics with independent hidden states (R2D2 + QR-DQN).

    Each Q network emits its own quantile vector. The TD3 min-Q trick is
    applied at the *scalar mean* level (``min(mean(q1), mean(q2))``); the
    quantile-Huber loss is computed separately per critic against the
    target's selected quantile vector.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        n_quantiles: int = N_QUANTILES_DEFAULT,
    ) -> None:
        super().__init__()
        self.q1 = RecurrentQRQNetwork(obs_dim, action_dim, hidden, n_quantiles)
        self.q2 = RecurrentQRQNetwork(obs_dim, action_dim, hidden, n_quantiles)
        self.hidden = hidden
        self.n_quantiles = n_quantiles

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


def quantile_huber_loss(
    quantile_pred: torch.Tensor,
    target_quantiles: torch.Tensor,
    kappa: float = 1.0,
) -> torch.Tensor:
    """Standard QR-DQN quantile-Huber loss (Dabney et al. 2018 §4 Eq. 3).

    Args:
        quantile_pred: shape ``(B, N)`` — quantile predictions for the
            current state-action.
        target_quantiles: shape ``(B, N)`` — target quantile values
            ``y = r + γ(1-d) q_target`` (one row per batch element).
        kappa: Huber threshold (default 1.0, QR-DQN canonical).

    Returns:
        scalar tensor — mean loss over batch.

    Implementation:
        τ_i = (i + 0.5) / N is the quantile midpoint level. For each pair
        (i, j), δ_ij = target_j - pred_i. The asymmetric Huber loss is

            ρ_τ(δ) = | τ - 𝟙(δ < 0) | · Huber_κ(δ)

        averaged over j (target dim, "the M-projection"), summed over i
        (prediction dim), then averaged over batch.
    """
    n_quantiles = quantile_pred.shape[-1]
    assert target_quantiles.shape[-1] == n_quantiles, (
        f"pred N={n_quantiles} target N={target_quantiles.shape[-1]} mismatch"
    )

    # τ_i ∈ [0, 1] — quantile midpoints. (1, N) so it broadcasts over batch.
    tau = (torch.arange(n_quantiles, dtype=quantile_pred.dtype,
                        device=quantile_pred.device) + 0.5) / n_quantiles
    tau = tau.view(1, n_quantiles, 1)  # (1, N_pred, 1)

    # δ_ij = target_j - pred_i. pred is rows, target is cols.
    # pred  → (B, N_pred, 1)
    # tgt   → (B, 1, N_tgt)
    # delta → (B, N_pred, N_tgt)
    delta = target_quantiles.unsqueeze(1) - quantile_pred.unsqueeze(2)

    # Huber loss: 0.5 δ² if |δ|<κ else κ(|δ| - 0.5κ)
    abs_delta = delta.abs()
    huber = torch.where(
        abs_delta < kappa,
        0.5 * delta.pow(2),
        kappa * (abs_delta - 0.5 * kappa),
    )

    # asymmetric weight |τ - 𝟙(δ<0)| ∈ [0, 1]
    weight = (tau - (delta < 0).to(delta.dtype)).abs()  # (B, N_pred, N_tgt)

    # mean over target dim, sum over pred dim, mean over batch — Dabney 2018
    # Eq. 3 canonical QR-DQN form. R143 attempted "mean over pred dim" as a
    # fix for CLM-0263 do-nothing attractor; R142 (untouched sum form)
    # empirically scored geo=0.3845 ≈ R72_w4 baseline 0.3908, while R143
    # (mean form) stalled at do-nothing → REVERTED. The CLM-0263 attractor
    # mechanism is real but the actor escapes if critic gradient magnitude
    # is large enough — sum-over-pred IS the correct scale.
    loss_per_pred = (weight * huber).mean(dim=2)  # (B, N_pred)
    loss_per_batch = loss_per_pred.sum(dim=1)     # (B,) — sum, canonical
    return loss_per_batch.mean()


# ─── Action-feature-engineered critic ─────────────────────────────────────


def _afe_features(action: torch.Tensor) -> torch.Tensor:
    """Expand action ∈ [-1, 1]^A to 5A features capturing different
    nonlinearities the bilinear LSTM-cell first layer can't synthesise:

    - ``action``       — original linear path (preserves R56-R72 expressivity)
    - ``action²``      — concave-around-interior preference, the missing
                         second-order pathway flagged by CLM-0150 (d²Q/da² ≈ 0)
    - ``|action|``     — saturation magnitude, sign-agnostic
    - ``sign(action)`` — discrete categorical for boundary detection

    Returns ``(B, 4*A)`` concat along last dim. Original ``action`` is
    duplicated by ``sign(action) * |action|`` algebraically, but explicit
    inclusion keeps the path interpretable for ablation.
    """
    return torch.cat(
        [action, action.pow(2), action.abs(), torch.sign(action)],
        dim=-1,
    )


AFE_EXPAND = 4  # number of feature blocks _afe_features stacks (must match)


class RecurrentAfeQNetwork(nn.Module):
    """Action-feature-engineered Q network. Critic eats ``[obs, AFE(a)]``
    where ``AFE`` expands action to 4*action_dim features.

    Output interface identical to ``RecurrentQNetwork`` — scalar Q +
    LSTM hidden — so ``TD3LSTMAgent.update()`` works unchanged with this
    drop-in critic via ``TD3AfeLstmAgent(__init__-only-override)``.
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim + AFE_EXPAND * action_dim, hidden)
        self.fc_out = nn.Linear(hidden, 1)
        self.hidden = hidden
        self.action_dim = action_dim
        self.input_dim = obs_dim + AFE_EXPAND * action_dim

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev: HiddenState,
    ) -> tuple[torch.Tensor, HiddenState]:
        afe = _afe_features(action)              # (B, 4A)
        x = torch.cat([obs, afe], dim=-1)        # (B, obs+4A)
        h, c = self.lstm(x, h_prev)
        q = self.fc_out(h)
        return q, (h, c)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> HiddenState:
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)


class RecurrentAfeDoubleQCritic(nn.Module):
    """Twin AFE-Q critics with independent hidden states.

    Bit-compatible interface with ``RecurrentDoubleQCritic`` — same forward
    signature, same hidden-state structure, same scalar-Q output. Action
    feature expansion happens inside each Q network's forward.
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.q1 = RecurrentAfeQNetwork(obs_dim, action_dim, hidden)
        self.q2 = RecurrentAfeQNetwork(obs_dim, action_dim, hidden)
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


# ─── Stacked QR + AFE critic (R125 prototype) ────────────────────────────


class RecurrentQRAfeQNetwork(nn.Module):
    """Stacked QR + AFE Q network — input is action-feature-engineered,
    output is N quantiles. Combines CLM-0157(a) + (b) into a single critic
    head. Input dim = ``obs_dim + 4*action_dim``; output = ``(B, n_quantiles)``.

    Use when both R98 prototype interventions are stacked (R125+ candidates).
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        n_quantiles: int = N_QUANTILES_DEFAULT,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim + AFE_EXPAND * action_dim, hidden)
        self.fc_out = nn.Linear(hidden, n_quantiles)
        self.hidden = hidden
        self.action_dim = action_dim
        self.input_dim = obs_dim + AFE_EXPAND * action_dim
        self.n_quantiles = n_quantiles

    def forward(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        h_prev: HiddenState,
    ) -> tuple[torch.Tensor, HiddenState]:
        afe = _afe_features(action)
        x = torch.cat([obs, afe], dim=-1)
        h, c = self.lstm(x, h_prev)
        quantiles = self.fc_out(h)
        return quantiles, (h, c)

    def mean_q(self, quantiles: torch.Tensor) -> torch.Tensor:
        return quantiles.mean(dim=-1, keepdim=True)

    def init_hidden(
        self, batch_size: int, device: str | torch.device = "cpu"
    ) -> HiddenState:
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)


class RecurrentQRAfeDoubleQCritic(nn.Module):
    """Twin stacked QR+AFE critics. Output shape (B, n_quantiles) per critic;
    twin hidden states (R2D2 + QR-DQN + AFE)."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
        n_quantiles: int = N_QUANTILES_DEFAULT,
    ) -> None:
        super().__init__()
        self.q1 = RecurrentQRAfeQNetwork(obs_dim, action_dim, hidden, n_quantiles)
        self.q2 = RecurrentQRAfeQNetwork(obs_dim, action_dim, hidden, n_quantiles)
        self.hidden = hidden
        self.n_quantiles = n_quantiles

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
