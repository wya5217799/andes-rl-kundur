# R339 advisory package admissibility

## Identity and inventory

- ZIP: `C:/Users/27443/Downloads/input_bridge_resolution_package.zip`
- ZIP SHA-256: `fbe43205abc8f9f03ba1dff327f281b54322cc49fba08b8f0176f52e307afe41`
- User-provided extracted root:
  `C:/Users/27443/Downloads/input_bridge_resolution_package/input_bridge_resolution_package`
- Inventory: 15 files: two reports, one README, one reproduction script,
  nine tabular/JSON analysis outputs, and two exploratory NPZ models.
- The extracted files match the files inspected from the ZIP extraction.

The reproduction script is not self-contained. It hard-codes
`/tmp/input_bridge_diagnostic_bundle_extracted/input_bridge_diagnostic_bundle`
as its source root and `/mnt/data/input_bridge_analysis_work` as its output,
but the required source bundle is absent from both delivered forms. The saved
CSV, JSON, and NPZ files can be inspected, but the claimed recomputation cannot
be replayed from this package alone.

## Bounded numerical checks

Both exploratory models contain finite arrays with the declared joint shape:
`A` 12x12, `Bu` and `Bd` 12x4, `C` 4x12, and `Du` and `Dd` 4x4. Their reported
discrete spectral radii recompute to 0.9778751386 at HS0 and 0.9785446897 at
HS1.

The package reports for joint order 12:

| Point | maximum NRMSE | maximum peak residual | control Markov NRMSE |
| --- | ---: | ---: | ---: |
| HS0 | 0.02828935 | 0.03110470 | 0.01910007 |
| HS1 | 0.03062045 | 0.03342252 | 0.02457897 |

Order 11 is materially worse (maximum NRMSE 0.17104872 at HS0 and 0.12814384
at HS1). The order-4 residual does not transfer cleanly between the exposed
points (cross-point maximum NRMSE 0.15120706 and 0.19323490). These values are
advisory only because the package selected among orders 8 through 14 after
examining both points.

## Review disposition

- BR-01, major: the package is not independently reproducible from its own
  contents.
- BR-02, blocker for validation claims: HS0 and HS1, the candidate orders, and
  both saved models are exposed development material.
- BR-03, blocker for direct adoption: the empirical realization is not a full
  installed-DAE derivation and therefore does not establish the physical input
  map or plant modes.
- BR-04, blocker for direct adoption: the repository records output after each
  held interval, requiring the post-step sampled realization frozen in the
  R339 plan.
- BR-05, major: input coordinates require physical-energy normalization before
  joint ERA so unequal basis norms do not choose the order implicitly.

Verdict: **QUALIFY**. Adopt the independent control/load input concept and use
order 12 as a prospectively fixed development candidate. Do not import the
saved models or reported metrics as formal evidence. First derive the full
descriptor model from the installed plant, verify its state reduction and
finite-difference input columns, and replay only the already exposed records.
Only a passing R339 result may authorize a separately sealed fresh validation
round.
