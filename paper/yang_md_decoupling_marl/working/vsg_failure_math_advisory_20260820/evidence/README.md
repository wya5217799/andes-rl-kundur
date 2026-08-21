# Evidence-register usage guide

`evidence_register.csv` and `evidence_register.json` contain the same records.

| Field | Meaning |
|---|---|
| `evidence_id` | Stable identifier used in the report. |
| `problem_id` | P1, P2, P3, M1–M5, or C1. |
| `status` | `SEALED_JSON`, `DERIVED_FROM_SEALED_JSON`, `PACKAGE_SOURCE_CODE`, or `HYPOTHETICAL`. |
| `source_path` | Path relative to the extracted source package. |
| `json_pointer_or_range` | RFC-6901-style JSON Pointer, or a package-source line/range description. |
| `value` | Canonical text form of the sealed or derived value. |
| `unit` | Package unit or descriptive unit where available. |
| `derivation` | Formula/aggregate used for a derived value. |
| `source_evidence_ids` | Semicolon-separated direct inputs when compact; aggregate source roots are supplied in companion JSON files. |
| `notes` | Comparability and source-root cautions. |

Run `python verification/verify_evidence.py --source-root <extracted-package>` to check every sealed JSON field and the source package hashes. Run `python verification/rebuild_evidence.py --source-root <extracted-package> --output-root <temporary-output>` to independently reconstruct the full ledger and compare it with the shipped register.
