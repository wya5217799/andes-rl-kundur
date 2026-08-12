"""Audit the R371 four-VSG energy-port design without running ANDES TDS.

The probe binds the design to the installed ANDES source, checks the local
power/torque and energy seams, and writes a create-only result with a SHA-256
sidecar.  A pass authorizes only a later physical object gate, never training.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.vsg_energy_port import (  # noqa: E402
    VSGEnergyPortContract,
)
from andes_rl_kundur.env.andes.vsg_energy_port_env import (  # noqa: E402
    AndesVSGEnergyPortEnv,
)

DEFAULT_OUTPUT = ROOT / "results/research_loop/r371_vsg_energy_port_design/analysis.json"
DEFAULT_WSL_PYTHON = "/home/wya/andes_venv/bin/python"


_ANDES_SOURCE_SCRIPT = r"""
import hashlib
import inspect
import json

import andes
from andes.models.group import GroupBase, SynGen
from andes.models.synchronous.genbase import GENBase

group_path = inspect.getsourcefile(SynGen)
genbase_path = inspect.getsourcefile(GENBase)
set_pref_source = inspect.getsource(SynGen.set_pref)
get_pref_source = inspect.getsource(SynGen.get_pref)
setpoint_source = inspect.getsource(GroupBase.set_setpoint)
genbase_source = inspect.getsource(GENBase)

def record(path):
    with open(path, "rb") as stream:
        digest = hashlib.sha256(stream.read()).hexdigest()
    return {"path": path, "sha256": digest}

