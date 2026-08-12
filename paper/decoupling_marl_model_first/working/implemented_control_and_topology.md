# Implemented Control Algorithms and Topology of the Model-First Line

## 1. Scope and Status Classes

This document inventories the topology and control algorithms implemented for the Model-First manuscript line. It distinguishes three implementation levels:

- **Physical closed loop**: executed against the nonlinear ANDES plant.
- **Model-only controller**: executable feedback code evaluated on reduced models.
- **Offline gate**: optimization or regression code used to test physical headroom or information sufficiency; not a deployed controller.

The line implements deterministic centralized and endpoint-local control, physical action governors, reduced-order controller prototypes, and offline residual gates. It does **not** implement a neural residual controller, a distributed MPC optimizer/runtime, MARL training, or a learned checkpoint. The DMPC-style component is an offline shared-prediction message generator only.

## 2. Physical Topology

### 2.1 Base network

The plant is the phasor-domain Kundur two-area system loaded from **kundur/kundur_full.xlsx**. It retains all four original **GENROU** synchronous generators. Each **GENROU** is equipped with

$$
\mathrm{GENROU}+\mathrm{IEEEG1}+\mathrm{EXST1}.
$$

The default line-outage toggler is disabled in the Model-First environment. A wind-generation proxy is connected at bus 8.

### 2.2 Added controllable nodes

Four controllable nodes are added. This document uses one-based node indices.

| Node $i$ | Area | Device bus | Parent network bus | VSG proxy | Storage plant |
|---:|---:|---:|---:|---|---|
| 1 | 1 | 12 | 7 | **VSG_1** | **R272_BESS_1** |
| 2 | 1 | 16 | 8 | **VSG_2** | **R272_BESS_2** |
| 3 | 2 | 14 | 10 | **VSG_3** | **R272_BESS_3** |
| 4 | 2 | 15 | 9 | **VSG_4** | **R272_BESS_4** |

The local model composition is

$$
\boxed{
\text{network bus}_i
+(\mathrm{PV}+\mathrm{GENCLS})_i
+(\mathrm{PV}+\mathrm{ESD1})_i
}.
$$

In ANDES, **PV** is a power-flow PV interface; it does not mean a photovoltaic generator.

- **PV + GENCLS**: simplified VSG **proxy** with swing dynamics.
- **PV + ESD1**: battery plant with externally commanded active power.
- The VSG proxy and ESD1 are separate, co-located models.
- The VSG controller is not embedded in ESD1.

The complete source/actuator inventory is

$$
4\,\mathrm{GENROU}
+4\,\mathrm{GENCLS}_{\mathrm{VSG}}
+1\,\mathrm{GENCLS}_{\mathrm{wind}}
+4\,\mathrm{ESD1}.
$$

Hence, the modified plant contains more than the four original synchronous machines.

### 2.3 Ratings and frozen parameters

Each VSG proxy has a 200 MVA device rating. On the 100 MVA system base,

$$
M_i=400,\qquad D_i=200.
$$

Each ESD1 storage unit has

$$
S_{n,i}=36\ \mathrm{MVA},\qquad
E_{n,i}=28\ \mathrm{MWh},\qquad
s_i(0)=0.5,
$$

$$
0.2\le s_i\le0.8,\qquad
\eta_i^{\mathrm{ch}}=\eta_i^{\mathrm{dis}}=0.9848857802,
\qquad |I_{p,i}|\le1\ \mathrm{p.u.}
$$

The active-current lag is

$$
T_{ip}=0.02\ \mathrm{s}.
$$

Reactive-power authority and the internal ESD1 frequency-droop path are disabled in this line.

### 2.4 Four distinct graphs

The implementation separates:

1. $\mathcal G_e$: physical electrical graph;
2. $\mathcal G_c$: four-node communication ring;
3. $\mathcal G_a$: three-edge differential-action path;
4. $\mathcal G_d$: disturbance-location graph.

The communication graph is

$$
\mathcal E_c=\{(1,2),(2,3),(3,4),(1,4)\},
$$

whereas the action graph is

