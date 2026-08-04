# R294 Stage E — explicit decentralized-execution verification

The post-Stage-D publication audit found that the neighbour-sparse DAPI law
was evaluated through one vector controller object.  Although every row used
only local and ring-neighbour values, that software seam did not itself prove
independent local-agent execution.  Stage E is a prospective implementation-
equivalence repair; it does not select a new controller, gain, scenario,
endpoint, or performance threshold, and it does not modify Stage D.

Four separate `LocalDAPIAgent` objects each own one scalar integral state and
one scalar `P_i` output.  Agent `i` receives only its own frequency, the two
declared ring-neighbour frequencies, the two neighbour integral messages, and
its own previous projection feedback.  A simulator harness routes these local
values and commits simultaneous messages; it computes no global frequency,
joint action, or action aggregation.

The fixed Stage-D gain (`Kp=2.0`, `Ki=0.2`, `Ksync=1.0`, consensus gain
`1.0 1/s`) is rerun on the same 12 Stage-D scenarios for 100 steps.  Each new
local-agent trajectory is paired to the already sealed Stage-D DAPI record.
The gate requires:

- 12/12 new trajectories complete with every original physical/action guard;
- all source and record sidecars verify;
- maximum absolute difference in requested power, commanded power, physical
  frequency deviation, and SOC is at most `1e-10`; and
- all five registered common/differential endpoint differences are at most
  `1e-12` in absolute value.

Pass means the Stage-D DAPI outcomes are numerically transferable to the
explicit local-agent execution within this deterministic single-process ANDES
simulation.  It does not test real communication delay/dropout, multiple
processes/controllers, embedded deployment, or MARL.
