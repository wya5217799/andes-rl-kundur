# Memory System — Note Entity + Legacy Ingest — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the R39 memory subsystem with a new `Note` entity that indexes all out-of-schema archives (`handoffs/`, `docs/adr/`, `docs/eng-notes/`, `_legacy/`), so future AI sessions can discover prior research without manual file archaeology. Spec: [`docs/superpowers/specs/2026-05-19-memory-system-notes-ingest-design.md`](../specs/2026-05-19-memory-system-notes-ingest-design.md).

**Architecture:** Notes live at `memory/notes/NOTE-NNNN.md`, validated by extending `memory/tools/validate.py` with 5 hard rules + 2 cross-entity warnings; surfaced in `memory/STATE.md` via a new `## Archive Index` section emitted by `memory/tools/render.py`. Original handoff / ADR / legacy files stay byte-identical — Notes are pure index over them. Two new CLI tools (`new_note.py`, `note_query.py`) mirror the existing `reserve_round.py` / `query.py` conventions.

**Tech Stack:** Python 3.10+, PyYAML, pytest. Existing project layout under `memory/tools/`.

**Repository conventions (read before starting):**
- All Python style is `black` + `ruff` + PEP 8 + full type hints (per `~/.claude/rules/python/coding-style.md`).
- Tests under `memory/tools/tests/`, use `sys.path.insert(0, str(Path(__file__).parent.parent))` to import siblings (see `test_validate.py`).
- Fixtures under `memory/tools/tests/fixtures/`; mirror `claims/` style when adding `notes/` fixtures.
- Per project CLAUDE.md: commits only on explicit user authorization. This plan's commit steps assume that authorization has been granted; if not, batch all commits at the end.

---

## File Structure

**New files:**
- `memory/notes/_TEMPLATE.md` — Note template (mirrors `claims/_TEMPLATE.md` style)
- `memory/notes/NOTE-0001.md` .. `NOTE-NNNN.md` — actual notes created during Waves 0-4
- `memory/tools/new_note.py` — reserve next id + scaffold stub
- `memory/tools/note_query.py` — filter / search CLI
- `memory/tools/tests/test_new_note.py`
- `memory/tools/tests/test_note_query.py`
- `memory/tools/tests/fixtures/notes/NOTE-0001.md` .. `NOTE-0003.md` — test fixtures
- `memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md` — a stub source file fixture for path-existence checks
- `memory/tools/tests/fixtures/notes_adr_src/0001-demo-adr.md` — stub ADR fixture
- `docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md` — this plan

**Modified files:**
- `memory/tools/validate.py` — add `load_notes()`, `validate_note_rules()`, `warn_cross_entity_handoff_coverage()`, `warn_cross_entity_adr_coverage()`; wire into `main()`
- `memory/tools/render.py` — add `_load_notes()`, `_archive_index_rows()`, emit `## Archive Index` section between Stats and 历史简报
- `memory/tools/tests/test_validate.py` — add N1-N5 + X1-X2 tests
- `memory/tools/tests/test_render.py` — add archive-index section tests
- `memory/STATE.md` — auto-regenerates (do not hand-edit)
- `memory/rounds/_TEMPLATE_VERDICT.md` — no change (Notes are independent of round verdicts)
- `CLAUDE.md` — add Note row to entity table + add "Read first" hint
- `memory/handoffs/README.md` — append note that handoffs are now indexed by `NOTE-*` entities (but still scratchpad-first)
- Hygiene fixes (Phase B): `memory/rounds/R45/verdict.md`, `memory/rounds/R90/verdict.md`, `memory/rounds/R91/verdict.md` (close/abandon decisions case-by-case)

**No changes to:**
- `memory/claims/`, `memory/questions/`, `memory/rounds/` schemas
- Existing R39 validate rules (claim / question / verdict)
- `query.py`, `reserve_round.py`

---

## Phase A — Schema and Tooling (TDD, all code)

### Task 1: Note template + directory bootstrap

**Files:**
- Create: `memory/notes/_TEMPLATE.md`
- Create: `memory/notes/.gitkeep`

- [ ] **Step 1: Verify directory parent exists, create directory**

Run: `ls memory/`
Expected: shows `claims/`, `questions/`, `rounds/`, `handoffs/`, `tools/`, `STATE.md`, `glossary.yml`

Run: `mkdir memory/notes && touch memory/notes/.gitkeep`

- [ ] **Step 2: Write the template file**

Create `memory/notes/_TEMPLATE.md` with content:

```markdown
---
id: NOTE-NNNN
source: handoff          # handoff | eng-note | adr-rationale | legacy | session-report
source_path: memory/handoffs/<filename>.md   # repo-relative; must exist on disk
date: YYYY-MM-DD         # ORIGINAL creation date of source (not ingest date)
related_rounds: [R<N>, R<N>]
topics: [<top-level>, <free-sub-tag>, <free-sub-tag>]
                         # Top-level (closed): env, training-infra, evaluation,
                         #                     agents, scenarios, paper,
                         #                     memory-system, pipeline
extracted_claims: []     # CLM-NNNN ids; empty initially, filled lazily when a
                         # round promotes a Key Fact into an atomic claim
status: ingested         # ingested | partially-extracted | fully-extracted
---

## Summary
<3-5 sentences. An AI scanning STATE.md's Archive Index should be able to
decide from this paragraph alone whether to open source_path.>

## Key facts (claim candidates)
- <Bullet 1 — if later promoted to claim, append `→ CLM-NNNN`>
- <Bullet 2>

## Open threads
- <Things the source flagged as TODO/unknown but did not become a Q-NNNN>
```

- [ ] **Step 3: Commit**

```bash
git add memory/notes/_TEMPLATE.md memory/notes/.gitkeep
git commit -m "feat(memory): add Note entity template + directory"
```

---

### Task 2: `validate.py` — load_notes + 5 hard rules (N1-N5)

**Files:**
- Modify: `memory/tools/validate.py` — add module-level constants, `load_notes()`, `validate_note_rules()`, wire into `main()`
- Create: `memory/tools/tests/fixtures/notes/NOTE-0001.md` (valid)
- Create: `memory/tools/tests/fixtures/notes/NOTE-0002.md` (valid, multi-topic)
- Create: `memory/tools/tests/fixtures/notes/NOTE-0003.md` (valid, partially-extracted)
- Create: `memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md` — stub source (1 line: `placeholder`)
- Create: `memory/tools/tests/fixtures/notes_adr_src/0001-demo-adr.md` — stub source (1 line: `placeholder`)
- Modify: `memory/tools/tests/test_validate.py` — add N1-N5 tests

- [ ] **Step 1: Create the source-file fixtures**

```bash
mkdir -p memory/tools/tests/fixtures/notes
mkdir -p memory/tools/tests/fixtures/notes_handoff_src
mkdir -p memory/tools/tests/fixtures/notes_adr_src
```

Create `memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md`:
```
placeholder
```

Create `memory/tools/tests/fixtures/notes_adr_src/0001-demo-adr.md`:
```
placeholder
```

- [ ] **Step 2: Create three valid fixture notes**

Create `memory/tools/tests/fixtures/notes/NOTE-0001.md`:

```markdown
---
id: NOTE-0001
source: handoff
source_path: memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md
date: 2026-05-17
related_rounds: [R58]
topics: [training-infra, hyper-sweep]
extracted_claims: []
status: ingested
---

## Summary
Demo handoff fixture. Used to exercise the validator's source-path-exists check.

## Key facts (claim candidates)
- Placeholder fact.

## Open threads
- Placeholder open thread.
```

Create `memory/tools/tests/fixtures/notes/NOTE-0002.md`:

```markdown
---
id: NOTE-0002
source: adr-rationale
source_path: memory/tools/tests/fixtures/notes_adr_src/0001-demo-adr.md
date: 2026-05-16
related_rounds: [R37]
topics: [pipeline, src-layout]
extracted_claims: []
status: ingested
---

## Summary
Demo ADR-rationale fixture. Exercises multi-topic and adr-rationale source type.

## Key facts (claim candidates)
- Placeholder fact.

## Open threads
- Placeholder thread.
```

Create `memory/tools/tests/fixtures/notes/NOTE-0003.md`:

```markdown
---
id: NOTE-0003
source: handoff
source_path: memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md
date: 2026-05-17
related_rounds: [R58, R59]
topics: [evaluation]
extracted_claims: [CLM-0001]
status: partially-extracted
---

## Summary
Demo partially-extracted note pointing at CLM-0001 (which exists in the claims fixture).

## Key facts (claim candidates)
- Placeholder fact → CLM-0001

## Open threads
- (none)
```