$$
\mathcal E_a=\{(1,2),(2,3),(3,4)\}.
$$

The edge $(1,4)$ communicates information but does not define an independent differential-action coordinate. Therefore,

$$
\mathcal G_e\neq\mathcal G_c\neq\mathcal G_a\neq\mathcal G_d
$$

in both semantics and implementation.

## 3. Plant, Actuator, and Control Variables

### 3.1 Nonlinear sampled-data DAE

The physical plant is represented by

$$
E_d(\rho_k)\dot x
=f(x,y;\rho_k,p_k^\star,d_k),
\qquad
0=g(x,y;\rho_k,p_k^\star,d_k),
$$

where $x$ is the dynamic state, $y$ is the algebraic state, $\rho_k$ contains physical parameters, $p_k^\star\in\mathbb R^4$ is requested storage power, and $d_k$ is physical disturbance.

### 3.2 VSG proxy

For VSG proxy $i$, **GENCLS** contributes

$$
\dot\delta_i=2\pi f_n(\omega_i-1),
$$

$$
M_i\dot\omega_i
=t_{m,i}-t_{e,i}-D_i(\omega_i-1).
$$

Thus, $M_i$ and $D_i$ are explicit plant parameters. They are not online actions in the implemented active-power route.

### 3.3 ESD1 realization

The controller requests power; it does not directly set achieved grid power. ESD1 realizes the projected command through

$$
T_{ip}\dot I_{p,i}
=I_{p,i}^{\mathrm{cmd}}-I_{p,i},
\qquad
p_i^{\mathrm{act}}=v_i I_{p,i}.
$$

Positive $p_i^{\mathrm{act}}$ denotes grid injection and battery discharge. The energy balance is

$$
\dot E_i=
\begin{cases}
-p_i^{\mathrm{act}}/\eta_i^{\mathrm{dis}},
&p_i^{\mathrm{act}}>0,\\[1mm]
-\eta_i^{\mathrm{ch}}p_i^{\mathrm{act}},
&p_i^{\mathrm{act}}<0,
\end{cases}
\qquad
s_i=\dfrac{E_i}{E_{n,i}}.
$$

The implementation distinguishes

$$
\boxed{
p^\star
\longrightarrow p^{\mathrm{cmd}}
\longrightarrow p^{\mathrm{act}}
}.
$$

### 3.4 Manipulated, regulated, and constrained variables

The online manipulated variable is storage active power:

$$
u_k=p_{\mathrm{BESS},k}^\star\in\mathbb R^4.
$$

The regulated output is the four-coordinate frequency response:

$$
z_k=
\begin{bmatrix}
z_k^c & z_{k,1}^d & z_{k,2}^d & z_{k,3}^d
\end{bmatrix}^{\mathsf T},
$$

with one inertia-weighted common coordinate and three differential coordinates.

SOC, energy, voltage, current, power, and ramp are feasibility variables and constraints. The controller does not command SOC directly.

## 4. Coordinates and Action Maps

Let $u\in\mathbb R^4$ denote node-power requests. The common/differential decomposition is

$$
u=u^c+u^d,
\qquad
u^c=\alpha\mathbf1,
\qquad
u^d=B_ar,
$$

where

$$
B_a=
\begin{bmatrix}
1&0&0\\
-1&1&0\\
0&-1&1\\
0&0&-1
\end{bmatrix},
\qquad
r\in\mathbb R^3.
$$

Therefore,

$$
\mathbf1^{\mathsf T}u^d=0.
$$

The differential action redistributes power; the common action changes total fleet injection. A differential-only controller cannot create net system power.

## 5. Physical Action Governors

### 5.1 Node-level BESS projection

**EnergyFeasibleBESSContract** computes

$$
p_{i,k}^{\mathrm{cmd}}
=\Pi_{\mathcal U_i(k)}
\left(p_{i,k}^\star\right),
$$

where

