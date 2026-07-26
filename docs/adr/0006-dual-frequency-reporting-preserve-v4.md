# ADR-0006: Expose ANDES physical frequency while preserving frozen V4 semantics

- **Status:** Accepted
- **Date:** 2026-07-24
- **Deciders:** repository owner and R261 correctness audit
- **Supersedes:** none
- **Related:** R89 / CLM-0171, ADR-0002, ADR-0004

## Context

R89 established that the ANDES `kundur_full.xlsx` case encodes
`GENROU.fn=60 Hz` and `Line.fn=60 Hz`, while the project contract and V4
control code use `FN=50 Hz`. V4 consequently reports
`freq_hz = omega_pu * 50` even though the simulator's physical base is
60 Hz. Absolute frequency deviations stored in legacy traces are therefore
smaller than physical deviations by `50/60`.

R261 reproduced this against the live WSL environment
(`andes==2.0.0`), not only the cached R89 JSON:

- ANDES GENROU nominal frequency: 60 Hz
- ANDES Line nominal frequency: 60 Hz
- project `KUNDUR.fn`: 50 Hz

Changing V4's `FN` or mutating the case before `ss.setup()` would alter the
meaning of historical observations, rewards, checkpoints, and evaluation
numbers. Leaving the mismatch visible only as an `xfail` would preserve
reproducibility but allow new trace consumers to continue confusing the
legacy 50-Hz reporting scale with physical Hz.

## Decision

V4's existing control and training semantics remain frozen:

- `FN`, `_omega_scale`, rewards, observations, `freq_hz`, `delta_f_es`,
  `max_df`, and `cum_rf` keep their historical 50-Hz basis.
- Historical checkpoints and stored result JSON are not rewritten.

The environment now detects the simulator's uniform nominal frequency after
every system build and exposes a second, explicit physical reporting path:

- `andes_nominal_frequency_hz`
- `freq_hz_physical`
- `max_freq_deviation_physical_hz`
- `frequency_calibration_mismatch`

Canonical trace generation preserves both bases and labels the basis used by
legacy metrics:

- `control_nominal_frequency_hz`
- `andes_nominal_frequency_hz`
- `frequency_reporting_basis = "legacy_control_hz"`
- `metric_frequency_basis = "legacy_control_hz"`
- per-step `freq_hz_physical` and `delta_f_physical_hz`
- top-level `max_df_physical_hz`

Any paper comparison using absolute Hz must either use the physical fields or
explicitly say that it is reporting the frozen legacy-control basis. Switching
the canonical score to physical Hz requires a separate re-baselining round and
must not mix new scores with historical 11-axis numbers.

## Alternatives considered

### A. Override ANDES `GENROU.fn` and `Line.fn` to 50 Hz inside V4

Rejected for V4: this changes simulator dynamics and silently invalidates the
checkpoint/result lineage. A corrected 50-Hz plant remains a valid future
environment-version experiment.

### B. Change `AndesBaseEnv.FN` from 50 to 60

Rejected: `FN` participates in observations, reward units, and historical
evaluation. This would be more than a reporting fix.

### C. Keep only the deliberate `xfail`

Rejected: an audit-only warning does not travel with generated trace data.
Downstream consumers need machine-readable provenance.

### D. Immediately make physical Hz the canonical 11-axis input

Deferred: scientifically preferable for future paper comparison, but it
requires re-scoring/re-running all baselines under a versioned metric and is
outside the correctness-only R261 gate.

## Consequences

### Positive

- New traces are self-describing and contain the physically calibrated values.
- V4 training and checkpoint compatibility remain bit-identical.
- A future physical-metric rebaseline can use stored R261+ traces without
  rerunning ANDES.
- Mixed-basis paper claims become detectable from JSON metadata.

### Negative

- Trace schema carries two frequency representations.
- Legacy headline metrics remain on the 50-Hz control basis until a dedicated
  rebaseline is completed.
- Consumers must choose a frequency basis deliberately.

## Verification

- Live WSL regression:
  `test_frequency_metadata_exposes_andes_60hz_without_changing_legacy_v4`
- Trace-schema regression:
  `test_run_scenario_records_legacy_and_physical_frequency_bases`
- Historical V4 no-control frequency traces remain bit-identical in
  `test_v4_env_regression.py`.
