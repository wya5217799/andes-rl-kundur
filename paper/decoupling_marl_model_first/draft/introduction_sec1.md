# Introduction draft — Section I (intro-drafter, 2026-08-14)

Status: first draft, six paragraphs, citations from the registered
differentiation memo numbering (renumbered citation-sequence at LaTeX
assembly). All cited-work statements stay at metadata level where the memo
marks them metadata-level; all reported numbers are from this line's
sealed feeds.

---

Inverter-based resources are reshaping power-system dynamics, and grid
interconnection standards now specify grid-forming capability and
coordination behaviour for these devices [32], [33], [34]. Among the
proposed mechanisms, paralleled virtual synchronous generators (VSGs) with
co-located energy storage are a natural platform for coordinated
active-power control: the storage devices provide the intervention
authority, and the VSG swing dynamics provide the frequency objectives
that matter for both the system-wide common mode and the relative
synchronization between units. Learned control is now routinely proposed
for this coordination task, from decentralized multi-agent deep
reinforcement learning for multi-VSG frequency stability [1] and
distributed multi-agent reinforcement learning for dynamic inertia-droop
coordination [2] to multi-agent learning for fast frequency response in
hybrid plants [29], and the field has matured enough to carry dedicated
surveys [31]. A study that adds another learned controller to this list
would be incremental; the open question is not whether learning can be
applied, but whether it should be trained at all for a given plant and
baseline.

Despite this progress, three limitations persist in the way learning-based
coordination evidence is produced. First, the executable plant is rarely
reconciled against the intended model before results are measured:
benchmarking efforts explicitly document how much fidelity work realistic
grid tasks require [4], and the field's own surveys call for exactly the
fidelity, comparator, and safety discipline that individual studies often
omit [24], [25]. Second, the residual-learning premise, that a learned
layer improves over a strong deterministic base, is usually assumed
rather than measured: the residual family trains the correction by default
[3], [17], [18], without first quantifying whether a residual of material
size exists after the base controller. Third, when a learned layer fails
to add value, the failure is rarely attributed: the evaluation literature
shows how easily reported gains dissolve under seed and implementation
variation [8], [11], but positive coordination studies typically do not
report matched deterministic baselines or such statistical discipline.
The consequence is a literature in which training-worthiness is decided by
convention rather than by evidence, even though structured-learning
results show that learning can beat optimized classical controllers when
the conditions are right [7].

In this work we pose the training-worthiness question directly and make it
the object of study. Our goal is a gate-sequenced methodology that
decides, before any training, whether a bounded learned residual has
physical headroom above an implementation-faithful deterministic baseline
on a storage-coordinated paralleled-VSG plant, with "do not train" as a
legitimate, pre-registered terminal decision. Two hard constraints define
the problem. Every candidate arm, learned or not, must act through the
same actuator map, limits, projection, and information timing as the
deterministic baseline, so that a measured difference is attributable.
And every verdict must be produced by a fail-closed, pre-registered gate
whose thresholds cannot be relaxed after inspection.

Three challenges stand between this goal and a naive implementation. The
first is fidelity: the simulator's executable device laws differ from the
intended equations in ways that change measured endpoints, so the plant
contract must be reconciled against source and validated by canary stages
before any controller result is trusted. The second is structure: the
plant is not hard-decoupled, its common and differential coordinates are
measurably cross-coupled, and a distributed action basis can structurally
lack authority over the very endpoint the residual is supposed to
improve. The third is attribution: a negative learning verdict must
separate "there is no residual" from "the information path cannot see it"
from "the action basis cannot express it", and the information-structure
literature shows these are genuinely different regimes [13], [16].

