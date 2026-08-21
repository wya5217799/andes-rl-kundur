---
round: R444
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R444 plan — 签名探针奇次响应阶数：几何幅值缩放实验

**Opened**: 2026-08-20
**Driver**: 草稿 §3.4 目前主动拒绝"签名探针对奇次响应按平方还是立方收敛"的
阶数结论，因为没有几何幅值缩放实验（theory audit C.7/C.8 要求的
finite-amplitude scaling test）。owner 点单：约一小时评估型小实验，测出
δ_odd(ε) 的实测阶数，允许 §3.4 加一句有依据的措辞；测不出就维持现状。
**Parent**: theory audit C.7/C.8（`working/theory_audit_bundle/vsg_theory_audit.md`，
外部理论吸收路径）; R411 幅度阶梯先例（CLM-1220，未测 oddness）;
手稿 §3.4 末句的拒绝措辞; CLM-1220 (R411)。

## TL;DR

Workload: `evidence`。Eval-only。几何幅度阶梯 ε_k = ε_0·2^{-k}（k=0..5，
6 个尺度，跨度 32×）作用于注册 probe/localized magnitudes；两个
zero-bias 控制器——deterministic law `local_neighbour_md_km2_kd2` 与
zero action（无动作参照）——在 4 个 eval profiles × 3 pair kinds
(common/differential/localized) × ± 符号下各跑 30 步物理轨迹；
形成两控制器响应差之奇部分 δ_odd(ε_k)（C.7 定义），固定 L2 范数
（跨幅度不变），log-log 回归估局部阶数 p̂，补偿量 ‖δ_odd‖/ε、/ε²、
/ε³ 平台检查；预注册判定 QUADRATIC (p̂∈[1.5,2.5]) / CUBIC (p̂∈[2.5,3.5])
/ INCONCLUSIVE；mode-signature 一致性 + 数值/噪声底拒绝规则。
结论进手稿 §3.4 一句（有依据才写，无结论维持现状）。
6 尺度 × 2 控制器 × 2 符号 × 3 pair kinds × 4 profiles = 288 records
≈ 58 min serial；容量阶梯 rungs 1/2/4（每 rung 32 代表任务）选 rung，
seal 冻结预算后并行执行。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= 每 (profile, pair_kind) 的
  δ_odd 幅度表 + log-log 回归阶数 p̂ + 补偿平台判定 + mode 一致性 +
  可用尺度数 + 阶数分类（QUADRATIC/CUBIC/INCONCLUSIVE）+ 1.0 锚
  bit-identical 对照 R410 deterministic 记录；随后
  feed/claim/verdict/LINE/ARTIFACTS 一致关闭，手稿措辞按预注册分支。
- Authority: owner 直接点单（2026-08-20 对话："启动任务"）；LINE.md
  stop_when 允许（评估型、不改训练/标题/摘要、只可能给 §3.4 加一句）。
- Permitted: 新 runner `scripts/run_r444_signed_probe_order.py` + 定向
  测试；results 根 `results/research_loop/r444_signed_probe_order/`
  （create-only, hashed）；本轮 ledger/feed/verdict/LINE 收尾；
  §3.4 一句话措辞更新（仅按预注册分支且有 feed 证据）。
- Forbidden: 改 R410/R411 runner、canary contract、learner、estimator、
  guard、classifier 或任何 sealed 资产；训练任何策略；动 R410/R411
  results 根（只读）；写任何其他手稿线。
- Terminal: formal_analysis.json 存在且全部 288 records 落盘 hashed。

### 冻结协议 (frozen-first)

- **几何幅度阶梯**: 对每个 eval profile，ε_k = 注册 magnitude × 2^{-k}，
  k=0..5。common/differential pair 用 `probe_magnitude`（0.8–1.1），
  localized pair 用 `localized_magnitude`（0.85–1.2）。最小尺度 =
  注册值/32（≈0.025–0.0375），低于 R411 已测下限（0.5× 注册值），
  专测小幅度渐近区。
