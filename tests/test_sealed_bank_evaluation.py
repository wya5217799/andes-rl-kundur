"""Regression tests for prospective bank sealing and paired statistics."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    binomial_rate_summary,
    build_scenario_bank,
    canonical_json_bytes,
    classify_gate_replication,
    classify_smoothing_replication,
    empirical_upper_tail,
    load_scenario_bank,
    paired_binary_outcome_table,
    paired_bootstrap_contrasts,
    sha256_bytes,
    write_scenario_bank,
)


def _bank() -> dict:
    return build_scenario_bank(
        n=4,
        seed=20260724,
        repository_head="abc123",
        generator_source_sha256="f" * 64,
    )


def test_scenario_bank_is_deterministic_no_anchor_and_byte_sealed(tmp_path):
    first = _bank()
    second = _bank()
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert [row["name"] for row in first["scenarios"]] == [
        "random_00",
        "random_01",
        "random_02",
        "random_03",
    ]

    path = tmp_path / "bank.json"
    digest = write_scenario_bank(path, first)
    loaded, verified_digest = load_scenario_bank(path, expected_sha256=digest)

    assert loaded == first
    assert verified_digest == sha256_bytes(path.read_bytes())
    assert Path(f"{path}.sha256").read_text(encoding="ascii").startswith(digest)
    with pytest.raises(FileExistsError):
        write_scenario_bank(path, first)


def test_scenario_bank_rejects_tampering(tmp_path):
    path = tmp_path / "bank.json"
    digest = write_scenario_bank(path, _bank())
    path.write_bytes(path.read_bytes().replace(b"random_00", b"random_xx"))

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_scenario_bank(path, expected_sha256=digest)


def test_exact_failure_interval_and_tail_are_auditable():
    failure = binomial_rate_summary(0, 20)
    assert failure["rate"] == 0.0
    assert failure["exact_95_interval"][0] == 0.0
    assert failure["exact_95_interval"][1] == pytest.approx(0.168433, abs=1e-6)

    tail = empirical_upper_tail({"a": 1.0, "b": 4.0, "c": 3.0, "d": 2.0})
    assert tail["worst_1"] == {"scenario": "b", "value": 4.0}
    assert tail["worst_2"] == [
        {"scenario": "b", "value": 4.0},
        {"scenario": "c", "value": 3.0},
    ]
    assert tail["tail_count"] == 1
    assert tail["cvar_upper_tail"] == 4.0


def test_paired_bootstrap_uses_shared_scenarios_and_is_deterministic():
    controller_endpoints = {
        "left": {
            "metric_a": [0.9, 1.8, 2.7, 3.6],
            "metric_b": [9.0, 18.0, 27.0, 36.0],
        },
        "right": {
            "metric_a": [1.0, 2.0, 3.0, 4.0],
            "metric_b": [10.0, 20.0, 30.0, 40.0],
        },
    }
    kwargs = {
        "contrasts": [("left_minus_right", "left", "right")],
        "seed": 42,
        "n_resamples": 1000,
    }

    first = paired_bootstrap_contrasts(controller_endpoints, **kwargs)
    second = paired_bootstrap_contrasts(controller_endpoints, **kwargs)
    assert first == second
    assert first["shared_index_resampling"] is True
    for endpoint in ("metric_a", "metric_b"):
        effect = first["contrasts"]["left_minus_right"]["endpoints"][endpoint]
        assert effect["ratio_of_means_percent"]["point"] == pytest.approx(-10.0)
        assert effect["ratio_of_means_percent"]["percentile_95_interval"] == pytest.approx(
            [-10.0, -10.0]
        )
        assert effect["scenario_improvement_fraction"] == 1.0
        assert effect["scenario_improvement_count"] == 4
        assert len(effect["paired_absolute_differences"]) == 4


def test_paired_completion_table_keeps_discordant_failures():
    table = paired_binary_outcome_table(
        [True, True, False, False],
        [True, False, True, False],
    )
    assert table == {
        "both_success": 1,
        "left_only_success": 1,
        "right_only_success": 1,
        "both_failure": 1,
        "discordant_pairs": 2,
        "two_sided_exact_mcnemar_p": 1.0,
    }


def test_paired_bootstrap_keeps_absolute_effect_when_reference_is_zero():
    result = paired_bootstrap_contrasts(
        {
            "left": {"saturation": [0.0, 0.0, 0.0]},
            "right": {"saturation": [0.0, 0.0, 0.0]},
        },
        contrasts=[("left_minus_right", "left", "right")],
        seed=1,
        n_resamples=100,
    )
    effect = result["contrasts"]["left_minus_right"]["endpoints"]["saturation"]
    assert effect["absolute_mean_difference"]["point"] == 0.0
    assert effect["ratio_of_means_percent"]["point"] is None
    assert "unavailable_reason" in effect["ratio_of_means_percent"]


def test_replication_classifier_requires_both_co_primary_intervals():
    def controller(scale: float) -> dict:
        endpoint = {
            "cvar_upper_tail": scale,
            "maximum": scale,
        }
        return {
            "complete_count": 20,
            "failures": {"count": 0},
            "settling": {"count": 20},
            "endpoints": {
                "worst_bus_peak_abs_hz": dict(endpoint),
                "max_abs_rocof_hz_s": dict(endpoint),
                "action_total_variation": dict(endpoint),
            },
        }

    effect = {
        "ratio_of_means_percent": {
            "point": -2.0,
            "percentile_95_interval": [-3.0, -1.0],
        }
    }
    primary = {
        "endpoints": {
            "vsg_mean_iae_hz_s": effect,
            "normalized_sync_loss_hz2": effect,
        }
    }
    positive = classify_gate_replication(
        controller_summaries={
            "gate": controller(0.98),
            "static": controller(1.0),
        },
        primary_contrast=primary,
        gate_name="gate",
        static_name="static",
        total_scenarios=20,
    )
    assert positive["classification"] == "POSITIVE"

    primary["endpoints"]["normalized_sync_loss_hz2"] = {
        "ratio_of_means_percent": {
            "point": -1.0,
            "percentile_95_interval": [-3.0, 1.0],
        }
    }
    partial = classify_gate_replication(
        controller_summaries={
            "gate": controller(0.98),
            "static": controller(1.0),
        },
        primary_contrast=primary,
        gate_name="gate",
        static_name="static",
        total_scenarios=20,
    )
    assert partial["classification"] == "PARTIAL"


def test_smoothing_classifier_accepts_both_mean_directions_with_one_clear_interval():
    def controller(scale: float) -> dict:
        endpoint = {
            "cvar_upper_tail": scale,
            "maximum": scale,
        }
        return {
            "complete_count": 20,
            "failures": {"count": 0},
            "settling": {"count": 20},
            "endpoints": {
                "worst_bus_peak_abs_hz": dict(endpoint),
                "max_abs_rocof_hz_s": dict(endpoint),
                "action_total_variation": dict(endpoint),
            },
        }

    primary = {
        "endpoints": {
            "vsg_mean_iae_hz_s": {
                "ratio_of_means_percent": {
                    "point": -2.0,
                    "percentile_95_interval": [-3.0, -1.0],
                }
            },
            "normalized_sync_loss_hz2": {
                "ratio_of_means_percent": {
                    "point": -1.0,
                    "percentile_95_interval": [-3.0, 1.0],
                }
            },
        }
    }
    mechanism = {
        "endpoints": {
            "action_total_variation": {
                "ratio_of_means_percent": {
                    "point": -50.0,
                    "percentile_95_interval": [-60.0, -40.0],
                }
            }
        }
    }

    result = classify_smoothing_replication(
        controller_summaries={
            "smooth": controller(0.98),
            "static": controller(1.0),
        },
        primary_contrast=primary,
        mechanism_contrast=mechanism,
        smooth_name="smooth",
        static_name="static",
        total_scenarios=20,
    )

    assert result["classification"] == "POSITIVE"
    assert result["guards"]["smooth_action_tv_mean_below_raw"] is True


def test_smoothing_classifier_rejects_when_action_tv_does_not_fall_vs_raw():
    def controller(scale: float) -> dict:
        endpoint = {
            "cvar_upper_tail": scale,
            "maximum": scale,
        }
        return {
            "complete_count": 20,
            "failures": {"count": 0},
            "settling": {"count": 20},
            "endpoints": {
                "worst_bus_peak_abs_hz": dict(endpoint),
                "max_abs_rocof_hz_s": dict(endpoint),
                "action_total_variation": dict(endpoint),
            },
        }

    clear_effect = {
        "ratio_of_means_percent": {
            "point": -2.0,
            "percentile_95_interval": [-3.0, -1.0],
        }
    }
    result = classify_smoothing_replication(
        controller_summaries={
            "smooth": controller(0.98),
            "static": controller(1.0),
        },
        primary_contrast={
            "endpoints": {
                "vsg_mean_iae_hz_s": clear_effect,
                "normalized_sync_loss_hz2": clear_effect,
            }
        },
        mechanism_contrast={
            "endpoints": {
                "action_total_variation": {
                    "ratio_of_means_percent": {
                        "point": 1.0,
                        "percentile_95_interval": [-1.0, 3.0],
                    }
                }
            }
        },
        smooth_name="smooth",
        static_name="static",
        total_scenarios=20,
    )

    assert result["classification"] == "NEGATIVE"
    assert result["guards"]["smooth_action_tv_mean_below_raw"] is False
