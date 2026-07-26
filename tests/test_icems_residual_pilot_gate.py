from __future__ import annotations

from andes_rl_kundur.evaluation.icems_residual import classify_icems_pilot


def _contrast(
    *,
    sync: tuple[float, float] = (-3.0, -0.5),
    inter: tuple[float, float] = (-2.5, -0.1),
    rocof: tuple[float, float] = (1.0, 2.0),
    peak: tuple[float, float] = (2.0, 3.0),
    iae: tuple[float, float] = (1.0, 2.0),
    final: tuple[float, float] = (1.5, 3.0),
) -> dict:
    rows = {
        "normalized_sync_loss_hz2": sync,
        "fast_inter_area_iae_hz_s": inter,
        "max_abs_rocof_hz_s": rocof,
        "worst_bus_peak_abs_hz": peak,
        "vsg_mean_iae_hz_s": iae,
        "final_window_common_abs_mean_hz": final,
    }
    return {
        "endpoints": {
            name: {
                "ratio_of_means_percent": {
                    "point": values[0],
                    "percentile_95_interval": [-5.0, values[1]],
                }
            }
            for name, values in rows.items()
        }
    }


def _classify(contrast: dict | None, **overrides: bool) -> dict:
    flags = {
        "provenance_valid": True,
        "complete_pairs": True,
        "action_guard_pass": True,
        "storage_guard_pass": True,
        "tail_guard_pass": True,
    }
    flags.update(overrides)
    return classify_icems_pilot(primary_contrast=contrast, **flags)


def test_pilot_gate_requires_both_material_primary_improvements() -> None:
    assert _classify(_contrast())["classification"] == "PILOT-GO"
    decision = _classify(_contrast(inter=(-1.9, -0.1)))
    assert decision["classification"] == "PILOT-NO-GO"
    assert not decision["guards"]["both_primary_endpoints_clear"]


def test_pilot_gate_rejects_uncertain_primary_and_no_harm_failure() -> None:
    assert (
        _classify(_contrast(sync=(-3.0, 0.01)))["classification"]
        == "PILOT-NO-GO"
    )
    decision = _classify(_contrast(rocof=(5.01, 6.0)))
    assert decision["classification"] == "PILOT-NO-GO"
    assert not decision["guards"]["fast_mean_guard_pass"]


def test_pilot_gate_marks_missing_or_invalid_evidence_invalid() -> None:
    assert _classify(None)["classification"] == "INVALID"
    assert (
        _classify(_contrast(), action_guard_pass=False)["classification"]
        == "INVALID"
    )
