# Value-estimation repair deep research — critic-divergence / dying-actor single-factor repairs for the yang_md TD3 setup (2026-08-17)

> Bounded deep-research pass (one frozen research question, five targeted
> verification searches, existence-verified citations only — not a
> survey-grade sweep) feeding R423.  Every cited work was checked against
> its arXiv / venue record before use.  Nothing here changes the frozen
> scientific contracts by itself; the measured divergence signature is
> paraphrased, not copied from any repository table or claim card.

## Research question

For TD3 training whose measured signature is — critic loss growing ~24–126×
from the first to last quartile, TD-error standard deviation growing
~4.9–11.3×, Bellman-residual magnitude growing ~3.6–12.6×, actor
log-gradient norms vanishing (Q4/Q1 ≈ −0.40 to +0.12), with sampled-state
variance stable (no exploration collapse) — which single-factor,
literature-established repairs for critic divergence / value-estimation
instability are best, ranked by (a) evidence strength, (b) fit to this
exact signature (critic diverges while the actor dies and exploration stays
healthy), and (c) applicability to a multi-agent shared-policy
voltage/frequency decoupling controller whose two-channel reward carries a
common channel with a Lagrange budget that must not change semantics?

## Method (bounded)

One question frozen up front; no cross-question drift.  Search perspectives
were collapsed into five targeted queries (original-TD3 stabilizers;
reward/value normalization; normalization-in-critic; gradient clipping and
learning-rate decoupling; divergence diagnostics and actor-death).  Every
candidate repair is matched to a verified anchor, and hedges follow the
evidence (an unconfirmable claim is dropped, not padded).  The Lagrange-budget
interaction is assessed per repair rather than asserted globally.

## Findings (ranked menu)

**P1 — Critic-side value/target normalization (PopArt-style running std, or
return-based scaling).**  The single most on-mechanism repair.  Evidence:
PopArt adaptively rescales TD targets while *preserving outputs precisely*
(i.e., the network still emits original-scale Q-values), invented exactly
because heterogeneous/divergent reward scales destabilize value learning
(Hessel et al., AAAI 2019); Return-based Scaling shows a running-std
normalization of returns is a simpler fix for unstable value training
(Schrittwieser et al., 2021); the TD3 successor TD7 builds its stability on
state-action normalization over vanilla TD3 (Fujimoto et al., NeurIPS 2023).
Fit: directly removes the runaway target magnitude that simultaneously drives
the 3.6–12.6× Bellman-residual growth and flattens the critic's
action-Jacobian, which is what kills the actor gradients (Q4/Q1 ≤ +0.12)
while exploration stays healthy.  Budget interaction: **doable
budget-preservingly** — normalize the critic's TD target / the differential
channel only, and use PopArt's output correction so reported values stay on
the original scale; do **not** rescale the raw common-channel reward that
feeds the Lagrange multiplier, or the multiplier's marginal-price semantics
shift by the scale factor.
*Implication (adopt):* critic-side PopArt (or running-std return scaling) on
the differential channel with output correction; freeze the common/budget
channel's reward as-is.

**P2 — Normalization inside the critic MLP (LayerNorm; BatchNorm per
CrossQ).**  Evidence: CrossQ puts BatchNorm in the critic and reports large
gains in stability and sample efficiency — enough to drop target networks
(Bhatt et al., ICLR 2024); SALE/TD7 apply LayerNorm to the state-action
representation feeding the Q-function (Fujimoto et al., NeurIPS 2023).  Fit:
counters activation saturation under the growing value magnitude; it bounds
hidden activations but not the output/target scale, so it complements P1
rather than replacing it.  Budget interaction: **safe** — it touches no
reward and no multiplier.
*Implication (adopt):* LayerNorm on the critic's hidden layers as the
lowest-risk complementary change; the strongest single change if P1's
reward-side surgery is judged too invasive for this round.

**P3 — Critic gradient clipping (`clip_grad_norm_` on the critic
optimizer).**  Evidence: gradient clipping is the canonical
exploding-gradient repair (Pascanu, Mikolov & Bengio, ICML 2013) and is
routine in continuous-control implementations.  Fit: caps the diverging
critic update magnitude directly (the 24–126× critic-loss growth), but it
damps the symptom without removing the target-scale cause.  Budget
interaction: **safe**.
*Implication (adopt):* clip critic gradients (≈0.5–1.0) as a cheap guard
alongside P1/P2, not as the standalone fix.

