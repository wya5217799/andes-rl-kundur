"""R478 corrected M/D revalidation — thin adapter over the frozen
deterministic bank runners.

Authority: revalidation plan
``paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md``
(Phase 1A / 1B / 1C) and ``memory/rounds/R478/plan.md``.

Adapter rule (non-negotiable): the parent sealed runners and every frozen
scientific function stay byte-identical. This adapter only

- re-keys the round id and output roots of the loaded parent module,
- records an adapter sidecar (parent source hash + patched globals),
- delegates each phase to the parent's own entry point,
- delegates zero-action scenario/execution/validity logic to the reusable probe,
- requires create-only seals plus owner approval bound to each seal hash.

Family table (family -> parent runner -> corrected output root):

    zero            (none; tracers.run_zero_action_trace)  r478_zero_action
    ninelaw         run_r416_headroom_expansion            r478_md_ninelaw
    schedule        run_r458_dev_select_eval_validate      r478_md_schedule
    port_unseen     run_r409_heldout_gate                  r478_port_unseen
    port_extra_k35  run_r415_energy_port_extra_banks       r478_port_extra_k35
    port_extra_k4   run_r417_energy_port_banks_k4          r478_port_extra_k4
    topology        run_r413_topology_robustness           r478_topology_variants

Physical phases are WSL-only and must run through the scratch launcher:

    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r478_md_revalidation.py <family> <command> [args...]

Every formal artifact is create-only with a ``.sha256`` sidecar. Parent
lineage keys inside inherited contracts (e.g. ``contract["r415"]``) are
true provenance and stay unchanged; the adapter identity is recorded in
the rekey sidecar instead of rewriting lineage.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# ─── Frozen parent source hashes (freeze-in 2026-08-24; fail-closed) ───

PARENT_SHA256 = {
    "run_r416_headroom_expansion.py":
        "16869b415df14e1942bd20ba0ff8d68558494846bc15c1dd3924a5685dd56a29",
    "run_r458_dev_select_eval_validate.py":
        "5be961a71defa2238cacf9685bf8875a1f9202d54d5134fce4b7f9d79ec883c8",
    "run_r409_heldout_gate.py":
        "14f012278c7f725566c7c6540b8bc5e81240be1f7cc70f31b1d022ea2da2f000",
    "run_r415_energy_port_extra_banks.py":
        "df84af97ef1bb0f94c42a4653ca05641ebd1ec414edae6d4dcc8bd17599f2dac",
    "run_r417_energy_port_banks_k4.py":
        "261046f49dda728982fa0015db9ffe1e3340b9944f5fded9cabbbb2c6ef7b7c5",
    "run_r413_topology_robustness.py":
        "2e1482d5250db64817654661cac18c6126b440eb6d84642ba93406d6fb6125f0",
}

FAMILIES: dict[str, dict[str, str | None]] = {
    "zero": {"parent": None, "out": "r478_zero_action"},
    "ninelaw": {"parent": "run_r416_headroom_expansion.py",
                "out": "r478_md_ninelaw"},
    "schedule": {"parent": "run_r458_dev_select_eval_validate.py",
                 "out": "r478_md_schedule"},
    "port_unseen": {"parent": "run_r409_heldout_gate.py",
                    "out": "r478_port_unseen"},
    "port_extra_k35": {"parent": "run_r415_energy_port_extra_banks.py",
                       "out": "r478_port_extra_k35"},
    "port_extra_k4": {"parent": "run_r417_energy_port_banks_k4.py",
                      "out": "r478_port_extra_k4"},
    "topology": {"parent": "run_r413_topology_robustness.py",
                 "out": "r478_topology_variants"},
}

ROUND_ID = "R478"
AUTHORITY_GENERATION = "repair4"
CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32
MARGINAL_GAIN_MIN = 1.05
MARGINAL_GAIN_CONFIRM_LOW = 1.03
MARGINAL_GAIN_CONFIRM_HIGH = 1.07
WORKER_RSS_FLOOR_BYTES = 944_214_016
OS_MEMORY_FLOOR_BYTES = 3 * 1024**3

# Parent CLI shapes differ: positional commands (R416/R458/R413/R415/R417)
# vs flags (R409). The adapter translates the uniform command vocabulary.
COMMAND_TRANSLATION: dict[str, dict[str, list[str]]] = {
    "port_unseen": {
        "execute": ["--execute"],
    },
}

FAMILY_COMMANDS: dict[str, frozenset[str]] = {
    "zero": frozenset({
        "contract", "measure-capacity", "rehearse", "prepare", "execute"
    }),
    "ninelaw": frozenset({"measure-capacity", "rehearse", "prepare",
                          "shards", "shard", "classify"}),
    "schedule": frozenset({"capacity", "rehearse", "prepare", "shard",
                           "select", "aggregate", "classify"}),
    "port_unseen": frozenset({
        "measure-capacity", "rehearse", "prepare", "execute"
    }),
    "port_extra_k35": frozenset({"measure-capacity", "rehearse", "prepare",
                                 "execute", "classify"}),
    "port_extra_k4": frozenset({"measure-capacity", "rehearse", "prepare",
                                "execute", "classify"}),
    "topology": frozenset({"inventory", "measure-capacity", "rehearse",
                           "prepare", "shards", "shard", "classify"}),
}

EXECUTION_COMMANDS: dict[str, frozenset[str]] = {
    "zero": frozenset({"execute"}),
    "ninelaw": frozenset({"shard", "classify"}),
    "schedule": frozenset({"shard", "select", "aggregate", "classify"}),
    "port_unseen": frozenset({"execute"}),
    "port_extra_k35": frozenset({"execute", "classify"}),
    "port_extra_k4": frozenset({"execute", "classify"}),
    "topology": frozenset({"shard", "classify"}),
}

OWNER_APPROVAL = ROOT / "memory/rounds/R478/formal_owner_approval.json"
PHYSICAL_EXECUTION_AUTHORIZATION = (
    ROOT / "memory/rounds/R478/physical_execution_authorization_repair4.json"
)
PHYSICAL_PREFORMAL_COMMANDS = frozenset(
    {"inventory", "measure-capacity", "capacity", "rehearse"}
)
ADAPTER_CAPACITY_COMMANDS = {
    "schedule": "capacity",
    "port_extra_k35": "measure-capacity",
    "port_extra_k4": "measure-capacity",
}


def _patched_authority(parent: Any, family: str) -> dict[str, bool]:
    """R478-keyed equivalent of the parent's authority gate.

    Identity re-key only: every scientific check delegates to the parent's
    own primitives; the round-id string is the R478 plan. Parent source
    files stay byte-identical (the override is recorded in the rekey sidecar).
    """
    plan_text = (ROOT / "memory/rounds/R478/plan.md").read_text(encoding="utf-8")
    line_text = (
        ROOT / "paper/yang_md_decoupling_marl/LINE.md"
    ).read_text(encoding="utf-8")
    checks = {
        "active_plan": (
            "state: active" in plan_text
            and "manuscript_line: yang-md-decoupling-marl" in plan_text
            and "R478" in plan_text
        ),
        "active_line": (
            "line_id: yang-md-decoupling-marl" in line_text
            and "status: active" in line_text
        ),
        "output_absence": not parent.OUT.exists(),
    }
    if family == "ninelaw":
        contract = parent._r399_contract()
        checks.update({
            "contract_shape": (
                len(contract["profiles"]) == 6 and int(contract["steps"]) == 30
            ),
            "candidates_frozen": (
                len(parent.extended_candidate_ids()) == 21
                and set(parent.original_nine_ids()).issubset(
                    set(parent.extended_candidate_ids())
                )
            ),
        })
    elif family == "schedule":
        checks.update({
            "candidate_contract": (
                len(parent.candidates()) == 350
                and parent.R452.candidate_sequence_sha256()
                == parent.R452.EXPECTED_CANDIDATE_SHA256
            ),
            "shard_contract": (
                len(parent.expected_dev_shard_ids()) == 34
                and len(parent.expected_eval_shard_ids()) == 8
            ),
        })
    elif family in ("port_extra_k35", "port_extra_k4", "topology"):
        contract = parent._base_contract()
        checks.update({
            "contract_shape": (
                len(contract["mode_ids"]) == 4
                and int(contract["device_count"]) == 4
                and int(contract["steps"]) == 50
            ),
        })
        if family == "topology":
            checks["variant_bank_frozen"] = (
                len(parent.TOPOLOGY_VARIANTS) == 12
                and parent.variant_ids()[0] == "nominal"
            )
        else:
            checks["banks_frozen"] = (
                len(parent.BLOCKS) == 3
                and parent.block_ids()[0] == "a4_conditions_b"
            )
    return checks


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_source_file(path: Path) -> str:
    """Hash Python source canonically across LF and CRLF checkouts."""
    source = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(source).hexdigest()


def _write_new_json(path: Path, payload: dict[str, Any]) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _read_hashed_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(f"missing artifact: {path}")
    digest = _sha256_file(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(f"missing hash sidecar: {sidecar}")
    recorded = sidecar.read_text(encoding="utf-8").split()[0]
    if recorded != digest:
        raise RuntimeError(f"artifact hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"artifact must contain a JSON object: {path}")
    return payload, digest


def _physical_authority_sources() -> dict[str, str]:
    """Return the exact non-physical sources an owner authorizes to simulate."""
    return {
        "runner": _sha256_source_file(Path(__file__).resolve()),
        "plan": _sha256_file(ROOT / "memory/rounds/R478/plan.md"),
        "parameter_card": _sha256_file(
            ROOT
            / "paper/yang_md_decoupling_marl/working/"
            "md_parameter_card_20260824.json"
        ),
    }


def _require_physical_authorization(family: str, command: str) -> None:
    """Fail closed unless a hashed owner artifact approves this physical phase."""
    payload, _digest = _read_hashed_json(PHYSICAL_EXECUTION_AUTHORIZATION)
    if (
        payload.get("round") != ROUND_ID
        or payload.get("authority_generation") != AUTHORITY_GENERATION
        or payload.get("physical_execution_authorized") is not True
    ):
        raise RuntimeError("physical execution authorization is absent or invalid")
    approved = (payload.get("approved_commands") or {}).get(family, [])
    if command not in approved:
        raise RuntimeError(
            f"physical authorization does not approve {family} {command}"
        )
    if payload.get("sources") != _physical_authority_sources():
        raise RuntimeError("physical authorization source binding drifted")


def _require_capacity_before_rehearsal(
    capacity_path: Path,
    *,
    current_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    capacity, _digest = _read_hashed_json(capacity_path)
    rows = list(capacity.get("rungs") or [])
    confirmation_rows = list(capacity.get("confirmation_pass_2") or [])

    def row_is_valid(row: Mapping[str, Any]) -> bool:
        job_count = row.get("job_count", row.get("jobs", 0))
        records_valid = row.get("all_records_valid", row.get("all_ok"))
        return int(job_count) == CAPACITY_TASKS_PER_RUNG and records_valid is True

    ladder_is_complete = (
        [int(row.get("workers", 0)) for row in rows] == list(CAPACITY_RUNGS)
        and all(row_is_valid(row) for row in [*rows, *confirmation_rows])
    )
    pre_attempt = capacity.get("pre_attempt") or {}
    post_attempt = capacity.get("post_attempt") or {}
    identity_stable = (
        capacity.get("identity_stable") is True
        and pre_attempt.get("sources") == post_attempt.get("sources")
        and pre_attempt.get("installed_runtime")
        == post_attempt.get("installed_runtime")
    )
    current_identity_matches = current_snapshot is None or (
        current_snapshot.get("sources") == post_attempt.get("sources")
        and current_snapshot.get("installed_runtime")
        == post_attempt.get("installed_runtime")
    )
    if (
        capacity.get("readiness") != "RUN-READY"
        or not ladder_is_complete
        or not identity_stable
        or not current_identity_matches
    ):
        raise RuntimeError("capacity is not RUN-READY before rehearsal")
    return capacity


def _bind_post_capacity_identity(
    payload: dict[str, Any],
    *,
    family: str,
    command: str,
    out_root: Path,
    parent_name: str | None,
    pre_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a completed ladder to one unchanged source/runtime identity."""
    post_attempt = _adapter_pre_attempt_snapshot(
        family=family,
        out_root=out_root,
        parent_name=parent_name,
    )
    _require_green_pre_attempt(post_attempt)
    _require_physical_authorization(family, command)
    if (
        pre_attempt.get("sources") != post_attempt.get("sources")
        or pre_attempt.get("installed_runtime")
        != post_attempt.get("installed_runtime")
    ):
        raise RuntimeError("capacity source/runtime identity drifted during ladder")
    payload.update(
        {
            "pre_attempt": dict(pre_attempt),
            "post_attempt": post_attempt,
            "identity_stable": True,
        }
    )
    return payload


