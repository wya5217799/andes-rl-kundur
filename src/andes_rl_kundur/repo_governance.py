"""Repository-wide governance behind one validation interface.

The research ledger has its own validator. This module deliberately owns only
repository structure: root entries, canonical/derived artifacts, navigation
pointers, future round-document budgets, opaque subtrees, and the debt
baseline. Callers should use
``validate_repository`` or the ``scripts/repo_health.py`` CLI adapter.

The validator never mutates the repository. Invalid or missing policy produces
an actionable finding instead of a traceback.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

CONTRACT_PATH = Path("docs/repo-hygiene/contract.json")
_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


@dataclass(frozen=True)
class Finding:
    """One stable, externally reportable repository-policy violation."""

    rule_id: str
    path: str
    message: str
    severity: str = "error"
    baselined: bool = False

    @property
    def fingerprint(self) -> str:
        payload = f"{self.rule_id}\0{self.path}".encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "fingerprint": self.fingerprint,
            "baselined": self.baselined,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Repository findings after the checked-in debt baseline is applied."""

    root: Path
    findings: tuple[Finding, ...]

    @property
    def active_findings(self) -> tuple[Finding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity == "error" and not finding.baselined
        )

    @property
    def exit_code(self) -> int:
        return 1 if self.active_findings else 0

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root.as_posix(),
            "ok": self.exit_code == 0,
            "active_count": len(self.active_findings),
            "baselined_count": sum(item.baselined for item in self.findings),
            "findings": [item.as_dict() for item in self.findings],
        }


class ContractError(ValueError):
    """The repository contract cannot be interpreted safely."""


def repository_root() -> Path:
    """Return the checkout root without relying on the caller's cwd."""

    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"expected JSON object in {path}")
    return raw


def _relative_path(value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{field} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ContractError(f"{field} must stay inside the repository: {value}")
    return path


def _list_of_strings(value: object, *, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractError(f"{field} must be a list of strings")
    return value


def _root_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    root_policy = contract.get("root")
    if not isinstance(root_policy, dict):
        raise ContractError("root must be an object")
    allowed = set(_list_of_strings(root_policy.get("allowed", []), field="root.allowed"))
    allowed.update(_list_of_strings(root_policy.get("tool_state", []), field="root.tool_state"))
    allowed_globs = _list_of_strings(
        root_policy.get("allowed_globs", []),
        field="root.allowed_globs",
    )

    for entry in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if entry.name in allowed:
            continue
        if any(fnmatch.fnmatch(entry.name, pattern) for pattern in allowed_globs):
            continue
        yield Finding(
            "ROOT_UNDECLARED",
            entry.name,
            "root entry is not declared by the repository contract",
        )


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_input(path: Path) -> str:
    """Hash one file or a deterministic snapshot of a directory tree."""

    if path.is_file():
        return _hash_file(path)
    if not path.is_dir():
        raise OSError(f"input path is neither a file nor a directory: {path}")

    digest = hashlib.sha256()
    digest.update(b"directory-tree-v1\0")
    files = sorted(
        (candidate for candidate in path.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(path).as_posix(),
    )
    for candidate in files:
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(bytes.fromhex(_hash_file(candidate)))
    return digest.hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ContractError(f"{path}: missing YAML frontmatter")
    try:
        value = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ContractError(f"{path}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path}: frontmatter must be an object")
    return value


def _manuscript_reference_targets(
    root: Path,
    line_path: Path,
    metadata: dict[str, Any],
) -> tuple[set[Path], tuple[Finding, ...]]:
    """Validate lazy navigation pointers and return their feed targets."""

    findings: list[Finding] = []
    evidence_targets: set[Path] = set()
    evidence_values = metadata.get("evidence_refs", [])
    if not isinstance(evidence_values, list) or not all(
        isinstance(value, str) for value in evidence_values
    ):
        findings.append(
            Finding(
                "MANUSCRIPT_REFERENCE_INVALID",
                line_path.as_posix(),
                "evidence_refs must be a list of CLM-NNNN -> path pointers",
            )
        )
        evidence_values = []
    for value in evidence_values:
        match = re.fullmatch(r"(CLM-\d+)\s*->\s*(.+)", value)
        if match is None:
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_INVALID",
                    line_path.as_posix(),
                    f"invalid evidence ref: {value}",
                )
            )
            continue
        claim_id = match.group(1)
        try:
            feed_path = _relative_path(
                match.group(2).strip(),
                field="evidence_refs",
            )
        except ContractError as exc:
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_INVALID",
                    line_path.as_posix(),
                    str(exc),
                )
            )
            continue
        if not _is_within(feed_path, line_path.parent):
            findings.append(
                Finding(
                    "MANUSCRIPT_EVIDENCE_SCOPE_ESCAPE",
                    line_path.as_posix(),
                    f"evidence target must stay inside the manuscript root: {value}",
                )
            )
            continue
        claim_path = Path("memory") / "claims" / f"{claim_id}.md"
        if not (root / claim_path).is_file() or not (root / feed_path).is_file():
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_MISSING",
                    line_path.as_posix(),
                    f"evidence ref does not resolve: {value}",
                )
            )
            continue
        try:
            claim_text = (root / claim_path).read_text(encoding="utf-8")
            feed_text = (root / feed_path).read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_MISSING",
                    line_path.as_posix(),
                    f"cannot read evidence ref {value}: {exc}",
                )
            )
            continue
        if feed_path.as_posix() not in claim_text or claim_id not in feed_text:
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_UNBOUND",
                    line_path.as_posix(),
                    f"claim and feed do not bind each other: {value}",
                )
            )
            continue
        evidence_targets.add(feed_path)

    decision_values = metadata.get("decision_refs", [])
    if not isinstance(decision_values, list) or not all(
        isinstance(value, str) for value in decision_values
    ):
        findings.append(
            Finding(
                "MANUSCRIPT_REFERENCE_INVALID",
                line_path.as_posix(),
                "decision_refs must be a list of path#locator pointers",
            )
        )
        decision_values = []
    for value in decision_values:
        path_text, separator, locator = value.partition("#")
        try:
            decision_path = _relative_path(
                path_text.strip(),
                field="decision_refs",
            )
        except ContractError as exc:
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_INVALID",
                    line_path.as_posix(),
                    str(exc),
                )
            )
            continue
        if not separator or not locator.strip():
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_INVALID",
                    line_path.as_posix(),
                    f"decision ref has no locator: {value}",
                )
            )
        elif not (root / decision_path).is_file():
            findings.append(
                Finding(
                    "MANUSCRIPT_REFERENCE_MISSING",
                    line_path.as_posix(),
                    f"decision ref does not resolve: {value}",
                )
            )

    return evidence_targets, tuple(findings)


