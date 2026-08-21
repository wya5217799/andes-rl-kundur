from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


slew = _load(
    "slew_aware_td3_interface",
    ROOT / "reference_fixes" / "slew_aware_td3_interface.py",
)
effort = _load(
    "componentwise_effort_cost",
    ROOT / "reference_fixes" / "componentwise_effort_cost.py",
)


def test_target_projection_enforces_bounds_and_slew() -> None:
    previous = np.array([[0.9, -0.9], [0.0, 0.0]], dtype=np.float32)
    target = np.array([[1.0, -1.0], [0.5, -0.5]], dtype=np.float32)
    executed = slew.project_target_np(previous, target, slew_limit=0.25)
    assert np.all(executed <= 1.0) and np.all(executed >= -1.0)
    assert np.all(np.abs(executed - previous) <= 0.25 + 1e-7)
    assert np.allclose(executed[0], [1.0, -1.0])
    assert np.allclose(executed[1], [0.25, -0.25])


def test_hidden_projector_state_is_exposed_by_augmentation() -> None:
    base = np.zeros((2, 7), dtype=np.float32)
    previous_a = np.array([[0.0, 0.0], [0.5, -0.5]], dtype=np.float32)
    augmented = slew.augment_actor_observation_np(base, previous_a)
    assert augmented.shape == (2, 9)
    assert np.array_equal(augmented[:, -2:], previous_a)

    target = np.zeros((2, 2), dtype=np.float32)
    executed = slew.project_target_np(previous_a, target)
    assert not np.array_equal(executed[0], executed[1])


def test_torch_action_map_has_gradient_inside_active_region() -> None:
    previous = torch.zeros((3, 2), dtype=torch.float32)
    target = torch.tensor(
        [[0.2, -0.2], [0.1, 0.2], [-0.15, 0.15]],
        dtype=torch.float32,
        requires_grad=True,
    )
    action = slew.project_target_torch(previous, target, slew_limit=0.25)
    action.sum().backward()
    assert torch.allclose(target.grad, torch.ones_like(target))


def test_componentwise_effort_detects_cancelling_actions() -> None:
    # Global mean is zero at every time, but componentwise effort is nonzero.
    actions = np.array(
        [
            [
                [[0.5, -0.5], [-0.5, 0.5], [0.5, -0.5], [-0.5, 0.5]],
                [[0.25, -0.25], [-0.25, 0.25], [0.25, -0.25], [-0.25, 0.25]],
            ]
        ],
        dtype=np.float64,
    )
    assert np.allclose(actions.mean(axis=2), 0.0)
    components = effort.effort_components_np(actions)
    assert float(components["mean_squared_magnitude"][0]) > 0.0
    assert float(components["total_variation"][0]) > 0.0
