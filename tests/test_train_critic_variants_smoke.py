"""R108 smoke test — verify train.py dispatch for ``--algo td3_qr_lstm``
and ``--algo td3_afe_lstm`` wires correctly.

Zero ANDES. Just exercises ``build_agents`` with stub args + dummy shapes
and asserts the right agent class + key fields. Plus regression check
that the existing dispatch (``td3_lstm``, ``td3_lstm_hreg``) still works.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _make_args(algo: str, **overrides) -> argparse.Namespace:
    """Construct a Namespace mirroring train.parse_args() with the
    fields ``build_agents`` actually reads, then apply overrides."""
    defaults = {
        "algo": algo,
        "ctde": False,
        "warmstart_shared": None,
        "lstm_lr_warmup_eps": 0,
        "h_norm_reg": 0.01,
        "qr_n_quantiles": 51,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _import_train_module():
    """Import scripts/train.py as a module without executing main()."""
    import importlib.util

    train_py = ROOT / "scripts" / "train.py"
    spec = importlib.util.spec_from_file_location("train", train_py)
    train_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(train_mod)
    return train_mod


def test_train_module_imports_without_andes():
    """Regression: train.py module-level imports do not require ANDES."""
    train_mod = _import_train_module()
    assert hasattr(train_mod, "build_agents")
    assert hasattr(train_mod, "parse_args")


def test_algo_choices_include_qr_and_afe():
    """--algo choices list contains the new R98/R108 entries."""
    train_mod = _import_train_module()
    # Parse with --help would call sys.exit; instead introspect by
    # parsing a minimal arg vector and looking at the resulting algo.
    orig_argv = sys.argv
    try:
        sys.argv = ["train.py", "--algo", "td3_qr_lstm"]
        args = train_mod.parse_args()
        assert args.algo == "td3_qr_lstm"
        assert args.qr_n_quantiles == 51

        sys.argv = ["train.py", "--algo", "td3_afe_lstm",
                    "--qr-n-quantiles", "21"]
        args = train_mod.parse_args()
        assert args.algo == "td3_afe_lstm"
        # --qr-n-quantiles still accepted (no error) even though afe
        # doesn't use it — common-flag convention.
        assert args.qr_n_quantiles == 21
    finally:
        sys.argv = orig_argv


def test_build_agents_dispatches_td3_qr_lstm():
    """--algo td3_qr_lstm produces 4 TD3QRLstmAgent instances."""
    from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent

    train_mod = _import_train_module()
    args = _make_args("td3_qr_lstm", qr_n_quantiles=31)
    agents, coordinator = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    assert coordinator is None
    assert len(agents) == 4  # AndesMultiVSGEnvV4.N_AGENTS
    for ag in agents:
        assert isinstance(ag, TD3QRLstmAgent)
        assert ag.algo_name == "td3_qr_lstm"
        assert ag.is_recurrent is True
        assert ag.n_quantiles == 31


def test_build_agents_dispatches_td3_afe_lstm():
    """--algo td3_afe_lstm produces 4 TD3AfeLstmAgent instances."""
    from andes_rl_kundur.agents.td3_afe_lstm import TD3AfeLstmAgent

    train_mod = _import_train_module()
    args = _make_args("td3_afe_lstm")
    agents, coordinator = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    assert coordinator is None
    assert len(agents) == 4
    for ag in agents:
        assert isinstance(ag, TD3AfeLstmAgent)
        assert ag.algo_name == "td3_afe_lstm"
        assert ag.is_recurrent is True


def test_build_agents_regression_td3_lstm_still_works():
    """Existing td3_lstm dispatch must still produce TD3LSTMAgent
    instances (R108 must not break the base agent path)."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    train_mod = _import_train_module()
    args = _make_args("td3_lstm")
    agents, coordinator = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    assert coordinator is None
    assert len(agents) == 4
    for ag in agents:
        assert isinstance(ag, TD3LSTMAgent)
        assert ag.algo_name == "td3_lstm"


def test_build_agents_regression_td3_lstm_hreg_still_works():
    """R100/R93+ td3_lstm_hreg dispatch must still work."""
    from andes_rl_kundur.agents.td3_lstm_hreg import TD3LSTMHRegAgent

    train_mod = _import_train_module()
    args = _make_args("td3_lstm_hreg", h_norm_reg=0.005)
    agents, coordinator = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    assert coordinator is None
    assert len(agents) == 4
    for ag in agents:
        assert isinstance(ag, TD3LSTMHRegAgent)
        assert ag.algo_name == "td3_lstm_hreg"


def test_qr_lstm_warmstart_shared_rejected():
    """--warmstart-shared must be rejected for td3_qr_lstm (different
    state_dict structure from GaussianActor)."""
    train_mod = _import_train_module()
    args = _make_args("td3_qr_lstm", warmstart_shared="/tmp/fake.pt")
    # Build agents first (warmstart check happens at apply_warmstart_shared)
    agents, _ = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    with pytest.raises(ValueError, match="warmstart-shared.*incompatible"):
        train_mod.apply_warmstart_shared(agents, args)


def test_afe_lstm_ctde_rejected():
    """--ctde must be rejected for td3_afe_lstm (SAC-only flag)."""
    train_mod = _import_train_module()
    args = _make_args("td3_afe_lstm", ctde=True)
    with pytest.raises(ValueError, match="--ctde is SAC-only"):
        train_mod.build_agents(
            args=args, obs_dim=7, action_dim=2,
            hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
            buffer_size=200, batch_size=32, device="cpu",
        )


def test_build_agents_dispatches_td3_qr_afe_lstm():
    """R125 — stacked QR+AFE agent via --algo td3_qr_afe_lstm."""
    from andes_rl_kundur.agents.td3_qr_afe_lstm import TD3QRAfeLstmAgent

    train_mod = _import_train_module()
    args = _make_args("td3_qr_afe_lstm", qr_n_quantiles=21)
    agents, coordinator = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    assert coordinator is None
    assert len(agents) == 4
    for ag in agents:
        assert isinstance(ag, TD3QRAfeLstmAgent)
        assert ag.algo_name == "td3_qr_afe_lstm"
        assert ag.is_recurrent is True
        assert ag.n_quantiles == 21


def test_build_agents_dispatches_td3_warmh0_qr_afe_lstm():
    """R130 — triple-stack via --algo td3_warmh0_qr_afe_lstm."""
    from andes_rl_kundur.agents.td3_warmh0_qr_afe_lstm import TD3WarmH0QRAfeLstmAgent

    train_mod = _import_train_module()
    args = _make_args("td3_warmh0_qr_afe_lstm", qr_n_quantiles=31)
    agents, coordinator = train_mod.build_agents(
        args=args, obs_dim=7, action_dim=2,
        hidden_sizes=[64], lr=1e-4, gamma=0.99, tau=0.001,
        buffer_size=200, batch_size=32, device="cpu",
    )
    assert coordinator is None
    assert len(agents) == 4
    for ag in agents:
        assert isinstance(ag, TD3WarmH0QRAfeLstmAgent)
        assert ag.algo_name == "td3_warmh0_qr_afe_lstm"
        assert ag.is_recurrent is True
        assert ag.n_quantiles == 31