$$
\mathcal U_i(k)=
\left\{
p_i:
\begin{aligned}
&p_i^{\min}\le p_i\le p_i^{\max},\\
&|p_i-p_{i,k-1}^{\mathrm{cmd}}|
\le r_i\Delta t,\\
&|p_i|\le v_iI_{p,i}^{\max},\\
&s_i^{\min}\le s_i(k+1;p_i)\le s_i^{\max}
\end{aligned}
\right\}.
$$

This deterministic layer enforces nameplate power, voltage-current capability, ramp, SOC, and energy limits.

### 5.2 Edge-action governor

**MatchedEdgeActionGovernor** applies

$$
a_k
\longrightarrow r_k^{\mathrm{req}}
\longrightarrow r_k^{\mathrm{exe}}
\longrightarrow p_k^d=B_ar_k^{\mathrm{exe}}
\longrightarrow\Pi_{\mathcal U(k)}.
$$

It enforces

$$
|r_{e,k}|\le0.05\ \mathrm{p.u.},
\qquad
|r_{e,k}-r_{e,k-1}|\le0.05\ \mathrm{p.u./step},
$$

plus endpoint headroom and the node-level BESS constraints. The same governor is used by deterministic and prospective learned edge policies.

## 6. Implemented Control Algorithms

### 6.1 Equal-sharing droop-PI utility

**DroopPIActivePowerController** uses

$$
\bar f_k=\frac14\sum_{i=1}^{4}f_{i,k},
\qquad
e_{f,k}=f_n-\bar f_k.
$$

With conditional anti-windup,

$$
\eta_k^+=
\begin{cases}
\eta_k+K_ie_{f,k}\Delta t,
&\text{integration allowed},\\
\eta_k,
&\text{saturation drives in the same direction},
\end{cases}
$$

$$
p_{i,k}^\star=K_pe_{f,k}+\eta_k^+,
\qquad i=1,\ldots,4.
$$

All four devices receive the same pre-projection request. This is an implemented shared baseline utility, not the final Model-First controller.

### 6.2 Model-based controller development sequence

Several deterministic designs were implemented before the retained physical controller.

| Design | Compact law | Status |
|---|---|---|
| Delayed DC-inverse static feedback | $u_k=-\alpha K_{dc}y_{k-1}$ | Model-only; rejected before physical execution (R317) |
| Delay-augmented observer-LQR | $u_k=-K\hat z_k,\ z_k=[x_k^{\mathsf T},y_{k-1}^{\mathsf T}]^{\mathsf T}$ | Model-only; nominal pole gate failed (R319) |
| Exact pole-target observer feedback | $u_k=-K_{pp}\hat z_k$ with prescribed controller/observer poles | Model-only; pole placement passed, performance gate failed (R321) |
| SLSQP finite-horizon output feedback | constrained $N=25$ optimization | Model-only; repeated solver termination, formulation rejected (R325) |
| Disturbance-augmented estimator + sparse constrained horizon | Kalman-type correction + sparse QP | Model-only development/holdout bridge (R329--R330) |
| Separate-input constrained horizon controller | independent $B_P$ and $B_d$, OSQP, physical ESD1 actuation | Physical closed loop; bounded bridge passed (R344) |

These are successive implemented designs, not simultaneous runtime controllers.

### 6.3 Retained centralized constrained horizon controller

**SeparateInputHorizonController** uses the order-12 reduced model

$$
x_{k+1}=A_dx_k+B_{P,d}u_k+B_{d,d}d_k,
$$

$$
z_k=C_dx_k+D_{P,d}u_k+D_{d,d}d_k.
$$

The disturbance-augmented estimator uses

$$
\xi_k=
\begin{bmatrix}
x_k\\d_k
\end{bmatrix},
\qquad
d_{k+1}=d_k+w_k,
$$

$$
\xi_{k|k}
=\xi_{k|k-1}
+L\left(
z_k-C_a\xi_{k|k-1}-D_{P,d}u_{k-1}
\right),
$$

$$
\xi_{k+1|k}
=A_a\xi_{k|k}+B_a^u u_{k-1}.
$$

At each control instant, direct OSQP solves a finite-horizon quadratic program of the form