def _payload_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _family_artifacts(family: str, out_root: Path) -> dict[str, Path]:
    stem = out_root.name
    round_dir = ROOT / "memory/rounds/R478"
    return {
        "contract": round_dir / f"contract_{stem}_{AUTHORITY_GENERATION}.json",
        "capacity": round_dir / f"capacity_{stem}_{AUTHORITY_GENERATION}.json",
        "rehearsal": round_dir / f"rehearsal_{stem}_{AUTHORITY_GENERATION}.json",
        "report": round_dir / f"report_{stem}_{AUTHORITY_GENERATION}.json",
        "seal": round_dir / f"formal_seal_{stem}_{AUTHORITY_GENERATION}.json",
    }


def _adapter_contract(family: str, parent: Any | None) -> dict[str, Any]:
    if family == "zero":
        return _zero_contract()
    if family == "port_unseen" and parent is not None:
        return dict(parent.build_contract())
    raise ValueError(f"adapter-native seal is not defined for {family}")


def _adapter_sources(
    family: str, parent_name: str | None
) -> dict[str, dict[str, str]]:
    sources = {
        "runner": {
            "path": "scripts/run_r478_md_revalidation.py",
            "sha256": _sha256_source_file(Path(__file__).resolve()),
        },
        "plan": {
            "path": "memory/rounds/R478/plan.md",
            "sha256": _sha256_file(ROOT / "memory/rounds/R478/plan.md"),
        },
        "parameter_card": {
            "path": (
                "paper/yang_md_decoupling_marl/working/"
                "md_parameter_card_20260824.json"
            ),
            "sha256": _sha256_file(
                ROOT
                / "paper/yang_md_decoupling_marl/working/"
                "md_parameter_card_20260824.json"
            ),
        },
    }
    if family == "zero":
        for name, relative in {
            "semantic_gate": "probes/r478_md_semantic_gate.py",
            "physical_probe": "src/andes_rl_kundur/probes/md_revalidation.py",
            "tracer": "src/andes_rl_kundur/probes/andes_common/tracers.py",
            "paper_constants": (
                "src/andes_rl_kundur/probes/andes_common/paper_constants.py"
            ),
            "v4_env": "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
            "base_env": "src/andes_rl_kundur/env/andes/base_env.py",
            "v4_config": "src/andes_rl_kundur/env/andes/v4_config.py",
            "md_convention": "src/andes_rl_kundur/env/andes/md_convention.py",
        }.items():
            path = ROOT / relative
            sources[name] = {
                "path": relative,
                "sha256": _sha256_source_file(path),
            }
    elif family == "port_unseen":
        for name, relative in {
            "r408_runner": "scripts/run_r408_v2_solving_gate.py",
            "r372_runner": "scripts/run_r372_energy_port_object_gate.py",
            "classifier": (
                "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py"
            ),
            "v4_env": "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
            "base_env": "src/andes_rl_kundur/env/andes/base_env.py",
            "md_convention": "src/andes_rl_kundur/env/andes/md_convention.py",
            "energy_port_env": (
                "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py"
            ),
        }.items():
            path = ROOT / relative
            sources[name] = {
                "path": relative,
                "sha256": _sha256_source_file(path),
            }
    if parent_name is not None:
        sources["parent_runner"] = {
            "path": f"scripts/{parent_name}",
            "sha256": PARENT_SHA256[parent_name],
        }
    return sources


