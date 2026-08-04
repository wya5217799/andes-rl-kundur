"""R336 successor for the unchanged four-channel disturbance package.

R335 stopped before formal-attempt reservation because its adapter expected a
case member from the R333 verifier.  This thin adapter preserves the sealed
scientific implementation and replaces only that pre-execution verifier with
the already audited R334 official-case wrapper.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (_BOOTSTRAP_ROOT, _BOOTSTRAP_ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from scripts import run_r334_pq_disturbance_identification as _r334  # noqa: E402
from scripts import run_r335_disturbance_package as _base  # noqa: E402

ROUND_ID = "R336"
QUESTION_ID = "Q-0086"
ROOT = _base.ROOT
DEFAULT_SEAL = ROOT / "memory/rounds/R336/disturbance_package_seal.json"
DEFAULT_OUT = ROOT / "results/r336_disturbance_package"

_original_source_paths = _base._source_paths


def _source_paths() -> dict[str, Path]:
    paths = _original_source_paths()
    paths.update(
        {
            "r336_adapter": Path(__file__).resolve(),
            "r336_adapter_tests": ROOT
            / "tests/test_r336_disturbance_package_repair.py",
            "r334_adapter": ROOT
            / "scripts/run_r334_pq_disturbance_identification.py",
        }
    )
    return paths


def _parent_paths() -> dict[str, Path]:
    return {
        "r316_model": _base.R316_MODEL,
        "r316_analysis": ROOT / "results/r316_dynamic_reduction/analysis.json",
        "r329_seal": ROOT / "memory/rounds/R329/disturbance_estimator_seal.json",
        "r329_analysis": ROOT / "results/r329_disturbance_estimator/analysis.json",
        "r334_seal": ROOT
        / "memory/rounds/R334/pq_disturbance_identification_seal.json",
        "r334_analysis": ROOT
        / "results/r334_pq_disturbance_identification/analysis.json",
        "r334_claim": ROOT / "memory/claims/CLM-0880.md",
        "r335_seal": ROOT / "memory/rounds/R335/disturbance_package_seal.json",
        "r335_failure": ROOT / "memory/rounds/R335/pre_execution_failure.md",
        "r336_plan": ROOT / "memory/rounds/R336/plan.md",
        "q0086": ROOT / "memory/questions/Q-0086.md",
    }


def _profile_contract(
    *, channel: dict[str, object] | None, shape: str, sign: str
) -> _base.TimedPQProfileContract:
    if channel is None:
        target = _base.CHANNELS[-1]
        profile = (0.0,)
        prefix = "R336_zero"
    else:
        target = channel
        multiplier = 1.0 if sign == "positive" else -1.0
        profile = tuple(multiplier * value for value in _base.SHAPES[shape])
        prefix = f"R336_{target['device_idx']}_{shape}_{sign}"
    return _base.TimedPQProfileContract(
        event_prefix=prefix,
        device_idx=str(target["device_idx"]),
        bus_idx=int(target["bus_idx"]),
        initial_active_system_pu=float(target["initial_active_system_pu"]),
        initial_reactive_system_pu=float(target["initial_reactive_system_pu"]),
        delta_profile_system_pu=profile,
        plant_baselines=_base.BASELINES,
    )


def _verify_installed_andes(seal: dict[str, Any]) -> dict[str, object]:
    installed = _r334._verify_installed_andes()
    expected = seal["expected_runtime"]
    if installed["version"] != expected["andes_version"]:
        raise RuntimeError("installed ANDES version drift")
    if installed["sources"] != expected["installed_sources"]:
        raise RuntimeError("installed ANDES source drift")
    if installed["case"]["sha256"] != expected["case_sha256"]:
        raise RuntimeError("installed Kundur case drift")
    return installed


@contextmanager
def _configured_base():
    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "DEFAULT_SEAL": DEFAULT_SEAL,
        "DEFAULT_OUT": DEFAULT_OUT,
        "_source_paths": _source_paths,
        "_parent_paths": _parent_paths,
        "_profile_contract": _profile_contract,
        "_verify_installed_andes": _verify_installed_andes,
    }
    previous = {name: getattr(_base, name) for name in replacements}
    for name, value in replacements.items():
        setattr(_base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(_base, name, value)


def build_contract() -> dict[str, object]:
    with _configured_base():
        return _base.build_contract()


def prepare(*args, **kwargs):
    with _configured_base():
        return _base.prepare(*args, **kwargs)


def execute(*args, **kwargs):
    with _configured_base():
        return _base.execute(*args, **kwargs)


def analyse(*args, **kwargs):
    with _configured_base():
        return _base.analyse(*args, **kwargs)


def build_parser():
    with _configured_base():
        return _base.build_parser()


def main() -> None:
    with _configured_base():
        _base.main()


if __name__ == "__main__":
    main()
