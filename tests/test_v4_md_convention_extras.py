"""R478 extended convention tests — V5 build writes + distributed-residual
readback boundary (reviewer-C findings).

WSL-only: these construct real ANDES systems.
"""

from __future__ import annotations

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
    pytest.skip(
        "real ANDES is WSL-only; run extended M/D convention tests under WSL",
        allow_module_level=True,
    )

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v5 import AndesMultiVSGEnvV5  # noqa: E402
from andes_rl_kundur.env.andes.distributed_residual_env import (  # noqa: E402
    DistributedVectorResidualEnv,
)
from andes_rl_kundur.env.andes.md_convention import (  # noqa: E402
    device_to_system,
)
from andes_rl_kundur.env.andes.v5_config import V5Config  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_andes_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize(
    "config",
    [V5Config.v5_default(), V5Config.v4_plant_fallback()],
    ids=["regca1-w2-only", "gencls-fallback"],
)
def test_v5_heterogeneous_d_write_is_system_base(config: V5Config) -> None:
    """Both V5 build paths must leave the runtime D on the system base."""
    env = AndesMultiVSGEnvV5(
        random_disturbance=False,
        comm_fail_prob=0.0,
        config=config,
    )
    try:
        env.seed(42)
        env.reset(delta_u=SCENARIOS["load_step_1"])
        positions = env._vsg_pos
        d_runtime = np.asarray(
            [env.ss.GENCLS.D.v[p] for p in positions], dtype=float
        )
        expected = device_to_system(
            np.asarray(env.D0_HETEROGENEOUS, dtype=float),
            device_mva=env.VSG_SN,
        )
        np.testing.assert_allclose(d_runtime, expected, atol=1e-9, rtol=0)
    finally:
        env.close()


@pytest.mark.xfail(
    strict=False,
    reason=(
        "full regca1 (both plants) path is documented as practically "
        "unusable in this ANDES case; the L292 write is fixed and verified "
        "post-owner-approval"
    ),
)
def test_v5_full_regca1_path_heterogeneous_d_write() -> None:
    """The full-regca1 build path must also convert D0_HETEROGENEOUS."""
    from andes_rl_kundur.env.andes.v5_config import V5Config

    env = AndesMultiVSGEnvV5(
        config=V5Config.v5_regca1_both(),
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    try:
        env.seed(42)
        env.reset(delta_u=SCENARIOS["load_step_1"])
        positions = env._vsg_pos
        d_runtime = np.asarray(
            [env.ss.GENCLS.D.v[p] for p in positions], dtype=float
        )
        expected = device_to_system(
            np.asarray(env.D0_HETEROGENEOUS, dtype=float),
            device_mva=env.VSG_SN,
        )
        np.testing.assert_allclose(d_runtime, expected, atol=1e-9, rtol=0)
    finally:
        env.close()


def test_distributed_residual_readback_is_device_base() -> None:
    """The residual wrapper must return M/D in device-base model units."""
    base = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env = DistributedVectorResidualEnv(base_env=base)
    try:
        env.reset(delta_u=SCENARIOS["load_step_1"])
        actual_m, actual_d = env._read_actual_vsg_md()
        np.testing.assert_allclose(actual_m, base.M0, atol=1e-9, rtol=0)
        np.testing.assert_allclose(actual_d, base.D0, atol=1e-9, rtol=0)
    finally:
        base.close()