def _installed_runtime() -> dict[str, str]:
    """Record the installed ANDES distribution and exact Kundur case identity."""
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    module_path = Path(andes.__file__).resolve()
    try:
        distribution_version = importlib.metadata.version("andes")
    except importlib.metadata.PackageNotFoundError:
        distribution_version = "unknown"
    return {
        "python": sys.version,
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_distribution_version": distribution_version,
        "andes_module_path": str(module_path),
        "andes_module_sha256": _sha256_file(module_path),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _loaded_scientific_sources() -> dict[str, dict[str, str]]:
    """Hash every loaded repository Python module used by the rehearsal."""
    sources: dict[str, dict[str, str]] = {}
    root = ROOT.resolve()
    for module in tuple(sys.modules.values()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if path.suffix != ".py" or not relative.startswith(
            ("src/andes_rl_kundur/", "scripts/", "probes/")
        ):
            continue
        sources[f"loaded:{relative}"] = {
            "path": relative,
            "sha256": _sha256_source_file(path),
        }
    return sources


def _source_manifest_valid(sources: Mapping[str, Mapping[str, str]]) -> bool:
    for entry in sources.values():
        path = ROOT / entry["path"]
        if not path.is_file():
            return False
        actual = (
            _sha256_source_file(path)
            if path.suffix == ".py"
            else _sha256_file(path)
        )
        if actual != entry["sha256"]:
            return False
    return True


def _adapter_pre_attempt_snapshot(
    *, family: str, out_root: Path, parent_name: str | None
) -> dict[str, Any]:
    """Run the shared rehearsal/formal-entry identity and absence checks."""
    sources = {
        **_adapter_sources(family, parent_name),
        **_loaded_scientific_sources(),
    }
    runtime = _installed_runtime()
    case_path = Path(runtime["case_path"])
    module_path = Path(runtime["andes_module_path"])
    parent_entry = sources.get("parent_runner")
    checks = {
        "source_hash": _source_manifest_valid(sources),
        "parent_hash": (
            parent_entry is None
            or parent_entry["sha256"]
            == PARENT_SHA256.get(parent_name or "")
        ),
        "installed_package": (
            runtime["andes_version"] != "unknown"
            and runtime["andes_distribution_version"] != "unknown"
            and module_path.is_file()
            and _sha256_file(module_path) == runtime["andes_module_sha256"]
        ),
        "installed_case": (
            case_path.is_file()
            and _sha256_file(case_path) == runtime["case_sha256"]
        ),
        "output_absence": not out_root.exists(),
    }
    return {
        "sources": sources,
        "installed_runtime": runtime,
        "checks": checks,
    }


def _require_green_pre_attempt(snapshot: Mapping[str, Any]) -> None:
    checks = snapshot.get("checks") or {}
    if not checks or not all(checks.values()):
        raise RuntimeError(f"adapter pre-attempt checks failed: {checks}")


def _prepare_adapter_seal(
    *, family: str, out_root: Path, parent: Any | None, parent_name: str | None
) -> str:
    artifacts = _family_artifacts(family, out_root)
    capacity, capacity_sha = _read_hashed_json(artifacts["capacity"])
    rehearsal, rehearsal_sha = _read_hashed_json(artifacts["rehearsal"])
    if capacity.get("all_ok") is not True:
        raise RuntimeError(f"{family} capacity did not pass")
    if rehearsal.get("rehearsal_ok") is not True:
        raise RuntimeError(f"{family} rehearsal did not pass")
    report_sha: str | None = None
    if family == "zero":
        report, report_sha = _read_hashed_json(artifacts["report"])
        if (
            report.get("gate") != "semantic_invariant"
            or report.get("validity") is not True
            or report.get("decision") != "retain old route"
            or report.get("next_gate") != "direct_md_canary_2a"
            or (report.get("output_hashes") or {}).get("rehearsal_sha256")
            != rehearsal_sha
        ):
            raise RuntimeError("zero semantic report does not authorize the next gate")
    pre_attempt = rehearsal.get("pre_attempt") or {}
    _require_green_pre_attempt(pre_attempt)
    sources = pre_attempt.get("sources") or {}
    if not _source_manifest_valid(sources):
        raise RuntimeError(f"{family} rehearsal source manifest drifted")
    if out_root.exists():
        raise FileExistsError(f"formal output root already exists: {out_root}")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "family": family,
        "formal_authority": True,
        "owner_approved": False,
        "contract_sha256": _payload_sha256(_adapter_contract(family, parent)),
        "capacity_sha256": capacity_sha,
        "rehearsal_sha256": rehearsal_sha,
        "sources": sources,
        "installed_runtime": pre_attempt["installed_runtime"],
    }
    if report_sha is not None:
        payload["report_sha256"] = report_sha
    return _write_new_json(artifacts["seal"], payload)


def _verify_adapter_seal(
    *, family: str, out_root: Path, parent: Any | None
) -> tuple[dict[str, Any], str]:
    artifacts = _family_artifacts(family, out_root)
    seal, seal_sha = _read_hashed_json(artifacts["seal"])
    if (
        seal.get("round") != ROUND_ID
        or seal.get("family") != family
        or seal.get("formal_authority") is not True
    ):
        raise RuntimeError(f"{family} seal authority mismatch")
    if seal.get("contract_sha256") != _payload_sha256(
        _adapter_contract(family, parent)
    ):
        raise RuntimeError(f"{family} contract drifted after seal")
    for entry in seal.get("sources", {}).values():
        path = ROOT / entry["path"]
        actual = (
            _sha256_source_file(path)
            if path.suffix == ".py"
            else _sha256_file(path)
        )
        if actual != entry["sha256"]:
            raise RuntimeError(f"{family} sealed source drift: {entry['path']}")
    if _installed_runtime() != seal.get("installed_runtime"):
        raise RuntimeError(f"{family} installed runtime or case drifted after seal")
    artifact_keys = ["capacity", "rehearsal"]
    if family == "zero":
        artifact_keys.append("report")
    for key in artifact_keys:
        if _read_hashed_json(artifacts[key])[1] != seal[f"{key}_sha256"]:
            raise RuntimeError(f"{family} {key} drifted after seal")
    return seal, seal_sha


def _require_owner_approval(family: str, seal_path: Path) -> None:
    _seal, seal_sha = _read_hashed_json(seal_path)
    approval, _approval_sha = _read_hashed_json(OWNER_APPROVAL)
    if approval.get("round") != ROUND_ID or approval.get("owner_approved") is not True:
        raise RuntimeError("formal owner approval is absent or invalid")
    if (approval.get("approved_seals") or {}).get(family) != seal_sha:
        raise RuntimeError(f"owner approval does not bind the {family} seal")


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Register the module so ProcessPoolExecutor workers can re-import (pickle)
    # functions defined inside the parent runner (capacity ladders fork pools).
    sys.modules[name] = module
    return module


def _verify_parent_source(name: str, path: Path) -> None:
    expected = PARENT_SHA256[name]
    actual = _sha256_source_file(path)
    if actual != expected:
        raise RuntimeError(
            f"frozen parent source drift: {name} "
            f"(expected {expected[:16]}..., got {actual[:16]}...)"
        )


def _rekey(parent: Any, family: str, out_root: Path) -> dict[str, Any]:
    """Patch parent module globals to the R478 identity; return the snapshot."""
    stem = out_root.name  # unique per family -> no cross-family path collisions
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    if hasattr(parent, "ROUND_ID"):
        before["ROUND_ID"] = parent.ROUND_ID
        parent.ROUND_ID = ROUND_ID
        after["ROUND_ID"] = parent.ROUND_ID
    for attr, rel in (
        ("OUT", f"results/research_loop/{stem}"),
        ("LINE", "paper/yang_md_decoupling_marl/LINE.md"),
        ("PLAN", "memory/rounds/R478/plan.md"),
        (
            "REHEARSAL",
            f"memory/rounds/R478/rehearsal_{stem}_{AUTHORITY_GENERATION}.json",
        ),
        (
            "CAPACITY",
            f"memory/rounds/R478/capacity_{stem}_{AUTHORITY_GENERATION}.json",
        ),
        (
            "SEAL",
            f"memory/rounds/R478/formal_seal_{stem}_{AUTHORITY_GENERATION}.json",
        ),
        (
            "DEV_SHARDS",
            f"tmp/andes/r478_{AUTHORITY_GENERATION}_{stem}_dev_shards.json",
        ),
        (
            "EVAL_SHARDS",
            f"tmp/andes/r478_{AUTHORITY_GENERATION}_{stem}_eval_shards.json",
        ),
    ):
        if hasattr(parent, attr):
            before[attr] = str(getattr(parent, attr))
            setattr(parent, attr, ROOT / rel)
            after[attr] = str(getattr(parent, attr))
    if hasattr(parent, "SELECTION"):
        before["SELECTION"] = str(parent.SELECTION)
        parent.SELECTION = parent.OUT / "selection.json"
        after["SELECTION"] = str(parent.SELECTION)
    return {"before": before, "after": after}


def _write_rekey_sidecar(
    *,
    family: str,
    command: str,
    command_args: tuple[str, ...],
    parent_name: str | None,
    parent_hash: str | None,
    snapshot: dict[str, Any],
    sidecar_dir: Path,
) -> Path:
    """Create-only per (family, command, args) identity sidecar.

    Re-dispatch with identical content is a no-op (needed for ``--resume``
    re-entry); a content mismatch is refused (fail-closed, no silent rekey).
    """
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    slug = "_".join(
        ["".join(ch if ch.isalnum() else "_" for ch in part) or "noargs"
         for part in (command, *command_args)]
    )
    adapter_sha = _sha256_source_file(Path(__file__).resolve())
    path = sidecar_dir / f"{family}_{slug}_{adapter_sha[:12]}.json"
    payload = {
        "adapter_round": ROUND_ID,
        "family": family,
        "command": command,
        "command_args": list(command_args),
        "parent_runner": parent_name,
        "parent_sha256": parent_hash,
        "adapter_sha256": adapter_sha,
        "rekey_snapshot": snapshot,
        "written_utc": datetime.now(UTC).isoformat(),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        # Drop the timestamp, which is the only field allowed to differ on a
        # byte-identical re-dispatch.
        existing_payload = json.loads(existing)
        existing_payload.pop("written_utc", None)
        payload.pop("written_utc", None)
        if existing_payload != payload:
            raise FileExistsError(f"rekey sidecar content mismatch: {path}")
        return path
    path.write_text(text, encoding="utf-8")
    return path


def _assert_wsl_scratch() -> None:
    """Physical phases are WSL-only and must run through the scratch launcher
    (ANDES writes kundur_full_out.* to cwd; the repo root must stay clean)."""
    if os.name != "posix":
        raise RuntimeError("physical phases are WSL/POSIX-only (ANDES runtime)")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("must run through scripts/andes_scratch.py")


def _memory_resources() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            values[parts[0].rstrip(":")] = int(parts[1]) * 1024
    return {
        "logical_processors": int(os.cpu_count() or 1),
        "memory_total_bytes": int(values["MemTotal"]),
        "memory_available_bytes": int(values["MemAvailable"]),
    }


def _other_research_processes() -> list[str]:
    lines = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return [
        line.strip()
        for line in lines
        if ("scripts/run_" in line or "soft_spot_shard_driver.py" in line)
        and "run_r478_md_revalidation.py" not in line
    ]


def _measure_capacity_rung(
    task: Callable[[int], Mapping[str, Any]], workers: int
) -> dict[str, Any]:
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        rows = list(executor.map(task, range(CAPACITY_TASKS_PER_RUNG)))
    wall_seconds = time.perf_counter() - started
    valid = all(
        bool(row.get("ok", row.get("completed", False)))
        and not bool(row.get("tds_failed", False))
        for row in rows
    )
    maximum_rss = max(
        (
            int(row.get("worker_max_rss_bytes", 0))
            for row in rows
        ),
        default=0,
    )
    return {
        "workers": workers,
        "native_threads_per_worker": 1,
        "wall_seconds": wall_seconds,
        "job_count": len(rows),
        "valid_completions": sum(
            bool(row.get("ok", row.get("completed", False)))
            and not bool(row.get("tds_failed", False))
            for row in rows
        ),
        "all_records_valid": bool(valid),
        "throughput_jobs_per_second": len(rows) / max(wall_seconds, 1e-12),
        "maximum_worker_rss_bytes": maximum_rss,
    }


def _capacity_ladder(
    *,
    task: Callable[[int], Mapping[str, Any]],
    family: str,
    memory_total_bytes: int,
) -> dict[str, Any]:
    """Measure the mandated 1/2/4/8/12/16 ladder with anti-noise replay."""
    first_pass = [_measure_capacity_rung(task, workers) for workers in CAPACITY_RUNGS]
    final = {
        workers: float(first_pass[index]["throughput_jobs_per_second"])
        for index, workers in enumerate(CAPACITY_RUNGS)
    }
    confirm_pairs: list[tuple[int, int]] = []
    for index in range(len(CAPACITY_RUNGS) - 1):
        low, high = CAPACITY_RUNGS[index:index + 2]
        gain = final[high] / max(final[low], 1e-12)
        if MARGINAL_GAIN_CONFIRM_LOW <= gain <= MARGINAL_GAIN_CONFIRM_HIGH:
            confirm_pairs.append((low, high))
    remeasure = sorted({workers for pair in confirm_pairs for workers in pair})
    second_pass = [_measure_capacity_rung(task, workers) for workers in remeasure]
    for index, workers in enumerate(remeasure):
        final[workers] = float(np.mean([
            final[workers],
            second_pass[index]["throughput_jobs_per_second"],
        ]))

    all_rows = [*first_pass, *second_pass]
    all_records_valid = all(
        row["job_count"] == CAPACITY_TASKS_PER_RUNG
        and row["all_records_valid"] is True
        for row in all_rows
    )
    selected: int | None = None
    selected_throughput: float | None = None
    accepting = True
    decisions: list[dict[str, Any]] = []
    for index, workers in enumerate(CAPACITY_RUNGS):
        measured_rss = max(
            int(first_pass[index]["maximum_worker_rss_bytes"]),
            WORKER_RSS_FLOOR_BYTES,
        )
        projected_memory = measured_rss * workers + OS_MEMORY_FLOOR_BYTES
        memory_safe = projected_memory <= memory_total_bytes
        gain = (
            None
            if selected_throughput is None
            else final[workers] / max(selected_throughput, 1e-12)
        )
        accepted = bool(
            accepting
            and first_pass[index]["all_records_valid"] is True
            and memory_safe
            and (gain is None or gain >= MARGINAL_GAIN_MIN)
        )
        if accepted:
            selected = workers
            selected_throughput = final[workers]
        else:
            accepting = False
        decisions.append({
            "workers": workers,
            "accepted": accepted,
            "marginal_gain": gain,
            "memory_safe": memory_safe,
            "projected_memory_bytes": projected_memory,
            "final_throughput_jobs_per_second": final[workers],
        })
    readiness = "RUN-READY" if selected is not None and all_records_valid else "HOLD"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "family": family,
        "stage": "representative_capacity_ladder_rungs_1_2_4_8_12_16",
        "jobs_per_rung": CAPACITY_TASKS_PER_RUNG,
        "rungs": first_pass,
        "confirmation_pairs": [
            {"low_workers": low, "high_workers": high}
            for low, high in confirm_pairs
        ],
        "confirmation_pass_2": second_pass,
        "final_throughput_jobs_per_second": final,
        "rung_decisions": decisions,
        "selected_workers": selected,
        "host_process_budget": None if selected is None else selected + 1,
        "wsl_python_processes": None if selected is None else selected + 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "memory_total_bytes": memory_total_bytes,
        "os_memory_floor_bytes": OS_MEMORY_FLOOR_BYTES,
        "worker_rss_floor_bytes": WORKER_RSS_FLOOR_BYTES,
        "readiness": readiness,
        "all_ok": readiness == "RUN-READY" and all_records_valid,
        "marginal_rule": (
            "next rung requires >=5% gain; gains in 3%-7% are remeasured "
            "once and averaged"
        ),
    }


def _zero_capacity_task(task_index: int) -> dict[str, Any]:
    import resource

    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.md_revalidation import (
        ZERO_SCENARIOS,
        run_zero_action_scenario,
    )

    scenario_id, delta_u = ZERO_SCENARIOS[task_index % len(ZERO_SCENARIOS)]
    run_zero_action_scenario(
        AndesMultiVSGEnvV4,
        scenario_id=scenario_id,
        delta_u=delta_u,
    )
    return {
        "ok": True,
        "tds_failed": False,
        "worker_max_rss_bytes": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ) * 1024,
    }


