# R436 execution amendment — local 参照臂执行路径修复 (2026-08-19)

**Precedent**: R281/R283 execution_amendment_20260729.md (分析层声明, 不改
plant / 不改数据口径). 本修正案同为执行层声明: plant、数据口径、判定树、
阈值全部未动; 只替换了有缺陷的 local 参照臂执行路径。

## 触发

第一遍评估 (driver log `tmp/andes/R436_shard_logs_20260819T142111.959062Z/`,
22:19-22:50, 10/10 shard exit 0) aggregate 后 classify 显示: bandpass 参照
端点 r_d/r_cross 全 Infinity, nominal 锚未过。根因定位在 local 参照臂:

1. `_run_eval_job` 以位置参数调用
   `FeasibilityNativeLocalController.act(frequencies, dt_seconds)`, 真实
   签名是 keyword-only (`*, frequencies_hz, dt_seconds`) → 每步 TypeError
   → local 臂 10/10 记录 "incomplete or failed" → 所有比值 Infinity。
2. (科学正确性) local 控制器是带积分器的 PI 律, 但在 step 循环内每步
   重新构造 → 积分状态每步清零 → 即便能跑, local 参照轨迹也科学无效。

## 修复 (runner `scripts/run_r436_energy_residual_sac.py`)

1. local 臂调用改 keyword: `act(frequencies_hz=..., dt_seconds=...)`。
2. local 控制器构造移到循环外 (轨迹开始构造一次, 积分状态跨步保留)。

两处修复只落在 eval 路径 (`_run_eval_job`); train 路径
(`_train_arm_seed`) 未触碰 → 训练 ckpt (10/10, 43200 步, 0 TDS 失败)
仍由 seal e88b7667 (runner sha `3944c194…495a`) 覆盖, 不重训。

## 执行重跑

- 第一遍输出全部删除 (create-only 输出无法覆盖写; 被删 10 变体的
  JSON sha256 指纹留档):
  nominal `8e02f9db…`, out_Line_4 `dcb55713…`, out_Line_5 `887805d2…`,
  out_Line_7 `063e7f7b…`, out_Line_8 `25e1fbde…`, x0p5_Line_4 `04c3547e…`,
  x0p5_Line_7 `9b4ea9de…`, x1p5_Line_4 `048d7b13…`, x1p5_Line_7
  `1b98d708…`, x1p5_Line_7_12 `fb286eef…`。
- 第二遍评估 22:53:37 启动 (driver log
  `tmp/andes/R436_shard_logs_20260819T145336.788603Z/`), 8 workers,
  与 R438 训练并发共享 CPU (owner 常设并发授权; 22:45 实测内存
  17/27 GiB, 未超预算)。runner 此时 sha256:
  `1c6d0720bed710c06231ee13957cfc45919676fc26e6480196d61e0d79012462`。
- seal 文件本身不再可重写 (prepare 为 create-only 且要求 output
  absence), 故本修正案声明: 训练执行于旧 runner (seal 覆盖), 第二遍
  评估与 aggregate 执行于新 runner (本修正案覆盖)。

## 第二修正 (2026-08-20, 缺陷 3, 由 Session A 在第二遍之后发现)

第二遍评估 aggregate 后 nominal 锚仍不过 (bandpass r_d=0.924357 /
r_cross=0.889806 vs R408 锚 0.938947/0.539791)。根因: eval 路径
(`_run_eval_job` / `_run_eval_job_seed`) 的 action map 调用每步用固定
`soc=0.5` 与零 `previous_power_system_pu`, 未按 R408/R413 语义跨步
跟踪能量端口状态 → local 臂 (PI 积分 + 能量投影) 数值漂移。
修复: 两步跨步跟踪 current_soc / previous_power_system_pu (与 R408
`_run_job` 逐字对齐)。验证: 修复后 local 臂差分能量 0.00038671873518287457
与 R413 bit-identical。第二遍输出删除, 第三遍评估 23:47-00:46
(driver log `tmp/andes/R436_shard_logs_20260819T154825*/`, 8 workers,
wall 3690s, 10/10 exit 0), aggregate 后 nominal 锚 2.2e-7 复现
(r_d=0.9389467910702068 / r_cross=0.5397906554502304), 分类
NO-LEARNING-INCREMENT, round 已 close (CLM-1345, feed R436.md)。

## 边界

- 不改 plant, 不改数据口径 (bandpass K=3.5 / local / 学习臂 reward 公式
  全部原样), 不改判定树 (plan.md §Outcomes), 不在结果上重调阈值。
- 第一/第二修正只替换有缺陷的 local 臂执行路径; 其余臂执行路径未动。
- 正式结果 = 第三遍评估 + 一次 aggregate; 训练 ckpt (10/10, 43200 步,
  0 TDS 失败) 由 seal e88b7667 (runner sha `3944c194…495a`) 覆盖,
  评估/aggregate 由本修正案覆盖 (runner sha 逐次记录于各 driver_result)。
