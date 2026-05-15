# andes-rl-kundur Migration + Claim Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a new private GitHub repo `andes-rl-kundur` that migrates all ANDES assets from `Multi-Agent  VSGs` + `毕业论文`, equipped from day 1 with a Claim Ledger memory subsystem (claims + rounds + auto-rendered STATE.md) that solves number-drift and onboarding-cost pain.

**Architecture:** Three-layer memory: Layer 1 `memory/claims/CLM-NNNN.md` (atomic, append-only, YAML frontmatter, 5 required fields), Layer 2 `memory/rounds/RNN/{plan,verdict}.md` (free-form, append-only), Layer 3 `memory/STATE.md` (auto-rendered, ~50 lines, single AI onboarding entry). Two Python tools (`validate.py` ~80 LOC + `render.py` ~150 LOC). Markdown-first; no DB, no web UI.

**Tech Stack:** Python 3.11+, `pyyaml`, `pytest` (for tool tests), `gh` CLI (GitHub repo creation), standard `git`, plain markdown.

**Spec:** `docs/superpowers/specs/2026-05-15-andes-research-workbench-design.md`

**Source repos:**
- Primary: `C:\Users\27443\Desktop\Multi-Agent  VSGs\` (ANDES code + research records + paper)
- Secondary: `C:\Users\27443\Desktop\毕业论文\` (dissertation + writing standard)

**Destination:** `C:\Users\27443\Desktop\andes-rl-kundur\` (new repo, sibling of sources)

---

## Pre-flight

### Task 0: Verify environment

**Files:** none

- [ ] **Step 1: Verify Python and pyyaml available**

Run:
```powershell
python --version
python -c "import yaml; print(yaml.__version__)"
```
Expected: Python 3.11+ and pyyaml 6.0+. If pyyaml missing, install:
```powershell
python -m pip install --user pyyaml pytest
```

- [ ] **Step 2: Verify `gh` CLI authenticated**

Run:
```powershell
gh auth status
```
Expected: `Logged in to github.com as <username>`. If not, run `gh auth login`.

- [ ] **Step 3: Verify destination directory does not exist**

Run:
```powershell
Test-Path "C:\Users\27443\Desktop\andes-rl-kundur"
```
Expected: `False`. If `True`, ask user before proceeding (could overwrite work).

---

## Phase A — Scaffold New Repo Skeleton

### Task 1: Create top-level directory structure

**Files:**
- Create: `C:\Users\27443\Desktop\andes-rl-kundur\` (root)
- Create: subdirectories listed below

- [ ] **Step 1: Create root and all top-level dirs**

Run:
```powershell
$ROOT = "C:\Users\27443\Desktop\andes-rl-kundur"
New-Item -ItemType Directory -Path $ROOT
New-Item -ItemType Directory -Path "$ROOT\memory\claims"
New-Item -ItemType Directory -Path "$ROOT\memory\rounds"
New-Item -ItemType Directory -Path "$ROOT\memory\handoffs"
New-Item -ItemType Directory -Path "$ROOT\memory\tools"
New-Item -ItemType Directory -Path "$ROOT\memory\tools\tests"
New-Item -ItemType Directory -Path "$ROOT\memory\tools\tests\fixtures"
New-Item -ItemType Directory -Path "$ROOT\env\andes"
New-Item -ItemType Directory -Path "$ROOT\scenarios\kundur"
New-Item -ItemType Directory -Path "$ROOT\scenarios\new_england"
New-Item -ItemType Directory -Path "$ROOT\probes\andes_common"
New-Item -ItemType Directory -Path "$ROOT\scripts\research_loop\_archive"
New-Item -ItemType Directory -Path "$ROOT\evaluation"
New-Item -ItemType Directory -Path "$ROOT\agents"
New-Item -ItemType Directory -Path "$ROOT\utils"
New-Item -ItemType Directory -Path "$ROOT\paper\figure_scripts"
New-Item -ItemType Directory -Path "$ROOT\paper\figures"
New-Item -ItemType Directory -Path "$ROOT\dissertation\figures"
New-Item -ItemType Directory -Path "$ROOT\docs\paper"
New-Item -ItemType Directory -Path "$ROOT\docs\superpowers\specs"
New-Item -ItemType Directory -Path "$ROOT\docs\superpowers\plans"
New-Item -ItemType Directory -Path "$ROOT\results\whitelist"
New-Item -ItemType Directory -Path "$ROOT\_legacy"
```

- [ ] **Step 2: Verify all dirs exist**

Run:
```powershell
Get-ChildItem -Path "C:\Users\27443\Desktop\andes-rl-kundur" -Recurse -Directory | Select-Object FullName
```
Expected: All 23 directories listed.

- [ ] **Step 3: Copy this spec to the new repo**

Run:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur"
Copy-Item "$SRC\docs\superpowers\specs\2026-05-15-andes-research-workbench-design.md" `
  "$DST\docs\superpowers\specs\"
Copy-Item "$SRC\docs\superpowers\plans\2026-05-15-andes-rl-kundur-migration.md" `
  "$DST\docs\superpowers\plans\"
```

- [ ] **Step 4: git init + initial commit**

Run:
```powershell
Set-Location "C:\Users\27443\Desktop\andes-rl-kundur"
git init -b main
git add docs/
git commit -m "chore: scaffold andes-rl-kundur skeleton + import spec/plan"
```
Expected: 2 files committed (the spec and the plan).

---

## Phase B — Memory Subsystem Tools (TDD)

The tools handle two responsibilities cleanly separated by file:

- `validate.py` — read frontmatter, run 3 rules + 2 warnings, optionally write back-edges in `--fix` mode
- `render.py` — read frontmatter, emit `STATE.md` from filtered claims + latest round + latest handoff

### Task 2: Write test fixtures

**Files:**
- Create: `memory/tools/tests/fixtures/claims/CLM-0001.md`
- Create: `memory/tools/tests/fixtures/claims/CLM-0002.md`
- Create: `memory/tools/tests/fixtures/claims/CLM-0003.md`
- Create: `memory/tools/tests/fixtures/claims/CLM-0004.md`
- Create: `memory/tools/tests/fixtures/rounds/R01/plan.md`
- Create: `memory/tools/tests/fixtures/rounds/R01/verdict.md`
- Create: `memory/tools/tests/fixtures/rounds/R02/verdict.md`
- Create: `memory/tools/tests/fixtures/handoffs/2026-01-01-init.md`

- [ ] **Step 1: Create fixture claim CLM-0001 (current finding, no relations)**

Path: `memory/tools/tests/fixtures/claims/CLM-0001.md`
```markdown
---
id: CLM-0001
type: finding
trust: V
status: current
statement: |
  Test claim one — simple current finding
round: R01
provenance:
  - path/to/script.py @ deadbeef
tags: [test, headline]
superseded_by: []
---
```

- [ ] **Step 2: Create fixture CLM-0002 (a superseded claim)**

Path: `memory/tools/tests/fixtures/claims/CLM-0002.md`
```markdown
---
id: CLM-0002
type: finding
trust: V
status: superseded
statement: |
  Old value 0.613 — superseded by CLM-0003
round: R01
provenance:
  - path/to/old.py @ deadbeef
tags: [test, headline]
superseded_by: [CLM-0003]
---
```

- [ ] **Step 3: Create fixture CLM-0003 (correction that supersedes CLM-0002)**

Path: `memory/tools/tests/fixtures/claims/CLM-0003.md`
```markdown
---
id: CLM-0003
type: correction
trust: V
status: current
statement: |
  Corrected value 0.444 — supersedes CLM-0002
round: R02
supersedes: [CLM-0002]
provenance:
  - path/to/new.py @ cafebabe
tags: [test, headline]
superseded_by: []
---
```

- [ ] **Step 4: Create fixture CLM-0004 (decision)**

Path: `memory/tools/tests/fixtures/claims/CLM-0004.md`
```markdown
---
id: CLM-0004
type: decision
trust: V
status: current
statement: |
  Test pivot — change direction
round: R02
provenance:
  - memory/rounds/R02/verdict.md
tags: [test, pivot]
superseded_by: []
---
```

- [ ] **Step 5: Create fixture round files**

Path: `memory/tools/tests/fixtures/rounds/R01/plan.md`
```markdown
# R01 plan

Test plan for fixture.
```

Path: `memory/tools/tests/fixtures/rounds/R01/verdict.md`
```markdown
# R01 verdict

Produced: CLM-0001, CLM-0002.
```

Path: `memory/tools/tests/fixtures/rounds/R02/verdict.md`
```markdown
# R02 verdict

Produced: CLM-0003, CLM-0004. Superseded: CLM-0002.
```

- [ ] **Step 6: Create fixture handoff**

Path: `memory/tools/tests/fixtures/handoffs/2026-01-01-init.md`
```markdown
# Initial handoff

Test handoff for fixture.
```

- [ ] **Step 7: Commit fixtures**

Run:
```powershell
git add memory/tools/tests/fixtures/
git commit -m "test: add fixture claims, rounds, handoff for tool tests"
```

### Task 3: Implement `validate.py` (TDD)

**Files:**
- Create: `memory/tools/validate.py`
- Create: `memory/tools/tests/test_validate.py`

- [ ] **Step 1: Write failing test for loading claims**

Path: `memory/tools/tests/test_validate.py`
```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from validate import load_claims  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "claims"


def test_load_claims_returns_dict_of_id_to_frontmatter():
    claims = load_claims(FIXTURES)
    assert set(claims.keys()) == {"CLM-0001", "CLM-0002", "CLM-0003", "CLM-0004"}
    assert claims["CLM-0001"]["type"] == "finding"
    assert claims["CLM-0001"]["status"] == "current"
    assert claims["CLM-0002"]["superseded_by"] == ["CLM-0003"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
Set-Location "C:\Users\27443\Desktop\andes-rl-kundur"
python -m pytest memory/tools/tests/test_validate.py::test_load_claims_returns_dict_of_id_to_frontmatter -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'validate'`.

- [ ] **Step 3: Implement `load_claims`**

Path: `memory/tools/validate.py`
```python
"""Claim ledger validator. Runs 3 hard rules + 2 warnings."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def load_claims(claims_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every CLM-*.md frontmatter into a dict keyed by id."""
    claims: dict[str, dict[str, Any]] = {}
    for path in sorted(claims_dir.glob("CLM-*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"{path.name}: no YAML frontmatter")
        meta = yaml.safe_load(match.group(1)) or {}
        meta["_path"] = path
        meta.setdefault("superseded_by", [])
        meta.setdefault("supersedes", [])
        claims[meta["id"]] = meta
    return claims
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
python -m pytest memory/tools/tests/test_validate.py::test_load_claims_returns_dict_of_id_to_frontmatter -v
```
Expected: PASS.