- [ ] **Step 3: Write failing tests for N1-N5 in `test_validate.py`**

Append to `memory/tools/tests/test_validate.py`:

```python
# ---------- Note entity rules (N1-N5) ----------
NOTE_FIXTURES = Path(__file__).parent / "fixtures" / "notes"
REPO_ROOT_FOR_TESTS = Path(__file__).parent.parent.parent.parent  # andes-rl-kundur/


def test_load_notes_returns_dict_of_id_to_frontmatter():
    from validate import load_notes  # noqa: E402
    notes = load_notes(NOTE_FIXTURES)
    assert set(notes.keys()) == {"NOTE-0001", "NOTE-0002", "NOTE-0003"}
    assert notes["NOTE-0001"]["source"] == "handoff"
    assert notes["NOTE-0002"]["topics"][0] == "pipeline"


def test_rule_N1_filename_must_match_id():
    from validate import validate_note_rules  # noqa: E402
    # Build a note dict whose _path filename disagrees with the id.
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["training-infra"], "extracted_claims": [],
            "_path": Path("NOTE-0099.md"),
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("filename" in e.lower() and "NOTE-0001" in e for e in errors)


def test_rule_N2_source_in_whitelist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "blog",  # invalid
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["training-infra"], "extracted_claims": [],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("source" in e and "blog" in e for e in errors)


def test_rule_N3_source_path_must_exist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/this/file/does/not/exist.md",
            "topics": ["training-infra"], "extracted_claims": [],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("source_path" in e and "exist" in e.lower() for e in errors)


def test_rule_N4_extracted_claims_must_exist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["training-infra"], "extracted_claims": ["CLM-9999"],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={"CLM-0001": {}}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("CLM-9999" in e and "extracted" in e.lower() for e in errors)


def test_rule_N5_topic_top_level_in_whitelist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["not-a-real-bucket", "lstm"],   # top-level invalid
            "extracted_claims": [],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("topics[0]" in e or "top-level" in e for e in errors)


def test_clean_note_fixtures_have_no_errors():
    from validate import load_notes, validate_note_rules  # noqa: E402
    notes = load_notes(NOTE_FIXTURES)
    # Provide claims dict with CLM-0001 so NOTE-0003's extracted_claims passes.
    fake_claims = {"CLM-0001": {}}
    errors = validate_note_rules(notes, claims=fake_claims, repo_root=REPO_ROOT_FOR_TESTS)
    assert errors == [], f"unexpected errors on clean fixtures: {errors}"
```

- [ ] **Step 4: Run tests to verify they fail (load_notes / validate_note_rules don't exist yet)**

Run: `cd memory/tools && python -m pytest tests/test_validate.py -v -k "note"`
Expected: ImportError / AttributeError on `load_notes` and `validate_note_rules` — all new tests fail.

- [ ] **Step 5: Implement `load_notes` and `validate_note_rules` in `validate.py`**

Add to `memory/tools/validate.py` (after `load_questions`, before `validate_question_rules`):

```python
# ---------- Note entity (R-this-round addition) ----------

NOTE_SOURCE_ENUM = {
    "handoff",
    "eng-note",
    "adr-rationale",
    "legacy",
    "session-report",
}

NOTE_TOPIC_TOP_LEVEL = {
    "env",
    "training-infra",
    "evaluation",
    "agents",
    "scenarios",
    "paper",
    "memory-system",
    "pipeline",
}


def load_notes(notes_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every NOTE-*.md frontmatter into a dict keyed by id.

    Returns empty dict if ``notes_dir`` does not exist (Note entity is
    optional — a repo without notes is valid).
    """
    return _load_entities(
        notes_dir,
        glob_pattern="NOTE-*.md",
        require_dir=False,
    )


def validate_note_rules(
    notes: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
    repo_root: Path,
) -> list[str]:
    """Five hard rules on Note entities. Returns list of error strings.

    N1: filename matches frontmatter ``id``
    N2: ``source`` ∈ NOTE_SOURCE_ENUM
    N3: ``source_path`` resolves to an existing file under ``repo_root``
    N4: every id in ``extracted_claims`` exists in ``claims``
    N5: ``topics[0]`` (top-level) ∈ NOTE_TOPIC_TOP_LEVEL
    """
    errors: list[str] = []
    for note in notes.values():
        nid = note["id"]

        # N1: filename ↔ id
        path: Path | None = note.get("_path")
        if path is not None and path.stem != nid:
            errors.append(
                f"{nid}: filename {path.name!r} does not match id"
            )

        # N2: source enum
        source = note.get("source")
        if source not in NOTE_SOURCE_ENUM:
            errors.append(
                f"{nid}: source {source!r} not in "
                f"{sorted(NOTE_SOURCE_ENUM)}"
            )

        # N3: source_path exists on disk
        src_path_raw = note.get("source_path")
        if not isinstance(src_path_raw, str) or not src_path_raw:
            errors.append(f"{nid}: source_path missing or empty")
        else:
            resolved = (repo_root / src_path_raw).resolve()
            if not resolved.exists():
                errors.append(
                    f"{nid}: source_path does not exist on disk: {src_path_raw}"
                )

        # N4: extracted_claims must reference existing claim ids
        for clm_id in note.get("extracted_claims", []) or []:
            if clm_id not in claims:
                errors.append(
                    f"{nid}: extracted_claims references {clm_id} which is not a known claim"
                )

        # N5: topics[0] in top-level whitelist
        topics = note.get("topics") or []
        if not topics:
            errors.append(f"{nid}: topics list is empty (need at least top-level)")
        else:
            top = topics[0]
            if top not in NOTE_TOPIC_TOP_LEVEL:
                errors.append(
                    f"{nid}: topics[0]={top!r} not a valid top-level "
                    f"(allowed: {sorted(NOTE_TOPIC_TOP_LEVEL)})"
                )

    return errors
```

Wire into `main()` — find the block that loads questions and runs `validate_question_rules`, add right after:

```python
    notes_dir = base / "notes"
    notes = load_notes(notes_dir)
    repo_root = Path(__file__).resolve().parents[2]
    n_errors = validate_note_rules(notes, claims, repo_root=repo_root)
    errors.extend(n_errors)
```

Update the final `print` line to include notes count:

```python
    print(
        f"OK: {len(claims)} claims, {len(questions)} questions, "
        f"{len(notes)} notes, {len(warnings)} warnings"
    )
```

Also add an argparse argument near the existing `--claims-dir` arguments:

```python
    parser.add_argument("--notes-dir", type=Path, default=base / "notes",
                        help="path to memory/notes/")
```

And replace the `notes_dir = base / "notes"` line with `notes_dir = args.notes_dir`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd memory/tools && python -m pytest tests/test_validate.py -v -k "note"`
Expected: all 7 new note tests pass; pre-existing tests still pass.

Run: `cd memory/tools && python -m pytest tests/ -v`
Expected: full suite green.

- [ ] **Step 7: Run validate on real memory tree (should succeed with 0 notes)**

Run: `python memory/tools/validate.py`
Expected: `OK: 161 claims, 20 questions, 0 notes, <warning_count> warnings` (exact warning count depends on current tree state)

- [ ] **Step 8: Commit**

```bash
git add memory/tools/validate.py memory/tools/tests/test_validate.py memory/tools/tests/fixtures/notes/ memory/tools/tests/fixtures/notes_handoff_src/ memory/tools/tests/fixtures/notes_adr_src/
git commit -m "feat(memory): add Note entity validation (N1-N5 hard rules)"
```

---

### Task 3: `validate.py` — cross-entity warnings X1 + X2

**Files:**
- Modify: `memory/tools/validate.py` — add `warn_cross_entity_handoff_coverage()`, `warn_cross_entity_adr_coverage()`, wire into `main()`
- Modify: `memory/tools/tests/test_validate.py` — add X1, X2 tests

- [ ] **Step 1: Write failing tests**

Append to `memory/tools/tests/test_validate.py`:

```python
def test_warning_X1_adr_without_note_warns(tmp_path):
    """X1: every docs/adr/*.md should have at least one note pointing to it."""
    from validate import warn_cross_entity_adr_coverage  # noqa: E402
    # ADR dir has 0001-foo.md, but no note references it.
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "0001-foo.md").write_text("# ADR placeholder\n")
    notes: dict[str, dict[str, Any]] = {}
    warnings = warn_cross_entity_adr_coverage(notes, adr_dir=adr_dir)
    assert any("0001-foo.md" in w for w in warnings)


