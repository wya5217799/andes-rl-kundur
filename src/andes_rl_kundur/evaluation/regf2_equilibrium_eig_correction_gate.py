"""Science-identical R391 correction classifier for the invalid R390 gate."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from andes_rl_kundur.evaluation import regf2_equilibrium_eig_gate as parent

ROUND_ID = "R391"
QUESTION_ID = "Q-0108"
PARENT_R390_SHA256 = {
    "seal": "99c0b3c9dd1cf792d2d5343a2e63664c56a09aadf10de351584a8fefffe080fc",
    "attempt": "51344ed00e364c24fa3105ee38bbb321f0af79d7c96e6368ecf72a44fe02db35",
    "execution": "08cf8d8646bf1b65f017ddd3657f10449e434342f9b7df820ee56cef1f47340f",
    "analysis": "a6a0bd51dec900ac978993aeba86347b1535e6b1e8b3a76f3b70e60382523d0e",
    "manifest": "6255da6cef51d8ed230372a6b38cdbe07ae4797d3ce03dd2b1220e6beda2b64f",
    "claim": "d4b3b75ea53ce9a69bf6684dfd080aa611d3d6f626c442e15338d6c5079e2e28",
    "feed": "17eb82df481f27afdc0fe933d777f55e91168fb2051137bbe47baf6caefb0f77",
    "diagnosis": "f18a50e9192e7910984aab36e180fbd2c21d8e4166f9ce35a5289ab409d3bb64",
    "publication_audit": "864ac75987cac96bdf10e5f9791ee7a5ddb7ac015cfbeb62c4e97488e1a7601e",
    "verdict": "9dea3255817c47405d87a1ec90ce76a71bb4f5b2cdb6cea6225190f4bfc05ad7",
}
SPARSE_ADAPTER_RUNTIME = {
    "andes_shared_sha256": (
        "4de1748db771159d36cb30bf315f70956cfda6a9f7f6ca020ec74674d1e8c15c"
    ),
    "kvxopt_base_sha256": (
        "75d075ca30ca1d988b4218c0d9892264f14658fde94579ade94d9de42c76414b"
    ),
    "kvxopt_version": "1.3.3.1",
}


def payload_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_regf2_equilibrium_eig_correction_contract() -> dict[str, Any]:
    """Return R390's science unchanged plus R391 correction provenance."""

    parent_contract = parent.build_regf2_equilibrium_eig_contract()
    contract = deepcopy(parent_contract)
    contract.update(
        {
            "schema_version": 2,
            "round": ROUND_ID,
            "parent_round": "R390",
            "correction_of_contract_sha256": payload_sha256(parent_contract),
            "parent_r390_sha256": deepcopy(PARENT_R390_SHA256),
            "sparse_adapter_runtime": deepcopy(SPARSE_ADAPTER_RUNTIME),
            "evidence_corrections": [
                "installed_sparse_jacobian_conversion",
                "configured_index_to_display_ordinal_binding",
            ],
        }
    )
    return contract


def _expected_binding_keys(spec: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (model, f"{model}_{device}", variable)
        for model, variables in spec["registered_state_variables"].items()
        for device in range(1, 5)
        for variable in variables
    }