We address the three challenges with three methodology modules executed as
one gate sequence. The implementation-faithful contract reconciles the
intended equations with the executable simulator, distinguishes request,
commanded, and achieved power, and terminates in nominal and signed-power
canary stages (Section IV). The coordinate contract derives an exact
inertia-weighted common/differential decomposition, freezes the action
basis and the deterministic baseline, and qualifies reduced models on a
fresh bank (Section IV). The diagnostic gates then answer the headroom
question in three layers: an outcome-seeing offline oracle that ignores
information constraints; causal map families under progressively richer
neighbour information, including one-hop state and model-prediction
messages; and an action-basis ablation that adds one fleet-equal common
channel to the zero-common basis (Sections V and VI). Cooperative
distributed model predictive control represents the alternative of
extending the information path instead of gating it [36]-[38], and
structured-learning designs represent the alternative of guaranteeing the
learner rather than the baseline [19].
Our methodology keeps both as options that the gate decides whether to open.

The methodology was executed end to end on a modified Kundur phasor-domain
plant, and it returned a complete, attributable verdict. We summarise the
contributions as follows. First, we present an implementation-faithful,
gate-sequenced pre-training protocol for storage-coordinated paralleled
VSGs, including the executable plant contract and its canary stages
(Sections III-IV). Second, we report a bounded deterministic result and a
bounded negative result from the same discipline: the deterministic
baseline reduces the common-coordinate integral absolute error by 95.5%
and the differential-coordinate squared error by 99.3% over matched zero
control on a sealed paired bank, while the outcome-seeing residual upper
bound stops at the registered 2% common-endpoint floor to within 1.7e-9
and the tested causal families add no qualifying increment (Section V).
Third, we provide the mechanism-level diagnosis: a zero-common residual
basis structurally cannot reach the common endpoint, and adding one
fleet-equal common channel makes all sixteen exposed cases physically
feasible versus ten of sixteen without it (Section VI). Together these
results demonstrate the protocol, not a learned controller: the gate
established a real deterministic gain, refused training when the measured
headroom could not justify it, and named the structural reason.

## References (cited subset; memo numbering)

[1] S. Kang et al., IJEPES, vol. 168, art. 111374, 2025.
[2] Q. Yang et al., IEEE Trans. Power Syst., vol. 38, no. 6, pp. 5598-5612, 2023.
[3] Q. Liu et al., IEEE Trans. Sustain. Energy, 2025; arXiv:2408.06790.
[4] E. Marchesini et al., "RL2Grid," arXiv:2503.23101, 2025.
[7] W. Cui, Y. Jiang, B. Zhang, IEEE Trans. Power Syst., 2023.
[8] P. Henderson et al., AAAI, 2018.
[11] R. Agarwal et al., NeurIPS, 2021.
[13] R. Dobbe, D. Fridovich-Keil, C. Tomlin, arXiv:1707.06334, 2017.
[16] Y. C. Ho, Proc. IEEE, vol. 68, no. 6, pp. 644-654, 1980.
[17] T. Johannink et al., ICRA, 2019.
[18] T. Silver et al., "Residual Policy Learning," arXiv:1812.06298, 2018.
[19] J. Kwon et al., IEEE Control Syst. Lett., 2023.
[24] P. Yu et al., Renew. Sustain. Energy Rev., vol. 217, art. 116022, 2025.
[25] Glover et al., Proc. IEEE, 2025.
[29] S. Ikram, S. Aziz, D. Habibi, SEGAN, 2026.
[31] X. Ding et al., Energies, vol. 17, no. 11, art. 2620, 2024.
[32] IEEE Std 2800-2022.
[33] NERC, Grid Forming Functional Specifications for BPS-Connected BESS, 2023.
[34] UNIFI Consortium, Specifications for Grid-Forming IBRs, Version 2, 2024.
[36] B. T. Stewart et al., Syst. Control Lett., vol. 59, no. 8, 2010.
[37] C. Conte et al., Automatica, vol. 69, 2016.
[38] J. Lin et al., IJEPES, vol. 155, art. 109459, 2024.

Note: this subset matches the memo's full verified list bidirectionally;
full author lists and verification grades live in
working/differentiation_memo_2026-08-14.md. Citation-sequence renumbering
happens at assembly.
