---
round: R271
state: completed
opened: '2026-07-25'
closed: '2026-07-25'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R271 plan — equation and terminal-trace audit of actuator sufficiency

**Status**: ACTIVE
**Opened**: 2026-07-25
**Driver**: Q-0033 after the R270 modal attainability split
**Parents**: CLM-0555, CLM-0560
**Prospective claim slot**: CLM-0565

## TL;DR

Audit whether the current model can support a credible common-frequency
restoration claim.  Combine exact repository/ANDES equations with R268/R270
early and terminal trace windows.  Run no new simulation, training, or model
change.  The result must choose between existing actuator authority and a
model/actuator correction; it may not recommend another neural algorithm.

## Falsifiable objective

Determine whether material common-mode frequency restoration in the current
modified Kundur model structurally requires an explicit active-power or
secondary-frequency actuator beyond virtual inertia and damping.

## Methodology

### Source and equation audit

Verify machine-readably:

1. the environment action is exactly two components, normalized delta-M and
   delta-D;
2. `step()` changes only live `GENCLS.M` and `GENCLS.D`, not VSG `tm`, `pref`,
   `p0`, or an active-power command;
3. the installed ANDES `GENBase` speed equation is
   `M*domega/dt = tm - te - D*(omega-1)`;
4. at equilibrium `domega/dt=0`, so M disappears, while finite D remains only
   as proportional speed-error torque and cannot force zero error under a
   nonzero sustained imbalance without a changed power setpoint/integral
   mechanism;
5. each VSG is a `PV + GENCLS` proxy with fallback setpoint `tm0`; IEEEG1
   governors are attached to original `GENROU`, not to the four VSG `GENCLS`
   units;
6. the active V4 VSG path contains no storage energy/SOC/headroom state or
   constraint and no independent active-power action.

Record repository source hashes, installed ANDES version, and hashes for
`genbase.py` and `gencls.py`.

### Existing-trajectory audit

Use only immutable R268 droop traces and R270 candidate traces/summary.
For every scenario calculate physical common/differential metrics over:

- active window: first 15 recorded steps;
- terminal window: final 25 steps (5 seconds);
- terminal sample.

Report:

1. selected R270 library oracle versus droop;
2. `common_M_pos` versus droop;
3. `common_D_pos` and `common_D_neg` versus droop;
4. M/D parameter values before and after the scheduled residual ends;
5. VSG electrical-power (`P_es`) differences as measured output, explicitly
   not mislabeled as an independent command or energy state.

Use the same 2% materiality threshold as R270.  No window, controller, or
threshold may be changed after calculating results.

## Pre-registered outcomes and decision gate

### MODEL-CORRECTION-REQUIRED

All source/equilibrium checks pass, R270's full-horizon joint IAE gate remains
failed, and the terminal-window/common terminal-sample improvement of the
outcome-seeing selected oracle remains below 2% even though its differential
or safety improvement is at least 2%.

Interpretation:

- M/D is retained only for fast transient/safety shaping;
- exact sustained restoration requires a power-balance/secondary mechanism;
- the current GENCLS proxy is insufficient for a credible storage/VSG energy
  control claim because it has no commanded power/energy state or headroom
  accounting;
- do not implement a new action until a physically sourced converter/storage
  model, power rating, energy capacity, SOC bounds, ramp/lag, and classical
  secondary-control baseline are frozen.

This closes Q-0033 as a model/actuator correction and ends the current
automatic experiment sequence.

### EXISTING-AUTHORITY

Any source hypothesis is false, or an existing admissible M/D direction
provides at least 2% terminal common-mode improvement without a power-setpoint
channel.  Route the next work to the exact existing authority/timescale
mechanism; do not add an actuator and do not reopen a broad search.

### INVALID

Missing/drifting source or traces, non-finite data, wrong 15/25-step windows,
or endpoint-identity failure.  Repair only integrity and rerun the identical
offline audit.

The audit is structural/development evidence, not a stability proof or a
general impossibility theorem.

`cum_rf_total` is reported only as historical differential-mode context;
`geo` is not used.  No paper or figure output is permitted.

## Asset protection and scope limits

- Add one offline audit script, one focused test file, and machine-readable
  results.
- Do not change V4, ANDES models, actions, rewards, agents, training, R268-R270
  traces, paper metrics, manuscript files, or figures.
- Do not run ANDES, train, browse for post-hoc component ratings, or invent
  power/energy limits absent from the current sources.
- Preserve the distinction between a measured electrical-power output and a
  controllable energy-limited storage input.

## Verification

- `python memory/tools/round_preflight.py R271 --json`;
- focused actuator-audit tests;
- `python -m pytest tests -q`;
- run the formal audit in WSL with the recorded ANDES installation;
- `python memory/tools/dual_metric_lint.py --claim CLM-0565`;
- `python memory/tools/validate.py`;
- `python memory/tools/render.py`.

## Planned outputs

- `scripts/audit_actuator_authority.py`;
- `tests/test_actuator_authority_audit.py`;
- `results/r271_actuator_authority_audit/`;
- CLM-0565, Q-0033 update, R271 verdict;
- no new ANDES trajectory, training, model, manuscript, or figure.

## Cross-references

- CLM-0555: measured R270 transient/common-mode separation.
- CLM-0560: stop learned M/D-only development pending actuator audit.
- Q-0033: current structural question.
- `docs/research/2026-07-25_project_value_and_publication_strategy.md`:
  pre-existing warning that the project lacks an energy/headroom/SOC contract.
