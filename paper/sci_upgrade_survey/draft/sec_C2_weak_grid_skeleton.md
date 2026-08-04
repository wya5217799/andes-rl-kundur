# C2 weak-grid validation — argument contract

Status: PI-review contract, not manuscript prose. This file specifies what a
future section may argue; it deliberately contains no copied result values.

## Authority and role

- Story role: validation boundary for the C1 allocation-mechanism spine.
- Research decision: `paper/sci_upgrade_survey/REPORT.md` §7.
- Honesty boundary: `paper/sci_upgrade_survey/DIFFERENTIATION_MEMO.md` §4.
- Evidence authority: CLM-0630, CLM-0640, CLM-0645, and CLM-0650, followed by
  their registered feeds and result locators.
- Drafting rule: claim card first, feed second, machine result only when exact
  values are needed. This contract is never a numerical source.

## Paragraph map

| Paragraph | Purpose | Allowed evidence | Required boundary |
|---|---|---|---|
| P1 | Motivate the grid-strength validation and define the declared proxy. | CLM-0630; R283 Frozen setup | Corridor impedance scaling is a proxy, not converted SCR. |
| P2 | Establish the measured electrical-strength gradient. | CLM-0630; R283 Observations/Conclusions | Same identified branch; scanned range only. |
| P3 | Explain the observed change in mapping shape and useful direction. | CLM-0630; R283 Conclusions | Empirical structure, not a global monotone law or mechanism proof. |
| P4 | Bound the inertia-axis result by the mapped identification zone. | CLM-0630, CLM-0640; R283/R285 Conclusions | Flagged cells are unmeasured, not negative evidence. |
| P5 | Give the minimum identification and guard defense needed for reproducibility. | CLM-0630, CLM-0640; R283/R285 setup and guards | Do not turn the screen into a physical theory. |
| P6 | State frozen-controller time-domain survival under the declared proxy. | CLM-0645, CLM-0650; R286/R287 Conclusions | Zero training; one controller family, bank, topology, and tested boundary. |
| P7 | Close with non-claims and transfer limits. | All four claims; all feed Limits sections | No collapse threshold, retraining, topology transfer, cross-simulator, HIL, or sustained restoration claim. |

## Evidence locators

- R283 feed: `paper/sci_upgrade_survey/reports/R283.md`; machine sources:
  `results/r283_strength_sweep/summary.json` and `branch_analysis.json`.
- R285 feed: `paper/sci_upgrade_survey/reports/R285.md`; machine sources:
  `results/r285_hybridization_map/summary.json` and `zone_analysis.json`.
- R286 feed: `paper/sci_upgrade_survey/reports/R286.md`; machine source:
  `results/r286_weak_grid_td/weak_tie_summary.json`.
- R287 feed: `paper/sci_upgrade_survey/reports/R287.md`; machine source:
  `results/r287_weak_grid_stress/weak_tie_summary.json`.
- Exact wording and numbers must be re-read from these authorities at drafting
  time; they must not be reconstructed from memory or copied into navigation.

## Figure and table contract

- W1: strength sensitivity across the two declared axes. Show invalid
  identification cells without inventing values.
- W2: measured allocation-response shape across corridor settings. Keep the
  scanned-range qualifier visible.
- T2: identification validity and guards, with flagged cells distinguished
  from measured effects.
- T3 or compact inline result: frozen-controller endpoint effects and retained
  value across the tested corridor settings.
- Figures consume the registered machine results above; this file provides
  layout intent only.

## Wording constraints

Allowed:

- “within the scanned range”;
- “declared corridor-impedance-scaling proxy”;
- “identification boundary”;
- “frozen centralized controller” and “through the tested boundary”.

Forbidden:

- converting the proxy into SCR or penetration values;
- “allocation creates damping” or an unrestricted monotonic law;
- assigning a physical mechanism to flagged identification cells;
- treating survival as a collapse threshold or weak-grid retraining result;
- topology generalization, cross-simulator transfer, HIL validation, or
  sustained common-frequency restoration.

## PI decisions before prose

1. Use separate W1/W2 figures or one two-panel figure?
2. Keep the identification-zone map in the main text or an appendix?
3. Keep P5 here or move it to a shared reproducibility section?

Formal prose, LaTeX, and polished figures remain blocked until these decisions
and the user’s explicit drafting authorization are present.
