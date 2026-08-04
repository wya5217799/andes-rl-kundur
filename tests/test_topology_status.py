from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from andes_rl_kundur.evaluation.topology_status import (
    apply_line_outage,
    eig_validity_guard,
)


class SetterOnlyLine:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def test_line_outage_uses_the_model_setter_boundary() -> None:
    system = SimpleNamespace(Line=SetterOnlyLine())

    apply_line_outage(system, "Line_2")

    assert system.Line.calls == [
        (("u", "Line_2", 0.0), {"attr": "v"}),
    ]


def _system(*, test_ok: bool, exit_code: int, f: list[float], mu: list[complex]):
    return SimpleNamespace(
        TDS=SimpleNamespace(test_ok=test_ok, config=SimpleNamespace(tol=1e-4)),
        EIG=SimpleNamespace(mu=np.asarray(mu)),
        dae=SimpleNamespace(f=np.asarray(f), g=np.asarray([1e-9])),
        exit_code=exit_code,
    )


def test_eig_validity_guard_requires_initialization_residual_and_spectrum() -> None:
    valid = eig_validity_guard(
        _system(test_ok=True, exit_code=0, f=[1e-8], mu=[-0.1 + 1j])
    )
    invalid_init = eig_validity_guard(
        _system(test_ok=False, exit_code=1, f=[0.02], mu=[-0.1 + 1j])
    )
    invalid_spectrum = eig_validity_guard(
        _system(test_ok=True, exit_code=0, f=[1e-8], mu=[0.04 + 1j])
    )

    assert valid["passed"] is True
    assert invalid_init["passed"] is False
    assert invalid_init["initialization_pass"] is False
    assert invalid_spectrum["passed"] is False
    assert invalid_spectrum["positive_real_count"] == 1