def _artifact_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    artifacts = contract.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ContractError("artifacts must be a list")
    canonical_paths: set[Path] = set()
    derived_paths: set[Path] = set()

    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ContractError(f"artifacts[{index}] must be an object")
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ContractError(f"artifacts[{index}].id must be a non-empty string")
        canonical = _relative_path(
            artifact.get("canonical"),
            field=f"artifacts[{index}].canonical",
        )
        derived_values = _list_of_strings(
            artifact.get("derived", []),
            field=f"artifacts[{index}].derived",
        )
        relation = artifact.get("relation", "declared")
        if relation not in {"declared", "byte-identical"}:
            raise ContractError(f"artifacts[{index}].relation must be declared or byte-identical")

        if canonical in canonical_paths or canonical in derived_paths:
            yield Finding(
                "ARTIFACT_ROLE_CONFLICT",
                canonical.as_posix(),
                f"artifact path has more than one role ({artifact_id})",
            )
        canonical_paths.add(canonical)
        canonical_on_disk = root / canonical
        if not canonical_on_disk.is_file():
            yield Finding(
                "CANONICAL_MISSING",
                canonical.as_posix(),
                f"canonical artifact is missing ({artifact_id})",
            )

        for derived_value in derived_values:
            derived = _relative_path(
                derived_value,
                field=f"artifacts[{index}].derived",
            )
            if derived == canonical or derived in canonical_paths or derived in derived_paths:
                yield Finding(
                    "ARTIFACT_ROLE_CONFLICT",
                    derived.as_posix(),
                    f"artifact path has more than one role ({artifact_id})",
                )
            derived_paths.add(derived)
            derived_on_disk = root / derived
            if not derived_on_disk.is_file():
                yield Finding(
                    "DERIVED_MISSING",
                    derived.as_posix(),
                    f"derived artifact is missing ({artifact_id})",
                )
                continue
            if (
                relation == "byte-identical"
                and canonical_on_disk.is_file()
                and _hash_file(canonical_on_disk) != _hash_file(derived_on_disk)
            ):
                yield Finding(
                    "DERIVED_DRIFT",
                    derived.as_posix(),
                    f"derived artifact differs from {canonical.as_posix()} ({artifact_id})",
                )


def _navigation_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    navigation = contract.get("navigation", [])
    if not isinstance(navigation, list):
        raise ContractError("navigation must be a list")

    for index, item in enumerate(navigation):
        if not isinstance(item, dict):
            raise ContractError(f"navigation[{index}] must be an object")
        adapter = _relative_path(
            item.get("adapter"),
            field=f"navigation[{index}].adapter",
        )
        targets = _list_of_strings(
            item.get("must_reference", []),
            field=f"navigation[{index}].must_reference",
        )
        forbidden_fragments = _list_of_strings(
            item.get("forbid_text", []),
            field=f"navigation[{index}].forbid_text",
        )
        adapter_on_disk = root / adapter
        if not adapter_on_disk.is_file():
            yield Finding(
                "NAV_ADAPTER_MISSING",
                adapter.as_posix(),
                "navigation adapter is missing",
            )
            continue
        try:
            content = adapter_on_disk.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            yield Finding(
                "NAV_ADAPTER_UNREADABLE",
                adapter.as_posix(),
                "navigation adapter is not UTF-8 text",
            )
            continue
        for fragment in forbidden_fragments:
            if fragment in content:
                yield Finding(
                    "NAV_FORBIDDEN_TEXT",
                    adapter.as_posix(),
                    f"navigation adapter contains stale copy marker: {fragment}",
                )
        for target_value in targets:
            target = _relative_path(
                target_value,
                field=f"navigation[{index}].must_reference",
            )
            if not (root / target).exists():
                yield Finding(
                    "NAV_TARGET_MISSING",
                    target.as_posix(),
                    f"target required by {adapter.as_posix()} is missing",
                )
            elif target.as_posix() not in content and str(target) not in content:
                yield Finding(
                    "NAV_POINTER_MISSING",
                    adapter.as_posix(),
                    f"adapter does not reference {target.as_posix()}",
                )


def _delivery_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    lines = contract.get("delivery_lines", [])
    if not isinstance(lines, list):
        raise ContractError("delivery_lines must be a list")
    discovery = _list_of_strings(
        contract.get("delivery_discovery", []),
        field="delivery_discovery",
    )
    binary_extensions = {
        extension.casefold()
        for extension in _list_of_strings(
            contract.get("delivery_binary_extensions", []),
            field="delivery_binary_extensions",
        )
    }
    if any(not extension.startswith(".") for extension in binary_extensions):
        raise ContractError("delivery_binary_extensions values must start with '.'")
    valid_kinds = {
        "external-report",
        "manuscript",
        "plan",
        "proposal",
        "review",
        "teaching",
    }
    valid_statuses = {"active", "archived", "frozen"}
    valid_roles = {
        "archive",
        "canonical",
        "corpus",
        "derived",
        "release",
        "reports",
        "support",
    }
    seen_ids: set[str] = set()
    registered_roots: set[Path] = set()

    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise ContractError(f"delivery_lines[{index}] must be an object")
        line_id = line.get("id")
        if not isinstance(line_id, str) or not line_id:
            raise ContractError(f"delivery_lines[{index}].id must be a string")
        kind = line.get("kind")
        if kind not in valid_kinds:
            raise ContractError(
                f"delivery_lines[{index}].kind must be one of {sorted(valid_kinds)}"
            )
        status = line.get("status")
        if status not in valid_statuses:
            raise ContractError(
                f"delivery_lines[{index}].status must be one of {sorted(valid_statuses)}"
            )
        line_root = _relative_path(
            line.get("root"),
            field=f"delivery_lines[{index}].root",
        )
        if line_id in seen_ids:
            yield Finding(
                "DELIVERY_ID_DUPLICATE",
                line_id,
                "delivery line id must be unique",
            )
        seen_ids.add(line_id)
        if line_root in registered_roots:
            yield Finding(
                "DELIVERY_ROOT_DUPLICATE",
                line_root.as_posix(),
                "delivery root must belong to one registered line",
            )
        registered_roots.add(line_root)
        if not (root / line_root).exists():
            yield Finding(
                "DELIVERY_ROOT_MISSING",
                line_root.as_posix(),
                f"delivery root is missing ({line_id})",
            )

        roles = line.get("roles")
        if not isinstance(roles, dict):
            raise ContractError(f"delivery_lines[{index}].roles must be an object")
        unknown_roles = set(roles) - valid_roles
        if unknown_roles:
            raise ContractError(
                f"delivery_lines[{index}].roles has unknown keys: {sorted(unknown_roles)}"
            )
        canonical = roles.get("canonical", [])
        if not canonical:
            raise ContractError(f"delivery_lines[{index}].roles.canonical must not be empty")

        path_roles: dict[Path, str] = {}
        for role in sorted(roles):
            values = _list_of_strings(
                roles[role],
                field=f"delivery_lines[{index}].roles.{role}",
            )
            for value in values:
                path = _relative_path(
                    value,
                    field=f"delivery_lines[{index}].roles.{role}",
                )
                previous_role = path_roles.get(path)
                if previous_role is not None:
                    yield Finding(
                        "DELIVERY_ROLE_CONFLICT",
                        path.as_posix(),
                        f"path has both {previous_role} and {role} roles ({line_id})",
                    )
                else:
                    path_roles[path] = role
                if not (root / path).exists():
                    yield Finding(
                        "DELIVERY_PATH_MISSING",
                        path.as_posix(),
                        f"{role} path is missing ({line_id})",
                    )

        line_root_on_disk = root / line_root
        if line_root_on_disk.is_dir() and binary_extensions:
            declared_paths = tuple(path_roles)
            for candidate in sorted(line_root_on_disk.rglob("*")):
                if not candidate.is_file():
                    continue
                if candidate.suffix.casefold() not in binary_extensions:
                    continue
                relative = candidate.relative_to(root)
                covered = any(
                    relative == declared
                    or ((root / declared).is_dir() and declared in relative.parents)
                    for declared in declared_paths
                )
                if not covered:
                    yield Finding(
                        "DELIVERY_BINARY_UNDECLARED",
                        relative.as_posix(),
                        f"binary is not assigned a delivery role ({line_id})",
                    )

    for pattern in discovery:
        for candidate in sorted(root.glob(pattern)):
            if not candidate.is_dir():
                continue
            relative = candidate.relative_to(root)
            if relative not in registered_roots:
                yield Finding(
                    "DELIVERY_UNREGISTERED",
                    relative.as_posix(),
                    f"directory matches delivery discovery pattern {pattern}",
                )


