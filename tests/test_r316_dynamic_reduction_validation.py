import numpy as np
import pytest

from probes.r316_dynamic_reduction_validation import (
    normalize_achieved_power_residue,
)


def test_guard_normalization_accepts_only_small_zero_request_solver_residue() -> None:
    requested = np.array([0.0, 0.02, 0.0, -0.02])
    achieved = np.array([3.5e-7, 0.0195, -9.0e-7, -0.0195])

    normalized = normalize_achieved_power_residue(
        requested,
        achieved,
        zero_request_tolerance=1e-6,
    )

    np.testing.assert_allclose(normalized, [0.0, 0.0195, 0.0, -0.0195])

    with pytest.raises(ValueError, match="zero-request achieved-power residue"):
        normalize_achieved_power_residue(
            requested,
            np.array([2e-6, 0.0195, 0.0, -0.0195]),
            zero_request_tolerance=1e-6,
        )
