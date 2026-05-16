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
from andes_rl_kundur.config import HIDDEN_SIZES
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4


CKPT_NAME_FMT = "agent_{i}_{suffix}.pt"


def detect_algo(ckpt_path: Path) -> str:
    """Inspect the ckpt's self-described ``algo`` field. Defaults to ``"sac"``
    for pre-2026-05-17 ckpts that don't carry the field."""
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    return ckpt.get("algo", "sac")


def load_agents(
    ckpt_dir: Path,
    *,
    suffix: str = "best",
    n_agents: int | None = None,
    hidden_sizes: tuple[int, ...] | None = None,
    device: str = "cpu",
) -> list:
    """Load N agents from ``ckpt_dir/agent_{i}_{suffix}.pt``.

    Args:
        ckpt_dir:     directory containing the per-agent ckpt files.
        suffix:       ckpt filename suffix (``"best"`` or ``"final"``).
        n_agents:     number of agents (default: ``AndesMultiVSGEnvV4.N_AGENTS``).
        hidden_sizes: actor/critic hidden layer sizes (default:
                      ``andes_rl_kundur.config.HIDDEN_SIZES``).
        device:       torch device.

    Returns:
        List of agent instances (SACAgent or TD3Agent depending on each
        ckpt's ``algo`` field). Each agent has had ``.load(ckpt_path)`` called.

    Raises:
        FileNotFoundError: if any expected ckpt file is missing.
    """
    if n_agents is None:
        n_agents = AndesMultiVSGEnvV4.N_AGENTS
    if hidden_sizes is None:
        hidden_sizes = HIDDEN_SIZES
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
        else:
            agent = SACAgent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes, device=device,
            )
        agent.load(str(ckpt_path))
        agents.append(agent)
    return agents
