#!/usr/bin/env python3
"""Run deterministic integrity checks on a LaTeX submission package.

Usage:
    python memory/tools/scan_latex_package.py paper/main.tex --bib paper/references.bib
    python memory/tools/scan_latex_package.py paper/main.tex --require-file paper/highlights.docx

This script checks package mechanics. Journal-specific requirements must be
captured from current official author instructions.
It cannot prove scientific validity or venue compliance when the corresponding
rule is not supplied as an explicit required file or deterministic check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\{((?:\{[^{}]*\})+)\}")
GRAPHICSPATH_ITEM_RE = re.compile(r"\{([^{}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|pageref|autoref|cref|Cref)\{([^}]+)\}")
CITE_RE = re.compile(
    r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|parencite|textcite)"
    r"\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}"
)
BIB_RESOURCE_RE = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]+)\}")
BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\{([^}]+)\}")
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.IGNORECASE)
TODO_RE = re.compile(
    r"\b(?:TODO|FIXME|TBD|XXX|PLACEHOLDER|CITATION\s+NEEDED|INSERT\s+FIGURE)\b",
    re.IGNORECASE,
)
LATEX_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
GRAPHIC_SUFFIXES = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg")


@dataclass
class Finding:
    level: str
    code: str
    location: str
    message: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def strip_comments(text: str) -> str:
    return "\n".join(LATEX_COMMENT_RE.sub("", line) for line in text.splitlines())


def resolve_tex(raw: str, parent: Path) -> Path:
    path = (parent / raw).resolve()
    return path if path.suffix else path.with_suffix(".tex")


def collect_tex(main: Path, findings: list[Finding]) -> tuple[list[Path], str]:
    visited: set[Path] = set()
    ordered: list[Path] = []
    chunks: list[str] = []

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in visited:
            return
        visited.add(path)
        if not path.is_file():
            findings.append(Finding("fail", "missing-tex", str(path), "Included TeX file is missing."))
            return
        text = strip_comments(read_text(path))
        ordered.append(path)
        chunks.append(f"\n% SOURCE {path}\n{text}")
        for raw in INPUT_RE.findall(text):
            visit(resolve_tex(raw.strip(), path.parent))

    visit(main)
    return ordered, "\n".join(chunks)


def resolve_graphic(raw: str, parent: Path, search_dirs: list[Path]) -> Path | None:
    candidates = [(parent / raw).resolve()]
    candidates.extend((directory / raw).resolve() for directory in search_dirs)
    for candidate in candidates:
        suffixes = ("",) if candidate.suffix else GRAPHIC_SUFFIXES
        for suffix in suffixes:
            path = candidate if not suffix else candidate.with_suffix(suffix)
            if path.is_file():
                return path
    return None


def parse_bibliography_paths(text: str, main_parent: Path) -> list[Path]:
    paths: list[Path] = []
    for raw in BIB_RESOURCE_RE.findall(text):
        paths.append((main_parent / raw.strip()).resolve())
    for group in BIBLIOGRAPHY_RE.findall(text):
        for raw in group.split(","):
            path = (main_parent / raw.strip()).resolve()
            paths.append(path if path.suffix else path.with_suffix(".bib"))
    return paths


def duplicate_values(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def digest_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: str(item).lower()):
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# LaTeX submission package scan",
        "",
        f"- Decision: **{payload['decision']}**",
        f"- Package SHA-256: `{payload['package_sha256']}`",
        f"- TeX files: {len(payload['tex_files'])}",
        f"- Bibliography files: {len(payload['bib_files'])}",
        f"- Graphics: {len(payload['graphics'])}",
        "",
        "| Level | Code | Location | Message |",
        "|---|---|---|---|",
    ]
    for finding in payload["findings"]:
        values = [
            finding["level"],
            finding["code"],
            finding["location"],
            finding["message"],
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    if not payload["findings"]:
        lines.append("| info | clean-static-scan | - | No static package findings. |")
    lines.extend(
        [
            "",
            "> This result covers package mechanics only. Venue rules, page limits,",
            "> disclosures, visual PDF quality, and scientific validity require separate checks.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("main_tex", type=Path)
    parser.add_argument("--bib", action="append", type=Path, default=[])
    parser.add_argument("--require-file", action="append", type=Path, default=[])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    main = args.main_tex.resolve()
    if not main.is_file():
        print(f"Main TeX file does not exist: {main}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    tex_files, text = collect_tex(main, findings)
    project_root = main.parent

    markers = sorted(set(TODO_RE.findall(text)), key=str.lower)
    for marker in markers:
        findings.append(Finding("fail", "unresolved-marker", str(main), f"Unresolved marker: {marker}"))

    labels = LABEL_RE.findall(text)
    refs = REF_RE.findall(text)
    for label in duplicate_values(labels):
        findings.append(Finding("fail", "duplicate-label", label, "Label is defined more than once."))
    for ref in sorted(set(refs) - set(labels)):
        findings.append(Finding("fail", "missing-label", ref, "Reference target has no matching label."))
    for label in sorted(set(labels) - set(refs)):
        findings.append(Finding("warn", "unreferenced-label", label, "Label is never referenced."))

    graphic_paths: list[Path] = []
    graphic_search_dirs = [
        (project_root / raw).resolve()
        for group in GRAPHICSPATH_RE.findall(text)
        for raw in GRAPHICSPATH_ITEM_RE.findall(group)
    ]
    for tex_path in tex_files:
        source_text = strip_comments(read_text(tex_path))
        for raw in GRAPHICS_RE.findall(source_text):
            resolved = resolve_graphic(raw.strip(), tex_path.parent, graphic_search_dirs)
            if resolved is None:
                findings.append(
                    Finding("fail", "missing-graphic", f"{tex_path}:{raw}", "Graphic file cannot be resolved.")
                )
            else:
                graphic_paths.append(resolved)

    bib_paths = [path.resolve() for path in args.bib]
    if not bib_paths:
        bib_paths = parse_bibliography_paths(text, project_root)
    bib_paths = sorted(set(bib_paths))
    for path in bib_paths:
        if not path.is_file():
            findings.append(Finding("fail", "missing-bibliography", str(path), "Bibliography file is missing."))

    cited_keys = {
        key.strip()
        for group in CITE_RE.findall(text)
        for key in group.split(",")
        if key.strip()
    }
    bib_keys: list[str] = []
    for path in bib_paths:
        if path.is_file():
            bib_keys.extend(BIB_KEY_RE.findall(read_text(path)))
    for key in duplicate_values(bib_keys):
        findings.append(Finding("fail", "duplicate-bib-key", key, "BibTeX key is defined more than once."))
    for key in sorted(cited_keys - set(bib_keys)):
        findings.append(Finding("fail", "missing-bib-key", key, "Cited key is absent from the bibliography."))
    for key in sorted(set(bib_keys) - cited_keys):
        findings.append(Finding("warn", "unused-bib-key", key, "Bibliography entry is not cited."))

    required_paths: list[Path] = []
    for raw in args.require_file:
        path = raw.resolve()
        required_paths.append(path)
        if not path.is_file():
            findings.append(Finding("fail", "missing-required-file", str(path), "Required artifact is missing."))

    if not re.search(r"\\begin\{abstract\}", text, re.IGNORECASE):
        findings.append(Finding("warn", "abstract-not-detected", str(main), "No abstract environment was detected."))
    if not re.search(r"\\(?:keywords|begin\{IEEEkeywords\})", text, re.IGNORECASE):
        findings.append(Finding("warn", "keywords-not-detected", str(main), "No keyword command or environment was detected."))

    existing_files = [
        path
        for path in tex_files + bib_paths + graphic_paths + required_paths
        if path.is_file()
    ]
    package_hash = digest_files(existing_files)
    fail_count = sum(finding.level == "fail" for finding in findings)
    decision = "FAIL" if fail_count else ("WARN" if findings else "PASS")
    payload = {
        "schema_version": "latex-submission-scan-v1",
        "decision": decision,
        "main_tex": str(main),
        "package_sha256": package_hash,
        "tex_files": [str(path) for path in tex_files],
        "bib_files": [str(path) for path in bib_paths],
        "graphics": [str(path) for path in graphic_paths],
        "required_files": [str(path) for path in required_paths],
        "findings": [asdict(finding) for finding in findings],
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
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
