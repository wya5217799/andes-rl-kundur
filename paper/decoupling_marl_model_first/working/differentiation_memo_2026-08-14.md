# Differentiation memo — decoupling-marl-model-first (2026-08-14)

Registered differentiation context for the manuscript line, produced by the
bounded deep-research pass of 2026-08-14 (3 research questions, 3
perspectives, 3 retrieval rounds each; web search + Crossref REST + arXiv
API). This is advisory literature context, not project evidence: it cannot
upgrade or change any claim, feed, or result, and any project-internal
number used in the paper must be re-read from the line's feeds.

## 1. Method note (verification status, degradations)

- Every cited reference carries a grade: `VERIFIED this pass` (existence +
  title/author/abstract via Crossref DOI or arXiv API), `carried from line
  notes, recorded VERIFIED` (verified in the line's 2026-08-03/06/07
  surveys), or `metadata-level` (existence verified, content readable only
  at title/abstract level).
- Degradations: paywalled full texts are metadata-level only; SSRN
  abstract unreadable (HTTP 403); IEEE Std 2800-2022 DOI is not
  Crossref-indexed (carried); absence claims are bounded to this pass's
  tools (web + Crossref + arXiv) — one authoritative full-text query
  (IEEE Xplore / Scopus / Web of Science / Google Scholar) plus a
  Chinese-venue check is an open human item before the paper asserts
  novelty.

## 2. RQ answers (hedged)

RQ1: No retrieved work proposes the exact fidelity-contract ->
deterministic-baseline -> residual-headroom gate protocol; each ingredient
exists separately (residual-after-base: Liu et al. TSTE 2025, Johannink et
al., Silver et al.; structured/guaranteed learning: Cui et al. TPWRS 2023,
Kwon et al., Shuai et al.; fidelity benchmarking: RL2Grid, L2RPN;
model-based-first design: Häberle et al.). Claim as "no protocol of this
exact form retrieved in our search", never as "nobody combined RL with a
baseline".

RQ2: Direct quantitative null results above strong deterministic baselines
in grid/storage control are rare (`[unconfirmed]`); the published
mechanisms predicting such nulls are the statistics-of-RL canon (Henderson
2018, Ilyas 2020, Engstrom 2020, Agarwal 2021, Yu 2022) and benchmark-side
realism (RL2Grid, L2RPN); the information-structure theory (Dobbe et al.,
Ho 1980, Witsenhausen family) explains this line's own null.

RQ3: The adjacent lines establish fidelity, comparator discipline, and
headroom framing separately; the "pre-registered training-worthiness gate
sequenced after an implementation-faithful deterministic baseline" cell is
empty. That is the paper's differentiation.

## 3. Differentiation table

| Closest work | What it establishes | Axis on which our paper differs |
|---|---|---|
| Kang et al., IJEPES 2025 | direct surface combination (decentralized adaptive MARL multi-VSGs) | we add the fidelity contract, matched deterministic baseline, pre-training gate; headline is a bounded negative with mechanism |
| Yang et al., IEEE TPWRS 2023 | title-level combination (distributed MADRL inertia-droop, paralleled VSGs) | no matched deterministic baseline reported; we answer the training-worthiness question and diagnose the mechanism |
| Liu et al., IEEE TSTE 2025 | residual-after-deterministic-base architecture (Volt-Var) | they train the residual immediately on a quasi-static task; we gate training on measured headroom on a fast electromechanical plant |
| Marchesini et al., RL2Grid, arXiv:2503.23101, 2025 | benchmark fidelity; classic RL baselines define the reference bar | benchmark across tasks vs protocol + diagnosis on one plant contract |
| Marot et al., EPSR 2020/2022 (L2RPN) | competition-grade evaluation; rule-based baselines stay competitive | ranking vs controlled pre-registered headroom diagnosis |
| Cui, Jiang & Zhang, IEEE TPWRS 2023 | structured Lyapunov RL beats optimal linear droop (positive) | calibration counterpoint: headroom is information/action-specific; our negative must not generalize to "RL never helps" |
| Kwon et al., IEEE L-CSS 2023/2024 | structured risk-constrained learning on linearized models | our contract is implementation-faithful with exact coordinate decomposition |
| Zhang, Xie & Huang, ICPST 2025 | meta-RL pre-training for adaptation speed | our pre-training is a gate whose terminal output can be "no training" |
| Shuai et al., JMPSCE 2024 | RL for GFM regulation with stability guarantee | guarantee lives in the learned controller; ours lives in the deterministic baseline |
| Ma, Zhang & Wang, IEEE TSG 2023 | explicit NN imitating constrained optimization | imitation of a known optimum vs gating a residual whose direction is information-limited |
| Yu et al., RSER 2025; Glover et al., Proc. IEEE 2025 | field-wide methodology surveys | they describe the discipline; we execute it with negative results |
| Salawuddeen et al., SSRN 2025 | DRL algorithm benchmarking in islanded microgrids (preprint) | algorithm ranking vs deciding whether training should start |
| Benhmidouch et al., EPSR 2024 | RL adapts VSG inertia/damping inside admissible ranges | envelope for the learner vs full deterministic controller + frozen guards |
| DMPC/cooperative MPC (Stewart 2010, Conte 2016, Lin 2024) | shared-prediction information compensation | they extend information to close a gap; we prove the frozen information path cannot close it |

