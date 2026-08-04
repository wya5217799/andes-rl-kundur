"""Validate an experiment feed and its pre-draft publication gate.

Motivation
----------
The feed is the single paper-facing fact layer.  A deterministic structure
check prevents agents from deferring evidence, domain, or literature-boundary
review until after LaTeX prose and figures have already accumulated.

Usage
-----
    python memory/tools/feed_check.py paper/<line>/reports/RNN.md
    python memory/tools/feed_check.py old-feed.md --legacy
    python memory/tools/feed_check.py feed.md --format json

Failure modes
-------------
Exit 1 means a required section or gate field is missing, a hard review gate
failed, or external context still requires deep research.  ``--legacy`` checks
the original feed structure without claiming publication readiness.  The tool
is read-only.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
from pathlib import Path

BASE_SECTIONS = (
    "identity",
    "frozen setup",
    "observations",
    "conclusions",
    "limits",
    "manuscript mapping",
)
PUBLICATION_FIELDS = (
    "evidence audit",
    "domain audit",
    "external context",
    "claim disposition",
    "allowed claim",
    "stay-out",
)
_HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
_FIELD_RE = re.compile(
    r"(?m)^-\s+\*{0,2}([^*:]+?)\*{0,2}\s*:\s*(.+?)\s*$"
)
_CLAIM_RE = re.compile(r"\bCLM-\d+\b", re.IGNORECASE)
_ROUND_RE = re.compile(r"\bR\d+\b", re.IGNORECASE)
_OBSERVATION_RE = re.compile(
    r"(?ms)^-\s+(O\d+)\b(.*?)(?=^-\s+O\d+\b|\Z)",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?%?")
_BACKTICK_RE = re.compile(r"`([^`\r\n]+)`")
_PLACEHOLDER_RE = re.compile(
    r"(?i)^(?:TODO|TBD|TBC|FIXME|N/?A|NONE|reason|pointer|\?+)$|^<[^>]+>$"
)
_SIDECAR_CONTRACT_ROUND = 286
_RESULT_MANIFEST_CONTRACT_ROUND = 291


@dataclasses.dataclass(frozen=True)
class FeedFinding:
    code: str
    message: str


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _section_map(text: str) -> dict[str, str]:
    matches = list(_HEADING_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        key = _normalise(match.group(1))
        sections[key] = text[start:end].strip()
    return sections


def _find_section(sections: dict[str, str], prefix: str) -> str | None:
    for heading, body in sections.items():
        if heading == prefix or heading.startswith(f"{prefix} "):
            return body
    return None


def _repo_root(path: Path) -> Path:
    """Find the checkout root without assuming the caller's working directory."""

    start = path.resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "docs" / "repo-hygiene" / "contract.json").is_file():
            return candidate
    return start


def _meaningful_gate_value(value: str) -> bool:
    value = value.strip()
    if not value or _PLACEHOLDER_RE.fullmatch(value):
        return False
    status_and_detail = re.split(r"\s+[\u2013\u2014-]\s+|\s+", value, maxsplit=1)
    if len(status_and_detail) == 1:
        return False
    if _PLACEHOLDER_RE.fullmatch(status_and_detail[0].strip()):
        return False
    return not bool(_PLACEHOLDER_RE.fullmatch(status_and_detail[1].strip()))