# ─── Family: zero (registered zero-action trace bank, Phase 1A/1C) ───

def _zero_contract() -> dict[str, Any]:
    from andes_rl_kundur.probes.md_revalidation import zero_contract

    return zero_contract(round_id=ROUND_ID)


def _zero_prepare(contract_path: Path) -> str:
    return _write_new_json(contract_path, _zero_contract())


def _zero_measure_capacity(
    contract_path: Path, capacity_path: Path, out_root: Path
) -> str:
    _assert_wsl_scratch()
    contract, _contract_sha = _read_hashed_json(contract_path)
    if contract != _zero_contract():
        raise RuntimeError("zero-action contract drifted before capacity")
    pre_attempt = _adapter_pre_attempt_snapshot(
        family="zero", out_root=out_root, parent_name=None
    )
    _require_green_pre_attempt(pre_attempt)
    other = _other_research_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    resources = _memory_resources()
    payload = _capacity_ladder(
        task=_zero_capacity_task,
        family="zero",
        memory_total_bytes=resources["memory_total_bytes"],
    )
    payload.update({
        "created_utc": datetime.now(UTC).isoformat(),
        "host": resources,
        "other_processes": other,
    })
    _bind_post_capacity_identity(
        payload,
        family="zero",
        command="measure-capacity",
        out_root=out_root,
        parent_name=None,
        pre_attempt=pre_attempt,
    )
    return _write_new_json(capacity_path, payload)