## 4. Must-cite works (one-line differentiation each)

1. Kang, Jung, You & Jang, IJEPES 2025 — closest surface-combination
   neighbor; we add the fidelity contract, matched deterministic baseline,
   and pre-training gate, and publish a bounded negative with mechanism.
2. Liu, Guo, Deng, Liu, Li & Sun, IEEE TSTE 2025 — closest
   residual-after-base architecture; we refuse to train until a frozen
   non-learning gate proves headroom.
3. Marchesini et al., RL2Grid, arXiv:2503.23101, 2025 — establishes that
   classic RL baselines define the reference bar; we contribute the
   gate-sequenced protocol and an information-path negative, not a
   benchmark.
4. Yang, Yan, Chen, Chen & Wen, IEEE TPWRS 2023 — title/venue-nearest
   precedent; we replace the positive coordination claim with a bounded
   negative and its mechanism under comparator discipline it does not
   report.
5. Henderson et al., AAAI 2018 (with Agarwal et al., NeurIPS 2021) — the
   evaluation-discipline canon the power-MARL positive literature mostly
   ignores; our protocol implements it and our null is what their
   statistics predict.

Calibration counterpoint the paper must engage: Cui, Jiang & Zhang, IEEE
TPWRS 2023 (Lyapunov-structured RL beats optimal linear droop) — the
headroom question is information- and action-specific, so the negative
result must not be generalized to "RL never helps".

## 5. Open items needing human verification

0. Supplementary RQ1 check (2026-08-14, supervisor): two additional bounded
   web queries ("pre-training gate / training-worthiness / residual
   headroom ... decide whether to train"; "when not to train reinforcement
   learning grid control headroom gate deterministic baseline first") both
   returned no matching work. The absence claim remains search-bounded; a
   human full-text pass (IEEE Xplore / Scopus / Google Scholar, Chinese
   venues, TechRxiv/SSRN) is still required before asserting novelty.

1. Kang et al. IJEPES 2025 full text: test system, baseline matching,
   seeds/statistics.
2. RL2Grid v1/v2 drift and exact reference-metric wording before quoting.
3. Liu et al. TSTE 2025 full text: no headroom gate; residual bound; margin.
4. Marot et al. L2RPN exact outcomes before quoting any lesson.
5. Nguyen Minh Cuong, JMST 2026: full author list and actual outcome.
6. Salawuddeen et al., SSRN 5532101: abstract/full text; baselines; nulls.
7. Standards claims (IEEE Std 2800-2022, NERC 2023, UNIFI 2024): re-verify
   landing pages if quoted.
8. RQ1 absence claim: one authoritative full-text + Chinese-venue query
   before asserting novelty.
9. Project-internal numbers: re-read from feeds/claims before paper use.
10. Cui et al. experimental conditions (test system, droop definition).

## 6. References

[1] S. Kang, Y. Jung, D. You, G. Jang, "Enhancing frequency stability with
decentralized adaptive control using multi-agent deep reinforcement
learning of multi-VSGs," IJEPES, vol. 168, art. 111374, 2025. (VERIFIED
this pass; metadata-level)

[2] Q. Yang, L. Yan, X. Chen, Y. Chen, J. Wen, "A Distributed Dynamic
Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement
Learning for Multiple Paralleled VSGs," IEEE Trans. Power Syst., vol. 38,
no. 6, pp. 5598-5612, 2023. (VERIFIED this pass; DOI 10.1109/tpwrs.2022.3221439)

[3] Q. Liu, Y. Guo, L. Deng, H. Liu, D. Li, H. Sun, "Residual Deep
Reinforcement Learning With Model-Based Optimization for Inverter-Based
Volt-Var Control," IEEE Trans. Sustain. Energy, 2025; arXiv:2408.06790.
(VERIFIED this pass)

[4] E. Marchesini, B. Donnot, C. Crozier, et al., "RL2Grid: Benchmarking
Reinforcement Learning in Power Grid Operations," arXiv:2503.23101, 2025.
(VERIFIED this pass)