def test_warning_X1_adr_with_note_silent(tmp_path):
    from validate import warn_cross_entity_adr_coverage  # noqa: E402
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "0001-foo.md").write_text("# ADR\n")
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "adr-rationale",
            "source_path": str((adr_dir / "0001-foo.md").as_posix()),
        }
    }
    warnings = warn_cross_entity_adr_coverage(notes, adr_dir=adr_dir)
    assert warnings == []


def test_warning_X2_handoff_without_note_warns(tmp_path):
    from validate import warn_cross_entity_handoff_coverage  # noqa: E402
    handoffs_dir = tmp_path / "handoffs"
    handoffs_dir.mkdir()
    (handoffs_dir / "2026-05-17_demo.md").write_text("handoff body\n")
    (handoffs_dir / "README.md").write_text("intentionally excluded\n")
    (handoffs_dir / "_archive").mkdir()
    (handoffs_dir / "_archive" / "old.md").write_text("excluded\n")
    warnings = warn_cross_entity_handoff_coverage({}, handoffs_dir=handoffs_dir)
    # README.md and _archive/ excluded; only 2026-05-17_demo.md should warn.
    assert any("2026-05-17_demo.md" in w for w in warnings)
    assert not any("README.md" in w for w in warnings)
    assert not any("_archive" in w for w in warnings)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd memory/tools && python -m pytest tests/test_validate.py -v -k "warning_X"`
Expected: ImportError on `warn_cross_entity_adr_coverage` / `warn_cross_entity_handoff_coverage`.

- [ ] **Step 3: Implement the two warning functions**

Add to `memory/tools/validate.py` (after `validate_note_rules`):

```python
def _notes_referencing(notes: dict[str, dict[str, Any]], abs_path: Path) -> list[str]:
    """Return note ids whose source_path resolves to ``abs_path``.

    Both sides are resolved to absolute paths so that the comparison is
    insensitive to ``./`` prefixes and casing differences on Windows.
    """
    hits: list[str] = []
    target = abs_path.resolve()
    for note in notes.values():
        sp = note.get("source_path")
        if not isinstance(sp, str):
            continue
        # source_path may be repo-relative; compare against the literal too.
        if Path(sp).resolve() == target:
            hits.append(note["id"])
            continue
        # also allow string equality (cheap fallback for the unit-test case
        # where notes dict has POSIX path strings).
        if Path(sp).as_posix() == abs_path.as_posix():
            hits.append(note["id"])
    return hits


def warn_cross_entity_adr_coverage(
    notes: dict[str, dict[str, Any]],
    *,
    adr_dir: Path,
) -> list[str]:
    """X1: every ``docs/adr/*.md`` should have at least one note with
    ``source: adr-rationale`` pointing at it. Soft warning."""
    if not adr_dir.exists():
        return []
    warnings: list[str] = []
    for adr in sorted(adr_dir.glob("*.md")):
        if not _notes_referencing(notes, adr):
            warnings.append(
                f"ADR {adr.name} has no Note pointing to it "
                f"(X1: consider adding one with source: adr-rationale)"
            )
    return warnings


