# ADR-0013: Bind candidates before long-horizon validation at measured host capacity

- **Status:** Accepted
- **Date:** 2026-08-04
- **Deciders:** repository owner and Codex research workflow
- **Related:** ADR-0008, ADR-0012, Q-0089, R340

## Context

The model-first manuscript line reached a fresh nonlinear predictor gate. The
candidate construction depends on equilibrium Jacobians at the declared
operating point, so its exact artifact hash cannot be known before the
construction computation runs. Combining construction and validation in one
opaque command would allow a model to be changed after a validation trajectory
was visible and would violate the candidate-before-data order required by
Q-0089.

The host exposes 16 physical cores and 32 logical processors. R339 already
demonstrated 16 overlapping single-threaded ANDES processes without swap. A
short 25-step, 66-record bank would finish too quickly to test long-tail decay
and would make momentary low CPU readings easy to misinterpret as unused
capacity. Artificial duplicate jobs, empty loops, or identical deterministic
replicates would raise utilization without adding evidence.

## Decision

Fresh predictor validation uses two create-only sealed phases:

1. Construction extracts the prospectively fixed input-aware descriptor at
   each declared validation point, builds the unchanged order-12 realization,
   persists the candidate artifact, and stops without a nonlinear trajectory.
2. Validation creates a new seal that binds the exact candidate hash and the
   complete trajectory inventory. Only then may nonlinear trajectories start.

Neither phase permits retry or outcome-driven repair. A construction failure
stops before validation. A validation failure is retained as evidence.

Whole-host ANDES work uses one single-threaded Python process per measured
physical core: one parent plus fifteen forked workers. The 32 logical
processors are not assumed to provide 32 independent simulation cores because
they share physical execution resources. A different budget requires a new
measured capacity record; repository constants do not decide it.

R340 keeps the 66 unique, prospectively declared records but extends every
record to 1000 samples at 0.2 seconds, or 200 seconds. The disturbance waveform
is unchanged and zero-padded; the added interval tests model decay and slow
drift. The R339 candidate construction still uses exactly 25 Markov samples,
so duration is not selected from the validation outcome. Based on measured
R336 per-record cost, the advance wall-clock estimate is 11--15 minutes at 16
processes.

Full per-step audit rows are written as separate create-only compressed JSON
artifacts and bound by the run manifest. The parent retains the full-resolution
prediction inputs and outputs but not duplicate rich trace dictionaries. This
preserves evidence while avoiding avoidable memory and inter-process-transfer
pressure.

## Consequences

- The candidate hash is independently auditable and necessarily predates all
  fresh nonlinear records.
- Sustained CPU use comes from registered scientific trajectories, not
  synthetic load or duplicate deterministic evidence.
- The longer horizon can expose slow drift or insufficient modal decay that a
  five-second record cannot show.
- The experiment remains a predictor test only. It authorizes no controller,
  distributed-agent, learning, stability, safety, topology-generalization, or
  paper-title claim.
- Formal execution takes materially longer and creates more trace data; gzip
  trace separation and manifest hashing are therefore mandatory.
