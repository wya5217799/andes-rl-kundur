"""Export the sealed R339 descriptor extraction as a portable bridge bundle.

This is an offline engineering adapter.  It reads the create-only R339 JSON
artifacts, performs deterministic Schur reduction and ZOH discretization, and
writes a self-checking bundle.  It never imports ANDES, runs a controller,
changes a research ledger, or treats the derived files as new evidence.

Usage::

    python -m andes_rl_kundur.evaluation.full_order_bridge_bundle build \
        --output tmp/decoupling_marl_model_first/full_order_bridge_bundle
    python -m andes_rl_kundur.evaluation.full_order_bridge_bundle verify \
        --bundle tmp/decoupling_marl_model_first/full_order_bridge_bundle

The command fails rather than overwriting an existing output directory.  A
missing optional diagnostic archive is recorded as ``MISSING`` and is never
replaced with another model or operating point.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.signal import cont2discrete

from andes_rl_kundur.env.andes.model_first_contract import stage1_power_coordinates
from andes_rl_kundur.evaluation.model_first_input_bridge import (
    fold_zero_time_constant_states,
    reduce_folded_descriptor,
)

SAMPLE_PERIOD_SECONDS = 0.2
POINT_NAMES = ("HS0", "HS1")
CONTROL_COORDINATE_NAMES = ("common", "edge_0", "edge_1", "edge_2")
LOAD_DEVICE_NAMES = ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
LOAD_BUS_NAMES = ("Bus7", "Bus8", "Bus14", "Bus15")
OUTPUT_COORDINATE_NAMES = (
    "weighted_common",
    "differential_0",
    "differential_1",
    "differential_2",
)
SOURCE_EXECUTION = Path("results/r339_input_bridge_diagnosis/execution.json")
SOURCE_ANALYSIS = Path("results/r339_input_bridge_diagnosis/analysis.json")
SOURCE_PROVENANCE = Path("results/r339_input_bridge_diagnosis/provenance.json")
SOURCE_REPORT = Path("paper/decoupling_marl_model_first/reports/R339.md")
SOURCE_EXPORTER = Path("src/andes_rl_kundur/evaluation/full_order_bridge_bundle.py")
SOURCE_BRIDGE_IMPLEMENTATION = Path("src/andes_rl_kundur/evaluation/model_first_input_bridge.py")


@dataclass(frozen=True)
class PointModel:
    point: str
    base: dict[str, Any]
    control: dict[str, Any]
    load: dict[str, Any]
    node_basis: np.ndarray
    dynamic_indices: np.ndarray
    folded_indices: np.ndarray
    a_c: np.ndarray
    bu_node_c: np.ndarray
    bu_coord_c: np.ndarray
    bd_load_c: np.ndarray
    c_omega_c: np.ndarray
    c_coord_c: np.ndarray
    ad: np.ndarray
    bu_node_d: np.ndarray
    bu_coord_d: np.ndarray
    bd_load_d: np.ndarray


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matrix(value: object) -> np.ndarray:
    return np.asarray(value, dtype=float)


def _node_basis() -> np.ndarray:
    coordinates = stage1_power_coordinates(1.0)
    return np.column_stack([coordinates[name] for name in CONTROL_COORDINATE_NAMES])


def _selected_derivatives(family: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    steps = family.get("steps", [])
    if [float(row["step_system_pu"]) for row in steps] != [1e-4, 1e-5, 1e-6]:
        raise ValueError("R339 derivative scales or order drifted")
    return _matrix(steps[-1]["f_input"]), _matrix(steps[-1]["g_input"])


def _construct_point(point: dict[str, Any]) -> PointModel:
    base = dict(point["base_snapshot"])
    control = dict(point["control_input_derivatives"])
    load = dict(point["load_input_derivatives"])
    control_f, control_g = _selected_derivatives(control)
    load_f, load_g = _selected_derivatives(load)
    f_input = np.hstack([control_f, load_f])
    g_input = np.hstack([control_g, load_g])
    folded = fold_zero_time_constant_states(
        time_constants=base["Tf"],
        f_x=base["f_x"],
        f_y=base["f_y"],
        g_x=base["g_x"],
        g_y=base["g_y"],
        f_input=f_input,
        g_input=g_input,
    )
    reduced = reduce_folded_descriptor(folded, minimum_reciprocal_condition=1e-12)
    node_basis = _node_basis()
    bu_node_c = reduced.input_matrix[:, :4]
    bu_coord_c = bu_node_c @ node_basis
    bd_load_c = reduced.input_matrix[:, 4:]

    state_count = len(base["x"])
    c_omega_raw = np.zeros((4, state_count), dtype=float)
    for row, address in enumerate(base["omega_state_addresses"]):
        c_omega_raw[row, int(address)] = 1.0
    c_coord_raw = _matrix(base["output_map"])
    if np.linalg.norm(c_omega_raw[:, folded.folded_state_indices]) != 0.0:
        raise ValueError("physical omega output depends on a folded state")
    if np.linalg.norm(c_coord_raw[:, folded.folded_state_indices]) != 0.0:
        raise ValueError("coordinate output depends on a folded state")
    c_omega_c = c_omega_raw[:, folded.dynamic_state_indices]
    c_coord_c = c_coord_raw[:, folded.dynamic_state_indices]

    b_all_c = np.hstack([bu_node_c, bd_load_c])
    d_zero = np.zeros((4, 8), dtype=float)
    ad, b_all_d, _, _, _ = cont2discrete(
        (reduced.state_matrix, b_all_c, c_omega_c, d_zero),
        SAMPLE_PERIOD_SECONDS,
        method="zoh",
    )
    bu_node_d = np.asarray(b_all_d[:, :4], dtype=float)
    bd_load_d = np.asarray(b_all_d[:, 4:], dtype=float)
    return PointModel(
        point=str(point["point"]),
        base=base,
        control=control,
        load=load,
        node_basis=node_basis,
        dynamic_indices=folded.dynamic_state_indices,
        folded_indices=folded.folded_state_indices,
        a_c=reduced.state_matrix,
        bu_node_c=bu_node_c,
        bu_coord_c=bu_coord_c,
        bd_load_c=bd_load_c,
        c_omega_c=c_omega_c,
        c_coord_c=c_coord_c,
        ad=np.asarray(ad, dtype=float),
        bu_node_d=bu_node_d,
        bu_coord_d=bu_node_d @ node_basis,
        bd_load_d=bd_load_d,
    )


def _save_equilibrium(path: Path, model: PointModel) -> None:
    base = model.base
    x0 = _matrix(base["x"])
    y0 = _matrix(base["y"])
    u0_node = _matrix(model.control["equilibrium_input_system_pu"])
    d0_load = _matrix(model.load["equilibrium_input_system_pu"])
    omega_addresses = np.asarray(base["omega_state_addresses"], dtype=int)
    output0_omega = x0[omega_addresses]
    output0_coord = _matrix(base["coordinate_forward"]) @ output0_omega
    np.savez_compressed(
        path,
        x0=x0,
        y0=y0,
        z0=_matrix(base.get("z", [])),
        u0_node=u0_node,
        u0_coord=np.linalg.solve(model.node_basis, u0_node),
        d0_load=d0_load,
        output0_omega4=output0_omega,
        output0_coord4=output0_coord,
        omega_state_addresses=omega_addresses,
        coordinate_forward=_matrix(base["coordinate_forward"]),
        coordinate_inverse=_matrix(base["coordinate_inverse"]),
        node_to_coord=np.linalg.inv(model.node_basis),
        coord_to_node=model.node_basis,
        operating_point_json=np.asarray(json.dumps(base["operating_point"], sort_keys=True)),
        structural_contract_json=np.asarray(
            json.dumps(base["structural_contract"], sort_keys=True)
        ),
        system_base_mva=np.asarray(100.0),
        frequency_base_hz=np.asarray(60.0),
    )


def _save_jacobians(path: Path, model: PointModel) -> None:
    base = model.base
    state_count = len(base["x"])
    algebraic_count = len(base["y"])
    c_omega = np.zeros((4, state_count), dtype=float)
    for row, address in enumerate(base["omega_state_addresses"]):
        c_omega[row, int(address)] = 1.0
    c_coord = _matrix(base["output_map"])
    control_steps = model.control["steps"]
    load_steps = model.load["steps"]
    zeros_y = np.zeros((4, algebraic_count), dtype=float)
    zeros_direct = np.zeros((4, 4), dtype=float)
    np.savez_compressed(
        path,
        E=np.diag(_matrix(base["Tf"])),
        Fx=_matrix(base["f_x"]),
        Fy=_matrix(base["f_y"]),
        Gx=_matrix(base["g_x"]),
        Gy=_matrix(base["g_y"]),
        Bx_u_node=_matrix(control_steps[-1]["f_input"]),
        Hy_u_node=_matrix(control_steps[-1]["g_input"]),
        Bx_d_load=_matrix(load_steps[-1]["f_input"]),
        Hy_d_load=_matrix(load_steps[-1]["g_input"]),
        Bx_u_node_scales=np.asarray([row["f_input"] for row in control_steps]),
        Hy_u_node_scales=np.asarray([row["g_input"] for row in control_steps]),
        Bx_d_load_scales=np.asarray([row["f_input"] for row in load_steps]),
        Hy_d_load_scales=np.asarray([row["g_input"] for row in load_steps]),
        finite_difference_steps=np.asarray([row["step_system_pu"] for row in control_steps]),
        Cx_omega4=c_omega,
        Cy_omega4=zeros_y,
        Ju_omega4=zeros_direct,
        Jd_omega4=zeros_direct,
        Cx_coord4=c_coord,
        Cy_coord4=zeros_y,
        Ju_coord4=zeros_direct,
        Jd_coord4=zeros_direct,
    )


def _continuous_payload(model: PointModel) -> dict[str, np.ndarray]:
    zeros = np.zeros((4, 4), dtype=float)
    return {
        "A_c": model.a_c,
        "Bu_node_c": model.bu_node_c,
        "Bu_coord_c": model.bu_coord_c,
        "Bd_load_c": model.bd_load_c,
        "C_omega4_c": model.c_omega_c,
        "Du_node_omega4_c": zeros,
        "Du_coord_omega4_c": zeros,
        "Dd_load_omega4_c": zeros,
        "C_coord4_c": model.c_coord_c,
        "Du_node_coord4_c": zeros,
        "Du_coord_coord4_c": zeros,
        "Dd_load_coord4_c": zeros,
    }


def _discrete_payload(model: PointModel) -> dict[str, np.ndarray]:
    zeros = np.zeros((4, 4), dtype=float)
    c_omega_post = model.c_omega_c @ model.ad
    c_coord_post = model.c_coord_c @ model.ad
    return {
        "A_d": model.ad,
        "Bu_node_d": model.bu_node_d,
        "Bu_coord_d": model.bu_coord_d,
        "Bd_load_d": model.bd_load_d,
        "C_omega4_d": c_omega_post,
        "Du_node_omega4_d": model.c_omega_c @ model.bu_node_d,
        "Du_coord_omega4_d": model.c_omega_c @ model.bu_coord_d,
        "Dd_load_omega4_d": model.c_omega_c @ model.bd_load_d,
        "C_coord4_d": c_coord_post,
        "Du_node_coord4_d": model.c_coord_c @ model.bu_node_d,
        "Du_coord_coord4_d": model.c_coord_c @ model.bu_coord_d,
        "Dd_load_coord4_d": model.c_coord_c @ model.bd_load_d,
        "C_omega4_pre_d": model.c_omega_c,
        "C_coord4_pre_d": model.c_coord_c,
        "D_pre_d": zeros,
        "Ts": np.asarray(SAMPLE_PERIOD_SECONDS),
        "discretization_method": np.asarray("zero-order hold (scipy.signal.cont2discrete)"),
        "observation_convention": np.asarray("end-of-held-interval/post-step"),
    }


def _catalog_entry(index: int, name: str, category: str) -> dict[str, object]:
    tokens = name.split()
    model = tokens[1] if len(tokens) > 1 else "MISSING"
    unit = "per-unit speed" if name.lower().startswith("omega ") else "MISSING"
    return {
        "index": index,
        "name": name,
        "device/model": model,
        "bus": "MISSING_NOT_PERSISTED_BY_R339",
        "category": category,
        "unit": unit,
        "system_base": "100 MVA, 60 Hz where applicable",
        "physical_meaning": "MISSING_NOT_PERSISTED_BY_R339",
    }


def _write_catalog(path: Path, model: PointModel) -> None:
    base = model.base
    payload = {
        "point": model.point,
        "dynamic_states": [
            _catalog_entry(index, str(name), "dynamic")
            for index, name in enumerate(base["state_names"])
        ],
        "algebraic_variables": [
            _catalog_entry(index, str(name), "algebraic")
            for index, name in enumerate(base["algebraic_names"])
        ],
        "node_control_inputs": list(model.control["channel_ids"]),
        "control_coordinate_inputs": list(CONTROL_COORDINATE_NAMES),
        "load_input_devices": list(model.load["channel_ids"]),
        "load_inputs": list(LOAD_BUS_NAMES),
        "physical_outputs": [f"omega_VSG_{index + 1}" for index in range(4)],
        "coordinate_outputs": list(OUTPUT_COORDINATE_NAMES),
        "coordinate_output_transform": base["coordinate_forward"],
        "coordinate_output_inverse": base["coordinate_inverse"],
        "coordinate_input_to_node_transform": model.node_basis.tolist(),
        "node_input_to_coordinate_transform": np.linalg.inv(model.node_basis).tolist(),
        "missing_policy": "Unavailable metadata is literal MISSING; no inferred bus or unit is substituted.",
    }
    _write_json(path, payload)


def _write_convention(path: Path, model: PointModel) -> None:
    nx = len(model.base["x"])
    ny = len(model.base["y"])
    payload = {
        "point": model.point,
        "dae_equation": "diag(Tf) * x_dot = f(x,y,u_node,d_load); 0 = g(x,y,u_node,d_load)",
        "definitions": {
            "E": "diag(Tf)",
            "Fx": "partial f / partial x at the persisted equilibrium",
            "Fy": "partial f / partial y at the persisted equilibrium",
            "Gx": "partial g / partial x at the persisted equilibrium",
            "Gy": "partial g / partial y at the persisted equilibrium",
            "Bx_u_node": "partial f / partial ESD1 Pext0 node input",
            "Hy_u_node": "partial g / partial ESD1 Pext0 node input",
            "Bx_d_load": "partial f / partial PQ Ppf load consumption",
            "Hy_d_load": "partial g / partial PQ Ppf load consumption",
        },
        "signs": {
            "positive_storage_power": "positive network injection",
            "positive_load_power": "increased active-power consumption",
        },
        "outputs": {
            "omega4": "four GENCLS omega states at persisted omega_state_addresses",
            "coord4": "coordinate_forward @ omega4",
            "continuous_direct_feedthrough": "zero; outputs are state-only in R339",
        },
        "dimensions": {
            "dynamic_states": nx,
            "algebraic_variables": ny,
            "node_control_inputs": 4,
            "coordinate_control_inputs": 4,
            "physical_load_inputs": 4,
            "outputs": 4,
        },
        "continuous_time_unit": "second",
        "system_base_mva": 100.0,
        "frequency_base_hz": 60.0,
        "discretization": {
            "method": "ZOH via scipy.signal.cont2discrete",
            "Ts_seconds": SAMPLE_PERIOD_SECONDS,
            "exported_output_convention": "post-step/end-of-held-interval",
            "formula": "C_post=C*Ad; D_post=C*Bd+D",
            "pre_step_matrices_also_exported": True,
        },
        "state_order": "variable_catalog.json dynamic_states order",
        "algebraic_order": "variable_catalog.json algebraic_variables order",
        "control_coordinate_order": list(CONTROL_COORDINATE_NAMES),
        "load_order": list(LOAD_BUS_NAMES),
    }
    _write_json(path, payload)


def _relative_fro(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(np.linalg.norm(right), 1e-12))


def _write_finite_difference_audit(path: Path, model: PointModel) -> None:
    fieldnames = [
        "point",
        "input_name",
        "input_family",
        "step_size",
        "norm_plus_minus_symmetry_error",
        "persisted_even_to_odd_midpoint_ratio",
        "relative_change_to_next_scale",
        "algebraic_residual",
        "equilibrium_algebraic_residual_absolute_maximum",
        "status",
    ]
    base_g_max = float(np.max(np.abs(_matrix(model.base["g"]))))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for family_name, family in (("control", model.control), ("load", model.load)):
            steps = family["steps"]
            for column, channel in enumerate(family["channel_ids"]):
                for index, step in enumerate(steps):
                    current = np.concatenate(
                        [
                            _matrix(step["f_input"])[:, column],
                            _matrix(step["g_input"])[:, column],
                        ]
                    )
                    if index + 1 < len(steps):
                        following = np.concatenate(
                            [
                                _matrix(steps[index + 1]["f_input"])[:, column],
                                _matrix(steps[index + 1]["g_input"])[:, column],
                            ]
                        )
                        relative: float | str = _relative_fro(following, current)
                    else:
                        relative = "MISSING_NO_NEXT_SCALE"
                    symmetry = float(step["midpoint_ratios"][column])
                    writer.writerow(
                        {
                            "point": model.point,
                            "input_name": channel,
                            "input_family": family_name,
                            "step_size": step["step_system_pu"],
                            "norm_plus_minus_symmetry_error": "MISSING_RAW_NORM_NOT_PERSISTED",
                            "persisted_even_to_odd_midpoint_ratio": symmetry,
                            "relative_change_to_next_scale": relative,
                            "algebraic_residual": "MISSING_NOT_PERSISTED_PER_SIGNED_EVALUATION",
                            "equilibrium_algebraic_residual_absolute_maximum": base_g_max,
                            "status": "PASS" if step["all_branch_snapshots_match"] else "FAIL",
                        }
                    )


def _markov_direct(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    state = np.zeros((a.shape[0], b.shape[1]), dtype=float)
    rows = []
    for step in range(20):
        input_now = np.eye(b.shape[1]) if step == 0 else np.zeros((b.shape[1], b.shape[1]))
        rows.append(c @ state + d @ input_now)
        state = a @ state + b @ input_now
    return np.asarray(rows)


def _markov_formula(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    rows = [d]
    power = np.eye(a.shape[0])
    for _ in range(1, 20):
        rows.append(c @ power @ b)
        power = power @ a
    return np.asarray(rows)


def _point_verification(model: PointModel) -> dict[str, object]:
    gy = _matrix(model.base["g_y"])
    gx = _matrix(model.base["g_x"])
    gy_condition = float(np.linalg.cond(gy))
    gy_rank = int(np.linalg.matrix_rank(gy))
    solved = np.linalg.solve(gy, gx)
    gy_solve_residual = float(np.linalg.norm(gy @ solved - gx) / max(np.linalg.norm(gx), 1e-12))
    eig_a = _matrix(model.base["eig_state_matrix"])
    state_error = _relative_fro(model.a_c, eig_a)
    coordinate_error_c = _relative_fro(model.bu_coord_c, model.bu_node_c @ model.node_basis)
    coordinate_error_d = _relative_fro(model.bu_coord_d, model.bu_node_d @ model.node_basis)
    b_all = np.hstack([model.bu_node_d, model.bd_load_d])
    c_post = model.c_coord_c @ model.ad
    d_post = model.c_coord_c @ b_all
    markov_error = float(
        np.max(
            np.abs(
                _markov_direct(model.ad, b_all, c_post, d_post)
                - _markov_formula(model.ad, b_all, c_post, d_post)
            )
        )
    )
    midpoint = max(
        float(value)
        for family in (model.control, model.load)
        for step in family["steps"]
        for value in step["midpoint_ratios"]
    )
    passed = bool(
        gy_rank == gy.shape[0]
        and gy_solve_residual <= 1e-10
        and state_error <= 1e-8
        and coordinate_error_c <= 1e-12
        and coordinate_error_d <= 1e-12
        and markov_error <= 1e-12
        and midpoint <= 1e-6
    )
    return {
        "pass": passed,
        "Gy": {
            "shape": list(gy.shape),
            "condition_2": gy_condition,
            "reciprocal_condition_2": 0.0 if not np.isfinite(gy_condition) else 1.0 / gy_condition,
            "rank": gy_rank,
            "solve_relative_residual": gy_solve_residual,
        },
        "descriptor_to_schur_state_relative_frobenius_error": state_error,
        "node_to_coordinate_continuous_relative_error": coordinate_error_c,
        "node_to_coordinate_discrete_relative_error": coordinate_error_d,
        "first_20_markov_direct_simulation_maximum_absolute_error": markov_error,
        "maximum_signed_midpoint_ratio": midpoint,
        "dimensions": {
            "A_c": list(model.a_c.shape),
            "B_node_c": list(model.bu_node_c.shape),
            "B_load_c": list(model.bd_load_c.shape),
            "C_coord_c": list(model.c_coord_c.shape),
        },
    }


def _git_value(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "MISSING"


def _line_of(path: Path, needle: str) -> int | str:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith(needle):
            return line_number
    return "MISSING"


def _write_root_documents(
    bundle: Path,
    repo_root: Path,
    source_hashes: dict[str, str],
    verification: dict[str, object],
    diagnostic_archive: Path | None,
) -> None:
    external_reference: dict[str, object]
    if diagnostic_archive is not None and diagnostic_archive.is_file():
        external_reference = {
            "path": str(diagnostic_archive),
            "sha256": _sha256(diagnostic_archive),
            "status": "PRESENT_HASH_REFERENCE_ONLY",
        }
    else:
        external_reference = {
            "path": str(diagnostic_archive) if diagnostic_archive else "MISSING_NOT_SUPPLIED",
            "status": "MISSING",
        }

    environment = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "git": {
            "branch": _git_value(repo_root, "branch", "--show-current"),
            "commit": _git_value(repo_root, "rev-parse", "HEAD"),
            "dirty_status": _git_value(repo_root, "status", "--short"),
        },
        "andes": _read_json(repo_root / SOURCE_PROVENANCE)["runtime"]["andes"],
        "random_seed": "NOT_USED_DETERMINISTIC_EXPORT",
        "exact_command": " ".join(sys.argv),
    }
    _write_json(bundle / "environment.json", environment)
    _write_json(bundle / "verification.json", verification)
    _write_json(
        bundle / "missing_inventory.json",
        {
            "items": [
                {
                    "item": "per-variable bus, unit, and physical meaning metadata",
                    "status": "PARTIAL_WITH_LITERAL_MISSING_FIELDS",
                    "reason": "R339 persisted ordered names but not the full requested metadata catalog.",
                },
                {
                    "item": "per-signed-evaluation algebraic residual",
                    "status": "MISSING",
                    "reason": "R339 persisted derivatives and midpoint ratios, not each signed residual vector.",
                },
                {
                    "item": "raw plus/minus symmetry-error norm",
                    "status": "MISSING",
                    "reason": "R339 persisted only the normalized even-to-odd midpoint ratio; the raw norm is not reconstructed.",
                },
                {
                    "item": "optional 32-record prediction NPZ set",
                    "status": "MISSING_OPTIONAL_NOT_EXPORTED",
                    "reason": "R339 persisted formal metrics; this engineering export does not create a second trajectory copy.",
                },
            ]
        },
    )
    (bundle / "README.md").write_text(
        "# Full-order DAE input bridge bundle\n\n"
        "This is a deterministic offline export of the sealed R339 HS0/HS1 extraction. "
        "It is not a new experiment or a new scientific claim. No ANDES run, controller, "
        "closed loop, training, model-order search, or threshold selection occurs.\n\n"
        "Start with `verification.json`, then each point's `linearization_convention.json`. "
        "Unavailable metadata is written literally as `MISSING`; FV0/FV1 matrices are never "
        "substituted for HS0/HS1. The external diagnostic archive is referenced by hash only.\n",
        encoding="utf-8",
    )
    exporter_path = repo_root / "src/andes_rl_kundur/evaluation/full_order_bridge_bundle.py"
    bridge_path = repo_root / "src/andes_rl_kundur/evaluation/model_first_input_bridge.py"
    runner_path = repo_root / "scripts/run_r339_input_bridge_diagnosis.py"
    probe_path = repo_root / "probes/r339_input_bridge_diagnosis.py"
    code_refs = [
        (exporter_path, "def build_full_order_bridge_bundle"),
        (exporter_path, "def verify_full_order_bridge_bundle"),
        (bridge_path, "def fold_zero_time_constant_states"),
        (bridge_path, "def reduce_folded_descriptor"),
        (runner_path, "def _extract_live_job"),
        (probe_path, "def analyse_r339_input_bridge"),
    ]
    code_ref_lines = ["# Code references", ""]
    for source, needle in code_refs:
        relative = source.relative_to(repo_root).as_posix()
        code_ref_lines.append(f"- `{relative}:{_line_of(source, needle)}` — `{needle}`")
    (bundle / "code_refs.md").write_text("\n".join(code_ref_lines) + "\n", encoding="utf-8")
    (bundle / "reproduce.ps1").write_text(
        "param(\n"
        "  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\\..\\..')),\n"
        "  [string]$DiagnosticArchive = 'E:\\input_bridge_diagnostic_bundle_for_gpt.zip'\n"
        ")\n"
        "$ErrorActionPreference = 'Stop'\n"
        "$env:PYTHONPATH = Join-Path $RepoRoot 'src'\n"
        "python -m andes_rl_kundur.evaluation.full_order_bridge_bundle build "
        "--repo-root $RepoRoot --output "
        "(Join-Path $RepoRoot 'tmp/decoupling_marl_model_first/reproduced_full_order_bridge_bundle') "
        "--diagnostic-archive $DiagnosticArchive\n",
        encoding="utf-8",
    )
    (bundle / "reproduce.sh").write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        'repo_root=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)}\n'
        "diagnostic_archive=${2:-/mnt/e/input_bridge_diagnostic_bundle_for_gpt.zip}\n"
        'PYTHONPATH="$repo_root/src" python -m '
        "andes_rl_kundur.evaluation.full_order_bridge_bundle build "
        '--repo-root "$repo_root" --output '
        '"$repo_root/tmp/decoupling_marl_model_first/reproduced_full_order_bridge_bundle" '
        '--diagnostic-archive "$diagnostic_archive"\n',
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "classification": "DERIVED-OFFLINE-EXPORT-OF-R339",
        "claim_ceiling": "No new evidence or controller, learning, stability, safety, generalization, or title claim.",
        "source_artifacts": source_hashes,
        "external_diagnostic_archive": external_reference,
        "points": list(POINT_NAMES),
        "sample_period_seconds": SAMPLE_PERIOD_SECONDS,
        "discretization": "ZOH; exported output convention is post-step/end-of-held-interval",
        "missing_inventory": "missing_inventory.json",
    }
    _write_json(bundle / "manifest.json", manifest)


def _write_hash_manifest(bundle: Path) -> None:
    files = sorted(
        path for path in bundle.rglob("*") if path.is_file() and path.name != "manifest.sha256"
    )
    lines = [f"{_sha256(path)}  {path.relative_to(bundle).as_posix()}" for path in files]
    (bundle / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_full_order_bridge_bundle(
    *,
    repo_root: Path | str | None = None,
    output_dir: Path | str,
    diagnostic_archive: Path | str | None = None,
) -> Path:
    """Build a create-only bundle from the sealed R339 extraction."""

    root = Path(repo_root) if repo_root is not None else _repo_root()
    root = root.resolve()
    output = Path(output_dir)
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"create-only output already exists: {output}")
    source_paths = [
        SOURCE_EXECUTION,
        SOURCE_ANALYSIS,
        SOURCE_PROVENANCE,
        SOURCE_REPORT,
        SOURCE_EXPORTER,
        SOURCE_BRIDGE_IMPLEMENTATION,
    ]
    missing = [str(path) for path in source_paths if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing authoritative R339 source(s): {', '.join(missing)}")
    execution = _read_json(root / SOURCE_EXECUTION)
    if (
        execution.get("round") != "R339"
        or execution.get("fresh_nonlinear_trajectory_executed") is not False
    ):
        raise ValueError("source is not the bounded sealed R339 offline extraction")
    points = {str(row["point"]): row for row in execution["points"]}
    if set(points) != set(POINT_NAMES):
        raise ValueError("R339 point inventory must be exactly HS0 and HS1")
    analysis = _read_json(root / SOURCE_ANALYSIS)
    formal_analysis_pass = bool(
        analysis.get("classification") == "ALLOW-CANDIDATE"
        and analysis.get("descriptor_gate_pass") is True
        and analysis.get("linearization_gate_pass") is True
        and analysis.get("order12_reduction_gate_pass") is True
    )
    if not formal_analysis_pass:
        raise ValueError("R339 formal analysis no longer carries the qualified pass state")

    source_hashes = {path.as_posix(): _sha256(root / path) for path in source_paths}
    output.mkdir(parents=True)
    verification_points: dict[str, object] = {}
    try:
        for point_name in POINT_NAMES:
            model = _construct_point(points[point_name])
            point_dir = output / "points" / point_name
            point_dir.mkdir(parents=True)
            _save_equilibrium(point_dir / "equilibrium.npz", model)
            _save_jacobians(point_dir / "dae_jacobians.npz", model)
            np.savez_compressed(
                point_dir / "full_order_continuous.npz", **_continuous_payload(model)
            )
            np.savez_compressed(point_dir / "full_order_discrete.npz", **_discrete_payload(model))
            _write_catalog(point_dir / "variable_catalog.json", model)
            _write_convention(point_dir / "linearization_convention.json", model)
            _write_finite_difference_audit(point_dir / "finite_difference_audit.csv", model)
            verification_points[point_name] = _point_verification(model)
        verification = {
            "pass": all(bool(row["pass"]) for row in verification_points.values()),
            "points": verification_points,
            "source_hashes": source_hashes,
            "formal_r339_analysis": {
                "pass": formal_analysis_pass,
                "classification": analysis["classification"],
                "descriptor_gate_pass": analysis["descriptor_gate_pass"],
                "linearization_gate_pass": analysis["linearization_gate_pass"],
                "order12_reduction_gate_pass": analysis["order12_reduction_gate_pass"],
            },
            "scope_guards": {
                "andes_executed": False,
                "controller_executed": False,
                "training_executed": False,
                "formal_artifact_modified": False,
            },
        }
        _write_root_documents(
            output,
            root,
            source_hashes,
            verification,
            Path(diagnostic_archive).resolve() if diagnostic_archive is not None else None,
        )
        _write_hash_manifest(output)
        if not verify_full_order_bridge_bundle(output)["pass"]:
            raise RuntimeError("generated bundle failed its own verification")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise
    return output


def verify_full_order_bridge_bundle(bundle_dir: Path | str) -> dict[str, object]:
    """Verify generated-file hashes and the persisted numerical decision."""

    bundle = Path(bundle_dir).resolve()
    failures: list[str] = []
    hash_manifest = bundle / "manifest.sha256"
    if not hash_manifest.is_file():
        return {"pass": False, "failures": ["manifest.sha256 is missing"]}
    for line in hash_manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = bundle / Path(relative)
        if not path.is_file():
            failures.append(f"missing file: {relative}")
        elif _sha256(path) != digest:
            failures.append(f"hash mismatch: {relative}")
    verification = _read_json(bundle / "verification.json")
    if verification.get("pass") is not True:
        failures.append("persisted numerical verification is not PASS")
    for point in POINT_NAMES:
        required = {
            "equilibrium.npz",
            "dae_jacobians.npz",
            "full_order_continuous.npz",
            "full_order_discrete.npz",
            "variable_catalog.json",
            "linearization_convention.json",
            "finite_difference_audit.csv",
        }
        actual = {path.name for path in (bundle / "points" / point).iterdir()}
        if not required <= actual:
            failures.append(f"{point} required-file inventory is incomplete")
    return {"pass": not failures, "failures": failures}


def archive_full_order_bridge_bundle(bundle_dir: Path | str, archive_path: Path | str) -> Path:
    """Create and integrity-read one ZIP for upload."""

    bundle = Path(bundle_dir).resolve()
    if not verify_full_order_bridge_bundle(bundle)["pass"]:
        raise ValueError("refusing to archive an invalid bundle")
    archive = Path(archive_path).resolve()
    if archive.exists():
        raise FileExistsError(f"create-only archive already exists: {archive}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(item for item in bundle.rglob("*") if item.is_file()):
            handle.write(path, (Path(bundle.name) / path.relative_to(bundle)).as_posix())
    with zipfile.ZipFile(archive, "r") as handle:
        bad = handle.testzip()
        if bad is not None:
            archive.unlink(missing_ok=True)
            raise RuntimeError(f"ZIP integrity read failed at {bad}")
    return archive


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--repo-root", type=Path, default=_repo_root())
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--diagnostic-archive", type=Path)
    build.add_argument("--zip", dest="archive", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "build":
        bundle = build_full_order_bridge_bundle(
            repo_root=args.repo_root,
            output_dir=args.output,
            diagnostic_archive=args.diagnostic_archive,
        )
        payload: dict[str, object] = {
            "bundle": str(bundle),
            "verification": verify_full_order_bridge_bundle(bundle),
        }
        if args.archive is not None:
            archive = archive_full_order_bridge_bundle(bundle, args.archive)
            payload["archive"] = str(archive)
            payload["archive_sha256"] = _sha256(archive)
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0
    result = verify_full_order_bridge_bundle(args.bundle)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
