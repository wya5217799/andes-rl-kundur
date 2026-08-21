# Verification recipes

These tools are deliberately separated into evidence verification and future-experiment recipes.

## Deterministic checks on the delivered package

```bash
./verification/run_all_checks.sh /path/to/extracted/gpt_pro_math_pack_20260820
```

The command verifies all source hashes, checks every `SEALED_JSON` pointer/value pair, rebuilds all 225 evidence rows from the source package, compares the rebuilt ledger by evidence ID, runs a HYPOTHETICAL exact-rational SOCP example, and writes a non-failing numeric traceability review to `qa/numeric_trace_lint.json`.

`verify_evidence.py` does not claim to recompute derived rows. `rebuild_evidence.py` performs that independent reconstruction and is the authoritative derived-value test.

## P1 matched complex-response check

Prepare an NPZ following the schema in `p1_complex_sensitivity_recipe.py`, then run:

```bash
python verification/p1_complex_sensitivity_recipe.py matched_responses.npz --output p1_check.json
```

The output compares the central finite difference of `log(E_K/E_L)` with the two weighted complex-response derivative terms. All supplied step sizes and responses are HYPOTHETICAL until registered and sealed.

## P2 delay-law check

```bash
python verification/p2_delay_boundary_recipe.py nominal_loop.npz --output p2_curve.json
```

The script evaluates the exact integer-delay sensitivity ratio. It computes a registered endpoint curve only when the complex numerator, weights, and fixed same-bank local-reference energy are supplied. It never labels an endpoint crossing as instability.

## P3 DAE finite-difference check

Generate equilibrium algebraic re-solves for positive and negative action perturbations and store the differential residuals in the schema documented by `p3_dae_fd_recipe.py`:

```bash
python verification/p3_dae_fd_recipe.py dae_fd_evaluations.npz --output p3_channel.json
```

Supplying `f_u`, `f_y`, `g_u`, and `g_y` adds the independent Schur reconstruction. The experiment must separately seal the gauge, active mode, solver tolerance, perturbation sequence, and materiality rule.

## C1 exact dual checker

`c1_exact_conic_dual_checker.py` verifies a positive dual lower bound in exact rational arithmetic for the stated standard-form SOCP convention:

```bash
python verification/c1_exact_conic_dual_checker.py exact_dual_certificate.json
```

The included file `examples/HYPOTHETICAL_c1_dual_example.json` is a toy schema test, not VSG evidence. A project certificate must also prove that its conic data come from a valid DCF/Youla or SLS parameterization and the frozen response map.

## Mechanism observables

`m_observable_matrix.csv` is machine-readable. Each row names the sealed or proposed file, field/pointer, and directions that count as support or refutation for M3, M5, M4, M1, and M2.
