# Compliance matrix

Cover each applicable row. Add journal-specific rows discovered from official
instructions.

| Category | Examples of fields to verify |
|---|---|
| Identity | journal, article type, submission stage, manuscript title |
| Scope | journal scope, systems versus component emphasis, originality |
| Length | page or word limit, abstract length, supplement treatment |
| Structure | required sections, numbering, appendices, nomenclature |
| Front matter | title, authors, affiliations, corresponding author, keywords |
| Submission artifacts | source files, PDF, highlights, graphical abstract, cover letter |
| Figures and tables | formats, resolution, fonts, captions, permissions, accessibility |
| References | citation completeness, style at submission, DOI or metadata expectations |
| Review model | anonymization, identifying links, acknowledgments, repository URLs |
| Ethics | originality, concurrent submission, authorship, conflicts, funding |
| AI use | author-use declaration, image restrictions, confidentiality, human responsibility |
| Prior work | conference paper, preprint, thesis, report, related manuscript |
| Open science | data statement, code, repository, persistent identifier, supplement |
| Rights | copyright, third-party permissions, licenses |
| Submission system | required forms, author accounts, ORCID, classifications |
| Build | clean compilation, PDF inspection, package inventory and hash |
| Human approval | all-author approval, author order, corresponding-author confirmation |

## Status semantics

- `PASS`: artifact or author confirmation satisfies an official requirement.
- `WARN`: a soft recommendation, optional improvement, or documented
  journal-specific exception remains.
- `FAIL`: an applicable hard requirement is unmet.
- `UNKNOWN`: the source, applicability, or evidence is unresolved.
- `N/A`: the requirement is demonstrably inapplicable to this article type.

Every `PASS` needs either an artifact locator or named human confirmation.
Every `N/A` needs a reason. `UNKNOWN` prevents a readiness decision.

## Final report

Include package fingerprints:

- source file inventory;
- compilation command and exit status;
- reviewed PDF path and hash;
- date of official-source capture;
- date and owners of human sign-offs.

This makes the audit reproducible without turning it into a permanent scientific
evidence ledger.
