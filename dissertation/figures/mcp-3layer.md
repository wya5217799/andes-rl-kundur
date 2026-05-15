# Figure D — MCP Simulink Toolkit three-layer architecture (Asset 1)

The bespoke MCP toolkit is structured as three layers above a single persistent MATLAB engine. L3 exposes 45 Pydantic-validated tools; L2 provides noise filtering and IPC bundling helpers; L1 is a singleton MATLAB engine session that persists across all tool calls (~20s cold start, then reused). The dashed red anti-pattern node shows the design alternative explicitly avoided: spawning a new engine per L3 call would incur the 20s cold start on every tool invocation.

```mermaid
%%{init: {"flowchart": {"defaultRenderer": "elk", "htmlLabels": true, "curve": "linear"}, "themeVariables": {"fontSize": "14px"}}}%%
flowchart TB
    Agent["Claude / Codex agent"]:::agent

    subgraph L3["L3: 45 Pydantic-validated MCP tool wrappers"]
        direction LR
        T1["harness_model<br/>_diagnose"]
        T2["simulink_run<br/>_script"]
        T3["simulink_query<br/>_params"]
        Tdots["+ 42 more"]
    end

    subgraph L2["L2: slx_helpers (noise filter + IPC bundling)"]
        direction LR
        H1["slx_run_quiet<br/>(stderr filter)"]
        H2["assignin_safe<br/>(no checksum invalidation)"]
        H3["important_lines<br/>(RESULT: prefix)"]
    end

    subgraph L1["L1: Singleton MATLAB Engine (~20s cold start, persistent across calls)"]
        Engine["matlab.engine.MatlabSession<br/>single process for the project"]
    end

    MATLAB["MATLAB R2025b backend<br/>(set_param, sim, find_system, ...)"]:::matlab

    Agent -->|"1 MCP call"| L3
    L3 -->|"N internal calls"| L2
    L2 -->|"single op per helper"| L1
    L1 --> MATLAB

    AntiPattern["wrong design: each L3 call spawns new engine<br/>=> 20 s cold start per tool call"]:::bad
    AntiPattern -. avoided by L1 singleton .-> Engine

    classDef agent fill:#fff,stroke:#000,stroke-width:2px,color:#000
    classDef matlab fill:#ffe7c0,stroke:#a60,color:#000
    classDef bad fill:#fdd,stroke:#a00,stroke-dasharray: 5 4,color:#700
    style L3 fill:#dde7ff,stroke:#33a
    style L2 fill:#e0f4d8,stroke:#3a3
    style L1 fill:#fef0d0,stroke:#a80
```
