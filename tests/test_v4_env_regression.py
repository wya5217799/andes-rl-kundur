"""V4 env behavioral regression test.

Locks the public-interface contract that ``AndesMultiVSGEnvV4`` produces
bit-identical no-control trajectories under the R478-corrected M/D base
convention (device-base controller math, system-base runtime arrays,
convert exactly once per boundary crossing).

The reference JSONs in
``results/research_loop/eval_v4_baseline_R478/`` were generated on the
corrected object. The older
``results/research_loop/eval_v4_baseline_PRE_REFACTOR/`` references lock
the pre-correction physics and stay untouched as historical evidence.
The R478 re-lock is the single deliberate behavioral change of that round.

Tolerance is tight (1e-9) because the env is deterministic given
fixed ``(seed, random_disturbance=False, comm_fail_prob=0)``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _real_andes_available() -> bool:
    try:
        import andes
    except ModuleNotFoundError:
        return False
    return callable(getattr(andes, "get_case", None))


if not _real_andes_available():
    pytest.skip("real ANDES is WSL-only; run V4 env tests under WSL", allow_module_level=True)

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

BASELINE_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline_R478"


@pytest.fixture(autouse=True)
def _isolate_andes_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep real-ANDES TDS outputs out of the repository root during replay."""
    monkeypatch.chdir(tmp_path)

# Match the no-control eval harness exactly
SEED = 42
STEPS = 150


def _run_no_control(scenario_name: str) -> dict:
    """Replay one no-control episode end-to-end."""
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(SEED)
    env.STEPS_PER_EPISODE = STEPS
    obs = env.reset(delta_u=SCENARIOS[scenario_name])

    N = env.N_AGENTS
    traces = []
    for step in range(STEPS):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(N)}
        obs, rewards, done, info = env.step(actions)
        if info.get("tds_failed"):
            break
        traces.append({
            "t":        float(info["time"]),
            "freq_hz":  info["freq_hz"].astype(float).tolist(),
            "M_es":     info["M_es"].astype(float).tolist(),
            "D_es":     info["D_es"].astype(float).tolist(),
        })
        if done:
            break
    env.close()
    return {"n_steps": len(traces), "traces": traces}


@pytest.mark.parametrize("scenario", ["load_step_1", "load_step_2"])
def test_first_step_freq_hz_matches_baseline(scenario: str) -> None:
    """The very first post-disturbance step must be bit-identical."""
    baseline_path = BASELINE_DIR / f"no_control_{scenario}.json"
    if not baseline_path.exists():
        pytest.skip(f"baseline JSON missing: {baseline_path}")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    expected = baseline["traces"][0]["freq_hz"]

    actual = _run_no_control(scenario)["traces"][0]["freq_hz"]

    np.testing.assert_allclose(
        actual, expected, atol=1e-9, rtol=0,
        err_msg=(
            f"V4 env initial-step freq_hz drifted from the R478-corrected "
            f"baseline for {scenario}. The corrected base convention must "
            f"stay bit-identical."
        ),
    )


def test_frequency_metadata_exposes_andes_60hz_without_changing_legacy_v4() -> None:
    """Live ANDES must report both the frozen 50-Hz and physical 60-Hz bases."""
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(SEED)
    env.STEPS_PER_EPISODE = 1
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        actions = {
            i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)
        }
        _obs, _rewards, _done, info = env.step(actions)
    finally:
        env.close()

    assert env.FN == 50.0
    assert env.andes_nominal_frequency_hz == 60.0
    assert info["frequency_calibration_mismatch"] is True
    np.testing.assert_allclose(info["freq_hz"], info["omega"] * 50.0)
    np.testing.assert_allclose(
        info["freq_hz_physical"], info["omega"] * 60.0
    )
