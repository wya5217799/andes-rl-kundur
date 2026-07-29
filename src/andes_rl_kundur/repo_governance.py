"""Repository-wide governance behind one validation interface.

The research ledger has its own validator. This module deliberately owns only
repository structure: root entries, canonical/derived artifacts, navigation
pointers, opaque subtrees, and the debt baseline. Callers should use
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
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path("docs/repo-hygiene/contract.json")


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
    allowed.update(
        _list_of_strings(root_policy.get("tool_state", []), field="root.tool_state")
    )
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
            raise ContractError(
                f"artifacts[{index}].relation must be declared or byte-identical"
            )

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
                f"delivery_lines[{index}].roles has unknown keys: "
                f"{sorted(unknown_roles)}"
            )
        canonical = roles.get("canonical", [])
        if not canonical:
            raise ContractError(
                f"delivery_lines[{index}].roles.canonical must not be empty"
            )

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
                    or (
                        (root / declared).is_dir()
                        and declared in relative.parents
                    )
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
            raise ContractError(
                f"executables.classifiers[{index}].pattern must be a string"
            )
        if role not in valid_roles:
            raise ContractError(
                f"executables.classifiers[{index}].role must be one of "
                f"{sorted(valid_roles)}"
            )
        if state not in valid_states:
            raise ContractError(
                f"executables.classifiers[{index}].state must be one of "
                f"{sorted(valid_states)}"
            )
        if not isinstance(owner, str) or not owner:
            raise ContractError(
                f"executables.classifiers[{index}].owner must be a string"
            )
        evidence_paths = _list_of_strings(
            classifier.get("evidence", []),
            field=f"executables.classifiers[{index}].evidence",
        )
        if role == "figure-adapter" and not evidence_paths:
            raise ContractError(
                f"executables.classifiers[{index}].evidence must not be empty "
                "for a figure-adapter"
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
                elif (
                    evidence_path.as_posix() not in source
                    and evidence_path.stem not in source
                ):
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
            raise ContractError(
                f"external_adapters[{index}].authority must be explicit-adapter"
            )
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


def _opaque_findings(root: Path, contract: dict[str, Any]) -> Iterable[Finding]:
    values = _list_of_strings(
        contract.get("opaque_subtrees", []),
        field="opaque_subtrees",
    )
    root_policy = contract.get("root", {})
    if not isinstance(root_policy, dict):
        raise ContractError("root must be an object")
    declared_roots = set(
        _list_of_strings(root_policy.get("allowed", []), field="root.allowed")
    )
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
            raise ContractError(
                f"baseline findings[{index}].fingerprint must be a string"
            )
        if fingerprint in by_fingerprint:
            raise ContractError(f"duplicate baseline fingerprint: {fingerprint}")
        by_fingerprint[fingerprint] = entry
    return baseline_path, by_fingerprint


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
            *_executable_findings(resolved_root, contract),
            *_external_adapter_findings(resolved_root, contract),
            *_opaque_findings(resolved_root, contract),
        ]
        baseline_path, baseline = (
            _load_baseline(resolved_root, contract)
            if use_baseline
            else (Path(), {})
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