**P4 — Lower critic learning rate.**  Evidence: hyperparameter sensitivity
is large across DRL (Henderson et al., AAAI 2018), but there is no strong
TD3-specific ablation establishing "lower critic LR" as the fix, and TD3's
delayed policy updates already assume the critic tracks faster than the
actor.  Fit: reduces per-step critic update magnitude (symptom-damping), with
a genuine tension against the delayed-update design.  Budget interaction:
**safe**.
*Implication (adopt):* a secondary knob (3e-4 → 1e-4 acceptable), not the
targeted repair.

**P5 — Target-network smoothing changes (policy noise, noise clip, tau).**
Evidence: in-paper TD3 stabilizers (Fujimoto et al., ICML 2018).  Fit:
already present; further tuning (smaller tau, tighter noise) is second-order
relative to the value-scale driver.  Budget interaction: **safe**.
*Implication (adopt):* keep defaults; revisit only if P1/P2 under-deliver.

**P6 — Twin-critic aggregation.**  Evidence: clipped double-Q (min over two
critics) is already the TD3 standard for overestimation suppression
(Fujimoto et al., ICML 2018).  Fit: already in use — the family is exhausted;
min-aggregation is already doing its job.  Budget interaction: n/a.
*Implication:* no change (assessed, not a candidate).

**P7 — Soft-update / batch-size / buffer-size adjustments.**  Evidence:
larger batch and replay buffer reduce gradient variance and target
non-stationarity (Henderson et al., AAAI 2018; buffer-size sensitivity noted
in Fujimoto et al., ICML 2018).  Fit: general and indirect; does not target
the scale mismatch.  Budget interaction: **safe**.
*Implication (adopt):* increase batch/buffer only as a variance-reduction
complement, not as the targeted repair.

## Recommendation

**Critic-side value/target normalization (PopArt-style running std with
output correction, or return-based scaling), applied to the differential
channel only.**  One-sentence justification: it is the only repair in the
menu that removes the runaway target magnitude — the shared upstream cause of
both the Bellman-residual/critic-loss divergence and the actor-gradient
collapse — and it is the one that can be made budget-preserving by
normalizing the critic's targets rather than the raw common-channel reward.

## Citations (verified)

- Fujimoto, van Hoof & Meger (2018). *Addressing Function Approximation
  Error in Actor-Critic Methods* (TD3). ICML 2018. arXiv:1802.09477.
  https://icml.cc/virtual/2018/poster/2227
- Hessel et al. (2019). *Multi-Task Deep Reinforcement Learning with
  PopArt*. AAAI 2019. arXiv:1809.04474.
  https://mlanthology.org/aaai/2019/hessel2019aaai-multi/
- Schaul, Ostrovski, Kemaev & Borsa (2021). *Return-based Scaling: Yet
  Another Normalisation Trick for Deep RL*. arXiv:2105.05347.
  https://arxiv.org/abs/2105.05347
- Fujimoto, Chang, van Hoof & Meger (2023). *For SALE: State-Action
  Representation Learning for Deep Reinforcement Learning* (basis of TD7).
  NeurIPS 2023. https://mlanthology.org/neurips/2023/fujimoto2023neurips-sale/
- Bhatt, Palenicek, Belousov, Argus, Amiranashvili, Brox & Peters (2024).
  *CrossQ: Batch Normalization in Deep Reinforcement Learning for Greater
  Sample Efficiency and Simplicity*. ICLR 2024. arXiv:1902.05605.
  https://arxiv.org/abs/1902.05605
- Fu, Kumar, Soh & Levine (2019). *Diagnosing Bottlenecks in Deep Q-learning
  Algorithms*. ICML 2019. arXiv:1902.10250.
  https://icml.cc/virtual/2019/poster/4253
- Sokar, Agarwal, Castro & Evci (2023). *The Dormant Neuron Phenomenon in
  Deep Reinforcement Learning*. ICML 2023.
  https://mlanthology.org/icml/2023/sokar2023icml-dormant/
- Henderson, Islam, Bachman, Pineau, Precup & Meger (2018). *Deep
  Reinforcement Learning that Matters*. AAAI 2018. arXiv:1709.06560.
  https://mlanthology.org/aaai/2018/henderson2018aaai-deep/
- Pascanu, Mikolov & Bengio (2013). *On the difficulty of training recurrent
  neural networks*. ICML 2013. arXiv:1211.5063.
  https://mlanthology.org/icml/2013/pascanu2013icml-difficulty/
