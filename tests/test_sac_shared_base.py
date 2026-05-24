"""``_SACBase`` shared concrete base class for SACAgent + SACAgentCTDE.

Both per-agent SAC variants duplicate ~80 lines of constructor (actor
network + actor optimizer + log_alpha + alpha optimizer + per-agent
replay buffer + entropy target + max_grad_norm). Lift them into
``_SACBase``. SACAgent extends with its independent critic; SACAgentCTDE
extends with hooks for a coordinator-owned shared critic.

The BaseAgent Protocol (Cand 7 of the architecture review) covers the
contract; this base class covers the concrete implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_sac_base_provides_shared_state():
    from andes_rl_kundur.agents.sac_base import _SACBase
    base = _SACBase(obs_dim=7, action_dim=2, hidden_sizes=[64, 64], device="cpu")
    assert hasattr(base, "actor")
    assert hasattr(base, "actor_optimizer")
    assert hasattr(base, "log_alpha")
    assert hasattr(base, "alpha_optimizer")
    assert hasattr(base, "buffer")
    assert hasattr(base, "max_grad_norm")
    # alpha property
    assert float(base.alpha) > 0


def test_sac_agent_inherits_from_sac_base():
    from andes_rl_kundur.agents.sac import SACAgent
    from andes_rl_kundur.agents.sac_base import _SACBase
    agent = SACAgent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    assert isinstance(agent, _SACBase)
    # SACAgent's own state: critic
    assert hasattr(agent, "critic")
    assert hasattr(agent, "critic_target")


def test_sac_agent_ctde_inherits_from_sac_base():
    from andes_rl_kundur.agents.sac_base import _SACBase
    from andes_rl_kundur.agents.sac_ctde import SACAgentCTDE
    agent = SACAgentCTDE(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    assert isinstance(agent, _SACBase)
    # SACAgentCTDE has NO per-agent critic
    assert not hasattr(agent, "critic")


def test_sac_base_is_recurrent_false_by_default():
    """``_SACBase`` (and SAC/SAC-CTDE) must expose ``is_recurrent=False``
    explicitly so the training loop can read ``ag.is_recurrent`` directly
    instead of falling back through ``getattr(ag, "is_recurrent", False)``.

    Pinned in R77 follow-up to R76 review IMPORTANT-1: without an
    explicit attribute, a future agent that forgets the flag silently
    inherits the legacy MLP buffer-size branch, which is correct for
    SAC but a latent bug for any new recurrent agent."""
    from andes_rl_kundur.agents.sac import SACAgent
    from andes_rl_kundur.agents.sac_base import _SACBase
    from andes_rl_kundur.agents.sac_ctde import SACAgentCTDE
    assert _SACBase.is_recurrent is False
    sac = SACAgent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    ctde = SACAgentCTDE(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    assert sac.is_recurrent is False
    assert ctde.is_recurrent is False


def test_td3_lstm_is_recurrent_true():
    """Cross-check: the only recurrent agent in the repo keeps
    ``is_recurrent=True``. Pins the contract from the other side."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent
    assert TD3LSTMAgent.is_recurrent is True


def test_td3_mlp_is_recurrent_false():
    """Non-recurrent TD3 also exposes the flag explicitly."""
    from andes_rl_kundur.agents.td3 import TD3Agent
    assert TD3Agent.is_recurrent is False


def test_select_action_works_identically_for_both():
    """Both variants share select_action; they should produce a valid
    action shape from the same obs+seed."""
    from andes_rl_kundur.agents.sac import SACAgent
    from andes_rl_kundur.agents.sac_ctde import SACAgentCTDE

    torch.manual_seed(0)
    sac = SACAgent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    torch.manual_seed(0)
    ctde = SACAgentCTDE(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])

    obs = np.zeros(7, dtype=np.float32)
    a_sac = sac.select_action(obs, deterministic=True)
    a_ctde = ctde.select_action(obs, deterministic=True)
    assert a_sac.shape == (2,)
    assert a_ctde.shape == (2,)
    # Same actor init (seeded) → same deterministic output
    np.testing.assert_allclose(a_sac, a_ctde)
