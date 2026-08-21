# Tests

Run from the deliverable root:

```bash
python -m pip install -r code/requirements.txt
R402_PACKAGE_ROOT=/path/to/r402_causal_validation_v1 pytest -q tests
```

`test_r402_validation_audit.py` checks the raw 240-record package, exact endpoint
recomputation, all 36 profile-block guard failures, physical clamp diagnostics,
source-code defects, copied-source dependency closure, and preservation of partial-observation, credit-assignment, and distribution-shift alternatives.

`test_reference_fixes.py` checks the proposed slew-aware Markov action map and
componentwise effort terms without importing ANDES.
