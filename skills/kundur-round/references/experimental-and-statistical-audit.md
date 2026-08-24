# Experimental and statistical audit

## Identification

- State the scientific unit: topology, operating point, disturbance, trajectory,
  seed, controller training run, or hardware run.
- State the estimand and its population: mean paired effect, median effect,
  failure probability, tail risk, worst case, or another target.
- Verify that resampling and uncertainty follow the dependence structure.
  Preserve pairing when controllers share a scenario; keep training seeds above
  trajectories in hierarchical designs.

## Prospective integrity

- Locate the prospective question, endpoint, disturbance bank, controller set,
  exclusion rules, thresholds, and stopping rule.
- Compare planned and executed sample counts, bootstrap budgets, tolerances, and
  analysis code.
- Classify amendments by timing and access to outcomes. Treat post-outcome
  changes as exploratory unless independently justified and transparently
  labeled.

## Comparisons

- Match baselines on observations, actions, actuator limits, training
  interactions, tuning effort, seeds, scenario bank, and deployment information.
- Include strong classical controls when the paper claims learning-enabled
  control value; include non-graph and centralized controls when attributing
  value to graph structure or decentralization.
- Separate absolute performance from incremental value over the strongest
  matched baseline.

## Endpoints and uncertainty

- Report physical endpoints alongside composite or reward metrics.
- Provide effect sizes and intervals, not only significance decisions.
- Audit multiple endpoints, subgroup reads, and optional stopping for multiplicity
  and selective emphasis.
- Report failure rates, guard violations, saturation, control effort, energy use,
  and tail measures when the claim concerns robustness, safety, or deployment.
- Distinguish descriptive small-cell subgroup reads from powered inferential
  claims.

## Missingness and validity

- Account for every registered case. Classify solver failures, divergence,
  protection trips, timeouts, and missing traces as outcomes or exclusions under
  the registered rule.
- Preserve invalid experiments in the record and prevent their directional
  estimates from becoming positive evidence.
- Inspect the final formal guard result, not only trajectory completion counts.
- Reconcile all headline numbers with the final analysis artifact and its
  provenance.

## Mechanism and generalization

- Require an intervention, ablation, or model-based test that distinguishes the
  proposed mechanism from plausible alternatives.
- Bound a mechanism result to the variables and regime actually interrogated.
- Require completely held-out systems, graphs, or topologies for zero-shot
  topology claims and report uncertainty over those held-out units.
- Treat cross-simulator, HIL, and field claims as separate evidence tiers.
