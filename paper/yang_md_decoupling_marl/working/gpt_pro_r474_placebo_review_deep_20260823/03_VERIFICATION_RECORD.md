# R474 Deep 审查：验证记录与证据校准

## 1. Harness 与模式

```text
Harness: GitHub OK
Repository: wya5217799/gpt-pro-math-harness
Ref: main（工具未返回可固定的 default-branch commit SHA，因此未猜测 SHA）
Mode: deep
Loaded:
  README.md
  NAVIGATION.md
  AGENTS.md
  profiles/deep.md
  harness/WORKFLOW.md
  harness/CONTEXT_POLICY.md
  harness/VERIFICATION.md
```

本任务按“冻结命题 -> 证伪优先 -> 多路线审查 -> 精确计算 -> 敌对审计 -> 证据分级”执行。没有把同一上下文的重复检查描述为独立 reviewer。

## 2. 输入完整性

### 实际执行

- 对输入 ZIP 内 `SHA256SUMS` 执行 `sha256sum -c`；列出的 17 个文件全部 `OK`。
- 输入 ZIP SHA-256：`d87dbc63fb63052366a57530eeed8b9a6cd58d846fc6ed9263c09777702f6f12`。
- 没有修改或回写用户输入。

### 证据等级

`RUN / C2`：精确文件哈希检查，证明包内列出的文件与其清单一致；不证明文件中的科学主张正确。

## 3. 代码静态检查

### 实际执行

```text
python -m py_compile \
  scripts/run_r470_u2_source_factorial.py \
  scripts/run_r474_u2_source_factorial.py \
  tests/test_run_r474_u2_source_factorial.py
```

结果：`PASS`。

### 含义

只证明三个 Python 文件可被编译为字节码；不证明依赖可导入、测试通过或运行语义正确。

## 4. 单元测试尝试

### 第一次

```text
pytest -q tests/test_run_r474_u2_source_factorial.py
```

collection 在 `import scripts...` 处失败；通过 `PYTHONPATH=.` 修正包路径后再次执行。

### 第二次

```text
PYTHONPATH=. pytest -q tests/test_run_r474_u2_source_factorial.py
```

collection 失败：

```text
ModuleNotFoundError: No module named 'andes_rl_kundur'
```

### 结论

状态：`FAILED / ENVIRONMENT-PACKAGE-INCOMPLETE`。

不能声称 R474 tests passed。失败不是数学反例，但说明当前审查包不足以完成动态实现验证；缺少 agent/environment 与多级父脚本也阻止 real rehearsal。

## 5. 精确路由枚举

### 方法

使用来源设备 ID 而非浮点值，完整枚举 4 环上的来源映射。检查：

- N/P 每个邻居槽的来源-ID多重集；
- 完整有序来源元组多重集；
- 每个接收者元组是否改变；
- P 每个来源是否为真邻居；
- 两个 P 槽是否重复；
- 在逐槽池保持和非真邻居限制下的所有可行映射。

### 当前映射的精确结果

```text
per-slot equality:      FAIL for slot 3,4,5,6
combined-channel pool:  PASS
full tuple multiset:    FAIL
within-P tuple duplicate: TRUE for every recipient
same-time construction: PASS by formula
non-neighbour pivot:    PASS
```

### 可行映射枚举

逐槽池保持、每槽来源非真邻居、且同一 feature 的两个槽不使用同一来源时，只有两个不同来源布线：

```text
rho(i)=i+1 mod 4
rho(i)=i-1 mod 4
```

两者均等价于把真实 N 的完整 `3:7` 邻居块按行循环置换。

### 证据等级

`RUN / C3`：对四设备有限来源-ID空间的完整枚举。它严格证明当前结构性 guardrail 失败和两个候选修复的有限组合性质；不证明实际 ANDES 运行无其他错误。

## 6. 统计诊断性重算

### 6.1 R473 材料性边界

使用包内已封存的六个 R473 seed-level actor/critic log effects，枚举全部 64 个符号分配。

派生结果：

```text
actor p at null 0:             0.578125
critic p at null 0:            0.015625
actor p at null log(1.10):     0.921875
critic p at null log(1.10):    0.03125
Holm first threshold:          0.025
critic materiality pass:       FALSE
```

旧 critic effect 的 97.5% 单侧符号翻转下界之上确界约 `0.0848624`，小于 `log(1.10)=0.0953102`。

用途：只诊断“零效应 Holm”与“直接材料性 Holm”的不等价性；不是 R474 结果，也不是对旧轮预注册结论的追溯改写。

### 6.2 bootstrap 完全枚举

