# Technical-route census — direction recovery gate

Use this gate only when the next technical direction is unclear, several old
routes appear reusable, or someone proposes another algorithm before the
control object and evidence gap are settled. It is a `scratch` audit over
existing evidence. It does not authorize ANDES, training, a title change, a
claim, or a new round.

## Unit of classification

Classify **route episodes**, not directories and not every checkpoint. A route
episode is the smallest group of records sharing all four items below:

1. physical control object;
2. actuator/action authority;
3. control or learning architecture;
4. scientific comparison question.

Changing only seed, network width, learning rate, or evaluation wrapper stays
inside one episode. A changed physical port, information pattern, deterministic
anchor, or distributed execution semantics starts another episode.

Implementations and scientific evidence are separate fields. Reusable code
does not make an old result transferable to the selected manuscript line.

## The five families

Assign every inventoried route exactly once. These are project classification
labels, not scientific conclusions:

| ID | Family | Primary discriminator |
|---|---|---|
| F1 | Algorithm-first direct M/D reinforcement learning | The VSG inertia/droop action is fixed; the main intervention changes learner, memory, critic, training, or ensemble. |
| F2 | Classical baseline plus multiscale/neural residual | A classical controller carries the main response and a learned, shared, edge, pulse, or handoff layer seeks incremental value. |
| F3 | Classical distributed storage active-power control | Node/edge storage power is coordinated by deterministic distributed control without neural training. |
| F4 | Model-first control and training-necessity audit | Model, authority, deterministic bridge, headroom, information, or feasibility gates decide whether training is warranted. |
| F5 | One-VSG-one-agent object reconstruction | Runtime ownership is rebuilt so every physical VSG has an independently intervenable, matched action port before MARL. |

`NON-ROUTE` and `UNRESOLVED` are accounting dispositions, not sixth and seventh
families. Use `NON-ROUTE` for pure infrastructure, governance, manuscript, or
metric-audit records. Use `UNRESOLVED` when authoritative records do not permit
one family assignment; unresolved records block route selection.

## Procedure

1. Freeze the selected manuscript line with `session_context.py --line
   <line-id>`. Record its title, object, current stage, stop rules, and write
   authority. A census never overrides them.
2. Discover route episodes from all of these surfaces: current claim cards;
   completed round plans/verdicts; bound feeds and results manifest; relevant
   ADRs; every paper `LINE.md`; and registered research records. Do not infer a
   route from a folder name alone.
3. Make one inventory row per route episode. Cite at least one authoritative
   repo-relative record for each row. Keep superseded, invalid, legacy, and
   negative episodes visible; they are not omissions.
4. Assign every inventory row exactly once to F1–F5. For each assignment record:
   trained, physical execution, genuine multi-agent execution, status,
   implementation reuse, evidence transferability, title fit, headroom,
   observed outcome, fatal boundary, and next decisive gate.
5. Reconcile coverage: `inventoried = assigned`; no duplicate route IDs; no
   unresolved records hidden in prose. Run:

   ```powershell
   python memory/tools/technical_route_census.py validate `
     tmp/<line-id>/technical-route-census.json
   ```

6. Apply the route decision rules below. Render the review table with:

   ```powershell
   python memory/tools/technical_route_census.py render `
     tmp/<line-id>/technical-route-census.json
   ```

7. Keep the census JSON/Markdown in `tmp/<line-id>/`. If its decision must
   persist across sessions, convert only the terminal decision into the normal
   project authority named by `CLAUDE.md`; do not create a route ledger or copy
   experimental facts into `LINE.md`.

## Eligibility and terminal decision

A route is experiment-eligible only when all are true:

- its literal object, actuator, distributed semantics, and target metric fit
  the selected manuscript title;
- no current claim, feed, ADR, route contract, or `LINE.md` stop rule closes it;
- its missing evidence is one falsifiable gate, not an algorithm sweep;
- authority and non-learning headroom have passed when the proposed learner
  depends on them;
- one bounded next experiment can distinguish success, pivot, and stop.

Return exactly one terminal outcome:

- `PROCEED`: select exactly one eligible route and name its next gate. Only the
  normal round workflow can authorize execution.
- `MANUSCRIPT-ONLY`: current evidence and stop rules leave no eligible
  experiment route under the selected paper authority. Close the paper with
  bounded claims or make a separately authorized title/project decision.
- `UNRESOLVED`: source conflict or missing authoritative record prevents a
  classification. Name the missing record and do not experiment.

Do not rank families by arbitrary weighted scores. Hard title/evidence/stop
gates dominate attractive historical performance. “Best old metric,” “most
code,” and “neural network present” are not eligibility conditions.

## Completion contract

The gate is complete only when:

- every discovered route episode has one family assignment;
- every row has a resolvable authoritative pointer;
- implementation reuse and evidence transferability are separately stated;
- current negative and superseding evidence is included;
- unresolved count is explicit;
- exactly one terminal outcome and one authorized next action are present;
- the validator passes.

Anything less is an informal summary and cannot select the next experiment.
