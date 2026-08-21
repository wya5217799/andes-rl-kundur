# Repository-side verification

These files were generated locally during the 2026-08-21 intake. They are not
part of the external solver's declared 10-file SHA-256 manifest.

- `repo_checks.py` independently checks the U1 class dimension, U2 permutation
  combinatorics, U3 repository slew projector, U4 budget counterexample, U5 MIMO
  total derivative, U6 fractional ZOH split, U7 missing pure-action Taylor term,
  U8 projector identities, and the actual R458/U9 branch.
- `repo_checks.json` is the output of that checker. SHA-256:
  `9822dfbacb2f8b1bf34eba05173ed0321f0e1877dbb916b596bd7dd00bb48e61`.
- `derived_results_recomputed.json` is the output of rerunning the imported
  `verify_solution.py` against a fresh extraction of the sent evidence pack with
  source hashes enabled. It differs from the supplied derived JSON only in the
  absolute extraction path and one hypothetical Clopper--Pearson endpoint at
  approximately `1e-18` scale.

The governing scientific disposition remains `../IMPORT_NOTE.md`; detailed
claim-level verification remains `../SOURCE_VERIFICATION.md`.
