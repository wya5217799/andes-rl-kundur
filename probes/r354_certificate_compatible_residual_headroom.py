"""Certificate-compatible adapter for the otherwise unchanged R353 analysis.

The R354 execution adapter installs :func:`certificate_serialization_scope`
around each inherited operation.  :func:`solve_oracle_case` exposes the same
seam for regression tests.  Both paths temporarily replace only the frozen
parent's certificate-to-JSON function and always restore it.  Unsupported
certificate schemas fail before sealing; solver, projection, estimator,
endpoint, or decision failures are delegated unchanged to R353.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from probes import r353_matched_residual_headroom as parent

from andes_rl_kundur.control.minimum_norm_certificate import MinimumNormCertificate


def certificate_payload(certificate: MinimumNormCertificate) -> dict[str, Any]:
    """Serialize the public fields of the current minimum-norm certificate."""

    return {
        "valid": bool(certificate.valid),
        "feasible": bool(certificate.feasible),
        "reason": str(certificate.reason),
        "active_constraint_count": int(certificate.active_constraint_count),
        "maximum_constraint_violation": float(certificate.maximum_constraint_violation),
        "stationarity_residual": float(certificate.stationarity_residual),
        "complementarity_residual": float(certificate.complementarity_residual),
        "optimality_tolerance": float(certificate.optimality_tolerance),
        "multipliers": certificate.multipliers.tolist(),
    }


@contextmanager
def certificate_serialization_scope() -> Iterator[None]:
    """Install the R354 serializer only while one inherited operation runs."""

    previous = parent._certificate_payload
    parent._certificate_payload = certificate_payload
    try:
        yield
    finally:
        parent._certificate_payload = previous


def solve_oracle_case(
    case: Mapping[str, Any],
    *,
    minimum_improvement_fraction: float,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> dict[str, Any]:
    """Run the unchanged R353 oracle with only certificate serialization repaired."""

    with certificate_serialization_scope():
        return parent.solve_oracle_case(
            case,
            minimum_improvement_fraction=minimum_improvement_fraction,
            maximum_iterations=maximum_iterations,
            function_tolerance=function_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )
