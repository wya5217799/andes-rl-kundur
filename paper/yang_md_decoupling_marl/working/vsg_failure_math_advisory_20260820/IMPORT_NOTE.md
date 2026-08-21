# VSG failure-math advisory — import and disposition

## Scope and integrity

- Source: `C:\Users\27443\Downloads\vsg_math_advisory_markdown_20260820`
  (Markdown-first bundle of `gpt_pro_math_pack_20260820.zip`).
- Imported 2026-08-21 for the fixed-title ICEMS 2026 manuscript line
  `yang-md-decoupling-marl` (camera-ready 2026-09-07).
- Role: advisory mathematical review of the failure mechanisms left open by
  the execution-complete program (R398–R441). Design aid, not authority.
- Source-hash check (repo-side): 95/96 files match the repository exactly;
  the single mismatch is the live `manuscript/manuscript.md` (expected drift
  for an actively edited document). All sealed `results/research_loop/*`
  and source files match bit-for-bit.
- Self-verification (bundle QA): 96 source hashes, 171 sealed-JSON entries,
  225/225 evidence rows rebuilt, C1 HYPOTHETICAL dual example exact.

## Three-way intake disposition

### 1. Algebraic identities — VERIFIED (repo-side)

Probe `probes/vsg_failure_advisory_algebra_verify.py` re-derives each identity
independently; 8/8 PASS:

| Identity | Check |
|---|---|
| P1.1 log-sensitivity decomposition (quotient rule) | symbolic, diff = 0 |
| P1.2 fixed-controller scalar-loop sensitivity `S dlogP` | symbolic, diff = 0 |
| P2.1 integer-delay sensitivity ratio | numeric, gap 7.8e-10 |
| P2.2 infinitesimal delay direction | numeric, gap 4.3e-9 |
| P3.1 index-1 DAE Schur channel `B_{u,r}=f_u-f_y g_y^-1 g_u` | numeric IFT, gap 1.4e-10 |
| P3.2 zero first-order M/D authority at synchronous balance | symbolic, exact 0 |
| M1 projected-dual ceiling-persistence law | numeric |
| M2 twin-min pessimistic (signed) bias | numeric, E[min] < Q |

These exact identities are usable as conditional statements. They do NOT, by
themselves, identify any empirical cause (gain/phase margin, delay margin, or
the actual ANDES `B_{u,r}`).

### 2. Mechanism predictions M1–M5 — sealed facts supported; causal attribution undecidable

Observable matrix registered at `verification/m_observable_matrix.md`
(machine-readable; each row names sealed/new file, field, support and refute
directions).

| id | Sealed-fact verdict | Causal-attribution verdict |
|---|---|---|
| M3 | supported (CD message sign negative, SAC positive, R410/R431 sealed) | undecidable (finite-learning vs information needs NEW nested-class intervention) |
| M5 | supported (all four winners are the constant schedule (3,3); endpoint gain paid by action stress, R441 sealed) | undecidable (Pareto law / lower-stress winner needs NEW_ALL_CANDIDATE_GUARD_TABLE) |
| M4 | supported (R436 residual SAC shows no learning increment, endpoint within <0.005 of anchor) | undecidable (identity-local-optimum needs NEW_SYMMETRIC_RESIDUAL_PROBE + Hessian) |
| M1 | supported (R425/R427 multiplier ceiling with positive residual, consistent with the ceiling law) | undecidable (infeasibility vs optimization needs NEW_REGISTERED_CAP_SWEEP / bounded-class certificate) |
| M2 | supported (R427 normalization reduces critic growth and stops guard failures) | undecidable (common-channel-specific causation needs NEW_HEAD_SPECIFIC_DIAGNOSTIC + factorial intervention) |

The M-tier causal predictions are **not-pursued** in the camera-ready window:
they target the journal extension and need new registered experiments. The
observable checklist is ready to be dropped into a successor round plan's
`## Theory intake` section.

### 3. Paper-grade propositions P1/P2/P3 — conditional propositions, four-proof assessment

| Proposition | Self-contained proof | repo-side verification | Assumption boundary | Model-theory gap | Verdict |
|---|---|---|---|---|---|
| P1.1/P1.2 ratio-sensitivity | yes (quotient rule + loop) | symbolic PASS (probe) | yes (differentiable, positive energies) | yes (complex loop not measured) | **conditional PASS** |
| P2.1–P2.3 delay law | yes (sensitivity def) | numeric PASS (probe) | yes (scalar loop, integer delay) | yes (L0 not measured; endpoint != stability) | **conditional PASS** |
| P3.1/P3.2 DAE authority | yes (implicit function theorem) | symbolic/numeric PASS (probe) | yes (index-1, synchronous balance) | yes (actual ANDES Jacobians not supplied) | **conditional PASS** |

The exact identities and conditional statements pass the four-proof bar and may
enter the manuscript as **conditional propositions/lemmas** with the advisory's
bounded wording (`report/paper_ready_paragraphs_P1_P3.md`). The *empirical
instantiations* — P1 gain/phase margin, P2 numeric delay margin, P3 the actual
`B_{u,r}` of the implemented ANDES object — remain unresolved: each needs new
sealed measurements (complex response export, same-bank delay sweep, DAE
Jacobian / finite-difference) and are marked HYPOTHETICAL by the advisory.

### 4. C1 controller-class certificate — design aid only (construction complete)

The offline construction (`tmp/yang_md_decoupling_marl/c1_youlas_sls_certificate.md`,
719 lines) fully derives the class-limited certificate route: stable FIR-Youla
(DCF) / FIR-SLS response parameterization with internal-stability guarantee,
affine finite-window energy constraints as second-order-cone constraints, and a
common-slack phase-I SOCP whose certified positive dual bound `delta > 0` proves
infeasibility for the exact named class. The conclusion is **procedural**: a
valid route exists, but **no instantiated project certificate** — the minimal
supplying experiment is a linearization-and-lifting run (export DAE Jacobians +
active-mode log, discretize once, verify baseline + DCF/SLS identities, solve
the conic phase-I, export the primal-dual certificate), which overlaps the R446
P3 DAE-Jacobian export. No controller-class impossibility claim may enter the
manuscript without a verified factorization, exact class, and positive
dual/Farkas certificate on the frozen response map.

## Manuscript disposition

Usable in the camera-ready window (after normal evidence audit):

- P1 ratio-sensitivity identity + "relative-energy failure" wording.
- P2 integer-delay identity + "endpoint failure, guards pass" wording.
- P3 index-1 DAE Schur channel as a conditional lemma + the finite-difference
  recipe (contribution: turns a limitation paragraph into a measured claim,
  once executed).

Must NOT enter the manuscript:

- any gain/phase-margin, delay-margin, or `B_{u,r}`-is-zero claim for the
  implemented object;
- message-is-harmful or time-variation-is-necessary claims;
- multiplier-ceiling = policy-class infeasibility;
- critic divergence = sole cause of the common gap;
- any controller-class impossibility statement.

## Data gaps (from `06_LIMITATIONS_AND_MISSING_QUANTITIES.md`)

Complex candidate/reference responses and loop transfer (P1/P2); equilibrium
DAE Jacobians or converged centered differences (P3); residual/Hessian probes
(M4); head-specific critic diagnostics (M2); per-candidate guard tables (M5);
a verified Youla/SLS factorization and response matrices (C1).

## Resolution update 2026-08-21 — P3 structural authority

Offline code-structure analysis (`tmp/yang_md_decoupling_marl/p3_dae_authority_code_analysis.md`,
scratch lane, no WSL run) confirms both P3.2 hypotheses hold for Object A as
implemented:

- `g_u = 0` structurally: no GENCLS algebraic residual (Id/Iq/vd/vq/tm/te/vf/
  Pe/Qe/psid/psiq/bus P-Q) references M or D; no COI/COI2 device is
  instantiated, so no service-level M/D reduction exists.
- `f_u = 0` at balance: M/D enter only the VSG's own swing row (M as the
  `t_const`, D in `-D(omega-1)`); at the synchronous power-balanced point
  `omega=1, tm=te` both `df_omega/dM = -f_omega/M` and
  `df_omega/dD = -(omega-1)/M` vanish.

Therefore `B_{u,r} = f_u - f_y g_y^-1 g_u = 0` at the registered equilibrium,
**structurally**. This is now also a **sealed numerical measurement** (R446,
CLM-1390, trust V): the finite-difference Schur fold of all 8 M/D columns over
h ∈ {1e-2, 1e-3, 1e-4} gives max|B_{u,r}| = 0.0 exactly, at ω = 1.0, f_ω =
1.5e-10, g_y cond 1.14e6 (`results/research_loop/r446_md_authority_fd/formal_analysis.json`).
The first-order authority is zero at balance; the action's leading effect is
second-order (bilinear state-matrix modulation `1/M`, `-D/M`), not force injection.

## Next-step pointers

- Camera-ready insertion of P1/P2/P3 conditional text is a manuscript action on
  this line (write_roots), gated by the normal evidence audit, not a new round.
- Pursuing any M-tier causal prediction or the P3 Jacobian measurement is an
  evidence round: copy the `m_observable_matrix.md` rows into the plan's
  `## Theory intake`, then run `external_theory_intake_lint.py R<N>`.