def _zero_rehearse(
    contract_path: Path,
    capacity_path: Path,
    rehearsal_path: Path,
    report_path: Path,
    out_root: Path,
) -> str:
    """Walk the zero family's same-pre-attempt path without writing records.

    Runs the complete semantic gate: both zero-action traces, the bounded
    nonzero five-substep target/readback check, and reset repeatability. It
    then writes the mandatory create-only report. No formal artifact is
    created (records.json remains exclusive to ``execute``).
    """
    _assert_wsl_scratch()
    contract, contract_sha = _read_hashed_json(contract_path)
    if contract != _zero_contract():
        raise RuntimeError("zero-action contract drifted before rehearsal")
    current_snapshot = _adapter_pre_attempt_snapshot(
        family="zero", out_root=out_root, parent_name=None
    )
    _require_green_pre_attempt(current_snapshot)
    capacity = _require_capacity_before_rehearsal(
        capacity_path, current_snapshot=current_snapshot
    )
    capacity_sha = _sha256_file(capacity_path)
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from probes.r478_md_semantic_gate import run_semantic_gate

    parameter_card = json.loads(
        (
            ROOT
            / "paper/yang_md_decoupling_marl/working/"
            "md_parameter_card_20260824.json"
        ).read_text(encoding="utf-8")
    )
    gate_result = run_semantic_gate(
        AndesMultiVSGEnvV4,
        parameter_card=parameter_card,
    )
    pre_attempt = _adapter_pre_attempt_snapshot(
        family="zero", out_root=out_root, parent_name=None
    )
    _require_green_pre_attempt(pre_attempt)
    passed = gate_result["classification"] == "SEMANTIC-GATE-PASS"
    rehearsal_sha = _write_new_json(
        rehearsal_path,
        {
            "round": ROUND_ID,
            "family": "zero",
            "rehearsal_ok": passed,
            "pre_attempt": pre_attempt,
            "checks": [
                "same-pre-attempt-path",
                "source-and-parent-hashes",
                "installed-package-and-case",
                "formal-output-absent",
                "two-zero-action-disturbances",
                "bounded-nonzero-five-substep-readback",
                "reset-repeatability",
            ],
            "gate_result": gate_result,
        },
    )
    _authorization, authorization_sha = _read_hashed_json(
        PHYSICAL_EXECUTION_AUTHORIZATION
    )
    report = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": "yang-md-decoupling-marl",
        "gate": "semantic_invariant",
        "validity": passed,
        "classification": gate_result["classification"],
        "input_hashes": {
            "contract_sha256": contract_sha,
            "capacity_sha256": capacity_sha,
            "physical_authorization_sha256": authorization_sha,
            "authorized_sources": _physical_authority_sources(),
        },
        "output_hashes": {"rehearsal_sha256": rehearsal_sha},
        "registered_metrics": gate_result,
        "old_yang_line_conclusion_comparison": (
            "corrected M/D semantics are operationally plausible; no old "
            "Yang-line numerical or paper conclusion is revalidated"
            if passed
            else "old Yang-line numerical conclusions cannot be transported "
            "to the corrected object"
        ),
        "decision": "retain old route" if passed else "redesign successor",
        "next_gate": (
            "direct_md_canary_2a" if passed else "stop_repair_md_semantics"
        ),
        "formal_evidence": False,
        "training_authorized": False,
        "capacity_selected_workers": capacity.get("selected_workers"),
    }
    return _write_new_json(report_path, report)


