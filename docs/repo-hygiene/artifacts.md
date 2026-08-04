# Scratch, cache, and binary policy

## Scratch and cache

- `tmp/andes/` holds preserved per-run ANDES working directories.
- `tmp/cache/` holds pytest, Ruff, and mypy caches.
- `tmp/quarantine/` holds recoverable cleanup moves until the owner decides
  they are no longer needed.
- Tool state that requires a fixed root name is declared explicitly in the
  repository contract.

The whole `tmp/` tree is ignored. Repository health still checks the root
filesystem, so ignored output that escapes `tmp/` is a violation.

## Durable manuscript documents

Binary registration and semantic document registration are separate checks.
Every active manuscript line declares its durable generated documents in
`paper/<line>/ARTIFACTS.json`. Repository health enforces ownership, existence,
one active canonical artifact per purpose, supersession consistency, review
dates for time-sensitive decisions, and optional input hashes. Every durable
file below the manuscript root must be covered by a registered file or
directory; `ARTIFACTS.json` itself is the only implicit entry. An expired
active artifact or a changed hashed input is a hard failure, not a warning.
`session_context.py` always adds the manifest to the bounded reading set and
surfaces document alerts instead of silently treating stale analysis as
current.

### Selecting a manuscript line

Several ongoing manuscripts may be `active` simultaneously. `active` is a
lifecycle state; it does not select a repository-wide paper. Discover lines
without loading research history:

```powershell
python memory/tools/session_context.py --json --list-lines
```

Select the paper named by the current request:

```powershell
python memory/tools/session_context.py --json --line <line-id>
```

An explicit selection loads and validates only that line's navigation
metadata. Its `write_roots` remain exclusive, while claims and results are
shared read-only evidence reached through that line's pointers. `priority` is
used only when no paper is named. Switching does not edit priorities, freeze a
different line, or copy evidence. A frozen line must be deliberately
reactivated before it becomes selectable.

Input hashes may snapshot either one file or a directory tree. When a
manuscript line owns an authoritative `experiment-feeds` artifact, its active
canonical `line-state` must declare and hash that feed directory. Adding or
editing a feed therefore produces `DOCUMENT_INPUT_DRIFT` and cold-start mode
`manuscript-refresh`. Refresh the hash only after reconciling `LINE.md`,
`required_reading`, and every affected registered draft/review input; changing
the hash alone is not an acknowledgement.

`LINE.md` is a bounded navigation document. It declares at least one
`decision_refs` entry using `path#locator` and binds current experimental
evidence with `CLM-NNNN -> feed-path` entries in `evidence_refs`. The latest
authoritative feed must be present in those bindings. Feed files may not appear
in `required_reading`; consumers open one through its claim pointer only when a
specific statement needs evidence. The exact line and total cold-start byte
budgets live in `docs/repo-hygiene/contract.json` and are hard repository-health
failures.

Deep Research and reviewer output remains under `tmp/<line>/` unless another
session must rely on it. Promotion means updating the existing consolidated
artifact or superseding it in the manifest; a filename such as `final-v2-new`
is not a lifecycle.

The contract's `manuscript_lines.transient_patterns` excludes declared LaTeX
auxiliaries and runtime caches from durable-document registration. Keep this
list narrow: a manuscript `.gitignore`, source, evidence map, figure source, or
other cross-session input remains a registered artifact.

## Binaries

A binary is tracked only when a registered delivery line declares it as a
canonical, derived, release, or support artifact. Final manuscript and proposal
PDFs may therefore remain tracked. LaTeX auxiliaries, simulator scratch files,
runtime logs, caches, and temporary review output remain generated locally.
Small historical logs that are still cited by current claim provenance live
under `_legacy/logs/`; this is an archive exception, not an active runtime
output location.

The contract's `delivery_binary_extensions` list defines the enforced binary
set. Every matching file under a registered delivery root must be covered by a
declared role path; a declared directory covers its descendants. Undeclared
binaries fail repository health even when ignored by Git, preventing local
build debris from becoming a second delivery source.

When a release PDF is a second physical copy of a manuscript PDF, the artifact
contract declares a `byte-identical` relationship. Repository health compares
their SHA-256 content and fails on drift.
