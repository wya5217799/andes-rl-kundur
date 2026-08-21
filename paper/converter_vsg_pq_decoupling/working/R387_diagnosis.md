# R387 strict failure diagnosis

## Scope and immutable symptom

The sole sealed R387 attempt remains immutable. Its formal analysis is
`ANALYSIS-INVALID`, not a scientific STOP. The diagnostic loop reads only the
create-only formal artifacts and never launches a replacement trajectory.

Red feedback command:

```powershell
$env:PYTHONUTF8='1'
@'
import json
from pathlib import Path
d = json.loads(Path(
    'results/research_loop/r387_regcv1_signed_authority_gate/formal_analysis.json'
).read_text(encoding='utf-8'))
print('feedback_classification=' + d['classification'])
raise SystemExit(d['classification'] not in {
    'REGCV1-SIGNED-AUTHORITY-PASS',
    'STOP-REGCV1-SIGNED-AUTHORITY',
})
'@ | python -
```

Observed red output: `feedback_classification=ANALYSIS-INVALID`, exit code 1.

## Ranked hypotheses and probes

1. **Classifier lifecycle mismatch** -- a captured trajectory that terminates
   after advancing but before 2.0 s is rejected as malformed instead of being
   represented as a native-solver scientific failure.
2. **Independent trace-schema mismatch** -- valid canonical JSON key ordering
   or native ANDES time-storage semantics do not satisfy a non-semantic
   classifier assumption.
3. **Action/reference mismatch** -- the commanded baseline or applied value is
   not the captured post-init REGCV1 reference.
4. **Source/object/diagnostic drift** -- provenance, structural mapping, or
   initialization evidence is malformed independently of the trajectory.

The per-arm integrity decomposition tested metadata, inventory, reference
schema and values, diagnostic rows, solver schema, action schema,
action-to-reference binding, and trajectory schema one field family at a time.
Only `trace_schema` failed in all 17 arms. Contract digest, source/object,
reference, diagnostic, solver-field, and action checks passed.

## Root causes

### 1. Mapping order was confused with bus identity

The create-only JSON writer canonicalizes dictionaries with `sort_keys=True`.
Consequently, the ten voltage-trace keys are read as
`1,10,2,3,4,5,6,7,8,9`. The sealed classifier required iteration order
`1,2,3,4,5,6,7,8,9,10`, even though the identities and all ten traces are
present. Mapping order is not physical or evidentiary identity.

### 2. Native stored time series omit the initialization sample

For every arm, the ANDES time-series store begins at the first integration
sample, `0.03333333333333333 s`; it does not contain a `t=0` row. The sealed
classifier requires the first stored time to equal zero and the stored-array
duration to equal 2.0 s. The runner recorded neither a separate full initial
signal snapshot nor an explicit `trajectory_start_time_seconds`, so the
missing initialization row cannot be reconstructed prospectively after the
attempt.

### 3. Premature native termination lacks a typed partial-trace branch

Eight arms advanced but terminated without convergence between
`1.026536619317691 s` and `1.990480459866156 s`. R387 defined scientific
sentinels for PFlow failure, TDS-init failure, and zero time advancement, but
not for an advanced partial trajectory ending before `tf`. Those arms retain
complete partial traces and `tds_converged=false`, yet the classifier rejects
them at integrity precedence instead of reaching the native-solver STOP check.

These are measurement/classification defects. None can be repaired inside the
sealed attempt or used to reinterpret its formal classification.

## Quarantined mechanism signal

The preserved traces are inspected only to decide whether a correction is
worth executing. The zero-step arm completed 2.0 s within all registered
electrical guards. Among the 16 nonzero arms, all 16 crossed the registered
voltage envelope; 10 crossed the current bound; 13 crossed the apparent-power
bound; six crossed the virtual-speed bound; and eight failed native
convergence. All 17 arms retained finite stored values, zero reported
initialization residuals, and zero clamped-limit rows.

This pattern is inconsistent with a harmless classifier-only false alarm. It
is consistent with the direct step exciting an unacceptable dynamic response
under the frozen REGCV1 card, but R387 cannot promote that pattern to a
scientific failure because its compound evidence record is invalid.

## Decision and green-loop target

R387 is not retried and supports no signed-authority, stability, or
decoupling claim. One separately planned and sealed successor may change only
measurement/classification integrity:

1. compare bus identity as the exact frozen set, independent of JSON order;
2. serialize explicit pre-run time and complete initial signal snapshots, then
   validate the native stored grid as the post-start samples;
3. admit an exact advanced-partial-trajectory sentinel with
   `tds_converged=false` as a scientific STOP candidate while keeping malformed
   or unexplained partial traces invalid.

The successor's regression loop must first fail on canonical JSON round-trip,
native first-sample timing, and advanced partial termination fixtures, then
pass without changing topology, device model/card, step magnitude, horizon,
electrical limits, authority thresholds, arm order, or no-training boundary.
