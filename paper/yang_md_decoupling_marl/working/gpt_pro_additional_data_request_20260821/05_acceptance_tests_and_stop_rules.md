# 机械验收、失败分支与停止规则

## 0. 通用完整性

必须全部通过：

- 所有正式输入/输出有 SHA-256；
- root `SHA256SUMS` 无缺失、无 mismatch；
- source/config/threshold/profile/candidate hashes 与 seal 一致；
- create-only 输出目录在 formal run 前不存在；
- rerun使用新 run ID；
- JSON schema/version可解析；
- NaN/Inf、维数漂移、重复 candidate ID、缺失 trajectory 均为 formal failure；
- raw 文件与 summary 的 record counts一致；
- 独立 checker 与生成脚本不共享 endpoint/证书汇总函数。

任何一项失败，状态为 `INVALID`，不得继续给科学结论。

---

## 1. WP1 模型导出验收

### DAE/equilibrium

- `||f(x0,y0)||∞`、`||g(x0,y0)||∞` 按项目现有 gate 达标；
- state/algebraic/input/output labels 数量与矩阵维数一致；
- `g_y`/folded algebraic block报告 `sigma_min, sigma_max, cond, rcond`；
- Schur reduction使用 solve/SVD，不显式形成 inverse；
- 保存 solve backward residual。

### sampled realization

- 由 continuous model重新 ZOH得到 `A_d,B_d`，与导出值相对误差在预注册 tolerance 内；
- 项目 post-step convention满足 `C_post=C_pre A_d`、`D_post=C_pre B_d+D_pre`；
- 选定 columns 的 impulse response与直接 sampled simulator一致；
- gauge/neutral modes按 basis 验证，不凭 eigenvalue 接近 1 猜测。

### units

- normalized→physical round-trip一致；
- 60-Hz output与50-Hz model-base字段不可共用同一名称；
- Object A/B 文件不能引用另一对象的 numerical reference denominator。

---

## 2. U1 证书验收

推荐门槛沿用解答中的预注册值：

1. block Bézout/achievability relative residual `<=1e-10`；
2. lift selected-column vs symmetric finite difference relative error `<=1e-7`，或在近零列使用预注册绝对 tolerance；
3. primal equality residual `<=1e-9(1+||data||)`；
4. maximum cone violation `<=1e-9`；
5. dual stationarity residual `<=1e-9`；
6. unscaled relative duality gap `<=1e-8`；
7. 若声称 infeasible，positive dual lower bound必须大于 `10×(全部数值残差 + nonlinear discrepancy allowance)`；
8. positive bound 使用 80-bit/MPFR/interval arithmetic 复评；
9. witness直接线性仿真与 lifted prediction逐样本一致；
10. nonlinear transfer若 mode改变，则只能保留线性类证书，不能写 nonlinear可行。

### 停止规则

- baseline internal stability未验证：停止；
- DCF convention/Bézout失败：停止；
- denominator不正或随 q 变化：停止/重定义问题并新封存；
- solver只返回 `infeasible` 而无可复核 dual：状态 `CERTIFICATE-INVALID`；
- MISOCP无全局 gap：不得声称精确不可行。

---

## 3. U2 factorial验收

### 设计完整性

- seed在所有网络/optimizer/environment构造前设置；
- 同 seed 18 cells 的初始共享参数字节哈希一致（允许按 access mask 保持同维度）；
- donor bank seed与目标 training seed独立；
- `pi(e)!=e`；
- 每个 agent 的两个 placebo donor均不是其真实语义邻居；
- 每 slot/feature/time 的 pooled multiset hash与 authentic donor pool精确相同；
- 固定 R 时 reward code/config/hash完全相同；
- 固定 A/C 时网络维数和 compute budget相同；
- U3 replay/target tests先通过。

### 统计完整性

- training seed是顶层样本；
- 先按 seed 聚合，再做 contrast；
- 预注册 primary endpoint和materiality；
- failed seeds全部列出；
- 不把 scenario count当独立 n；
- seed数未达到 power plan时状态自动为 `EXPLORATORY`；
- budget变化导致结论翻转/未平台时状态 `OPTIMIZATION-UNRESOLVED`。

### 支持/反驳

- `N-P` paired contrast在固定 reward/access另一侧下达到预注册 materiality，且held-out bank方向稳定：支持 budget-specific semantic value；
- 区间排除 materiality：反驳该特定机制；
- `P-0` 大而 `N-P` 只抵消：结论是 dimension cost recovery；
- 不得从任何分支声称 universal intrinsic value。

---

## 4. U3 Bellman语义验收

### 一步

