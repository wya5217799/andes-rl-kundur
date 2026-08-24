# Submission Audit Module

Internal reference of `kundur-round`; it is loaded only after the venue,
article type, and concrete submission package are fixed. It never participates
in skill discovery.

Separate current venue compliance from scientific review. Verify unstable rules
from official sources during every audit.

Read [the project research adapter](research-skill-adapter.md)
first; its venue boundary owns manuscript-line state and source freshness.

## Freeze the submission identity

Record:

- journal and article type;
- initial submission, revision, or camera-ready stage;
- manuscript source, compiled PDF, bibliography, supplement, data/code package,
  cover letter, highlights, graphical abstract, and declarations;
- prior conference, preprint, thesis, report, or related submission;
- corresponding author and coauthor sign-off state.

Complete this stage only when the exact article type and package inventory are
known. Mark missing decisions as blockers instead of assuming a default.

## Capture current official requirements

Browse the journal's official Guide for Authors, journal scope page, submission
checklist, publisher ethics policies, and any society-specific author kit.
Start from
[official-source-routing.md](official-source-routing.md)
for IJEPES, EPSR, and IEEE PES venues.

For every requirement record:

```text
Requirement | Hard/soft | Applies? | Official URL | Page heading
Access date | Manuscript/package evidence | PASS/WARN/FAIL/UNKNOWN | Action
```

Use `UNKNOWN` when an official page is inaccessible or ambiguous. Resolve it
through the journal office or submission portal before declaring readiness.

Complete this stage only when every official `must`, `required`, and submission
checklist item for the chosen article type appears in the matrix.

## Run the mechanical package scan

For LaTeX packages, run:

```powershell
python memory\tools\scan_latex_package.py paper\main.tex `
  --bib paper\references.bib `
  --require-file paper\highlights.docx
```

The scanner checks unresolved markers, included TeX files, labels and
references, citation keys, graphics, required artifacts, and package hashes. It
does not encode venue page limits or policy rules; bind those separately to the
official-source matrix.

Compile the actual source and visually inspect the produced PDF. Record compiler
command, warnings, page count, and the exact PDF reviewed.

Complete this stage only when all scanner failures are repaired or classified as
documented venue-specific exceptions.

## Audit ethics, provenance, and extensions

Apply
[extension-and-disclosures.md](extension-and-disclosures.md).
Reconcile the manuscript, cover letter, declarations, and submission-system
answers. Obtain human confirmation for authorship, conflicts, funding,
permissions, data availability, and AI-tool disclosure.

Complete this stage only when each disclosure has an owner and every related
prior work is identified, cited, and differentiated.

## Decide readiness

Use the matrix in
[compliance-matrix.md](compliance-matrix.md). Report:

1. target, article type, stage, and access date;
2. official sources consulted;
3. `FAIL` items, then `WARN`, then verified items;
4. mechanical scan and compilation results;
5. required human sign-offs;
6. decision: `NOT READY`, `CONDITIONALLY READY`, or `READY`.

Return `READY` only when all applicable hard requirements pass, the reviewed PDF
matches the source package, every required disclosure is confirmed by a human
author, and no `UNKNOWN` remains. Re-run a scoped audit after any material change
to claims, authorship, figures, references, or submission artifacts.
