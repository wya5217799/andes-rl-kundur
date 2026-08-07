"""Reject infeasible prospective profile banks before they are sealed."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any


class ProfileBankFeasibilityError(ValueError):
    """Report every record rejected by the authoritative contract builder."""

    def __init__(self, failures: tuple[dict[str, object], ...]) -> None:
        self.failures = failures
        super().__init__(f"{len(failures)} infeasible profile record(s)")


def _channel_device_idx(spec: Mapping[str, object]) -> str | None:
    channel = spec.get("channel")
    if not isinstance(channel, Mapping):
        return None
    device_idx = channel.get("device_idx")
    return None if device_idx is None else str(device_idx)


def require_profile_bank_feasible(
    record_specs: Iterable[Mapping[str, object]],
    build_contract: Callable[[Mapping[str, object]], Any],
) -> None:
    """Build every profile with the production contract and reject as a bank."""

    failures: list[dict[str, object]] = []
    for raw_spec in record_specs:
        spec = dict(raw_spec)
        try:
            build_contract(spec)
        except ValueError as error:
            failures.append(
                {
                    "record_index": int(spec["record_index"]),
                    "point": str(spec["point"]),
                    "channel_device_idx": _channel_device_idx(spec),
                    "waveform": str(spec["waveform"]),
                    "amplitude_system_pu": float(spec["amplitude_system_pu"]),
                    "sign": str(spec["sign"]),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

    if failures:
        raise ProfileBankFeasibilityError(tuple(failures))
