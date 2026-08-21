# R391 publication audit

## Coverage and authority

Scope: `paper/converter_vsg_pq_decoupling/reports/R391.md`,
`paper/converter_vsg_pq_decoupling/working/R391_diagnosis.md`,
`memory/claims/CLM-1100.md`, and the immutable R391 formal artifacts.

Authority order: formal analysis and execution; formal manifest and seal;
registered claim; diagnosis; feed prose. The authoritative classification is
`STOP-REGF2-POSITIVE-REAL-GUARD`.

## Evidence audit

Independent replay verified every cited SHA-256 value, sidecar, manifest entry,
seal-to-attempt-to-execution-to-analysis link, canonical contract, R390/R389
parent hash, JSON locator, and WSL source/runtime identity. The two arms have
exactly identical matrices, equilibrium snapshots, catalogs, bindings,
inventories, references, and runtime sources; only their registered names and
initialization tolerances differ.

WSL replay reproduces the formal leading roots
`+46.41533383454654 s^-1` and `+4.606789511264594 s^-1`, the sealed positive
count of three, near-zero count of nine, zero spectrum mismatch,
`1.8868120112399466e-15` maximum backward error, `8.353337703423357`
leading condition number, and zero cross-arm leading distance. The third
positive root, `+6.452814682866848e-7 s^-1`, is correctly retained in the
sealed threshold count but excluded from material interpretation because it
lies in the frozen `1e-6` near-zero region.

Participation and R389 comparison values were independently recomputed from
the sealed matrices and trace. The feed correctly limits participation to
state association and describes the R391 leading rate as `24.95096%` below
R389's diagnostic sampled-output slope.

**Evidence decision: PASS.**

## Power-systems domain audit

The exact DAE-reduced matrix is finite and evaluated at unchanged time and
x/y/z vectors. `max|f|=0`, `max|g|=3.745103976937614e-7`, both material roots
are real and well separated, and the registered numerical guards are strong.
Installed REGF2, REGF1, PLL2, DAE, and EIG source hashes match the seal; their
mass-matrix/time-constant semantics support reciprocal-second units.

The documents correctly distinguish local phasor-model growth from physical
converter instability, nonlinear/global stability, and causal-loop
identification. They also exclude authority, decoupling, controller, learning,
topology, EMT/HIL, hardware, safety, and deployment claims.

**Domain decision: DOMAIN PASS.**

## Maximum defensible claim

For the exact sealed ANDES 2.0.0 four-stock-REGF2 Kundur model, the registered
initialized operating point has two material, reproducible positive-real
eigenvalues in its 64 by 64 reduced small-signal matrix. The result is
identical across two fresh initialization-tolerance arms without advancing
simulation time, strongly disfavoring time stepping or initialization
tolerance as the sole explanation for the earlier growing trace. It does not
establish physical-converter instability, a causal feedback loop, nonlinear
or global instability, safety, actuator authority, decoupling, controller or
learning value, generalization, hardware behavior, or deployment readiness.

## Publication disposition

Retain CLM-1100 and the R391 feed in local evidence history. Keep the result
out of current manuscript result prose because the tested formulation stops
before authority and control. External literature, novelty, venue, and
submission-package audits are not applicable to this local mechanism gate.
