"""R288 sealed topology-information value probe.

The module is import-safe without ANDES.  Simulator imports occur only inside
``prepare``/``run`` so the CLI contract and seal schema can be tested under
Windows.  Formal execution remains WSL-only.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT / "src", ROOT / "probes"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from andes_rl_kundur.evaluation.topology_information import (  # noqa: E402
    DEFAULT_THRESHOLDS,
    REQUIRED_CELL_GUARDS,
    allocation_library,
    analyze_eig_matrix,
    rank_topology_candidates,
    select_topology_variants,
)

ROUND_ID = "R288"
QUESTION_ID = "Q-0047"
TOPOLOGY_COUNT = 3
FORBIDDEN_LINES = {"Line_4", "Line_5", "Line_6", "Line_8"}
VSG_BUSES = {12, 14, 15, 16}
POSITIVE_REAL_TOLERANCE = 1e-7
PLAN = ROOT / "memory" / "rounds" / ROUND_ID / "plan.md"
R281_SUMMARY = ROOT / "results" / "r281_eig_mechanism" / "summary.json"
PURE_MODULE = ROOT / "src" / "andes_rl_kundur" / "evaluation" / "topology_information.py"
COMMON_MODULE = ROOT / "probes" / "eig_alloc_common.py"
ENV_SOURCE = (
    ROOT
    / "src"
    / "andes_rl_kundur"
    / "env"
    / "andes"
    / "andes_vsg_env_v4.py"
)
ADAPTER = ROOT / "scripts" / "run_r288_topology_information.py"
DEFAULT_INVENTORY_NAME = "topology_inventory.json"
DEFAULT_MATRIX_NAME = "eig_matrix.json"
DEFAULT_ANALYSIS_NAME = "analysis.json"
DEFAULT_PROVENANCE_NAME = "provenance.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_payload_sha256(payload: object) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _write_new_json(path: Path, payload: object) -> str:
    sidecar = path.with_name(f"{path.name}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"formal artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as handle:
        handle.write(data)
    with sidecar.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(path: Path, expected_sha256: str | None = None) -> tuple[dict, str]:
    sidecar = path.with_name(f"{path.name}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"artifact or sidecar missing: {path}")
    observed = sha256_file(path)
    recorded = sidecar.read_text(encoding="utf-8").split()[0].lower()
    if observed != recorded:
        raise RuntimeError(f"sidecar mismatch for {path}: {recorded} != {observed}")
    if expected_sha256 is not None and observed != expected_sha256.lower():
        raise RuntimeError(
            f"unexpected SHA-256 for {path}: expected {expected_sha256}, got {observed}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload, observed


def _source_entry(path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
    }


def _load_common():
    return importlib.import_module("eig_alloc_common")


def _field_values(group: Any, name: str, length: int) -> list[float | None]:
    field = getattr(group, name, None)
    values = getattr(field, "v", None)
    if values is None:
        return [None] * length
    return [float(value) for value in values]


def _line_rows(ss: Any) -> list[dict[str, Any]]:
    indices = list(ss.Line.idx.v)
    bus1 = list(ss.Line.bus1.v)
    bus2 = list(ss.Line.bus2.v)
    active = list(ss.Line.u.v)
    r_values = _field_values(ss.Line, "r", len(indices))
    x_values = _field_values(ss.Line, "x", len(indices))
    b_values = _field_values(ss.Line, "b", len(indices))
    b1_values = _field_values(ss.Line, "b1", len(indices))
    b2_values = _field_values(ss.Line, "b2", len(indices))
    return [
        {
            "idx": str(idx),
            "position": position,
            "bus1": int(bus1[position]),
            "bus2": int(bus2[position]),
            "active": bool(active[position]),
            "u": float(active[position]),
            "r": r_values[position],
            "x": x_values[position],
            "b": b_values[position],
            "b1": b1_values[position],
            "b2": b2_values[position],
        }
        for position, idx in enumerate(indices)
    ]


def _set_m_vector(ss: Any, vsg_pos: list[int], values: tuple[float, ...]) -> None:
    for position, machine_position in enumerate(vsg_pos):
        ss.GENCLS.M.v[machine_position] = float(values[position])


def _open_line(ss: Any, line_idx: str | None) -> tuple[list[str], list[float], list[float]]:
    indices = [str(value) for value in ss.Line.idx.v]
    before = [float(value) for value in ss.Line.u.v]
    if line_idx is not None:
        position = indices.index(line_idx)
        if before[position] != 1.0:
            raise RuntimeError(f"selected line is not active in the base plant: {line_idx}")
        ss.Line.u.v[position] = 0.0
    after = [float(value) for value in ss.Line.u.v]
    changed = [
        idx
        for idx, old, new in zip(indices, before, after, strict=True)
        if abs(old - new) > 1e-12
    ]
    return changed, before, after


def _plant_counts(ss: Any, vsg_pos: list[int]) -> dict[str, int]:
    return {
        "bus_count": len(ss.Bus.idx.v),
        "line_count": len(ss.Line.idx.v),
        "vsg_count": len(vsg_pos),
    }


def _g4_zeroed(ss: Any) -> bool:
    position = list(ss.GENROU.idx.v).index(4)
    return bool(
        abs(float(ss.GENROU.M.v[position]) - 0.1) < 1e-9
        and abs(float(ss.GENROU.D.v[position])) < 1e-9
    )


def _q0_pflow(common: Any, line_idx: str) -> dict[str, Any]:
    _, ss, vsg_pos = common.build_frozen_plant()
    _set_m_vector(ss, vsg_pos, allocation_library()["q0"])
    changed, _, _ = _open_line(ss, line_idx)
    converged = bool(ss.PFlow.run())
    return {
        "pflow_converged": converged,
        "opened_line_pass": changed == [line_idx],
        "g4_zeroed": _g4_zeroed(ss),
        "total_m_pass": abs(
            sum(float(ss.GENCLS.M.v[position]) for position in vsg_pos) - 1400.0
        )
        < 1e-6,
    }


def _r281_anchors(common: Any) -> dict[str, float]:
    source = json.loads(R281_SUMMARY.read_text(encoding="utf-8"))
    by_q: dict[float, float] = {}
    for row in source["main_sweep"]:
        q = float(row["q"])
        if not any(abs(q - target) < 1e-12 for target in (-0.25, 0.0, 0.25)):
            continue
        identified = common.identify_interarea(
            common.merge_conjugate_pairs(row["modes"])
        )
        if identified is None:
            raise RuntimeError(f"R281 anchor could not be identified at q={q}")
        by_q[q] = float(identified["damping_ratio"])
    if set(by_q) != {-0.25, 0.0, 0.25}:
        raise RuntimeError(f"R281 anchor set incomplete: {sorted(by_q)}")
    return {
        "q0": by_q[0.0],
        "h1_pos": by_q[0.25],
        "h1_neg": by_q[-0.25],
    }


def _seal_sources() -> dict[str, dict[str, str]]:
    return {
        "plan": _source_entry(PLAN),
        "adapter": _source_entry(ADAPTER),
        "probe": _source_entry(Path(__file__).resolve()),
        "pure_decision_module": _source_entry(PURE_MODULE),
        "eig_common": _source_entry(COMMON_MODULE),
        "environment": _source_entry(ENV_SOURCE),
        "r281_anchor_source": _source_entry(R281_SUMMARY),
    }


def _verify_sources(seal: dict[str, Any]) -> None:
    for name, entry in seal["sources"].items():
        path = ROOT / entry["path"]
        observed = sha256_file(path)
        if observed != entry["sha256"]:
            raise RuntimeError(
                f"sealed source drift for {name}: {entry['sha256']} != {observed}"
            )


def prepare(seal_path: Path, out_dir: Path) -> None:
    """Perform Stage A only and freeze the selected topology variants."""

    seal_path = seal_path.resolve()
    out_dir = out_dir.resolve()
    inventory_path = out_dir / DEFAULT_INVENTORY_NAME
    if seal_path.exists() or inventory_path.exists():
        raise FileExistsError("R288 prepare artifacts already exist; refusing overwrite")

    common = _load_common()
    _, ss, vsg_pos = common.build_frozen_plant()
    lines = _line_rows(ss)
    structural_inventory = rank_topology_candidates(
        lines,
        forbidden_line_ids=FORBIDDEN_LINES,
        vsg_buses=VSG_BUSES,
    )
    structural_candidates = sorted(
        (row for row in structural_inventory if row["structural_eligible"]),
        key=lambda row: int(row["structural_rank"]),
    )
    pflow_checks = {
        row["idx"]: _q0_pflow(common, row["idx"]) for row in structural_candidates
    }
    pflow_pass = {
        idx: bool(
            result["pflow_converged"]
            and result["opened_line_pass"]
            and result["g4_zeroed"]
            and result["total_m_pass"]
        )
        for idx, result in pflow_checks.items()
    }
    selection = select_topology_variants(
        lines,
        pflow_pass=pflow_pass,
        forbidden_line_ids=FORBIDDEN_LINES,
        vsg_buses=VSG_BUSES,
        count=TOPOLOGY_COUNT,
        require_count=False,
    )
    for row in selection["inventory"]:
        if row["idx"] in pflow_checks:
            row["q0_pflow_check"] = pflow_checks[row["idx"]]

    counts = _plant_counts(ss, vsg_pos)
    inventory = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "pre-EIG topology selection",
        "created_utc": datetime.now(UTC).isoformat(),
        "base_plant_counts": counts,
        "selection_status": (
            "COMPLETE" if selection["selection_complete"] else "STRUCTURALLY-INFEASIBLE"
        ),
        "requested_topology_count": TOPOLOGY_COUNT,
        "selection_contract": {
            "forbidden_lines": sorted(FORBIDDEN_LINES),
            "vsg_buses": sorted(VSG_BUSES),
            "exclude_parallel_endpoint_groups": True,
            "exclude_disconnecting_edges": True,
            "rank": ["distance_impact desc", "abs(x) desc", "line idx asc"],
            "selection": "endpoint-disjoint first, then structural-rank fill",
            "q0_pflow_before_eig": True,
        },
        "selected": selection["selected"],
        "lines": selection["inventory"],
        "sources": _seal_sources(),
    }
    inventory_digest = _write_new_json(inventory_path, inventory)
    if not selection["selection_complete"]:
        print(f"inventory_sha256={inventory_digest}", flush=True)
        print(
            f"selection_status=STRUCTURALLY-INFEASIBLE "
            f"selected={len(selection['selected'])}/{TOPOLOGY_COUNT}",
            flush=True,
        )
        raise RuntimeError(
            "no R288 seal written: the frozen structural screen cannot supply "
            f"{TOPOLOGY_COUNT} eligible topology variants"
        )

    selected_rows = {
        row["idx"]: row for row in selection["inventory"] if row["selected"]
    }
    topologies = [{"name": "nominal", "opened_line": None}]
    topologies.extend(
        {
            "name": f"topology_{position}",
            "opened_line": line_idx,
            "line": {
                key: selected_rows[line_idx][key]
                for key in ("idx", "position", "bus1", "bus2", "r", "x", "b", "b1", "b2")
            },
        }
        for position, line_idx in enumerate(selection["selected"], start=1)
    )
    contract = {
        "topologies": topologies,
        "allocations": {key: list(values) for key, values in allocation_library().items()},
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "positive_real_tolerance": POSITIVE_REAL_TOLERANCE,
        "required_cell_guards": list(REQUIRED_CELL_GUARDS),
        "mode_rule": {
            "frequency_band_hz": [0.2, 1.5],
            "conjugate_merge": True,
            "pick": "max abs(P_area1-P_area2)",
        },
        "nominal_anchors": _r281_anchors(common),
        "anchor_mapping": {
            "q0": "R281 q=0",
            "h1_pos": "R281 q=+0.25",
            "h1_neg": "R281 q=-0.25",
        },
        "matrix_shape": [4, 7],
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "topology_inventory": {
            "path": inventory_path.relative_to(ROOT).as_posix(),
            "sha256": inventory_digest,
        },
        "contract": contract,
        "contract_payload_sha256": _canonical_payload_sha256(contract),
        "sources": _seal_sources(),
        "asset_protection": {
            "no_training": True,
            "no_time_domain": True,
            "no_gnn": True,
            "no_manuscript_write": True,
            "formal_artifacts_are_create_only": True,
        },
    }
    seal_digest = _write_new_json(seal_path, seal)
    print(f"inventory_sha256={inventory_digest}", flush=True)
    print(f"seal_sha256={seal_digest}", flush=True)
    print(f"selected={selection['selected']}", flush=True)


def _load_seal(seal_path: Path, expected_sha256: str) -> tuple[dict, str]:
    seal, seal_digest = _read_verified_json(seal_path.resolve(), expected_sha256)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("seal round/question identity mismatch")
    if _canonical_payload_sha256(seal["contract"]) != seal["contract_payload_sha256"]:
        raise RuntimeError("seal contract payload hash mismatch")
    _verify_sources(seal)
    inventory_entry = seal["topology_inventory"]
    _read_verified_json(
        ROOT / inventory_entry["path"],
        inventory_entry["sha256"],
    )
    return seal, seal_digest


def _eig_cell(
    common: Any,
    *,
    topology: dict[str, Any],
    allocation_name: str,
    m_vector: tuple[float, ...],
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    _, ss, vsg_pos = common.build_frozen_plant()
    counts = _plant_counts(ss, vsg_pos)
    _set_m_vector(ss, vsg_pos, m_vector)
    opened_line = topology["opened_line"]
    changed, before, after = _open_line(ss, opened_line)
    expected_changed = [] if opened_line is None else [opened_line]
    indices = [str(value) for value in ss.Line.idx.v]
    status_detail = {
        "changed_lines": changed,
        "opened_line": opened_line,
        "opened_line_before": (
            None if opened_line is None else before[indices.index(opened_line)]
        ),
        "opened_line_after": (
            None if opened_line is None else after[indices.index(opened_line)]
        ),
    }
    guards = {
        "pflow_converged": False,
        "g4_zeroed": _g4_zeroed(ss),
        "total_m_pass": abs(sum(m_vector) - 1400.0) < 1e-6,
        "opened_line_pass": changed == expected_changed,
        "bus_count_pass": counts["bus_count"] == expected_counts["bus_count"],
        "vsg_count_pass": counts["vsg_count"] == expected_counts["vsg_count"],
        "positive_real_stable": False,
    }
    identified = None
    modes: list[dict[str, Any]] = []
    eigenvalue_audit = {
        "finite": False,
        "positive_real_count": None,
        "max_real": None,
        "tolerance": POSITIVE_REAL_TOLERANCE,
    }
    pflow_ok = bool(ss.PFlow.run())
    guards["pflow_converged"] = pflow_ok
    if pflow_ok:
        ss.EIG.run()
        ss.EIG.calc_pfactor()
        eigenvalues = np.asarray(ss.EIG.mu)
        real = np.real(eigenvalues)
        imag = np.imag(eigenvalues)
        finite = bool(np.all(np.isfinite(real)) and np.all(np.isfinite(imag)))
        positive_count = int(np.count_nonzero(real > POSITIVE_REAL_TOLERANCE))
        eigenvalue_audit = {
            "finite": finite,
            "positive_real_count": positive_count,
            "max_real": float(np.max(real)),
            "tolerance": POSITIVE_REAL_TOLERANCE,
        }
        guards["positive_real_stable"] = bool(finite and positive_count == 0)
        pfactors = np.abs(np.asarray(ss.EIG.pfactors))
        machine_states = common.machine_state_indices(ss, vsg_pos, None)
        for mode_index, eigenvalue in enumerate(eigenvalues):
            if eigenvalue.real >= 0:
                continue
            frequency = abs(eigenvalue.imag) / (2 * np.pi)
            if not (common.F_BAND[0] <= frequency <= common.F_BAND[1]):
                continue
            modes.append(
                {
                    "freq_hz": float(frequency),
                    "damping_ratio": float(-eigenvalue.real / abs(eigenvalue)),
                    "real": float(eigenvalue.real),
                    "p_machines": {
                        key: float(pfactors[state_index, mode_index])
                        for key, state_index in machine_states.items()
                    },
                }
            )
        modes = common.merge_conjugate_pairs(modes)
        identified = common.identify_interarea(modes)

    return {
        "topology": topology["name"],
        "opened_line": opened_line,
        "allocation": allocation_name,
        "m_vector": list(m_vector),
        "guards": guards,
        "status_detail": status_detail,
        "eigenvalue_audit": eigenvalue_audit,
        "identified": identified,
        "n_modes_merged": len(modes),
    }


def run(seal_path: Path, expected_seal_sha256: str, out_dir: Path) -> None:
    """Execute the sealed 4x7 EIG matrix and write it once."""

    seal, seal_digest = _load_seal(seal_path, expected_seal_sha256)
    out_dir = out_dir.resolve()
    matrix_path = out_dir / DEFAULT_MATRIX_NAME
    if matrix_path.exists() or matrix_path.with_name(f"{matrix_path.name}.sha256").exists():
        raise FileExistsError(f"formal matrix already exists: {matrix_path}")
    inventory, inventory_digest = _read_verified_json(
        ROOT / seal["topology_inventory"]["path"],
        seal["topology_inventory"]["sha256"],
    )
    common = _load_common()
    contract = seal["contract"]
    cells = []
    for topology in contract["topologies"]:
        for allocation_name, values in contract["allocations"].items():
            cell = _eig_cell(
                common,
                topology=topology,
                allocation_name=allocation_name,
                m_vector=tuple(float(value) for value in values),
                expected_counts=inventory["base_plant_counts"],
            )
            cells.append(cell)
            print(
                f"{topology['name']}/{allocation_name}: "
                f"pflow={cell['guards']['pflow_converged']} "
                f"stable={cell['guards']['positive_real_stable']} "
                f"identified={cell['identified'] is not None}",
                flush=True,
            )
    try:
        andes_version = importlib.import_module("andes").__version__
    except (AttributeError, ImportError):
        andes_version = "unknown"
    matrix = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "inventory_sha256": inventory_digest,
        "topologies": [item["name"] for item in contract["topologies"]],
        "allocations": list(contract["allocations"]),
        "cells": cells,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "andes": andes_version,
        },
    }
    digest = _write_new_json(matrix_path, matrix)
    print(f"matrix_sha256={digest}", flush=True)


def analyse(seal_path: Path, expected_seal_sha256: str, out_dir: Path) -> None:
    """Verify the formal matrix and apply the frozen pure decision gate."""

    seal, seal_digest = _load_seal(seal_path, expected_seal_sha256)
    out_dir = out_dir.resolve()
    matrix_path = out_dir / DEFAULT_MATRIX_NAME
    matrix, matrix_digest = _read_verified_json(matrix_path)
    if matrix.get("seal_sha256") != seal_digest:
        raise RuntimeError("matrix was not produced under the expected seal")
    if matrix.get("round") != ROUND_ID or matrix.get("question") != QUESTION_ID:
        raise RuntimeError("matrix round/question identity mismatch")

    result = analyze_eig_matrix(
        matrix,
        nominal_anchors=seal["contract"]["nominal_anchors"],
        thresholds=seal["contract"]["thresholds"],
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "matrix_sha256": matrix_digest,
        **result,
    }
    analysis_path = out_dir / DEFAULT_ANALYSIS_NAME
    analysis_digest = _write_new_json(analysis_path, analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {
            "path": seal_path.resolve().relative_to(ROOT).as_posix(),
            "sha256": seal_digest,
        },
        "matrix": {
            "path": matrix_path.relative_to(ROOT).as_posix(),
            "sha256": matrix_digest,
        },
        "analysis": {
            "path": analysis_path.relative_to(ROOT).as_posix(),
            "sha256": analysis_digest,
        },
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
    }
    provenance_digest = _write_new_json(
        out_dir / DEFAULT_PROVENANCE_NAME,
        provenance,
    )
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)
