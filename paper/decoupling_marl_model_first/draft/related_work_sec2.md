# Related Work draft — Section II (paper-writer, 2026-08-14)

Status: first draft. All citations come from the registered differentiation
memo (working/differentiation_memo_2026-08-14.md); bracketed numbers are
that memo's numbering and will be renumbered citation-sequence at LaTeX
assembly. Statements about cited works stay at metadata level where the
memo marks them metadata-level.

---

## II. Related Work

**Learned control of VSGs and frequency.** Deep and reinforcement learning
for virtual-synchronous-generator control is an active and surveyed field
[31], driven by grid-forming specifications and interconnection standards
[32]-[34]. Representative works apply decentralized multi-agent deep
reinforcement learning to multi-VSG frequency stability [1], distributed
multi-agent deep reinforcement learning to dynamic inertia-droop
coordination of paralleled VSGs [2], multi-agent learning to fast
frequency response in inverter-based hybrid plants [29], reinforcement
learning inside small-signal admissible ranges of VSG inertia and damping
[30], and bio-inspired multi-agent learning to islanded load-frequency
control [35]. What this literature rarely reports is the combination this
paper makes load-bearing: an implementation-faithful plant contract, a
matched strong deterministic baseline under identical information, action,
and limit permissions, and seed-level statistical discipline, and
the two representative studies closest to this surface combination [1],
[2] report positive coordination claims without such a matched baseline.

**Residual and structured learning.** The residual-learning family layered a
learned correction over a good-but-imperfect base controller [17], [18],
and its power-systems instance trained deep reinforcement learning over a
model-based optimization base for inverter Volt-Var control [3]. The base
is named, but training is not conditional on a measured residual: the
learned layer is trained by default. The structured-learning school instead
engineers the learner's guarantees directly: Lyapunov-structured policies
for primary frequency control [7], risk-constrained and coherency-aware
learning for inverter-dominated grids [19], [20], safe reinforcement
learning with stability guarantees for grid-forming frequency regulation
[22], explicit neural networks that imitate constrained optimization
inside a certified region [21], and meta-reinforcement-learning
pre-training for fast adaptation of grid-forming storage [23]. These
results are strong and must calibrate our claims: in particular, [7]
reported a structured learner that outperforms optimal linear droop, which
is exactly why this paper's negative results are stated as
information-path-specific rather than as a verdict on learning in general.
What none of these works does is gate the training decision itself on a
pre-registered, non-learning residual-headroom measurement after an
implementation-faithful deterministic baseline.

**Fidelity and benchmarking.** The benchmarking stream establishes the
fidelity half of this paper's contract. RL2Grid builds on the Grid2Op
framework with operator collaboration, standardized tasks, operational
heuristics, and safety constraints, and reports that classic reinforcement
learning baselines define a reference bar that realistic tasks strain [4].
The L2RPN challenge ran competition-grade evaluation with rule-based
baselines remaining competitive and unseen-topology generalization as a
first-class object [5], [6]. Adjacent comparative studies cover safe
reinforcement learning against classical controllers for voltage
regulation [27], linear-to-learning converter control assessments [26],
and algorithm-level deep reinforcement learning benchmarking for islanded
microgrid frequency control [28]. These works rank algorithms or
benchmark tasks; none decides, for one plant contract, whether training
should start at all.

**Evaluation discipline and information structure.** Two bodies of theory
explain why a bounded negative above a strong deterministic baseline is
the statistically expected outcome and how to state it honestly. The
statistics-of-reinforcement-learning canon shows that reported gains shift
with seeds, hyperparameters, and implementation details [8], [10], that
policy-gradient estimates can misalign with the true gradient [9], that
single point estimates are rarely informative [11], and that simple strong
baselines are systematically underestimated in multi-agent settings [12].
The information-structure literature has shown that the amount of a
centralized optimum a decentralized information structure can reconstruct
is a structural property [13], [16], and that nonlinear policies can beat
affine ones only when the information structure supplies the needed side
information [14], [15].
Cooperative distributed model predictive control represents the
"extend the information path" alternative: neighbour trajectory exchange
approaches centralized performance under iteration [36]-[38]. This paper
sits in the cell these lines leave empty: a pre-registered, gate-sequenced
training-worthiness decision after an implementation-faithful
deterministic baseline, with the negative verdict attributed by design.