def _normalized_parent_record(
    record: Mapping[str, Any], spec: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Validate raw ANDES names and return a detached R390-compatible view."""

    try:
        if not (
            record["schema_version"] == 2
            and record["round"] == ROUND_ID
            and record["question"] == QUESTION_ID
            and record["contract_sha256"] == payload_sha256(spec)
            and isinstance(record["arms"], list)
            and len(record["arms"]) == len(spec["arms"])
        ):
            return None
        normalized = deepcopy(record)
        expected = _expected_binding_keys(spec)
        expected_replacements = {
            f"{variable} {model} {device}": f"{variable} {model} {model}_{device}"
            for model, variables in spec["registered_state_variables"].items()
            for device in range(1, 5)
            for variable in variables
        }
        for raw_arm, normalized_arm in zip(
            record["arms"], normalized["arms"], strict=True
        ):
            if not isinstance(raw_arm, Mapping):
                return None
            error = raw_arm.get("scientific_error")
            if error in {"PFlow did not converge", "TDS initialization failed"}:
                continue
            raw_matrix = raw_arm["matrix"]
            normalized_matrix = normalized_arm["matrix"]
            bindings = raw_matrix["state_bindings"]
            catalog = raw_matrix["dae_state_catalog"]
            if (
                not isinstance(bindings, list)
                or not isinstance(catalog, list)
                or not all(isinstance(row, Mapping) for row in catalog)
            ):
                return None
            seen: set[tuple[str, str, str]] = set()
            replacements: dict[str, str] = {}
            if error is None:
                for raw_binding, normalized_binding in zip(
                    bindings, normalized_matrix["state_bindings"], strict=True
                ):
                    if not isinstance(raw_binding, Mapping):
                        return None
                    key = (
                        raw_binding["model"],
                        raw_binding["idx"],
                        raw_binding["variable"],
                    )
                    if key not in expected or key in seen:
                        return None
                    seen.add(key)
                    model, idx, variable = key
                    prefix, separator, ordinal_text = idx.rpartition("_")
                    if separator != "_" or prefix != model:
                        return None
                    ordinal = int(ordinal_text)
                    if not 1 <= ordinal <= 4:
                        return None
                    raw_name = raw_binding["dae_name"]
                    address = raw_binding["original_address"]
                    if (
                        not isinstance(raw_name, str)
                        or raw_name.split() != [variable, model, str(ordinal)]
                        or isinstance(address, bool)
                        or not isinstance(address, int)
                        or not 0 <= address < len(catalog)
                        or catalog[address].get("name") != raw_name
                    ):
                        return None
                    normalized_name = f"{variable} {model} {idx}"
                    if (
                        raw_name in replacements
                        and replacements[raw_name] != normalized_name
                    ):
                        return None
                    replacements[raw_name] = normalized_name
                    normalized_binding["dae_name"] = normalized_name
                if seen != expected or replacements != expected_replacements:
                    return None
            elif error == "EIG calculation failed":
                catalog_names = [row.get("name") for row in catalog]
                if not all(name in catalog_names for name in expected_replacements):
                    return None
                replacements = expected_replacements
            else:
                return None
            for row in normalized_matrix["dae_state_catalog"]:
                row["name"] = replacements.get(row["name"], row["name"])
            for field in (
                "state_names",
                "zero_tf_state_names",
                "dae_algebraic_names",
                "dae_discrete_names",
                "eig_augmented_algebraic_names",
            ):
                normalized_matrix[field] = [
                    replacements.get(name, name) for name in normalized_matrix[field]
                ]

        parent_contract = parent.build_regf2_equilibrium_eig_contract()
        normalized["schema_version"] = parent_contract["schema_version"]
        normalized["round"] = parent_contract["round"]
        normalized["contract_sha256"] = payload_sha256(parent_contract)
        return normalized
    except (KeyError, TypeError, ValueError):
        return None


def _invalid_analysis(*, contract_ok: bool, raw_binding_ok: bool) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "classification": "ANALYSIS-INVALID",
        "checks": {
            "correction_contract": contract_ok,
            "raw_andes_state_binding": raw_binding_ok,
        },
        "arms": [],
        "positive_real_count": 0,
        "cross_arm_leading_normalized_distance": None,
        "post_init_actions_authorized": False,
        "next_gate": None,
        "training_authorized": False,
    }


def classify_regf2_equilibrium_eig_correction_record(
    record: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify R391 after raw-name validation and detached R390 replay."""

    canonical = build_regf2_equilibrium_eig_correction_contract()
    spec = canonical if contract is None else contract
    contract_ok = spec == canonical
    if not contract_ok:
        return _invalid_analysis(contract_ok=False, raw_binding_ok=False)
    normalized = _normalized_parent_record(record, spec)
    if normalized is None:
        return _invalid_analysis(contract_ok=True, raw_binding_ok=False)

    analysis = parent.classify_regf2_equilibrium_eig_record(normalized)
    corrected = deepcopy(analysis)
    corrected["schema_version"] = 2
    corrected["round"] = ROUND_ID
    corrected["parent_round"] = "R390"
    corrected["correction_of_contract_sha256"] = spec[
        "correction_of_contract_sha256"
    ]
    corrected["checks"] = {
        "correction_contract": True,
        "raw_andes_state_binding": True,
        **analysis["checks"],
    }
    return corrected


__all__ = [
    "PARENT_R390_SHA256",
    "SPARSE_ADAPTER_RUNTIME",
    "build_regf2_equilibrium_eig_correction_contract",
    "classify_regf2_equilibrium_eig_correction_record",
    "payload_sha256",
]
