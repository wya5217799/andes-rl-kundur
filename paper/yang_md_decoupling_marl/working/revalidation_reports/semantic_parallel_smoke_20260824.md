# Yang M/D old-conclusion revalidation — parallel semantic smoke

> Governance status: quarantined pre-repair3 diagnostic. The later authorized
> repair3 capacity and semantic rehearsal supersede this smoke for authority;
> this report cannot enter a formal seal, claim, or manuscript number.

## Scope

This report covers only the Yang M/D decoupling manuscript line. Eleven
independent WSL/ANDES pytest commands were launched concurrently on 2026-08-24.
They exercised 13 registered test cases. No training, formal bank, paper result
number, or non-Yang research line was touched.

The concurrently running capacity ladder is excluded from capacity evidence
because these tests added host load after that ladder began. It is a stress run
only and must not set formal worker count or ETA.

## Frozen inputs

- physical authorization SHA-256:
  `d16e17b77fb36973d021db43db31d997e3b1d18c20817e2458ed52a9225a6a3e`
- runner file SHA-256:
  `62b894c1286fd7a18a1f8b5c37178b96f50b34572a5a91d910570684dba90bd4`
- runtime: WSL, ANDES 2.0.0, `/home/wya/andes_venv/bin/python`

## Results

- All seven device/system-base invariants passed in real ANDES: zero-action
  preservation, telemetry/readback equality, device-system-device round trip,
  heterogeneous card preservation, nonzero branch/clamp/slew units,
  energy-port slow-channel preservation, and reset repeatability.
- Both V5 heterogeneous-D build configurations passed.
- The distributed-residual device-base readback boundary passed.
- The physical/control nominal-frequency metadata check passed.
- The two first-step numerical regression comparisons did not execute because
  the corrected post-freeze baseline files are intentionally absent. This is a
  fail-closed missing-input result, not a physical-semantic failure and not
  evidence that the old numerical conclusion is correct.

Aggregate: 11 semantic/boundary cases passed; 2 numerical-regression cases were
blocked by missing corrected baselines; 0 executed semantic case failed.

## Output hashes

| Job | SHA-256 | Result |
|---|---|---|
| 01 | `0236d959497cca06a3b22a367627883fd613dfe1b6d3832cd778dea2926c275b` | pass |
| 02 | `2d44ec222af3536449ccbad4439ca0e6fb4a22c900af8b2454e70f4a50a6e38b` | pass |
| 03 | `9b9d775071d62ea9100ba472d0dcf382a99549b4d9993371f2c6afd16785ec03` | pass |
| 04 | `806a9cc86590dc707cd7e0b46e4cb7695510067a02ceb3fd1da724d24144d4d5` | pass |
| 05 | `8c1ee96acda7d1a52eb6b083614cd479c49c555fd7d52180b8944ea7fb5f9525` | pass |
| 06 | `43fed8850c569b7431f344154ea7171c1d62ba89d0757b56b40ba23155fd743a` | pass |
| 07 | `b11fe566595402793b378ab8ca557a708f399166ed42c0d2d0d943c913c17c46` | pass |
| 08 | `98a30c6a8c761eaaf652fdf048a8766b92830663def04875c1a21b21f1993ef1` | 2 pass |
| 09 | `6d6d703218b47837c02273c32476c4dcb4ac7ba6c38a791ef441f504fbb2dbca` | pass |
| 10 | `16e81ab0316ce30b0b081decf3f40241858466bca9360bb25b8b5a19a2db6536` | 2 blocked |
| 11 | `140fb53e59af5a728200462970fe61577683014aa75db6e9e7971e54621d3048` | pass |

## Old-conclusion assessment and route decision

The corrected M/D semantics are operationally plausible across every executed
real-ANDES invariant. This supports retaining the current correction route; it
does not revalidate any old time-domain number, deterministic ranking, MARL
failure count, or source-factor effect.

Decision: **retain old route**, do not redesign the controller or learner yet.

Next single gate: finish the serial, create-only semantic rehearsal/report on a
cleanly measured capacity context. If it passes, run only the 12-trajectory
direct-M/D canary. If it fails, stop and redesign the M/D semantic successor.
