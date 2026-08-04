"""Prepare and analyse the R331 static ANDES bridge reconciliation.

Motivation: the reduced-model controller may enter a physical ANDES bridge only
after every interface semantic is reconciled.  This adapter fingerprints the
repository and installed ANDES 2.0.0 sources, builds the frozen mapping record,
and emits a fail-closed ALLOW/QUALIFY/BLOCK analysis.  It never runs ANDES TDS,
a controller, distributed code, training, or EVAL.

Usage:
    python scripts/run_r331_andes_bridge_reconciliation.py prepare
    python scripts/run_r331_andes_bridge_reconciliation.py analyse \
        --expected-sha256 <seal-sha256>

Failure mode: all artifacts are create-only.  Source, package, or contract
drift aborts analysis rather than weakening the judgment.
"""

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
from probes.r331_andes_bridge_reconciliation import (  # noqa: E402
    REQUIRED_MAPPING_IDS,
    evaluate_bridge_reconciliation,
)

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    active_power_incidence,
)

ROUND_ID = "R331"
QUESTION_ID = "Q-0084"
DEFAULT_SEAL = ROOT / "memory/rounds/R331/andes_bridge_reconciliation_seal.json"
DEFAULT_OUT = ROOT / "results/r331_andes_bridge_reconciliation"

ANDES_PYTHON = "/home/wya/andes_venv/bin/python"
OFFICIAL_MANUAL = "https://docs.andes.app/en/v2.0.0/"
OFFICIAL_TDS = "https://docs.andes.app/en/v2.0.0/tutorials/04-time-domain.html"
OFFICIAL_SYNGEN = "https://docs.andes.app/en/v2.0.0/reference/models/SynGen.html"
OFFICIAL_DG = "https://docs.andes.app/en/v2.0.0/reference/models/DG.html"
OFFICIAL_PARAMETERS = "https://docs.andes.app/en/v2.0.0/modeling/components/parameters.html"
OFFICIAL_GENCLS = "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/synchronous/gencls.py"
OFFICIAL_ESD1 = "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/distributed/esd1.py"
OFFICIAL_PVD1 = "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/distributed/pvd1.py"

EXPECTED_INSTALLED_SOURCE_SHA256 = {
    "gencls": "b9b84d57434b989e7923a2eba197d5ce7122fd7b51c30e4d6ff547ed33797168",
    "esd1": "8049088d711d47c3799826c8977fb86e6b0af822b579bc04625d26b584e419cb",
    "pvd1": "56fb6012016b821104df0f38efed0ca2a048635e95872439efadf39534600c95",
}
EXPECTED_INSTALLED_SOURCE_SUFFIX = {
    "gencls": "/andes/models/synchronous/gencls.py",
    "esd1": "/andes/models/distributed/esd1.py",
    "pvd1": "/andes/models/distributed/pvd1.py",
}
EXPECTED_INSTALLED_SEMANTICS = {
    "esd1_lower_bound_is_minus_pmx": True,
    "ipul_has_no_lower_saturation_term": True,
    "achieved_power_is_voltage_times_ipout": True,
}


