"""Warm-h_0 LSTM actor (Q-0022 implementation, R107).

Drop-in replacement for ``networks.RecurrentActor`` that learns an
initial hidden state from the first-step observation instead of
defaulting to zeros. CLM-0188 (R104) confirmed via 9-ckpt forensic
sweep that the R72_w4 LSTM weights have architectural slack to reach
99%+ of saturation at step 0 if (h_0, c_0) ≠ 0; this module gives the
actor that slack via two tiny MLP heads from obs.

Lives in a separate file from ``networks.py`` so concurrent training
runs (R83 / R94 etc.) that depend on the original ``RecurrentActor``
are not perturbed.

Backward-compat:
- ``state_dict`` is a strict superset of ``RecurrentActor``'s
  (adds ``h_init.*`` and ``c_init.*`` keys).
- ``from_pretrained(rec_actor_state_dict)`` builds a WarmH0 actor with
  LSTM + fc_out copied from a vanilla ``RecurrentActor`` ckpt; the
  warm-init heads are random-initialised, ready to be fine-tuned.
- If ``use_warm_init=False`` (default during R96 ablation), the actor
  reduces to the original RecurrentActor behaviour exactly.

Public surface:
- ``WarmH0RecurrentActor(obs_dim, action_dim, hidden)``
- ``.forward(obs, h_prev) -> (action_tanh, (h, c))`` — same as base
- ``.init_hidden(batch_size, device, *, obs_for_warm=None) ->
  HiddenState`` — warm h_0 if obs_for_warm provided, else zeros
- ``.from_pretrained(state_dict) -> WarmH0RecurrentActor`` — class
  method
"""
from __future__ import annotations

import torch
from torch import nn

from andes_rl_kundur.agents.networks import HiddenState

WARM_INIT_HEAD_HIDDEN: int = 32


class WarmH0RecurrentActor(nn.Module):
    """LSTMCell deterministic actor with learnable h_0, c_0 from obs.

    Parameter count vs RecurrentActor:
      - base LSTM (input=obs_dim, hidden) + fc_out (hidden → action_dim)
      - h_init MLP: obs_dim × 32 + 32 + 32 × hidden + hidden
      - c_init MLP: obs_dim × 32 + 32 + 32 × hidden + hidden
    For obs_dim=7, hidden=64: extra params ≈ 2 × (7×32 + 32 + 32×64 + 64)
    = 2 × 2336 = 4672, vs LSTM core ≈ 18K params. ~25% overhead.
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim, hidden)
        self.fc_out = nn.Linear(hidden, action_dim)
        self.hidden = hidden
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        self.h_init = nn.Sequential(
            nn.Linear(obs_dim, WARM_INIT_HEAD_HIDDEN),
            nn.Tanh(),
            nn.Linear(WARM_INIT_HEAD_HIDDEN, hidden),
        )
        self.c_init = nn.Sequential(
            nn.Linear(obs_dim, WARM_INIT_HEAD_HIDDEN),
            nn.Tanh(),
            nn.Linear(WARM_INIT_HEAD_HIDDEN, hidden),
        )

    def forward(
        self, obs: torch.Tensor, h_prev: HiddenState
    ) -> tuple[torch.Tensor, HiddenState]:
        h, c = self.lstm(obs, h_prev)
        a = torch.tanh(self.fc_out(h))
        return a, (h, c)

    def init_hidden(
        self,
        batch_size: int,
        device: str | torch.device = "cpu",
        *,
        obs_for_warm: torch.Tensor | None = None,
    ) -> HiddenState:
        """Return (h_0, c_0).

        If ``obs_for_warm`` is provided (shape ``(batch_size, obs_dim)``),
        run the warm-init heads to produce non-zero (h_0, c_0). Otherwise
        return zeros, matching the original ``RecurrentActor`` semantics.

        The first-step convention used by the training loop is:
            obs_0 = env.reset()
            h_0, c_0 = actor.init_hidden(B, device, obs_for_warm=obs_0)
            a_0, (h_1, c_1) = actor.forward(obs_0, (h_0, c_0))
        """
        if obs_for_warm is None:
            h = torch.zeros(batch_size, self.hidden, device=device)
            c = torch.zeros(batch_size, self.hidden, device=device)
            return (h, c)

        # Guard against shape mismatch (callers can pass a single obs
        # vector and forget to unsqueeze). batch_size is authoritative.
        if obs_for_warm.dim() == 1:
            obs_for_warm = obs_for_warm.unsqueeze(0)
        if obs_for_warm.shape[0] != batch_size:
            raise ValueError(
                f"obs_for_warm batch {obs_for_warm.shape[0]} != batch_size {batch_size}"
            )

        h = self.h_init(obs_for_warm)
        c = self.c_init(obs_for_warm)
        return (h, c)

    def deterministic(
        self, obs: torch.Tensor, h_prev: HiddenState
    ) -> tuple[torch.Tensor, HiddenState]:
        return self.forward(obs, h_prev)

    @classmethod
    def from_pretrained(
        cls,
        state_dict: dict,
        obs_dim: int,
        action_dim: int,
        hidden: int = 64,
    ) -> WarmH0RecurrentActor:
        """Build a WarmH0 actor from a vanilla RecurrentActor state_dict.

        Copies ``lstm.*`` and ``fc_out.*`` keys; random-inits h_init /
        c_init heads. Use this when bootstrapping R96 training from an
        existing R57+ ckpt — h_init / c_init are then fine-tuned by
        the policy gradient.
        """
        actor = cls(obs_dim=obs_dim, action_dim=action_dim, hidden=hidden)
        own = actor.state_dict()
        # Only copy keys present in both — leaves h_init / c_init at
        # their random init.
        for k in state_dict:
            if k in own and own[k].shape == state_dict[k].shape:
                own[k] = state_dict[k].clone()
        actor.load_state_dict(own)
        return actor
