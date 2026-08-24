#!/usr/bin/env python3
"""Inventory evidence-sensitive manuscript lines without judging support.

Usage:
    python memory/tools/inventory_manuscript.py paper/main.tex --project-root . --format markdown
    python memory/tools/inventory_manuscript.py draft/ --format json --output inventory.json

The script uses only the Python standard library. It scans Markdown and LaTeX
files, reports numeric tokens and high-risk claim language, and resolves CLM and
round references for projects that expose memory/claims and memory/rounds.
It reports candidates, not semantic support; missing or unconventional syntax
may be omitted and every emitted finding still requires audit review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_SUFFIXES = {".md", ".tex"}
CLAIM_RE = re.compile(r"\bCLM-\d{4}\b", re.IGNORECASE)
ROUND_RE = re.compile(r"\bR\d{2,4}\b", re.IGNORECASE)
NUMBER_RE = re.compile(
    r"(?<![A-Za-z_\\])"
    r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+|\.\d+)"
    r"(?:\.\d+)?(?:[eE][+-]?\d+)?"
    r"(?:\s*(?:%|Hz|s|ms|p\.u\.|pu|MW|MVA|Mvar|rad/s))?"
    r"(?![A-Za-z_])",
    re.IGNORECASE,
)
LATEX_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
FENCE_RE = re.compile(r"^\s*```")
MARKDOWN_CITATION_RE = re.compile(r"(?<!\\)\[(?:\d+(?:\s*[-,]\s*\d+)*)\]")
LATEX_CITATION_RE = re.compile(
    r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear)"
    r"\*?(?:\[[^\]]*\]){0,2}\{[^}]*\}",
    re.IGNORECASE,
)
QUESTION_RE = re.compile(r"\bQ-\d{4}\b", re.IGNORECASE)
HEX_TOKEN_RE = re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{8,}\b", re.IGNORECASE)

RISK_PATTERNS = {
    "comparative": re.compile(
        r"\b(?:outperform\w*|superior|improv\w*|reduc\w*|increase\w*|decrease\w*|gain|benefit)\b",
        re.IGNORECASE,
    ),
    "causal": re.compile(
        r"\b(?:cause\w*|lead(?:s|ing)?\s+to|result(?:s|ing)?\s+in|because|therefore)\b",
        re.IGNORECASE,
    ),
    "mechanism": re.compile(
        r"\b(?:mechanis\w*|explain\w*|attribut\w*|mediat\w*|driv(?:e|es|en|ing))\b",
        re.IGNORECASE,
    ),
    "generalization": re.compile(
        r"\b(?:generali[sz]\w*|unseen|held[- ]out|topolog\w*|transfer\w*|cross[- ]simulator)\b",
        re.IGNORECASE,
    ),
    "robustness-safety": re.compile(
        r"\b(?:robust\w*|safe\w*|stabl\w*|guarantee\w*|certif\w*|constraint\w*|violation\w*)\b",
        re.IGNORECASE,
    ),
    "statistical": re.compile(
        r"\b(?:significant\w*|confidence interval|bootstrap|p[- ]?value|median|mean|tail risk|CVaR)\b",
        re.IGNORECASE,
    ),
    "scope": re.compile(
        r"\b(?:always|all systems|universal\w*|deployment|real[- ]world|arbitrary|across systems)\b",
        re.IGNORECASE,
    ),
}


@dataclass
class Record:
    file: str
    line: int
    claim_ids: list[str]
    round_ids: list[str]
    numbers: list[str]
    risk_classes: list[str]
    flags: list[str]
    excerpt: str


def discover_inputs(raw_paths: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for raw in raw_paths:
        path = Path(raw).resolve()
        if path.is_file():
            if path.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(path)
            else:
                raise ValueError(f"Unsupported manuscript suffix: {path}")
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
            )
        else:
            raise ValueError(f"Input does not exist: {path}")
    return sorted(set(files))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter_scalar(text: str, key: str) -> str | None:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", parts[1])
    return match.group(1).strip() if match else None


def claim_metadata(root: Path, claim_id: str) -> dict[str, object]:
    normalized = claim_id.upper()
    path = root / "memory" / "claims" / f"{normalized}.md"
    if not path.is_file():
        return {"id": normalized, "exists": False}
    text = read_text(path)
    return {
        "id": normalized,
        "exists": True,
        "path": str(path.relative_to(root)),
        "trust": parse_frontmatter_scalar(text, "trust"),
        "status": parse_frontmatter_scalar(text, "status"),
        "round": parse_frontmatter_scalar(text, "round"),
    }


def round_metadata(root: Path, round_id: str) -> dict[str, object]:
    normalized = round_id.upper()
    path = root / "memory" / "rounds" / normalized / "verdict.md"
    if not path.is_file():
        return {"id": normalized, "exists": False}
    text = read_text(path)
    match = re.search(r"(?mi)^\*\*Status\*\*:\s*(.*?)\s*$", text)
    status = match.group(1).strip() if match else None
    return {
        "id": normalized,
        "exists": True,
        "path": str(path.relative_to(root)),
        "status": status,
        "invalid": bool(status and re.search(r"\bINVALID\b", status, re.IGNORECASE)),
    }


def scan_file(path: Path, display_root: Path) -> list[Record]:
    records: list[Record] = []
    in_fence = False
    for line_number, raw_line in enumerate(read_text(path).splitlines(), start=1):
        if FENCE_RE.match(raw_line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = LATEX_COMMENT_RE.sub("", raw_line) if path.suffix.lower() == ".tex" else raw_line
        claim_ids = sorted({item.upper() for item in CLAIM_RE.findall(line)})
        round_ids = sorted({item.upper() for item in ROUND_RE.findall(line)})
        number_line = CLAIM_RE.sub(" ", line)
        number_line = ROUND_RE.sub(" ", number_line)
        number_line = QUESTION_RE.sub(" ", number_line)
        number_line = LATEX_CITATION_RE.sub(" ", number_line)
        number_line = MARKDOWN_CITATION_RE.sub(" ", number_line)
        number_line = HEX_TOKEN_RE.sub(" ", number_line)
        numbers = NUMBER_RE.findall(number_line)
        risk_classes = sorted(name for name, pattern in RISK_PATTERNS.items() if pattern.search(line))
        if not claim_ids and not round_ids and not numbers and not risk_classes:
            continue
        flags: list[str] = []
        excerpt = " ".join(line.strip().split())
        try:
            display_path = str(path.relative_to(display_root))
        except ValueError:
            display_path = str(path)
        records.append(
            Record(
                file=display_path,
                line=line_number,
                claim_ids=claim_ids,
                round_ids=round_ids,
                numbers=numbers,
                risk_classes=risk_classes,
                flags=flags,
                excerpt=excerpt[:240],
            )
        )
    return records


def escape_table(value: object) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "# Manuscript evidence inventory",
        "",
        f"- Files scanned: {summary['files_scanned']}",
        f"- Evidence-sensitive lines: {summary['records']}",
        f"- Unique CLM references: {summary['claim_ids']}",
        f"- Unique round references: {summary['round_ids']}",
        "",
        "| File | Line | CLM | Rounds | Numbers | Risk classes | Flags | Excerpt |",
        "|---|---:|---|---|---|---|---|---|",
    ]
    for record in payload["records"]:
        lines.append(
            "| "
            + " | ".join(
                escape_table(record[key])
                for key in (
                    "file",
                    "line",
                    "claim_ids",
                    "round_ids",
                    "numbers",
                    "risk_classes",
                    "flags",
                    "excerpt",
                )
            )
            + " |"
        )
    lines.extend(["", "## Ledger resolution", ""])
    lines.append("### Claims")
    lines.append("")
    lines.append("| ID | Exists | Trust | Status | Round | Path |")
    lines.append("|---|---|---|---|---|---|")
    for item in payload["claims"]:
        lines.append(
            "| "
            + " | ".join(
                escape_table(item.get(key, ""))
                for key in ("id", "exists", "trust", "status", "round", "path")
            )
            + " |"
        )
    lines.extend(["", "### Rounds", ""])
    lines.append("| ID | Exists | Status | Invalid | Path |")
    lines.append("|---|---|---|---|---|")
    for item in payload["rounds"]:
        lines.append(
            "| "
            + " | ".join(
                escape_table(item.get(key, ""))
                for key in ("id", "exists", "status", "invalid", "path")
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Authority differential",
            "",
            f"- Claims only in authority files: {escape_table(payload['authority']['claims_only_in_authority'])}",
            f"- Claims only in manuscript: {escape_table(payload['authority']['claims_only_in_manuscript'])}",
            "",
            "",
            "> Inventory only: a matching ID or number is not proof. Bind each material",
            "> claim to a canonical locator and verify its conditions and validity.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manuscript", nargs="+", help="Markdown/LaTeX files or directories")
    parser.add_argument("--project-root", type=Path, help="Root containing memory/claims and memory/rounds")
    parser.add_argument(
        "--authority-file",
        action="append",
        type=Path,
        default=[],
        help="Active line, evidence map, or other authority file used for CLM coverage comparison",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path, help="Write output instead of stdout")
    args = parser.parse_args()

    try:
        files = discover_inputs(args.manuscript)
        if not files:
            raise ValueError("No Markdown or LaTeX files found")
        project_root = args.project_root.resolve() if args.project_root else Path.cwd().resolve()
        authority_files = [path.resolve() for path in args.authority_file]
        missing_authority = [path for path in authority_files if not path.is_file()]
        if missing_authority:
            raise ValueError(
                "Authority file does not exist: " + ", ".join(str(path) for path in missing_authority)
            )
        records = [record for path in files for record in scan_file(path, project_root)]
    except (OSError, ValueError) as exc:
        print(f"Inventory failed: {exc}", file=sys.stderr)
        return 2

    claim_ids = sorted({item for record in records for item in record.claim_ids})
    round_ids = sorted({item for record in records for item in record.round_ids})
    authority_claim_ids = sorted(
        {
            item.upper()
            for path in authority_files
            for item in CLAIM_RE.findall(read_text(path))
        }
    )
    claims = [claim_metadata(project_root, item) for item in claim_ids]
    rounds = [round_metadata(project_root, item) for item in round_ids]
    missing_claims = {item["id"] for item in claims if not item["exists"]}
    missing_rounds = {item["id"] for item in rounds if not item["exists"]}
    invalid_rounds = {item["id"] for item in rounds if item.get("invalid")}

    for record in records:
        if missing_claims.intersection(record.claim_ids):
            record.flags.append("missing-claim-record")
        if missing_rounds.intersection(record.round_ids):
            record.flags.append("missing-round-verdict")
        if invalid_rounds.intersection(record.round_ids):
            record.flags.append("invalid-round-reference")
        if authority_claim_ids and set(record.claim_ids) - set(authority_claim_ids):
            record.flags.append("claim-not-in-authority")

    payload = {
        "schema_version": "manuscript-evidence-inventory-v1",
        "summary": {
            "files_scanned": len(files),
            "records": len(records),
            "claim_ids": len(claim_ids),
            "round_ids": len(round_ids),
        },
        "files": [str(path) for path in files],
        "authority": {
            "files": [str(path) for path in authority_files],
            "claim_ids": authority_claim_ids,
            "claims_only_in_authority": sorted(set(authority_claim_ids) - set(claim_ids)),
            "claims_only_in_manuscript": sorted(set(claim_ids) - set(authority_claim_ids)),
        },
        "records": [asdict(record) for record in records],
        "claims": claims,
        "rounds": rounds,
    }
    rendered = (
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
        if args.format == "json"
        else render_markdown(payload)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
