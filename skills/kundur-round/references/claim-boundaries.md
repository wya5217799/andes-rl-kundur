# Claim boundaries

Use the narrowest wording that carries the verified result.

| Evidence | Supported wording | Scope expansion requiring more evidence |
|---|---|---|
| One simulator, one plant, sealed scenarios | improved on the tested plant and scenario bank | general power-system improvement |
| One topology with parameter stress tests | survived the scanned stress range | topology generalization |
| Held-out operating points on one network | operating-condition generalization on that network | unseen-topology generalization |
| Held-out networks or graphs | topology generalization over the sampled network family | arbitrary-size or universal generalization |
| Local eigenvalue analysis | local small-signal mode or damping change | transient stability or global stability |
| Time-domain tests | empirical transient behavior in the tested envelope | certificate, region of attraction, or guaranteed safety |
| Constraint guards on tested traces | no recorded violations under the tested contract | formally safe deployment |
| Directional point estimate | directional effect | superiority |
| Interval excluding the null under a registered analysis | supported effect for the registered estimand | universal or causal mechanism |
| Declared impedance scaling | weaker-tie or impedance-scaling proxy | measured SCR unless converted and validated |
| Centralized learned controller | centralized learned-control value | decentralized or MARL value |
| Parameter-shared policy | parameter-sharing result under its information pattern | emergent cooperation |

## Cross-section drift

Check the same claim in:

1. title;
2. abstract;
3. introduction and contribution bullets;
4. results and captions;
5. discussion and limitations;
6. conclusion.

Use the evidence-bearing Results wording as the ceiling. Record every stronger
restatement as a finding.

## Mechanism language

Separate three levels:

- `association`: variables move together;
- `intervention`: a controlled change alters the endpoint;
- `mechanism`: evidence distinguishes the proposed causal path from credible
  alternatives.

Use `consistent with` or `supports` when the evidence does not close the
alternative explanations. Name the unresolved alternative rather than replacing
it with vague caution.
