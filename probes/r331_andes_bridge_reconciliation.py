"""Fail-closed classifier for the R331 ANDES bridge reconciliation.

R331 is a static, source-bound gate.  It does not execute a controller or an
ANDES trajectory.  The classifier first checks that the reconciliation record
is complete and primary-source bound, then separates load-bearing bridge
blockers from honest scope qualifications.  A structurally invalid record
cannot produce an ALLOW, QUALIFY, or BLOCK platform judgment.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MAPPING_IDS = frozenset(
    {
        "platform_scope",
        "bases_and_frequency",
        "device_identity",
        "delivered_outputs",
        "action_mapping",
        "feasibility_limits",
        "storage_dynamics",
        "sample_timing",
        "disturbance_and_initialization",
        "reduced_latent_state",
    }
)

REQUIRED_MAPPING_FIELDS = frozenset(
    {
        "id",
        "reduced_model_meaning",
        "implementation_locators",
        "official_locators",
        "unit",
        "base",
        "sign",
        "sample_time",
        "disposition",
        "claim_ceiling_consequence",
    }
)

ALLOWED_DISPOSITIONS = frozenset(
    {"exact", "derived", "declared-assumption", "declared-omission", "unsupported"}
)
QUALIFYING_DISPOSITIONS = frozenset({"declared-assumption", "declared-omission"})
BLOCKING_DISPOSITIONS = frozenset({"unsupported"})

SOURCE_IDENTITY_FIELDS = frozenset(
    {
        "repository_sources_match",
        "installed_andes_version",
        "installed_sources_match",
        "installed_semantics_match",
        "official_sources_primary",
    }
)

SEMANTIC_GUARD_IDS = (
    "no_hidden_md_write",
    "requested_projected_internal_achieved_distinguished",
    "active_power_incidence_sign_correct",
    "physical_frequency_base_60_hz",
    "sample_order_and_delay_explicit",
    "disturbance_and_initialization_explicit",
    "all_feasibility_limits_explicit",
    "reduced_latent_state_not_claimed_as_physical_readback",
    "platform_claim_ceiling_respected",
)

SCOPE_GUARD_IDS = (
    "physical_execution_performed",
    "controller_executed",
    "distributed_runtime_executed",
    "training_executed",
    "eval_executed",
)


def _is_nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_locator_list(value: object) -> bool:
    return bool(
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) > 0
        and all(_is_nonempty_text(item) for item in value)
    )


def _implementation_locator_resolves(locator: str) -> bool:
    """Resolve the file portion and any declared line of a repository locator."""

    file_part = locator.split("#", 1)[0]
    line_number: int | None = None
    candidate, separator, suffix = file_part.rpartition(":")
    if separator and suffix.isdigit():
        file_part = candidate
        line_number = int(suffix)
    path = Path(file_part)
    if path.is_absolute() or not file_part or ".." in path.parts:
        return False
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return False
    if not resolved.is_file():
        return False
    if line_number is not None:
        if line_number < 1:
            return False
        with resolved.open("r", encoding="utf-8") as handle:
            if sum(1 for _ in handle) < line_number:
                return False
    return True


def _official_locator_is_versioned_primary(locator: str) -> bool:
    parsed = urlparse(locator)
    if parsed.scheme != "https":
        return False
    if parsed.netloc == "docs.andes.app":
        return parsed.path.startswith("/en/v2.0.0/")
    if parsed.netloc == "github.com":
        return parsed.path.startswith("/CURENT/andes/blob/v2.0.0/")
    return False


def _mapping_rows(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _inventory_valid(rows: list[Mapping[str, Any]], raw_rows: object) -> bool:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        return False
    identifiers = [str(row.get("id", "")) for row in rows]
    return bool(
        len(rows) == len(raw_rows) == len(REQUIRED_MAPPING_IDS)
        and len(set(identifiers)) == len(identifiers)
        and set(identifiers) == set(REQUIRED_MAPPING_IDS)
    )


def _mapping_fields_and_locators_valid(rows: list[Mapping[str, Any]]) -> bool:
    for row in rows:
        if not REQUIRED_MAPPING_FIELDS <= set(row):
            return False
        if str(row.get("disposition")) not in ALLOWED_DISPOSITIONS:
            return False
        if not _is_locator_list(row.get("implementation_locators")):
            return False
        if not _is_locator_list(row.get("official_locators")):
            return False
        if not all(
            _implementation_locator_resolves(str(locator))
            for locator in row["implementation_locators"]
        ):
            return False
        if not all(
            _official_locator_is_versioned_primary(str(locator))
            for locator in row["official_locators"]
        ):
            return False
        if not all(
            _is_nonempty_text(row.get(field))
            for field in (
                "reduced_model_meaning",
                "unit",
                "base",
                "sign",
                "sample_time",
                "claim_ceiling_consequence",
            )
        ):
            return False
    return True


def _source_identity_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or not SOURCE_IDENTITY_FIELDS <= set(value):
        return False
    return bool(
        value.get("repository_sources_match") is True
        and value.get("installed_andes_version") == "2.0.0"
        and value.get("installed_sources_match") is True
        and value.get("installed_semantics_match") is True
        and value.get("official_sources_primary") is True
    )


def _scope_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or not set(SCOPE_GUARD_IDS) <= set(value):
        return False
    return all(value.get(identifier) is False for identifier in SCOPE_GUARD_IDS)


def _semantic_guards(value: object) -> dict[str, bool]:
    if not isinstance(value, Mapping):
        return {identifier: False for identifier in SEMANTIC_GUARD_IDS}
    return {identifier: value.get(identifier) is True for identifier in SEMANTIC_GUARD_IDS}


def evaluate_bridge_reconciliation(payload: object) -> dict[str, Any]:
    """Return the registered R331 platform judgment and explicit failures."""

    if not isinstance(payload, Mapping):
        return {
            "classification": "INVALID-BRIDGE-RECONCILIATION",
            "validity_guards": {"payload_mapping": False},
            "bridge_guards": {},
            "blocking_mapping_ids": [],
            "blocking_guard_ids": [],
            "qualification_ids": [],
        }

    raw_rows = payload.get("mapping_rows")
    rows = _mapping_rows(raw_rows)
    validity_guards = {
        "identity": (
            payload.get("schema_version") == 1
            and payload.get("round") == "R331"
            and payload.get("question") == "Q-0084"
        ),
        "mapping_inventory": _inventory_valid(rows, raw_rows),
        "mapping_fields_and_locators": _mapping_fields_and_locators_valid(rows),
        "source_identity": _source_identity_valid(payload.get("source_identity")),
        "scope": _scope_valid(payload.get("scope_guards")),
        "deterministic_replay": payload.get("deterministic_replay") is True,
    }

    if not all(validity_guards.values()):
        return {
            "classification": "INVALID-BRIDGE-RECONCILIATION",
            "validity_guards": validity_guards,
            "bridge_guards": {},
            "blocking_mapping_ids": [],
            "blocking_guard_ids": [],
            "qualification_ids": [],
            "claim_ceiling": "invalid reconciliation; no platform judgment admissible",
        }

    bridge_guards = _semantic_guards(payload.get("semantic_guards"))
    bridge_guards["all"] = all(bridge_guards.values())
    blocking_mapping_ids = sorted(
        str(row["id"]) for row in rows if str(row["disposition"]) in BLOCKING_DISPOSITIONS
    )
    blocking_guard_ids = sorted(
        identifier for identifier in SEMANTIC_GUARD_IDS if not bridge_guards[identifier]
    )
    qualification_ids = sorted(
        str(row["id"]) for row in rows if str(row["disposition"]) in QUALIFYING_DISPOSITIONS
    )

    if blocking_mapping_ids or blocking_guard_ids:
        classification = "BLOCK"
    elif qualification_ids:
        classification = "QUALIFY"
    else:
        classification = "ALLOW"

    return {
        "classification": classification,
        "validity_guards": validity_guards,
        "bridge_guards": bridge_guards,
        "blocking_mapping_ids": blocking_mapping_ids,
        "blocking_guard_ids": blocking_guard_ids,
        "qualification_ids": qualification_ids,
        "mapping_count": len(rows),
        "claim_ceiling": (
            "prospective deterministic phasor-domain electromechanical ANDES "
            "bridge design only; no controller-performance, EMT, hardware, "
            "distributed-agent, learning, safety, stability, or topology claim"
        ),
    }
