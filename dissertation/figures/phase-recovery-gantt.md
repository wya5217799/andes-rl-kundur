# Figure K — Stage 2 SPEC-8 recovery plan with acceptance gates G1–G6

Phase-level Gantt of the four-phase physical-model recovery plan (B–E), preceded by the algorithm-level interventions actually executed within the project's time budget (Phase A: action smoothing, confirmed as a path-blocker; Phase 12: heterogeneous-actor ensemble, which closed the overall G1 gate at 0.554). Acceptance gates G1–G6 are pre-registered (Section 4.4); G1 is shown closed, G2–G6 pending the planned physical-model interventions.

```mermaid
%%{init: {"theme": "default", "themeVariables": {"fontSize": "14px"}, "gantt": {"barHeight": 22, "fontSize": 13, "leftPadding": 130, "rightPadding": 30}}}%%
gantt
    title Stage 2 SPEC-8 recovery plan: phases A-E + acceptance gates G1-G6
    dateFormat  YYYY-MM-DD
    axisFormat  %m-%d

    section Algorithm-level (executed)
    Phase A action smoothing (path-blocker confirmed) :done, pa, 2026-05-06, 1d
    Phase 12 heterogeneous ensemble (G1 closed)       :done, p12, after pa, 2d

    section Physical-model (planned)
    Phase B IEEEG1 governor + EXST1 AVR               :crit, pb, after p12, 3d
    Phase C rebaseline H0 = 50 (paper-literal range)  :crit, pc, after pb, 2d
    Phase D 5-seed retrain on V3 env (6-8 hr each)    :pd, after pc, 5d
    Phase E re-render Yang Fig.6/7/8/9 + verdict      :pe, after pd, 2d

    section Acceptance gates
    G1 overall >= 0.5  (closed by Phase 12 = 0.554)        :milestone, g1, after p12, 0d
    G2 max-dF <= 0.20 Hz (pending physical-model phases)   :milestone, g2, after pd, 0d
    G3 settling <= 6 s   (pending)                         :milestone, g3, after pd, 0d
    G4 dH range >= 100   (pending)                         :milestone, g4, after pd, 0d
    G5 smoothness sigma <= 1.0 (pending)                   :milestone, g5, after pd, 0d
    G6 DDIC > adaptive > no-control (pending)              :milestone, g6, after pd, 0d
```
