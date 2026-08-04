# R295 consensus-time-scale probe protocol

This protocol is frozen before any R295 ANDES trajectory. It implements the
prospective R295 plan as a development-only mechanism probe.

## Fixed plant and controller contract

- Full nonlinear `AndesMultiVSGEnvV4Storage`, Toggler disabled.
- Four explicit local DAPI agents with independent integrals and power
  requests; ring-neighbour frequency and integral messages only.
- `Kp=2.0`, `Ki=0.2`, `Ks=1.0`, `dt=0.2 s`, 100 steps, zero M/D action.
- Identical ESD1 projection, power/ramp/current/SOC/energy limits and
  anti-windup across all arms.
- Sole treatment is `kc in {1,2,4} 1/s`.

## Development bank

The four cases are reused knowingly from R294 controller development and are
not held out: `k1/PQ_0/+1`, `k1/PQ_Bus15/-1`, `k2/PQ_1/+1`, and
`k2/PQ_Bus14/-1`. Their role is rapid fault finding. The Cartesian ordering
is scenario then gain, producing 12 jobs split deterministically across three
workers.

## Validity and decision

All 12 jobs must pass completion, finite telemetry, ANDES TDS/exit, storage
constraint, and vector-action guards. Invalid records make the entire stage
invalid and performance endpoints non-evidence.

Candidate-to-`kc=1` ratios use matched-bank means. A candidate passes iff
fast inter-area IAE is at most `0.99`, synchronization loss at most `1.01`,
each common mean endpoint at most `1.05`, and every individual common ratio at
most `1.10`. If both pass, choose the smallest fast-inter-area ratio, with an
exact tie resolved toward lower `kc`. No adaptive expansion is allowed.

Allowed conclusion: the selected consensus time scale is eligible for a new,
disjoint held-out confirmation on this fixed modified Kundur formulation.
Prohibited conclusions include neural or MARL value, distributed superiority,
topology generalization, stability, safety certification, and deployment.