def _zero_execute(out_root: Path) -> str:
    _assert_wsl_scratch()
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.md_revalidation import run_zero_action_bank

    records = run_zero_action_bank(AndesMultiVSGEnvV4)
    out_root.mkdir(parents=True, exist_ok=False)
    return _write_new_json(out_root / "records.json", {"round": ROUND_ID,
                                                       "records": records})


def _port_unseen_preformal(
    *, command: str, parent: Any, out_root: Path, parent_name: str
) -> str:
    artifacts = _family_artifacts("port_unseen", out_root)
    if command == "measure-capacity":
        pre_attempt = _adapter_pre_attempt_snapshot(
            family="port_unseen", out_root=out_root, parent_name=parent_name
        )
        _require_green_pre_attempt(pre_attempt)
        other = _other_research_processes()
        if other:
            raise RuntimeError(
                f"other research Python processes are active: {other}"
            )
        resources = _memory_resources()
        payload = _capacity_ladder(
            task=parent._capacity_job,
            family="port_unseen",
            memory_total_bytes=resources["memory_total_bytes"],
        )
        payload.update({
            "created_utc": datetime.now(UTC).isoformat(),
            "host": resources,
            "other_processes": other,
        })
        _bind_post_capacity_identity(
            payload,
            family="port_unseen",
            command="measure-capacity",
            out_root=out_root,
            parent_name=parent_name,
            pre_attempt=pre_attempt,
        )
        return _write_new_json(artifacts["capacity"], payload)
    if command == "rehearse":
        current_snapshot = _adapter_pre_attempt_snapshot(
            family="port_unseen", out_root=out_root, parent_name=parent_name
        )
        _require_green_pre_attempt(current_snapshot)
        _require_capacity_before_rehearsal(
            artifacts["capacity"], current_snapshot=current_snapshot
        )
        payload = json.loads(parent.rehearse())
        scenario = payload.get("scenario") or {}
        pre_attempt = _adapter_pre_attempt_snapshot(
            family="port_unseen", out_root=out_root, parent_name=parent_name
        )
        _require_green_pre_attempt(pre_attempt)
        payload.update({
            "round": ROUND_ID,
            "family": "port_unseen",
            "pre_attempt": pre_attempt,
            "rehearsal_ok": (
                all(pre_attempt["checks"].values())
                and scenario.get("tds_failed") is False
                and scenario.get("identity_ok") is True
            ),
        })
        return _write_new_json(artifacts["rehearsal"], payload)
    if command == "prepare":
        return _prepare_adapter_seal(
            family="port_unseen",
            out_root=out_root,
            parent=parent,
            parent_name=parent_name,
        )
    raise ValueError(f"not a port_unseen preformal command: {command}")


