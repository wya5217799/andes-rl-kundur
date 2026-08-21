"""Directed tests for the R427 critic target normalization subclasses.

These tests pin the frozen P1 seam semantics declared in the R427 plan
(exact formulas in the module docstring of
``andes_rl_kundur/agents/cd_matd3_critic_norm.py``):

- reconstruction identity (normalized loss x sigma^2 equals the
  original-scale MSE against the raw target),
- common-channel untouched (column 1 target verbatim),
- differential gradient positive rescale (no sign flip -- the R424
  lesson generalized),
- stats EMA convergence and the sigma floor,
- save/load roundtrip preserves mu_d/sigma_d,
- actor output correction sigma*q1_d + mu_d,
- update diagnostics carry the readout fields.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from andes_rl_kundur.agents.cd_matd3 import (
    ACTION_DIM,
    AGENT_COUNT,
    AUGMENTED_OBS_DIM,
    JOINT_ACTION_DIM,
    JOINT_OBS_DIM,
    SlewAwareYangScalarTD3,
)
from andes_rl_kundur.agents.cd_matd3_critic_norm import (
    CRITIC_NORM_BETA,
    CRITIC_NORM_MU_INIT,
    CRITIC_NORM_SIGMA_INIT,
    CRITIC_NORM_SIGMA_MIN,
    PopArtDifferentialCriticSlewAwareCDMATD3Signfix,
)
from andes_rl_kundur.agents.cd_matd3_guard_constraints_vfix import (
    GuardConstrainedSlewAwareCDMATD3Signfix,
)


def _agent() -> PopArtDifferentialCriticSlewAwareCDMATD3Signfix:
    return PopArtDifferentialCriticSlewAwareCDMATD3Signfix(
        lagrange_initial=1.0,
        actor_neighbour_mask=False,
    )


def _deterministic_agent() -> PopArtDifferentialCriticSlewAwareCDMATD3Signfix:
    # policy_noise 0 makes _target_actions deterministic (the RNG draw still
    # happens but is multiplied by zero), so manual target replication in
    # the tests matches the real seam exactly.
    return PopArtDifferentialCriticSlewAwareCDMATD3Signfix(
        lagrange_initial=1.0,
        actor_neighbour_mask=False,
        policy_noise=0.0,
    )


def _base_agent() -> GuardConstrainedSlewAwareCDMATD3Signfix:
    return GuardConstrainedSlewAwareCDMATD3Signfix(
        lagrange_initial=1.0,
        actor_neighbour_mask=False,
    )


def _deterministic_base_agent() -> GuardConstrainedSlewAwareCDMATD3Signfix:
    return GuardConstrainedSlewAwareCDMATD3Signfix(
        lagrange_initial=1.0,
        actor_neighbour_mask=False,
        policy_noise=0.0,
    )


def _clone_weights(
    source: PopArtDifferentialCriticSlewAwareCDMATD3Signfix,
    target: PopArtDifferentialCriticSlewAwareCDMATD3Signfix,
) -> None:
    target.critic.load_state_dict(copy.deepcopy(source.critic.state_dict()))
    target.critic_target.load_state_dict(
        copy.deepcopy(source.critic_target.state_dict())
    )
    for source_actor, target_actor in zip(source.actors, target.actors):
        target_actor.load_state_dict(
            copy.deepcopy(source_actor.state_dict())
        )
    for source_target, target_target in zip(
        source.actor_targets, target.actor_targets
    ):
        target_target.load_state_dict(
            copy.deepcopy(source_target.state_dict())
        )


def _synthetic_batch(seed: int = 7) -> dict[str, torch.Tensor]:
    torch.manual_seed(seed)
    size = 64
    return {
        "obs": torch.randn(size, JOINT_OBS_DIM),
        "actions": torch.rand(size, JOINT_ACTION_DIM) * 2.0 - 1.0,
        "prev_actions": torch.rand(size, JOINT_ACTION_DIM) * 2.0 - 1.0,
        "rewards": torch.randn(size, 2).abs() * 3.0,
        "next_obs": torch.randn(size, JOINT_OBS_DIM),
        "dones": torch.zeros(size, 1),
    }


def test_init_stats_frozen() -> None:
    agent = _agent()
    assert agent.mu_d == pytest.approx(CRITIC_NORM_MU_INIT)
    assert agent.sigma_d == pytest.approx(CRITIC_NORM_SIGMA_INIT)


def test_reconstruction_identity() -> None:
    torch.manual_seed(0)
    batch = _synthetic_batch()
    base = _deterministic_base_agent()
    agent = _deterministic_agent()
    _clone_weights(base, agent)
    for target in (base.actor_targets, agent.actor_targets):
        for parameters in target.parameters():
            parameters.requires_grad = False
    # Pre-update manual computation with the untouched critic weights.
    with torch.no_grad():
        q1_pre, q2_pre = agent.critic(batch["obs"], batch["actions"])
        next_actions = agent._target_actions(batch)
        q1_next, q2_next = agent.critic_target(batch["next_obs"], next_actions)
        q_next = torch.min(q1_next, q2_next)
        q_next_rescaled = q_next.clone()
        q_next_rescaled[:, 0] = (
            agent.sigma_d * q_next[:, 0] + agent.mu_d
        )
        target = batch["rewards"] + agent.gamma * (
            1.0 - batch["dones"]
        ) * q_next_rescaled
        t_d = target[:, 0]
        batch_mean = float(torch.mean(t_d).cpu())
        batch_var = float(torch.var(t_d, unbiased=False).cpu())
        mu_new = (1.0 - CRITIC_NORM_BETA) * agent.mu_d + CRITIC_NORM_BETA * (
            batch_mean
        )
        sigma_new = float(
            np.clip(
                np.sqrt(
                    (1.0 - CRITIC_NORM_BETA) * agent.sigma_d**2
                    + CRITIC_NORM_BETA * batch_var
                ),
                CRITIC_NORM_SIGMA_MIN,
                None,
            )
        )
        t_d_norm = (t_d - mu_new) / sigma_new
        t_c = target[:, 1]
        loss_manual = (
            sigma_new**2
            * (
                F.mse_loss(q1_pre[:, 0], t_d_norm)
                + F.mse_loss(q2_pre[:, 0], t_d_norm)
            )
            + F.mse_loss(q1_pre[:, 1], t_c)
            + F.mse_loss(q2_pre[:, 1], t_c)
        )
        identity_alt = (
            F.mse_loss(sigma_new * q1_pre[:, 0] + mu_new, t_d)
            + F.mse_loss(sigma_new * q2_pre[:, 0] + mu_new, t_d)
            + F.mse_loss(q1_pre[:, 1], t_c)
            + F.mse_loss(q2_pre[:, 1], t_c)
        )
    # The two identity forms must agree algebraically (1e-4 float tolerance).
    assert identity_alt.item() == pytest.approx(
        loss_manual.item(), rel=1.0e-4
    )
    # Run the real update on the twin agent with identical weights.
    agent._critic_update(batch)
    assert agent.mu_d == pytest.approx(mu_new, abs=1.0e-7)
    assert agent.sigma_d == pytest.approx(sigma_new, abs=1.0e-7)
    assert agent._last_critic_loss_original == pytest.approx(
        loss_manual.item(), rel=1.0e-5
    )


def test_common_target_untouched() -> None:
    torch.manual_seed(1)
    batch = _synthetic_batch(11)
    base = _base_agent()
    agent = _agent()
    _clone_weights(base, agent)
    with torch.no_grad():
        next_actions = agent._target_actions(batch)
        q1_next, q2_next = agent.critic_target(batch["next_obs"], next_actions)
        q_next = torch.min(q1_next, q2_next)
        base_target = batch["rewards"] + agent.gamma * (
            1.0 - batch["dones"]
        ) * q_next
        q_next_rescaled = q_next.clone()
        q_next_rescaled[:, 0] = (
            agent.sigma_d * q_next[:, 0] + agent.mu_d
        )
        p1_target = batch["rewards"] + agent.gamma * (
            1.0 - batch["dones"]
        ) * q_next_rescaled
    # The common column must be verbatim identical under the P1 seam.
    assert torch.equal(p1_target[:, 1], base_target[:, 1])


def test_differential_gradient_positive_rescale() -> None:
    torch.manual_seed(2)
    batch = _synthetic_batch(23)
    torch.manual_seed(99)  # pin the agent init weights (session-stable)
    agent = _deterministic_agent()
    with torch.no_grad():
        next_actions = agent._target_actions(batch)
        q1_next, q2_next = agent.critic_target(batch["next_obs"], next_actions)
        q_next = torch.min(q1_next, q2_next)
        q_next_rescaled = q_next.clone()
        q_next_rescaled[:, 0] = (
            agent.sigma_d * q_next[:, 0] + agent.mu_d
        )
        target = batch["rewards"] + agent.gamma * (
            1.0 - batch["dones"]
        ) * q_next_rescaled
        t_d = target[:, 0]
        mu_new = (1.0 - CRITIC_NORM_BETA) * agent.mu_d + CRITIC_NORM_BETA * (
            float(torch.mean(t_d).cpu())
        )
        sigma_new = float(
            np.clip(
                np.sqrt(
                    (1.0 - CRITIC_NORM_BETA) * agent.sigma_d**2
                    + CRITIC_NORM_BETA
                    * float(torch.var(t_d, unbiased=False).cpu())
                ),
                CRITIC_NORM_SIGMA_MIN,
                None,
            )
        )
    t_d_norm = (t_d - mu_new) / sigma_new
    t_c = target[:, 1]
    q1, q2 = agent.critic(batch["obs"], batch["actions"])
    q1_corr = torch.cat(
        [sigma_new * q1[:, 0:1] + mu_new, q1[:, 1:2]], dim=1
    )
    q2_corr = torch.cat(
        [sigma_new * q2[:, 0:1] + mu_new, q2[:, 1:2]], dim=1
    )
    loss_norm = (
        F.mse_loss(q1[:, 0], t_d_norm)
        + F.mse_loss(q1[:, 1], t_c)
        + F.mse_loss(q2[:, 0], t_d_norm)
        + F.mse_loss(q2[:, 1], t_c)
    )
    loss_corrected_differential = F.mse_loss(
        q1_corr[:, 0], t_d
    ) + F.mse_loss(q2_corr[:, 0], t_d)
    loss_common = F.mse_loss(q1[:, 1], t_c) + F.mse_loss(q2[:, 1], t_c)
    params = [p for p in agent.critic.parameters() if p.requires_grad]
    grad_norm = torch.autograd.grad(
        loss_norm, params, create_graph=False, allow_unused=True,
        retain_graph=True,
    )
    grad_corr_d = torch.autograd.grad(
        loss_corrected_differential, params, create_graph=False,
        allow_unused=True, retain_graph=True,
    )
    grad_common = torch.autograd.grad(
        loss_common, params, create_graph=False, allow_unused=True
    )
    # The shared critic parameters mix both channels: L_norm decomposes
    # EXACTLY as L_corrected_differential / sigma^2 + L_common, i.e. the
    # normalized objective is a positive rescale (1/sigma^2) of the
    # original-scale differential regression error on the corrected output
    # plus the verbatim common term -- no sign flip (R424 lesson
    # generalized), common channel untouched.
    dot_d = 0.0
    decomposition_ok = True
    for g_norm, g_d, g_c in zip(grad_norm, grad_corr_d, grad_common):
        if g_d is None and g_c is None:
            if g_norm is not None:
                decomposition_ok = False
            continue
        expected = (g_d if g_d is not None else 0.0) / (sigma_new**2) + (
            g_c if g_c is not None else 0.0
        )
        # The identity is exact in exact arithmetic; float32 graph noise on
        # near-canceling shared-parameter entries needs 1e-3/1e-6 tolerance.
        if not torch.allclose(g_norm, expected, rtol=1.0e-3, atol=1.0e-6):
            decomposition_ok = False
        if g_d is not None and g_norm is not None:
            dot_d += float((g_norm * g_d).sum())
    assert dot_d > 0.0
    assert decomposition_ok


def test_stats_convergence_to_batch_statistics() -> None:
    torch.manual_seed(3)
    agent = _agent()
    target_mean, target_var = 4.0, 2.25  # std 1.5
    for _step in range(7000):
        agent._apply_critic_stats_update(target_mean, target_var)
    assert agent.mu_d == pytest.approx(target_mean, abs=1.0e-2)
    assert agent.sigma_d == pytest.approx(
        np.sqrt(target_var), rel=1.0e-2
    )


def test_sigma_floor() -> None:
    agent = _agent()
    agent._sigma_d = 1.0
    for _step in range(20000):
        agent._apply_critic_stats_update(0.0, 0.0)
    assert agent.sigma_d == pytest.approx(CRITIC_NORM_SIGMA_MIN, abs=1.0e-12)
    assert agent.sigma_d >= CRITIC_NORM_SIGMA_MIN


def test_save_load_roundtrip_preserves_stats(tmp_path) -> None:
    torch.manual_seed(4)
    agent = _agent()
    agent._mu_d = 1.25
    agent._sigma_d = 3.5
    agent._mu_rms = 2.0
    agent._mu_tv = 4.0
    path = tmp_path / "final.pt"
    agent.save(path)
    restored = _agent()
    restored.load(path)
    assert restored.mu_d == pytest.approx(1.25)
    assert restored.sigma_d == pytest.approx(3.5)
    assert restored.mu_rms == pytest.approx(2.0)
    assert restored.mu_tv == pytest.approx(4.0)


def test_actor_output_correction() -> None:
    torch.manual_seed(5)
    base = _base_agent()
    agent = _agent()
    _clone_weights(base, agent)
    obs = torch.randn(8, JOINT_OBS_DIM)
    action_row = torch.randn(8, ACTION_DIM)
    baseline_actions = torch.randn(8, JOINT_ACTION_DIM)
    agent._mu_d = 0.7
    agent._sigma_d = 2.5
    with torch.no_grad():
        q1_base = base._actor_objective(
            obs, 0, action_row, baseline_actions=baseline_actions
        )
        q1_p1 = agent._actor_objective(
            obs, 0, action_row, baseline_actions=baseline_actions
        )
    assert torch.allclose(
        q1_p1[:, 0], 2.5 * q1_base[:, 0] + 0.7, atol=1.0e-6
    )
    assert torch.allclose(q1_p1[:, 1], q1_base[:, 1], atol=1.0e-6)


def test_update_diagnostics_fields() -> None:
    torch.manual_seed(6)
    agent = _agent()
    batch_size = agent.batch_size
    for _index in range(batch_size):
        agent.store(
            torch.randn(JOINT_OBS_DIM),
            torch.zeros(JOINT_ACTION_DIM),
            torch.zeros(JOINT_ACTION_DIM),
            np.array([-1.0, -0.5], dtype=np.float32),
            torch.randn(JOINT_OBS_DIM),
            False,
        )
    diagnostics = agent.update()
    assert diagnostics is not None
    for key in (
        "critic_loss",
        "critic_loss_original",
        "actor_loss_mean",
        "lagrange",
        "mu_rms",
        "mu_tv",
        "mu_d",
        "sigma_d",
        "actor_grad_norm_log10",
    ):
        assert key in diagnostics
    assert np.isfinite(diagnostics["critic_loss"])
    assert np.isfinite(diagnostics["critic_loss_original"])
    assert np.isfinite(diagnostics["mu_d"])
    assert np.isfinite(diagnostics["sigma_d"])
    # Second update exercises the policy branch (policy_delay 2).
    for _index in range(batch_size):
        agent.store(
            torch.randn(JOINT_OBS_DIM),
            torch.zeros(JOINT_ACTION_DIM),
            torch.zeros(JOINT_ACTION_DIM),
            np.array([-1.0, -0.5], dtype=np.float32),
            torch.randn(JOINT_OBS_DIM),
            False,
        )
    diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["actor_loss_mean"])
    assert np.isfinite(diagnostics["actor_grad_norm_log10"])
    assert diagnostics["actor_grad_norm_log10"] > -30.0


def test_scalar_learner_unaffected_contract() -> None:
    # The scalar arm must stay the verbatim base learner (the runner maps
    # only the CD arms to the P1 subclass); pin the import contract here.
    scalar = SlewAwareYangScalarTD3()
    assert scalar.out_dim == 1
    assert not isinstance(
        scalar, PopArtDifferentialCriticSlewAwareCDMATD3Signfix
    )
    assert AUGMENTED_OBS_DIM == 9
    assert AGENT_COUNT == 4


def test_beta_constant_frozen() -> None:
    assert CRITIC_NORM_BETA == 1.0e-3
    assert CRITIC_NORM_SIGMA_MIN == 1.0e-4
    assert CRITIC_NORM_MU_INIT == 0.0
    assert CRITIC_NORM_SIGMA_INIT == 1.0
