# Machine checks

## Recompute sealed and derived values

```bash
python verify_solution.py \
  --source /path/to/gpt_pro_unresolved_math_pack_20260821 \
  --output derived_results.json \
  --verify-hashes
```

The script verifies the source package hashes and recomputes:

- exported Object-B dimensions and proposed U1 class dimension;
- U3 slew-state aliasing counterexample;
- U4 sufficient common-cost budget bounds from the four R452 references;
- U6 threshold bracket, interpolation and bisection counts;
- U8 M/D projector heterogeneity measures for all eight R405 profiles;
- U9 branch verdicts and the explicitly hypothetical IID binomial intervals;
- R446/R447/R449/R453/R456 decision-bearing recap.

## Test generic mathematical blueprints

```bash
python test_blueprints.py
```

`math_blueprints.py` contains plant-agnostic implementations for:

- stateful slew projection;
- exact ZOH fractional-delay splitting;
- complete closed-loop transfer sensitivity;
- finite-band energy derivative;
- mixed second-derivative probes;
- projector/resolvent commutator identity;
- elementary eigenvalue branch matching.

These routines do not reconstruct omitted Object-B matrices. They become directly usable after the project exports the missing arrays named in U1/U5/U6/U7.
