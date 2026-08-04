# R294 Stage C — fast coupling-aware controller development

This is a prospective, outcome-aware **development** protocol written after
R294 Stage A and Stage B.  It does not modify either sealed stage and cannot
support a paper-facing efficacy claim.  Its purpose is to find controller-law
failures cheaply before any compact frozen comparison.

## Evidence-driven design choice

Stage A rejected hard common/differential decoupling and the coarse static
four-axis LPV interpolation.  Stage B found active power to be the dominant
budget-normalized common and inter-area actuator and found trajectory-local
linearization eligible.  Therefore this development step uses independent
ESD1 active-power requests only and explicitly retains common/differential
coupling.  It does not claim that LPV-MPC, DMPC, neural control, or global
decoupling has been validated.

The initial deterministic law is deliberately simpler than MPC:

- `equal_sharing_pi`: one common-frequency PI request repeated across all
  four devices; this is the scalar-action baseline.
- `central_vector`: joint four-frequency observation, one common integral,
  global mean/differential projection, and four independently projected
  active-power requests.
- `distributed_dapi`: each physical device uses its own frequency, its two
  declared ring neighbours, and neighbour-coupled integral states; it emits
  its own active-power request without output aggregation.

All arms share `Kp=2.0 system-pu/(Hz device)`, `Ki=0.2
system-pu/(Hz s device)`, the same 0.2 s sample time, the same ESD1/BESS
projection, and zero M/D modulation.  Vector arms test `Ksync={0,1.0}`;
distributed arms fix the integral-consensus gain at `1.0 1/s`.  This is a
small mechanism screen, not a gain optimization claim.

## Fast bank and precommitted stopping rule

The development bank contains exactly four high-information cases and five
arms, for 20 retained trajectories of 100 steps each:

1. `k=1, PQ_0, delta_u=+1`;
2. `k=1, PQ_Bus15, delta_u=-1`;
3. `k=2, PQ_1, delta_u=+1`;
4. `k=2, PQ_Bus14, delta_u=-1`.

`k` is the already declared tie-impedance strength proxy within this modified
Kundur plant.  This bank does not establish multi-topology generalization.

For each architecture, a gain is eligible only if all four trajectories are
complete and finite, have zero storage-constraint violations, and relative to
the matched equal-sharing PI arm:

- no individual scenario worsens mean-frequency IAE, worst-bus peak, or
  maximum absolute RoCoF by more than 5%;
- the mean normalized synchronization-loss ratio is at most 0.98; and
- the mean fast inter-area IAE ratio is at most 0.98.

Among eligible gains, select the smallest geometric mean of the two
differential ratios.  If no distributed gain is eligible, stop and diagnose
the law; do not enlarge the bank or train a neural policy.  If both
architectures identify an eligible candidate, freeze those gains in a new,
compact, held-out controller-validation protocol.  Development results may
choose that later protocol but may never be pooled with it.

## Identifiability boundary

`equal_sharing_pi` versus either vector arm estimates action-space plus
coordination value.  `central_vector` versus `distributed_dapi` compares the
executed joint-information and neighbour-information formulations; it does
not isolate a universal architecture effect.  A result cannot support
"multi-agent control is superior" or any MARL claim.  It can only identify a
valid deterministic genuinely distributed baseline and a candidate control
law for later frozen evaluation.