def _artifact_manifest_findings(
    root: Path,
    *,
    line_id: str,
    line_root: Path,
    manifest_path: Path,
    policy: dict[str, Any],
    line_metadata: dict[str, Any],
    required_reading: tuple[Path, ...],
) -> Iterable[Finding]:
    manifest_on_disk = root / manifest_path
    if not manifest_on_disk.is_file():
        yield Finding(
            "DOCUMENT_MANIFEST_MISSING",
            manifest_path.as_posix(),
            f"active manuscript line {line_id} has no artifact manifest",
        )
        return
    try:
        manifest = _load_json(manifest_on_disk)
    except ContractError as exc:
        yield Finding("DOCUMENT_MANIFEST_INVALID", manifest_path.as_posix(), str(exc))
        return
    if manifest.get("version") != 1 or manifest.get("line_id") != line_id:
        yield Finding(
            "DOCUMENT_MANIFEST_INVALID",
            manifest_path.as_posix(),
            "manifest version must be 1 and line_id must match the delivery line",
        )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        yield Finding(
            "DOCUMENT_MANIFEST_INVALID",
            manifest_path.as_posix(),
            "artifacts must be a list",
        )
        return

    valid_statuses = set(
        _list_of_strings(
            policy.get(
                "artifact_statuses",
                ["active", "frozen", "stale", "superseded"],
            ),
            field="manuscript_lines.artifact_statuses",
        )
    )
    time_sensitive = set(
        _list_of_strings(
            policy.get("time_sensitive_purposes", []),
            field="manuscript_lines.time_sensitive_purposes",
        )
    )
    transient_patterns = _list_of_strings(
        policy.get("transient_patterns", []),
        field="manuscript_lines.transient_patterns",
    )
    seen_ids: set[str] = set()
    records: dict[str, dict[str, Any]] = {}
    active_canonical: dict[str, str] = {}
    registered_paths: set[Path] = set()

    for index, artifact in enumerate(artifacts):
        location = f"{manifest_path.as_posix()}#artifacts[{index}]"
        if not isinstance(artifact, dict):
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "artifact record must be an object",
            )
            continue
        artifact_id = artifact.get("id")
        purpose = artifact.get("purpose")
        status = artifact.get("status")
        producer = artifact.get("producer")
        canonical = artifact.get("canonical")
        authoritative = artifact.get("authoritative")
        if not isinstance(artifact_id, str) or not artifact_id:
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "id must be a non-empty string",
            )
            continue
        if artifact_id in seen_ids:
            yield Finding(
                "DOCUMENT_ID_DUPLICATE",
                manifest_path.as_posix(),
                f"artifact id must be unique: {artifact_id}",
            )
        seen_ids.add(artifact_id)
        records[artifact_id] = artifact
        if not isinstance(purpose, str) or not purpose:
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "purpose must be a non-empty string",
            )
            continue
        if status not in valid_statuses:
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                f"status must be one of {sorted(valid_statuses)}",
            )
        if not isinstance(producer, str) or not producer:
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "producer must be a non-empty string",
            )
        if not isinstance(canonical, bool) or not isinstance(authoritative, bool):
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "canonical and authoritative must be booleans",
            )
        if status == "active" and canonical is True:
            previous = active_canonical.get(purpose)
            if previous is not None:
                yield Finding(
                    "DOCUMENT_CANONICAL_DUPLICATE",
                    manifest_path.as_posix(),
                    f"purpose {purpose} has active canonical artifacts "
                    f"{previous} and {artifact_id}",
                )
            active_canonical[purpose] = artifact_id

        try:
            artifact_path = _relative_path(
                artifact.get("path"),
                field=f"artifacts[{index}].path",
            )
        except ContractError as exc:
            yield Finding("DOCUMENT_RECORD_INVALID", location, str(exc))
            continue
        if not _is_within(artifact_path, line_root):
            yield Finding(
                "DOCUMENT_SCOPE_ESCAPE",
                artifact_path.as_posix(),
                f"artifact owned by {line_id} must stay inside {line_root.as_posix()}",
            )
        else:
            registered_paths.add(artifact_path)
        if not (root / artifact_path).exists():
            yield Finding(
                "DOCUMENT_PATH_MISSING",
                artifact_path.as_posix(),
                f"registered artifact is missing ({artifact_id})",
            )

        inputs = artifact.get("inputs", [])
        if not isinstance(inputs, list) or not all(isinstance(value, str) for value in inputs):
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "inputs must be a list of repository-relative paths",
            )
            inputs = []
        for input_index, value in enumerate(inputs):
            try:
                input_path = _relative_path(
                    value,
                    field=f"artifacts[{index}].inputs[{input_index}]",
                )
            except ContractError as exc:
                yield Finding("DOCUMENT_RECORD_INVALID", location, str(exc))
                continue
            if not (root / input_path).exists():
                yield Finding(
                    "DOCUMENT_INPUT_MISSING",
                    input_path.as_posix(),
                    f"input for {artifact_id} is missing",
                )

        review_after = artifact.get("review_after")
        if purpose in time_sensitive and not isinstance(review_after, str):
            yield Finding(
                "DOCUMENT_REVIEW_DATE_MISSING",
                location,
                f"time-sensitive purpose {purpose} requires review_after",
            )
        if review_after is not None:
            if not isinstance(review_after, str):
                yield Finding(
                    "DOCUMENT_RECORD_INVALID",
                    location,
                    "review_after must be an ISO date or null",
                )
            else:
                try:
                    deadline = date.fromisoformat(review_after)
                except ValueError:
                    yield Finding(
                        "DOCUMENT_RECORD_INVALID",
                        location,
                        "review_after must use YYYY-MM-DD",
                    )
                else:
                    if status == "active" and deadline < date.today():
                        yield Finding(
                            "DOCUMENT_REVIEW_EXPIRED",
                            artifact_path.as_posix(),
                            f"{artifact_id} passed its review_after date {review_after}",
                        )

        input_hashes = artifact.get("input_hashes", {})
        if not isinstance(input_hashes, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in input_hashes.items()
        ):
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                location,
                "input_hashes must map repository-relative paths to SHA-256 strings",
            )
        else:
            for value, expected_hash in input_hashes.items():
                if value not in inputs:
                    yield Finding(
                        "DOCUMENT_RECORD_INVALID",
                        location,
                        f"input_hashes key is not declared in inputs: {value}",
                    )
                if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
                    yield Finding(
                        "DOCUMENT_RECORD_INVALID",
                        location,
                        f"input_hashes value is not SHA-256: {value}",
                    )
                    continue
                try:
                    input_path = _relative_path(
                        value,
                        field=f"artifacts[{index}].input_hashes",
                    )
                except ContractError as exc:
                    yield Finding("DOCUMENT_RECORD_INVALID", location, str(exc))
                    continue
                input_on_disk = root / input_path
                if status == "active" and input_on_disk.exists():
                    try:
                        actual_hash = _hash_input(input_on_disk)
                    except OSError as exc:
                        yield Finding(
                            "DOCUMENT_INPUT_UNREADABLE",
                            input_path.as_posix(),
                            f"cannot hash input for {artifact_id}: {exc}",
                        )
                    else:
                        if actual_hash.casefold() != expected_hash.casefold():
                            yield Finding(
                                "DOCUMENT_INPUT_DRIFT",
                                artifact_path.as_posix(),
                                f"{artifact_id} input changed: {input_path.as_posix()}",
                            )

    active_line_states = [
        artifact
        for artifact in records.values()
        if artifact.get("purpose") == "line-state"
        and artifact.get("status") == "active"
        and artifact.get("canonical") is True
    ]
    authoritative_feed_sets = [
        artifact
        for artifact in records.values()
        if artifact.get("purpose") == "experiment-feeds"
        and artifact.get("status") == "active"
        and artifact.get("canonical") is True
        and artifact.get("authoritative") is True
    ]
    line_path = line_root / str(policy.get("entry_name", "LINE.md"))
    evidence_targets, reference_findings = _manuscript_reference_targets(
        root,
        line_path,
        line_metadata,
    )
    yield from reference_findings
    if authoritative_feed_sets:
        if len(active_line_states) != 1:
            yield Finding(
                "DOCUMENT_NAVIGATION_WATCH_MISSING",
                manifest_path.as_posix(),
                "an authoritative experiment-feeds artifact requires exactly one "
                "active canonical line-state artifact",
            )
        else:
            line_state = active_line_states[0]
            line_state_path = line_state.get("path")
            finding_path = (
                line_state_path if isinstance(line_state_path, str) else manifest_path.as_posix()
            )
            line_inputs = line_state.get("inputs", [])
            line_hashes = line_state.get("input_hashes", {})
            for feed_set in authoritative_feed_sets:
                feed_path = feed_set.get("path")
                if not isinstance(feed_path, str):
                    continue
                if (
                    not isinstance(line_inputs, list)
                    or feed_path not in line_inputs
                    or not isinstance(line_hashes, dict)
                    or feed_path not in line_hashes
                ):
                    yield Finding(
                        "DOCUMENT_NAVIGATION_WATCH_MISSING",
                        finding_path,
                        "line-state must declare and hash authoritative "
                        f"experiment feeds: {feed_path}",
                    )
                feed_root = Path(feed_path)
                eager = [
                    path.as_posix() for path in required_reading if _is_within(path, feed_root)
                ]
                if eager:
                    yield Finding(
                        "MANUSCRIPT_EAGER_EVIDENCE_LOAD",
                        finding_path,
                        "required_reading must use evidence_refs instead of "
                        f"loading experiment feeds: {eager}",
                    )
                round_feeds: list[tuple[int, Path]] = []
                feed_root_on_disk = root / feed_root
                if feed_root_on_disk.is_dir():
                    for candidate in feed_root_on_disk.glob("R*.md"):
                        match = re.fullmatch(
                            r"R(\d+)\.md",
                            candidate.name,
                            flags=re.IGNORECASE,
                        )
                        if match is not None:
                            round_feeds.append(
                                (
                                    int(match.group(1)),
                                    candidate.relative_to(root),
                                )
                            )
                if round_feeds:
                    latest_feed = max(round_feeds, key=lambda item: item[0])[1]
                    if latest_feed not in evidence_targets:
                        yield Finding(
                            "DOCUMENT_NAVIGATION_FRONTIER_STALE",
                            finding_path,
                            "latest experiment feed is not acknowledged by "
                            f"evidence_refs: {latest_feed.as_posix()}",
                        )

    for artifact_id, artifact in records.items():
        supersedes = artifact.get("supersedes", [])
        if not isinstance(supersedes, list) or not all(
            isinstance(value, str) for value in supersedes
        ):
            yield Finding(
                "DOCUMENT_RECORD_INVALID",
                manifest_path.as_posix(),
                f"{artifact_id}.supersedes must be a list of artifact ids",
            )
            continue
        for old_id in supersedes:
            old = records.get(old_id)
            if old is None:
                yield Finding(
                    "DOCUMENT_SUPERSEDES_UNKNOWN",
                    manifest_path.as_posix(),
                    f"{artifact_id} supersedes unknown artifact {old_id}",
                )
            elif old.get("status") not in {"stale", "superseded"}:
                yield Finding(
                    "DOCUMENT_SUPERSESSION_INCONSISTENT",
                    manifest_path.as_posix(),
                    f"{old_id} must be stale or superseded",
                )

    line_root_on_disk = root / line_root
    if line_root_on_disk.is_dir():
        for candidate in sorted(line_root_on_disk.rglob("*")):
            if not candidate.is_file():
                continue
            line_relative = candidate.relative_to(line_root_on_disk).as_posix()
            if any(
                fnmatch.fnmatch(line_relative, pattern)
                or (
                    pattern.startswith("**/")
                    and fnmatch.fnmatch(line_relative, pattern.removeprefix("**/"))
                )
                for pattern in transient_patterns
            ):
                continue
            relative = candidate.relative_to(root)
            if relative == manifest_path:
                continue
            covered = any(
                relative == registered
                or ((root / registered).is_dir() and registered in relative.parents)
                for registered in registered_paths
            )
            if not covered:
                yield Finding(
                    "DOCUMENT_UNREGISTERED",
                    relative.as_posix(),
                    f"durable manuscript file is not registered ({line_id})",
                )


