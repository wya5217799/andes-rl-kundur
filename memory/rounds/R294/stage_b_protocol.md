# R294 Stage-B protocol — full-DAE M/D/P trajectory authority

**Frozen before execution.**  This protocol does not revise the sealed Stage-A
thresholds or outcome.  It maps transient input authority on the full ANDES
DAE before any controller synthesis or neural training.

## Plant and bank

- Plant: `AndesMultiVSGEnvV4Storage`, default Toggler disabled, public
  `Model.set` path for the 7--8 tie-corridor `r/x` scaling.
- Horizon: 50 control steps at 0.2 s (10 s), after the environment's existing
  0.5 s initialization; probe active for the first 15 steps (3 s).
- Disturbances: `PQ_0`, `PQ_1`, `PQ_Bus14`, and `PQ_Bus15`, each at
  `delta_u=-1.0` and `+1.0`, under tie multipliers `k=1.0` and `k=2.0`.
  This gives 16 deterministic plant scenarios.
- Per scenario: one zero-input baseline plus paired positive/negative probes
  for each actuator `M`, `D`, and `P` in each coordinate `common` and
  `interarea`, giving 13 arms and 208 trajectories.

## Coordinates and probe budgets

Use the orthonormal rows

\[
q_c=\tfrac12[1,1,1,1],\qquad
q_a=\tfrac12[1,1,-1,-1],
\]

completed by the two within-area difference rows.  The signed probe is active
for 3 s and zero afterwards.

- `M`: coordinate amplitude 40 physical M units, so a common probe changes
  each device by `+/-20` around `M=200`.
- `D`: coordinate amplitude 40 physical D units, so a common probe changes
  each device by `+/-20` around `D=100`.
- `P`: requested coordinate amplitude 0.20 system pu, so a common probe
  requests `+/-0.10` system pu per device.  The existing BESS ramp, current,
  power, energy, and SOC projection remains active.

These amplitudes are independently safe engineering budgets, not
dimensionally equal inputs.  Cross-actuator comparisons are therefore
`budget-normalized authority`, not intrinsic gain or equal-energy optimality.

## Estimands

For every scenario, actuator, and coordinate, with coordinate-output traces
`y+`, `y-`, and matched baseline `y0`, define

\[
s(t)=\frac{y_+(t)-y_-(t)}{2},\qquad
e_{nl}=\frac{\lVert (y_++y_-)/2-y_0\rVert_2}
{\max(\lVert s\rVert_2,10^{-12})}.
\]

Record target-coordinate L2 gain, target peak, off-target/target L2 ratio,
the same quantities over the first 3 s, and `e_nl`.  Aggregate each actuator
by median and full range over all 16 scenarios.  An actuator is
`budget-relevant` for one coordinate only when its median target gain is at
least 25% of the largest actuator median for that coordinate.  This is a
screening rule, not a controller-performance claim.

Trajectory-local linearization is eligible only if median `e_nl <= 0.25` and
maximum `e_nl <= 0.50` for every retained actuator-coordinate pair.  Otherwise
the result is `TRAJECTORY-LINEARIZATION-NO-GO` over this domain and the next
model must retain stronger nonlinear/scheduled structure or narrow the domain.

## Validity and stopping rule

Every trajectory must complete exactly 50 steps with `TDS.test_ok`, system
`exit_code=0`, finite telemetry, no storage constraint violation, exact M/D
target execution, and projected P commands inside the sealed BESS contract.
Any failed trajectory is retained without retry and makes Stage B invalid.

After a valid authority map, stop before controller design.  The map may
select inputs for a richer LTV/LPV or reduced nonlinear controller, but it
cannot establish that any controller, distributed architecture, MARL method,
or deployment is superior.
