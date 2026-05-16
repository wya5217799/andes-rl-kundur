# R45 plan — Escalate R44 deferrals + s52 reproducibility + SAC long

**Date**: 2026-05-17
**Type**: experiment (Q-0001 escalation × 2 + SAC long-training probe + s52 anchor reproducibility)
**Status**: DRAFT — awaiting R44 verdict landing (Codex session in flight)

**Trigger**: R44 (concurrent Codex session) executed a deliberately narrow
slice of the Q-0001 candidate ladder + a HAWE actor-pool exploration that
surfaced an unexpected result. Specifically:

- **R44-β** (Q-0001 cand 1): no_control G4-preserved 6-axis = **0.101**, inside
  the [0.09, 0.12] pass band → no_control ranking robust to G4 preservation.
  R44 closed-negative at this rung and **deferred** the higher rungs (R21
  s49 rerun, R41-B retrain) under the "no escalation unless > 0.05 shift"
  rule. From a `/grill-with-docs` review of R43's "what R43 does not
  establish" list, the R21 + R41-B rungs are still load-bearing: paper
  headline depends on R21 0.444, and the production recommendation (CLM-0047)
  depends on R41-B 0.275. The grill argued for one-shot resolution rather
  than ladder escalation.
- **R44-α** (HAWE actor-pool exploration): s52-anchored configurations
  reached geo-mean 6-axis = **0.338** (75%) / **0.347** (90%), crossing
  the +10% threshold over R43-β's 0.310 uniform HAWE-3. **But each config
  was run at a single eval seed (=42)**. Reproducibility across eval seeds
  is untested.
- **SAC long-training probe** (3 seed × 200 ep): explicitly out of scope
  in R44 plan. Grill argued for closing the "75ep insufficient" reproach
  permanently — cheap in compute (~30 min wall via 3-parallel WSL) and
  prevents future re-litigation.

This plan packages the four R44-deferred experiments into a single round.

## Part α — s52-anchored HAWE reproducibility (verify R44-α 0.347 / 0.338)

**Question**: Are R44-α's `hawe_td3_s52_anchored` configurations
(50/75/90% anchor weight on s52) reproducible across multiple eval seeds,
or is the single eval at seed=42 a lucky disturbance trajectory?

**Method**: Re-run `scripts/eval_ensemble.py` with the three anchored
configs at eval seeds {42, 43, 44}. Score via
`paper_grade_axes.evaluate_trace`, geo-mean across LS1+LS2 per seed; report
3-seed mean + range.

Configs (mirroring R44-α exactly):

```bash
# 50% anchor
--ckpt-dirs results/td3_phi0_200ep_s52 results/td3_norm_s51 results/td3_norm_s49 \
--suffixes  best best best  --agg weighted --weights 0.50 0.25 0.25

# 75% anchor
--weights 0.75 0.125 0.125

# 90% anchor
--weights 0.90 0.05 0.05
```

**Predictions** (mapped to grill 5-tier on best 90% anchor vs uniform 0.310):

- 3-seed mean ∈ [0.305, 0.315] → R44-α 0.347 was eval-seed luck; sweep
  flat band; close as "HAWE robustness limit hit"
- 3-seed mean ∈ [0.315, 0.325] → microweight (+1.5-5%); report as finding
  but don't switch production recipe
- 3-seed mean ∈ [0.325, 0.340] → +5-10% switch-production band; new CLM
  recommends s52-anchored HAWE; open Q "hold-out CV needed before paper
  cites"
- 3-seed mean ∈ [0.340, 0.400] → matches R44-α single-eval; ≥ +10%; new
  CLM + new Q on stability
- 3-seed mean > 0.40 → big news; open Q "non-lucky path explanation"

## Part β — Q-0001 cand 2: R21 lucky s49 G4-preserved

**Question**: Does the R21 lucky single-seed s49 6-axis = 0.444 (CLM-0005)
survive switching to `V4Config.zero_g4_inertia=False`? If R21 collapses
< 0.30, the paper headline is G4-zeroed-only.