def _path_text(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _artifact_path_text(path: Path) -> str:
    try:
        return _path_text(path)
    except ValueError:
        return path.as_posix()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R331/plan.md",
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
        "validator": ROOT / "probes/r331_andes_bridge_reconciliation.py",
        "adapter": Path(__file__).resolve(),
        "validator_tests": ROOT / "tests/test_r331_andes_bridge_reconciliation.py",
        "adapter_tests": ROOT / "tests/test_r331_andes_bridge_adapter.py",
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
import andes.models.distributed.esd1 as esd1
import andes.models.distributed.pvd1 as pvd1
import andes.models.synchronous.gencls as gencls

payload = {"version": andes.__version__, "sources": {}, "semantic_facts": {}}
for name, module in (("gencls", gencls), ("esd1", esd1), ("pvd1", pvd1)):
    path = inspect.getsourcefile(module)
    with open(path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    payload["sources"][name] = {"path": path, "sha256": digest}
esd1_source = inspect.getsource(esd1)
pvd1_source = inspect.getsource(pvd1)
payload["semantic_facts"] = {
    "esd1_lower_bound_is_minus_pmx": (
        "self.pmin = ConstService(v_str='-pmx')" in esd1_source
        and "self.PHL.lower = self.pmin" in esd1_source
    ),
    "ipul_has_no_lower_saturation_term": (
        "(Psum * PHL_zi + pmx * PHL_zu) / vp" in pvd1_source
        and "PHL_zl" not in pvd1_source.split("self.Ipul =", 1)[1].split(")", 1)[0]
    ),
    "achieved_power_is_voltage_times_ipout": "Pe = Ipout_y * v" in pvd1_source,
}
print(json.dumps(payload, sort_keys=True))
"""
    completed = subprocess.run(
        ["wsl.exe", "--exec", ANDES_PYTHON, "-c", code],
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


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _qualified_call_names(source: str, class_name: str, method_name: str) -> set[str]:
    """Return dotted direct call targets in one method, without executing it."""

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
    plan = _read("memory/rounds/R331/plan.md")
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
        [[1.0, 0.0, 0.0], [-1.0, 1.0, 0.0], [0.0, -1.0, 1.0], [0.0, 0.0, -1.0]]
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
        ),
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
            and "N_SUBSTEPS override" in plan
            and "five 0.04-s wrapper segments" in plan
            and "previous_delivered_output" in estimator
            and "previous_executed_action" in estimator
            and "one-sample causal timing" in model_contract
        ),
        "disturbance_and_initialization_explicit": (
            "R306 Stage-0 forbids every PQ edit" in environment
            and '"disturbance_graph": {"kind": "none"' in environment
            and "total_input = disturbance + coordinate_action" in r329
            and "B_d\\delta d" in model_contract
            and "edits the PQ" in model_contract
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
        and '"bess_internal"' in step_source,
        "reduced_latent_state_not_claimed_as_physical_readback": (
            "internal-estimator-memory"
            in _read("memory/rounds/R329/disturbance_estimator_seal.json")
            and "previous_delivered_output" in estimator
            and "prior_estimate" in estimator
            and "delta_f_physical_hz" in r315_validation
        ),
        "platform_claim_ceiling_respected": (
            "phasor-domain electromechanical" in plan
            and "EMT" in plan
            and "Do not run a physical closed loop" in plan
        ),
    }


def _installed_sources_valid(installed: Mapping[str, object]) -> bool:
    if installed.get("version") != "2.0.0":
        return False
    sources = installed.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != {"gencls", "esd1", "pvd1"}:
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


def _row(
    identifier: str,
    *,
    meaning: str,
    implementation: list[str],
    official: list[str],
    unit: str,
    base: str,
    sign: str,
    sample_time: str,
    disposition: str,
    ceiling: str,
) -> dict[str, object]:
    return {
        "id": identifier,
        "reduced_model_meaning": meaning,
        "implementation_locators": implementation,
        "official_locators": official,
        "unit": unit,
        "base": base,
        "sign": sign,
        "sample_time": sample_time,
        "disposition": disposition,
        "claim_ceiling_consequence": ceiling,
    }


def build_mapping_rows(installed: Mapping[str, object]) -> list[dict[str, object]]:
    if not _installed_sources_valid(installed):
        raise RuntimeError("installed ANDES source identity or semantics differ from R331")
    rows = [
        _row(
            "platform_scope",
            meaning="sampled reduced realization of ANDES time-domain electromechanical response",
            implementation=[
                "paper/decoupling_marl_model_first/working/model_contract.md:26",
                "results/r316_dynamic_reduction/dynamic_model.json#/realization_contract",
            ],
            official=[OFFICIAL_TDS, OFFICIAL_MANUAL],
            unit="not applicable",
            base="phasor-domain transmission-system electromechanical model",
            sign="not applicable",
            sample_time="continuous DAE integration observed every 0.2 s",
            disposition="declared-omission",
            ceiling="no EMT switching, converter inner-loop, hardware, or field claim",
        ),
        _row(
            "bases_and_frequency",
            meaning="four physical frequency deviations normalized by 60 Hz and transformed with system-base inertia",
            implementation=[
                "src/andes_rl_kundur/env/andes/model_first_contract.py:121",
                "src/andes_rl_kundur/env/andes/model_first_env.py:48",
                "probes/r315_dynamic_reduction_validation.py:340",
            ],
            official=[OFFICIAL_GENCLS, OFFICIAL_SYNGEN, OFFICIAL_PARAMETERS],
            unit="Hz before normalization; dimensionless after division by 60",
            base="100-MVA system base; GENCLS M and D converted from 200-MVA device base",
            sign="positive deviation means rotor speed above nominal",
            sample_time="0.2 s",
            disposition="exact",
            ceiling="valid only for the declared 60-Hz model-first path",
        ),
        _row(
            "device_identity",
            meaning="four controlled GENCLS proxies paired one-to-one with four separate ESD1 devices",
            implementation=[
                "src/andes_rl_kundur/env/andes/model_first_env.py:196",
                "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:25",
            ],
            official=[OFFICIAL_GENCLS, OFFICIAL_ESD1, OFFICIAL_SYNGEN, OFFICIAL_DG],
            unit="indexed devices and buses",
            base="one GENCLS plus one 36-MVA ESD1 at each declared controlled bus",
            sign="not applicable",
            sample_time="fixed at setup and checked at reset/readback",
            disposition="exact",
            ceiling="no claim that GENCLS plus ESD1 is an EMT-faithful VSG converter",
        ),
        _row(
            "delivered_outputs",
            meaning="inertia-weighted common and three differential coordinates of physical frequency deviation",
            implementation=[
                "scripts/run_r315_dynamic_reduction.py:555",
                "probes/r315_dynamic_reduction_validation.py:337",
                "src/andes_rl_kundur/env/andes/model_first_env.py:373",
            ],
            official=[OFFICIAL_ESD1, OFFICIAL_PVD1, OFFICIAL_DG],
            unit="dimensionless frequency coordinate; active-power telemetry in system p.u.",
            base="60-Hz physical frequency and 100-MVA system power",
            sign="positive frequency coordinate follows positive rotor-speed deviation",
            sample_time="post-step readback at each 0.2-s boundary",
            disposition="exact",
            ceiling="requested, projected, internal, and achieved power remain distinct telemetry",
        ),
        _row(
            "action_mapping",
            meaning=(
                "one common plus three source-positive coordinates mapped invertibly "
                "to four node requests; estimator return input must be the inverse "
                "transform of the externally projected command"
            ),
            implementation=[
                "src/andes_rl_kundur/env/andes/model_first_contract.py:16",
                "src/andes_rl_kundur/control/model_first_constrained_horizon.py:108",
                "src/andes_rl_kundur/control/model_first_constrained_qp.py:308",
            ],
            official=[OFFICIAL_ESD1, OFFICIAL_PVD1, OFFICIAL_DG],
            unit="system p.u. active-power request",
            base="100-MVA system base",
            sign="edge source positive and target negative; positive node power discharges to grid",
            sample_time="one held node vector per 0.2-s interval",
            disposition="declared-assumption",
            ceiling=(
                "legacy inertia-action incidence is excluded; a later induced-projection "
                "test must reject planned request and achieved power as estimator input, "
                "and live M/D readback must remain unchanged"
            ),
        ),
        _row(
            "feasibility_limits",
            meaning="node power, ramp, SOC and energy constraints plus external voltage-current projection and internal ESD1 limiters",
            implementation=[
                "src/andes_rl_kundur/control/active_power.py:99",
                "src/andes_rl_kundur/control/model_first_constrained_qp.py:308",
                "src/andes_rl_kundur/env/andes/model_first_env.py:373",
            ],
            official=[OFFICIAL_ESD1, OFFICIAL_PVD1, OFFICIAL_DG],
            unit="system p.u., system p.u. per sample, SOC fraction, MWh, device p.u. current",
            base="100-MVA system, 36-MVA and 28-MWh per ESD1",
            sign=(
                "signed active-power request; charging must remain strictly above "
                "the ESD1 -pmx comparator boundary or reproduce its zero-below-lower path"
            ),
            sample_time="recomputed before every 0.2-s command and checked after the interval",
            disposition="declared-assumption",
            ceiling=(
                "later seal must fail on external projection or internal limiter activation, "
                "and must freeze a strict charging-boundary margin or exact ESD1 behavior"
            ),
        ),
        _row(
            "storage_dynamics",
            meaning="ESD1 active-current lag and continuous SOC integration driven by achieved grid power",
            implementation=[
                "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py:54",
                "src/andes_rl_kundur/control/active_power.py:162",
                "src/andes_rl_kundur/env/andes/model_first_env.py:295",
            ],
            official=[OFFICIAL_ESD1, OFFICIAL_PVD1, OFFICIAL_DG],
            unit="seconds, SOC fraction, MWh, system p.u. power",
            base="0.02-s active-current lag and 28-MWh device energy",
            sign="positive grid injection discharges SOC; negative injection charges SOC",
            sample_time="continuous plant state with 0.2-s controller readback",
            disposition="declared-assumption",
            ceiling="controller envelope is guarded, not an exact replacement for internal limiter dynamics",
        ),
        _row(
            "sample_timing",
            meaning="previous delivered output and previous executed coordinate action update a causal estimator before the next held command",
            implementation=[
                "src/andes_rl_kundur/control/model_first_disturbance_estimator.py:196",
                "src/andes_rl_kundur/env/andes/model_first_env.py:267",
                "paper/decoupling_marl_model_first/working/model_contract.md:421",
            ],
            official=[OFFICIAL_TDS, OFFICIAL_PVD1, OFFICIAL_DG],
            unit="seconds and discrete samples",
            base="0.2-s controller hold with TDS substeps",
            sign="not applicable",
            sample_time="one-sample causal delay; first command uses pre-disturbance observation",
            disposition="declared-assumption",
            ceiling=(
                "zero-delay language is forbidden; the later seal must reject any inherited "
                "N_SUBSTEPS override, pin five wrapper segments, and record the actual TDS grid"
            ),
        ),
        _row(
            "disturbance_and_initialization",
            meaning="declared plant has a separate physical disturbance channel, but the frozen reduced package adds its test disturbance through the control-input channel",
            implementation=[
                "paper/decoupling_marl_model_first/working/model_contract.md:57",
                "paper/decoupling_marl_model_first/working/model_contract.md:433",
                "src/andes_rl_kundur/env/andes/model_first_env.py:123",
                "src/andes_rl_kundur/env/andes/model_first_env.py:210",
                "scripts/run_r329_disturbance_estimator.py:427",
            ],
            official=[OFFICIAL_TDS, OFFICIAL_MANUAL],
            unit="physical PQ/load or outage disturbance versus system-p.u. actuator coordinate",
            base="separate physical device/event channel versus 100-MVA ESD1 command channel",
            sign="physical load sign is not identified by the frozen control-input model",
            sample_time="0.5-s unperturbed initialization; physical event after reset; one-sample observation delay",
            disposition="unsupported",
            ceiling="current R329 package cannot authorize a load-disturbance ANDES bridge",
        ),
        _row(
            "reduced_latent_state",
            meaning="ten realization states plus four random-walk unknown-input states kept only in estimator memory",
            implementation=[
                "src/andes_rl_kundur/control/model_first_disturbance_estimator.py:195",
                "memory/rounds/R329/disturbance_estimator_seal.json#/contract/estimator",
                "results/r316_dynamic_reduction/dynamic_model.json#/points",
            ],
            official=[OFFICIAL_TDS, OFFICIAL_MANUAL],
            unit="realization coordinates without direct physical units",
            base="input-output realization basis",
            sign="basis-dependent; only delivered output and node action have physical sign",
            sample_time="updated once per 0.2-s sample",
            disposition="derived",
            ceiling="latent coordinates are never described as direct ANDES state readbacks",
        ),
    ]
    if {str(row["id"]) for row in rows} != set(REQUIRED_MAPPING_IDS):
        raise RuntimeError("R331 mapping inventory differs from the validator")
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


def prepare(
    seal_path: Path,
    *,
    installed_identity: Mapping[str, object] | None = None,
) -> str:
    installed = dict(installed_identity or _installed_andes_identity())
    reconciliation = build_reconciliation(installed)
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "reconciliation": reconciliation,
        "reconciliation_payload_sha256": payload_sha256(reconciliation),
        "repository_sources": _repository_sources(),
        "installed_andes": installed,
        "official_sources": [
            OFFICIAL_MANUAL,
            OFFICIAL_TDS,
            OFFICIAL_SYNGEN,
            OFFICIAL_DG,
            OFFICIAL_PARAMETERS,
            OFFICIAL_GENCLS,
            OFFICIAL_ESD1,
            OFFICIAL_PVD1,
        ],
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
        raise RuntimeError("R331 seal, source, installation, or contract drift")
    return seal, digest


def _runtime_record() -> dict[str, str]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
    }


def analyse(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    *,
    installed_identity: Mapping[str, object] | None = None,
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
        raise RuntimeError("R331 analysis replay is not deterministic")
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
            "identify and validate a separate physical disturbance channel before "
            "any deterministic ANDES closed-loop bridge"
        ),
    }
    out_dir = out_dir.resolve()
    analysis_digest = write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
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
        "created_utc": datetime.now(UTC).isoformat(),
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
