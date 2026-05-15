# Figure A — Modified Kundur 4-bus topology with 4 ESS and LS1/LS2 disturbance buses

Single-line diagram of the Stage 2 modified Kundur four-bus system. Three GENROU synchronous generators (G1@B7, G2@B8, G3@B9) and one wind unit replacing G4 (W1@B10), plus auxiliary wind W2@B8. Four ESS attached to load buses 12, 14, 15, 16. Disturbance scenarios LS1 (Bus 14, −2.48 p.u.) and LS2 (Bus 15, +1.88 p.u.) injected at their respective host buses. ES3@Bus 14 highlighted in red as the disturbance-host agent referenced in §3.9 failure clustering.

```mermaid
%%{init: {"flowchart": {"defaultRenderer": "elk", "htmlLabels": true, "curve": "basis"}, "themeVariables": {"fontSize": "14px"}}}%%
flowchart LR
    subgraph TX["Modified Kundur 4-bus transmission"]
        direction LR
        B7(("Bus 7"))
        B8(("Bus 8"))
        B9(("Bus 9"))
        B10(("Bus 10"))
        B7 --- B8 --- B9 --- B10
    end

    G1["G1<br/>GENROU"] --- B7
    G2["G2<br/>GENROU"] --- B8
    G3["G3<br/>GENROU"] --- B9
    W1["W1 wind<br/>(replaces G4)"] --- B10
    W2["W2 wind"] --- B8

    subgraph LD["Load buses with ESS"]
        direction LR
        Bus12(("Bus 12"))
        Bus14(("Bus 14"))
        Bus15(("Bus 15"))
        Bus16(("Bus 16"))
    end

    B7 --- Bus12
    B9 --- Bus14
    B9 --- Bus15
    B10 --- Bus16

    ES2["ES2<br/>(a1 in §3.4)"] --- Bus12
    ES3["ES3<br/>disturbance host"]:::host --- Bus14
    ES5["ES5"] --- Bus15
    ES6["ES6"] --- Bus16

    LS1["LS1: -2.48 p.u."]:::ls -.->|injects at| Bus14
    LS2["LS2: +1.88 p.u."]:::ls -.->|injects at| Bus15

    classDef host fill:#fcc,stroke:#c00,stroke-width:3px,color:#000
    classDef ls fill:#fff3cd,stroke:#a80,stroke-width:2px,color:#000
    style ES2 fill:#ffd,stroke:#a80
    style ES5 fill:#ffd,stroke:#a80
    style ES6 fill:#ffd,stroke:#a80
    style G1 fill:#e0e0ff,stroke:#33f
    style G2 fill:#e0e0ff,stroke:#33f
    style G3 fill:#e0e0ff,stroke:#33f
    style W1 fill:#cfc,stroke:#0a0
    style W2 fill:#cfc,stroke:#0a0
```
