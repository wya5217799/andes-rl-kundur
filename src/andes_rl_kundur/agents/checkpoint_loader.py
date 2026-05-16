"""Single source of truth for ``agent_{i}_{suffix}.pt`` checkpoint loading.

Eval scripts (eval_ddic, eval_ensemble, eval_all_seeds, eval_no_control)
previously copy-pasted the same load_actors() function — naming convention,
SAC vs TD3 detection, hidden-size config — into 3 places. Any rename of the
checkpoint file pattern had to be updated in lockstep.

This module is a thin function-not-class wrapper. The deletion test passes
because the duplicated logic across 3 callers now lives in one place; the
seam (SAC vs TD3 via the ckpt's ``algo`` field) is a real fork point, not
speculation.
"""
from __future__ import annotations

from pathlib import Path

import torch

from andes_rl_kundur.agents.sac import SACAgent
from andes_rl_kundur.agents.td3 import TD3Agent
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent
from andes_rl_kundur.config import HIDDEN_SIZES
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4


CKPT_NAME_FMT = "agent_{i}_{suffix}.pt"

# nn.LSTMCell stacks the input/forget/cell/output gate weights into one
# ``weight_ih`` tensor with first dim ``4 * hidden`` (standard PyTorch
# layout). Use this constant when recovering ``hidden`` from a ckpt.
LSTM_GATE_COUNT = 4


def detect_algo(ckpt_path: Path) -> str:
    """Inspect the ckpt's self-described ``algo`` field. Defaults to ``"sac"``
    for pre-2026-05-17 ckpts that don't carry the field."""
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    return ckpt.get("algo", "sac")


def detect_actor_dims(ckpt_path: Path) -> tuple[int, int]:
    """Inspect ckpt['actor'] shape to recover (obs_dim, hidden_size).

    Three actor architectures are supported:

    * MLP (SAC ``GaussianActor`` / non-recurrent TD3): the first linear
      layer is ``net.0.weight`` with shape ``(hidden, obs_dim)``.
    * Recurrent (R56 ``RecurrentActor``): the LSTMCell input-to-hidden
      weight is ``lstm.weight_ih`` with shape ``(4 * hidden, obs_dim)``
      — the 4× block contains the i/f/g/o gate stacks.

    All four MLP hidden layers are assumed uniform-width (matches
    ``train.py --hidden-size N`` semantics); the LSTM is a single cell
    so hidden has only one value.

    R50 optimization A + R56 LSTM branch.
    """
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    actor = ckpt["actor"]
    if "lstm.weight_ih" in actor:
        # RecurrentActor: weight_ih shape is (LSTM_GATE_COUNT*hidden, obs_dim)
        w = actor["lstm.weight_ih"]
        return int(w.shape[1]), int(w.shape[0] // LSTM_GATE_COUNT)
    w = actor["net.0.weight"]
    return int(w.shape[1]), int(w.shape[0])


def load_agents(
    ckpt_dir: Path,
    *,
    suffix: str = "best",
    n_agents: int | None = None,
    hidden_sizes: tuple[int, ...] | None = None,
    obs_dim: int | None = None,
    device: str = "cpu",
) -> list:
    """Load N agents from ``ckpt_dir/agent_{i}_{suffix}.pt``.

    Args:
        ckpt_dir:     directory containing the per-agent ckpt files.
        suffix:       ckpt filename suffix (``"best"`` or ``"final"``).
        n_agents:     number of agents (default: ``AndesMultiVSGEnvV4.N_AGENTS``).
        hidden_sizes: actor/critic hidden layer sizes. If ``None`` (default),
                      auto-detected from ``ckpt['actor']['net.0.weight']``.
                      Pass explicitly to override / pin for safety.
        obs_dim:      actor input dimension. If ``None`` (default), auto-detected
                      from the ckpt as above. Pass explicitly when loading into
                      an env whose ``OBS_DIM`` may differ (e.g. INCLUDE_OWN_ACTION_OBS).
        device:       torch device.

    Returns:
        List of agent instances (SACAgent or TD3Agent depending on each
        ckpt's ``algo`` field). Each agent has had ``.load(ckpt_path)`` called.

    Raises:
        FileNotFoundError: if any expected ckpt file is missing.
        RuntimeError:      if explicit ``hidden_sizes`` / ``obs_dim`` mismatch
                           the ckpt's actor (user-intent-wins semantics).
    """
    if n_agents is None:
        n_agents = AndesMultiVSGEnvV4.N_AGENTS

    # Auto-detect dims from the first ckpt when caller did not pin them.
    if hidden_sizes is None or obs_dim is None:
        first_ckpt = ckpt_dir / CKPT_NAME_FMT.format(i=0, suffix=suffix)
        if first_ckpt.exists():
            detected_obs, detected_hidden = detect_actor_dims(first_ckpt)
            if hidden_sizes is None:
                hidden_sizes = (detected_hidden,) * 4
            if obs_dim is None:
                obs_dim = detected_obs

    # Fallbacks (only reached if first ckpt is missing; the per-i loop below
    # will then raise FileNotFoundError, but we still need non-None values).
    if hidden_sizes is None:
        hidden_sizes = HIDDEN_SIZES
    if obs_dim is None:
        obs_dim = AndesMultiVSGEnvV4.OBS_DIM
    action_dim = 2

    agents: list = []
    for i in range(n_agents):
        ckpt_path = ckpt_dir / CKPT_NAME_FMT.format(i=i, suffix=suffix)
        if not ckpt_path.exists():
            raise FileNotFoundError(f"No ckpt: {ckpt_path}")
        algo = detect_algo(ckpt_path)
        if algo == "td3":
            agent = TD3Agent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes, device=device,
            )
        elif algo == "td3_lstm":
            agent = TD3LSTMAgent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes, device=device,
            )
        else:
            agent = SACAgent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes, device=device,
            )
        agent.load(str(ckpt_path))
        agents.append(agent)
    return agents