- **控制器**: Y_1 = `LocalNeighbourMDExecution(local_neighbour_md_km2_kd2)`
  （zero-bias: 平衡点动作零）; Y_2 = zero action（无控制器，动作恒零）。
  两者共享 equilibrium bias、共享 first-order plant map（Lemma 1）、
  动作只经乘性 M/D 参数变化进入——满足 C.8 假设场景。
- **场景**: 4 个 eval profiles × 3 pair kinds × 2 符号 = 24 场景，
  幅度按阶梯缩放；`_signed_scenarios` 冻结重建（只改 magnitude）。
- **评估循环**: 逐字复用 R410 eval 语义（同 `_build_env` /
  `PerVSGMDActionProjector` / `adapt_v4_observations_to_physical`）；
  record 增 `amplitude_k` / `magnitude_executed` / `controller_id` 字段，
  数值路径不变。
- **mode signature**: 每步记录 action_norm（→ 饱和检测）、delta_M/D、
  M_es/D_es（→ limiter clamp 检测）; 分析时从 actions 推每步饱和/限幅
  标志序列，作为跨幅度 mode 一致性检查依据。
- **输出布局**: `eval/<controller>/a<key>/<profile>.json`（hashed,
  create-only），每条含 6 条 scenario records（同 profile 同幅度）。
- **分片**: shard = (controller, amplitude_k) 12 个；resume 规则同
  R411（crash 签名下 `--resume` 只补缺失文件）。
- **完成判据**: 48 个 profile 文件（12 shards × 4 profiles）hashed
  存在 + sidecar 有效；classify 输出完整阶数表。

### 预注册判定树 (Gate)

对每 (profile, pair_kind)：

1. **δ 分解**: δ_±(ε_k) = Y_law(±ε_k) − Y_zero(±ε_k)（轨迹差，4×30
   数组）；δ_odd = (δ_+ − δ_−)/2；δ_even = (δ_+ + δ_−)/2。
2. **固定范数**: ‖δ‖ = sqrt(Σ_t Σ_units δ(t,u)² × dt)（weighted L2，
   跨幅度不变，不做任何 ε 归一化）。
3. **可用尺度过滤**: 剔除 (a) TDS 失败或不完整 record；(b) 范数落入
   数值/噪声底的尺度——判据: 该尺度 ‖δ_odd‖ ≤ 10 × max(全尺度最小
   非零范数的 1e-3, 1e-12) 或与相邻大尺度比值 > 4（即下降率异常）时
   标记 noise-floor 剔除；可用尺度 ≥ 5 才继续，否则该块 INCONCLUSIVE。
4. **mode 一致性**: 拟合范围内每尺度的饱和/限幅标志序列必须一致
   （无新 active-set 出现）; 不一致 → 该块 INCONCLUSIVE 并记录。
5. **阶数估计**: log-log 回归 ln‖δ_odd(ε_k)‖ = p̂ ln ε_k + c（仅可用
   尺度），报 p̂、R²、每对相邻尺度局部斜率。
6. **分类**: p̂ ∈ [1.5, 2.5] → QUADRATIC; p̂ ∈ [2.5, 3.5] → CUBIC;
   其余 → INCONCLUSIVE。补偿量检查: 报 ‖δ_odd‖/ε、/ε²、/ε³ 各尺度值
   与平台稳定性（相对展宽 ≤20% 视为平台），作为分类的佐证字段。
7. **汇总**: 跨 4 profiles × 3 pair kinds 的分类多数 + 一致性；
   手稿措辞分支:
   - 全部/多数 QUADRATIC 且无 INCONCLUSIVE 反对 → §3.4 可加：
     "geometric-amplitude scaling of the implemented law shows the
     signed-pair odd response scaling as ε², consistent with asymmetric
     one-sided branch coefficients."
   - 全部/多数 CUBIC 且无 INCONCLUSIVE 反对 → 可加：
     "...scaling as ε³..."（措辞在 publication gate 再核准）。
   - 混合或 INCONCLUSIVE 主导 → 维持现有拒绝措辞，不加句子。
