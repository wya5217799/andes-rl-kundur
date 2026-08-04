"""Prepare and analyse the corrected R332 static ANDES bridge reconciliation."""

from __future__ import annotations

import argparse
import ast
import json
import platform
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT, ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from memory.tools.artifact_io import (  # noqa: E402
    payload_sha256,
    read_verified_json,
    sha256_file,
    write_new_json,
)
from probes.r332_andes_bridge_reconciliation import (  # noqa: E402
    REQUIRED_MAPPING_IDS,
    evaluate_bridge_reconciliation,
)
from scripts import run_r331_andes_bridge_reconciliation as r331  # noqa: E402

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    active_power_incidence,
)

ROUND_ID = "R332"
QUESTION_ID = "Q-0084"
DEFAULT_SEAL = ROOT / "memory/rounds/R332/andes_bridge_reconciliation_seal.json"
DEFAULT_OUT = ROOT / "results/r332_andes_bridge_reconciliation"

OFFICIAL_SOURCES = (
    r331.OFFICIAL_MANUAL,
    r331.OFFICIAL_TDS,
    r331.OFFICIAL_SYNGEN,
    r331.OFFICIAL_DG,
    r331.OFFICIAL_PARAMETERS,
    r331.OFFICIAL_GENCLS,
    r331.OFFICIAL_ESD1,
    r331.OFFICIAL_PVD1,
)
OFFICIAL_TDS_SOURCE = "https://github.com/CURENT/andes/blob/v2.0.0/andes/routines/tds.py"
OFFICIAL_DISCRETE_SOURCE = "https://github.com/CURENT/andes/blob/v2.0.0/andes/core/discrete.py"
OFFICIAL_GROUP_SOURCE = "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/group.py"
EXPECTED_INSTALLED_SOURCE_SHA256 = {
    **r331.EXPECTED_INSTALLED_SOURCE_SHA256,
    "tds": "224ff43d78de8e6808efa0a6b858d8dbe2ca511128a90a8260009c8146d6e8ba",
    "discrete": "93bc2c82379fef80f157e5916b20437d82afb2381bba5b5730c2d4a1877c73fc",
    "group": "139e172b31e96fa7e92ee8909feca704253702a3e9b5ea6c3df12b54d46b9697",
}
EXPECTED_INSTALLED_SOURCE_SUFFIX = {
    **r331.EXPECTED_INSTALLED_SOURCE_SUFFIX,
    "tds": "/andes/routines/tds.py",
    "discrete": "/andes/core/discrete.py",
    "group": "/andes/models/group.py",
}
EXPECTED_INSTALLED_SEMANTICS = {
    **r331.EXPECTED_INSTALLED_SEMANTICS,
    "tds_store_precedes_switch": True,
    "limiter_lower_flag_excludes_inside_flag": True,
    "set_paux_writes_pext0_absolute_system_base": True,
}
OFFICIAL_SOURCES = (
    *OFFICIAL_SOURCES,
    OFFICIAL_TDS_SOURCE,
    OFFICIAL_DISCRETE_SOURCE,
    OFFICIAL_GROUP_SOURCE,
)