- [ ] **Step 5: Write failing tests for rules 1-3**

Append to `memory/tools/tests/test_validate.py`:
```python
from validate import validate_rules  # noqa: E402


def test_rule1_duplicate_id_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": [], "superseded_by": []},
        "CLM-0001b": {"id": "CLM-0001", "status": "current",
                      "supersedes": [], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("duplicate id" in e.lower() for e in errors)


def test_rule2_supersedes_nonexistent_target_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": ["CLM-9999"], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("CLM-9999" in e and "does not exist" in e for e in errors)


def test_rule3_current_with_nonempty_superseded_by_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": [], "superseded_by": ["CLM-0002"]},
        "CLM-0002": {"id": "CLM-0002", "status": "current",
                     "supersedes": ["CLM-0001"], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("status: current" in e and "superseded_by" in e for e in errors)


def test_clean_fixtures_have_no_errors():
    claims = load_claims(FIXTURES)
    errors, _warnings = validate_rules(claims)
    assert errors == [], f"Unexpected errors: {errors}"
```

- [ ] **Step 6: Run new tests to verify they fail**

Run:
```powershell
python -m pytest memory/tools/tests/test_validate.py -v
```
Expected: 3 new tests FAIL with `ImportError: cannot import name 'validate_rules'`, the load test still PASSES.

- [ ] **Step 7: Implement `validate_rules`**

Append to `memory/tools/validate.py`:
```python
def validate_rules(claims: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Hard rules go to errors; soft checks to warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    # Rule 1: id uniqueness — already de-duped by dict key; check via duplicate
    # detection across file ids vs dict keys, but since load_claims keys by id,
    # we also check that no two files declared the same id.
    seen_ids: dict[str, Path] = {}
    for key, claim in claims.items():
        cid = claim["id"]
        if cid in seen_ids and seen_ids[cid] != claim.get("_path"):
            errors.append(f"duplicate id {cid} in {claim['_path']} and {seen_ids[cid]}")
        seen_ids[cid] = claim.get("_path")

    # Rule 2: supersedes target must exist
    for claim in claims.values():
        for target in claim.get("supersedes", []) or []:
            if target not in claims:
                errors.append(
                    f"{claim['id']}.supersedes references {target} which does not exist"
                )

    # Rule 3: status: current ↔ superseded_by must be empty
    for claim in claims.values():
        if claim.get("status") == "current" and claim.get("superseded_by"):
            errors.append(
                f"{claim['id']} has status: current but non-empty "
                f"superseded_by: {claim['superseded_by']}"
            )

    # Warning A: forward/back edge symmetry
    for claim in claims.values():
        for target in claim.get("supersedes", []) or []:
            if target not in claims:
                continue
            back = claims[target].get("superseded_by", []) or []
            if claim["id"] not in back:
                warnings.append(
                    f"asymmetric edge: {claim['id']}.supersedes lists {target}, "
                    f"but {target}.superseded_by missing {claim['id']}"
                )

    # Warning B: trust: V requires non-empty provenance
    for claim in claims.values():
        if claim.get("trust") == "V" and not claim.get("provenance"):
            warnings.append(f"{claim['id']} has trust: V but empty provenance")

    return errors, warnings
```

- [ ] **Step 8: Run all tests, verify pass**

Run:
```powershell
python -m pytest memory/tools/tests/test_validate.py -v
```
Expected: 4 passing.

- [ ] **Step 9: Write failing test for `--fix` mode (auto-write back edges + flip status)**

Append to `memory/tools/tests/test_validate.py`:
```python
import shutil
from validate import fix_back_edges  # noqa: E402


def test_fix_back_edges_writes_superseded_by_and_flips_status(tmp_path):
    src = FIXTURES
    dst = tmp_path / "claims"
    shutil.copytree(src, dst)

    # Wipe back edge + status from CLM-0002 to simulate forgotten metadata
    target = dst / "CLM-0002.md"
    content = target.read_text(encoding="utf-8")
    content = content.replace("status: superseded", "status: current")
    content = content.replace("superseded_by: [CLM-0003]", "superseded_by: []")
    target.write_text(content, encoding="utf-8")

    claims = load_claims(dst)
    assert claims["CLM-0002"]["status"] == "current"
    assert claims["CLM-0002"]["superseded_by"] == []

    fix_back_edges(claims, write=True)

    fixed = load_claims(dst)
    assert fixed["CLM-0002"]["status"] == "superseded"
    assert fixed["CLM-0002"]["superseded_by"] == ["CLM-0003"]
```

- [ ] **Step 10: Run new test to verify it fails**

Run:
```powershell
python -m pytest memory/tools/tests/test_validate.py::test_fix_back_edges_writes_superseded_by_and_flips_status -v
```
Expected: FAIL with `ImportError: cannot import name 'fix_back_edges'`.

- [ ] **Step 11: Implement `fix_back_edges` (file rewrite)**

Append to `memory/tools/validate.py`:
```python
def _rewrite_frontmatter(path: Path, updates: dict[str, Any]) -> None:
    """Rewrite the YAML block of a claim file, preserving body and key order
    where possible."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path.name}: no frontmatter to rewrite")
    meta = yaml.safe_load(match.group(1)) or {}
    meta.update(updates)
    new_block = yaml.safe_dump(
        meta, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).strip()
    body = text[match.end():]
    path.write_text(f"---\n{new_block}\n---\n{body}", encoding="utf-8")


def fix_back_edges(claims: dict[str, dict[str, Any]], *, write: bool) -> list[str]:
    """For every X with supersedes: [Y, ...], ensure Y.superseded_by includes X
    and Y.status == 'superseded'. Returns list of changes made."""
    changes: list[str] = []
    for claim in claims.values():
        for target_id in claim.get("supersedes", []) or []:
            target = claims.get(target_id)
            if target is None:
                continue
            back = list(target.get("superseded_by", []) or [])
            need_back = claim["id"] not in back
            need_status = target.get("status") != "superseded"
            if not (need_back or need_status):
                continue
            if need_back:
                back.append(claim["id"])
            updates = {"superseded_by": back, "status": "superseded"}
            changes.append(
                f"{target_id}: superseded_by += {claim['id']}, status -> superseded"
            )
            if write:
                _rewrite_frontmatter(target["_path"], updates)
                target.update(updates)
    return changes
```

- [ ] **Step 12: Run fix-mode test, verify pass**

Run:
```powershell
python -m pytest memory/tools/tests/test_validate.py -v
```
Expected: 5 passing.

- [ ] **Step 13: Add CLI entry point**

Append to `memory/tools/validate.py`:
```python
def main() -> int:
    parser = argparse.ArgumentParser(description="Claim ledger validator")
    parser.add_argument(
        "--claims-dir", type=Path,
        default=Path(__file__).parent.parent / "claims",
        help="path to memory/claims/",
    )
    parser.add_argument("--fix", action="store_true",
                        help="auto-write missing back edges and flip status")
    args = parser.parse_args()

    claims = load_claims(args.claims_dir)
    if args.fix:
        changes = fix_back_edges(claims, write=True)
        for c in changes:
            print(f"FIX: {c}")
        # reload after writing
        claims = load_claims(args.claims_dir)

    errors, warnings = validate_rules(claims)
    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {len(claims)} claims, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 14: Test CLI manually on fixtures**

Run:
```powershell
python memory/tools/validate.py --claims-dir memory/tools/tests/fixtures/claims
```
Expected: `OK: 4 claims, 0 warnings`.

- [ ] **Step 15: Commit validate.py**

Run:
```powershell
git add memory/tools/validate.py memory/tools/tests/test_validate.py
git commit -m "feat(memory): add validate.py with 3 hard rules + 2 warnings + --fix mode"
```

### Task 4: Implement `render.py` (TDD)

**Files:**
- Create: `memory/tools/render.py`
- Create: `memory/tools/tests/test_render.py`

- [ ] **Step 1: Write failing test for STATE.md generation**

Path: `memory/tools/tests/test_render.py`
```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from render import render_state  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_render_state_includes_current_headlines_and_decisions(tmp_path):
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir=FIXTURES / "claims",
        rounds_dir=FIXTURES / "rounds",
        handoffs_dir=FIXTURES / "handoffs",
        out_path=out,
    )
    text = out.read_text(encoding="utf-8")
    # Current headline finding (CLM-0001) appears
    assert "CLM-0001" in text
    # Current correction (CLM-0003) appears
    assert "CLM-0003" in text
    # Current decision (CLM-0004) appears in decisions section
    assert "CLM-0004" in text
    # Superseded claim (CLM-0002) does NOT appear under current
    # (allowed in stats/drift but not in current headlines)
    headlines_section = text.split("## Current Headlines")[1].split("##")[0]
    assert "CLM-0002" not in headlines_section
    # Latest round (R02) referenced
    assert "R02" in text
    # Latest handoff referenced
    assert "2026-01-01-init" in text
    # Stats line includes counts
    assert "4 claims" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest memory/tools/tests/test_render.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'render'`.

- [ ] **Step 3: Implement `render.py`**

Path: `memory/tools/render.py`
```python
"""Render memory/STATE.md from claims + rounds + handoffs."""
from __future__ import annotations
import argparse
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _load_claims(claims_dir: Path) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for path in sorted(claims_dir.glob("CLM-*.md")):
        match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
        if not match:
            continue
        meta = yaml.safe_load(match.group(1)) or {}
        claims.append(meta)
    return claims


def _latest_round(rounds_dir: Path) -> str | None:
    rounds = [p.name for p in rounds_dir.iterdir() if p.is_dir() and p.name.startswith("R")]
    if not rounds:
        return None
    return sorted(rounds, key=lambda r: int(r.lstrip("R")))[-1]


def _latest_handoff(handoffs_dir: Path) -> str | None:
    files = sorted(handoffs_dir.glob("*.md"))
    return files[-1].name if files else None


def _format_claim_line(claim: dict[str, Any]) -> str:
    cid = claim["id"]
    trust = claim.get("trust", "?")
    statement = (claim.get("statement") or "").strip().splitlines()[0]
    round_label = claim.get("round")
    suffix = f" ({round_label})" if round_label else ""
    return f"- {cid} [{trust}] {statement}{suffix}"