def _manuscript_line_findings(
    root: Path,
    contract: dict[str, Any],
) -> Iterable[Finding]:
    policy = contract.get("manuscript_lines")
    if policy is None:
        return
    if not isinstance(policy, dict):
        raise ContractError("manuscript_lines must be an object")
    entry_name = policy.get("entry_name", "LINE.md")
    manifest_name = policy.get("manifest_name", "ARTIFACTS.json")
    if not isinstance(entry_name, str) or not entry_name:
        raise ContractError("manuscript_lines.entry_name must be a string")
    if not isinstance(manifest_name, str) or not manifest_name:
        raise ContractError("manuscript_lines.manifest_name must be a string")
    navigation_budgets = policy.get("navigation_budgets", {})
    if not isinstance(navigation_budgets, dict):
        raise ContractError("manuscript_lines.navigation_budgets must be an object")

    def navigation_budget(field: str, default: int) -> int:
        value = navigation_budgets.get(field, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ContractError(
                f"manuscript_lines.navigation_budgets.{field} must be a positive integer"
            )
        return value

    line_max_lines = navigation_budget("line_max_lines", 90)
    line_max_bytes = navigation_budget("line_max_bytes", 8192)
    required_reading_max_bytes = navigation_budget(
        "required_reading_max_bytes",
        24576,
    )
    venue_statuses = set(
        _list_of_strings(
            policy.get(
                "venue_statuses",
                ["unassessed", "shortlisted", "locked", "revalidate"],
            ),
            field="manuscript_lines.venue_statuses",
        )
    )
    venue_kinds = set(
        _list_of_strings(
            policy.get(
                "venue_kinds",
                ["journal", "conference", "other"],
            ),
            field="manuscript_lines.venue_kinds",
        )
    )
    source_statuses = set(
        _list_of_strings(
            policy.get(
                "official_source_statuses",
                ["unverified", "partial", "current"],
            ),
            field="manuscript_lines.official_source_statuses",
        )
    )
    lines = contract.get("delivery_lines", [])
    if not isinstance(lines, list):
        raise ContractError("delivery_lines must be a list")
    priorities: dict[int, str] = {}

    for index, line in enumerate(lines):
        if (
            not isinstance(line, dict)
            or line.get("kind") != "manuscript"
            or line.get("status") != "active"
        ):
            continue
        line_id = line.get("id")
        if not isinstance(line_id, str) or not line_id:
            continue
        line_root = _relative_path(
            line.get("root"),
            field=f"delivery_lines[{index}].root",
        )
        line_path = line_root / entry_name
        if not (root / line_path).is_file():
            yield Finding(
                "MANUSCRIPT_LINE_MISSING",
                line_path.as_posix(),
                f"active manuscript {line_id} requires {entry_name}",
            )
            continue
        try:
            line_bytes = (root / line_path).read_bytes()
            line_count = len(line_bytes.decode("utf-8").splitlines())
        except (OSError, UnicodeError) as exc:
            yield Finding(
                "MANUSCRIPT_LINE_INVALID",
                line_path.as_posix(),
                f"cannot read UTF-8 manuscript navigation: {exc}",
            )
            continue
        if line_count > line_max_lines or len(line_bytes) > line_max_bytes:
            yield Finding(
                "MANUSCRIPT_LINE_BUDGET_EXCEEDED",
                line_path.as_posix(),
                (
                    f"navigation is {line_count} lines/{len(line_bytes)} bytes; "
                    f"limits are {line_max_lines} lines/{line_max_bytes} bytes"
                ),
            )
        try:
            metadata = _frontmatter(root / line_path)
        except ContractError as exc:
            yield Finding("MANUSCRIPT_LINE_INVALID", line_path.as_posix(), str(exc))
            continue
        decision_refs = metadata.get("decision_refs")
        if (
            not isinstance(decision_refs, list)
            or not decision_refs
            or not all(isinstance(value, str) and value.strip() for value in decision_refs)
        ):
            yield Finding(
                "MANUSCRIPT_DECISION_REFS_MISSING",
                line_path.as_posix(),
                "active manuscript must navigate to at least one durable decision",
            )
        if metadata.get("line_id") != line_id:
            yield Finding(
                "MANUSCRIPT_LINE_INVALID",
                line_path.as_posix(),
                "frontmatter line_id must match the delivery line id",
            )
        priority = metadata.get("priority")
        if not isinstance(priority, int) or priority < 1:
            yield Finding(
                "MANUSCRIPT_PRIORITY_INVALID",
                line_path.as_posix(),
                "active manuscript priority must be a positive integer",
            )
        else:
            previous = priorities.get(priority)
            if previous is not None:
                yield Finding(
                    "MANUSCRIPT_PRIORITY_DUPLICATE",
                    line_path.as_posix(),
                    f"priority {priority} is already assigned to {previous}",
                )
            priorities[priority] = line_id

        scope = metadata.get("scope")
        if not isinstance(scope, dict):
            yield Finding(
                "MANUSCRIPT_SCOPE_INVALID",
                line_path.as_posix(),
                "scope must declare write_roots and shared_read_roots",
            )
            scope = {}
        write_values = scope.get("write_roots", [])
        read_values = scope.get("shared_read_roots", [])
        if not isinstance(write_values, list) or not all(
            isinstance(value, str) for value in write_values
        ):
            yield Finding(
                "MANUSCRIPT_SCOPE_INVALID",
                line_path.as_posix(),
                "scope.write_roots must be a list of paths",
            )
            write_values = []
        if not isinstance(read_values, list) or not all(
            isinstance(value, str) for value in read_values
        ):
            yield Finding(
                "MANUSCRIPT_SCOPE_INVALID",
                line_path.as_posix(),
                "scope.shared_read_roots must be a list of paths",
            )
            read_values = []
        write_roots: list[Path] = []
        for value in write_values:
            try:
                write_path = _relative_path(
                    value,
                    field="scope.write_roots",
                )
            except ContractError as exc:
                yield Finding("MANUSCRIPT_SCOPE_INVALID", line_path.as_posix(), str(exc))
                continue
            write_roots.append(write_path)
            if not _is_within(write_path, line_root):
                yield Finding(
                    "MANUSCRIPT_WRITE_SCOPE_ESCAPE",
                    write_path.as_posix(),
                    f"{line_id} write scope must stay inside {line_root.as_posix()}",
                )
        if line_root not in write_roots:
            yield Finding(
                "MANUSCRIPT_WRITE_SCOPE_INCOMPLETE",
                line_path.as_posix(),
                "write_roots must include the manuscript delivery root",
            )
        read_roots: list[Path] = []
        for value in read_values:
            try:
                read_roots.append(_relative_path(value, field="scope.shared_read_roots"))
            except ContractError as exc:
                yield Finding("MANUSCRIPT_SCOPE_INVALID", line_path.as_posix(), str(exc))

        required = metadata.get("required_reading", [])
        if not isinstance(required, list) or not all(isinstance(value, str) for value in required):
            yield Finding(
                "MANUSCRIPT_SCOPE_INVALID",
                line_path.as_posix(),
                "required_reading must be a list of paths",
            )
            required = []
        allowed_roots = tuple(write_roots + read_roots)
        required_paths: list[Path] = []
        for value in required:
            try:
                required_path = _relative_path(value, field="required_reading")
            except ContractError as exc:
                yield Finding("MANUSCRIPT_SCOPE_INVALID", line_path.as_posix(), str(exc))
                continue
            required_paths.append(required_path)
            if not any(_is_within(required_path, base) for base in allowed_roots):
                yield Finding(
                    "MANUSCRIPT_READ_SCOPE_ESCAPE",
                    required_path.as_posix(),
                    f"required reading for {line_id} is outside its declared scope",
                )

        venue = metadata.get("venue")
        if not isinstance(venue, dict):
            yield Finding(
                "VENUE_STATE_INVALID",
                line_path.as_posix(),
                "active manuscript must declare venue state",
            )
        else:
            venue_kind = venue.get("kind", "journal")
            venue_status = venue.get("status")
            source_status = venue.get("official_source_status")
            if (
                venue_kind not in venue_kinds
                or venue_status not in venue_statuses
                or source_status not in source_statuses
            ):
                yield Finding(
                    "VENUE_STATE_INVALID",
                    line_path.as_posix(),
                    "venue kind, status, or official_source_status is invalid",
                )
            if venue_status in {"shortlisted", "locked", "revalidate"}:
                required_fields = ["primary", "decision_record"]
                if venue_kind == "journal":
                    required_fields.append("backup")
                for field in required_fields:
                    if not isinstance(venue.get(field), str) or not venue[field]:
                        yield Finding(
                            "VENUE_STATE_INVALID",
                            line_path.as_posix(),
                            f"venue.{field} is required for {venue_status}",
                        )
                backup = venue.get("backup")
                if backup is not None and (
                    not isinstance(backup, str) or not backup.strip()
                ):
                    yield Finding(
                        "VENUE_STATE_INVALID",
                        line_path.as_posix(),
                        "venue.backup must be a non-empty string",
                    )
                record = venue.get("decision_record")
                if isinstance(record, str) and record:
                    try:
                        record_path = _relative_path(
                            record,
                            field="venue.decision_record",
                        )
                    except ContractError as exc:
                        yield Finding(
                            "VENUE_STATE_INVALID",
                            line_path.as_posix(),
                            str(exc),
                        )
                    else:
                        if not (root / record_path).is_file():
                            yield Finding(
                                "VENUE_DECISION_MISSING",
                                record_path.as_posix(),
                                f"venue decision record is missing for {line_id}",
                            )
            if venue_status == "locked" and source_status != "current":
                yield Finding(
                    "VENUE_LOCK_UNVERIFIED",
                    line_path.as_posix(),
                    "locked venue requires current official-source verification",
                )

        manifest_value = metadata.get("artifact_manifest")
        try:
            manifest_path = _relative_path(
                manifest_value,
                field="artifact_manifest",
            )
        except ContractError as exc:
            yield Finding("MANUSCRIPT_LINE_INVALID", line_path.as_posix(), str(exc))
            manifest_path = line_root / manifest_name
        expected_manifest = line_root / manifest_name
        if manifest_path != expected_manifest:
            yield Finding(
                "DOCUMENT_MANIFEST_NONSTANDARD",
                manifest_path.as_posix(),
                f"active manuscript manifest must be {expected_manifest.as_posix()}",
            )
        context_paths = dict.fromkeys((*required_paths, manifest_path))
        context_bytes = sum(
            (root / context_path).stat().st_size
            for context_path in context_paths
            if (root / context_path).is_file()
        )
        if context_bytes > required_reading_max_bytes:
            yield Finding(
                "MANUSCRIPT_CONTEXT_BUDGET_EXCEEDED",
                line_path.as_posix(),
                (
                    f"cold-start context is {context_bytes} bytes; "
                    f"limit is {required_reading_max_bytes} bytes"
                ),
            )
        yield from _artifact_manifest_findings(
            root,
            line_id=line_id,
            line_root=line_root,
            manifest_path=manifest_path,
            policy=policy,
            line_metadata=metadata,
            required_reading=tuple(required_paths),
        )


def _round_owner(path: Path, owner: str) -> str | None:
    if re.fullmatch(r"R\d+", owner, flags=re.IGNORECASE):
        return owner.upper()
    if owner == "round-from-path":
        match = re.search(r"(?:^|/)R(\d+)(?:/|$)", path.as_posix(), flags=re.IGNORECASE)
        return f"R{match.group(1)}" if match else None
    if owner != "round-from-filename":
        return None
    match = re.search(r"(?:^|[_-])r(\d+)", path.stem, flags=re.IGNORECASE)
    return f"R{match.group(1)}" if match else None


def _round_is_closed(root: Path, round_id: str) -> bool:
    verdict = root / "memory" / "rounds" / round_id / "verdict.md"
    if not verdict.is_file():
        return False
    try:
        content = verdict.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return bool(
        re.search(
            r"\*\*Status\*\*:\s*(?:completed|superseded|aborted)\b",
            content,
            flags=re.IGNORECASE,
        )
    )


def _round_document_findings(
    root: Path,
    contract: dict[str, Any],
) -> Iterable[Finding]:
    policy = contract.get("round_documents")
    if policy is None:
        return
    if not isinstance(policy, dict):
        raise ContractError("round_documents must be an object")
    enforce_from = policy.get("enforce_from")
    if not isinstance(enforce_from, int) or enforce_from < 1:
        raise ContractError("round_documents.enforce_from must be a positive integer")
    allowed = _list_of_strings(
        policy.get("allowed_markdown", []),
        field="round_documents.allowed_markdown",
    )
    allowed_paths = _list_of_strings(
        policy.get("allowed_paths", []),
        field="round_documents.allowed_paths",
    )
    if not allowed:
        raise ContractError("round_documents.allowed_markdown must not be empty")

    rounds_dir = root / "memory" / "rounds"
    if not rounds_dir.is_dir():
        return
    for round_dir in sorted(rounds_dir.iterdir()):
        match = re.fullmatch(r"R(\d+)", round_dir.name)
        if not round_dir.is_dir() or not match:
            continue
        if int(match.group(1)) < enforce_from:
            continue
        for document in sorted(round_dir.rglob("*.md")):
            relative_in_round = document.relative_to(round_dir).as_posix()
            relative_in_rounds = document.relative_to(rounds_dir).as_posix()
            if any(fnmatch.fnmatch(relative_in_round, pattern) for pattern in allowed):
                continue
            if relative_in_rounds in allowed_paths:
                continue
            yield Finding(
                "ROUND_DOCUMENT_UNDECLARED",
                document.relative_to(root).as_posix(),
                "future round prose exceeds the declared document budget",
            )


def _executable_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    policy = contract.get("executables")
    if policy is None:
        return
    if not isinstance(policy, dict):
        raise ContractError("executables must be an object")
    discovery = _list_of_strings(
        policy.get("discover", []),
        field="executables.discover",
    )
    classifiers = policy.get("classifiers", [])
    if not isinstance(classifiers, list):
        raise ContractError("executables.classifiers must be a list")
    valid_roles = {
        "evaluation-adapter",
        "figure-adapter",
        "maintenance",
        "operation",
        "round-probe",
        "round-runner",
        "training-adapter",
    }
    valid_states = {"active", "archived", "exempt", "frozen", "generated"}
    parsed_classifiers: list[dict[str, Any]] = []
    for index, classifier in enumerate(classifiers):
        if not isinstance(classifier, dict):
            raise ContractError(f"executables.classifiers[{index}] must be an object")
        pattern = classifier.get("pattern")
        role = classifier.get("role")
        state = classifier.get("state")
        owner = classifier.get("owner")
        if not isinstance(pattern, str) or not pattern:
            raise ContractError(f"executables.classifiers[{index}].pattern must be a string")
        if role not in valid_roles:
            raise ContractError(
                f"executables.classifiers[{index}].role must be one of {sorted(valid_roles)}"
            )
        if state not in valid_states:
            raise ContractError(
                f"executables.classifiers[{index}].state must be one of {sorted(valid_states)}"
            )
        if not isinstance(owner, str) or not owner:
            raise ContractError(f"executables.classifiers[{index}].owner must be a string")
        evidence_paths = _list_of_strings(
            classifier.get("evidence", []),
            field=f"executables.classifiers[{index}].evidence",
        )
        if role == "figure-adapter" and not evidence_paths:
            raise ContractError(
                f"executables.classifiers[{index}].evidence must not be empty for a figure-adapter"
            )
        parsed_classifiers.append(
            {
                "pattern": pattern,
                "role": role,
                "state": state,
                "owner": owner,
                "evidence": evidence_paths,
            }
        )

    discovered: set[Path] = set()
    for pattern in discovery:
        discovered.update(path for path in root.glob(pattern) if path.is_file())
    for executable in sorted(discovered):
        relative = executable.relative_to(root)
        relative_posix = relative.as_posix()
        classifier = next(
            (
                item
                for item in parsed_classifiers
                if fnmatch.fnmatch(relative_posix, str(item["pattern"]))
            ),
            None,
        )
        if classifier is None:
            yield Finding(
                "EXECUTABLE_UNCLASSIFIED",
                relative_posix,
                "executable has no lifecycle classifier",
            )
            continue
        if classifier["role"] == "figure-adapter":
            try:
                source = executable.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                yield Finding(
                    "EXECUTABLE_UNREADABLE",
                    relative_posix,
                    "executable is not UTF-8 text",
                )
                continue
            for evidence_value in classifier["evidence"]:
                evidence_path = _relative_path(
                    evidence_value,
                    field=f"evidence for {relative_posix}",
                )
                if not (root / evidence_path).exists():
                    yield Finding(
                        "EXECUTABLE_EVIDENCE_MISSING",
                        evidence_path.as_posix(),
                        f"declared evidence for {relative_posix} is missing",
                    )
                elif evidence_path.as_posix() not in source and evidence_path.stem not in source:
                    yield Finding(
                        "EXECUTABLE_EVIDENCE_UNREFERENCED",
                        relative_posix,
                        f"figure adapter does not reference {evidence_path.as_posix()}",
                    )

        round_id = _round_owner(relative, str(classifier["owner"]))
        if (
            classifier["state"] == "active"
            and round_id is not None
            and _round_is_closed(root, round_id)
        ):
            yield Finding(
                "EXECUTABLE_ARCHIVE_CANDIDATE",
                relative_posix,
                f"active executable belongs to closed {round_id}",
                severity="warning",
            )


def _external_adapter_findings(
    root: Path,
    contract: dict[str, Any],
) -> Iterable[Finding]:
    adapters = contract.get("external_adapters", [])
    if not isinstance(adapters, list):
        raise ContractError("external_adapters must be a list")
    seen_ids: set[str] = set()
    for index, adapter in enumerate(adapters):
        if not isinstance(adapter, dict):
            raise ContractError(f"external_adapters[{index}] must be an object")
        adapter_id = adapter.get("id")
        if not isinstance(adapter_id, str) or not adapter_id:
            raise ContractError(f"external_adapters[{index}].id must be a string")
        if adapter_id in seen_ids:
            raise ContractError(f"duplicate external adapter id: {adapter_id}")
        seen_ids.add(adapter_id)
        if adapter.get("authority") != "explicit-adapter":
            raise ContractError(f"external_adapters[{index}].authority must be explicit-adapter")
        lock_path = _relative_path(
            adapter.get("lock"),
            field=f"external_adapters[{index}].lock",
        )
        lock_on_disk = root / lock_path
        if not lock_on_disk.is_file():
            yield Finding(
                "EXTERNAL_LOCK_MISSING",
                lock_path.as_posix(),
                f"external adapter lock is missing ({adapter_id})",
            )
            continue
        try:
            lock = _load_json(lock_on_disk)
        except ContractError as exc:
            yield Finding(
                "EXTERNAL_LOCK_INVALID",
                lock_path.as_posix(),
                str(exc),
            )
            continue
        license_id = lock.get("license")
        sources = lock.get("source_repositories")
        install = lock.get("install")
        authority = lock.get("project_write_authority")
        metadata_valid = (
            isinstance(license_id, str)
            and bool(license_id)
            and isinstance(sources, list)
            and bool(sources)
            and all(
                isinstance(source, dict)
                and isinstance(source.get("url"), str)
                and bool(source["url"])
                and isinstance(source.get("commit"), str)
                and bool(source["commit"])
                for source in sources
            )
            and isinstance(install, dict)
            and install.get("scope") == "global"
            and isinstance(authority, list)
        )
        if not metadata_valid:
            yield Finding(
                "EXTERNAL_LOCK_INVALID",
                lock_path.as_posix(),
                "lock must declare license, pinned sources, global install, and authority",
            )
            continue
        if authority:
            yield Finding(
                "EXTERNAL_AUTHORITY_LEAK",
                lock_path.as_posix(),
                "external adapter must have empty project_write_authority",
            )


def _research_skill_scope_findings(
    root: Path,
    contract: dict[str, Any],
) -> Iterable[Finding]:
    scope_value = contract.get("research_skill_scope")
    if scope_value is None:
        return
    scope_path = _relative_path(scope_value, field="research_skill_scope")
    scope_on_disk = root / scope_path
    if not scope_on_disk.is_file():
        yield Finding(
            "RESEARCH_SKILL_SCOPE_MISSING",
            scope_path.as_posix(),
            "research skill scope manifest is missing",
        )
        return
    try:
        scope = _load_json(scope_on_disk)
    except ContractError as exc:
        yield Finding("RESEARCH_SKILL_SCOPE_INVALID", scope_path.as_posix(), str(exc))
        return
    adapter_value = scope.get("project_adapter")
    try:
        adapter_path = _relative_path(
            adapter_value,
            field="research_skill_scope.project_adapter",
        )
    except ContractError as exc:
        yield Finding("RESEARCH_SKILL_SCOPE_INVALID", scope_path.as_posix(), str(exc))
    else:
        if not (root / adapter_path).is_file():
            yield Finding(
                "RESEARCH_SKILL_ADAPTER_MISSING",
                adapter_path.as_posix(),
                "declared project-local research adapter is missing",
            )
    local_skills = scope.get("project_local_skills", [])
    if not isinstance(local_skills, list):
        yield Finding(
            "RESEARCH_SKILL_SCOPE_INVALID",
            scope_path.as_posix(),
            "project_local_skills must be a list",
        )
    else:
        for index, skill in enumerate(local_skills):
            if not isinstance(skill, dict):
                yield Finding(
                    "RESEARCH_SKILL_SCOPE_INVALID",
                    scope_path.as_posix(),
                    f"project_local_skills[{index}] must be an object",
                )
                continue
            try:
                skill_path = _relative_path(
                    skill.get("path"),
                    field=f"project_local_skills[{index}].path",
                )
            except ContractError as exc:
                yield Finding(
                    "RESEARCH_SKILL_SCOPE_INVALID",
                    scope_path.as_posix(),
                    str(exc),
                )
                continue
            if not (root / skill_path / "SKILL.md").is_file():
                yield Finding(
                    "RESEARCH_SKILL_LOCAL_MISSING",
                    skill_path.as_posix(),
                    "project-local skill entrypoint is missing",
                )

    global_skills = scope.get("global_skills", [])
    if not isinstance(global_skills, list):
        yield Finding(
            "RESEARCH_SKILL_SCOPE_INVALID",
            scope_path.as_posix(),
            "global_skills must be a list",
        )
        return
    seen: set[str] = set()
    for index, skill in enumerate(global_skills):
        if not isinstance(skill, dict):
            yield Finding(
                "RESEARCH_SKILL_SCOPE_INVALID",
                scope_path.as_posix(),
                f"global_skills[{index}] must be an object",
            )
            continue
        name = skill.get("name")
        authority = skill.get("project_write_authority")
        implicit = skill.get("allow_implicit_invocation")
        if not isinstance(name, str) or not name:
            yield Finding(
                "RESEARCH_SKILL_SCOPE_INVALID",
                scope_path.as_posix(),
                f"global_skills[{index}].name must be a string",
            )
            continue
        if name in seen:
            yield Finding(
                "RESEARCH_SKILL_NAME_DUPLICATE",
                scope_path.as_posix(),
                f"global skill appears more than once: {name}",
            )
        seen.add(name)
        if authority != []:
            yield Finding(
                "RESEARCH_SKILL_AUTHORITY_LEAK",
                scope_path.as_posix(),
                f"global skill {name} must not own project writes",
            )
        if not isinstance(implicit, bool):
            yield Finding(
                "RESEARCH_SKILL_SCOPE_INVALID",
                scope_path.as_posix(),
                f"global skill {name} must declare allow_implicit_invocation",
            )


def _opaque_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    values = _list_of_strings(
        contract.get("opaque_subtrees", []),
        field="opaque_subtrees",
    )
    root_policy = contract.get("root", {})
    if not isinstance(root_policy, dict):
        raise ContractError("root must be an object")
    declared_roots = set(_list_of_strings(root_policy.get("allowed", []), field="root.allowed"))
    declared_roots.update(
        _list_of_strings(root_policy.get("tool_state", []), field="root.tool_state")
    )
    for index, value in enumerate(values):
        path = _relative_path(value, field=f"opaque_subtrees[{index}]")
        if path.parts and path.parts[0] not in declared_roots:
            yield Finding(
                "OPAQUE_ROOT_UNDECLARED",
                path.as_posix(),
                "opaque subtree must also be declared at the repository root",
            )
        if not (root / path).exists():
            yield Finding(
                "OPAQUE_SUBTREE_MISSING",
                path.as_posix(),
                "declared opaque subtree is missing",
                severity="warning",
            )


def _load_baseline(
    root: Path,
    contract: dict[str, Any],
) -> tuple[Path, dict[str, dict[str, Any]]]:
    baseline_value = contract.get("baseline")
    baseline_path = (
        _relative_path(baseline_value, field="baseline")
        if baseline_value is not None
        else Path("docs/repo-hygiene/baseline.json")
    )
    baseline_on_disk = root / baseline_path
    if not baseline_on_disk.exists():
        return baseline_path, {}
    payload = _load_json(baseline_on_disk)
    entries = payload.get("findings", [])
    if not isinstance(entries, list):
        raise ContractError("baseline findings must be a list")
    by_fingerprint: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ContractError(f"baseline findings[{index}] must be an object")
        fingerprint = entry.get("fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ContractError(f"baseline findings[{index}].fingerprint must be a string")
        if fingerprint in by_fingerprint:
            raise ContractError(f"duplicate baseline fingerprint: {fingerprint}")
        by_fingerprint[fingerprint] = entry
    return baseline_path, by_fingerprint


def inspect_manuscript_lines(root: Path | None = None) -> tuple[Finding, ...]:
    """Return manuscript-scope and document-lifecycle findings only.

    Cold-start routing uses this narrower interface so it does not scan every
    unrelated repository policy merely to decide whether a paper artifact is
    current. The full repository command remains ``validate_repository``.
    """

    resolved_root = (root or repository_root()).resolve()
    contract = _load_json(resolved_root / CONTRACT_PATH)
    return tuple(_manuscript_line_findings(resolved_root, contract))


def validate_repository(
    root: Path | None = None,
    *,
    use_baseline: bool = True,
) -> ValidationReport:
    """Validate repository structure without mutating it."""

    resolved_root = (root or repository_root()).resolve()
    try:
        contract = _load_json(resolved_root / CONTRACT_PATH)
        if contract.get("version") != 1:
            raise ContractError("contract version must be 1")
        findings = [
            *_root_findings(resolved_root, contract),
            *_artifact_findings(resolved_root, contract),
            *_navigation_findings(resolved_root, contract),
            *_delivery_findings(resolved_root, contract),
            *_manuscript_line_findings(resolved_root, contract),
            *_round_document_findings(resolved_root, contract),
            *_executable_findings(resolved_root, contract),
            *_external_adapter_findings(resolved_root, contract),
            *_research_skill_scope_findings(resolved_root, contract),
            *_opaque_findings(resolved_root, contract),
        ]
        baseline_path, baseline = (
            _load_baseline(resolved_root, contract) if use_baseline else (Path(), {})
        )
    except (ContractError, OSError) as exc:
        return ValidationReport(
            resolved_root,
            (
                Finding(
                    "CONTRACT_INVALID",
                    CONTRACT_PATH.as_posix(),
                    str(exc),
                ),
            ),
        )

    matched: set[str] = set()
    applied: list[Finding] = []
    for finding in findings:
        if finding.fingerprint in baseline:
            applied.append(replace(finding, baselined=True))
            matched.add(finding.fingerprint)
        else:
            applied.append(finding)

    if use_baseline:
        for fingerprint, entry in baseline.items():
            if fingerprint in matched:
                continue
            entry_path = entry.get("path")
            path = entry_path if isinstance(entry_path, str) else baseline_path.as_posix()
            applied.append(
                Finding(
                    "BASELINE_STALE",
                    path,
                    f"baseline entry no longer matches ({fingerprint}); remove it",
                )
            )

    ordered = tuple(
        sorted(
            applied,
            key=lambda item: (item.baselined, item.rule_id, item.path, item.message),
        )
    )
    return ValidationReport(resolved_root, ordered)