def _path_text(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _artifact_path_text(path: Path) -> str:
    try:
        return _path_text(path)
    except ValueError:
        return path.name


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R332/plan.md",
        "question": ROOT / "memory/questions/Q-0084.md",
        "model_contract": ROOT / "paper/decoupling_marl_model_first/working/model_contract.md",
        "r329_seal": ROOT / "memory/rounds/R329/disturbance_estimator_seal.json",
        "r316_dynamic_model": ROOT / "results/r316_dynamic_reduction/dynamic_model.json",
        "model_first_contract": ROOT / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "model_first_environment": ROOT / "src/andes_rl_kundur/env/andes/model_first_env.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "storage_environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py",
        "active_power_contract": ROOT / "src/andes_rl_kundur/control/active_power.py",
        "constrained_horizon": ROOT
        / "src/andes_rl_kundur/control/model_first_constrained_horizon.py",
        "sparse_controller": ROOT / "src/andes_rl_kundur/control/model_first_constrained_qp.py",
        "estimator": ROOT / "src/andes_rl_kundur/control/model_first_disturbance_estimator.py",
        "r315_execution_adapter": ROOT / "scripts/run_r315_dynamic_reduction.py",
        "r315_validation": ROOT / "probes/r315_dynamic_reduction_validation.py",
        "r329_execution_adapter": ROOT / "scripts/run_r329_disturbance_estimator.py",
        "r331_installed_source_reader": ROOT / "scripts/run_r331_andes_bridge_reconciliation.py",
        "validator": ROOT / "probes/r332_andes_bridge_reconciliation.py",
        "adapter": Path(__file__).resolve(),
        "validator_tests": ROOT / "tests/test_r332_andes_bridge_reconciliation.py",
        "adapter_tests": ROOT / "tests/test_r332_andes_bridge_adapter.py",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _repository_sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _installed_andes_identity() -> dict[str, object]:
    code = """
import hashlib
import inspect
import json
import andes
import andes.core.discrete as discrete
import andes.models.distributed.esd1 as esd1
import andes.models.distributed.pvd1 as pvd1
import andes.models.group as group
import andes.models.synchronous.gencls as gencls
import andes.routines.tds as tds

modules = (
    ("gencls", gencls),
    ("esd1", esd1),
    ("pvd1", pvd1),
    ("tds", tds),
    ("discrete", discrete),
    ("group", group),
)
payload = {"version": andes.__version__, "sources": {}, "semantic_facts": {}}
sources = {}
for name, module in modules:
    path = inspect.getsourcefile(module)
    with open(path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    payload["sources"][name] = {"path": path, "sha256": digest}
    sources[name] = inspect.getsource(module)
ipul_block = sources["pvd1"].split("self.Ipul =", 1)[1].split(")", 1)[0]
tds_store = sources["tds"].find("dae.store()")
tds_switch = sources["tds"].find("self.do_switch()", tds_store)
group_paux = sources["group"].rsplit("def set_paux(self, system, idx, value):", 1)[-1]
group_paux = group_paux.split("def get_paux", 1)[0]
payload["semantic_facts"] = {
    "esd1_lower_bound_is_minus_pmx": (
        "self.pmin = ConstService(v_str='-pmx')" in sources["esd1"]
        and "self.PHL.lower = self.pmin" in sources["esd1"]
    ),
    "ipul_has_no_lower_saturation_term": (
        "(Psum * PHL_zi + pmx * PHL_zu) / vp" in sources["pvd1"]
        and "PHL_zl" not in ipul_block
    ),
    "achieved_power_is_voltage_times_ipout": "Pe = Ipout_y * v" in sources["pvd1"],
    "tds_store_precedes_switch": 0 <= tds_store < tds_switch,
    "limiter_lower_flag_excludes_inside_flag": (
        "self.zl[:] = np.less_equal(self.u.v, lower_v)" in sources["discrete"]
        and "self.zi[:] = np.logical_not(np.logical_or(self.zu, self.zl))"
        in sources["discrete"]
    ),
    "set_paux_writes_pext0_absolute_system_base": (
        "Writes to the device's ``Pext0``" in group_paux
        and "The value is in system-base per-unit." in group_paux
        and "self.set_setpoint(system, idx, 'paux', value)" in group_paux
    ),
}
print(json.dumps(payload, sort_keys=True))
"""
    completed = subprocess.run(
        ["wsl.exe", "--exec", r331.ANDES_PYTHON, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "cannot inspect the WSL ANDES installation: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("installed ANDES identity is not an object")
    return payload


def _installed_sources_valid(installed: Mapping[str, object]) -> bool:
    if installed.get("version") != "2.0.0":
        return False
    sources = installed.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != set(EXPECTED_INSTALLED_SOURCE_SHA256):
        return False
    for name, entry in sources.items():
        if not isinstance(entry, Mapping):
            return False
        path = entry.get("path")
        digest = entry.get("sha256")
        if (
            not isinstance(path, str)
            or not path.endswith(EXPECTED_INSTALLED_SOURCE_SUFFIX[str(name)])
            or digest != EXPECTED_INSTALLED_SOURCE_SHA256[str(name)]
        ):
            return False
    return installed.get("semantic_facts") == EXPECTED_INSTALLED_SEMANTICS


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _qualified_call_names(source: str, class_name: str, method_name: str) -> set[str]:
    tree = ast.parse(source)
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            target = next(
                (
                    item
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ),
                None,
            )
            break
    if target is None:
        return set()

    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = dotted(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return f"{node.func.id}()"
        return ""

    return {
        dotted(node.func)
        for node in ast.walk(target)
        if isinstance(node, ast.Call) and dotted(node.func)
    }


def _static_repo_semantics() -> dict[str, bool]:
    environment = _read("src/andes_rl_kundur/env/andes/model_first_env.py")
    base_environment = _read("src/andes_rl_kundur/env/andes/base_env.py")
    contract = _read("src/andes_rl_kundur/env/andes/model_first_contract.py")
    active_power = _read("src/andes_rl_kundur/control/active_power.py")
    horizon = _read("src/andes_rl_kundur/control/model_first_constrained_horizon.py")
    sparse = _read("src/andes_rl_kundur/control/model_first_constrained_qp.py")
    estimator = _read("src/andes_rl_kundur/control/model_first_disturbance_estimator.py")
    r315 = _read("scripts/run_r315_dynamic_reduction.py")
    r315_validation = _read("probes/r315_dynamic_reduction_validation.py")
    r329 = _read("scripts/run_r329_disturbance_estimator.py")
    plan = _read("memory/rounds/R332/plan.md")
    model_contract = _read("paper/decoupling_marl_model_first/working/model_contract.md")
    step_source = environment.split("    def step(self, actions, *, bess_power_request_pu):", 1)[
        1
    ].split("\ndef expected_model_first_system_md", 1)[0]
    step_calls = _qualified_call_names(
        environment,
        "AndesModelFirstEnv",
        "step",
    )
    expected_incidence = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [-1.0, 1.0, 0.0],
            [0.0, -1.0, 1.0],
            [0.0, 0.0, -1.0],
        ]
    )
    return {
        "no_hidden_md_write": (
            "np.any(action_matrix != 0.0)" in step_source
            and "self.ss.GENCLS.set" not in step_calls
            and "super().step" not in step_calls
            and "self.ss.DG.set_paux" in step_calls
        ),
        "requested_projected_internal_achieved_distinguished": all(
            token in step_source
            for token in (
                '"bess_requested_power_system_pu"',
                '"bess_commanded_power_system_pu"',
                '"bess_external_command_readback_system_pu"',
                '"bess_internal_power_reference_system_pu"',
                '"bess_actual_power_system_pu"',
            )
        )
        and "actual_power = self._get_bess_actual_power()" in step_source
        and '"bess_actual_power_system_pu": actual_power.copy()' in step_source
        and "externally projected" in plan,
        "active_power_incidence_sign_correct": bool(
            np.array_equal(active_power_incidence(), expected_incidence)
            and "source-positive, target-negative" in contract
            and "basis = np.column_stack((np.ones(4), active_power_incidence()))" in horizon
            and "coordinate_actions = (self.node_to_coordinate" in sparse
        ),
        "physical_frequency_base_60_hz": (
            "FN = 60.0" in environment
            and "physical_nominal_frequency_hz: float = 60.0" in contract
            and 'row["delta_f_physical_hz"] = (frequency - 60.0).tolist()' in r315
            and "frequency / 60.0" in r315_validation
        ),
        "sample_order_and_delay_explicit": (
            "control_period_seconds: float = 0.2" in contract
            and "dt_sub = self.DT / self.N_SUBSTEPS" in step_source
            and 'os.environ.get("N_SUBSTEPS")' in base_environment
            and "wrapper-owned exact-event sampling" in plan
            and "one-sample delay" in plan
            and "previous_delivered_output" in estimator
            and "previous_executed_action" in estimator
        ),
        "disturbance_and_initialization_explicit": (
            "R306 Stage-0 forbids every PQ edit" in environment
            and '"disturbance_graph": {"kind": "none"' in environment
            and "total_input = disturbance + coordinate_action" in r329
            and "B_d\\delta d" in model_contract
            and "edits the PQ" in model_contract
            and "prospective equivalence" in plan
        ),
        "all_feasibility_limits_explicit": all(
            token in active_power
            for token in (
                "device_power_limit_system_pu",
                "device_ramp_limit_system_pu_per_s",
                "active_current_limit_device_pu",
                "soc_min",
                "soc_max",
                "energy_limit",
                "charge_efficiency",
                "discharge_efficiency",
            )
        )
        and '"bess_internal"' in step_source
        and "Psum > -pmx + epsilon" in plan
        and "hard SOC clamp" in plan
        and "v * Ipout_y" in plan,
        "reduced_latent_state_not_claimed_as_physical_readback": (
            "internal-estimator-memory"
            in _read("memory/rounds/R329/disturbance_estimator_seal.json")
            and "previous_delivered_output" in estimator
            and "prior_estimate" in estimator
            and "delta_f_physical_hz" in r315_validation
        ),
        "platform_claim_ceiling_respected": (
            "phasor-domain electromechanical" in plan
            and "No performance, EMT, hardware" in plan
            and "Run no ANDES trajectory" in plan
        ),
    }


def _replace_row_locators(rows: list[dict[str, object]]) -> None:
    by_id = {str(row["id"]): row for row in rows}
    by_id["device_identity"]["implementation_locators"] = [
        "src/andes_rl_kundur/env/andes/model_first_env.py:200",
        "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:27",
        "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:38",
    ]
    by_id["delivered_outputs"]["implementation_locators"] = [
        "scripts/run_r315_dynamic_reduction.py:555",
        "probes/r315_dynamic_reduction_validation.py:340",
        "probes/r315_dynamic_reduction_validation.py:345",
        "src/andes_rl_kundur/env/andes/model_first_env.py:331",
        "src/andes_rl_kundur/env/andes/model_first_env.py:373",
        "src/andes_rl_kundur/env/andes/model_first_env.py:377",
        "src/andes_rl_kundur/env/andes/model_first_env.py:378",
        "src/andes_rl_kundur/env/andes/model_first_env.py:379",
    ]
    by_id["action_mapping"]["implementation_locators"] = [
        "src/andes_rl_kundur/env/andes/model_first_contract.py:16",
        "src/andes_rl_kundur/control/model_first_constrained_horizon.py:108",
        "src/andes_rl_kundur/control/model_first_constrained_qp.py:310",
        "src/andes_rl_kundur/control/model_first_constrained_qp.py:311",
    ]
    by_id["feasibility_limits"]["implementation_locators"] = [
        "src/andes_rl_kundur/control/active_power.py:99",
        "src/andes_rl_kundur/control/active_power.py:186",
        "src/andes_rl_kundur/control/active_power.py:266",
        "src/andes_rl_kundur/control/model_first_constrained_qp.py:236",
        "src/andes_rl_kundur/control/model_first_constrained_qp.py:279",
        "src/andes_rl_kundur/env/andes/model_first_env.py:374",
        "src/andes_rl_kundur/env/andes/model_first_env.py:382",
        "src/andes_rl_kundur/env/andes/model_first_env.py:383",
    ]
    by_id["storage_dynamics"]["implementation_locators"] = [
        "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:75",
        "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:120",
        "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:123",
        "src/andes_rl_kundur/control/active_power.py:162",
        "src/andes_rl_kundur/env/andes/model_first_env.py:295",
    ]
    by_id["sample_timing"]["implementation_locators"] = [
        "src/andes_rl_kundur/control/model_first_disturbance_estimator.py:196",
        "src/andes_rl_kundur/control/model_first_disturbance_estimator.py:220",
        "src/andes_rl_kundur/env/andes/model_first_env.py:267",
        "paper/decoupling_marl_model_first/working/model_contract.md:421",
    ]
    by_id["disturbance_and_initialization"]["implementation_locators"] = [
        "paper/decoupling_marl_model_first/working/model_contract.md:57",
        "paper/decoupling_marl_model_first/working/model_contract.md:433",
        "src/andes_rl_kundur/env/andes/model_first_env.py:123",
        "src/andes_rl_kundur/env/andes/model_first_env.py:130",
        "src/andes_rl_kundur/env/andes/model_first_env.py:210",
        "scripts/run_r329_disturbance_estimator.py:427",
        "scripts/run_r329_disturbance_estimator.py:428",
        "scripts/run_r329_disturbance_estimator.py:429",
    ]
    by_id["reduced_latent_state"]["implementation_locators"] = [
        "src/andes_rl_kundur/control/model_first_disturbance_estimator.py:196",
        "src/andes_rl_kundur/control/model_first_disturbance_estimator.py:220",
        "memory/rounds/R329/disturbance_estimator_seal.json#/contract/estimator",
        "results/r316_dynamic_reduction/dynamic_model.json#/points",
    ]


def build_mapping_rows(installed: Mapping[str, object]) -> list[dict[str, object]]:
    if not _installed_sources_valid(installed):
        raise RuntimeError("installed ANDES source identity or semantics differ from R332")
    legacy_identity = {
        "version": installed["version"],
        "sources": {name: installed["sources"][name] for name in ("gencls", "esd1", "pvd1")},
        "semantic_facts": {
            name: installed["semantic_facts"][name] for name in r331.EXPECTED_INSTALLED_SEMANTICS
        },
    }
    rows = r331.build_mapping_rows(legacy_identity)
    _replace_row_locators(rows)
    by_id = {str(row["id"]): row for row in rows}
    by_id["action_mapping"]["official_locators"] = [
        *by_id["action_mapping"]["official_locators"],
        OFFICIAL_GROUP_SOURCE,
    ]
    by_id["delivered_outputs"]["official_locators"] = [
        *by_id["delivered_outputs"]["official_locators"],
        OFFICIAL_GROUP_SOURCE,
    ]
    by_id["feasibility_limits"]["official_locators"] = [
        *by_id["feasibility_limits"]["official_locators"],
        OFFICIAL_DISCRETE_SOURCE,
    ]
    by_id["storage_dynamics"]["official_locators"] = [
        *by_id["storage_dynamics"]["official_locators"],
        OFFICIAL_DISCRETE_SOURCE,
    ]
    by_id["sample_timing"]["official_locators"] = [
        *by_id["sample_timing"]["official_locators"],
        OFFICIAL_TDS_SOURCE,
    ]
    by_id["delivered_outputs"]["reduced_model_meaning"] = (
        "inertia-weighted common and three differential coordinates of physical "
        "frequency deviation; achieved grid injection is v * Ipout_y, not Pext0, "
        "Psum, or Ipcmd"
    )
    by_id["feasibility_limits"]["sign"] = (
        "signed active-power request; internal system-base Psum must satisfy "
        "Psum > -pmx + epsilon or reproduce the installed zero-below-lower path"
    )
    by_id["feasibility_limits"]["claim_ceiling_consequence"] = (
        "later seal must fail on external projection or internal limiter activation; "
        "freeze the internal Psum margin or exact installed behavior"
    )
    by_id["storage_dynamics"]["claim_ceiling_consequence"] = (
        "ESD1 supplies lagged achieved power and directional SOC blocking, not an "
        "internal ramp, one-step-energy projector, or hard SOC clamp"
    )
    by_id["storage_dynamics"]["reduced_model_meaning"] = (
        "ESD1 active-current lag and continuous SOC integration driven by achieved "
        "grid injection v * Ipout_y, not Pext0, Psum, or Ipcmd"
    )
    by_id["sample_timing"]["claim_ceiling_consequence"] = (
        "the wrapper owns one-sample delay and must use the stored pre-switch "
        "exact-event row or an explicit pre-callback sample; reject N_SUBSTEPS drift"
    )
    by_id["disturbance_and_initialization"]["claim_ceiling_consequence"] = (
        "R329 remains immutable evidence; a distinct physical disturbance channel "
        "requires prospective equivalence or a separately sealed successor package"
    )
    if {str(row["id"]) for row in rows} != set(REQUIRED_MAPPING_IDS):
        raise RuntimeError("R332 mapping inventory differs from the validator")
    return sorted(rows, key=lambda row: str(row["id"]))


def build_reconciliation(installed_identity: Mapping[str, object]) -> dict[str, object]:
    installed = dict(installed_identity)
    semantics = _static_repo_semantics()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "mapping_rows": build_mapping_rows(installed),
        "source_identity": {
            "repository_sources_match": True,
            "installed_andes_version": installed.get("version"),
            "installed_sources_match": _installed_sources_valid(installed),
            "installed_semantics_match": (
                installed.get("semantic_facts") == EXPECTED_INSTALLED_SEMANTICS
            ),
            "official_sources_primary": True,
        },
        "semantic_guards": semantics,
        "scope_guards": {
            "physical_execution_performed": False,
            "controller_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
        },
        "deterministic_replay": True,
    }


def _created_utc(value: str | None) -> str:
    return value or datetime.now(UTC).isoformat()


def prepare(
    seal_path: Path,
    *,
    installed_identity: Mapping[str, object] | None = None,
    created_utc: str | None = None,
) -> str:
    installed = dict(installed_identity or _installed_andes_identity())
    reconciliation = build_reconciliation(installed)
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": _created_utc(created_utc),
        "reconciliation": reconciliation,
        "reconciliation_payload_sha256": payload_sha256(reconciliation),
        "repository_sources": _repository_sources(),
        "installed_andes": installed,
        "official_sources": list(OFFICIAL_SOURCES),
    }
    digest = write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(
    path: Path,
    expected_sha256: str,
    *,
    installed_identity: Mapping[str, object] | None = None,
) -> tuple[dict[str, Any], str]:
    seal, digest = read_verified_json(path, expected_sha256)
    installed = dict(installed_identity or _installed_andes_identity())
    reconciliation = build_reconciliation(installed)
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("installed_andes") != installed
        or seal.get("repository_sources") != _repository_sources()
        or seal.get("reconciliation") != reconciliation
        or seal.get("reconciliation_payload_sha256") != payload_sha256(reconciliation)
    ):
        raise RuntimeError("R332 seal, source, installation, or contract drift")
    return seal, digest