8. **1.0 锚**: 幅度 k=0（×1.0）的 law 记录 freq_hz_physical 行必须与
   R410 deterministic 同 profile 同 scenario 记录 bit-identical
   （0/48 块不匹配, 相对偏差 ≤1e-6）→ 环境身份证明；漂移 → DRIFT 标记
   并在 feed 报告，分类仍按数据（creative 分支：记录并继续）。

## Theory intake

外部理论 = `working/theory_audit_bundle/vsg_theory_audit.md` C.7/C.8
（机制预测类，三分表 M 类）。本轮用 C.7 实验设计测 C.8 机制预测的
可观测清单：

```
observable: delta_odd_norm(eps_k)
  definition: ||(Y_law(+eps)-Y_zero(+eps) - Y_law(-eps)+Y_zero(-eps))/2||_L2,
    4-unit frequency-deviation trajectories, 30 steps x 0.2s, dt-weighted
    L2 norm, per (profile, pair_kind), k=0..5
  source: results/research_loop/r444_signed_probe_order/eval/<controller>/a<key>/<profile>.json#/records
  predicts: C.8 predicts O(eps^2) ("may also be O(eps^2) rather than
    cubic") -> p_hat in [1.5,2.5] supports the quadratic branch;
    p_hat in [2.5,3.5] supports the cubic-leading branch; p_hat outside
    or <5 usable scales -> undecidable
observable: local_slope_pairs(eps_k, eps_{k+1})
  definition: (ln||delta_odd(eps_k)|| - ln||delta_odd(eps_{k+1})||) /
    (ln eps_k - ln eps_{k+1}) per consecutive usable scales
  source: same records; computed by probes/r444_signed_probe_order.py
  predicts: all pairwise slopes within the same classification band
    (quadratic or cubic) and R^2 >= 0.9 -> supports that order; slopes
    drifting with k -> mode/regime change, reject fitted order
observable: mode_signature_consistency
  definition: per-step action saturation/limiter flag sequences equal
    across all fitted scales (no new active-set below the largest scale)
  source: same records, derived from action_norm / delta_M / delta_D rows
  predicts: consistent -> order claim valid; inconsistent -> C.8's
    "one fixed active-mode sequence" assumption fails -> undecidable
```

裁决写回 feed（Conclusions 或 Follow-up）: supported / refuted /
undecidable 每条约一条，收尾跑 `external_theory_intake_lint.py R444`。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r444_signed_probe_order.py --shards tmp/andes/r444_shards.json --workers 4 --round R444` (12 shards, driver = launcher, budget 内) + `... run_r444_signed_probe_order.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 真实 1 场景 2 步 rollout（law 与 zero 各一，最大幅度）+ record 字段完整性; 不创建 formal artifact。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R444/capacity_evidence.json
- host_process_budget: 5
- wsl_python_processes: 5
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R410/R411 runner、canary contract、estimators、controller、env、
  results 根全部只读；R410 deterministic eval 记录只读（1.0 锚源）。
- paper-cited 资产（base_env / andes_vsg_env_v4 / train.py /
  paper_grade_axes.py）只读。
- 新文件仅: run_r444 runner + tests、R444 results 根（create-only）、
  ledger/feed/verdict 收尾、可能的 §3.4 一句话。
- 容量痕迹非 claim-bearing，住 tmp/andes 与 memory/rounds/R444。

## Cross-references

- theory audit C.7/C.8（`working/theory_audit_bundle/vsg_theory_audit.md`）:
  实验设计与机制预测源。
- CLM-1220 (R411): 先例——幅度网格测了分类不变性，未测 oddness
  （R411 Limits 明写）。
- CLM-1215 (R410): 1.0 锚 bit-identical 对照源（deterministic records）。
- R411 runner / soft_spot_shard_driver: 执行模板。
- SKILL.md §2/§4: evidence 生命周期、容量阶梯、rehearsal/seal 顺序。

## Snapshot at plan-time (oracle as of 2026-08-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->
