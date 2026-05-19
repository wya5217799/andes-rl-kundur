---
round: R89
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R89 plan — R09 sideline revival: ANDES Kundur vs paper parameter audit

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究". CLAUDE.md "R09 副线没做完" + R08 §2 Finding 2 (H=300
仍 max_df 2× paper, 归因 line/load/SBASE/solver) 12 天前提出但从未解决.
**Parent**: R08 verdict §3 R09 副线 plan (skipped); R88+ all RL-mechanism path;
this round is **power-systems audit**, not RL.

## Why this is meaningful + non-conflicting

R83 (obs space, training, WSL TDS), R85 (classical baseline, eval, WSL TDS),
R86 (cross-ckpt critic forensics), R87 (per-step on-manifold critic), R88
(?, plan TBD) — all are **RL-internal** explorations of why algo plateau.

**Counter-hypothesis (NEVER tested)**: 91-round algo plateau may be partly
explained by **ANDES simulating the wrong physics** vs paper. If ANDES Kundur
≠ paper Kundur in load distribution / nominal frequency / damping
distribution / line impedance, then:
- The plateau is partially "ANDES-local" rather than algorithm-fundamental
- R57-R85 RL conclusions are conditional on a particular flavour of Kundur
- Paper claims of RL transferability are weaker than the data suggests

R89 is pure **audit / inspection**, zero training, zero WSL TDS, zero R83
conflict. Just reads ANDES `kundur_full.json` + V4 env source + compares
with paper §IV-A + Kundur 1994 textbook references in
`paper_constants.py`.

## Initial findings already in hand (this conversation's exploration)

| # | Finding | Severity |
|---|---|---|
| F1 | **ANDES GENROU `fn=60.0 Hz`** in all 4 machines, NOT 50 Hz; V4 `base_env.py:441` does `freq_hz = omega * 50` to convert PU → Hz. **Unit conversion error**: env underreports max_df by 50/60 = 0.833×. ANDES is simulating a 60 Hz system but project labels output as 50 Hz. | **🚨 CRITICAL** |
| F2 | ANDES default `kundur_full.xlsx` has only **2 PQ loads at Bus 7 + Bus 8** (transmission, 230 kV); paper Sec.IV-A has ESS-co-located loads at Bus 14/15. V4 env `_build_system()` (line 290) adds NEW PQ at Bus 14/15 for disturbance, but the existing Bus 7/8 loads remain (different topology than paper). | **HIGH** |
| F3 | All 4 ANDES GENROU machines have `D=0` (no machine-side damping); paper Eq.1 uses lumped `D_es,i ≠ 0`. Effective system damping in ANDES comes only from TGOV1 governor droop (R=0.05) + line resistance + transient stator/rotor coupling. | MEDIUM |
| F4 | All 4 TGOV1 governors are **u=1.0 active** by default in ANDES kundur_full. Paper Sec.II-A explicitly neglects inner-loop dynamics — TGOV1 is a primary-frequency response governor, not "inner loop" but adds damping. R03/R04/R08 governor-wiring saga: this is the very feature R08 Finding 3 called "completely ineffective", but the JSON shows u=1.0 on all 4. | NEEDS VERIFICATION |
| F5 | ANDES kundur_full PQ loads have **q0 < 0** (capacitive injection: -0.735 and -0.899 pu). Unusual for "loads" — may include co-located shunt cap compensation. Affects voltage profile and damping. | LOW |

## Wave plan

### W1 (~30 min): write + run `scripts/r89_parameter_audit.py`

Produce structured comparison report (zero ANDES TDS):
1. Load `kundur_full.json` (already cached at `probes/r89_andes_kundur_full.json`)
2. Compare GENROU H/D/Sn vs `paper_constants.KUNDUR_AREA1_H` / `KUNDUR_AREA2_H` / `KUNDUR_TOTAL_GEN_MVA`
3. Tabulate Line impedances + tie-line layout
4. Check TGOV1 active state (u=1.0 vs paper's "no governor")
5. Detect fn mismatch + compute corrected max_df scaling factor
6. Save report to `results/r89_kundur_audit/{summary.json, audit_report.md}`

### W2 (~20 min): write `tests/test_v4_fn_consistency.py` regression check

Lock in finding F1 with a regression test:
```python
def test_andes_fn_matches_env_fn():
    """Detect 50/60 Hz mismatch between ANDES GENROU.fn and base_env.FN."""
    env = AndesMultiVSGEnvV4()
    ss = env._build_system()
    andes_fn = float(ss.GENROU.fn.v[0])  # all 4 same
    env_fn = env.FN
    assert abs(andes_fn - env_fn) < 0.1, \
        f"ANDES GENROU.fn={andes_fn} ≠ env.FN={env_fn} — unit conv error"
```
This test will currently **FAIL** (assertion catches the mismatch). The
failure is the desired R89 deliverable; deliberate "RED" regression
marker on a known bug.

### W3 (~30 min): write verdict + 3 claims + PI chat brief

- CLM-NEW1: F1 fn=60/50 mismatch documented + scaling impact
- CLM-NEW2: F2 load topology mismatch documented
- CLM-NEW3: aggregate audit finding — "R09 副线 2× max_df residual partial root cause"
  (estimated 17% from F1, rest unaccounted — invites R90+ to deepen)

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py
/ 任何 R57+ ckpt / 任何已有 test / R83/R85/R86/R87/R88 work.

新建:
- `probes/r89_andes_kundur_full.json` (already exists, parsed copy of ANDES file)
- `scripts/r89_parameter_audit.py` — audit driver
- `results/r89_kundur_audit/` — output dir
- `tests/test_v4_fn_consistency.py` — regression test (deliberately RED)
- `memory/rounds/R89/{plan.md, verdict.md}` — round bundle
- 3 CLM-NEW claims

## Gate / outcome categories

| outcome | meaning | next |
|---|---|---|
| All 5 findings confirmed + new mismatches found | ANDES Kundur ≠ paper Kundur substantially | R90+ either (a) fix V4 to be paper-faithful (high cost, breaks regression) or (b) document as ADR-0006 deviation |
| F1 + F2 confirmed only | 17% scaling correction + topology layout difference | accept as "ANDES Kundur replication deviation", lock in as ADR-0006 |
| F1 turns out to be intentional / handled elsewhere | bug-free, my audit wrong | close R89 negative, no claim |

## Cross-references

- R08 verdict §2 Finding 2 + §3 R09 副线 (12-day-old TODO)
- CLM-0040 (ZERO_G4_INERTIA hack, related G4 paper-deviation)
- CLM-0051 (R44-β: V4 no-control max_df 0.182 / 0.169 at H=300)
- ADR-0004 (V5 env paper-deviation framing — similar audit / framing approach)
- ADR-0005 (ANDES-only, drop Simulink 1-to-1)
- paper §IV-A (Kundur 2-area + 4 ESS + W1/W2 modifications)
- `docs/paper/kd_4agent_paper_facts.md` §6.1 (paper Kundur topology canonical)
- `src/andes_rl_kundur/probes/andes_common/paper_constants.py` (KUNDUR_AREA1_H etc.)
