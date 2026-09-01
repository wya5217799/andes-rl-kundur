# Compact data digest

These values are copied from the machine-readable files included in the
archive. Use the JSON files for calculation and exact precision.

## Formal context

- Policies: 208 all-fresh final checkpoints.
- Endpoint-qualified: 121/208.
- Complete contract: 0/208.
- Policy-profile blocks: 832; every block fails both command RMS and TV limits.
- Command-only break-even multiplier: 97.6575 / 131.9193 / 140.2508
  (minimum / median / maximum).
- Median comparator-relative activity: M RMS 31.2256, D RMS 5.6923, M TV
  87.9674, D TV 83.4118.

## Projection attribution — representative policy, four profiles

| Profile | projected/raw M TV | projected/raw D TV | raw/direct M TV | raw/direct D TV |
|---|---:|---:|---:|---:|
| a | 0.418772 | 0.397106 | 161.281 | 145.312 |
| b | 0.444175 | 0.387567 | 317.801 | 279.008 |
| c | 0.426297 | 0.417262 | 232.386 | 201.657 |
| d | 0.380347 | 0.360651 | 229.582 | 187.320 |

Exact projector replay error and saved action-delta error are both zero.

## Previous-action input grid — 24 policies, profile a

- Channel-policy ratios: 48.
- Fixed-mean previous-input / actual raw-TV ratio:
  min 0.070983, median 0.143787, q95 0.201726, max 0.204618.
- 48/48 ratios are <=0.50; replay error is zero for all 24 policies.

This is conditional on the same recorded observations. It is not a plant or
training counterfactual.

## Quasi-static RMS grid — 24 policies x four profiles

- Blocks: 96; M/D ratios: 192.
- Constant-anchor / actual raw-RMS ratio:
  min 0.701488, q05 0.802484, median 0.958785, q95 1.072541, max 1.195156.
- Overall prevalence >=0.90: 73.4375%; prevalence <=0.50: 0%.
- M channel: median 0.915499; 56.25% >=0.90.
- D channel: median 0.987098; 90.625% >=0.90.
- Profile prevalence >=0.90: a 72.92%, b 75.00%, c 70.83%, d 75.00%.

## Reward temporal-order blindness — representative policy

Across profiles a--d, rearrangements with identical action row multisets keep
the registered action cost exactly unchanged while high/low combined TV ratios
range from 13.2202 to 18.4581. This identifies invariance of that cost term; it
does not identify the training effect of adding a TV term.

## Recursive fixed-previous intervention — representative policy

| Profile | TV intervention/actual | RMS intervention/actual | TV intervention/direct | RMS intervention/direct |
|---|---:|---:|---:|---:|
| a | 0.297380 | 1.066173 | 18.6304 | 7.6607 |
| b | 0.249946 | 1.029888 | 31.6810 | 8.3977 |
| c | 0.279827 | 1.115212 | 26.5011 | 7.5013 |
| d | 0.318564 | 0.983682 | 24.5509 | 6.5298 |

The negative-control raw and projected replays have maximum absolute error
zero. The intervention keeps observations frozen, reduces TV materially, but
does not approach the comparator-relative action contract and raises M-channel
RMS on every profile.