def warn_cross_entity_handoff_coverage(
    notes: dict[str, dict[str, Any]],
    *,
    handoffs_dir: Path,
) -> list[str]:
    """X2: every ``memory/handoffs/*.md`` (excluding README.md and
    _archive/) should have at least one note pointing at it. Soft warning."""
    if not handoffs_dir.exists():
        return []
    warnings: list[str] = []
    for path in sorted(handoffs_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        if not _notes_referencing(notes, path):
            warnings.append(
                f"handoff {path.name} has no Note pointing to it "
                f"(X2: consider adding one with source: handoff)"
            )
    return warnings
```

Wire into `main()` (right after the `validate_note_rules` call added in Task 2):

```python
    adr_dir = repo_root / "docs" / "adr"
    handoffs_dir = base / "handoffs"
    warnings.extend(warn_cross_entity_adr_coverage(notes, adr_dir=adr_dir))
    warnings.extend(warn_cross_entity_handoff_coverage(notes, handoffs_dir=handoffs_dir))
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd memory/tools && python -m pytest tests/test_validate.py -v -k "warning_X"`
Expected: 3 new tests pass.

Run: `cd memory/tools && python -m pytest tests/ -v`
Expected: full suite green.

- [ ] **Step 5: Run validate against real tree**

Run: `python memory/tools/validate.py`
Expected: completes with errors=0; will show **many new WARN lines** — one per ADR (5) and one per handoff (9). This is expected — Wave 0 + Wave 1 will eliminate them.

- [ ] **Step 6: Commit**

```bash
git add memory/tools/validate.py memory/tools/tests/test_validate.py
git commit -m "feat(memory): add Note cross-entity coverage warnings (X1, X2)"
```

---

### Task 4: `new_note.py` — atomic id reservation + stub scaffold

**Files:**
- Create: `memory/tools/new_note.py`
- Create: `memory/tools/tests/test_new_note.py`

- [ ] **Step 1: Write failing tests**

Create `memory/tools/tests/test_new_note.py`:

```python
"""Tests for memory/tools/new_note.py — atomic Note id reservation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from new_note import reserve_next_note_id, scaffold_note  # noqa: E402


def test_reserve_next_note_id_empty_dir(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    assert reserve_next_note_id(notes_dir) == 1


def test_reserve_next_note_id_skips_template(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "_TEMPLATE.md").write_text("template")
    assert reserve_next_note_id(notes_dir) == 1


def test_reserve_next_note_id_existing(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "NOTE-0001.md").write_text("placeholder")
    (notes_dir / "NOTE-0003.md").write_text("placeholder")  # gap is fine
    assert reserve_next_note_id(notes_dir) == 4


def test_scaffold_note_writes_valid_frontmatter(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    path = scaffold_note(
        notes_dir,
        note_id=7,
        source="handoff",
        source_path="memory/handoffs/example.md",
        date="2026-05-17",
        topics=["training-infra", "lstm"],
        related_rounds=["R58"],
        summary="One line summary.",
    )
    assert path.name == "NOTE-0007.md"
    text = path.read_text(encoding="utf-8")
    assert "id: NOTE-0007" in text
    assert "source: handoff" in text
    assert "training-infra" in text
    assert "One line summary." in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd memory/tools && python -m pytest tests/test_new_note.py -v`
Expected: ModuleNotFoundError on `new_note`.

- [ ] **Step 3: Implement `new_note.py`**

Create `memory/tools/new_note.py`:

```python
"""Reserve next NOTE-NNNN id and scaffold a stub Note file.

Mirrors the pattern of reserve_round.py — atomic-ish: we read the highest
existing NOTE-NNNN, return max+1, and the caller writes a file at that id.
Concurrent races between sessions are mitigated by `scaffold_note` opening
the target file with ``x`` mode (fails if it already exists), prompting
the caller to retry with a higher id.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NOTE_ID_RE = re.compile(r"^NOTE-(\d+)\.md$")


def reserve_next_note_id(notes_dir: Path) -> int:
    """Return ``max(existing NOTE-NNNN ids) + 1``, or 1 if none exist.

    Skips ``_TEMPLATE.md`` and any non-NOTE-*.md files.
    """
    max_id = 0
    if notes_dir.exists():
        for entry in notes_dir.iterdir():
            if not entry.is_file():
                continue
            m = NOTE_ID_RE.match(entry.name)
            if not m:
                continue
            max_id = max(max_id, int(m.group(1)))
    return max_id + 1


def scaffold_note(
    notes_dir: Path,
    *,
    note_id: int,
    source: str,
    source_path: str,
    date: str,
    topics: list[str],
    related_rounds: list[str],
    summary: str = "",
) -> Path:
    """Write a NOTE-NNNN.md stub with the supplied frontmatter values.

    Raises FileExistsError if the target already exists (concurrent-write guard).
    """
    note_filename = f"NOTE-{note_id:04d}.md"
    target = notes_dir / note_filename
    related_rounds_yaml = "[" + ", ".join(related_rounds) + "]"
    topics_yaml = "[" + ", ".join(topics) + "]"
    body = f"""---
id: NOTE-{note_id:04d}
source: {source}
source_path: {source_path}
date: {date}
related_rounds: {related_rounds_yaml}
topics: {topics_yaml}
extracted_claims: []
status: ingested
---

## Summary
{summary or "<3-5 sentences>"}

## Key facts (claim candidates)
- <bullet>

## Open threads
- <bullet>
"""
    with target.open("x", encoding="utf-8") as f:
        f.write(body)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold the next NOTE-NNNN.md")
    base = Path(__file__).parent.parent
    parser.add_argument("--notes-dir", type=Path, default=base / "notes")
    parser.add_argument("--source", required=True,
                        choices=["handoff", "eng-note", "adr-rationale", "legacy", "session-report"])
    parser.add_argument("--source-path", required=True,
                        help="repo-relative path to the original file")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD of original source")
    parser.add_argument("--topic", action="append", required=True,
                        help="topic (first one is top-level); repeat for sub-tags")
    parser.add_argument("--round", action="append", default=[], dest="rounds",
                        help="related round (e.g. R58); repeat as needed")
    parser.add_argument("--summary", default="", help="optional one-line summary")
    args = parser.parse_args()

    note_id = reserve_next_note_id(args.notes_dir)
    path = scaffold_note(
        args.notes_dir,
        note_id=note_id,
        source=args.source,
        source_path=args.source_path,
        date=args.date,
        topics=args.topic,
        related_rounds=args.rounds,
        summary=args.summary,
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd memory/tools && python -m pytest tests/test_new_note.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Smoke-test the CLI**

Run:
```bash
python memory/tools/new_note.py \
  --source handoff \
  --source-path memory/handoffs/2026-05-15-migration-complete.md \
  --date 2026-05-15 \
  --topic pipeline --topic src-layout \
  --round R37 \
  --summary "Smoke test"
```
Expected: prints `memory/notes/NOTE-0001.md` and that file exists.

**IMPORTANT — clean up the smoke-test file before commit:**

```bash
rm memory/notes/NOTE-0001.md
```

(Wave 0 will create NOTE-0001 properly with full content.)

- [ ] **Step 6: Commit**

```bash
git add memory/tools/new_note.py memory/tools/tests/test_new_note.py
git commit -m "feat(memory): add new_note.py for NOTE id reservation + scaffolding"
```

---

### Task 5: `note_query.py` — filter and search

**Files:**
- Create: `memory/tools/note_query.py`
- Create: `memory/tools/tests/test_note_query.py`

- [ ] **Step 1: Write failing tests**

Create `memory/tools/tests/test_note_query.py`:

```python
"""Tests for note_query.py — filter / search over Note frontmatter."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from note_query import filter_notes, format_row  # noqa: E402

NOTE_FIXTURES = Path(__file__).parent / "fixtures" / "notes"


def test_filter_by_topic_top_level():
    hits = filter_notes(NOTE_FIXTURES, topic="training-infra")
    ids = [n["id"] for n in hits]
    assert "NOTE-0001" in ids
    assert "NOTE-0002" not in ids


def test_filter_by_sub_tag():
    hits = filter_notes(NOTE_FIXTURES, tag="src-layout")
    ids = [n["id"] for n in hits]
    assert "NOTE-0002" in ids


def test_filter_by_source():
    hits = filter_notes(NOTE_FIXTURES, source="adr-rationale")
    assert [n["id"] for n in hits] == ["NOTE-0002"]


def test_filter_by_round():
    hits = filter_notes(NOTE_FIXTURES, round_id="R58")
    ids = sorted(n["id"] for n in hits)
    assert ids == ["NOTE-0001", "NOTE-0003"]


def test_filter_by_grep_summary():
    """grep should match against summary text inside the body, not just frontmatter."""
    hits = filter_notes(NOTE_FIXTURES, grep="ADR-rationale fixture")
    assert [n["id"] for n in hits] == ["NOTE-0002"]


def test_format_row_one_line():
    notes = filter_notes(NOTE_FIXTURES, topic="training-infra")
    assert notes  # guard
    row = format_row(notes[0])
    assert notes[0]["id"] in row
    # 1-line row, length-capped
    assert "\n" not in row


def test_filter_no_args_returns_all():
    hits = filter_notes(NOTE_FIXTURES)
    assert len(hits) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd memory/tools && python -m pytest tests/test_note_query.py -v`
Expected: ModuleNotFoundError on `note_query`.

- [ ] **Step 3: Implement `note_query.py`**

Create `memory/tools/note_query.py`:

```python
"""Filter and search notes by topic / source / round / free-text grep.

CLI:
    python memory/tools/note_query.py --topic training-infra
    python memory/tools/note_query.py --tag lstm --round R58
    python memory/tools/note_query.py --grep "hyperparameter sweep"
    python memory/tools/note_query.py --source-path memory/handoffs/foo.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ROW_MAX_LEN = 200


def _load_note(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    meta = yaml.safe_load(match.group(1)) or {}
    meta["_path"] = path
    meta["_body"] = text[match.end():]
    return meta


def filter_notes(
    notes_dir: Path,
    *,
    topic: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    round_id: str | None = None,
    source_path: str | None = None,
    grep: str | None = None,
) -> list[dict[str, Any]]:
    """Return notes matching all supplied filters.

    Filters are AND-combined. ``topic`` matches only against ``topics[0]``
    (top-level); ``tag`` matches any element of ``topics`` (top or sub).
    ``grep`` is a substring search across both frontmatter (yaml dump) and
    body text. ``round_id`` matches any element of ``related_rounds``.
    """
    if not notes_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(notes_dir.glob("NOTE-*.md")):
        note = _load_note(path)
        if note is None:
            continue
        if topic is not None:
            topics = note.get("topics") or []
            if not topics or topics[0] != topic:
                continue
        if tag is not None:
            if tag not in (note.get("topics") or []):
                continue
        if source is not None and note.get("source") != source:
            continue
        if round_id is not None:
            if round_id not in (note.get("related_rounds") or []):
                continue
        if source_path is not None and note.get("source_path") != source_path:
            continue
        if grep is not None:
            haystack = (
                yaml.safe_dump(
                    {k: v for k, v in note.items() if not k.startswith("_")},
                    allow_unicode=True,
                )
                + (note.get("_body") or "")
            )
            if grep.lower() not in haystack.lower():
                continue
        out.append(note)
    return out


def format_row(note: dict[str, Any]) -> str:
    """One-line summary suitable for CLI output."""
    nid = note.get("id", "?")
    source = note.get("source", "?")
    topics = note.get("topics") or []
    topic = topics[0] if topics else "?"
    # Pull first non-blank line of body Summary section
    body = note.get("_body") or ""
    summary = ""
    in_summary = False
    for line in body.splitlines():
        if line.strip().startswith("## Summary"):
            in_summary = True
            continue
        if in_summary:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("##"):
                break
            summary = stripped
            break
    row = f"{nid} [{topic}/{source}] {summary}"
    if len(row) > ROW_MAX_LEN:
        row = row[: ROW_MAX_LEN - 1] + "…"
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter / search memory/notes/")
    base = Path(__file__).parent.parent
    parser.add_argument("--notes-dir", type=Path, default=base / "notes")
    parser.add_argument("--topic", help="filter by top-level topic")
    parser.add_argument("--tag", help="filter by any (top or sub) tag")
    parser.add_argument("--source",
                        choices=["handoff", "eng-note", "adr-rationale", "legacy", "session-report"])
    parser.add_argument("--round", dest="round_id", help="filter by related round (e.g. R58)")
    parser.add_argument("--source-path", help="exact source_path match (reverse lookup)")
    parser.add_argument("--grep", help="substring search in body + frontmatter")
    args = parser.parse_args()

    hits = filter_notes(
        args.notes_dir,
        topic=args.topic,
        tag=args.tag,
        source=args.source,
        round_id=args.round_id,
        source_path=args.source_path,
        grep=args.grep,
    )
    for note in hits:
        print(format_row(note))
    print(f"# {len(hits)} note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd memory/tools && python -m pytest tests/test_note_query.py -v`
Expected: 7 tests pass.

- [ ] **Step 5: Smoke-test CLI**

Run: `python memory/tools/note_query.py --notes-dir memory/tools/tests/fixtures/notes --topic training-infra`
Expected:
```
NOTE-0001 [training-infra/handoff] Demo handoff fixture. Used to exercise...
# 1 note(s)
```

- [ ] **Step 6: Commit**

```bash
git add memory/tools/note_query.py memory/tools/tests/test_note_query.py
git commit -m "feat(memory): add note_query.py for filter+grep search"
```

---

### Task 6: `render.py` — `## Archive Index` section

**Files:**
- Modify: `memory/tools/render.py` — add `_load_notes()`, `_archive_index_rows()`, emit new section
- Modify: `memory/tools/tests/test_render.py` — add archive-index tests

- [ ] **Step 1: Write failing tests**

Append to `memory/tools/tests/test_render.py`:

```python
def test_archive_index_section_emitted_when_notes_exist(tmp_path):
    """When notes/ dir has at least 1 note, STATE.md must contain
    `## Archive Index` section."""
    from render import render_state  # noqa: E402

    # Build a minimal in-tmp memory tree
    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()

    (notes_dir / "NOTE-0001.md").write_text("""---
id: NOTE-0001
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: [R58]
topics: [training-infra, lstm]
extracted_claims: []
status: ingested
---

## Summary
Demo note for the archive-index test.

## Key facts (claim candidates)
- foo

## Open threads
- bar
""", encoding="utf-8")

    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    assert "## Archive Index" in text
    assert "[training-infra]" in text
    assert "NOTE-0001" in text


def test_archive_index_section_omitted_when_no_notes(tmp_path):
    from render import render_state  # noqa: E402
    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    assert "## Archive Index" not in text


def test_archive_index_shows_extraction_count(tmp_path):
    from render import render_state  # noqa: E402
    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()

    # Two notes in training-infra; one has extracted_claims, one doesn't.
    (notes_dir / "NOTE-0001.md").write_text("""---
id: NOTE-0001
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: []
topics: [training-infra]
extracted_claims: [CLM-0001]
status: partially-extracted
---

## Summary
n1

## Key facts (claim candidates)
- a

## Open threads
- b
""", encoding="utf-8")
    (notes_dir / "NOTE-0002.md").write_text("""---
id: NOTE-0002
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: []
topics: [training-infra]
extracted_claims: []
status: ingested
---

## Summary
n2

## Key facts (claim candidates)
- a

## Open threads
- b
""", encoding="utf-8")

    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    # Per spec §9 decision 1: bucket line shows "X notes · Y claims extracted"
    assert "2 notes" in text
    assert "1 claim" in text  # singular OK; bucket line is "N notes · M claim(s) extracted"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd memory/tools && python -m pytest tests/test_render.py -v -k "archive_index"`
Expected: TypeError on `notes_dir=` kwarg, or missing section.

- [ ] **Step 3: Implement archive-index emitter in `render.py`**

Add to `memory/tools/render.py` near the section formatters (after `_format_closed_q_line`):

```python
# ---------- Archive Index (Note entity, this-round addition) ----------

# Top-level topic order for the Archive Index section. Buckets are emitted
# in this order regardless of insertion sequence; buckets with zero notes
# are skipped. Mirrors the NOTE_TOPIC_TOP_LEVEL whitelist in validate.py.
_TOPIC_ORDER = (
    "env",
    "training-infra",
    "evaluation",
    "agents",
    "scenarios",
    "paper",
    "memory-system",
    "pipeline",
)


def _load_notes(notes_dir: Path) -> list[dict[str, Any]]:
    """Load every NOTE-*.md frontmatter from ``notes_dir`` (or empty list)."""
    if notes_dir is None or not notes_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(notes_dir.glob("NOTE-*.md")):
        meta = _load_yaml_frontmatter(path)
        if meta is not None:
            meta["_path"] = path
            out.append(meta)
    return out


def _note_summary_first_line(note_path: Path) -> str:
    """Pull the first non-blank line of the note's `## Summary` body."""
    text = note_path.read_text(encoding="utf-8")
    match = re.search(
        r"^##\s+Summary\s*\n+(.*?)(?=\n##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ""
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _archive_index_rows(notes: list[dict[str, Any]]) -> list[str]:
    """Build bucket rows for the `## Archive Index` section.

    Per spec §3.5 and §9-1:
    - One row per top-level topic with ≥ 1 note
    - Within a row: ``[topic] N notes · M claims extracted — NOTE-X summary;
      NOTE-Y summary; NOTE-Z summary`` (up to 3 most-recent by date desc,
      summary truncated to 60 chars)
    - Row order follows ``_TOPIC_ORDER``
    """
    if not notes:
        return []
    buckets: dict[str, list[dict[str, Any]]] = {}
    for n in notes:
        topics = n.get("topics") or []
        if not topics:
            continue
        top = topics[0]
        buckets.setdefault(top, []).append(n)

    rows: list[str] = []
    for top in _TOPIC_ORDER:
        bucket = buckets.get(top)
        if not bucket:
            continue
        bucket.sort(key=lambda n: str(n.get("date", "")), reverse=True)
        recent = bucket[:3]
        recent_strs: list[str] = []
        for n in recent:
            nid = n.get("id", "?")
            summary = _note_summary_first_line(n["_path"])
            if len(summary) > 60:
                summary = summary[:59] + "…"
            recent_strs.append(f"{nid} {summary}" if summary else nid)
        extracted = sum(
            1 for n in bucket if (n.get("extracted_claims") or [])
        )
        extracted_part = (
            f" · {extracted} claim{'s' if extracted != 1 else ''} extracted"
            if extracted else ""
        )
        rows.append(
            f"- [{top}] {len(bucket)} note{'s' if len(bucket) != 1 else ''}"
            f"{extracted_part} — " + "; ".join(recent_strs)
        )
    return rows
```

Update `render_state()` signature to accept `notes_dir`:

```python
def render_state(
    claims_dir: Path,
    rounds_dir: Path,
    questions_dir: Path,
    out_path: Path,
    glossary_path: Path | None = None,
    notes_dir: Path | None = None,
) -> None:
```

Inside `render_state()`, just before the `## Stats` section emission, add:

```python
    # Archive Index (Note entity). Emitted only when ≥ 1 note exists.
    notes = _load_notes(notes_dir) if notes_dir else []
    arch_rows = _archive_index_rows(notes)
    if arch_rows:
        lines.append("## Archive Index")
        lines.append("")
        lines.append(
            "> Query: `python memory/tools/note_query.py --topic <top> "
            "[--tag <sub>] [--round <RNN>] [--grep <pattern>]`"
        )
        lines.append("")
        for row in arch_rows:
            lines.append(row)
        lines.append("")
```

Update `main()` to pass notes_dir:

```python
    parser.add_argument("--notes-dir", type=Path, default=base / "notes")
    args = parser.parse_args()
    render_state(
        args.claims_dir,
        args.rounds_dir,
        args.questions_dir,
        args.out,
        glossary_path=args.glossary,
        notes_dir=args.notes_dir,
    )
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd memory/tools && python -m pytest tests/test_render.py -v -k "archive_index"`
Expected: 3 new tests pass.

Run: `cd memory/tools && python -m pytest tests/ -v`
Expected: full suite green.

- [ ] **Step 5: Render against real tree (should be unchanged — 0 notes yet)**

Run: `python memory/tools/render.py`
Expected: prints `Rendered memory/STATE.md`. Inspect file: should NOT contain `## Archive Index` yet (no notes exist).

- [ ] **Step 6: Commit**

```bash
git add memory/tools/render.py memory/tools/tests/test_render.py
git commit -m "feat(memory): add STATE.md Archive Index section for Note entity"
```

---

### Task 7: Documentation — CLAUDE.md + handoffs/README.md

**Files:**
- Modify: `CLAUDE.md` — add Note row to entity table; add "Read first" hint
- Modify: `memory/handoffs/README.md` — note that handoffs are now mirror-indexed

- [ ] **Step 1: Update CLAUDE.md entity table**

Open `CLAUDE.md`, find the section "Memory subsystem (active oracle, R39+)" → "Entities at a glance" table. After the `STATE.md` row, insert:

```markdown
| **Note** (`NOTE-NNNN`) | `memory/notes/` | Indexed archive of handoffs / ADRs / legacy docs; NOT measurement-of-record | `validate.py` enforces 5 hard rules + 2 cross-entity warnings; `note_query.py` searches; `render.py` surfaces as `## Archive Index` |
```

- [ ] **Step 2: Update CLAUDE.md "Read first" list**

In the same section, after the existing bullet about open `memory/questions/Q-*.md` files, append:

```markdown
- For tasks that touch work from rounds older than ~20 rounds back, run
  `python memory/tools/note_query.py --topic <relevant> --grep <kw>`
  before assuming context is lost — historical handoffs / ADRs / legacy
  notes are indexed under `memory/notes/`.
```

- [ ] **Step 3: Update CLAUDE.md "When to write a new claim" — add Note**

Add a new subsection in the memory section after "When to open a Question":

```markdown
### When to write a new Note

When you encounter an external archive file (handoff, ADR, eng-note, legacy
doc, session report) that contains information AI sessions will want to
recall later. Use `python memory/tools/new_note.py --source ... --source-path
... --date ... --topic ... [--round ...]` to scaffold the stub, then fill
in `## Summary` (3-5 sentences), `## Key facts (claim candidates)`, and
`## Open threads`. Notes are index-only — they do NOT replace the source
file, and they do NOT feed Headlines / Leaderboard / Open Questions.
```

- [ ] **Step 4: Update `memory/handoffs/README.md`**

Append to end of file:

```markdown

## Indexed by Note entity (since 2026-05-19)

Each handoff in this directory is **also** indexed by a Note under
`memory/notes/` (with `source: handoff`). Notes contain a 3-5 sentence
summary + key facts; the handoff file itself is the verbatim source and
is unchanged. Use `python memory/tools/note_query.py --source handoff
--grep <kw>` to search the archive.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md memory/handoffs/README.md
git commit -m "docs: wire Note entity into CLAUDE.md and handoffs/README.md"
```

---

## Phase B — STATE.md hygiene (data-only, no TDD)

These tasks rectify stale state in the current oracle so the post-ingest
STATE.md is a clean baseline. Each task is "inspect + decide + write a
small file".

### Task 8: Audit R45 and R91 in-flight status

**Files:**
- Read: `memory/rounds/R45/plan.md`
- Read: `memory/rounds/R91/plan.md`
- Write (conditionally): `memory/rounds/R45/verdict.md` and/or `memory/rounds/R91/verdict.md`

- [ ] **Step 1: Read both plans**

Run: `cat memory/rounds/R45/plan.md memory/rounds/R91/plan.md`

For each round, determine:
- Is the work actually in progress in a parallel session? Check `git log --since="14 days ago" -- memory/rounds/R45/` and `--since="14 days ago" -- memory/rounds/R91/`.
- Is the plan from an old date with no follow-on commits?

- [ ] **Step 2: For each stale round, write an `abandoned` verdict**

If a round is determined stale (no recent commits, plan is from > 14 days ago, no active session referenced in STATE.md headlines), create `memory/rounds/RXX/verdict.md`:

```markdown
**Status**: abandoned

## TL;DR
Round opened 2026-MM-DD but never executed. Closing administratively as part of
the 2026-05-19 STATE.md hygiene pass. No claims written.

## Questions opened (this round)
(none)

## Questions closed (this round)
(none)

## Questions advanced (this round, status unchanged)
(none)
```

(Note: R≥59 verdicts must also have `## 给 PI 的话` per ADR-0003 — if either R45 or R91 is ≥ R59 and the abandonment is administrative, write a 1-line briefing under that heading explaining the abandonment.)

- [ ] **Step 3: For any round still genuinely in-flight, leave as-is**

(Do not modify verdict.md if work is real.)

- [ ] **Step 4: Re-render STATE.md**

Run: `python memory/tools/render.py && python memory/tools/validate.py`
Expected: validate green; STATE.md `## In-Flight` section drops the abandoned round(s).

- [ ] **Step 5: Commit**

```bash
git add memory/rounds/R45/verdict.md memory/rounds/R91/verdict.md memory/STATE.md
git commit -m "fix(memory): close stale R45/R91 in-flight markers; refresh STATE"
```

(Skip any path that wasn't actually created.)

---

### Task 9: Close R90 (or annotate why pending)

**Files:**
- Read: `memory/rounds/R90/plan.md` (or whatever exists)
- Write (conditionally): `memory/rounds/R90/verdict.md`

- [ ] **Step 1: Determine R90 state**

Run: `ls memory/rounds/R90/ && cat memory/rounds/R90/plan.md 2>/dev/null | head -40`

- [ ] **Step 2: Decide one of two paths**

**Path A — round actually completed but verdict missing:** Write a proper verdict.md with the 3 mandatory Q-sections and (R90 ≥ R59) the `## 给 PI 的话` briefing. Use `_TEMPLATE_VERDICT.md` as starting point.

**Path B — round really in-flight:** Leave plan as-is; this task no-ops.

- [ ] **Step 3: Re-render + validate**

Run: `python memory/tools/render.py && python memory/tools/validate.py`
Expected: STATE.md "Latest Round R90" no longer shows "(no TL;DR yet)" if Path A taken.

- [ ] **Step 4: Commit (if changes)**

```bash
git add memory/rounds/R90/verdict.md memory/STATE.md
git commit -m "fix(memory): close R90 verdict for clean STATE.md baseline"
```

---

### Task 10: Verify R88/R89 historical briefings render

**Files:**
- Read: `memory/rounds/R88/verdict.md`, `memory/rounds/R89/verdict.md`
- Inspect: `memory/STATE.md` after render

- [ ] **Step 1: Check verdicts exist with `## 给 PI 的话`**

Run:
```bash
grep -l "## 给 PI 的话" memory/rounds/R88/verdict.md memory/rounds/R89/verdict.md
```
Expected: both files listed.

- [ ] **Step 2: Re-render and inspect 历史简报**

Run: `python memory/tools/render.py && grep -A 8 "## 历史简报" memory/STATE.md`
Expected: R88 and R89 appear as one-line entries.

- [ ] **Step 3: If R88/R89 are missing from 历史简报, debug**

Possible causes: (a) verdict has section but body has no `**结果（一句话）**` line — fix verdict format; (b) `HISTORICAL_BRIEFINGS_KEEP = 5` cutoff — non-issue at current count.

- [ ] **Step 4: Commit any verdict fixes**

```bash
git add memory/rounds/R88/verdict.md memory/rounds/R89/verdict.md memory/STATE.md
git commit -m "fix(memory): make R88/R89 verdicts render in 历史简报"
```

(Skip if no changes were needed.)

---

## Phase C — Migration waves (data-only)

Each wave creates Note files via `new_note.py`, then fills in `## Summary`,
`## Key facts`, `## Open threads` from the source. Verification after each
wave: `validate.py` green + `render.py` regenerates with growing Archive
Index + warning count drops.

**Workflow per note (apply to all wave tasks):**

1. Identify source file path, original creation date, related rounds (grep
   for "RNN" mentions inside the source), topics (top-level from
   `_TOPIC_ORDER` + 1-3 free sub-tags).
2. Scaffold: `python memory/tools/new_note.py --source <S> --source-path <P> --date <D> --topic <top> --topic <sub> [--topic <sub>] --round <R> ...`
3. Open the created `NOTE-NNNN.md` and replace the body's `## Summary`,
   `## Key facts`, `## Open threads` placeholder bullets with real content.
4. Cap Summary at 5 sentences. Cap Key facts at 5 bullets unless source is
   exceptionally dense.

### Task 11: Wave 0 — 5 ADR notes

**Files:**
- Read: `docs/adr/0001-src-layout.md`, `0002-paper-strict-vs-paper-faithful.md`, `0003-pi-briefing-layer.md`, `0004-v5-env-regca1-plant-paper-deviation.md`, `0005-andes-only-drop-simulink-1to1.md`
- Create: 5 notes under `memory/notes/`

- [ ] **Step 1: Worked example — NOTE-0001 for ADR-0001**

Run:
```bash
python memory/tools/new_note.py \
  --source adr-rationale \
  --source-path docs/adr/0001-src-layout.md \
  --date 2026-05-16 \
  --topic pipeline --topic src-layout \
  --round R37 \
  --summary "Repository refactor to src/ layout."
```

Open the produced `memory/notes/NOTE-0001.md` and replace the body with:

```markdown
## Summary
ADR-0001 decided to move the package code from a flat repository layout
to `src/andes_rl_kundur/` to enable PEP 517 installable builds and to
separate library code from scripts. Decision was implemented during R37
which also triggered the move of `paper_grade_axes.py` from project root
into `src/andes_rl_kundur/evaluation/`.

## Key facts (claim candidates)
- `src/andes_rl_kundur/` is the only canonical home for library Python; scripts go in `scripts/`.
- R37 verdict (CLM-0040) is the implementation reference.
- Frozen ancestors of refactored modules live in `_legacy/`.

## Open threads
- Whether `tests/` should be promoted into `src/andes_rl_kundur/tests/` is unresolved.
```

(Use real content from the ADR; the above is illustrative.)

- [ ] **Step 2: Repeat for ADR-0002..ADR-0005**

For each remaining ADR:
- ADR-0002 paper-strict-vs-paper-faithful → topics `[paper, paper-strict]`; related round R72 (paper-grade evaluator)
- ADR-0003 pi-briefing-layer → topics `[memory-system, pi-briefing]`; related round R59
- ADR-0004 v5-env-regca1-plant-paper-deviation → topics `[env, v5, regca1]`; related round R80
- ADR-0005 andes-only-drop-simulink-1to1 → topics `[env, simulink]`; related round R80

Scaffold each with `new_note.py`, then fill body from the ADR's `## Decision` and `## Rationale` sections.

- [ ] **Step 3: Validate + render**

Run: `python memory/tools/validate.py`
Expected: 0 errors; X1 (ADR coverage) warnings drop to 0; X2 (handoff) warnings still ~9.

Run: `python memory/tools/render.py && head -30 memory/STATE.md`
Expected: `## Archive Index` section now exists with `[pipeline]`, `[paper]`, `[memory-system]`, `[env]` buckets.

- [ ] **Step 4: Add `## Related Notes` footer to each ADR**

For each ADR, append a section at the end of the file:

```markdown

## Related Notes

- [NOTE-XXXX](../../memory/notes/NOTE-XXXX.md) — Note index entry for this ADR's rationale.
```

(Update XXXX per ADR.)

- [ ] **Step 5: Commit**

```bash
git add memory/notes/NOTE-000{1,2,3,4,5}.md docs/adr/000{1,2,3,4,5}-*.md memory/STATE.md
git commit -m "feat(memory): Wave 0 — ingest 5 ADRs as Note index entries"
```

---

### Task 12: Wave 1 — 9 handoff notes (split where needed)

**Files:**
- Create: 9-11 notes under `memory/notes/` (NOTE-0006 onward)
- Read: each file in `memory/handoffs/*.md`

- [ ] **Step 1: Survey + split decisions**

Run: `wc -l memory/handoffs/*.md`

For each handoff:

| Handoff | Lines | Split? | Topic(s) |
|---|---|---|---|
| `2026-05-15-migration-complete.md` | 58 | no | `[pipeline]` |
| `2026-05-17_R52_memory_hygiene_plan.md` | 549 | **yes** if ≥ 2 top-level topics | `[memory-system]` (+ maybe `[evaluation]`) |
| `2026-05-17_R56_lstm-actor-implementation.md` | 470 | **yes** if ≥ 2 top-level topics | `[agents, lstm]` (+ maybe `[training-infra]`) |
| `2026-05-17_R58_paper_strict_handoff.md` | 229 | no | `[paper, paper-strict]` |
| `2026-05-17_R58_to_R66_hyper_sweep_handoff.md` | 289 | no | `[training-infra, hyper-sweep]` |
| `2026-05-17_post-R41.md` | 192 | no | depends on content — likely `[env]` or `[evaluation]` |
| `2026-05-17_post-R55_arc-summary.md` | 331 | maybe | `[evaluation]` |
| `2026-05-17_post-refactor.md` | 88 | no | `[pipeline]` |
| `2026-05-18_R67_to_R75_evaluator_evolution_handoff.md` | 302 | no | `[evaluation]` |

**Split rule (from spec §5 Wave 1):** if source > 400 lines AND covers ≥ 2 top-level topics → one note per top-level topic, all pointing to the same `source_path`.

- [ ] **Step 2: For each handoff, scaffold + fill**

Apply the standard workflow:
```bash
python memory/tools/new_note.py --source handoff --source-path memory/handoffs/<file> --date <YYYY-MM-DD> --topic <top> [--topic <sub>] --round R<N> [--round R<N>]
```

Then fill body. Pull the handoff's TL;DR / executive summary for `## Summary`. Extract concrete findings as bullets for `## Key facts`. Anything the handoff explicitly flagged as TODO becomes `## Open threads`.

- [ ] **Step 3: Validate after each note**

Run `python memory/tools/validate.py` between notes if you want to catch typos in source_path early. Otherwise batch and validate at end.

- [ ] **Step 4: Re-render + verify Archive Index growth**

Run: `python memory/tools/render.py && grep -A 12 "## Archive Index" memory/STATE.md`
Expected: at least 5 of 8 top-level buckets populated; X2 handoff warnings drop to 0.

- [ ] **Step 5: Commit**

```bash
git add memory/notes/NOTE-00{06,07,08,09,10,11,12,13,14,15,16}.md memory/STATE.md
git commit -m "feat(memory): Wave 1 — ingest 9 handoffs as Note index entries"
```

(Adjust glob if fewer/more notes were created. Use `git status` to see the exact list.)

---

### Task 13: Wave 2 — eng-notes + session-report (2 notes)

**Files:**
- Read: `docs/eng-notes/NOTES_ANDES.md`, `_legacy/session_report_2026-05-07_v4_audit.md`
- Create: 2 notes

- [ ] **Step 1: Scaffold + fill NOTES_ANDES**

```bash
python memory/tools/new_note.py \
  --source eng-note \
  --source-path docs/eng-notes/NOTES_ANDES.md \
  --date <look at git log first-commit date for this file> \
  --topic env --topic training-infra --topic andes
```

Fill body from NOTES_ANDES sections.

- [ ] **Step 2: Scaffold + fill v4 audit session report**

```bash
python memory/tools/new_note.py \
  --source session-report \
  --source-path _legacy/session_report_2026-05-07_v4_audit.md \
  --date 2026-05-07 \
  --topic env --topic evaluation --topic v4
```

- [ ] **Step 3: Validate + render**

Run: `python memory/tools/validate.py && python memory/tools/render.py`

- [ ] **Step 4: Commit**

```bash
git add memory/notes/ memory/STATE.md
git commit -m "feat(memory): Wave 2 — ingest 2 eng-notes/session-report"
```

---

### Task 14: Wave 3 — `_legacy/` (5-8 notes with topic splits)

**Files:**
- Read: `_legacy/CONTEXT.md` (575 lines), `_legacy/RESEARCH_TRAIL.md` (520), `_legacy/优化方向.md` (89)
- Create: 5-8 notes

- [ ] **Step 1: Survey `_legacy/CONTEXT.md` and decide splits**

Run: `cat _legacy/CONTEXT.md | head -100`

Likely split into 3 notes by section:
- env / scenarios (KUNDUR contract, V4 env, scenarios)
- agents (SAC, CTDE, agent registry)
- pipeline (project structure, file layout)

For each split: scaffold a note with the **same `source_path: _legacy/CONTEXT.md`** but distinct topics + distinct summaries focusing on that section.

- [ ] **Step 2: Survey `_legacy/RESEARCH_TRAIL.md` and split**

This is a chronological narrative. Split by **phase** rather than topic:
- pre-V4 phase (R01-R20 era)
- V4-bringup (R30-R37 era)
- paper-grade evaluator (R38+ pre-R39)

Each phase gets one note. `topics[0]` = `pipeline` for narrative log; sub-tags = `[research-trail, R0X-R0Y]`.

- [ ] **Step 3: `_legacy/优化方向.md` — single note**

```bash
python memory/tools/new_note.py \
  --source legacy \
  --source-path _legacy/优化方向.md \
  --date <git log first commit date> \
  --topic paper --topic optimization-direction
```

- [ ] **Step 4: Validate + render**

Run: `python memory/tools/validate.py && python memory/tools/render.py`
Expected: 6-8 of 8 top-level buckets populated.

- [ ] **Step 5: Commit**

```bash
git add memory/notes/ memory/STATE.md
git commit -m "feat(memory): Wave 3 — ingest _legacy/ docs as Note index entries (split by topic/phase)"
```

---

### Task 15: Wave 4 — sweep for missed sources

**Files:**
- Possibly create: more notes (≤ 5 expected)

- [ ] **Step 1: Check `scripts/_archive/` for substantial docstrings**

Run:
```bash
for f in scripts/_archive/r*.py; do
  echo "=== $f ==="
  head -30 "$f"
done | head -200
```

If any frozen driver has a multi-paragraph rationale **not** covered by an existing claim, scaffold a note with `source: legacy`, `topics: [pipeline, archived-script]`.

- [ ] **Step 2: Check `results/whitelist/` (if exists)**

Run: `ls results/whitelist/ 2>/dev/null`. If any `.md` files exist with experimental decisions, ingest as needed.

- [ ] **Step 3: Check GitHub issues for closed-with-decision items**

Run: `gh issue list --state closed --limit 20 --json number,title,closedAt --jq '.[] | "\(.number) \(.title) (\(.closedAt))"'`

If any closed issue contains a decision **not** captured in claims or ADRs, ingest as a note with `source: session-report`, `source_path: docs/issues/<N>.md` (you'll need to dump the issue body to a file first under `docs/issues/`).

(This step may produce 0 notes — that's fine.)

- [ ] **Step 4: Final validate + render**

Run: `python memory/tools/validate.py && python memory/tools/render.py`
Expected: 0 errors; X1 and X2 warnings both 0; Archive Index covers ≥ 6 of 8 buckets.

- [ ] **Step 5: Commit (if any notes added)**

```bash
git add memory/notes/ memory/STATE.md
git commit -m "feat(memory): Wave 4 — sweep additional sources into Note index"
```

---

## Phase D — Round documentation + close

The R39 memory subsystem itself logs schema/infra changes as a round.
This phase reserves a new round, writes its plan + verdict, and closes
the work.

### Task 16: Reserve round + write plan + write verdict

**Files:**
- Run: `python memory/tools/reserve_round.py`
- Create: `memory/rounds/RXX/plan.md`
- Create: `memory/rounds/RXX/verdict.md`
- Create: 1 claim (`memory/claims/CLM-NNNN.md`) documenting the schema decision

- [ ] **Step 1: Reserve next round number**

Run: `python memory/tools/reserve_round.py`
Expected: prints the next R-number (e.g. `93`). Note the number for subsequent steps; this plan will refer to it as `R<NEW>`.

- [ ] **Step 2: Write `memory/rounds/R<NEW>/plan.md`**

Use minimal but complete:

```markdown
# R<NEW> plan — Memory subsystem: Note entity + legacy archive ingest

**Date**: 2026-05-19
**Type**: infrastructure (schema + tooling + data migration, no experiment)
**Status**: complete (close concurrently with this plan)

## Trigger

User flagged that R39's intentional exclusion of `handoffs/` / `docs/adr/` /
`docs/eng-notes/` / `_legacy/` from the memory schema had become a research
liability: AI sessions could not surface prior research without manual file
archaeology. User goal: "let conversations be aware of all past experiments
and data for scientific work."

## Decisions (locked via brainstorming session 2026-05-19)

| ID | Decision |
|----|----------|
| A | New entity kind `Note` (`NOTE-NNNN`) as index layer; does NOT replace original files |
| B | `memory/notes/` directory; original `handoffs/` / `docs/` paths unchanged |
| C | Double-layer topics: 8 closed top-level + free sub-tags |
| D | STATE.md `## Archive Index` section: 9-row cap, query-hint footer |
| E | 5 hard rules (N1-N5) + 2 cross-entity warnings (X1, X2) in validate.py |
| F | 4 migration waves: ADR → handoffs → eng-notes → legacy + Wave 4 sweep |
| G | Pre-flight STATE.md hygiene: close R45/R90/R91 if stale |
| H | Lazy claim extraction: notes are index; claims come later when needed |

## Implementation

Plan: [docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md](../../../docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md)
Spec: [docs/superpowers/specs/2026-05-19-memory-system-notes-ingest-design.md](../../../docs/superpowers/specs/2026-05-19-memory-system-notes-ingest-design.md)

## Out of scope

- Auto-summarization of notes via LLM (Wave 0-4 summaries are human-written for accuracy)
- Note → claim auto-extraction (lazy; do it when a future round needs to cite a Key Fact)
- Indexing GitHub PRs / commit messages (would multiply note count by 10×)
```

- [ ] **Step 3: Write `memory/rounds/R<NEW>/verdict.md`**

Start from `memory/rounds/_TEMPLATE_VERDICT.md`. Required sections (per validate.py):

- `## Questions opened (this round)` — likely: `Q-NEXT — Will the Archive Index actually be queried in subsequent rounds (signal that the lazy-extraction loop is working)?`
- `## Questions closed (this round)` — none unless this round closed an open Q
- `## Questions advanced (this round, status unchanged)` — none
- `## 给 PI 的话` (because R<NEW> ≥ R59) — 4 paragraphs per ADR-0003: 这周干了啥 / 结果（一句话） / 意外 / 我默认下一步做

- [ ] **Step 4: Write CLM-NNNN documenting the decision**

Reserve next claim id: `ls memory/claims/CLM-*.md | tail -1` shows current max; next is +1.

Create `memory/claims/CLM-NNNN.md`:

```markdown
---
id: CLM-NNNN
type: decision
trust: S
status: current
statement: |
  R<NEW> introduced the Note entity (`NOTE-NNNN`) as an index layer over
  external archives (`handoffs/`, `docs/adr/`, `docs/eng-notes/`, `_legacy/`).
  Schema: 8 frontmatter fields + 3 mandatory body sections; double-layer topics
  with 8 closed top-level buckets; 5 hard validation rules (N1-N5) + 2 cross-
  entity warnings (X1, X2). Original source files remain byte-identical;
  Notes are not measurement-of-record (do NOT feed Headlines / Leaderboard).
  Migration: 4 waves (ADR / handoffs / eng-notes / legacy) + sweep = ~21-31
  notes total. Lazy claim extraction: notes are index; claims come later
  when a future round wants to cite a Key Fact.
round: R<NEW>
provenance:
  - docs/superpowers/specs/2026-05-19-memory-system-notes-ingest-design.md
  - docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md
  - memory/rounds/R<NEW>/verdict.md
tags: [memory-system, schema, decision, note-entity]
---
```

- [ ] **Step 5: If R<NEW>-verdict opened a Q, create Q-NNNN**

Reserve next Q id: `ls memory/questions/Q-*.md | tail -1`. Create `memory/questions/Q-NNNN.md` following the template, with status `open`, `opened_round: R<NEW>`.

- [ ] **Step 6: Final validate + render**

Run: `python memory/tools/validate.py && python memory/tools/render.py`
Expected: 0 errors; STATE.md shows R<NEW> as latest round with TL;DR + PI briefing.

- [ ] **Step 7: Per ADR-0003: paste the `## 给 PI 的话` body verbatim into the chat**

This is the contractual closing action. Do NOT skip it. Print the briefing body as your closing turn message in the format:

> 我已经把简报写进 verdict.md，下面是 `## 给 PI 的话` 全文：
>
> [briefing body verbatim]

- [ ] **Step 8: Commit**

```bash
git add memory/rounds/R<NEW>/ memory/claims/CLM-NNNN.md memory/questions/Q-NNNN.md memory/STATE.md
git commit -m "memory(R<NEW>): close round — Note entity + legacy archive ingest

Schema: 5 hard rules + 2 cross-entity warnings.
Migration: ~21-31 notes across 4 waves + sweep.
Original handoffs / ADRs / legacy docs unchanged.
See docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md
"
```

---

## Verification — End-to-end success criteria (from spec §7)

- [ ] `python memory/tools/validate.py` returns 0 errors after every wave
- [ ] `memory/STATE.md` contains a `## Archive Index` section showing ≥ 6 of 8 top-level buckets populated
- [ ] `python memory/tools/note_query.py --topic training-infra` returns ≥ 1 hit for the LSTM rollout zero-padding handoff content
- [ ] `python memory/tools/note_query.py --grep "paper-strict"` returns at least the ADR-rationale note + the R58 handoff note
- [ ] `python memory/tools/validate.py` X1 (ADR coverage) warnings = 0
- [ ] `python memory/tools/validate.py` X2 (handoff coverage) warnings = 0
- [ ] At least 1 claim has `extracted_from: NOTE-NNNN` (or equivalent provenance pointing at a note) within 30 days — deferred, not checked in this round.

---

## Plan Self-Review Notes (2026-05-19)

Spec coverage check passed: every requirement in spec §3-§9 maps to at least
one task. §9 decisions (extraction count in Archive Index, global note ids,
no back-reference into source files) are reflected in Tasks 4, 6, and the
absence of source-mutation steps respectively.

Placeholder scan passed: no TBD / TODO / "add appropriate handling" / etc.
Real test code blocks appear in Tasks 2-6; real migration content
sketches appear in Tasks 11-14.

Type consistency check: `load_notes` / `validate_note_rules` / `_load_notes`
(render.py) / `_archive_index_rows` signatures cross-checked. `notes_dir`
parameter name consistent across new_note.py, note_query.py, render.py,
validate.py. `NOTE_TOPIC_TOP_LEVEL` (validate.py) and `_TOPIC_ORDER`
(render.py) are intentionally separate symbols holding the same content
(set vs tuple — different access patterns) — both should stay in sync
when adding a 9th top-level topic.
