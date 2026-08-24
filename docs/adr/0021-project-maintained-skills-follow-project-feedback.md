# Project-maintained workflow follows the project feedback loop

- **Status:** Accepted
- **Date:** 2026-08-24

## Decision

Keep `skills/kundur-round/SKILL.md` as the only project skill entrypoint. The
research-junction, execution-readiness, evidence-audit, power-system-audit, and
submission-audit workflows remain versioned with the repository, but live as
plain internal references selected by `references/module-routing.md`.

External, pinned, system, plugin, and other-project skills remain outside the
repository. Installation location never grants research authority.

## Why

Moving five self-maintained workflows from global storage into five project
skills fixed ownership but created overlapping entrypoints. Several could
classify the same request, choose gates, or appear to own execution and claims.
Explicit-only metadata reduced accidental selection but did not define which
entrypoint should call which.

One entrypoint hides the repository lifecycle behind one interface. Internal
modules keep the feedback loop and specialized checks without participating in
skill discovery. Historical artifact producer names remain unchanged because
they record provenance, not current invocation.

## Verification

The scope manifest permits exactly one project entrypoint, lists internal
modules separately, and requires each module to be referenced by the internal
dispatch table. Contract tests exercise collision and dispatch scenarios.
