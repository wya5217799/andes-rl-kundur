# REGF2 successor-route source audit

## Status

- **Date:** 2026-08-14
- **Selected line:** `converter-vsg-pq-decoupling`
- **Purpose:** static direction audit after the sealed R388 REGCV1 authority stop.
- **Authority:** research input only. This document does not authorize ANDES execution, change a verdict, or transfer evidence from R384--R388.
- **Runtime inspected:** installed ANDES 2.0.0 under `/home/wya/andes_venv/lib/python3.12/site-packages/andes`.

## Frozen source identity

| Installed source | SHA-256 |
|---|---|
| `models/renewable/regcv1.py` | `fbd968098084837681e900a8913ec4ab4799038d8c4bc6103acf21e84b31fca8` |
| `models/renewable/regcv2.py` | `3e08023fb13bb13421d14d72b43b1eb9031474e7b3626c66f72657af738b5682` |
| `models/renewable/regf1.py` | `b3346a41dc302dfba314ac61fabff5920828fce963823a4d6761045e0d22323f` |
| `models/renewable/regf2.py` | `1109842ea912e27f8d750be525c26e4dfc41c40b3b6b692a333959aa8d635a53` |
| `models/renewable/regf3.py` | `137c532b257eb2e1c5e0740d9dabb00f9ff5b767e773fcd61e9845b73a27f87d` |
| `models/measurement/pll.py` | `ee147a79fcc7e375c67ccf885ccc0f97b6dca3a2490e2ead71afccb5b2f9081f` |
| `routines/eig.py` | `10a97879f0b3f15a59dc51f1ab6a6bd9a6f7ac6e7ada0337949af78e07ef5707` |

The source was read directly from the installed runtime. No dynamic trajectory was run for this audit.

## Candidate comparison

### REGCV2

REGCV2 inherits `REGCV1Data`, `REGCV1ModelBase`, and `VSGOuterPIModel`; it replaces only the inner current PI controllers with first-order lags. It therefore retains the stopped REGCV1 `Pref2`, `vref2`, virtual-speed, and outer-loop structure. Selecting it immediately after R388 would test a close implementation variant against an outcome already known to be electrically inadmissible, without first establishing a materially different control object. It is a near-retry and is not eligible as the next route.

### REGF1

REGF1 is a grid-forming droop model with dynamic voltage/current loops, `Paux` and `Qaux` algebraic signal paths, sensed-power filters, and active/reactive `LagAntiWindup` limit blocks. It is materially different from REGCV1, but its primary controller is droop rather than the VSM formulation named by the line. It is a useful structural parent and possible deterministic comparator, not the first successor object.

### REGF2

REGF2 extends the REGF1 plant and limit structure with a VSM primary controller. The installed class is documented as a grid-forming inverter with VSM control and adds a virtual-speed integrator, frequency-measurement link, damping, and inertia parameters. It preserves the static-generator replacement interface, the Kundur network can remain unchanged, and its dynamic control structure is materially different from REGCV1.

The public `RenGen.set_pref()` and `set_qref()` APIs still target the model's `Pref` and `Qref` constant services. In the installed REGF1/REGF2 equations, those services establish the operating-point initialization, while the dynamic signal paths use `Paux` and `Qaux`. Therefore no post-initialization authority claim is allowed from API naming or write receipt alone. A clean object/initialization gate must come first; a later separately sealed authority gate must identify and verify the actual dynamic input seam.

### REGF3

REGF3 uses dispatchable virtual oscillator control. It shares the REGF1 plant/limit structure but is not the VSM/VSG successor named by the current line. It is not eligible unless the research object and title are separately changed.

### Custom REGCV1 port or changed REGCV1 card

Adding a new physical port to REGCV1 or tuning its stopped gain/card after observing R388 would mix model engineering with outcome-conditioned rescue. Such work needs its own model specification and evidence line; it is not the smallest defensible successor experiment.

## Direction decision proposed to the repository gate

The repository five-family census covered 26 distinct episodes: F1 (7), F2
(6), F3 (1), F4 (4), and F5 (8). Only T24, stock REGF2 VSM object
reconstruction, remained eligible after enforcing title fit, prior-stop
boundaries, non-transfer of evidence, and the requirement for a materially
different installed object. This is a new route inside F5, not a sixth family.

Select a **stock REGF2 object reconstruction** inside the unchanged ANDES 2.0.0 Kundur two-area network. The first prospective question is limited to object identity and clean initialization:

> Can four stock REGF2 devices replace the four Kundur static source models one-for-one, preserve the 10-bus/15-line network and static operating-point identity, exclude the retired synchronous dynamic equations, and complete native power flow plus dynamic initialization with complete finite residual diagnostics?

This first gate performs no control action, no disturbance, no deterministic controller comparison, and no training. Failure stops REGF2 before authority testing. Passing it permits only a new question about the actual post-initialization `Paux/Qaux` authority seam.

## Post-R389 mechanism-only decision

R389 subsequently constructed and initialized the exact four-stock-REGF2
object but closed Q-0107 negative because its no-exogenous-action 0.2-second
trajectory left the registered stationarity envelope. The sealed trace did not
identify whether the growth was already present in the local linearized model
or arose only in trajectory integration or another model-solver interaction.
It did not authorize the previously conditional `Paux/Qaux` authority question.

The updated five-family census contains 27 episodes: F1 (7), F2 (6), F3 (1),
F4 (5), and F5 (8). T24 is now closed by R389. The sole eligible successor is
T27, an F4 mechanism method applied to the unchanged stopped F5 object: two
fresh no-time-advance equilibrium/EIG arms at numerical initialization
tolerances `1e-4` and `1e-6`. This is not an R389 retry, converter substitution,
parameter rescue, or sixth technical family.

The gate separates validity from spectral sign. Malformed evidence is analysis
invalid; equilibrium or numerical-reproduction failure is a scientific STOP;
and a finite, reproducible mode with real part above `1e-7` is the existing
paper-facing positive-real STOP. Such a result may identify a growing direction
in the exact ANDES reduced state matrix, but it cannot establish physical-
system instability, causality, output observability, or hardware behavior. No
outcome opens authority, control, learning, topology, EMT, HIL, or deployment.

## Reuse and non-transfer rules

- Reuse allowed: the R384--R388 case-derivation, source hashing, static-table identity, diagnostics, create-only lifecycle, and fail-closed classifier patterns.
- Evidence not transferable: REGCV1 initialization, references, action receipts, trajectories, thresholds, signed responses, or verdict language.
- Topology remains ANDES 2.0.0 Kundur 10-bus/15-line; no topology generalization claim follows.
- A passing object gate does not establish P/Q authority, decoupling, stability, safety, controller value, or MARL value.