$$
\min_{\mathbf u}
\sum_{j=0}^{N-1}
\left(
z_{k+j|k}^{\mathsf T}Qz_{k+j|k}
+u_{k+j|k}^{\mathsf T}Ru_{k+j|k}
\right),
$$

subject to

$$
|p_{i,k+j|k}|\le0.36,
\qquad
|\Delta p_{i,k+j|k}|\le0.072,
$$

$$
0.2\le s_{i,k+j|k}\le0.8,
$$

plus energy and actuator constraints.

Its runtime identity is

$$
\boxed{
\text{full-output centralized}
+\text{separate }(u,d)\text{ channels}
+\text{constrained receding horizon}
}.
$$

If the QP is unavailable or infeasible, the fallback applies a bounded ramp toward zero. The resulting node-power request is still passed through the physical BESS projection.

### 6.4 Endpoint-local deterministic edge controller

**LinearNeighbourEdgeController** is the implemented distributed deterministic baseline. For oriented edge $e=(i,j)$,

$$
a_{e,k}
=\operatorname{sat}_{[-1,1]}
\left[
-k_f(\Delta f_{i,k}-\Delta f_{j,k})
-k_r(\dot f_{i,k}-\dot f_{j,k})
\right].
$$

Three actors evaluate the law independently on

$$
(1,2),\qquad(2,3),\qquad(3,4).
$$

Each actor sees only

$$
o_{e,k}
=
\left[
\Delta f_i,\dot f_i,p_i^{\mathrm{prev}},s_i,v_i,h_i^-,h_i^+,
\Delta f_j,\dot f_j,p_j^{\mathrm{prev}},s_j,v_j,h_j^-,h_j^+,
r_{e,k-1}
\right].
$$

The selected gains are

$$
k_f=500\ \mathrm{Hz}^{-1},
\qquad
k_r=0\ \mathrm{s/Hz}.
$$

The resulting physical closed loop passed the bounded neighbour-distributed deterministic holdout gate in R352.

### 6.5 Joint-information diagnostic controller

The implemented diagnostic law removes the fleet mean:

$$
p_k^{\mathrm{des}}
=-k_f\left(\Delta f_k-\bar{\Delta f}_k\mathbf1\right)
-k_r\left(\dot f_k-\bar{\dot f}_k\mathbf1\right),
$$

then solves

$$
r_k=B_a^\dagger p_k^{\mathrm{des}}.
$$

This arm uses global information on the same three-edge action space. It was implemented and physically executed in R352, but its diagnostic analysis had a registered validity inconsistency; it supplies no scientific claim.

## 7. Implemented Offline Residual and Feasibility Algorithms

### 7.1 Zero-common residual headroom

The three-edge residual action is

$$
p_k^r=B_ar_k,
\qquad
\mathbf1^{\mathsf T}p_k^r=0.
$$

The implemented gates solve variants of

$$
\min_{\mathbf r}\ J_d(\mathbf r)
$$

subject to

$$
J_c(\mathbf r)\le0.98J_c(0),
\qquad
\mathbf p^r\in\mathcal U,
$$

where $J_c$ is the common-coordinate absolute-error endpoint and $J_d$ is the differential-coordinate energy endpoint.

| Gate | Implemented algorithm | Runtime meaning |
|---|---|---|
| R350 | Smooth convex oracle + endpoint-local standardized OLS proxy | Residual-headroom diagnosis; NO-TRAINING |
| R356 | Cone relaxation of simultaneous common/differential targets | Mathematical feasibility relaxation |
| R358 | Normalized physical QP with power, ramp, energy, SOC, and capability constraints | Physical action-space feasibility |

These programs test whether a residual action exists. They do not define how a causal runtime controller obtains it.

### 7.2 Causal per-edge residual maps

For standardized local observation $\tilde o_{e,k}$, the implemented families are

$$
\text{Affine:}\qquad
\hat a_{e,k}
=\operatorname{sat}
\left(w_e^{\mathsf T}\tilde o_{e,k}+b_e\right),
$$