[5] A. Marot, B. Donnot, C. Romero, et al., "Learning to run a power
network challenge for training topology controllers," Electr. Power Syst.
Res., vol. 189, art. 106635, 2020. (VERIFIED this pass; metadata-level)

[6] A. Marot, B. Donnot, K. Chaouache, et al., "Learning to run a power
network with trust," Electr. Power Syst. Res., vol. 212, art. 108487, 2022.
(VERIFIED this pass; metadata-level)

[7] W. Cui, Y. Jiang, B. Zhang, "Reinforcement Learning for Optimal
Primary Frequency Control: A Lyapunov Approach," IEEE Trans. Power Syst.,
2023; arXiv:2009.05654. (VERIFIED this pass)

[8] P. Henderson, R. Islam, P. Bachman, J. Pineau, D. Precup, D. Meger,
"Deep Reinforcement Learning that Matters," AAAI, 2018; arXiv:1709.06560.
(VERIFIED this pass)

[9] A. Ilyas, L. Engstrom, S. Santurkar, et al., "A Closer Look at Deep
Policy Gradients," ICLR, 2020; arXiv:1811.02553. (VERIFIED this pass)

[10] L. Engstrom, A. Ilyas, S. Santurkar, et al., "Implementation Matters
in Deep Policy Gradients: A Case Study on PPO and TRPO," ICLR, 2020;
arXiv:2005.12729. (VERIFIED this pass)

[11] R. Agarwal, M. Schwarzer, P. S. Castro, A. Courville, M. G.
Bellemare, "Deep Reinforcement Learning at the Edge of the Statistical
Precipice," NeurIPS, 2021; arXiv:2108.13264. (VERIFIED this pass)

[12] C. Yu, et al., "The Surprising Effectiveness of PPO in Cooperative
Multi-Agent Games," NeurIPS, 2022. (carried; recorded VERIFIED)

[13] R. Dobbe, D. Fridovich-Keil, C. Tomlin, "Fully Decentralized Policies
for Multi-Agent Systems: An Information Theoretic Approach,"
arXiv:1707.06334, 2017. (carried; recorded VERIFIED)

[14] M. Mehmetoglu, E. Akyol, K. Rose, "A Deterministic Annealing
Optimization Approach for Witsenhausen's and Related Decentralized Control
Settings," arXiv:1403.5315, 2014. (carried; recorded VERIFIED)

[15] M. Baglietto, T. Parisini, R. Zoppoli, "Numerical solutions to the
Witsenhausen counterexample by approximating networks," IEEE Trans. Autom.
Control, vol. 46, no. 9, pp. 1471-1477, 2001. (carried; recorded VERIFIED)

[16] Y. C. Ho, "Team decision theory and information structures," Proc.
IEEE, vol. 68, no. 6, pp. 644-654, 1980. (carried; recorded VERIFIED)

[17] T. Johannink, et al., "Residual Reinforcement Learning for Robot
Control," ICRA, 2019. (carried; recorded VERIFIED)

[18] T. Silver, K. Allen, J. Tenenbaum, L. Kaelbling, "Residual Policy
Learning," arXiv:1812.06298, 2018. (carried; recorded VERIFIED)

[19] J. Kwon, S. Mukherjee, T. Vu, et al., "Risk-Constrained Reinforcement
Learning for Inverter-Dominated Power System Controls," IEEE Control Syst.
Lett., 2023. (VERIFIED this pass)

[20] J. Kwon, et al., "Coherency-Aware Learning Control of Inverter-
Dominated Grids: A Distributed Risk-Constrained Approach," IEEE Control
Syst. Lett., 2024. (VERIFIED this pass)

[21] Z. Ma, Q. Zhang, Z. Wang, "Safe and Stable Secondary Voltage Control
of Microgrids Based on Explicit Neural Networks," IEEE Trans. Smart Grid,
2023. (VERIFIED this pass)

[22] H. Shuai, B. She, J. Wang, F. Li, "Safe Reinforcement Learning for
Grid-forming Inverter Based Frequency Regulation with Stability
Guarantee," J. Mod. Power Syst. Clean Energy, 2024. (VERIFIED this pass)

[23] Z. Zhang, Y. Xie, R. Huang, "Pre-training and Fine-Tuning Based
Meta-Reinforcement-Learning for Grid-Forming-Based Energy Storage System
Operation to Recover Power Grid Frequency," IEEE ICPST, 2025. (VERIFIED
this pass; metadata-level)