**Method**: Run `eval_ddic.py` on `results/v4_h50_s49/agent_*_best.pt` with
a one-off driver that flips `zero_g4_inertia=False` (mirror
`scripts/_r44_eval_no_control_g4preserved.py`'s pattern). Two scenarios
(LS1 + LS2), eval seed 42, single eval (R21 is deterministic-policy under
SAC mean-action eval).

**Pass criterion** (grill 6a, applied to single-seed eval): geo-mean ≥
0.40 → R21 ranking preserved; ∈ [0.30, 0.40] → mild collapse, paper
headline still valid; < 0.30 → ranking flipped, headline regen Q opens
(grill Q-0004).

## Part γ — Q-0001 cand 3: R41-B 3-seed retrain G4-preserved

**Question**: Does TD3 + normalized penalty (production recipe per CLM-0047)
still reach geo-mean ≥ 0.22 (= 0.275 × 0.80) under G4-preserved training,
or is CLM-0047 G4-zeroed-only?

**Method**: 3 retrain runs via `scripts/train.py`:

```bash
python scripts/train.py --algo td3 --normalize-actions --episodes 75 \
    --seed {49,50,51} \
    --config-override zero_g4_inertia=False \
    --out-dir results/td3_norm_g4preserved_s{49,50,51}
```

(If `train.py` doesn't expose a config-override flag, add a 2-line patch
or use an env-var hook before the run; this is the only new code R45
needs beyond eval drivers.)

Score with `paper_grade_axes.evaluate_trace`, geo-mean across LS1+LS2,
report 3-seed mean + range.

**Pass criterion** (grill 6a):

| 3-seed mean | Verdict | Schema action |
|---|---|---|
| ≥ 0.22 | production stable under G4-preserved | CLM-NNNN finding only; CLM-0047 unchanged |
| [0.15, 0.22) | production G4-dependent, caveat needed | new finding CLM-NNNN; CLM-0047 unchanged (decision still valid under V4 default env) |
| < 0.15 | production recommendation invalid under G4-preserved | correction CLM-NNNN supersedes CLM-0047 |
| NaN / divergence | env unstable under G4-preserved | new finding; CLM-0047 stays; possibly open Q "V4 + G4-preserved training stability" |

**Side benefit**: 3 new TD3-norm-G4-preserved actors → free HAWE eval
extension (~30 s) on the new pool, answering "does R43-β's +11% lift hold
under paper-faithful G4?".

## Part δ — SAC long: 3 seed × 200 ep, default V4 env (G4 zeroed)

**Question**: Does SAC + normalized penalty escape the R43-α 75ep
attractor (mean 0.117, range [0.106, 0.136]) at 200 ep? Or does it plateau
in the 0.10-0.14 band, quadruple-confirming H3?

**Method**: 3 retrain runs, identical to R43-α except `--episodes 200`:

```bash
python scripts/train.py --algo sac --normalize-actions --episodes 200 \
    --seed {49,50,51} --out-dir results/sac_norm_200ep_s{49,50,51}
```

Score 3 ways:
1. `best ckpt` 6-axis (training-time max) — primary metric, matches R43-α
2. `final ckpt` (ep=200) 6-axis — sanity
3. Per-episode 6-axis trajectory if `train.py` logs eval midway — to
   detect lucky-revisit (best ckpt jumps in ep > 75)

**Pass criterion** (grill 6c):

| best ckpt 3-seed | Verdict |
|---|---|
| ∈ [0.10, 0.14] | H3 quadruple-confirmed; SAC line **permanently closed** for paper-faithful production |
| > 0.20 in any seed | lucky-revisit at long training; new finding "SAC entropy occasionally accesses lucky basin during long training"; open Q "stability of access" |
| ∈ [0.14, 0.20] | unclear; new finding; consider 1 more seed |
| NaN / divergence | new finding "SAC normalized 200ep unstable" |

Threshold 0.20 ≈ 5.5σ above R43-α 75ep mean (using R43-α std ≈ 0.015).

## Order

Sequential due to WSL 3-parallel hard limit:

```
1. Part α (s52 reproducibility)         ~3 min  (3 evals × 3 configs)
2. Part β (R21 s49 G4-preserved eval)   ~5 min
3. GATE: R21 ≥ 0.30?
   ├─ NO  → motif pivots to "paper headline regen candidate search";
   │        open Q-0004 (paper revision); CONTINUE — R44-β PASS at
   │        no_control rung is no longer sufficient; need to know
   │        whether ANY headline survives
   └─ YES → continue
4. Part γ (R41-B retrain × 3 seed)      ~30 min  (3-parallel WSL)
5. HAWE on new G4-preserved actors       ~30 s   (free extension)
6. Part δ (SAC long × 3 seed)           ~30 min  (3-parallel WSL)
7. R45 verdict writeup
```

Total wall: **~70 min** (gate-fail does NOT abort; same path, different
framing — per grill question 9).

## Addresses Questions

- **Q-0001** (G4 inertia) — partially closed by R44 at no_control rung;
  R45 closes the remaining cand 2 + cand 3 rungs. Final closure happens
  in R45 verdict if both pass; new Q-NNNN opens if either fails.

## Out of scope

- 22-ckpt H₀ sweep under G4-preserved (~6h × 4 seeds) — deferred to R46+
  if R45 reveals headline regen necessary.
- Curriculum learning / PPO from scratch — separate big-bet round, R46+.
- HAWE simplex 0.2-step 21-point sweep — R44-α already explored
  anchored 50/75/90 + uniform + union; the simplex "extremes + center"
  manifold is covered. The mid-density sweep (60/80%) is not run unless
  Part α reveals a non-monotone trend in 50→75→90.
- Re-running CLM-0008 ranker-drift (R44 plan flagged no_control = 0.094
  vs CLM-0008's 0.104 as orthogonal ranker drift; do not touch in R45).

## Risks

- **R44 verdict not yet landed**: R45 plan references R44 results JSONs
  that exist on disk but the Codex session may revise them or rename
  during verdict commit. Pin specific JSON filenames in execution scripts
  as snapshots (copy to `results/research_loop/r45_inputs/` before R45
  runs) to avoid moving-target risk.
- **WSL slot contention with Codex's housekeeping pytest**: Codex
  session was running pytest at 18:43; R45 launch must verify WSL
  python slot availability before starting Part γ / δ.
- **Q-0001 cand 3 needs `train.py` config-override hook**: if the
  current CLI doesn't accept `zero_g4_inertia=False`, the patch must
  land cleanly without conflicting with Codex's recent `paper_path.py`
  / `monitor.py` modifications (visible in `git status`). Inspect both
  diffs before patching.
- **R44 verdict may reframe**: if R44 verdict opens its own follow-up Q
  (e.g. "s52 anchor reproducibility" — likely), Part α may duplicate it.
  Coordinate Q-NNNN numbering after R44 lands.

## New code budget

~110 lines split across:
- 1 driver for Part β (R21 G4-preserved eval), ~30 lines mirroring
  `_r44_eval_no_control_g4preserved.py`
- 1 patch to `scripts/train.py` accepting `zero_g4_inertia` override
  (~10 lines) OR an env-var hook + 5-line script wrapper
- 1 driver for Part α (re-run 3 anchored HAWE configs at 3 eval seeds),
  ~40 lines wrapping `eval_ensemble.py` calls
- 1 score consolidator for Part γ / δ (~30 lines), mirroring
  `_r41_score_B_normalized.py`

## Schema plan (post-R45)

Expected output (per grill question 8a, granularity (ii) = 4 CLM):

- **CLM-NNNN+0** Part α: s52-anchored HAWE 3-eval-seed reproducibility
- **CLM-NNNN+1** Part β: R21 s49 G4-preserved
- **CLM-NNNN+2** Part γ: R41-B G4-preserved 3-seed
- **CLM-NNNN+3** Part δ: SAC long 200ep 3-seed

Potential additions:

- **CLM-NNNN+4** (correction, supersedes CLM-0047) — only if Part γ
  3-seed mean < 0.15
- **Q-NNNN+0** "paper headline regen needed" — only if Part β R21 < 0.30
- **Q-NNNN+1** "SAC lucky-revisit mechanism" — only if Part δ any seed
  best > 0.20
- **Q-NNNN+2** "HAWE s52 anchor hold-out CV" — only if Part α 3-seed
  mean ∈ +5-10% band

ID numbers TBD after R44 verdict assigns its own CLM range.
