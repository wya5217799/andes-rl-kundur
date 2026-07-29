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

## Binaries

A binary is tracked only when a registered delivery line declares it as a
canonical, derived, release, or support artifact. Final manuscript and proposal
PDFs may therefore remain tracked. LaTeX auxiliaries, simulator scratch files,
runtime logs, caches, and temporary review output remain generated locally.

When a release PDF is a second physical copy of a manuscript PDF, the artifact
contract declares a `byte-identical` relationship. Repository health compares
their SHA-256 content and fails on drift.
