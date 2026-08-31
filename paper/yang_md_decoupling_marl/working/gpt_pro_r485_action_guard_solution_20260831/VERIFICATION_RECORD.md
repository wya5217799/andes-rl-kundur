# R485 verification record

## Status

- verification: `PASS`
- Python syntax compilation: `PASS`
- verification exit status: `0`
- stderr: empty (`0` bytes)
- record generated at: `2026-08-31T07:18:21Z` (UTC)

## Exact executed commands

```bash
python -m py_compile /mnt/data/r485_solution_build/verification.py

python /mnt/data/r485_solution_build/verification.py \
  --input-zip /mnt/data/r485_gpt_pro_action_guard_20260831.zip \
  --json-out /mnt/data/r485_solution_build/DERIVED_RESULTS.json \
  > /mnt/data/r485_solution_build/verification-output.txt \
  2> /mnt/data/r485_solution_build/verification-stderr.txt
```

## Runtime and artifact binding

| Item | Value |
|---|---|
| Runtime | CPython 3.13.5 |
| Harness ref | `main@5ff04507b7a84c374a5494a8c8883d9dd0c05946` |
| Input ZIP SHA256 | `66a4ae492810e4d64254966a7acfe75a751f93d50138adbcc54f6ce2d5cf68fd` |
| `verification.py` SHA256 | `4efa35faba9c43072c46575749e88ba3fcd83c57d8b6984645b5e3ad71b98fb9` |
| `SOLUTION.md` SHA256 | `5265dbe1bc832f375de22287e96a6a31adb6e286109ef6e4c9d306654c461ad4` |
| `DERIVED_RESULTS.json` SHA256 | `e93af5d320b40511e373ab2d9325633ea3220d870cd4a4f5b7a835a1094f5738` |
| `verification-output.txt` SHA256 | `b3ef43e911b7645f343f4a8644ac82f6f1291c549ce521b15896acbc23f2ff66` |
| empty `verification-stderr.txt` SHA256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Executed scope

The checker actually performed the following operations on the exact input ZIP above:

1. validated all 33 manifest-listed file hashes and all 11 `.sha256` sidecars;
2. confirmed the selected problem roster is exactly 1/1;
3. enumerated the sealed formal tables for 208 policy decisions, 832 policy/profile blocks, and 16 threshold-grid cells;
4. checked the frozen counts `121/208`, `0/208`, and `832/832` failures for each action component;
5. recomputed action RMS, action total variation, bounds, slew, and normalized-action-to-M/D mapping for the eight raw profiles included in the package;
6. checked the scaling examples and both logical counterexamples used in `SOLUTION.md`.

The verbatim stdout is in `verification-output.txt`; the corresponding stderr file is empty.

## Evidence boundary

This is an executed deterministic formula/data audit, not an ANDES rerun, retraining run, hardware experiment, HIL test, independent reviewer, or physical safety certification. The 832-block conclusions are checked against the sealed formal decision tables; only the eight raw profiles actually present in the input package are independently reconstructed from step-level action data. Consequently, the run verifies the frozen arithmetic and the counterexamples within the stated scope, while actual actuator harm remains `INFORMATION INSUFFICIENT`.