$$
\text{RBF kernel ridge:}\qquad
\hat a_{e,k}
=k_e(\tilde o_{e,k},X)^{\mathsf T}
(K_e+10^{-3}I)^{-1}y_e,
$$

$$
\text{5-NN:}\qquad
\hat a_{e,k}
=\frac15
\sum_{n\in\mathcal N_5(\tilde o_{e,k})}y_{e,n},
$$

$$
\text{Quadratic:}\qquad
\hat a_{e,k}
=w_e^{\mathsf T}
\begin{bmatrix}
1\\
\tilde o_{e,k}\\
\operatorname{vech}
(\tilde o_{e,k}\tilde o_{e,k}^{\mathsf T})
\end{bmatrix}.
$$

The information variants are:

| Gate | Edge-map input | Registered result |
|---|---|---|
| R359 | 15-field causal endpoint-local observation | Affine gate negative |
| R360 | Same 15 fields | RBF, 5-NN, and quadratic gates negative |
| R361 | 15 local fields + two four-field one-hop state messages | All four families negative |
| R362 | 15 local fields + two four-step model-prediction messages | All four families negative |

All four gates use offline leave-one-scenario-out fitting and the exact physical projection. They execute no neural network, reinforcement learning, nonlinear plant trajectory, or deployed distributed MPC loop.

### 7.3 DMPC-style shared-prediction message

For neighbour $j$, the offline prediction generator propagates the frozen separate-input model for four samples:

$$
\hat\xi_{j,k+\ell+1|k}
=A_a\hat\xi_{j,k+\ell|k},
\qquad
\ell=0,\ldots,3,
$$

with zero future residual control and held disturbance estimate. The message is

$$
m_{j\rightarrow e,k}
=
\begin{bmatrix}
\widehat{\Delta f}_{j,k+1|k}&
\widehat{\Delta f}_{j,k+2|k}&
\widehat{\Delta f}_{j,k+3|k}&
\widehat{\Delta f}_{j,k+4|k}
\end{bmatrix}^{\mathsf T}.
$$

This is a prediction-sharing feature for the R362 learnability gate, not a distributed MPC optimizer.

### 7.4 Common-channel physical-headroom QP

R363 extends the residual basis to

$$
p_k^r=\alpha_k\mathbf1+B_ar_k.
$$

The physically constrained endpoint QP is solved over four coordinates:

$$
\min_{\alpha,\mathbf r}\ J_d(\alpha,\mathbf r)
$$

subject to

$$
J_c(\alpha,\mathbf r)\le0.98J_c(0),
\qquad
\alpha\mathbf1+B_ar\in\mathcal U.
$$

This implemented gate established action-space feasibility on the exposed development bank. It implemented neither a causal information map for $\alpha_k$ nor a runtime controller.

## 8. Closed-Loop Execution

The controller period is

$$
\Delta t_c=0.2\ \mathrm{s}.
$$

ANDES advances five physical substeps:

$$
\Delta t_p=0.04\ \mathrm{s},
\qquad
5\Delta t_p=\Delta t_c.
$$

The physical signal flow is

$$
z_k
\longrightarrow
\text{estimation/controller}
\longrightarrow
p_k^\star
\longrightarrow
\Pi_{\mathcal U(k)}
\longrightarrow
p_k^{\mathrm{cmd}}
\longrightarrow
\mathrm{ESD1}
\longrightarrow
p_k^{\mathrm{act}}
\longrightarrow
z_{k+1}.
$$

During active-power validation, the environment requires every online $M/D$ action entry to be exactly zero. Therefore, the executed controllers act on ESD1 active power only; VSG-proxy $M_i$ and $D_i$ remain fixed.

## 9. Complete Implementation Boundary

