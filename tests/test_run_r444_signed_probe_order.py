"""Directed tests for the R444 signed-probe order ladder runner and probe.

Windows-safe: only pure protocol math, shard-id parsing, geometric scaling,
order-fit math, and rung selection are exercised here.  The WSL-only
lifecycle (measure-capacity / rehearse / prepare / shard / classify) runs
through the scratch launcher in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts", ROOT / "probes"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r444_signed_probe_order as runner  # noqa: E402
import probes.r444_signed_probe_order as order  # noqa: E402
from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract  # noqa: E402


def _frozen() -> dict:
    return build_contract()


def _trajectory(scale: float, *, cubic: bool = False, even: bool = False, sign: float = 1.0) -> np.ndarray:
    """Deterministic 4 x 30 trajectory whose L2 norm scales as eps^p.

    ``even=True`` gives a sign-independent quadratic response; otherwise the
    response is odd in the probe sign (sign * eps^p), which is what the C.7
    delta_odd decomposition needs.  A small sinusoid is added and cancels in
    the odd part (identical on both probe signs).
    """
    time = np.arange(30, dtype=float)
    if even:
        base = np.ones((4, 30)) * scale**2
        base[1] *= 0.5
        return base + 0.1 * np.sin(time)[None, :]
    if cubic:
        base = np.ones((4, 30)) * sign * scale**3
        base[2] *= 0.7
        return base + 0.1 * np.cos(time)[None, :]
    base = np.ones((4, 30)) * sign * scale**2
    base[3] *= 0.3
    return base + 0.1 * np.sin(time)[None, :]


def _record(
    scenario_id: str,
    scale: float,
    *,
    cubic: bool = False,
    even: bool = False,
    sign: float = 1.0,
    completed: bool = True,
    tds_failed: bool = False,
) -> dict:
    frequencies = _trajectory(scale, cubic=cubic, even=even, sign=sign) + 60.0
    steps = [
        {
            "step_index": index,
            "time": float(index) * 0.2,
            "action_norm": [[0.0, 0.0]] * 4,
            "freq_hz_physical": frequencies[:, index].tolist(),
            "M_es": [150.0, 250.0, 170.0, 230.0],
            "D_es": [60.0, 140.0, 80.0, 120.0],
            "delta_M": [0.0, 0.0, 0.0, 0.0],
            "delta_D": [0.0, 0.0, 0.0, 0.0],
            "tds_failed": False,
            "done": index == 29,
        }
        for index in range(30)
    ]
    return {
        "scenario_id": scenario_id,
        "steps": steps,
        "completed": completed,
        "tds_failed": tds_failed,
    }


# ── runner protocol math ──────────────────────────────────────────────

def test_scale_key_and_shard_roundtrip() -> None:
    for k in range(runner.SCALE_COUNT):
        assert runner.scale_key(k) == f"k{k}"
        sid = runner.shard_id("law", k)
        controller, parsed = runner.parse_shard_id(sid)
        assert controller == "law"
        assert parsed == k
    controller, parsed = runner.parse_shard_id("zero|k3")
    assert (controller, parsed) == ("zero", 3)
    with pytest.raises(ValueError):
        runner.parse_shard_id("bad|k0")
    with pytest.raises(ValueError):
        runner.parse_shard_id("law|x1")


def test_shard_list_expansion() -> None:
    shards = runner.shard_list()
    assert len(shards) == 12
    assert len(set(shards)) == 12
    for sid in shards:
        controller, k = runner.parse_shard_id(sid)
        assert controller in ("law", "zero")
        assert 0 <= k < runner.SCALE_COUNT


def test_scaled_profiles_geometric() -> None:
    contract = _frozen()
    frozen_eval = {
        row["profile_id"]: row
        for row in contract["profiles"]
        if row["split"] == "evaluation"
    }
    for k in range(runner.SCALE_COUNT):
        factor = 2.0 ** (-float(k))
        scaled = runner.scaled_profiles(k)
        assert len(scaled) == 4
        for profile in scaled:
            source = frozen_eval[profile["profile_id"]]
            assert profile["probe_magnitude"] == pytest.approx(
                factor * source["probe_magnitude"]
            )
            assert profile["localized_magnitude"] == pytest.approx(
                factor * source["localized_magnitude"]
            )
            assert profile["amplitude_k"] == k
            assert len(profile["scenarios"]) == 6
            by_kind = {
                scenario["pair_kind"]: scenario
                for scenario in profile["scenarios"]
            }
            assert by_kind["common"]["magnitude"] == pytest.approx(
                profile["probe_magnitude"]
            )
            assert by_kind["differential"]["magnitude"] == pytest.approx(
                profile["probe_magnitude"]
            )
            assert by_kind["localized"]["magnitude"] == pytest.approx(
                profile["localized_magnitude"]
            )
            positive = next(
                s for s in profile["scenarios"] if s["sign"] == "positive"
            )
            negative = next(
                s for s in profile["scenarios"] if s["sign"] == "negative"
            )
            for key in positive["delta_u"]:
                assert positive["delta_u"][key] == pytest.approx(
                    -negative["delta_u"][key]
                )


def test_rung_selection_marginal_rule() -> None:
    throughput = {1: 0.10, 2: 0.19, 4: 0.36}
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22 * 2**30
    )
    assert selection["readiness"] == "RUN-READY"
    assert selection["selected_workers"] == 4
    assert selection["host_process_budget"] == 5
    assert selection["wsl_python_processes"] == 5


def test_rung_selection_memory_guard() -> None:
    throughput = {1: 0.10, 2: 0.19, 4: 0.36}
    # even 1 worker projected RSS (944MB) exceeds half of 1 GiB available
    selection = runner._select_rung(
        throughput, wsl_available_bytes=1 * 2**30
    )
    assert selection["readiness"] == "HOLD"


# ── order-fit math (C.7) ──────────────────────────────────────────────

def _build_pair_blocks(magnitudes: list[float], *, cubic: bool = False) -> tuple[list[dict], list[dict]]:
    """Per-scale law/zero record maps for one profile-pair block."""
    law_by_scale: list[dict] = []
    zero_by_scale: list[dict] = []
    for magnitude in magnitudes:
        law_by_scale.append(
            {
                "p_common_positive": _record(
                    "p_common_positive", magnitude, cubic=cubic, sign=1.0
                ),
                "p_common_negative": _record(
                    "p_common_negative", magnitude, cubic=cubic, sign=-1.0
                ),
            }
        )
        zero_by_scale.append(
            {
                "p_common_positive": _record(
                    "p_common_positive", magnitude, even=True
                ),
                "p_common_negative": _record(
                    "p_common_negative", magnitude, even=True
                ),
            }
        )
    return law_by_scale, zero_by_scale


def test_pair_odd_norm_quadratic() -> None:
    """Odd law response (sign * eps^2) vs even zero response => odd ~ eps^2."""
    scale = 1.0
    law_positive = _record("p_common_positive", scale, sign=1.0)
    law_negative = _record("p_common_negative", scale, sign=-1.0)
    zero_positive = _record("p_common_positive", scale, even=True)
    zero_negative = _record("p_common_negative", scale, even=True)
    odd_norm, even_norm, odd, even = order.pair_odd_norm(
        law_positive, law_negative, zero_positive, zero_negative, dt=0.2
    )
    assert odd_norm > 0.0
    assert odd.shape == (4, 30)
    assert even.shape == (4, 30)
    # even response identical on both controllers cancels in odd part
    assert even_norm > 0.0


def test_classify_quadratic_band() -> None:
    """Synthetic odd-quadratic law response must classify QUADRATIC."""
    magnitudes = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]
    law_by_scale, zero_by_scale = _build_pair_blocks(magnitudes)
    block = order.classify_block(
        law_by_scale,
        zero_by_scale,
        profile_id="p",
        pair_kind="common",
        magnitudes=magnitudes,
        dt=0.2,
    )
    assert block["usable_count"] == 6
    assert block["classification"] == "QUADRATIC"
    assert block["loglog"]["p_hat"] == pytest.approx(2.0, abs=0.2)


def test_classify_cubic_band() -> None:
    magnitudes = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]
    law_by_scale, zero_by_scale = _build_pair_blocks(magnitudes, cubic=True)
    block = order.classify_block(
        law_by_scale,
        zero_by_scale,
        profile_id="p",
        pair_kind="common",
        magnitudes=magnitudes,
        dt=0.2,
    )
    assert block["usable_count"] == 6
    assert block["classification"] == "CUBIC"
    assert block["loglog"]["p_hat"] == pytest.approx(3.0, abs=0.2)


def test_classify_noise_floor_inconclusive() -> None:
    """Fewer than MIN_USABLE_SCALES usable => INCONCLUSIVE."""
    magnitudes = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]
    law_by_scale, zero_by_scale = _build_pair_blocks(magnitudes)
    # last two law scales collapse to the numerical floor
    for k in (4, 5):
        law_by_scale[k] = {
            "p_common_positive": _record(
                "p_common_positive", 1.0e-15, sign=1.0
            ),
            "p_common_negative": _record(
                "p_common_negative", 1.0e-15, sign=-1.0
            ),
        }
    block = order.classify_block(
        law_by_scale,
        zero_by_scale,
        profile_id="p",
        pair_kind="common",
        magnitudes=magnitudes,
        dt=0.2,
    )
    assert block["classification"] == "INCONCLUSIVE"
    assert block["usable_count"] < order.MIN_USABLE_SCALES


def test_classify_mode_inconsistent_inconclusive() -> None:
    magnitudes = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]
    law_by_scale, zero_by_scale = _build_pair_blocks(magnitudes)
    # perturb the largest-scale law record to a different saturation signature
    steps = law_by_scale[0]["p_common_positive"]["steps"]
    steps[0]["action_norm"] = [[1.0, 1.0]] * 4
    block = order.classify_block(
        law_by_scale,
        zero_by_scale,
        profile_id="p",
        pair_kind="common",
        magnitudes=magnitudes,
        dt=0.2,
    )
    assert block["classification"] == "INCONCLUSIVE"
    assert block["mode_consistency"]["overall"] is False


def test_summarize_consistent() -> None:
    blocks = [
        {"classification": "QUADRATIC"},
        {"classification": "QUADRATIC"},
        {"classification": "QUADRATIC"},
    ]
    summary = order.summarize(blocks)
    assert summary["manuscript_branch"] == "QUADRATIC-CONSISTENT"
    summary = order.summarize(
        [
            {"classification": "QUADRATIC"},
            {"classification": "CUBIC"},
            {"classification": "INCONCLUSIVE"},
        ]
    )
    # two of three blocks carry a decided order: majority, not dominant-inconclusive
    assert summary["manuscript_branch"] == "QUADRATIC-MAJORITY"
    summary = order.summarize(
        [
            {"classification": "INCONCLUSIVE"},
            {"classification": "INCONCLUSIVE"},
            {"classification": "QUADRATIC"},
        ]
    )
    assert summary["manuscript_branch"] == "INCONCLUSIVE-DOMINANT"