[24] P. Yu, Z. Wang, H. Zhang, Y. Song, "Safe reinforcement learning for
power system control: A review," Renew. Sustain. Energy Rev., vol. 217,
art. 116022, 2025. (VERIFIED this pass)

[25] Glover, Krishnamoorthy, Ren, et al., "Deep Reinforcement Learning for
Distribution System Operations: A Tutorial and Survey," Proc. IEEE, 2025.
(VERIFIED this pass; first three authors only)

[26] Y. Wan, Q. Xu, C. Garcia, et al., "A Comparative Assessment of Power
Converter Control Strategies: From Linear Control to Machine Learning
Approaches," IEEE Ind. Electron. Mag., 2026. (VERIFIED this pass;
metadata-level)

[27] Nguyen Minh Cuong, "Safe reinforcement learning versus classical
controllers for voltage regulation and power quality in the IEEE 33-bus
distribution system," J. Military Sci. Technol., vol. 110, pp. 12-21, 2026.
(VERIFIED this pass; metadata-level)

[28] Salawuddeen, Nnamoko, Braun, Ponci, "Benchmarking Deep Reinforcement
Learning Algorithms for Frequency Control in Islanded Microgrids: A
Comparative Analysis," SSRN preprint 5532101, 2025. (VERIFIED existence;
metadata-level)

[29] S. Ikram, S. Aziz, D. Habibi, "A novel multi-agent deep reinforcement
learning framework for fast frequency response in inverter-based hybrid
power plants," Sustainable Energy, Grids and Networks, 2026. (VERIFIED
this pass)

[30] H. Benhmidouch, et al., "A novel reinforcement learning policy
optimization based adaptive VSG control technique for improved frequency
stabilization in AC microgrids," Electr. Power Syst. Res., 2024. (VERIFIED
this pass)

[31] X. Ding, et al., "Deep and Reinforcement Learning in Virtual
Synchronous Generator: A Comprehensive Review," Energies, vol. 17, no. 11,
art. 2620, 2024. (VERIFIED this pass)

[32] IEEE Std 2800-2022, "IEEE Standard for Interconnection and
Interoperability of Inverter-Based Resources (IBRs) Interconnecting with
the Associated Transmission Electric Power Systems," 2022. (carried)

[33] NERC, "Grid Forming Functional Specifications for BPS-Connected
BESS," white paper, 2023. (carried)

[34] UNIFI Consortium, "Specifications for Grid-Forming Inverter-Based
Resources, Version 2," NREL technical report, 2024. (carried)

[35] J. Li, T. Zhou, "Bio-inspired distributed load frequency control in
Islanded Microgrids: A multi-agent deep reinforcement learning approach,"
Appl. Soft Comput., 2024. (VERIFIED this pass; metadata-level)

[36] B. T. Stewart, A. N. Venkat, J. B. Rawlings, S. J. Wright, G.
Pannocchia, "Cooperative distributed model predictive control," Syst.
Control Lett., vol. 59, no. 8, pp. 460-469, 2010. (carried; VERIFIED)

[37] C. Conte, N. R. Voellmy, M. N. Zeilinger, M. Morari, C. N. Jones,
"Distributed synthesis and stability of cooperative distributed model
predictive control for linear systems," Automatica, vol. 69, pp. 117-129,
2016. (carried; VERIFIED)

[38] J. Lin, et al., "Power oscillation suppression of multi-VSG based on
both consensus and model predictive control," IJEPES, vol. 155, art.
109459, 2024. (carried; VERIFIED)

[39] H. Xu, J. Zheng, G. Qu, "A Scalable Network-Aware Multi-Agent
Reinforcement Learning Framework for Decentralized Inverter-based Voltage
Control," arXiv:2312.04371, 2023. (VERIFIED this pass)

[40] H. Cui, F. Li, K. Tomsovic, "Hybrid Symbolic-Numeric Framework for
Power System Modeling and Analysis," IEEE Trans. Power Syst., 2024;
arXiv:2002.09455. (VERIFIED this pass via arXiv/ar5iv; full author list to
confirm at bib finalization)

[41] P. Kundur, "Power System Stability and Control," McGraw-Hill, 1994.
(canonical textbook; confirm edition at bib finalization)

[42] B. Stellato, G. Banjac, P. Goulart, A. Bemporad, S. Boyd, "OSQP: An
Operator Splitting Solver for Quadratic Programs," Mathematical
Programming Computation, vol. 12, no. 4, pp. 637-672, 2020. (VERIFIED this
pass via publisher/author pages)

[43] H. S. Witsenhausen, "A Counterexample in Stochastic Optimum Control,"
SIAM Journal on Control, vol. 6, no. 1, pp. 131-147, 1968. (VERIFIED this
pass via bibliographic listings)
