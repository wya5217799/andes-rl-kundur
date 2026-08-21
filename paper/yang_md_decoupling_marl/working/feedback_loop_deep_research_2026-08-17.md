# Feedback-loop deep research — protocol sharpening for B1 / R417 / B3 (2026-08-17)

> Bounded deep-research pass (three parallel literature-scout perspectives,
> existence-verified citations only) feeding the post-program feedback
> loop.  Decisions derived here are recorded in
> `working/gate_calibration_log.md`; nothing here changes the frozen
> scientific contracts by itself.

## Perspective 1: RL control under actuator slew/saturation (B1 protocol)

- Omitting the previous executed action from the policy state is a
  recognized failure mode, best framed as induced partial observability
  (state-omission/actuator-dynamics class).
- Canonical repairs: state augmentation with the last *executed*
  (post-projection) action; differentiable projection (SAC tanh);
  action-smoothness regularization; action-Jacobian penalty.
- Verified anchors: Sauté RL (state-augmentation repair, ICML 2022),
  SAC (ICML 2018), smooth-exploration (CoRL 2021),
  action-smoothness-regularization (arXiv:2407.04315),
  action-Jacobian penalty (arXiv:2602.18312), time-delay RL survey
  (arXiv:2602.00399), DRQN (AAAI 2015).
- Protocol implications (adopted for B1): (1) augment the actor state
  with the previous *executed* (post-slew) action — one step is the
  sufficient statistic for a first-order rate limiter; (2) align
  target-action semantics so critic and policy optimize the same
  post-projection quantity (the load-bearing change beyond augmentation);
  (3) record slew-saturation rate, execution-mismatch gap, and
  guard-failure rate as diagnostics.
- Dissenting view: augmentation alone is usually insufficient; if the
  critic still evaluates raw outputs, the value estimate stays biased;
  tanh squashing carries near-saturation gradient bias.  B1's registered
  single factor therefore keeps augmentation + target alignment together.

## Perspective 2: fixed-gain bandpass damping under plant perturbation (R417)

- Reporting a fixed-gain controller's pass/fail table across
  plant-parameter perturbations is defensible conference practice and
  exceeds the common norm (most VSG damping works report only a nominal
  tuned gain); the parametric-sensitivity tradition explicitly supports
  the failing cell being retained and reported.
- Adaptive/scheduled gain (alternating inertia, self-tuning VSG, adaptive
  NN damping) is the field's *remedy* for insufficient fixed-gain
  coverage — not a prerequisite for the breadth table.
- Hard constraint adopted: the second gain must have been frozen and
  disclosed *before* the unseen perturbation blocks were scored, and a
  third gain on the same held-out blocks would be test-set search.
  K=4.0 satisfies the disclosure condition (R408, 2026-08-15, before the
  R415 blocks were frozen 2026-08-17); after R417 the three blocks are
  closed to any further gain evaluation (calibration log).
- Verified anchors: Barcellona/Huo band-pass damping (SPEEDAM 2016),
  D'Arco & Suul parametric sensitivity (IJEPES 2015), Alipoor/Miura/Ise
  alternating inertia (JESTPE 2015), Torres & Lopes self-tuning VSG
  (IEEE TEC 2014), Rosso et al. GFM review (IEEE OJIA 2021), Bediako &
  Hosseinipour adaptive NN damping (EPSR 2025), comparative damping study
  (EPE 2019).

## Perspective 3: failure-attribution diagnostics (B3 protocol)

- Norm: full per-seed return/guard curves with aggregate reporting
  (IQM / stratified bootstrap CIs), never a cherry-picked best run
  (Henderson AAAI 2018; Agarwal et al. NeurIPS 2021; Colas et al.
  arXiv:1806.08295; Islam et al. arXiv:1708.04133).
- Ranked diagnostics for attribution: (1) per-seed full curves; (2)
  Bellman residual / TD-error magnitude and trend (TD3 overestimation
  class, Fu et al. ICML 2019); (3) per-module gradient norms (actor vs
  critic); (4) replay/buffer coverage (TD-error distribution + visitation
  entropy).
- Protocol implication adopted for B3: pre-register the rerun as
  confirmatory evidence — bit-comparable config and seeds, the four
  diagnostics declared as primary endpoints with a pre-specified readout
  rule mapping each pattern to a failure class (optimization /
  representation / reward-mismatch / exploration) before launch.

## Loop decisions (registered)

1. R417 (K=4.0 breadth on the three A4 blocks) proceeds; after it, the
   three blocks are closed to further gain evaluations.
2. B1 proceeds next with the registered slew-state single factor
   (augmentation + target alignment); diagnostics per Perspective 1.
3. B3 follows with the Perspective-3 diagnostic set, pre-registered
   readout rules.