def _parent_capacity_preformal(
    *, family: str, parent: Any, out_root: Path, parent_name: str
) -> str:
    """Apply the R478 capacity ladder to parents with obsolete capacity code."""
    _assert_wsl_scratch()
    pre_attempt = _adapter_pre_attempt_snapshot(
        family=family, out_root=out_root, parent_name=parent_name
    )
    _require_green_pre_attempt(pre_attempt)
    other = _other_research_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    resources = _memory_resources()
    task_name = "_capacity_job" if family == "schedule" else "_capacity_task"
    payload = _capacity_ladder(
        task=getattr(parent, task_name),
        family=family,
        memory_total_bytes=resources["memory_total_bytes"],
    )
    payload.update({
        "created_utc": datetime.now(UTC).isoformat(),
        "host": resources,
        "other_processes": other,
    })
    if family == "schedule":
        payload["authority"] = _patched_authority(parent, family)
    else:
        measured_selection = {
            "selected_workers": payload["selected_workers"],
            "host_process_budget": payload["host_process_budget"],
            "wsl_python_processes": payload["wsl_python_processes"],
        }
        # These two frozen parents execute serially.  The mandated ladder is
        # still measured, but the formal launch remains the one-process seam.
        payload.update({
            "measured_parallel_selection": measured_selection,
            "selected_workers": 0,
            "host_process_budget": 1,
            "whole_host_python_process_budget": 1,
            "wsl_python_processes": 1,
            "sources": parent._source_manifest(),
            "installed_runtime": parent._installed_runtime(),
            "formal_launch_mode": "frozen-parent-serial",
        })
    _bind_post_capacity_identity(
        payload,
        family=family,
        command=ADAPTER_CAPACITY_COMMANDS[family],
        out_root=out_root,
        parent_name=parent_name,
        pre_attempt=pre_attempt,
    )
    return _write_new_json(parent.CAPACITY, payload)


def _strict_schedule_analysis_payload(
    payload: Mapping[str, Any], parent: Any
) -> dict[str, Any]:
    """Require the unique development winner to pass every eval profile."""
    corrected = json.loads(json.dumps(payload))
    expected = tuple(str(profile) for profile in parent.EVAL_PROFILE_IDS)
    evaluation = corrected.get("evaluation") or {}
    clean_profiles = [
        profile
        for profile in expected
        if (
            profile in evaluation
            and (evaluation[profile].get("guards") or {}).get(
                "joint_guard_feasible"
            ) is True
        )
    ]
    all_clean = set(evaluation) == set(expected) and len(clean_profiles) == len(
        expected
    )
    integrity = corrected.get("integrity") or {}
    branch = int((corrected.get("selection") or {}).get("priority_branch", 3))
    if integrity.get("valid") is not True or integrity.get("errors"):
        verdict = "CANARY-INVALID"
    elif branch == 3:
        verdict = "FALLBACK-NO-WITNESS"
    elif all_clean:
        verdict = "GUARD-CLEAN-TRANSFER"
    else:
        verdict = "NO-GUARD-CLEAN-TRANSFER"
    corrected["classification"] = {
        "profiles_with_guard_clean_transfer": clean_profiles,
        "transfer_count": len(clean_profiles),
        "registered_profile_count": len(expected),
        "all_registered_profiles_guard_clean": all_clean,
        "verdict": verdict,
    }
    return corrected


def _install_schedule_aggregate_gate(parent: Any) -> None:
    """Patch only the adapter output boundary; the frozen parent stays intact."""
    original_write = parent._write_new_json
    analysis_path = parent.OUT / "formal_analysis.json"

    def strict_write(path: Path, payload: Mapping[str, Any]) -> str:
        if Path(path) == analysis_path:
            payload = _strict_schedule_analysis_payload(payload, parent)
        return str(original_write(path, payload))

    parent._write_new_json = strict_write


def _install_parent_rehearsal_overlay(
    *, parent: Any, family: str, out_root: Path, parent_name: str
) -> None:
    """Capture the physical rehearsal's actually loaded source/runtime set."""
    original_write = parent._write_new_json
    rehearsal_path = parent.REHEARSAL

    def overlay_write(path: Path, payload: Mapping[str, Any]) -> str:
        if Path(path) == rehearsal_path:
            payload = json.loads(json.dumps(payload))
            snapshot = _adapter_pre_attempt_snapshot(
                family=family, out_root=out_root, parent_name=parent_name
            )
            _require_green_pre_attempt(snapshot)
            payload["r478_pre_attempt"] = snapshot
        return str(original_write(path, payload))

    parent._write_new_json = overlay_write


