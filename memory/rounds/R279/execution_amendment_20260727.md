# R279 prospective execution-only amendment

**Recorded:** 2026-07-27T11:14:52+08:00  
**Trigger:** The user explicitly requested faster completion using the available hardware.  
**Applies before:** the fresh-bank screen seal, formal seal, and every trace in both stages.

## Change

- Increase fresh-bank and formal execution shards from 3 to 8.
- Increase the formal per-shard hard timeout from 60 minutes to 180 minutes.

## Scientific contract unchanged

This amendment changes scheduling only. It does not change the candidate-bank
seed, scenarios, feasibility rules, redraw policy, controllers, training seeds,
checkpoints, action contract, trajectory horizon, endpoint definitions,
bootstrap seeds, statistical thresholds, guards, retry policy, overwrite
policy, or decision tree.

The fresh-bank and formal seals must include this amendment and the modified
launcher/source hashes. No fresh-bank or formal result existed when this
amendment was recorded.

## Capacity evidence

- Host: 32 logical CPUs and 31.2 GB RAM.
- At three concurrent training workers: about 28--32% total CPU utilization.
- WSL at amendment time: 23 GiB total memory and about 16 GiB available.
- Eight workers retain substantial CPU and memory headroom while avoiding an
  untested jump to the full logical-core count.

## Stop rule

If the eight-worker execution produces a retained failure, timeout, resource
error, or provenance mismatch, preserve it and follow the registered
`INVALID`/no-overwrite rules. Do not change concurrency again based on
performance results.