def _identity_findings(
    identity: str,
    repo_root: Path,
    *,
    primary_round: int | None,
) -> list[FeedFinding]:
    findings: list[FeedFinding] = []
    claims = {value.upper() for value in _CLAIM_RE.findall(identity)}
    if not claims:
        findings.append(
            FeedFinding(
                "IDENTITY_CLAIM_MISSING",
                "identity must bind the feed to at least one CLM record",
            )
        )
    rounds = {value.upper() for value in _ROUND_RE.findall(identity)}
    if not rounds:
        findings.append(
            FeedFinding(
                "IDENTITY_ROUND_MISSING",
                "identity must bind the feed to an experiment round",
            )
        )
    for round_id in sorted(rounds):
        if not (repo_root / "memory" / "rounds" / round_id).is_dir():
            findings.append(
                FeedFinding(
                    "ROUND_MISSING",
                    f"identity references missing round: {round_id}",
                )
            )

    pointers = []
    for value in _BACKTICK_RE.findall(identity):
        pointer = value.split("#", 1)[0].split(":", 1)[0].strip()
        if (
            "/" not in pointer
            or pointer.startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:", pointer)
            or any(char in pointer for char in "*?<>|")
        ):
            continue
        pointers.append(pointer)
        target = repo_root / Path(pointer)
        if not target.exists():
            findings.append(
                FeedFinding(
                    "POINTER_MISSING",
                    f"identity evidence pointer does not exist: {pointer}",
                )
            )
            continue
        if (
            primary_round is not None
            and primary_round >= _SIDECAR_CONTRACT_ROUND
            and pointer.endswith(".json")
            and (
                pointer.startswith(f"results/r{primary_round}_")
                or pointer.startswith(f"memory/rounds/R{primary_round}/")
            )
        ):
            sidecar = Path(f"{target}.sha256")
            if not sidecar.is_file():
                findings.append(
                    FeedFinding(
                        "SIDECAR_MISSING",
                        f"feed-era evidence lacks SHA-256 sidecar: {pointer}",
                    )
                )
                continue
            try:
                tokens = sidecar.read_text(encoding="ascii").strip().split()
                expected = tokens[0].lower()
            except (OSError, UnicodeDecodeError, IndexError):
                findings.append(
                    FeedFinding(
                        "SIDECAR_INVALID",
                        f"SHA-256 sidecar is empty or unreadable: {pointer}",
                    )
                )
                continue
            if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
                findings.append(
                    FeedFinding(
                        "SIDECAR_INVALID",
                        f"SHA-256 sidecar has no valid lowercase digest: {pointer}",
                    )
                )
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if expected != actual:
                findings.append(
                    FeedFinding(
                        "SIDECAR_MISMATCH",
                        f"SHA-256 sidecar mismatch: {pointer}",
                    )
                )
    if (
        primary_round is not None
        and primary_round >= _RESULT_MANIFEST_CONTRACT_ROUND
        and any(
            pointer.startswith(f"results/r{primary_round}_")
            for pointer in pointers
        )
    ):
        manifest_path = repo_root / "results" / "MANIFEST.md"
        try:
            manifest = manifest_path.read_text(encoding="utf-8")
        except OSError:
            manifest = ""
        if re.search(
            rf"(?m)^\|\s*R{primary_round}\s*\|",
            manifest,
        ) is None:
            findings.append(
                FeedFinding(
                    "RESULT_MANIFEST_MISSING",
                    f"results/MANIFEST.md must register R{primary_round} "
                    "before the round can close",
                )
            )
    if not pointers:
        findings.append(
            FeedFinding(
                "IDENTITY_POINTER_MISSING",
                "identity must include at least one backticked repository-relative evidence pointer",
            )
        )
    return findings


def _observation_findings(
    observations: str,
    mapping: str,
) -> list[FeedFinding]:
    findings: list[FeedFinding] = []
    observation_ids: list[str] = []
    for match in _OBSERVATION_RE.finditer(observations):
        observation_id = match.group(1).upper()
        body = match.group(2)
        observation_ids.append(observation_id)
        scrubbed = _CLAIM_RE.sub("", body)
        scrubbed = _BACKTICK_RE.sub("", scrubbed)
        if _NUMBER_RE.search(scrubbed) and not _CLAIM_RE.search(body):
            findings.append(
                FeedFinding(
                    "OBSERVATION_CLAIM_MISSING",
                    f"{observation_id} contains a numeric fact without a CLM binding",
                )
            )
    for observation_id in observation_ids:
        if not re.search(rf"\b{re.escape(observation_id)}\b", mapping, re.IGNORECASE):
            findings.append(
                FeedFinding(
                    "OBSERVATION_UNMAPPED",
                    f"{observation_id} must map to the manuscript or an explicit stay-out",
                )
            )
    return findings


