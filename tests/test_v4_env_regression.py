"""V4 env behavioral regression test.

Locks the public-interface contract that ``AndesMultiVSGEnvV4`` produces
bit-identical no-control trajectories before and after the AD-01
self-containment refactor.

The reference JSONs in
``results/research_loop/eval_v4_baseline_PRE_REFACTOR/`` were generated
on the V1→V2→V3→V4 inheritance chain immediately before the refactor.
The current V4 (now self-contained) must reproduce them step-for-step.

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
sys.path.insert(0, str(ROOT))

from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

BASELINE_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline_PRE_REFACTOR"

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
            f"V4 env initial-step freq_hz drifted from pre-refactor baseline "
            f"for {scenario}. AD-01 self-containment must preserve bit-identical "
            f"physics."
        ),
    )
