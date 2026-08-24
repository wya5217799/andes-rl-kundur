# Comparison Identifiability Gate

Use this gate before freezing a prospective comparison, before argument design
or claim-bearing prose, and after any material comparator or claim change. It
sets the design target and inference ceiling; project governance still
authorizes experiments, and evidence and domain reviews still verify results.

## Comparator contract

For every arm, record evidence-backed values for:

- scientific object actually instantiated;
- controller inputs and any privileged, global, estimated, or communicated
  information;
- action dimension, coordinates, feasible set, actuator path, limits, timing,
  and post-processing;
- execution location, aggregation, communication, deployment assumptions, and
  training-only centralized information;
- model capacity, optimization, interaction, tuning, seed-selection, and
  evaluation-data budgets;
- primary estimand and unit of analysis.

Then state the observed or planned contrast, the single factor to be
attributed, every other causally load-bearing difference, the narrowest
identified claim, and the untested class-level or deployment claims.

Label global statistics as global information, central projection as central
execution, and expanded action coordinates as an action-space difference.

## Identification checks

Answer every check explicitly:

1. Do the arms share physical action coordinates, feasible set, actuator
   limits, and timing? Otherwise identify action-space value.
2. Do they share deployment information? Otherwise identify the combined
   information-and-architecture contrast or add the missing factorial arm.
3. Do aggregation, communication, parameter sharing, capacity, training,
   tuning, seed selection, or evaluation data differ? Preserve each as an
   alternative explanation.
4. Does the estimand concern one implementation, an algorithm family, an
   information pattern, or a deployment architecture? Use the narrowest tested
   object.
5. Do title, abstract, contributions, results, limitations, and conclusion use
   the same causal object and inference ceiling?

## Decision

Return one decision:

- `ALLOW`: the comparison identifies the named factor for the proposed bounded
  claim, with residual differences disclosed.
- `QUALIFY`: the result is usable, but several factors differ or only one
  constrained instantiation was tested. Use the executed comparison as the
  claim ceiling and list stay-out claims.
- `BLOCK`: the attribution is false or unidentified, a load-bearing mismatch is
  undisclosed, or one constrained instance is presented as an entire class.
  Repair the design or narrow the claim before proceeding.

Complete the gate only when every arm has every field populated or explicitly
marked unavailable, every load-bearing difference has an inference
consequence, and one allowed claim plus its stay-out claims covers every
headline location. Missing load-bearing information returns `BLOCK`.

Use this output:

```text
Decision: ALLOW | QUALIFY | BLOCK
Executed comparison:
Identified estimand:
Allowed claim:
Required qualification:
Stay-out claims:
Repair needed before comparator freeze or drafting:
```

## Negative-result rule

Keep three levels distinct:

- `A did not outperform B`: observed comparison;
- `A has no demonstrated incremental value in this executed formulation`:
  bounded evidential conclusion;
- `the method or architecture class has no value`: class-level conclusion that
  requires representative coverage or a justified impossibility argument.

Phrase failure to show superiority as bounded non-demonstration. Reserve
architecture-specific value for comparisons without weaker information,
action, execution, or budget alternatives.

## Canonical failure example

One arm applies a shared local mapping several times, centrally pools the
outputs, and executes one scalar action; another consumes the joint observation
and directly emits the same scalar. This identifies the shared scalar
factorization relative to the joint mapping. Return `QUALIFY` for that narrow
claim and `BLOCK` for conclusions about multi-agent methods as a class, fully
decentralized execution, communication, or vector-valued local coordination.
