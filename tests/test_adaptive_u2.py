"""Focused integration tests for the adaptive U2 training seam."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from andes_rl_kundur.training import adaptive_u2
from andes_rl_kundur.training.adaptive_stop import AdaptiveStopConfig
from andes_rl_kundur.training.adaptive_u2 import train_cell


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sidecar(path: Path) -> str:
    digest = _sha(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


class _FakeEnv:
    def reset(self, *, delta_u: dict[str, float]) -> np.ndarray:
        del delta_u
        return np.zeros((4, 7), dtype=np.float32)

    def step(
        self, actions: dict[int, np.ndarray]
    ) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        del actions
        return (
            np.zeros((4, 7), dtype=np.float32),
            0.0,
            False,
            {
                "tds_failed": False,
                "delta_M": np.zeros(4),
                "delta_D": np.zeros(4),
            },
        )

    def close(self) -> None:
        return None


class _FakeWrapper:
    def __init__(self, arm_id: str, core: Any) -> None:
        self.arm_id = arm_id
        self.core = core

    def import_states(self, states: list[dict[str, Any]]) -> None:
        assert len(states) == 4

    def act(
        self,
        actor_rows: np.ndarray,
        previous: np.ndarray,
        *,
        deterministic: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        del actor_rows, deterministic
        values = np.zeros_like(previous)
        return values, values

    def store(self, *args: Any) -> None:
        del args

    def update_all(self) -> dict[str, float]:
        return {
            "critic_loss": 1.0,
            "actor_loss": 1.0,
            "alpha_loss": 0.0,
            "alpha": 0.005,
            "actor_grad_norm": 0.1,
        }

    def save(self, path: Path, *, stage: str, base_sha256: str) -> str:
        path.write_text(f"{stage}:{base_sha256}", encoding="utf-8")
        return _sidecar(path)


class _FakeTorch:
    @staticmethod
    def load(path: str, **kwargs: Any) -> dict[str, Any]:
        del path, kwargs
        return {
            "kind": "r470-common-base-state",
            "training_seed": 7,
            "agents": [{}, {}, {}, {}],
        }


def _runtime(tmp_path: Path) -> tuple[Any, Path, Path]:
    root = tmp_path
    source = root / "source"
    donor = source / "donors/seed7"
    donor.mkdir(parents=True)
    base = donor / "base.pt"
    base.write_bytes(b"base")
    base_sha = _sha(base)
    manifest = donor / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "round": "R482",
                "training_seed": 7,
                "base_state_path": str(base),
                "base_state_sha256": base_sha,
                "reward_function_sha256": "reward-sha",
            }
        ),
        encoding="utf-8",
    )
    _sidecar(manifest)

    probe = root / "probe.npz"
    np.savez_compressed(
        probe,
        joint_observations=np.zeros((2, 4, 7), dtype=np.float32),
        previous_actions=np.zeros((2, 4, 2), dtype=np.float32),
    )
    _sidecar(probe)

    def write_json(path: Path, payload: dict[str, Any]) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return _sidecar(path)

    def write_npz(path: Path, **arrays: Any) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **arrays)
        return _sidecar(path)

    core = SimpleNamespace()
    core.ROOT = root
    core.torch = _FakeTorch
    core._assert_wsl_scratch = lambda: None
    core._seed_all = lambda seed: None
    core._read_hashed_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
    core._write_new_json = write_json
    core._write_new_npz = write_npz
    core._curve_stability = lambda values: {"valid": bool(len(values)), "stable": True}
    core.contract_sha256 = lambda: "contract-sha"
    core._relative = lambda path: str(path)
    core.torch = _FakeTorch
    core.r431 = SimpleNamespace(
        _build_env=lambda profile: _FakeEnv(),
        _joint_obs=lambda observation: observation,
    )
    core.legacy = SimpleNamespace(step_rewards=lambda *args, **kwargs: np.zeros(4, dtype=float))
    core.FactorialWrapper = lambda arm: _FakeWrapper(arm, core)
    level2 = SimpleNamespace(source_rows=lambda joint, source_name: joint)
    level3 = SimpleNamespace(core=core)
    level2.base = level3
    level1 = SimpleNamespace(base=level2)
    runtime = SimpleNamespace(
        base=level1,
        PHASE3B_ARM="an_cn_r1_rms",
        arm_factors=lambda arm: {
            "actor_source": "N",
            "critic_source": "N",
            "reward_access": True,
        },
        build_contract=lambda: {
            "steps": 5,
            "profiles": [
                {
                    "profile_id": "dev",
                    "split": "development",
                    "scenarios": [{"scenario_id": "s", "delta_u": {}}],
                }
            ],
            "training_contract": {"development_scenario_order": ["s"]},
        },
        _r482_penalized_step_rewards=lambda *args: np.zeros(4),
        _penalized_reward_sha=lambda: "penalty-sha",
    )
    return runtime, source, probe


def test_train_cell_stops_after_confirmed_action_and_curve_stability(tmp_path: Path) -> None:
    runtime, source, probe = _runtime(tmp_path)
    config = AdaptiveStopConfig(
        min_steps=30,
        max_steps=40,
        check_interval=5,
        window_updates=10,
        required_checks=2,
    )
    out = tmp_path / "out"
    orphan = out / "recovery_attempts/an_cn_r1/seed7/orphaned_attempt/half.pt"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("preserved partial", encoding="utf-8")
    digest = train_cell(
        runtime,
        round_id="R999",
        out=out,
        source_out=source,
        arm_id="an_cn_r1",
        seed=7,
        stop_config=config,
        probe_path=probe,
        probe_sha256=_sha(probe),
        source_round="R482",
        source_manifest_sha256=_sha(source / "donors/seed7/manifest.json"),
        source_base_sha256=_sha(source / "donors/seed7/base.pt"),
    )
    folder = out / "train/an_cn_r1/seed7"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    trace = json.loads((folder / "adaptive_trace.json").read_text(encoding="utf-8"))
    assert digest == _sha(folder / "manifest.json")
    assert manifest["interaction_steps"] == 35
    assert manifest["stop_reason"] == "converged"
    assert manifest["converged"] is True
    assert manifest["valid"] is True
    assert (folder / "half.pt").exists()
    assert orphan.read_text(encoding="utf-8") == "preserved partial"
    assert len(trace["checks"]) == 2
    assert trace["checks"][-1]["consecutive_passes"] == 2


def test_cumulative_probe_drift_prevents_false_early_stop(tmp_path: Path, monkeypatch: Any) -> None:
    runtime, source, probe = _runtime(tmp_path)
    values = iter((0.0, 0.019, 0.038, 0.057))

    def drifting_outputs(*args: Any, **kwargs: Any) -> np.ndarray:
        del args, kwargs
        return np.full((2, 4, 2), next(values), dtype=np.float32)

    monkeypatch.setattr(adaptive_u2, "action_probe_outputs", drifting_outputs)
    config = AdaptiveStopConfig(
        min_steps=30,
        max_steps=40,
        check_interval=5,
        window_updates=10,
        required_checks=2,
    )
    out = tmp_path / "out"
    train_cell(
        runtime,
        round_id="R999",
        out=out,
        source_out=source,
        arm_id="an_cn_r1",
        seed=7,
        stop_config=config,
        probe_path=probe,
        probe_sha256=_sha(probe),
        source_round="R482",
        source_manifest_sha256=_sha(source / "donors/seed7/manifest.json"),
        source_base_sha256=_sha(source / "donors/seed7/base.pt"),
    )
    folder = out / "train/an_cn_r1/seed7"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    trace = json.loads((folder / "adaptive_trace.json").read_text(encoding="utf-8"))
    assert manifest["interaction_steps"] == 40
    assert manifest["stop_reason"] == "max_steps"
    assert manifest["converged"] is False
    assert trace["checks"][1]["action_probe_adjacent_drift"] < 0.02
    assert trace["checks"][1]["action_probe_cumulative_drift"] > 0.02


def test_probe_bank_samples_full_trajectory_and_previous_action_contexts(
    tmp_path: Path,
) -> None:
    runtime, _source, _probe = _runtime(tmp_path)
    runtime.base.base.base.core.r431._joint_obs = lambda observation: observation.reshape(-1)
    path = tmp_path / "trajectory_probe.npz"
    adaptive_u2.create_probe_bank(runtime, path)
    with np.load(path, allow_pickle=False) as payload:
        assert payload["joint_observations"].shape == (10, 4, 7)
        assert sorted(set(payload["time_indices"].tolist())) == [0, 1, 2, 3, 4]
        assert set(payload["previous_action_contexts"].tolist()) == {
            "zero",
            "alternating",
        }


def test_action_probe_drift_does_not_average_away_one_unstable_state() -> None:
    previous = np.zeros((100, 4, 2), dtype=np.float32)
    current = previous.copy()
    current[37] = 0.1
    assert adaptive_u2.action_probe_drift(previous, current) > 0.09


def test_sealed_source_manifest_hash_rejects_self_consistent_substitution(
    tmp_path: Path,
) -> None:
    runtime, source, probe = _runtime(tmp_path)
    manifest = source / "donors/seed7/manifest.json"
    expected_manifest_sha = _sha(manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["substituted"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    _sidecar(manifest)
    try:
        train_cell(
            runtime,
            round_id="R999",
            out=tmp_path / "out",
            source_out=source,
            arm_id="an_cn_r1",
            seed=7,
            stop_config=AdaptiveStopConfig(
                min_steps=30,
                max_steps=40,
                check_interval=5,
                window_updates=10,
                required_checks=2,
            ),
            probe_path=probe,
            probe_sha256=_sha(probe),
            source_round="R482",
            source_manifest_sha256=expected_manifest_sha,
            source_base_sha256=_sha(source / "donors/seed7/base.pt"),
        )
    except RuntimeError as exc:
        assert "differs from formal seal" in str(exc)
    else:
        raise AssertionError("sealed source substitution should fail closed")
    assert not (tmp_path / "out/train/an_cn_r1/seed7").exists()
