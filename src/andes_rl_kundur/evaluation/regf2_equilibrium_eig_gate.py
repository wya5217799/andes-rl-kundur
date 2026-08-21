"""Classify the exact-R389 equilibrium and reduced-spectrum mechanism gate.

The module owns a detached prospective contract and a pure record classifier.
It imports no ANDES runtime code, so sealed records can be replayed on Windows.
Positive-real modes are scientific outcomes, not integrity defects.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np
from scipy.linalg import eig
from scipy.optimize import linear_sum_assignment

from andes_rl_kundur.evaluation.regf2_object_init_gate import (
    _diagnostics_schema,
    _empty_references,
    _inventory_schema,
    _references_schema,
    _source_schema,
    build_regf2_object_init_contract,
)

REGF2_STATE_VARIABLES = (
    "Psen_y",
    "Qsen_y",
    "Psig_y",
    "Qsig_y",
    "PIplim_xi",
    "PIqlim_xi",
    "delta",
    "INTw_y",
    "PIvd_xi",
    "PIvq_xi",
    "PIId_xi",
    "PIIq_xi",
    "udLag_y",
    "uqLag_y",
)
PLL2_STATE_VARIABLES = ("PI_xi", "am")
SCIENTIFIC_ERRORS = {
    None,
    "PFlow did not converge",
    "TDS initialization failed",
    "EIG calculation failed",
}


def build_regf2_equilibrium_eig_contract() -> dict[str, Any]:
    """Return a detached canonical R390 contract."""

    parent = build_regf2_object_init_contract()
    return deepcopy(
        {
            "schema_version": 1,
            "round": "R390",
            "question": "Q-0108",
            "object_contract": parent,
            "arms": [
                {
                    "name": "r389_reference_tol_1e-4",
                    "tds_tolerance": 1.0e-4,
                },
                {
                    "name": "sensitivity_tol_1e-6",
                    "tds_tolerance": 1.0e-6,
                },
            ],
            "positive_real_tolerance": 1.0e-7,
            "near_zero_tolerance": 1.0e-6,
            "eig_source_sha256": (
                "10a97879f0b3f15a59dc51f1ab6a6bd9a6f7ac6e7ada0337949af78e07ef5707"
            ),
            "pll2_source_sha256": (
                "ee147a79fcc7e375c67ccf885ccc0f97b6dca3a2490e2ead71afccb5b2f9081f"
            ),
            "numpy_version": "2.4.3",
            "scipy_version": "1.17.1",
            "system_source_sha256": (
                "b6aa12d10811a5b35e0d5939c309d3414713daff4f5d30f2b9063e0d518080c9"
            ),
            "tds_source_sha256": (
                "224ff43d78de8e6808efa0a6b858d8dbe2ca511128a90a8260009c8146d6e8ba"
            ),
            "dae_source_sha256": (
                "c702f8634b719b3fcaffc80efb60f5a572f06d5df9197e3d87e7400b0d5c45b1"
            ),
            "r389_parent_sha256": {
                "formal_seal": "5d0a209f8f3ac92867bba48e24e66db8b2ad9e289a41c956963d4f5d50da8372",
                "formal_attempt": "6a7ea05bbbf16598501eb90d981497cae9a34b0043976efe38ba8eb1ac1e56cc",
                "formal_execution": "c6ac20a4ef8614eb74bb38752826407417ee64ab4e7d3c0c3634a58d73ab2ea4",
                "formal_analysis": "45d3a4cd7942ec509cf399b71bf4115417ac4a79985cdd250aad594f793d931e",
                "formal_manifest": "5e109995295d6dca573fe45f776556b772fb1a9fb9c192020b68bc9cc42ef43d",
            },
            "registered_state_variables": {
                "REGF2": list(REGF2_STATE_VARIABLES),
                "PLL2": list(PLL2_STATE_VARIABLES),
            },
            "state_advance_abs_tolerance": 0.0,
            "spectrum_match_normalized_tolerance": 1.0e-8,
            "eigenpair_backward_error_max": 1.0e-8,
            "eigenvector_condition_number_max": 1.0e12,
            "cross_arm_leading_normalized_tolerance": 1.0e-4,
            "trajectory_count": 0,
            "post_init_actions_authorized": False,
            "retry_authorized": False,
            "training_authorized": False,
        }
    )


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _finite_number(value: object) -> bool:
    return bool(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _source_integrity(arm: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        source = arm["source"]
        return bool(
            _source_schema(arm, spec["object_contract"])
            and source["eig_source_sha256"] == spec["eig_source_sha256"]
            and source["pll2_source_sha256"] == spec["pll2_source_sha256"]
            and source["numpy_version"] == spec["numpy_version"]
            and source["scipy_version"] == spec["scipy_version"]
            and source["system_source_sha256"] == spec["system_source_sha256"]
            and source["tds_source_sha256"] == spec["tds_source_sha256"]
            and source["dae_source_sha256"] == spec["dae_source_sha256"]
        )
    except (KeyError, TypeError):
        return False


def _object_integrity(
    arm: Mapping[str, Any], spec: Mapping[str, Any], *, pflow_failed: bool
) -> tuple[bool, bool]:
    parent = spec["object_contract"]
    try:
        references_schema, references_pass = _references_schema(arm, parent)
        if pflow_failed:
            references_schema = _empty_references(arm["references"], parent)
            references_pass = False
        finite_guard = arm["finite_guard"]
        finite_schema = bool(
            finite_guard["checked"] is True
            and all(
                isinstance(finite_guard[key], bool)
                for key in (
                    "dae_finite",
                    "jacobian_finite",
                    "state_matrix_finite",
                )
            )
        )
        return (
            bool(
                _source_integrity(arm, spec)
                and _inventory_schema(arm, parent)
                and references_schema
                and _diagnostics_schema(arm, parent)
                and finite_schema
            ),
            bool(
                references_pass
                and finite_guard["dae_finite"]
                and finite_guard["jacobian_finite"]
                and arm["initialization_diagnostics"]["residual_count"] == 0
                and arm["initialization_diagnostics"]["clamped_limits"] == []
            ),
        )
    except (KeyError, TypeError):
        return False, False


def _complex_rows(rows: object, expected_length: int) -> np.ndarray | None:
    if not isinstance(rows, list) or len(rows) != expected_length:
        return None
    values: list[complex] = []
    for row in rows:
        if (
            not isinstance(row, Mapping)
            or not _finite_number(row.get("real"))
            or not _finite_number(row.get("imag"))
        ):
            return None
        values.append(complex(float(row["real"]), float(row["imag"])))
    return np.asarray(values, dtype=complex)


def _binding_integrity(
    matrix_record: Mapping[str, Any], names: list[str], spec: Mapping[str, Any]
) -> bool:
    try:
        bindings = matrix_record["state_bindings"]
        zero_names = matrix_record["zero_tf_state_names"]
        zero_addresses = matrix_record["zero_tf_state_addresses"]
        dead_indices = matrix_record["dead_algebraic_indices"]
        state_catalog = matrix_record["dae_state_catalog"]
        algebraic_names = matrix_record["dae_algebraic_names"]
        discrete_names = matrix_record["dae_discrete_names"]
        augmented_algebraic_names = matrix_record["eig_augmented_algebraic_names"]
        if not isinstance(state_catalog, list) or not state_catalog:
            return False
        normalized_catalog: list[tuple[int, str, float]] = []
        for row in state_catalog:
            if (
                not isinstance(row, Mapping)
                or isinstance(row.get("address"), bool)
                or not isinstance(row.get("address"), int)
                or not isinstance(row.get("name"), str)
                or not row["name"]
                or not _finite_number(row.get("tf"))
            ):
                return False
            normalized_catalog.append(
                (int(row["address"]), str(row["name"]), float(row["tf"]))
            )
        if (
            [row[0] for row in normalized_catalog]
            != list(range(len(normalized_catalog)))
            or len({row[1] for row in normalized_catalog}) != len(normalized_catalog)
            or not isinstance(algebraic_names, list)
            or any(not isinstance(name, str) or not name for name in algebraic_names)
            or len(algebraic_names) != len(set(algebraic_names))
            or not isinstance(discrete_names, list)
            or any(not isinstance(name, str) or not name for name in discrete_names)
            or len(discrete_names) != len(set(discrete_names))
            or not isinstance(augmented_algebraic_names, list)
            or any(
                not isinstance(name, str) or not name
                for name in augmented_algebraic_names
            )
        ):
            return False
        catalog_names = [row[1] for row in normalized_catalog]
        catalog_tf = [row[2] for row in normalized_catalog]
        expected_zero_addresses = [
            index for index, value in enumerate(catalog_tf) if value == 0.0
        ]
        expected_zero_names = [catalog_names[index] for index in expected_zero_addresses]
        if (
            not isinstance(bindings, list)
            or not isinstance(zero_names, list)
            or not isinstance(zero_addresses, list)
            or any(not isinstance(name, str) or not name for name in zero_names)
            or len(zero_names) != len(set(zero_names))
            or bool(set(zero_names) & set(names))
            or zero_addresses != expected_zero_addresses
            or zero_names != expected_zero_names
            or augmented_algebraic_names != algebraic_names + expected_zero_names
            or any(name not in catalog_names for name in names)
            or any(catalog_tf[catalog_names.index(name)] == 0.0 for name in names)
            or not isinstance(dead_indices, list)
            or any(
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(augmented_algebraic_names)
                for index in dead_indices
            )
            or len(dead_indices) != len(set(dead_indices))
        ):
            return False

        expected = {
            (model, f"{model}_{device}", variable)
            for model, variables in spec["registered_state_variables"].items()
            for device in range(1, 5)
            for variable in variables
        }
        seen: set[tuple[str, str, str]] = set()
        for row in bindings:
            if not isinstance(row, Mapping):
                return False
            key = (str(row["model"]), str(row["idx"]), str(row["variable"]))
            if key not in expected or key in seen:
                return False
            seen.add(key)
            dae_name = row["dae_name"]
            original_address = row["original_address"]
            status = row["status"]
            if (
                not isinstance(dae_name, str)
                or not dae_name
                or isinstance(original_address, bool)
                or not isinstance(original_address, int)
                or not 0 <= original_address < len(catalog_names)
                or catalog_names[original_address] != dae_name
                or not {key[0], key[1], key[2]}.issubset(set(dae_name.split()))
            ):
                return False
            if status == "retained":
                reduced_index = row["reduced_index"]
                if (
                    isinstance(reduced_index, bool)
                    or not isinstance(reduced_index, int)
                    or not 0 <= reduced_index < len(names)
                    or names[reduced_index] != dae_name
                    or names.count(dae_name) != 1
                    or catalog_tf[original_address] == 0.0
                ):
                    return False
            elif status == "folded":
                if (
                    row["reduced_index"] is not None
                    or original_address not in zero_addresses
                    or dae_name in names
                ):
                    return False
            elif status == "eliminated":
                if (
                    row["reduced_index"] is not None
                    or catalog_tf[original_address] == 0.0
                    or dae_name in names
                ):
                    return False
            else:
                return False
        return seen == expected
    except (KeyError, TypeError, ValueError):
        return False


def _same_float_bits(left: object, right: object) -> bool:
    return bool(
        _finite_number(left)
        and _finite_number(right)
        and struct.pack(">d", float(left)) == struct.pack(">d", float(right))
    )


def _snapshot_integrity(
    arm: Mapping[str, Any], matrix_record: Mapping[str, Any]
) -> tuple[bool, bool]:
    try:
        snapshot = arm["equilibrium_snapshot"]
        if snapshot["captured"] is not True:
            return False, False
        before = snapshot["before"]
        after = snapshot["after"]
        required = {"time", "x", "y", "z", "f", "g"}
        if (
            not isinstance(before, Mapping)
            or not isinstance(after, Mapping)
            or set(before) != required
            or set(after) != required
        ):
            return False, False
        state_catalog = matrix_record["dae_state_catalog"]
        algebraic_names = matrix_record["dae_algebraic_names"]
        discrete_names = matrix_record["dae_discrete_names"]
        for row in (before, after):
            if (
                not _finite_number(row["time"])
                or not all(isinstance(row[key], list) for key in ("x", "y", "z", "f", "g"))
                or len(row["x"]) != len(state_catalog)
                or len(row["f"]) != len(state_catalog)
                or len(row["y"]) != len(algebraic_names)
                or len(row["g"]) != len(algebraic_names)
                or len(row["z"]) != len(discrete_names)
                or not all(
                    _finite_number(value)
                    for key in ("x", "y", "z", "f", "g")
                    for value in row[key]
                )
            ):
                return False, False
        deltas = [
            abs(float(right) - float(left))
            for key in ("x", "y", "z")
            for left, right in zip(before[key], after[key], strict=True)
        ]
        recomputed_delta = max(deltas, default=0.0)
        solver = arm["solver"]
        schema = bool(
            _same_float_bits(solver["time_before_eig"], before["time"])
            and _same_float_bits(solver["time_after_eig"], after["time"])
            and _same_float_bits(solver["state_max_abs_delta"], recomputed_delta)
        )
        no_advance = bool(
            _same_float_bits(before["time"], after["time"])
            and before["x"] == after["x"]
            and before["y"] == after["y"]
            and before["z"] == after["z"]
        )
        return schema, no_advance
    except (KeyError, TypeError, ValueError):
        return False, False


def _matrix_metrics(
    arm: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[bool, bool, dict[str, Any]]:
    empty = {
        "positive_real_count": 0,
        "near_zero_count": 0,
        "leading_eigenvalue": None,
        "leading_eigenvalues": [],
        "spectrum_match_max": None,
        "eigenpair_backward_error_max": None,
        "leading_eigenvector_condition_number": None,
    }
    try:
        captured = arm["matrix"]
        if captured["captured"] is not True:
            return False, False, empty
        matrix = np.asarray(captured["as"], dtype=float)
        names = captured["state_names"]
        if (
            matrix.ndim != 2
            or matrix.shape[0] == 0
            or matrix.shape[0] != matrix.shape[1]
            or not np.all(np.isfinite(matrix))
            or not isinstance(names, list)
            or len(names) != matrix.shape[0]
            or any(not isinstance(name, str) or not name for name in names)
            or len(names) != len(set(names))
            or not _binding_integrity(captured, names, spec)
        ):
            return False, False, empty

        andes_values = _complex_rows(captured["andes_eigenvalues"], matrix.shape[0])
        if andes_values is None:
            return False, False, empty
        independent, left, right = eig(matrix, left=True, right=True)
        if not (
            np.all(np.isfinite(independent.real))
            and np.all(np.isfinite(independent.imag))
            and np.all(np.isfinite(left.real))
            and np.all(np.isfinite(left.imag))
            and np.all(np.isfinite(right.real))
            and np.all(np.isfinite(right.imag))
        ):
            return False, False, empty

        distances = np.abs(andes_values[:, None] - independent[None, :]) / (
            1.0 + np.abs(andes_values[:, None])
        )
        rows, columns = linear_sum_assignment(distances)
        spectrum_match_max = float(np.max(distances[rows, columns]))

        matrix_norm = float(np.linalg.norm(matrix, ord=2))
        backward_errors: list[float] = []
        for index, value in enumerate(independent):
            vector = right[:, index]
            denominator = (matrix_norm + abs(value)) * float(np.linalg.norm(vector))
            error = float(np.linalg.norm(matrix @ vector - value * vector)) / max(
                denominator, np.finfo(float).tiny
            )
            backward_errors.append(error)
        max_real = float(np.max(independent.real))
        leading_tolerance = float(spec["spectrum_match_normalized_tolerance"])
        leading_indices = [
            index
            for index, value in enumerate(independent)
            if max_real - float(value.real)
            <= leading_tolerance * (1.0 + abs(max_real))
        ]
        conditions: list[float] = []
        for leading_index in leading_indices:
            overlap = abs(np.vdot(left[:, leading_index], right[:, leading_index]))
            conditions.append(
                float(
                    np.linalg.norm(left[:, leading_index])
                    * np.linalg.norm(right[:, leading_index])
                    / max(float(overlap), np.finfo(float).tiny)
                )
            )
        canonical_leading: list[complex] = []
        for value in sorted(
            (complex(float(independent[index].real), abs(float(independent[index].imag)))
             for index in leading_indices),
            key=lambda item: (item.real, item.imag),
        ):
            if not canonical_leading or all(
                abs(value - prior) / (1.0 + abs(prior)) > leading_tolerance
                for prior in canonical_leading
            ):
                canonical_leading.append(value)
        leading = canonical_leading[0]
        condition = max(conditions)
        metrics = {
            "positive_real_count": int(
                np.count_nonzero(independent.real > spec["positive_real_tolerance"])
            ),
            "near_zero_count": int(
                np.count_nonzero(np.abs(independent) < spec["near_zero_tolerance"])
            ),
            "leading_eigenvalue": {
                "real": float(leading.real),
                "imag": float(leading.imag),
            },
            "leading_eigenvalues": [
                {"real": float(value.real), "imag": float(value.imag)}
                for value in canonical_leading
            ],
            "spectrum_match_max": spectrum_match_max,
            "eigenpair_backward_error_max": float(max(backward_errors)),
            "leading_eigenvector_condition_number": condition,
        }
        numerical_pass = bool(
            spectrum_match_max <= spec["spectrum_match_normalized_tolerance"]
            and metrics["eigenpair_backward_error_max"]
            <= spec["eigenpair_backward_error_max"]
            and condition <= spec["eigenvector_condition_number_max"]
        )
        return True, numerical_pass, metrics
    except (KeyError, TypeError, ValueError, np.linalg.LinAlgError):
        return False, False, empty


def _empty_matrix(matrix_record: object) -> bool:
    return isinstance(matrix_record, Mapping) and matrix_record == {
        "captured": False,
        "as": [],
        "state_names": [],
        "andes_eigenvalues": [],
        "zero_tf_state_names": [],
        "zero_tf_state_addresses": [],
        "dead_algebraic_indices": [],
        "dae_state_catalog": [],
        "dae_algebraic_names": [],
        "dae_discrete_names": [],
        "eig_augmented_algebraic_names": [],
        "state_bindings": [],
    }


def _empty_snapshot(snapshot: object) -> bool:
    return isinstance(snapshot, Mapping) and snapshot == {
        "captured": False,
        "before": None,
        "after": None,
    }


def _failed_matrix_integrity(matrix_record: object) -> bool:
    try:
        if not isinstance(matrix_record, Mapping):
            return False
        catalog = matrix_record["dae_state_catalog"]
        algebraic = matrix_record["dae_algebraic_names"]
        discrete = matrix_record["dae_discrete_names"]
        augmented_algebraic = matrix_record["eig_augmented_algebraic_names"]
        zero_addresses = matrix_record["zero_tf_state_addresses"]
        zero_names = matrix_record["zero_tf_state_names"]
        if (
            matrix_record["captured"] is not False
            or matrix_record["as"] != []
            or matrix_record["state_names"] != []
            or matrix_record["andes_eigenvalues"] != []
            or matrix_record["state_bindings"] != []
            or not isinstance(catalog, list)
            or not catalog
            or not isinstance(algebraic, list)
            or any(not isinstance(name, str) or not name for name in algebraic)
            or len(algebraic) != len(set(algebraic))
            or not isinstance(discrete, list)
            or any(not isinstance(name, str) or not name for name in discrete)
            or len(discrete) != len(set(discrete))
            or not isinstance(augmented_algebraic, list)
            or any(
                not isinstance(name, str) or not name
                for name in augmented_algebraic
            )
            or len(augmented_algebraic) != len(set(augmented_algebraic))
        ):
            return False
        normalized = []
        for row in catalog:
            if (
                not isinstance(row, Mapping)
                or row.get("address") != len(normalized)
                or not isinstance(row.get("name"), str)
                or not row["name"]
                or not _finite_number(row.get("tf"))
            ):
                return False
            normalized.append((row["name"], float(row["tf"])))
        if len({name for name, _ in normalized}) != len(normalized):
            return False
        expected_addresses = [
            index for index, (_, tf) in enumerate(normalized) if tf == 0.0
        ]
        return bool(
            zero_addresses == expected_addresses
            and zero_names == [normalized[index][0] for index in expected_addresses]
            and augmented_algebraic
            == algebraic + [normalized[index][0] for index in expected_addresses]
            and all(
                isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < len(augmented_algebraic)
                for index in matrix_record["dead_algebraic_indices"]
            )
            and len(matrix_record["dead_algebraic_indices"])
            == len(set(matrix_record["dead_algebraic_indices"]))
        )
    except (KeyError, TypeError, ValueError):
        return False


def _arm_integrity(
    arm: Mapping[str, Any], arm_spec: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[bool, bool, bool, dict[str, Any]]:
    empty_metrics: dict[str, Any] = {
        "positive_real_count": 0,
        "near_zero_count": 0,
        "leading_eigenvalue": None,
        "leading_eigenvalues": [],
        "spectrum_match_max": None,
        "eigenpair_backward_error_max": None,
        "leading_eigenvector_condition_number": None,
    }
    try:
        error = arm["scientific_error"]
        if (
            arm["name"] != arm_spec["name"]
            or not _finite_number(arm["tds_tolerance"])
            or float(arm["tds_tolerance"]) != float(arm_spec["tds_tolerance"])
            or arm["execution_error"] is not None
            or error not in SCIENTIFIC_ERRORS
            or arm["trajectory_attempted"] is not False
            or arm["physical_trajectory_executed"] is not False
            or arm["trajectory_count"] != 0
        ):
            return False, False, False, empty_metrics
        solver = arm["solver"]
        if any(
            not isinstance(solver[key], bool)
            for key in (
                "setup_completed",
                "pflow_converged",
                "tds_initialized",
                "tds_test_ok",
                "eig_return",
            )
        ) or (
            isinstance(solver["system_exit_code"], bool)
            or not isinstance(solver["system_exit_code"], int)
        ) or not all(
            _finite_number(solver[key])
            for key in (
                "actual_tds_tolerance",
                "time_before_eig",
                "time_after_eig",
                "state_max_abs_delta",
            )
        ):
            return False, False, False, empty_metrics
        if float(solver["actual_tds_tolerance"]) != float(arm_spec["tds_tolerance"]):
            return False, False, False, empty_metrics

        pflow_failed = error == "PFlow did not converge"
        object_schema, object_pass = _object_integrity(
            arm, spec, pflow_failed=pflow_failed
        )
        if not object_schema:
            return False, False, False, empty_metrics

        if error == "PFlow did not converge":
            sentinel = bool(
                solver["setup_completed"]
                and not solver["pflow_converged"]
                and not solver["tds_initialized"]
                and not solver["tds_test_ok"]
                and not solver["eig_return"]
                and float(solver["time_before_eig"]) == 0.0
                and float(solver["time_after_eig"]) == 0.0
                and float(solver["state_max_abs_delta"]) == 0.0
                and _empty_matrix(arm["matrix"])
                and _empty_snapshot(arm["equilibrium_snapshot"])
            )
            return sentinel, False, False, empty_metrics
        if error == "TDS initialization failed":
            sentinel = bool(
                solver["setup_completed"]
                and solver["pflow_converged"]
                and not (solver["tds_initialized"] and solver["tds_test_ok"])
                and not solver["eig_return"]
                and float(solver["time_before_eig"]) == 0.0
                and float(solver["time_after_eig"]) == 0.0
                and float(solver["state_max_abs_delta"]) == 0.0
                and _empty_matrix(arm["matrix"])
                and _empty_snapshot(arm["equilibrium_snapshot"])
            )
            return sentinel, False, False, empty_metrics

        snapshot_schema, time_and_state_static = _snapshot_integrity(
            arm, arm["matrix"]
        )
        if error == "EIG calculation failed":
            sentinel = bool(
                solver["setup_completed"]
                and solver["pflow_converged"]
                and solver["tds_initialized"]
                and solver["tds_test_ok"]
                and not solver["eig_return"]
                and not arm["finite_guard"]["state_matrix_finite"]
                and snapshot_schema
                and _failed_matrix_integrity(arm["matrix"])
            )
            equilibrium_pass = bool(
                sentinel
                and object_pass
                and solver["system_exit_code"] == 0
                and time_and_state_static
            )
            return sentinel, equilibrium_pass, False, empty_metrics

        equilibrium_pass = bool(
            object_pass
            and solver["setup_completed"]
            and solver["pflow_converged"]
            and solver["tds_initialized"]
            and solver["tds_test_ok"]
            and solver["eig_return"]
            and solver["system_exit_code"] == 0
            and snapshot_schema
            and time_and_state_static
            and arm["finite_guard"]["state_matrix_finite"]
        )
        matrix_schema, numerical_pass, metrics = _matrix_metrics(arm, spec)
        return snapshot_schema and matrix_schema, equilibrium_pass, numerical_pass, metrics
    except (KeyError, TypeError, ValueError):
        return False, False, False, empty_metrics


def classify_regf2_equilibrium_eig_record(
    record: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed R390 analysis for one immutable two-arm record."""

    canonical = build_regf2_equilibrium_eig_contract()
    spec = deepcopy(canonical if contract is None else contract)
    checks: dict[str, bool] = {}
    try:
        checks["canonical_contract"] = spec == canonical
        checks["record_identity"] = bool(
            record["schema_version"] == canonical["schema_version"]
            and record["round"] == canonical["round"]
            and record["question"] == canonical["question"]
            and record["contract_sha256"] == _payload_sha256(canonical)
            and record["formal_input_complete"] is True
            and record["execution_error"] is None
            and record["training_executed"] is False
            and record["post_init_action_executed"] is False
            and record["trajectory_count"] == 0
        )
        arms = record["arms"]
        checks["arm_order_and_count"] = bool(
            isinstance(arms, list)
            and len(arms) == len(canonical["arms"])
            and all(isinstance(arm, Mapping) for arm in arms)
            and [arm.get("name") for arm in arms]
            == [arm["name"] for arm in canonical["arms"]]
        )
    except (KeyError, TypeError):
        checks["record_identity"] = False
        checks["arm_order_and_count"] = False
        arms = []

    metrics: list[dict[str, Any]] = []
    arm_integrity: list[bool] = []
    arm_equilibrium_pass: list[bool] = []
    arm_numerical_pass: list[bool] = []
    if checks.get("arm_order_and_count"):
        for arm, arm_spec in zip(arms, canonical["arms"]):
            integrity, equilibrium, numerical, arm_metrics = _arm_integrity(
                arm, arm_spec, canonical
            )
            arm_integrity.append(integrity)
            arm_equilibrium_pass.append(equilibrium)
            arm_numerical_pass.append(numerical)
            metrics.append(arm_metrics)
    checks["arm_integrity"] = bool(arm_integrity and all(arm_integrity))

    reached_eig = bool(
        checks.get("arm_order_and_count")
        and all(
            arm.get("scientific_error") in {None, "EIG calculation failed"}
            for arm in arms
        )
    )
    if reached_eig:
        try:
            left_matrix = arms[0]["matrix"]
            right_matrix = arms[1]["matrix"]
            base_catalog_identity = bool(
                left_matrix["dae_state_catalog"]
                == right_matrix["dae_state_catalog"]
                and left_matrix["dae_algebraic_names"]
                == right_matrix["dae_algebraic_names"]
                and left_matrix["dae_discrete_names"]
                == right_matrix["dae_discrete_names"]
                and left_matrix["eig_augmented_algebraic_names"]
                == right_matrix["eig_augmented_algebraic_names"]
            )
            both_eig_succeeded = all(
                arm.get("scientific_error") is None for arm in arms
            )
            reduced_catalog_identity = bool(
                not both_eig_succeeded
                or (
                    left_matrix["state_names"] == right_matrix["state_names"]
                    and len(left_matrix["as"]) == len(right_matrix["as"])
                )
            )
            checks["cross_arm_catalog_identity"] = bool(
                base_catalog_identity and reduced_catalog_identity
            )
        except (KeyError, TypeError):
            checks["cross_arm_catalog_identity"] = False
    else:
        checks["cross_arm_catalog_identity"] = True

    integrity_pass = all(checks.values())
    scientific_errors = [
        arm.get("scientific_error")
        for arm in arms
        if isinstance(arm, Mapping)
    ]
    equilibrium_pass = bool(
        arm_equilibrium_pass and all(arm_equilibrium_pass)
    )
    numerical_pass = bool(arm_numerical_pass and all(arm_numerical_pass))
    positive_count = int(metrics[0]["positive_real_count"]) if metrics else 0
    reproduction_pass = False
    if equilibrium_pass and numerical_pass and len(metrics) == 2:
        left_values = np.asarray(
            [
                complex(float(row["real"]), float(row["imag"]))
                for row in metrics[0]["leading_eigenvalues"]
            ],
            dtype=complex,
        )
        right_values = np.asarray(
            [
                complex(float(row["real"]), float(row["imag"]))
                for row in metrics[1]["leading_eigenvalues"]
            ],
            dtype=complex,
        )
        if len(left_values) == len(right_values) and len(left_values) > 0:
            distances = np.abs(left_values[:, None] - right_values[None, :]) / (
                1.0 + np.abs(left_values[:, None])
            )
            rows, columns = linear_sum_assignment(distances)
            leading_distance = float(np.max(distances[rows, columns]))
            reproduction_pass = bool(
                metrics[0]["positive_real_count"]
                == metrics[1]["positive_real_count"]
                and leading_distance
                <= canonical["cross_arm_leading_normalized_tolerance"]
            )
        else:
            leading_distance = None
    else:
        leading_distance = None
    checks["cross_arm_reproduction"] = reproduction_pass

    if not integrity_pass:
        classification = "ANALYSIS-INVALID"
    elif any(
        error in {"PFlow did not converge", "TDS initialization failed"}
        for error in scientific_errors
    ) or not equilibrium_pass:
        classification = "STOP-REGF2-EQUILIBRIUM-INVALID"
    elif any(error == "EIG calculation failed" for error in scientific_errors):
        classification = "STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED"
    elif not numerical_pass or not reproduction_pass:
        classification = "STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED"
    elif positive_count > 0:
        classification = "STOP-REGF2-POSITIVE-REAL-GUARD"
    else:
        classification = "REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE"

    return {
        "schema_version": 1,
        "round": "R390",
        "question": "Q-0108",
        "classification": classification,
        "checks": checks,
        "arms": metrics,
        "positive_real_count": positive_count,
        "cross_arm_leading_normalized_distance": leading_distance,
        "post_init_actions_authorized": False,
        "training_authorized": False,
        "next_gate": None,
    }