print(json.dumps({
    "andes_version": andes.__version__,
    "source_files": {
        "group": record(group_path),
        "genbase": record(genbase_path),
    },
    "pref_priority_is_turbine_governor": (
        SynGen._setpoint_priority.get("pref") == [("TurbineGov", "syn")]
    ),
    "pref_fallback_is_tm0": GENBase._setpoints.get("pref") == "tm0",
    "set_pref_uses_setpoint_resolver": "self.set_setpoint(system, idx, 'pref', value)" in set_pref_source,
    "get_pref_uses_setpoint_resolver": "self.get_setpoint(system, idx, 'pref')" in get_pref_source,
    "pref_documented_system_base_pu": "system-base per-unit" in set_pref_source,
    "setpoint_write_targets_value_array": ".v[uid] = value" in setpoint_source,
    "omega_equation_uses_tm_minus_te_and_damping": (
        "tm - te - D * (omega - 1)" in genbase_source
    ),
    "tm_equation_is_tm0_minus_tm": "e_str='tm0 - tm'" in genbase_source,
}, sort_keys=True))
"""


def collect_andes_source_facts(
    *,
    wsl_python: str = DEFAULT_WSL_PYTHON,
) -> dict[str, Any]:
    """Collect source-bound facts from installed ANDES without loading a case."""

    completed = subprocess.run(
        ["wsl.exe", wsl_python, "-c", _ANDES_SOURCE_SCRIPT],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to inspect installed ANDES source: " + completed.stderr.strip()
        )
    return json.loads(completed.stdout)


def _valid_source_record(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    path = value.get("path")
    digest = value.get("sha256")
    return bool(
        isinstance(path, str)
        and path
        and isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest)
    )


def _class_method_source(source: str, class_name: str, method_name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return ast.get_source_segment(source, child) or ""
    return ""


def build_design_analysis(source_facts: Mapping[str, Any]) -> dict[str, Any]:
    """Classify source semantics and the nonexecuting local implementation."""

    energy = r272_frozen_bess_contract()
    contract = VSGEnergyPortContract(energy)
    requested = np.asarray([0.04, -0.04, 0.02, -0.02])
    omega = np.asarray([1.0, 0.99, 1.01, 1.0])
    baseline = np.full(4, 0.5)
    dispatch = contract.dispatch(
        requested_power_system_pu=requested,
        previous_power_system_pu=np.zeros(4),
        soc=np.full(4, energy.soc_initial),
        voltage_pu=np.ones(4),
        sampled_omega_pu=omega,
        baseline_pref_system_pu=baseline,
        dt_seconds=0.2,
    )
    actor_vector_shape_fails_closed = False
    try:
        contract.dispatch(
            requested_power_system_pu=np.zeros(3),
            previous_power_system_pu=np.zeros(4),
            soc=np.full(4, energy.soc_initial),
            voltage_pu=np.ones(4),
            sampled_omega_pu=np.ones(4),
            baseline_pref_system_pu=baseline,
            dt_seconds=0.2,
        )
    except ValueError:
        actor_vector_shape_fails_closed = True
    adapter_source = inspect.getsource(AndesVSGEnergyPortEnv)
    contract_source = inspect.getsource(VSGEnergyPortContract)
    v4_path = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
    v4_source = v4_path.read_text(encoding="utf-8")
    addon_source = _class_method_source(
        v4_source,
        "AndesMultiVSGEnvV4",
        "_pre_setup_addons",
    )
    source_files = source_facts.get("source_files", {})
    source_integrity = bool(
        source_facts.get("andes_version") == "2.0.0"
        and isinstance(source_files, Mapping)
        and _valid_source_record(source_files.get("group"))
        and _valid_source_record(source_files.get("genbase"))
    )
    torque_source = bool(
        source_facts.get("pref_fallback_is_tm0")
        and source_facts.get("omega_equation_uses_tm_minus_te_and_damping")
        and source_facts.get("tm_equation_is_tm0_minus_tm")
    )
    checks = {
        "installed_andes_2_0_0_source_hashes_bound": source_integrity,
        "installed_pref_resolver_and_system_base_units_verified": bool(
            source_facts.get("pref_priority_is_turbine_governor")
            and source_facts.get("set_pref_uses_setpoint_resolver")
            and source_facts.get("get_pref_uses_setpoint_resolver")
            and source_facts.get("pref_documented_system_base_pu")
            and source_facts.get("setpoint_write_targets_value_array")
        ),
        "installed_swing_equation_supports_torque_semantics": torque_source,
        "v4_vsgs_have_no_turbine_governor": bool(
            "for syn_idx in ss.GENROU.idx.v" in addon_source
            and "ss.IEEEG1.add" in addon_source
            and "GENCLS" not in addon_source
            and "VSG_" not in addon_source
        ),
        "four_independent_power_commands_map_to_four_pref_writes": bool(
            energy.device_count == 4
            and np.allclose(
                dispatch.pref_system_pu,
                baseline + dispatch.commanded_power_system_pu / omega,
                rtol=0.0,
                atol=1.0e-12,
            )
            and "for index, pref in zip(" in adapter_source
            and "SynGen.set_pref" in adapter_source
        ),
        "actor_vector_shape_fails_closed": actor_vector_shape_fails_closed,
        "legacy_md_path_is_forced_to_exact_zero": bool(
            "zero_md_actions = {index: np.zeros(2)" in adapter_source
            and "base_env.step(zero_md_actions)" in adapter_source
        ),
        "independent_storage_object_is_excluded": bool(
            "andes_vsg_storage_env" not in adapter_source
            and "andes_vsg_storage_env" not in contract_source
        ),
        "requested_commanded_written_and_achieved_values_are_distinct": bool(
            "requested_power_system_pu" in contract_source
            and "commanded_power_system_pu" in contract_source
            and "pref_system_pu" in contract_source
            and "achieved_power_system_pu" in contract_source
        ),
        "energy_is_settled_from_torque_readback_and_actual_speed": bool(
            "actual_torque_system_pu=actual_torque" in adapter_source
            and "actual_omega_pu=average_omega" in adapter_source
            and "integrate_soc(" in contract_source
        ),
        "soc_power_ramp_capability_and_energy_contract_is_traceable": bool(
            energy.source_ids
            and 0.0 <= energy.soc_min < energy.soc_initial < energy.soc_max <= 1.0
            and energy.device_power_limit_system_pu > 0.0
            and energy.device_energy_mwh > 0.0
        ),
        "design_pass_authorizes_no_execution_or_training": True,
    }

    if not source_integrity:
        classification = "ANALYSIS-INVALID"
    elif not torque_source:
        classification = "STOP-TORQUE-POWER-CONFLATION"
    elif not (
        checks["four_independent_power_commands_map_to_four_pref_writes"]
        and checks["v4_vsgs_have_no_turbine_governor"]
        and checks["legacy_md_path_is_forced_to_exact_zero"]
        and checks["independent_storage_object_is_excluded"]
    ):
        classification = "STOP-OBJECT-MISMATCH"
    elif not (
        checks["energy_is_settled_from_torque_readback_and_actual_speed"]
        and checks["soc_power_ramp_capability_and_energy_contract_is_traceable"]
    ):
        classification = "STOP-ENERGY-CONTRACT"
    elif all(checks.values()):
        classification = "ENERGY-PORT-DESIGN-PASS"
    else:
        classification = "ANALYSIS-INVALID"

    local_sources = {}
    for name, path in {
        "contract": ROOT / "src/andes_rl_kundur/control/vsg_energy_port.py",
        "adapter": ROOT / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py",
        "v4_plant": v4_path,
    }.items():
        local_sources[name] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    return {
        "schema_version": 1,
        "round": "R371",
        "manuscript_line": "paralleled-vsg-marl",
        "classification": classification,
        "checks": checks,
        "andes_source_contract": dict(source_facts),
        "local_source_contract": local_sources,
        "actor_object_contract": {
            "actors": 4,
            "owned_objects": "four governor-free GENCLS VSGs",
            "ports": "one SynGen.pref/tm0 input per VSG",
            "mapping": "one-to-one actor-to-VSG-to-port",
            "excluded_objects": ["independent ESD1", "central scalar", "M/D action"],
        },
        "power_torque_contract": {
            "requested_and_commanded_unit": "system-base per-unit active power",
            "pref_write_unit": "system-base per-unit mechanical torque",
            "sampled_write": (
                "pref = baseline_tm0 + commanded_power / sampled_omega"
            ),
            "energy_settlement": (
                "achieved_power = (readback_torque - baseline_tm0) * actual_omega"
            ),
            "settlement_quadrature": "trapezoidal endpoint speed over 0.2 s hold",
        },
        "energy_contract": {
            "source_ids": list(energy.source_ids),
            "soc_initial": energy.soc_initial,
            "soc_bounds": [energy.soc_min, energy.soc_max],
            "device_power_limit_system_pu": energy.device_power_limit_system_pu,
            "device_energy_mwh": energy.device_energy_mwh,
            "full_scale_ramp_seconds": energy.full_scale_ramp_seconds,
        },
        "claim_scope": "static design and implementation contract only",
        "physical_execution_authorized": False,
        "training_authorized": False,
        "next_gate": "physical_per_vsg_energy_port_object_gate",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_analysis(output: Path, source_facts: Mapping[str, Any]) -> None:
    sidecar = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite R371 analysis: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_design_analysis(source_facts)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    sidecar.write_text(f"{_sha256(output)}  {output.name}\n", encoding="ascii")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-facts", type=Path)
    parser.add_argument("--wsl-python", default=DEFAULT_WSL_PYTHON)
    args = parser.parse_args(argv)
    if args.source_facts is None:
        source_facts = collect_andes_source_facts(wsl_python=args.wsl_python)
    else:
        source_facts = json.loads(args.source_facts.read_text(encoding="utf-8"))
    write_analysis(args.output.resolve(), source_facts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