def _install_parent_seal_overlay(parent: Any) -> None:
    """Bind rehearsal-loaded sources, runtime, plan, card, and adapter."""
    original_write = parent._write_new_json
    seal_path = parent.SEAL

    def overlay_write(path: Path, payload: Mapping[str, Any]) -> str:
        if Path(path) == seal_path:
            payload = json.loads(json.dumps(payload))
            rehearsal, _digest = _read_hashed_json(parent.REHEARSAL)
            snapshot = rehearsal.get("r478_pre_attempt") or {}
            _require_green_pre_attempt(snapshot)
            sources = snapshot.get("sources") or {}
            if not _source_manifest_valid(sources):
                raise RuntimeError("parent rehearsal source manifest drifted")
            sealed_sources = payload.setdefault("sources", {})
            for name, entry in sources.items():
                source_path = ROOT / entry["path"]
                sealed_sources[f"r478:{name}"] = {
                    "path": entry["path"],
                    # Frozen parent load_seal functions use raw file hashes.
                    "sha256": _sha256_file(source_path),
                }
            payload["r478_installed_runtime"] = snapshot["installed_runtime"]
        return str(original_write(path, payload))

    parent._write_new_json = overlay_write


def _verify_parent_overlay_seal(parent: Any) -> None:
    seal, _digest = _read_hashed_json(parent.SEAL)
    r478_sources = {
        name: entry
        for name, entry in (seal.get("sources") or {}).items()
        if name.startswith("r478:")
    }
    if not r478_sources:
        raise RuntimeError("parent seal is missing the R478 source overlay")
    for name, entry in r478_sources.items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"parent sealed source drift: {name}")
    if _installed_runtime() != seal.get("r478_installed_runtime"):
        raise RuntimeError("parent installed runtime or case drifted after seal")


# ─── Dispatcher ───

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=sorted(FAMILIES))
    parser.add_argument("command")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    family_cfg = FAMILIES[args.family]
    allowed = FAMILY_COMMANDS[args.family]
    if args.command not in allowed:
        raise SystemExit(
            f"{args.family} commands: {' | '.join(sorted(allowed))}"
        )
    out_root = ROOT / "results" / "research_loop" / str(family_cfg["out"])
    sidecar_dir = ROOT / "memory" / "rounds" / "R478" / "adapter_rekey"
    artifacts = _family_artifacts(args.family, out_root)
    if args.command in PHYSICAL_PREFORMAL_COMMANDS:
        _require_physical_authorization(args.family, args.command)

    if args.family == "zero":
        if args.command == "contract":
            print(f"R478 zero contract: {_zero_prepare(artifacts['contract'])}")
            return 0
        if args.command == "measure-capacity":
            print(
                "R478 zero capacity: "
                f"{_zero_measure_capacity(artifacts['contract'], artifacts['capacity'], out_root)}"
            )
            return 0
        if args.command == "rehearse":
            print(
                "R478 zero rehearsal: "
                f"{_zero_rehearse(artifacts['contract'], artifacts['capacity'], artifacts['rehearsal'], artifacts['report'], out_root)}"
            )
            return 0
        if args.command == "prepare":
            print(
                "R478 zero seal: "
                f"{_prepare_adapter_seal(family='zero', out_root=out_root, parent=None, parent_name=None)}"
            )
            return 0
        if args.command == "execute":
            _verify_adapter_seal(family="zero", out_root=out_root, parent=None)
            _require_green_pre_attempt(_adapter_pre_attempt_snapshot(
                family="zero", out_root=out_root, parent_name=None
            ))
            _require_owner_approval("zero", artifacts["seal"])
            print(f"R478 zero records: {_zero_execute(out_root)}")
            return 0
        raise AssertionError("unreachable zero command")

    parent_name = str(family_cfg["parent"])
    parent_path = ROOT / "scripts" / parent_name
    _verify_parent_source(parent_name, parent_path)
    parent = _load_module(f"_r478_{args.family}_parent", parent_path)
    snapshot = _rekey(parent, args.family, out_root)
    # Identity re-key: replace the parent's round-id-hardcoded authority gate
    # with an R478-keyed equivalent built from its own primitives.
    for _auth_name in ("authority_checks", "_authority_checks"):
        if hasattr(parent, _auth_name):
            family_name = args.family
            setattr(
                parent,
                _auth_name,
                lambda: _patched_authority(parent, family_name),
            )
    if args.command in EXECUTION_COMMANDS[args.family]:
        if args.family == "port_unseen":
            _verify_adapter_seal(
                family="port_unseen", out_root=out_root, parent=parent
            )
            if args.command == "execute":
                _require_green_pre_attempt(_adapter_pre_attempt_snapshot(
                    family="port_unseen",
                    out_root=out_root,
                    parent_name=parent_name,
                ))
        else:
            _verify_parent_overlay_seal(parent)
        seal_path = getattr(parent, "SEAL", artifacts["seal"])
        _require_owner_approval(args.family, seal_path)
    sidecar = _write_rekey_sidecar(
        family=args.family,
        command=args.command,
        command_args=tuple(args.args),
        parent_name=parent_name,
        parent_hash=PARENT_SHA256[parent_name],
        snapshot=snapshot,
        sidecar_dir=sidecar_dir,
    )
    print(f"R478 rekey sidecar: {sidecar}")

    if args.family == "port_unseen" and args.command in {
        "measure-capacity", "rehearse", "prepare"
    }:
        digest = _port_unseen_preformal(
            command=args.command,
            parent=parent,
            out_root=out_root,
            parent_name=parent_name,
        )
        print(f"R478 port_unseen {args.command}: {digest}")
        return 0

    if ADAPTER_CAPACITY_COMMANDS.get(args.family) == args.command:
        digest = _parent_capacity_preformal(
            family=args.family,
            parent=parent,
            out_root=out_root,
            parent_name=parent_name,
        )
        print(f"R478 {args.family} {args.command}: {digest}")
        return 0

    if args.family == "schedule" and args.command == "aggregate":
        _install_schedule_aggregate_gate(parent)
    if args.command == "rehearse":
        current_snapshot = _adapter_pre_attempt_snapshot(
            family=args.family,
            out_root=out_root,
            parent_name=parent_name,
        )
        _require_green_pre_attempt(current_snapshot)
        _require_capacity_before_rehearsal(
            parent.CAPACITY, current_snapshot=current_snapshot
        )
        _install_parent_rehearsal_overlay(
            parent=parent,
            family=args.family,
            out_root=out_root,
            parent_name=parent_name,
        )
    if args.command == "prepare":
        _install_parent_seal_overlay(parent)

    saved_argv = sys.argv
    try:
        translated = COMMAND_TRANSLATION.get(
            args.family, {}
        ).get(args.command, [args.command])
        sys.argv = [str(parent_path), *translated, *args.args]
        return int(parent.main())
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    raise SystemExit(main())