对旧 critic 六个差值枚举 `6^6=46,656` 个有序非参数 bootstrap 重采样。exact percentile 95% 区间约：

```text
[0.12857068, 0.21634686]
```

与代码的 20,000 次区间 `[0.12867271, 0.21634686]` 几乎相同。因此 Monte Carlo 次数不是主要争议；主要问题是 small-n percentile coverage 与材料性/Holm目标不一致。

### 6.3 power 诊断

从五个先验差值得到的 `sd=0.0823901083`，在正态模型下其 95% sigma 区间约：

```text
[0.04936, 0.23675]
```

按单侧 alpha `0.025`、n=6、真实改善 20%、需要证明超过 10% 的粗略正态计算，功效约 `0.735`。这只用于指出现有“80%”标签的目标错位，不是新的封存 power analysis；正式设计应按实际 sign-flip/Holm 程序仿真。

### 证据等级

- 符号翻转枚举：`RUN / C3`，在给定六个数和指定算法范围内精确；其统计有效性仍依赖随机化/对称假设。
- bootstrap 枚举：`RUN / C3`，精确覆盖重采样空间；不自动赋予置信区间正确覆盖率。
- power 数值：`RUN / C2`，模型依赖的诊断性计算，不是证明。

## 7. 代码审计已确认的实现事实

### 已确认

- `source_rows(P)` 将 pivot 设备的两类特征各复制到两个槽。
- `routing_check` 的 pool flag 从预期来源公式重构池，而非直接比较实际 `n_rows/p_rows` 的逐槽池。
- `same_contemporaneous_pool` 在返回值中硬编码为 `True`。
- tests 明确要求旧双槽复制和合并通道池通过。
- `_upper_median` 对四个 evaluation profile 取第三顺序值。
- `_main_effect` 等权平均另一个 source 的三个水平和 reward 的两个水平。
- `_paired_inference` 只计算零中心 sign-flip p 与 percentile bootstrap CI。
- `materially_supported = holm_reject_zero AND ci_lower > log(1.10)`。
- P side 全新、N side 三分之一新/三分之二旧，因此加性批次偏移系数为 `2/3`。
- `objective_semantics_probe` 被记录但未进入 rehearsal `passed` 汇总。
- `prepare` 封存多项 evidence hashes，但继承 `load_seal` 只重验 contract 与 source entries。
- review gate 只搜索 `Decision: PASS` 子串。
- imported base manifest 的 `base_state_path` 仍可能指向 R473，继承 loader 按该路径读取。
- brief 的 10 eval shards 与代码的 20 arm-stage shards 不一致。

### 未确认

- R474 相对 R473 runner 的完整 diff；R473 runner 未包含。
- `SourceFactorialSACAgent`、ANDES env、父脚本的真实行为；内容未包含。
- real ANDES 三步 rehearsal、60/48/48-run 训练、evaluation、aggregate；均未执行。
- 两个独立代码 reviewer 的结果；相关 review 文件未包含且本上下文不独立。

## 8. 结论标签

| 命题 | 标签 |
|---|---|
| 当前 P 满足逐槽 guardrail | **DISPROVED** |
| 当前 P 是真实 N 邻居元组的置换 | **DISPROVED** |
| `rho=±1` 行置换满足有限来源-ID四项性质 | **COMPUTATIONALLY VERIFIED（完整有限枚举）**，并有直接代数证明 |
| 当前 R474 effect 是否 >10% | **INCOMPLETE / NOT RUN** |
| 当前代码在完整项目中可运行 | **INCOMPLETE**，仅 py_compile 通过，pytest 因依赖缺失未收集 |
| 独立双 reviewer gate | **NOT VERIFIED** |

## 9. 外部方法参考

这些来源只用于校准统计表述；核心路由反例不依赖外部文献。

1. Holm, S. (1979). *A Simple Sequentially Rejective Multiple Test Procedure*. Scandinavian Journal of Statistics 6(2), 65–70. JSTOR 4615733.
2. Canay, I. A., Romano, J. P., & Shaikh, A. M. (2017). *Randomization Tests Under an Approximate Symmetry Assumption*. Econometrica 85(3), 1013–1030. DOI: 10.3982/ECTA13081.
3. Hall, P. (1988). *Theoretical Comparison of Bootstrap Confidence Intervals*. The Annals of Statistics 16(3), 927–985. DOI: 10.1214/aos/1176350933.

## 10. 复核边界

本报告提供可审计的证明、有限枚举和实际命令结果，不输出隐藏思维过程。它没有使用或生成任何 R474 训练结果，没有修改私有仓库，也没有声称后台工作、机器形式化或独立审稿。
