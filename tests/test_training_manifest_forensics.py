"""Tests for retained learner-manifest failure classification."""

from __future__ import annotations

from probes.training_manifest_forensics import analyse_manifests


def test_nan_actor_sentinel_with_finite_critic_is_runner_invalid() -> None:
    manifests = [
        {
            "arm_id": arm,
            "interaction_steps": 256,
            "invalid_reason": "nonfinite learner diagnostic",
            "tds_failed_episodes": 0,
            "final_checkpoint_sha256": None,
            "update_diagnostics": [
                {
                    "critic_loss": 0.03,
                    "actor_loss_mean": float("nan"),
                    "lagrange": 1.0,
                }
            ],
        }
        for arm in ("no_message", "message")
    ]

    result = analyse_manifests(manifests)

    assert result["classification"] == "SCRATCH-INVALID"
    assert result["cause"] == "diagnostic-sentinel-misclassified"
    assert result["retry_authorized"] is False
    assert result["algorithm_efficacy_tested"] is False