def _runtime_record() -> dict[str, str]:
    return {"python": sys.version, "platform": platform.platform()}


def analyse(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    *,
    installed_identity: Mapping[str, object] | None = None,
    created_utc: str | None = None,
) -> str:
    seal, seal_digest = _load_seal(
        seal_path,
        expected_sha256,
        installed_identity=installed_identity,
    )
    reconciliation = seal["reconciliation"]
    first = evaluate_bridge_reconciliation(reconciliation)
    second = evaluate_bridge_reconciliation(reconciliation)
    if first != second:
        raise RuntimeError("R332 analysis replay is not deterministic")
    analysis = {
        **first,
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_digest,
        "deterministic_replay": True,
        "mapping_rows": reconciliation["mapping_rows"],
        "source_identity": reconciliation["source_identity"],
        "semantic_guards": reconciliation["semantic_guards"],
        "scope_guards": reconciliation["scope_guards"],
        "next_gate": (
            "prospectively identify and validate the separate physical disturbance "
            "channel while preserving R329 as immutable reduced-model evidence; "
            "require predeclared equivalence to R329's frozen disturbance channel "
            "or reserve a separately sealed successor estimator-controller package "
            "before any physical closed loop"
        ),
    }
    out_dir = out_dir.resolve()
    analysis_digest = write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": _created_utc(created_utc),
        "seal_sha256": seal_digest,
        "analysis_sha256": analysis_digest,
        "runtime": _runtime_record(),
        "installed_andes": seal["installed_andes"],
        "physical_execution_performed": False,
        "controller_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }
    provenance_digest = write_new_json(out_dir / "provenance.json", provenance)
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": _created_utc(created_utc),
        "seal_sha256": seal_digest,
        "classification": analysis["classification"],
        "records": [
            {
                "path": _artifact_path_text(out_dir / "analysis.json"),
                "sha256": analysis_digest,
            },
            {
                "path": _artifact_path_text(out_dir / "provenance.json"),
                "sha256": provenance_digest,
            },
        ],
        "physical_execution_performed": False,
        "controller_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }
    manifest_digest = write_new_json(out_dir / "run_manifest.json", manifest)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"run_manifest_sha256={manifest_digest}", flush=True)
    return analysis_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        prepare(args.seal)
    else:
        analyse(args.seal, args.expected_sha256, args.out)


if __name__ == "__main__":
    main()
