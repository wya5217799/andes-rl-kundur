"""Result-blind R375 correction of the sealed R374 VSG identity contract."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

R374_CLASSIFIER_VSG_IDX = ("ES1", "ES2", "ES3", "ES4")
CORRECTED_VSG_IDX = ("VSG_1", "VSG_2", "VSG_3", "VSG_4")
EXPECTED_VSG_BUSES = (12, 16, 14, 15)


class IdentityContractError(ValueError):
    """Raised before performance analysis when VSG identity is inconsistent."""


def build_corrected_contract(parent_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Copy the R374 contract and change only its round and classifier identity."""

    corrected = copy.deepcopy(dict(parent_contract))
    corrected["round"] = "R375"
    corrected["expected_vsg_idx"] = list(CORRECTED_VSG_IDX)
    if not validate_contract_correction(parent_contract, corrected):
        raise IdentityContractError("parent contract is not the sealed R374 identity")
    return corrected


def validate_contract_correction(
    parent_contract: Mapping[str, Any],
    corrected_contract: Mapping[str, Any],
) -> bool:
    """Return true only for the two registered administrative differences."""

    try:
        parent = copy.deepcopy(dict(parent_contract))
        corrected = copy.deepcopy(dict(corrected_contract))
        if parent.get("round") != "R374":
            return False
        if tuple(parent.get("expected_vsg_idx", ())) != R374_CLASSIFIER_VSG_IDX:
            return False
        if tuple(parent.get("expected_vsg_buses", ())) != EXPECTED_VSG_BUSES:
            return False
        if corrected.get("round") != "R375":
            return False
        if tuple(corrected.get("expected_vsg_idx", ())) != CORRECTED_VSG_IDX:
            return False
        if tuple(corrected.get("expected_vsg_buses", ())) != EXPECTED_VSG_BUSES:
            return False
        if corrected.get("training_authorized") is not False:
            return False
        parent["round"] = "R375"
        parent["expected_vsg_idx"] = list(CORRECTED_VSG_IDX)
        return parent == corrected
    except (TypeError, ValueError):
        return False


def _plan_identity(plan_text: str) -> dict[str, Any]:
    idx_match = re.search(r"VSG_1\s*\.\.\s*VSG_4", plan_text)
    bus_match = re.search(r"\[\s*12\s*,\s*16\s*,\s*14\s*,\s*15\s*\]", plan_text)
    if idx_match is None or bus_match is None:
        raise IdentityContractError("R374 plan identity is missing or ambiguous")
    return {
        "n_agents": 4,
        "vsg_idx": list(CORRECTED_VSG_IDX),
        "vsg_buses": list(EXPECTED_VSG_BUSES),
    }


_IDENTITY_PATTERN = re.compile(rb'"identity":(\{[^{}]*\})')
_RECORD_COUNT_PATTERN = re.compile(rb'"record_count":(\d+)')


def scan_execution_identities(path: Path) -> dict[str, Any]:
    """Extract only execution identity objects without decoding step arrays."""

    identities: list[dict[str, Any]] = []
    record_count: int | None = None
    overlap = b""
    absolute_offset = 0
    last_match_start = -1
    with path.open("rb") as stream:
        while chunk := stream.read(64 * 1024):
            data = overlap + chunk
            base_offset = absolute_offset - len(overlap)
            if record_count is None:
                count_match = _RECORD_COUNT_PATTERN.search(data)
                if count_match is not None:
                    record_count = int(count_match.group(1))
            for match in _IDENTITY_PATTERN.finditer(data):
                match_start = base_offset + match.start()
                if match_start <= last_match_start:
                    continue
                try:
                    identity = json.loads(match.group(1))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise IdentityContractError("malformed runtime identity") from exc
                if not isinstance(identity, dict):
                    raise IdentityContractError("runtime identity is not an object")
                identities.append(identity)
                last_match_start = match_start
            overlap = data[-4096:]
            absolute_offset += len(chunk)
    if record_count is None:
        raise IdentityContractError("execution record_count is missing")
    if len(identities) != record_count:
        raise IdentityContractError("runtime identity count does not match record_count")
    return {
        "record_count": record_count,
        "identities": identities,
        "performance_fields_parsed": False,
    }


def require_identity_alignment(
    *,
    plan_text: str,
    execution_identity_scan: Mapping[str, Any],
    corrected_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove plan, runtime, and classifier identity equality before analysis."""

    classifier_identity = {
        "n_agents": int(corrected_contract.get("device_count", -1)),
        "vsg_idx": list(corrected_contract.get("expected_vsg_idx", ())),
        "vsg_buses": list(corrected_contract.get("expected_vsg_buses", ())),
    }
    expected = {
        "n_agents": 4,
        "vsg_idx": list(CORRECTED_VSG_IDX),
        "vsg_buses": list(EXPECTED_VSG_BUSES),
    }
    if classifier_identity != expected:
        raise IdentityContractError("corrected classifier identity drift")
    plan_identity = _plan_identity(plan_text)
    if plan_identity != expected:
        raise IdentityContractError("plan identity drift")
    if execution_identity_scan.get("performance_fields_parsed") is not False:
        raise IdentityContractError("performance fields were parsed before seal")
    identities = list(execution_identity_scan.get("identities", ()))
    record_count = int(execution_identity_scan.get("record_count", -1))
    if record_count <= 0 or len(identities) != record_count:
        raise IdentityContractError("runtime identity count drift")
    if any(dict(identity) != expected for identity in identities):
        raise IdentityContractError("runtime identity drift")
    unique = {
        json.dumps(identity, sort_keys=True, separators=(",", ":"))
        for identity in identities
    }
    return {
        "valid": True,
        "plan_identity": plan_identity,
        "classifier_identity": classifier_identity,
        "runtime_record_count": record_count,
        "unique_runtime_identity_count": len(unique),
        "performance_fields_parsed": False,
    }