def render_state(
    claims_dir: Path, rounds_dir: Path, handoffs_dir: Path, out_path: Path
) -> None:
    claims = _load_claims(claims_dir)
    current = [c for c in claims if c.get("status") == "current"]

    headlines = [c for c in current if "headline" in (c.get("tags") or [])]
    decisions = [c for c in current if c.get("type") == "decision"]

    type_counts = Counter(c.get("type", "?") for c in claims)
    stats_line = (
        f"{len(claims)} claims "
        f"({type_counts.get('finding', 0)} finding / "
        f"{type_counts.get('decision', 0)} decision / "
        f"{type_counts.get('correction', 0)} correction), "
        f"{sum(1 for p in rounds_dir.iterdir() if p.is_dir())} rounds"
    )

    latest_round = _latest_round(rounds_dir) or "(none)"
    latest_handoff = _latest_handoff(handoffs_dir) or "(none)"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    lines.append(f"# Project State — auto-rendered {now}\n")
    lines.append("> Do not edit this file. Regenerate via `python memory/tools/render.py`.\n")
    lines.append("## Current Headlines (status=current, tags=headline)\n")
    if headlines:
        for c in headlines:
            lines.append(_format_claim_line(c))
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("## Open Decisions (type=decision, status=current)\n")
    if decisions:
        for c in decisions:
            lines.append(_format_claim_line(c))
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("## Latest Round\n")
    lines.append(
        f"{latest_round} — see `memory/rounds/{latest_round}/verdict.md`"
        if latest_round != "(none)"
        else "(no rounds yet)"
    )
    lines.append("")
    lines.append("## Most Recent Handoff\n")
    lines.append(
        f"`memory/handoffs/{latest_handoff}`"
        if latest_handoff != "(none)"
        else "(no handoffs yet)"
    )
    lines.append("")
    lines.append("## Stats\n")
    lines.append(stats_line)
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render memory/STATE.md")
    base = Path(__file__).parent.parent
    parser.add_argument("--claims-dir", type=Path, default=base / "claims")
    parser.add_argument("--rounds-dir", type=Path, default=base / "rounds")
    parser.add_argument("--handoffs-dir", type=Path, default=base / "handoffs")
    parser.add_argument("--out", type=Path, default=base / "STATE.md")
    args = parser.parse_args()
    render_state(args.claims_dir, args.rounds_dir, args.handoffs_dir, args.out)
    print(f"Rendered {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test, verify pass**

Run:
```powershell
python -m pytest memory/tools/tests/test_render.py -v
```
Expected: PASS.

- [ ] **Step 5: Test CLI manually on fixtures**

Run:
```powershell
python memory/tools/render.py `
  --claims-dir memory/tools/tests/fixtures/claims `
  --rounds-dir memory/tools/tests/fixtures/rounds `
  --handoffs-dir memory/tools/tests/fixtures/handoffs `
  --out /tmp/STATE_test.md 2>&1
Get-Content /tmp/STATE_test.md
```
Expected: STATE.md content printed, including CLM-0001, CLM-0003, CLM-0004, R02, 2026-01-01-init.

- [ ] **Step 6: Run full tool test suite**

Run:
```powershell
python -m pytest memory/tools/tests/ -v
```
Expected: all tests pass (5 in test_validate + 1 in test_render = 6).

- [ ] **Step 7: Commit render.py**

Run:
```powershell
git add memory/tools/render.py memory/tools/tests/test_render.py
git commit -m "feat(memory): add render.py to generate STATE.md from claims+rounds+handoffs"
```

---

## Phase C — Asset Migration

### Task 5: Copy ANDES code (env / scenarios / probes / agents / utils / evaluation)

**Files:**
- Copy: `env/andes/*`, `scenarios/kundur/train_andes*.py`, `scenarios/new_england/train_andes.py`, `probes/andes_common/*`, `agents/sac*.py`, `agents/ma_manager.py`, `agents/networks.py`, `utils/monitor.py`, `evaluation/paper_grade_axes.py`

- [ ] **Step 1: Copy env/andes**

Run:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur"
Copy-Item "$SRC\env\andes\*.py" "$DST\env\andes\"
```
Verify:
```powershell
Get-ChildItem "$DST\env\andes\*.py" | Measure-Object | ForEach-Object Count
```
Expected: 8 files (`__init__.py`, `base_env.py`, `andes_vsg_env.py`, `andes_vsg_env_v2.py`, `andes_vsg_env_v3.py`, `andes_vsg_env_v4.py`, `andes_ne_env.py`, `andes_ne_regca1_env.py`).

- [ ] **Step 2: Copy scenarios/kundur/train_andes\***

Run:
```powershell
Copy-Item "$SRC\scenarios\kundur\train_andes*.py" "$DST\scenarios\kundur\"
Copy-Item "$SRC\scenarios\kundur\NOTES_ANDES.md" "$DST\scenarios\kundur\"
```
Verify 5 train scripts + NOTES_ANDES.md present.

- [ ] **Step 3: Copy scenarios/new_england/train_andes.py**

Run:
```powershell
if (Test-Path "$SRC\scenarios\new_england\train_andes.py") {
  Copy-Item "$SRC\scenarios\new_england\train_andes.py" "$DST\scenarios\new_england\"
}
```

- [ ] **Step 4: Copy probes/andes_common**

Run:
```powershell
Copy-Item "$SRC\probes\andes_common\*.py" "$DST\probes\andes_common\"
Copy-Item "$SRC\probes\andes_common\README.md" "$DST\probes\andes_common\"
```
Verify: `__init__.py`, `paper_constants.py`, `tracers.py`, `utils.py`, `verdict.py`, `README.md`.

- [ ] **Step 5: Copy agents (selectively — RL only, no Simulink/MATLAB deps)**

Run:
```powershell
Copy-Item "$SRC\agents\sac*.py" "$DST\agents\"
Copy-Item "$SRC\agents\ma_manager.py" "$DST\agents\"
Copy-Item "$SRC\agents\networks.py" "$DST\agents\"
if (Test-Path "$SRC\agents\__init__.py") { Copy-Item "$SRC\agents\__init__.py" "$DST\agents\" }
```

- [ ] **Step 6: Copy utils/monitor.py**

Run:
```powershell
Copy-Item "$SRC\utils\monitor.py" "$DST\utils\"
if (Test-Path "$SRC\utils\__init__.py") { Copy-Item "$SRC\utils\__init__.py" "$DST\utils\" }
```

- [ ] **Step 7: Copy evaluation/paper_grade_axes.py**

Run:
```powershell
Copy-Item "$SRC\evaluation\paper_grade_axes.py" "$DST\evaluation\"
if (Test-Path "$SRC\evaluation\__init__.py") { Copy-Item "$SRC\evaluation\__init__.py" "$DST\evaluation\" }
```

- [ ] **Step 8: Commit code assets**

Run:
```powershell
Set-Location $DST
git add env/ scenarios/ probes/ agents/ utils/ evaluation/
git commit -m "feat: import ANDES env, scenarios, probes, agents, utils, evaluation from Multi-Agent VSGs"
```

### Task 6: Copy research_loop scripts (with triage)

**Files:**
- Copy active: `scripts/research_loop/eval_paper_spec_v2.py`, `eval_v4_*.py`, `r01-r36*.py`, `dump_*.py`, `analyze_*.py`, `experiment_*.py`, `__init__.py`, `check_state.py`, `state_io.py`, `k_max_calc.py`, `handoff_index.py`
- Archive: anything else under `scripts/research_loop/` not in the above list (move to `scripts/research_loop/_archive/`)

- [ ] **Step 1: Copy all .py files from research_loop (preserve all for safety)**

Run:
```powershell
Copy-Item "$SRC\scripts\research_loop\*.py" "$DST\scripts\research_loop\"
```

- [ ] **Step 2: Manual triage — review list and move obvious one-shots to _archive**

Run:
```powershell
Get-ChildItem "$DST\scripts\research_loop\*.py" | Sort-Object Name | ForEach-Object Name
```

Review the list manually. Move scripts matching these patterns to `_archive/`:
- Anything with `_v2`, `_v3` in name where a newer version exists
- One-shot debug scripts (look at file content to decide)
- Dryrun scripts that don't get called by the active probes

If unsure, leave in active. Conservative approach.

```powershell
# Example, adjust per actual review:
# Move-Item "$DST\scripts\research_loop\<script>.py" "$DST\scripts\research_loop\_archive\"
```

- [ ] **Step 3: Commit research_loop scripts**

Run:
```powershell
git add scripts/research_loop/
git commit -m "feat: import scripts/research_loop r01-r36 probes + eval drivers"
```

### Task 7: Copy paper + dissertation + docs/paper

**Files:**
- Copy: `paper/main.tex`, `paper/figure_scripts/*.py`, `paper/figures/*`
- Copy: `dissertation/main.tex`, `dissertation/figures/*`, `dissertation/refs.bib`, `dissertation/unnc-fyp.cls`, `dissertation/CONTEXT.md`, `dissertation/WRITING_STANDARD.md`
- Copy: `docs/paper/kd_4agent_paper_facts.md`, `docs/paper/andes_replication_status_2026-05-07_6axis.md`

- [ ] **Step 1: Copy paper/main.tex + figure_scripts**

Run:
```powershell
Copy-Item "$SRC\paper\main.tex" "$DST\paper\"
Copy-Item "$SRC\paper\figure_scripts\*.py" "$DST\paper\figure_scripts\"
```

- [ ] **Step 2: Copy paper/figures (large, ~36MB)**

Run:
```powershell
Copy-Item "$SRC\paper\figures\*" "$DST\paper\figures\" -Recurse
```
Verify size:
```powershell
(Get-ChildItem "$DST\paper\figures\" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
```
Expected: ~30-40 MB.

- [ ] **Step 3: Copy dissertation/**

Run:
```powershell
$DISS = "C:\Users\27443\Desktop\毕业论文"
Copy-Item "$DISS\dissertation\main.tex" "$DST\dissertation\"
Copy-Item "$DISS\dissertation\refs.bib" "$DST\dissertation\"
Copy-Item "$DISS\dissertation\unnc-fyp.cls" "$DST\dissertation\"
Copy-Item "$DISS\dissertation\monogram.jpg" "$DST\dissertation\"
Copy-Item "$DISS\dissertation\figures\*" "$DST\dissertation\figures\" -Recurse
# Skip .aux/.log/.bbl/.blg/.toc/.out/.lof/.lot (build artifacts; tex compile will regenerate)
```

- [ ] **Step 4: Copy 毕业论文 top-level docs into dissertation/**

Run:
```powershell
Copy-Item "$DISS\CONTEXT.md" "$DST\dissertation\CONTEXT.md"
Copy-Item "$DISS\WRITING_STANDARD.md" "$DST\dissertation\WRITING_STANDARD.md"
```

- [ ] **Step 5: Copy docs/paper**

Run:
```powershell
Copy-Item "$SRC\docs\paper\kd_4agent_paper_facts.md" "$DST\docs\paper\"
Copy-Item "$SRC\docs\paper\andes_replication_status_2026-05-07_6axis.md" "$DST\docs\paper\"
```

- [ ] **Step 6: Commit paper + dissertation**

Run:
```powershell
git add paper/ dissertation/ docs/paper/
git commit -m "feat: import paper/main.tex + figures + dissertation + docs/paper facts"
```

### Task 8: Trim config.py (ANDES sections only)

**Files:**
- Create: `config.py` (modified copy from source)

- [ ] **Step 1: Read source config.py to understand sections**

Read `C:\Users\27443\Desktop\Multi-Agent  VSGs\config.py` to identify ANDES vs ODE vs Simulink sections.

- [ ] **Step 2: Copy and trim**

Use Edit on a copied version: copy first, then remove sections.

```powershell
Copy-Item "$SRC\config.py" "$DST\config.py"
```

Open `$DST\config.py` and delete:
- ODE-specific config blocks (search for `ODE`, `multi_vsg_env`)
- Simulink-specific blocks (search for `SIMULINK`, `KUNDUR_BRIDGE_CONFIG`, `kundur_simulink`, `ne39_simulink`)

Keep:
- ANDES system parameters (H/D ranges, M0)
- Training hparams (LR, BATCH_SIZE, BUFFER_SIZE, etc.)
- Disturbance ranges (P_step values)
- Anything imported by `env/andes/*` or `scenarios/kundur/train_andes*.py`

After trimming, verify it still imports:
```powershell
python -c "import sys; sys.path.insert(0, '$DST'); import config; print('OK')"
```

- [ ] **Step 3: Commit trimmed config.py**

Run:
```powershell
Set-Location $DST
git add config.py
git commit -m "feat: import config.py trimmed to ANDES sections only"
```

---

## Phase D — results/ Strategy + .gitignore

### Task 9: Set up .gitignore and results/whitelist

**Files:**
- Create: `.gitignore`
- Create: `results/MANIFEST.md`
- Copy: key ckpts + eval JSON into `results/whitelist/`

- [ ] **Step 1: Write .gitignore**

Path: `.gitignore`
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
*.egg-info/

# OS
.DS_Store
Thumbs.db

# LaTeX build artifacts
*.aux
*.log
*.bbl
*.blg
*.toc
*.out
*.lof
*.lot
*.synctex.gz
*.fdb_latexmk
*.fls

# Training artifacts — gitignored except whitelist
results/*
!results/MANIFEST.md
!results/whitelist/
!results/whitelist/**

# Local config
.env
.venv/
venv/

# Editor
.vscode/
.idea/
```

- [ ] **Step 2: Write results/MANIFEST.md skeleton**

Path: `results/MANIFEST.md`
```markdown
# results/ Manifest

This directory is gitignored except for `whitelist/` (paper-cited checkpoints
and eval JSON) and this manifest itself.

## Why

Training artifacts can reach GB scale per round. Storing everything in git would
bloat the repo and slow clones. The whitelist contains only what the paper
directly cites; everything else is local-only.

## How to bring local artifacts in

Sibling local directory (not committed) contains the full training results.
Symlink or copy as needed:

```powershell
# Example: bring R21 best.pt from the source repo
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\results"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\results"
Copy-Item "$SRC\<run_dir>\best.pt" "$DST\<run_dir>\"
```

## Whitelist contents

| Path | Source | Cited by | Notes |
|------|--------|----------|-------|
| `whitelist/andes_paper_alignment_6axis_2026-05-07.json` | r30 ranker fix re-rank | paper §V-A, §V-B | post-fix headline ranking (CLM ledger source) |
| `whitelist/R21_v4_h50_s49_best.pt` | R21 lucky single | paper §V-A | 0.444 score ckpt (lineage: 0.613 pre-fix) |
| `whitelist/no_control_baseline.json` | baseline eval | paper §V | 0.104 baseline |
| `whitelist/HAWE_w9802_config.json` | R30 HAWE recipe | paper §V-B | 99.3% R21 |
| ... | | | |

(Update this table when adding files to whitelist/.)

## What is NOT in whitelist

- Per-step trajectory dumps from training runs
- Per-seed full result trees (e.g., `andes_dfloor_seed42/`)
- Intermediate ensemble eval JSON files
- Smoke test logs

These are reproducible from the code in this repo + the artifacts in the source
repo. If a future paper or revision needs to cite them, add to whitelist.
```

- [ ] **Step 3: Populate results/whitelist with key files**

Run:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\results"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\results\whitelist"
Copy-Item "$SRC\andes_paper_alignment_6axis_2026-05-07.json" "$DST\"
```

Then, for the R21 best.pt and HAWE/no_control artifacts, examine source directories and copy only the specific `.pt` and JSON files cited:

```powershell
# Identify R21 ckpt directory and copy best.pt
Get-ChildItem "$SRC" -Filter "*v4*h50*s49*" -Directory | ForEach-Object {
  $bestpt = Join-Path $_.FullName "best.pt"
  if (Test-Path $bestpt) { Copy-Item $bestpt "$DST\R21_v4_h50_s49_best.pt" }
}
# Similarly for HAWE config (if persisted as JSON) and no_control baseline
```

If the exact file names differ, look them up using:
```powershell
Get-ChildItem "$SRC" -Filter "*.json" -Recurse | Where-Object Name -match "no_control" | ForEach-Object FullName
```

Document each copy in the MANIFEST.md table.

- [ ] **Step 4: Commit .gitignore + manifest + whitelist**

Run:
```powershell
Set-Location $DST
cd ..
git add .gitignore results/MANIFEST.md results/whitelist/
git commit -m "chore: add .gitignore with results/ whitelist strategy + key ckpts"
```

---

## Phase E — Memory Population (rounds, handoffs, _legacy)

### Task 10: Migrate quality_reports/research_loop → memory/rounds

**Files:**
- Source: `C:\Users\27443\Desktop\Multi-Agent  VSGs\quality_reports\research_loop\round_*.md` (37 rounds + audits + incidents)
- Destination: `memory/rounds/RNN/{plan.md,verdict.md}`

- [ ] **Step 1: Enumerate source rounds**

Run:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\quality_reports\research_loop"
Get-ChildItem "$SRC\round_*_plan.md" | ForEach-Object BaseName | Sort-Object
Get-ChildItem "$SRC\round_*_verdict.md" | ForEach-Object BaseName | Sort-Object
```

Note rounds where only verdict (no plan) or only plan exists; rounds with merged names like `round_11_13_mvv_verdict.md` or `round_28_to_34_final_verdict.md`.

- [ ] **Step 2: For each round number N, create memory/rounds/RNN/ and copy plan/verdict**

Run script:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\quality_reports\research_loop"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\memory\rounds"
$rounds = @{}
Get-ChildItem "$SRC\round_*.md" | ForEach-Object {
  if ($_.Name -match "round_(\d+)_") {
    $n = [int]$matches[1]
    if (-not $rounds.ContainsKey($n)) { $rounds[$n] = @() }
    $rounds[$n] += $_.FullName
  }
}
foreach ($n in $rounds.Keys | Sort-Object) {
  $rdir = Join-Path $DST ("R{0:D2}" -f $n)
  New-Item -ItemType Directory -Path $rdir -Force | Out-Null
  foreach ($f in $rounds[$n]) {
    $name = Split-Path $f -Leaf
    if ($name -match "_plan\.md$") { Copy-Item $f "$rdir\plan.md" -Force }
    elseif ($name -match "_verdict\.md$") { Copy-Item $f "$rdir\verdict.md" -Force }
    else { Copy-Item $f "$rdir\$name" -Force }   # multi-round files like round_11_13_mvv_verdict.md
  }
}
```

- [ ] **Step 3: Copy audits / incidents into hosting round**

Run:
```powershell
$AUDITS = "$SRC\audits"
$INCIDENTS = "$SRC\incidents"
foreach ($d in @($AUDITS, $INCIDENTS)) {
  if (-not (Test-Path $d)) { continue }
  Get-ChildItem "$d\*.md" -ErrorAction SilentlyContinue | ForEach-Object {
    # Match filename like "r10_..." or "2026-05-07_..." — try to assign to round if possible
    if ($_.Name -match "^r(\d+)_") {
      $n = [int]$matches[1]
      $rdir = Join-Path $DST ("R{0:D2}" -f $n)
      if (Test-Path $rdir) {
        Copy-Item $_.FullName "$rdir\$($_.Name)" -Force
      } else {
        # No matching round dir; put in _legacy as audit/incident archive
        New-Item -ItemType Directory -Path "$DST\..\..\_legacy\audits" -Force | Out-Null
        Copy-Item $_.FullName "$DST\..\..\_legacy\audits\$($_.Name)" -Force
      }
    } else {
      # Date-stamped or unparseable filenames — drop in _legacy
      New-Item -ItemType Directory -Path "$DST\..\..\_legacy\audits" -Force | Out-Null
      Copy-Item $_.FullName "$DST\..\..\_legacy\audits\$($_.Name)" -Force
    }
  }
}
```

- [ ] **Step 4: Verify round count**

Run:
```powershell
Get-ChildItem "$DST" -Directory | Measure-Object | ForEach-Object Count
```
Expected: roughly 37 round directories (might be 30-40 depending on numbering gaps).

- [ ] **Step 5: Commit rounds migration**

Run:
```powershell
Set-Location "C:\Users\27443\Desktop\andes-rl-kundur"
git add memory/rounds/ _legacy/audits/
git commit -m "feat(memory): migrate quality_reports/research_loop rounds + audits/incidents"
```

### Task 11: Migrate handoffs

**Files:**
- Source: `C:\Users\27443\Desktop\Multi-Agent  VSGs\quality_reports\handoff\*andes*` and `C:\Users\27443\Desktop\毕业论文\plan\2026-05-*v17*`, `2026-05-07_handoff_v*`
- Destination: `memory/handoffs/YYYY-MM-DD-<topic>.md`

- [ ] **Step 1: Copy ANDES handoffs from source repo**

Run:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\quality_reports\handoff"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\memory\handoffs"
Get-ChildItem "$SRC\*andes*.md" | ForEach-Object {
  Copy-Item $_.FullName "$DST\$($_.Name)" -Force
}
```

- [ ] **Step 2: Copy 毕业论文/plan handoff_v* files**

Run:
```powershell
$PLAN = "C:\Users\27443\Desktop\毕业论文\plan"
Get-ChildItem "$PLAN\2026-05-*handoff_v*.md" | ForEach-Object {
  Copy-Item $_.FullName "$DST\$($_.Name)" -Force
}
Get-ChildItem "$PLAN\2026-05-08*v17*.md" | ForEach-Object {
  Copy-Item $_.FullName "$DST\$($_.Name)" -Force
}
```

- [ ] **Step 3: Verify list**

Run:
```powershell
Get-ChildItem "$DST\*.md" | ForEach-Object Name | Sort-Object
```
Expected: 5-10 handoff files spanning 2026-05-07 to 2026-05-08.

- [ ] **Step 4: Commit handoffs**

Run:
```powershell
Set-Location "C:\Users\27443\Desktop\andes-rl-kundur"
git add memory/handoffs/
git commit -m "feat(memory): migrate ANDES handoffs + 毕业论文 plan v12-v17"
```

### Task 12: Populate _legacy with frozen source-of-truth docs

**Files:**
- Source: `RESEARCH_TRAIL.md`, `CONTEXT.md`, `ANDES.md` from `C:\Users\27443\Desktop\Multi-Agent  VSGs\`
- Destination: `_legacy/`

- [ ] **Step 1: Copy frozen source docs**

Run:
```powershell
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\_legacy"
Copy-Item "$SRC\RESEARCH_TRAIL.md" "$DST\"
Copy-Item "$SRC\CONTEXT.md" "$DST\"
Copy-Item "$SRC\ANDES.md" "$DST\"
```

- [ ] **Step 2: Add legacy README**

Path: `_legacy/README.md`
```markdown
# _legacy/

Frozen source-of-truth documents from the predecessor repository
`Multi-Agent  VSGs`. These files are **NOT the current state** — the current
state is in `memory/claims/`, `memory/rounds/`, and `memory/STATE.md`.

These files are retained for:
1. **Audit trail** — verifying that the migrated claim ledger faithfully
   represents the original research record.
2. **Reflection writing** — paper/dissertation §VI reflection can mine these
   for context that the lite migration did not extract.
3. **Forensic** — if any claim's provenance is questioned, the original
   document is here.

**Do not edit these files.** If a fact in `_legacy/` contradicts a current
claim, the current claim is authoritative (and ideally cites the legacy
provenance). File a `type: correction` claim if reconciliation is needed.

## Files

| File | Original purpose |
|------|------------------|
| `RESEARCH_TRAIL.md` | R01-R37 causal trail with 6 拐点 (caveman style) |
| `CONTEXT.md` | ANDES track engineering context + anti-patterns |
| `ANDES.md` | Original entry-point doc |
| `audits/` | Cross-round audit reports that did not map cleanly to a single round |
```

- [ ] **Step 3: Commit _legacy**

Run:
```powershell
Set-Location "C:\Users\27443\Desktop\andes-rl-kundur"
git add _legacy/
git commit -m "feat: import frozen _legacy/ from source repo (audit trail)"
```

---

## Phase F — Knowledge Sedimentation (Lite, 30-50 Claims)

### Task 13: Author headline drift chain claims (8 claims)

**Files:**
- Create: `memory/claims/CLM-0001.md` through `memory/claims/CLM-0008.md`

This task assigns IDs 0001-0008. Each step authors one claim. Sources are `_legacy/RESEARCH_TRAIL.md` §1 + §11, `_legacy/CONTEXT.md` §11, paper §V-A.

- [ ] **Step 1: CLM-0001 — pre-fix R21 lucky single 0.613 (now superseded)**

Path: `memory/claims/CLM-0001.md`
```markdown
---
id: CLM-0001
type: finding
trust: V
status: superseded
statement: |
  R21 V4 ckpt h50_s49 6-axis overall = 0.613 (lucky single, pre-r30 ranker fix)
round: R21
provenance:
  - scripts/research_loop/eval_v4_ddic.py @ 9bc7a08
  - _legacy/RESEARCH_TRAIL.md §1
tags: [headline, numerical, 6-axis, pre-fix]
superseded_by: [CLM-0005]
---

# Context
This was the historic high-water mark before the r30 ranker audit
revealed that the geo-mean aggregation had a bug. Preserved here so
§VI reflection can trace the drift.
```

- [ ] **Step 2: CLM-0002 — pre-fix HAWE w8515 = 0.554 (superseded)**

Path: `memory/claims/CLM-0002.md`
```markdown
---
id: CLM-0002
type: finding
trust: V
status: superseded
statement: |
  HAWE w8515 (85% R21 + 15% ws8) 6-axis = 0.554 (R30 pre-fix)
round: R30
provenance:
  - scripts/research_loop/eval_v4_ensemble.py @ 9bc7a08
  - _legacy/RESEARCH_TRAIL.md §1
tags: [headline, numerical, HAWE, pre-fix]
superseded_by: [CLM-0006]
---
```

- [ ] **Step 3: CLM-0003 — pre-fix HAWE w9802 = 0.607 (superseded)**

Path: `memory/claims/CLM-0003.md`
```markdown
---
id: CLM-0003
type: finding
trust: V
status: superseded
statement: |
  HAWE w9802 (98% R21 + 2% ws8) 6-axis = 0.607 (R30 pre-fix; fresh-seed)
round: R30
provenance:
  - scripts/research_loop/eval_v4_ensemble.py @ 9bc7a08
  - _legacy/RESEARCH_TRAIL.md §1
tags: [headline, numerical, HAWE, pre-fix]
superseded_by: [CLM-0007]
---
```

- [ ] **Step 4: CLM-0004 — pre-fix no_control baseline = 0.110 (superseded)**

Path: `memory/claims/CLM-0004.md`
```markdown
---
id: CLM-0004
type: finding
trust: V
status: superseded
statement: |
  no_control baseline 6-axis = 0.110 (R30 pre-fix)
round: R30
provenance:
  - scripts/research_loop/eval_v4_no_control.py @ 9bc7a08
tags: [headline, numerical, baseline, pre-fix]
superseded_by: [CLM-0008]
---
```

- [ ] **Step 5: CLM-0005 — post-fix R21 = 0.444 (CURRENT, supersedes CLM-0001)**

Path: `memory/claims/CLM-0005.md`
```markdown
---
id: CLM-0005
type: correction
trust: V
status: current
statement: |
  R21 V4 h50_s49 6-axis = 0.444 (post r30/N1c ranker fix; 4.04× no_ctrl 0.104)
round: R30
supersedes: [CLM-0001]
provenance:
  - scripts/research_loop/eval_paper_spec_v2.py @ 2d9708e
  - results/whitelist/andes_paper_alignment_6axis_2026-05-07.json
  - _legacy/CONTEXT.md §11
tags: [headline, numerical, 6-axis, §V-A]
superseded_by: []
---

# Context
The r30 ranker audit (N1c) fixed the geo-mean aggregation across scenarios
+ added NaN/tds_failed guards. R21 dropped from 0.613 → 0.444 but remained
the highest reproducible single-seed score.
```

- [ ] **Step 6: CLM-0006 — post-fix HAWE w8515 (CURRENT, supersedes CLM-0002)**

Path: `memory/claims/CLM-0006.md`
```markdown
---
id: CLM-0006
type: correction
trust: V
status: current
statement: |
  HAWE w8515 post-fix 6-axis ≈ 0.42 (placeholder — fill exact value from JSON)
round: R30
supersedes: [CLM-0002]
provenance:
  - results/whitelist/andes_paper_alignment_6axis_2026-05-07.json
tags: [headline, numerical, HAWE, §V-B]
superseded_by: []
---
```
**Note:** Replace "0.42 (placeholder)" with the exact post-fix value from
`results/whitelist/andes_paper_alignment_6axis_2026-05-07.json`. Open the JSON
to extract.

- [ ] **Step 7: CLM-0007 — post-fix HAWE w9802 = 0.439 (CURRENT)**

Path: `memory/claims/CLM-0007.md`
```markdown
---
id: CLM-0007
type: correction
trust: V
status: current
statement: |
  HAWE w9802 post-fix 6-axis = 0.439 = 99.3% of R21 (fresh-seed reproducible)
round: R30
supersedes: [CLM-0003]
provenance:
  - results/whitelist/andes_paper_alignment_6axis_2026-05-07.json
  - _legacy/CONTEXT.md §11
tags: [headline, numerical, HAWE, §V-B, asset5]
superseded_by: []
---

# Context
99.3% recovery of R21 via heterogeneous-actor ensemble. Refutes the
fresh-seed lineage cycle. Forms the basis of Asset 5 (HAWE).
```

- [ ] **Step 8: CLM-0008 — post-fix no_control = 0.104 (CURRENT)**

Path: `memory/claims/CLM-0008.md`
```markdown
---
id: CLM-0008
type: correction
trust: V
status: current
statement: |
  no_control baseline 6-axis = 0.104 (post r30 ranker fix)
round: R30
supersedes: [CLM-0004]
provenance:
  - results/whitelist/andes_paper_alignment_6axis_2026-05-07.json
tags: [headline, numerical, baseline, §V-A]
superseded_by: []
---
```

- [ ] **Step 9: Run validate.py in --fix mode**

Run:
```powershell
python memory/tools/validate.py --fix
```
Expected:
- 4 FIX lines printed (CLM-0001, 0002, 0003, 0004 had explicit `superseded_by` already; tool detects no change needed) OR 0 FIX lines if the back-edges were pre-filled correctly.
- `OK: 8 claims, 0 warnings` at end.

- [ ] **Step 10: Commit headline claims**

Run:
```powershell
git add memory/claims/CLM-000[1-8].md
git commit -m "feat(memory): seed 8 headline drift chain claims (R21/HAWE/no_control pre+post fix)"
```

### Task 14: Author 6-pivot decision claims (6 claims)

**Files:** `memory/claims/CLM-0009.md` through `CLM-0014.md`

Source: `_legacy/RESEARCH_TRAIL.md` §1 (6 拐点 enumeration), `_legacy/CONTEXT.md` §6.

- [ ] **Step 1: CLM-0009 — Pivot 1: R06 axes.py Bug-A discovery**

Path: `memory/claims/CLM-0009.md`
```markdown
---
id: CLM-0009
type: decision
trust: V
status: current
statement: |
  Pivot 1 (R06): four parallel audit forks discovered axes.py Bug-A (range axis
  formula semantically inverted — box bound treated as trajectory span)
round: R06
provenance:
  - memory/rounds/R06/verdict.md
  - _legacy/RESEARCH_TRAIL.md §3
tags: [pivot, audit, §VI]
superseded_by: []
---
```

- [ ] **Step 2: CLM-0010 — Pivot 2: R10-R17 V4 env creation**

Path: `memory/claims/CLM-0010.md`
```markdown
---
id: CLM-0010
type: decision
trust: V
status: current
statement: |
  Pivot 2 (R10-R17): four ANDES forensic bugs identified (IEEEG1 DAE_INACTIVE,
  G4 inertia, DT 3× aliasing, baseline H₀+D₀ paper-deviation); V4 env
  consolidates all fixes; ANDES path RE-OPENED
round: R17
provenance:
  - memory/rounds/R10/verdict.md
  - memory/rounds/R17/verdict.md
  - env/andes/andes_vsg_env_v4.py
tags: [pivot, forensic, §VI]
superseded_by: []
---
```

- [ ] **Step 3: CLM-0011 — Pivot 3: R21 V4_h50_s49 0.613 lucky single**

Path: `memory/claims/CLM-0011.md`
```markdown
---
id: CLM-0011
type: decision
trust: V
status: current
statement: |
  Pivot 3 (R21): V4_h50_s49 reached 6-axis 0.613 (pre-fix) — 17× V2 attractor,
  paper-grade alignment confirmed on ANDES; ANDES path RE-OPENED → COMPLETED
round: R21
provenance:
  - memory/rounds/R21/verdict.md
  - _legacy/RESEARCH_TRAIL.md §3
tags: [pivot, breakthrough, §VI]
superseded_by: []
---
```

- [ ] **Step 4: CLM-0012 — Pivot 4: R24 multi-seed reveals R21 outlier**

Path: `memory/claims/CLM-0012.md`
```markdown
---
id: CLM-0012
type: decision
trust: V
status: current
statement: |
  Pivot 4 (R24): 22-ckpt multi-seed reproduction returns ≤ 0.22 ceiling;
  R21 confirmed as lucky outlier; per-agent dominance hypothesis triggered
round: R24
provenance:
  - memory/rounds/R24/verdict.md
tags: [pivot, validation, §VI]
superseded_by: []
---
```

- [ ] **Step 5: CLM-0013 — Pivot 5: R30 HAWE ensemble breakthrough**

Path: `memory/claims/CLM-0013.md`
```markdown
---
id: CLM-0013
type: decision
trust: V
status: current
statement: |
  Pivot 5 (R30): HAWE 2-actor weighted ensemble (R21+ws8) inference-time
  innovation reaches 0.554 (pre-fix); promoted to Asset 5
round: R30
provenance:
  - memory/rounds/R30/verdict.md
  - scripts/research_loop/eval_v4_ensemble.py
tags: [pivot, ensemble, asset5, §V-B]
superseded_by: []
---
```

- [ ] **Step 6: CLM-0014 — Pivot 6: r30 ranker N1c fix**

Path: `memory/claims/CLM-0014.md`
```markdown
---
id: CLM-0014
type: decision
trust: V
status: current
statement: |
  Pivot 6 (r30 audit): ranker N1c geo-mean across scenarios + NaN/tds_failed
  guard; final paper headline locked at 0.444 (R21) and 0.439 (HAWE w9802)
round: R36
provenance:
  - memory/rounds/R36/verdict.md
  - evaluation/paper_grade_axes.py @ 2d9708e
  - _legacy/CONTEXT.md §11
tags: [pivot, ranker, §VI]
superseded_by: []
---
```

- [ ] **Step 7: Validate + commit**

Run:
```powershell
python memory/tools/validate.py --fix
git add memory/claims/CLM-00[09|10-14]*.md
git commit -m "feat(memory): seed 6 pivot decision claims (R06/R17/R21/R24/R30/R36)"
```

### Task 15: Author 5 bespoke asset claims (5 claims)

**Files:** `memory/claims/CLM-0015.md` through `CLM-0019.md`

Source: `_legacy/CONTEXT.md` "5 Bespoke Asset" section, `dissertation/main.tex` §Asset 1-5.

- [ ] **Step 1: CLM-0015 — Asset 1: MCP Simulink toolkit**

Path: `memory/claims/CLM-0015.md`
```markdown
---
id: CLM-0015
type: finding
trust: V
status: current
statement: |
  Asset 1: MCP Simulink toolkit (45 structured tools) — Python FastMCP server
  exposing Simulink runtime control to AI agents
round:
provenance:
  - _legacy/CONTEXT.md §5-bespoke-asset
  - dissertation/main.tex §Asset 1
tags: [asset, asset1, infrastructure, §IV]
superseded_by: []
---

# Note
Not migrated into andes-rl-kundur (Simulink-specific). Source code remains in
predecessor repo. Cited here as a research contribution.
```

- [ ] **Step 2: CLM-0016 — Asset 2: Simulink-as-RL bridge**

Path: `memory/claims/CLM-0016.md`
```markdown
---
id: CLM-0016
type: finding
trust: V
status: current
statement: |
  Asset 2: Simulink-as-RL-Environment bridge — single-IPC-per-step Python ↔
  MATLAB engine layer enabling SAC training on Simulink models
round:
provenance:
  - _legacy/CONTEXT.md §5-bespoke-asset
  - dissertation/main.tex §Asset 2
tags: [asset, asset2, infrastructure, §IV]
superseded_by: []
---
```

- [ ] **Step 3: CLM-0017 — Asset 3: TDD probe layer**

Path: `memory/claims/CLM-0017.md`
```markdown
---
id: CLM-0017
type: finding
trust: V
status: current
statement: |
  Asset 3: TDD-inspired diagnostic probe layer — 760 LOC of reusable ANDES
  probe utilities (paper_constants, tracers, verdict, utils) in
  probes/andes_common/
round:
provenance:
  - probes/andes_common/README.md
  - dissertation/main.tex §Asset 3
tags: [asset, asset3, infrastructure, §IV]
superseded_by: []
---
```

- [ ] **Step 4: CLM-0018 — Asset 4: Six-axis paper-alignment ranker**

Path: `memory/claims/CLM-0018.md`
```markdown
---
id: CLM-0018
type: finding
trust: V
status: current
statement: |
  Asset 4: Six-axis paper-alignment ranker (evaluation/paper_grade_axes.py)
  — max_df / final_df / settling / smoothness / ΔH-range / ΔD-range geo-mean
  aggregation per LS1/LS2, with audit-driven N1c fix
round:
provenance:
  - evaluation/paper_grade_axes.py @ 2d9708e
  - dissertation/main.tex §Asset 4
  - memory/rounds/R36/verdict.md
tags: [asset, asset4, evaluation, §IV]
superseded_by: []
---
```

- [ ] **Step 5: CLM-0019 — Asset 5: HAWE Heterogeneous Actor Weighted Ensemble**

Path: `memory/claims/CLM-0019.md`
```markdown
---
id: CLM-0019
type: finding
trust: V
status: current
statement: |
  Asset 5: HAWE Heterogeneous Actor Weighted Ensemble — inference-time
  weighted aggregation of pretrained SAC actors across agent slots; achieves
  99.3% of R21 lucky-single via 98/2 weight on diverse seeds
round: R30
provenance:
  - scripts/research_loop/eval_v4_ensemble.py
  - dissertation/main.tex §Asset 5
  - results/whitelist/andes_paper_alignment_6axis_2026-05-07.json
tags: [asset, asset5, ensemble, §V-B]
superseded_by: []
---
```

- [ ] **Step 6: Validate + commit**

Run:
```powershell
python memory/tools/validate.py --fix
git add memory/claims/CLM-001[5-9].md
git commit -m "feat(memory): seed 5 bespoke asset claims (MCP/Bridge/Probes/Ranker/HAWE)"
```

### Task 16: Author anti-pattern correction claims (10 claims)

**Files:** `memory/claims/CLM-0020.md` through `CLM-0029.md`

Source: `_legacy/CONTEXT.md` §2 (anti-patterns table, 12 rows). Select 10 most-cited; one row produces TWO claims (the wrong belief + the correction).

For each anti-pattern: author one `type: correction` claim that states the truth and refutes a hypothetical "wrong belief" claim. (We do not need to author the wrong belief explicitly — the correction's statement encodes the refutation.)

- [ ] **Step 1: CLM-0020 — V3 governor wiring "worked" was wrong**

Path: `memory/claims/CLM-0020.md`
```markdown
---
id: CLM-0020
type: correction
trust: V
status: current
statement: |
  V3 env governor wiring claim WRONG: R08 measured governor on/off diff = 0.000,
  R10 found IEEEG1 entire model DAE_INACTIVE (0 Algeb/State). V3 governor dead.
round: R10
provenance:
  - memory/rounds/R08/verdict.md
  - memory/rounds/R10/verdict.md
  - _legacy/CONTEXT.md §2
tags: [anti-pattern, correction, governor, §IV-C]
superseded_by: []
---
```

- [ ] **Step 2: CLM-0021 — V4 default H₀=10 (wrong, actual 100)**

Path: `memory/claims/CLM-0021.md`
```markdown
---
id: CLM-0021
type: correction
trust: V
status: current
statement: |
  V4 default H₀ is 100 (paper-faithful Eq.12 box middle), NOT 10. V1/V2 used
  H₀=10. V4 is the paper-faithful baseline env.
round: R17
provenance:
  - env/andes/andes_vsg_env_v4.py
  - _legacy/CONTEXT.md §2
tags: [anti-pattern, correction, env-config]
superseded_by: []
---
```

- [ ] **Step 3-10: CLM-0022 through CLM-0029 — remaining anti-patterns**

For each row in `_legacy/CONTEXT.md` §2 you have not yet covered, author one
correction claim using the same template. Coverage targets:
- axes.py range axis formula correctness refuted (R06 found Bug-A)
- settling = ∞ being a "physical model problem" — actually 6s truncate bug (R28')
- Phase A-E recovery plan still active — actually abandoned, replaced by R28-R34
- 8 ANDES processes parallel OK — actually ≤ 3
- Stochastic ensemble can improve R21 — R32 refutes
- Reward shaping (PHI_MAX/PHI_SETTLE) can improve max_df/settling — R31/R33 refute
- Hparam sweep (PHI_ABS/PHI_H/PHI_F) can improve R21 — R29 refutes
- R21 0.613 best.pt = R23+ best.pt — different files (1.31MB vs 2.56MB)

Each claim follows the same shape as CLM-0020/0021. Use `_legacy/CONTEXT.md` §2 row contents for `statement` and `provenance`.

- [ ] **Step 11: Validate + commit**

Run:
```powershell
python memory/tools/validate.py --fix
git add memory/claims/CLM-002[0-9].md
git commit -m "feat(memory): seed 10 anti-pattern correction claims (from _legacy CONTEXT §2)"
```

### Task 17: Author paper-cited fact claims (~10 claims)

**Files:** `memory/claims/CLM-0030.md` through `CLM-0039.md`

Source: `paper/main.tex` (§Disclosed deviations, §Per-agent dominance, §LS asymmetry, etc.).

- [ ] **Step 1: CLM-0030 — Disclosed deviation 1: action range 33×**

Path: `memory/claims/CLM-0030.md`
```markdown
---
id: CLM-0030
type: finding
trust: V
status: current
statement: |
  Disclosed deviation #1: action range is 33× wider than paper Sec.IV-B
  (ΔH±16.1 / ΔD±72 vs paper ±0.5 / ±2.0). Required to keep SAC exploration
  off the box wall.
round:
provenance:
  - paper/main.tex §IV-C "Project deviations"
  - config.py (H_MIN/H_MAX/D_MIN/D_MAX)
tags: [paper-fact, deviation, §IV-C]
superseded_by: []
---
```

- [ ] **Step 2: CLM-0031 — Disclosed deviation 2: φ scaling 2000×**

Path: `memory/claims/CLM-0031.md`
```markdown
---
id: CLM-0031
type: finding
trust: V
status: current
statement: |
  Disclosed deviation #2: φ_H / φ_D reward scaling is 0.0056 (paper Eq.14
  uses 1.0). Without this rescale, reward diverges at ep > 75 under the wider
  action range (deviation #1).
round: R18
provenance:
  - paper/main.tex §IV-C
  - memory/rounds/R18/verdict.md
tags: [paper-fact, deviation, §IV-C, reward]
superseded_by: []
---
```

- [ ] **Step 3: CLM-0032 — Disclosed deviation 3: Pm_step calibration**

Path: `memory/claims/CLM-0032.md`
```markdown
---
id: CLM-0032
type: finding
trust: V
status: current
statement: |
  Disclosed deviation #3: Pm_step injection calibrated to 1.53 / 0.90 sys_pu
  for buses 14 / 15 (paper used 2.48 / 1.88 sys_pu, unreachable on this
  ANDES Kundur topology)
round:
provenance:
  - paper/main.tex §IV-C
  - probes/andes_common/paper_constants.py (PAPER_LS_MAGNITUDE_SYS_PU)
tags: [paper-fact, deviation, §IV-C, disturbance]
superseded_by: []
---
```

- [ ] **Step 4: CLM-0033 — Per-agent dominance pattern**

Path: `memory/claims/CLM-0033.md`
```markdown
---
id: CLM-0033
type: finding
trust: V
status: current
statement: |
  Per-agent dominance: one of the 4 agents accumulates >60% reward share
  across all seeds (per Gini analysis); root of R21 lucky-single fragility
round:
provenance:
  - paper/main.tex §ssec:dominance
  - paper/figure_scripts/analyze_per_agent_contribution.py
  - paper/figures/v4_per_agent_contribution_bars.png
tags: [paper-fact, dominance, §V-C]
superseded_by: []
---
```

- [ ] **Step 5: CLM-0034 — LS1 vs LS2 asymmetry**

Path: `memory/claims/CLM-0034.md`
```markdown
---
id: CLM-0034
type: finding
trust: V
status: current
statement: |
  LS1 vs LS2 axis-score asymmetry: R21 LS1 overall = 0.80 vs LS2 = 0.43;
  failure clusters on disturbance-host bus 15
round: R21
provenance:
  - memory/rounds/R21/verdict.md
  - results/whitelist/andes_paper_alignment_6axis_2026-05-07.json
tags: [paper-fact, LS-asymmetry, §V-A]
superseded_by: []
---
```

- [ ] **Step 6: CLM-0035 — Cross-platform 1.42× residual**

Path: `memory/claims/CLM-0035.md`
```markdown
---
id: CLM-0035
type: finding
trust: V
status: current
statement: |
  Cross-platform irreducible residual: LS1 max_|df| = 0.185 vs paper 0.13
  (1.42×) — attributed to ANDES vs Simulink solver + PQ vs ZIP load model
  differences; not SAC-fixable
round: R21
provenance:
  - memory/rounds/R20/verdict.md
  - memory/rounds/R21/verdict.md
tags: [paper-fact, cross-platform, §V-A, §App-B]
superseded_by: []
---
```

- [ ] **Step 7: CLM-0036 through CLM-0039 — additional paper claims**

Authoring targets (one claim each):
- Multi-seed attractor 0.137 ± 0.005 across H₀×seed×ckpts (§V-A)
- Phase 9 shared-parameter SAC baseline DECORATIVE_CONFIRMED (§V-C)
- Phase 10 shared-policy warmstart rejected (§V-C)
- Local hyperparameter sensitivity ssec:hparam-sensitivity (§V-D)

Use `paper/main.tex` text as source for each `statement`.

- [ ] **Step 8: Validate all 39 claims + commit**

Run:
```powershell
python memory/tools/validate.py --fix
```
Expected: `OK: 39 claims, 0 warnings` (or some warnings, fix if any are errors).

```powershell
git add memory/claims/CLM-003[0-9].md
git commit -m "feat(memory): seed 10 paper-cited fact claims (deviations, dominance, asymmetry)"
```

---

## Phase G — Verify + Onboard

### Task 18: Render STATE.md and sanity-check against handoff v17

**Files:**
- Generate: `memory/STATE.md`

- [ ] **Step 1: Run render**

Run:
```powershell
python memory/tools/render.py
Get-Content memory/STATE.md
```
Expected: STATE.md printed, ~50 lines, includes:
- Current Headlines section listing CLM-0005, CLM-0007, CLM-0008 (and any other with `tags: [headline]` and `status: current`)
- Open Decisions section listing CLM-0009 through CLM-0014
- Latest Round = R36 or similar
- Most Recent Handoff = handoff_v17 or 2026-05-08-andes-path-closure
- Stats = ~39 claims (~22 finding / ~6 decision / ~11 correction)

- [ ] **Step 2: Sanity check against handoff_v17**

Open `memory/handoffs/2026-05-08*v17*.md` and verify the headline numbers
(0.444 / 0.439 / 0.104) appear in STATE.md current headlines.

Specifically grep:
```powershell
Select-String -Path "memory/STATE.md" -Pattern "0.444"
Select-String -Path "memory/STATE.md" -Pattern "0.439"
Select-String -Path "memory/STATE.md" -Pattern "0.104"
```
Expected: all three present in current section, NONE of 0.613 / 0.554 / 0.110 appear in current section (they should be in superseded-by chain but not surfaced).

- [ ] **Step 3: Commit STATE.md**

Run:
```powershell
git add memory/STATE.md
git commit -m "chore(memory): initial STATE.md render (39 claims, 37 rounds)"
```

### Task 19: Write README.md, CLAUDE.md, MEMORY.md

**Files:**
- Create: `README.md`, `CLAUDE.md`, `MEMORY.md`

- [ ] **Step 1: Write README.md**

Path: `README.md`
```markdown
# andes-rl-kundur

Multi-agent SAC control of virtual synchronous generator (VSG) inertia and
damping on the modified Kundur 4-bus system, reproducing Yang et al. TPWRS
2023 on the ANDES quasi-static phasor backend.

## Status

ANDES main path completed (R37, 2026-05-08). Repository is a continuing
research workbench: post-review revisions, journal resubmission, ablations,
and new baselines happen here.

## Getting started

### Reading orientation
1. `memory/STATE.md` — auto-rendered ~50 lines, current headlines + open
   decisions + latest round + latest handoff. Read this first.
2. Latest file in `memory/handoffs/` — ongoing work, what's pending.
3. `_legacy/RESEARCH_TRAIL.md` — full causal chain R01-R37 (frozen).

### Running training
ANDES requires WSL. See `scenarios/kundur/NOTES_ANDES.md`.

```bash
# In WSL
wsl -e bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  <wsl_python> scenarios/kundur/train_andes_v4.py"
```

### Memory subsystem
See `MEMORY.md`. Run `python memory/tools/validate.py` before commits.
Regenerate `memory/STATE.md` via `python memory/tools/render.py`.

## Layout
- `env/`, `scenarios/`, `agents/`, `evaluation/`, `probes/`, `scripts/` —
  ANDES code + research probes
- `paper/` — IEEE journal manuscript + figure scripts + figures
- `dissertation/` — UNNC FYP dissertation
- `memory/` — claim ledger + rounds + handoffs + auto-rendered STATE.md
- `_legacy/` — frozen source-of-truth docs from predecessor repo
- `results/` — gitignored except `whitelist/` (paper-cited ckpts/JSON)

## Citations

If you reference findings from this repo, cite claim IDs:
"… achieved 0.444 6-axis score (CLM-0005)."

Claim IDs are stable; numerical values may be superseded — check `status:
current` before quoting.

## License

TBD (private repo).
```

- [ ] **Step 2: Write CLAUDE.md**

Path: `CLAUDE.md`
```markdown
# andes-rl-kundur — AI Navigation

## Read this first
- `memory/STATE.md` — current state (auto-rendered)
- Latest `memory/handoffs/*.md` — ongoing work

## Memory subsystem (the novel part of this repo)

Three layers, four file kinds, two tools. Full design:
`docs/superpowers/specs/2026-05-15-andes-research-workbench-design.md`.

### When to write a new claim
After producing any of:
- A new numerical result you might cite (`type: finding, tags: [numerical]`)
- A correction or replacement of a prior number (`type: correction, supersedes: [...]`)
- A research-direction pivot (`type: decision`)

### When NOT to write a claim
- Throwaway debug output
- Intermediate values from a sweep (only the final selected value gets a claim)
- "Working hypotheses" you have not verified — use trust: S or trust: T,
  do not write trust: V without provenance

### Claim authoring template
```yaml
---
id: CLM-NNNN
type: finding | decision | correction
trust: V | S | T
status: current
statement: |
  <one-line citable claim>
round: RNN
provenance:
  - <path> @ <commit>
tags: [...]
superseded_by: []
---
```

### Tools
- `python memory/tools/validate.py` — check 3 rules + 2 warnings
- `python memory/tools/validate.py --fix` — auto-write back edges
- `python memory/tools/render.py` — regenerate STATE.md

Run `validate.py` before every commit. Run `render.py` after adding or
superseding claims.

## Code conventions

### ANDES = WSL only
See `scenarios/kundur/NOTES_ANDES.md`. Windows-side ANDES installs are
historical mis-installs; do not use them.

### Modifying env/andes
Read `scenarios/kundur/NOTES_ANDES.md` before changing any
`env/andes/*` or `scenarios/kundur/train_andes*.py`.

### Modifying paper_grade_axes.py
Asset 4 is paper-cited. Any change requires a new round + new claim
documenting the ranker version.

## Active research rules

- Caveman Chinese for verdict/plan files (per user preference, see
  `_legacy/CONTEXT.md` style)
- Single ANDES session at a time on Windows (16C/32T workstation), max 3
  parallel WSL python processes
- Default model env: `andes_vsg_env_v4` (paper-faithful H₀=100)
```

- [ ] **Step 3: Write MEMORY.md**

Path: `MEMORY.md`
```markdown
# MEMORY index

This file is the index for the `memory/` subsystem. See the design spec:
`docs/superpowers/specs/2026-05-15-andes-research-workbench-design.md`.

## Layout

```
memory/
├── STATE.md              # auto-rendered, read first
├── claims/CLM-NNNN.md    # atomic facts (append-only)
├── rounds/RNN/           # plan.md + verdict.md (append-only)
├── handoffs/             # cross-session handoffs (append-only)
└── tools/                # validate.py + render.py (+ tests)
```

## Schema (claim frontmatter)

Required: `id`, `type` (finding|decision|correction), `trust` (V|S|T),
`status` (current|superseded|refuted), `statement`.

Optional: `round`, `supersedes`, `provenance`, `tags`.

Tool-managed (never write): `superseded_by`.

## Validator rules (hard, fail commit)

1. `id` unique across all claims
2. `supersedes: [X]` ⇒ X exists; tool auto-writes back edge
3. `status: current` ⇒ `superseded_by` is empty

Warnings (do not fail):
- forward/back edge symmetry
- `trust: V` requires non-empty `provenance`

## Workflow

```
# Start a new round
mkdir memory/rounds/R38
$EDITOR memory/rounds/R38/plan.md

# After running experiments, write verdict + claims
$EDITOR memory/rounds/R38/verdict.md
$EDITOR memory/claims/CLM-0040.md        # new finding
$EDITOR memory/claims/CLM-0041.md        # correction supersedes CLM-0005

# Validate (fix back edges) + render STATE
python memory/tools/validate.py --fix
python memory/tools/render.py

# Commit
git add memory/
git commit -m "round: R38 — <topic>"
```

## Append-only discipline

Substantive fields (`statement`, `provenance`, `supersedes`) NEVER edited.
To correct a claim, author a new claim with `type: correction` and
`supersedes: [old_id]`. Tool flips old claim to `status: superseded`.

## Stats (regenerate after migration)

See `memory/STATE.md` for current counts.
```

- [ ] **Step 4: Commit top-level docs**

Run:
```powershell
git add README.md CLAUDE.md MEMORY.md
git commit -m "docs: add README, CLAUDE, MEMORY top-level navigation"
```

### Task 20: GitHub repo creation + first push

**Files:** none

- [ ] **Step 1: Verify clean working tree**

Run:
```powershell
git status
```
Expected: `nothing to commit, working tree clean`.

- [ ] **Step 2: Create private GitHub repo**

Run:
```powershell
gh repo create andes-rl-kundur --private --source=. --remote=origin
```
Expected: repo created at `https://github.com/<user>/andes-rl-kundur`. Confirms creation and adds remote.

- [ ] **Step 3: Push main branch**

Run:
```powershell
git push -u origin main
```
Expected: all commits pushed. May take 30-90 seconds due to paper/figures size.

- [ ] **Step 4: Verify on GitHub**

Run:
```powershell
gh repo view andes-rl-kundur --web
```
Browser opens to repo page. Confirm:
- README displays correctly
- File tree shows `memory/`, `env/`, `paper/`, `dissertation/`
- Visibility shows "Private"
- Default branch is `main`

- [ ] **Step 5: Final acceptance check (per spec §8)**

Run these checks; all must pass:

a. validator returns 0 errors:
```powershell
python memory/tools/validate.py
```
Expected: `OK: 39 claims, 0 warnings` (or some warnings, 0 errors).

b. STATE.md exists and lists post-fix headlines:
```powershell
Select-String -Path memory/STATE.md -Pattern "0.444"
Select-String -Path memory/STATE.md -Pattern "0.439"
Select-String -Path memory/STATE.md -Pattern "0.104"
```
Expected: all three matched.

c. drift chain reconstructible:
```powershell
Get-Content memory/claims/CLM-0001.md | Select-String "superseded_by"
```
Expected: `superseded_by: [CLM-0005]` (or `superseded_by:\n- CLM-0005`).

d. 30+ claims with required breakdown (~8+6+5+10+10):
```powershell
(Get-ChildItem memory/claims/*.md | Measure-Object).Count
```
Expected: >= 30, ideally 39.

e. fresh-Claude check — open a new conversation, give it only `CLAUDE.md` +
`memory/STATE.md` + the latest handoff, and ask:
- "What is the current paper headline number?" → 0.444
- "What is HAWE?" → Asset 5 / ensemble / 0.439 / 99.3% R21
- "Is the ANDES path closed?" → re-opened and currently completed

If the new conversation can answer correctly, migration is successful.

---

## Phase H — Cleanup + Handoff

### Task 21: Write migration handoff to memory/handoffs

**Files:**
- Create: `memory/handoffs/2026-05-15-migration-complete.md`

- [ ] **Step 1: Write handoff**

Path: `memory/handoffs/2026-05-15-migration-complete.md`
```markdown
# Migration Complete — andes-rl-kundur (2026-05-15)

## What was migrated

From `Multi-Agent  VSGs`:
- ANDES code: env/andes (8 files), scenarios/kundur/train_andes*.py (5),
  probes/andes_common (4 modules), agents (SAC+MA+networks),
  utils/monitor, evaluation/paper_grade_axes
- scripts/research_loop r01-r36 + eval drivers
- paper/main.tex + 21 figure scripts + ~36MB figures
- docs/paper/kd_4agent_paper_facts.md, andes_replication_status_2026-05-07_6axis.md
- 37 round folders (memory/rounds/R01-R37)
- 5-10 handoffs

From `毕业论文`:
- dissertation/main.tex + figures + refs.bib + class file
- CONTEXT.md, WRITING_STANDARD.md (now in dissertation/)
- plan/2026-05-08*v17*.md handoff

## Memory subsystem
- 39 claims (8 headline drift + 6 pivot + 5 asset + 10 anti-pattern + 10 paper-cited)
- 2 Python tools (validate.py, render.py) with pytest coverage
- STATE.md auto-rendered

## Not migrated (intentional)
- ODE backend (`env/ode/`)
- Simulink backend (`env/simulink/`, `engine/`, `slx_helpers/`,
  `scenarios/*/train_simulink.py`)
- Simulink-specific config sections in config.py
- Full results/ tree (only whitelist + manifest)

## Next round suggestions
- R38 (future): use the new ledger by adding any post-review revision as
  a new round; cite CLM-IDs in paper text rather than copying numbers
- Add a pre-commit hook running `validate.py` if violations occur
- Decide on knowledge-deepening: optional full replay of remaining R01-R37
  findings (lite migration only seeded 39 headline-level claims)

## How to continue from here
1. `cd C:\Users\27443\Desktop\andes-rl-kundur`
2. Read `memory/STATE.md`
3. Read this file
4. For new work: `mkdir memory/rounds/R38 && $EDITOR memory/rounds/R38/plan.md`
```

- [ ] **Step 2: Re-render STATE.md to pick up new handoff**

Run:
```powershell
python memory/tools/render.py
```
Expected: STATE.md "Most Recent Handoff" now references `2026-05-15-migration-complete.md`.

- [ ] **Step 3: Commit + push**

Run:
```powershell
git add memory/handoffs/2026-05-15-migration-complete.md memory/STATE.md
git commit -m "docs(memory): migration-complete handoff + re-render STATE.md"
git push
```

---

## Self-Review (checklist run after writing this plan)

**Spec coverage:**
- §0 Purpose & Scope → Task 1 (scaffold) + tasks throughout
- §1 Architecture (three layers) → Tasks 3, 4 build the tools that enforce; Tasks 10-12 populate Layer 2; Tasks 13-17 populate Layer 1; Task 18 renders Layer 3
- §2 Claim Schema → Task 2 fixtures + Tasks 13-17 author claims using this schema
- §3 File Layout → Task 1 directory creation, Tasks 5-12 populate
- §4.1 Asset migration table → Tasks 5, 6, 7, 8 cover each row
- §4.2 results/ strategy → Task 9
- §4.3 Knowledge sedimentation → Tasks 13-17 (8+6+5+10+10 = 39 claims)
- §4.4 GitHub repo creation → Task 20
- §4.5 Execution order → Tasks 1-21 implement this
- §5 Non-functional (maintainability, AI ergonomics, paper writing) → satisfied structurally; not a task in itself
- §6 Excluded items → respected (no KG/DB/UI; no claim auto-extraction; lite only)
- §7 Open items → Item 1 (pre-commit hook) noted in Task 21 handoff; others deferred per spec
- §8 Success criteria → Task 20 Step 5 lists them as acceptance check

**Placeholder scan:**
- CLM-0006 has "0.42 (placeholder)" with explicit Note to fill from JSON. This is an instructed-action placeholder, not a plan failure. Acceptable.
- Task 6 Step 2 ("Manual triage") is intentionally judgement-based; engineer decides which scripts are one-shots based on file content review.
- Task 16 Step 3-10 lists 8 remaining anti-patterns by topic; engineer copies the row from `_legacy/CONTEXT.md` §2 and instantiates claim using the explicit CLM-0020/0021 templates.
- Task 17 Step 7 lists 4 paper claims by topic with `paper/main.tex` as source. Same template re-use applies.
- No "TBD" / "TODO" / "implement later" found.

**Type consistency:**
- Claim schema fields used consistently across all claim creations (id/type/trust/status/statement/round/provenance/supersedes/tags/superseded_by)
- Function names: `load_claims`, `validate_rules`, `fix_back_edges`, `render_state`, `_load_claims`, `_latest_round`, `_latest_handoff`, `_format_claim_line`, `_rewrite_frontmatter` — used identically wherever referenced
- Path conventions: `memory/claims/`, `memory/rounds/RNN/`, `memory/handoffs/`, `memory/tools/`, `results/whitelist/`, `_legacy/` — consistent across all tasks

No issues found. Plan ready for execution.

---

## Execution

**Plan complete and saved to `docs/superpowers/plans/2026-05-15-andes-rl-kundur-migration.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because tasks 5-12 are mechanical file copying, ideal for parallel/automated execution, while tasks 13-17 (claim authoring) benefit from review checkpoints.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