| Item | Status |
|---|---|
| Modified Kundur two-area ANDES plant | Implemented |
| Four original GENROU machines with governor/exciter | Implemented |
| Four PV + GENCLS VSG proxies | Implemented |
| Four PV + ESD1 storage plants | Implemented |
| Wind proxy | Implemented |
| Node-level BESS projection | Implemented and physically executed |
| Edge-action governor | Implemented and physically executed |
| Equal-sharing droop-PI utility | Implemented shared utility |
| Delayed DC-inverse feedback | Implemented model-only; rejected |
| Delay-augmented observer-LQR | Implemented model-only; rejected |
| Exact pole-target observer feedback | Implemented model-only; rejected |
| SLSQP finite-horizon output feedback | Implemented model-only; formulation rejected |
| Disturbance-augmented estimator + sparse QP | Implemented model-only bridge component |
| Separate-input constrained horizon controller | Implemented and physically executed |
| Endpoint-local linear three-edge controller | Implemented and physically executed |
| Joint-information diagnostic controller | Implemented and physically executed; claim-excluded |
| Convex residual-headroom programs | Implemented offline |
| Affine, RBF, 5-NN, and quadratic residual maps | Implemented offline; gates negative |
| One-hop state-message residual route | Implemented offline; gate negative |
| Shared-prediction residual route | Implemented offline; gate negative |
| Four-coordinate common-channel headroom QP | Implemented offline; positive headroom gate only |
| Neural residual controller | Not implemented |
| Distributed MPC optimizer/runtime | Not implemented |
| MARL policy or training | Not implemented |
| Learned checkpoint | Not implemented |
| Topology-generalization experiment | Not implemented |
| EMT, HIL, or field deployment | Not implemented |

The present line is a fixed-topology, phasor-domain deterministic-control programme. It contains one centralized physical controller, one endpoint-local distributed deterministic controller, and several offline residual gates. It does not yet contain a learned controller.

## 10. Repository Source Map

### Plant and physical actuation

- src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
- src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py
- src/andes_rl_kundur/env/andes/model_first_env.py
- src/andes_rl_kundur/env/andes/model_first_contract.py
- src/andes_rl_kundur/control/active_power.py
- src/andes_rl_kundur/control/headroom_aware_edge_allocation.py

### Deterministic controllers

- src/andes_rl_kundur/control/model_first_offline_feedback.py
- src/andes_rl_kundur/control/model_first_observer_lqr.py
- src/andes_rl_kundur/control/model_first_pole_target.py
- src/andes_rl_kundur/control/model_first_constrained_horizon.py
- src/andes_rl_kundur/control/model_first_constrained_qp.py
- src/andes_rl_kundur/control/model_first_disturbance_estimator.py
- src/andes_rl_kundur/control/model_first_separate_input.py
- src/andes_rl_kundur/control/model_first_distributed_edge.py

### Residual and learnability gates

- src/andes_rl_kundur/control/residual_headroom.py
- src/andes_rl_kundur/control/convex_residual_solver.py
- src/andes_rl_kundur/control/convex_first_order_certificate.py
- src/andes_rl_kundur/control/minimum_norm_certificate.py
- src/andes_rl_kundur/control/common_channel_qp.py
- src/andes_rl_kundur/control/neighbour_causal_residual.py
- src/andes_rl_kundur/control/flexible_neighbour_residual.py
- src/andes_rl_kundur/control/neighbour_message_residual.py
- src/andes_rl_kundur/control/shared_prediction_residual.py

### Authoritative line records

- paper/decoupling_marl_model_first/working/model_contract.md
- paper/decoupling_marl_model_first/reports/R317.md
- paper/decoupling_marl_model_first/reports/R319.md
- paper/decoupling_marl_model_first/reports/R321.md
- paper/decoupling_marl_model_first/reports/R325.md
- paper/decoupling_marl_model_first/reports/R329.md
- paper/decoupling_marl_model_first/reports/R330.md
- paper/decoupling_marl_model_first/reports/R344.md
- paper/decoupling_marl_model_first/reports/R352.md
- paper/decoupling_marl_model_first/reports/R358.md
- paper/decoupling_marl_model_first/reports/R359.md
- paper/decoupling_marl_model_first/reports/R360.md
- paper/decoupling_marl_model_first/reports/R361.md
- paper/decoupling_marl_model_first/reports/R362.md
- paper/decoupling_marl_model_first/reports/R363.md
