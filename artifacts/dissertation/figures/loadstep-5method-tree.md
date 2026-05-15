# Figure F — Six resolution paths for the Simulink Kundur load-step path-blocker

Six technical paths attempted on the Simulink Kundur backend to reproduce Yang Sec. IV-C's literal load-step disturbance specification (LS1 −2.48 p.u. at Bus 14, LS2 +1.88 p.u. at Bus 15). Five failed for individually-traceable reasons; only M5 (per-source Pm-step proxy, Plan B) survived as the project's evaluation default, accepted with an explicit physical-meaning deviation (Pm ≠ Pe). The PTDF dispatch attempt was an additional architectural attempt that also failed structurally because same-sign Pm dispatch destroys Yang's relative-synchronisation reward formula. This is the project's deepest engineering finding on the Simulink leg (§2.1.7).

```mermaid
%%{init: {"flowchart": {"defaultRenderer": "elk", "htmlLabels": true, "curve": "basis"}, "themeVariables": {"fontSize": "12px"}}}%%
flowchart TB
    Need["<b>Requirement (Yang Sec.IV-C)</b><br/>-2.48 p.u. load step at Bus 14<br/>+1.88 p.u. load step at Bus 15"]:::root

    M1["<b>M1:</b> Series RLC R-block<br/>Resistance = Vbase^2 / amp"]
    M2["<b>M2:</b> 3-Phase Breaker + RLC Load<br/>(Discrete powergui mode)"]
    M3["<b>M3:</b> Controlled Current Source<br/>at Bus 14 / Bus 15 (Phasor)"]
    M4["<b>M4:</b> CCS at load-centre Bus 7 / Bus 9<br/>(Option E)"]
    M5["<b>M5:</b> per-source Pm-step proxy<br/>(Plan B)"]
    M6["<b>+:</b> PTDF multi-source dispatch<br/>(architectural attempt)"]

    F1["FAIL<br/>FastRestart compile-freezes<br/>Resistance expr<br/>(5 scenarios bit-identical)"]:::failed
    F2["FAIL<br/>FastRestart compile-freezes<br/>SwitchTimes + ActivePower"]:::failed
    F3["FAIL<br/>~40x weaker than Pm-step<br/>(electrical-distance attenuation)"]:::failed
    F4["FAIL<br/>~62x weaker than paper LS1<br/>(Phasor CCS Init limitation)"]:::failed
    F5["PARTIAL<br/>signal applies but Pm != Pe<br/><b>chosen as evaluation default<br/>with documented deviation</b>"]:::accepted
    F6["FAIL<br/>same-sign dispatch destroys<br/>relative-sync reward r_f<br/>(branch frozen at R4)"]:::failed

    Need --> M1 --> F1
    Need --> M2 --> F2
    Need --> M3 --> F3
    Need --> M4 --> F4
    Need --> M5 --> F5
    Need --> M6 --> F6

    Verdict["<b>Verdict:</b> 5 of 6 paths blocked.<br/>M5 (Pm-step) accepted as default<br/>with explicit physical-meaning deviation;<br/>load-step path-blocker is structural,<br/>not removable within project time budget."]:::verdict
    F5 ==> Verdict

    classDef root fill:#fff,stroke:#000,stroke-width:2px,color:#000
    classDef failed fill:#fcc,stroke:#c00,stroke-width:2px,color:#000
    classDef accepted fill:#cfc,stroke:#080,stroke-width:3px,color:#000
    classDef verdict fill:#fffacd,stroke:#a80,stroke-width:2px,color:#000
```