- NumPy runtime projector vs Torch projector max abs error `<=1e-7`；
- replay `next_prev_action == executed_action`；
- 相同完整 `(z,u)` 在固定 exogenous seed 下给相同 `v,r,z'`；
- 删除 `v_prev` 后 aliasing test产生 two-valued transition；
- raw critic若使用，projection必须位于 transition/target路径；
- executed critic输入必须是实际 executed action。

### 多步

- 从 `v_-1` 和 raw sequence重构完整 executed sequence，逐步误差 `<=1e-7`；
- deterministic toy MDP hand return vs TD target `<=1e-6`；
- actor update critic input为projected action；
- entropy若声称 executed entropy，log-density和feasible interval parameterization一致。

历史 replay 不存在时，不允许输出精确 historical bias 数字。

---

## 5. U4 guard验收

- independent checker从频率/动作raw trace重算全部 metrics；
- summary与独立重算在预注册 numeric tolerance内；
- denominator严格正并高于物理 floor；
- invalid/TDS failed不能被当作零损失；
- 每 profile × seed 单独判 guard，不以期望值替代；
- phase-I输出最优 `t`、全部 active guards、witness/dual或枚举winner；
- neural optimizer的 `t>0` 只标 optimizer failure，不标 class infeasible。

---

## 6. U5 total sensitivity验收

- `rho±h` 每点 equilibrium residual通过；
- active-mode hash一致，否则改报 one-sided/mode-specific derivative；
- Fréchet derivative与direct finite difference一致；
- Richardson `D_h,D_h/2,D_h/4` 呈预期收敛，或明确 conditioning failure；
- 每 frequency保存 `cond(zI-A)` 与 `cond(I+PcK)`；
- total `G_rho` 与直接重建 `G(rho±h)` 的中心差分一致；
- candidate/reference denominator derivative明确包含；
- A-only attribution不得作为总因果结论。

若 full-frequency loop/open-loop pole count缺失，不计算 gain/phase margin。

---

## 7. U6 delay验收

- `delta=0` 与 integer-delay model逐矩阵一致；
- `delta→Ts` 连续接到下一整数 delay；
- augmented matrix包含controller state和完整 command memory；
- branch matching同时使用 eigenvalue distance与eigenvector MAC/Schur subspace；
- eigen residual `<=1e-9||A_cl||`；
- crossing bracket内 branch identity不变；
- simple crossing报告 transversality，near-defective则改用 invariant-subspace/pseudospectral结果；
- 全部非 gauge modes均扫描；
- nonlinear endpoint二分只依赖符号相反 bracket，发现mode jump则停止连续性声明。

无 uncertainty model时 classification必须写 `NOMINAL-LOCAL`，不能写 robust。

---

## 8. U7 tensor/scaling验收

- 每 mixed FD corner `||g||∞<=1e-9` 或更严格项目门槛；
- active-mode hash一致；
- 至少三组 step同时减半；
- Richardson/extrapolated tensor相对差建议 `<=1%`，近零量用预注册绝对 materiality；
- implicit AD/HVP与FD至少在抽样方向交叉核验；
- full tensor或directional operator的范围明确；
- amplitude sweep用同一 disturbance/initial condition；
- 保存 raw和executed action，确认zero bias；
- `||Delta y_MD||/eps^2` 后两级稳定且 `||Delta y_MD||/eps` 趋降，才支持二阶 scaling；
- additive `/eps` 非零且稳定，才支持一阶通道对照。

mode switch、nonzero bias、近奇异 DAE均触发 `LOCAL-TAYLOR-NOT-APPLICABLE`，不属于实验失败造假。

---

## 9. U8 bound验收

- projectors满足 idempotence；正交 projector还需 symmetry；
- basis labels与physical channels一致；
- full-state projector无物理构造证明时不得使用；
- finite-window Toeplitz lift与direct impulse simulation一致；
- actual cross norm `<= upper_bound + numerical_tolerance`；
- 若突破，状态 `BOUND-INCOMPLETE`，检查漏掉的 direct/I/O/algebraic leakage；
- 0–Nyquist conditioning完整，near singular频点明确标记；
- lower bound只有在input/output rank与projection条件满足时报告；
- homogeneous/small perturbation scaling需保持gauge/mode一致。

---

## 10. U9/R458验收

- R458 source/seal/candidate sequence hashes匹配；
- dev和eval shard inventories精确；
- select input inventory不含eval；
- `selection.json` 在eval开始前封存；
- eval四个文件使用同一 winner candidate ID/schedule/hash；
- transfer count从四个 exact booleans重算；
- branch/verdict与冻结代码一致；
- 无读取eval后重选、改threshold、改grid或重跑正式结果；
- priority 3无论K多少都保持 `FALLBACK-NO-WITNESS`。

四个固定 profiles 不计算总体成功率；仅可写 `K/4 fixed profiles`。