def check_feed(
    path: Path,
    *,
    legacy: bool = False,
    repo_root: Path | None = None,
) -> tuple[FeedFinding, ...]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (FeedFinding("FEED_MISSING", f"feed does not exist: {path}"),)
    except OSError as exc:
        return (FeedFinding("FEED_UNREADABLE", f"cannot read {path}: {exc}"),)

    findings: list[FeedFinding] = []
    sections = _section_map(text)
    for required in BASE_SECTIONS:
        body = _find_section(sections, required)
        if body is None:
            findings.append(
                FeedFinding(
                    "SECTION_MISSING",
                    f"required section is missing: {required}",
                )
            )
        elif not body:
            findings.append(
                FeedFinding(
                    "SECTION_EMPTY",
                    f"required section is empty: {required}",
                )
            )

    if legacy:
        return tuple(findings)

    resolved_root = (repo_root or _repo_root(path)).resolve()
    primary_match = re.search(r"\bR(\d+)\b", text, re.IGNORECASE)
    primary_round = int(primary_match.group(1)) if primary_match else None
    identity = _find_section(sections, "identity")
    mapping = _find_section(sections, "manuscript mapping")
    observations = _find_section(sections, "observations")
    if identity:
        findings.extend(
            _identity_findings(
                identity,
                resolved_root,
                primary_round=primary_round,
            )
        )
    if observations and mapping:
        findings.extend(_observation_findings(observations, mapping))
    claim_text = "\n".join(value for value in (identity, observations) if value)
    for claim_id in sorted(
        {value.upper() for value in _CLAIM_RE.findall(claim_text)}
    ):
        claim_path = resolved_root / "memory" / "claims" / f"{claim_id}.md"
        if not claim_path.is_file():
            findings.append(
                FeedFinding(
                    "CLAIM_MISSING",
                    f"feed references missing claim record: {claim_id}",
                )
            )
            continue
        claim_body = claim_path.read_text(encoding="utf-8")
        claim_round_match = re.search(
            r"(?m)^round:\s*R(\d+)\s*$",
            claim_body,
            re.IGNORECASE,
        )
        if (
            primary_round is not None
            and claim_round_match is not None
            and int(claim_round_match.group(1)) != primary_round
        ):
            # Parent claims may be cited as inputs; only the claim emitted by
            # this round must bind back to this feed.
            continue
        feed_relative = str(path)
        try:
            feed_relative = path.resolve().relative_to(resolved_root).as_posix()
            bound = feed_relative in claim_body
        except (OSError, ValueError):
            bound = False
        if not bound:
            findings.append(
                FeedFinding(
                    "CLAIM_FEED_UNBOUND",
                    f"{claim_id} does not point back to feed: {feed_relative}",
                )
            )

    publication = _find_section(sections, "publication gate")
    if publication is None:
        findings.append(
            FeedFinding(
                "PUBLICATION_GATE_MISSING",
                "required section is missing: publication gate",
            )
        )
        return tuple(findings)

    fields = {
        _normalise(match.group(1)): match.group(2).strip()
        for match in _FIELD_RE.finditer(publication)
    }
    for required in PUBLICATION_FIELDS:
        if required not in fields or not fields[required]:
            findings.append(
                FeedFinding(
                    "PUBLICATION_FIELD_MISSING",
                    f"publication gate field is missing: {required}",
                )
            )
        elif not _meaningful_gate_value(fields[required]):
            findings.append(
                FeedFinding(
                    "PUBLICATION_FIELD_PLACEHOLDER",
                    f"publication gate field needs a status plus evidence or rationale: {required}",
                )
            )

    def status(field: str) -> str:
        value = fields.get(field, "")
        return re.split(r"\s+[\u2014-]\s+|\s+", value, maxsplit=1)[0].upper()

    evidence = status("evidence audit")
    domain = status("domain audit")
    external = status("external context")
    disposition = status("claim disposition")

    if evidence and evidence not in {"PASS", "QUALIFIED", "FAIL"}:
        findings.append(
            FeedFinding("EVIDENCE_STATUS_INVALID", f"invalid evidence audit: {evidence}")
        )
    if domain and domain not in {"PASS", "QUALIFIED", "FAIL"}:
        findings.append(
            FeedFinding("DOMAIN_STATUS_INVALID", f"invalid domain audit: {domain}")
        )
    if external and external not in {
        "CURRENT",
        "DEEP-RESEARCH-REQUIRED",
        "NOT-APPLICABLE",
    }:
        findings.append(
            FeedFinding(
                "EXTERNAL_STATUS_INVALID",
                f"invalid external context status: {external}",
            )
        )
    if disposition and disposition not in {"ENTER", "QUALIFY", "STAY-OUT"}:
        findings.append(
            FeedFinding(
                "DISPOSITION_INVALID",
                f"invalid claim disposition: {disposition}",
            )
        )

    if evidence == "FAIL":
        findings.append(FeedFinding("EVIDENCE_GATE_FAILED", "evidence audit failed"))
    if domain == "FAIL":
        findings.append(FeedFinding("DOMAIN_GATE_FAILED", "domain audit failed"))
    if external == "DEEP-RESEARCH-REQUIRED":
        findings.append(
            FeedFinding(
                "EXTERNAL_RESEARCH_OPEN",
                "bounded deep research must close before publication readiness",
            )
        )
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feed", type=Path)
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="check the pre-publication-gate feed structure only",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    findings = check_feed(args.feed, legacy=args.legacy)
    if args.format == "json":
        print(
            json.dumps(
                [dataclasses.asdict(finding) for finding in findings],
                indent=2,
                ensure_ascii=False,
            )
        )
    elif findings:
        for finding in findings:
            print(f"ERROR {finding.code}: {finding.message}")
    else:
        mode = "legacy structure" if args.legacy else "publication gate"
        print(f"OK: {args.feed} ({mode})")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
