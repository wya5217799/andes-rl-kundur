# ADR-0017: Authorize one structurally clean REGCV1 successor

- **Status:** Accepted
- **Date:** 2026-08-14
- **Deciders:** repository owner and Codex research mission
- **Related:** ADR-0016, R384, CLM-1065, Q-0105

## Context

R384 validly stopped the first four-`REGCV1` formulation at native TDS
initialization. That construction retained four `GENROU`, four `TGOV1`, and
four `EXDC2` records with `u=0`. Its formal record proved status readback but
did not prove equation removal and did not archive equation-level residuals.

Read-only diagnosis of the installed ANDES 2.0.0 source found that TGOV1 block
equations can remain ungated by effective status. R80 independently observed
the same status-zero/TGOV1-residual mechanism on another plant formulation.
This is strong engineering motivation, not transferred R384 evidence and not
a basis for rewriting the sealed negative result.

## Decision

Authorize exactly one successor formulation on the existing
`converter-vsg-pq-decoupling` manuscript line. Keep ANDES 2.0.0, the Kundur
static tables and connectivity, the four controlled locations, and the R384
`REGCV1` parameter card fixed. Change only the system construction: derive a
deterministic input containing `Bus`, `PQ`, `PV`, `Slack`, `Line`, and `Area`
from the packaged case, require exact XLSX/JSON static-table equality, exclude
all legacy dynamic and event records by structure, and then add four
`REGCV1` devices before setup.

This is a materially different DAE formulation rather than an in-route retry:
the R384 object coexisted with twelve status-zero legacy dynamic records; the
successor admits none. Its first and only evidence question is clean
initialization and zero-input short-time validity. It does not repair,
supersede, or weaken CLM-1065.

## Consequences

- R385 owns the prospective structural-absence initialization gate.
- The formal record must archive source/derived hashes, static-table identity,
  forbidden-model/DAE absence, post-init references, solver flags, complete
  initialization residual diagnostics, finite guards, and drift.
- A valid failure stops `REGCV1` without gain tuning or model substitution.
- A pass opens only a separately registered signed `Pref/Qref` authority gate;
  it does not establish decoupling, controller value, learning need, stability,
  robustness, generalization, or deployment validity.

## Rejected alternatives

- **Repeat R384 with `u=0`:** rejected because it preserves the diagnosed
  ambiguity.
- **Patch installed ANDES equations:** rejected because it changes the platform
  implementation and would confound the device-object gate.
- **Switch immediately to REGCV2/REGF2 or EMT:** rejected because one cheaper
  causal construction test remains.
- **Change Kundur topology or static operating data:** rejected because it
  confounds the source-model intervention.
