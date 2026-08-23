# R474 强制重设计规范

本文件给出可直接转化为 successor round 的最小规范。任何实现偏离都应重新做同等级审查。

## 1. 冻结新的确认性问题

### 目标

在冻结的 4 环、训练预算、learner、场景库与 seed 下，估计并检验：

```text
actor source:  authentic N vs same-time row-permuted P
critic source: authentic N vs same-time row-permuted P
```

效应定义为正向：

```text
Delta = mean_seed[ log(loss_P / loss_N) ]
```

材料性阈值：

```text
delta = log(1.10)
```

确认性假设族：

```text
H0_actor:  Delta_actor  <= delta
H0_critic: Delta_critic <= delta
```

两个 p 值用 Holm 控制 familywise alpha 0.05。

### 非目标

- 不估计纯语义信息值；
- 不声称优化 gap 被消除；
- 不对场景或拓扑总体作概率泛化；
- 不把未通过解释为“无效应”。

---

## 2. P 路由的唯一主规格

### 2.1 推荐实现

不要从 own feature 列重新拼两个标量，也不要把一个设备复制两次。直接置换环境已经构造的真实 N 邻居块：

```python
ROW_PERM = np.array([1, 2, 3, 0], dtype=np.int64)  # rho(i)=i+1 mod 4


def source_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
    current = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
    if source == "N":
        return current.copy()

    rows = current.copy()
    if source == "0":
        rows[:, 3:7] = 0.0
        return rows
    if source != "P":
        raise ValueError(f"unknown source: {source}")

    # Own features remain those of recipient i.
    # Only the authentic N neighbour tuple is row-permuted.
    rows[:, 3:7] = current[ROW_PERM, 3:7]
    return rows
```

反方向 `[3,0,1,2]` 也合法，但主方向必须在运行前固定。不要动态选择更有利的方向。

### 2.2 结构证明

设 `rho(i)=i+1`。真实行 `N[rho(i)]` 的两个来源是 `rho(i)` 的真邻居，即 `{i, i+2}`。接收者 `i` 的真邻居是 `{i-1,i+1}`，两集合不相交。由于 `rho` 是无固定点的行置换：

- 每列多重集保持；
- 完整四元组多重集保持；
- 每个接收者获得不同于自身 N 的来源元组；
- 同时刻与同一 `joint` 保持。

### 2.3 必须删除的旧逻辑

删除：

```python
pivot = (i + 2) % 4
rows[i, 3] = current[pivot, 1]
rows[i, 4] = current[pivot, 1]
rows[i, 5] = current[pivot, 2]
rows[i, 6] = current[pivot, 2]
```

删除“per-column equality is not well-defined”这一 operationalization。逐列相等是 guardrail 的明文条件；如果某候选映射不能满足，应换映射，而不是降低门槛。

---

## 3. 新 routing gate

### 3.1 来源-ID结构门

用离散来源 ID，而非随机浮点偶然相等，构造：

```text
N source tuple IDs for i = COMM_ADJ[i]
P source tuple IDs for i = COMM_ADJ[rho(i)]
```

必须验证：

1. `rho` 是 0..3 的置换；
2. `rho(i) != i`；
3. 对每个 i，P 的两个来源都不在 `COMM_ADJ[i]`；
4. 对每个 slot，N/P 来源-ID多重集相同；
5. N/P 完整有序二元来源元组多重集相同；
6. 对每个 i，P 元组不同于 N 元组；
7. P 每个元组的两个来源不同。

### 3.2 实际值门

对真实和合成 `joint` 的实际函数输出：

```python
n_rows = source_rows(joint, "N")
p_rows = source_rows(joint, "P")

for c in range(3, 7):
    assert np.array_equal(np.sort(n_rows[:, c]), np.sort(p_rows[:, c]))

assert multiset_rows(n_rows[:, 3:7]) == multiset_rows(p_rows[:, 3:7])
assert np.array_equal(n_rows[:, :3], p_rows[:, :3])
```

不要从“预期来源公式”另算一个池来代替实际输出。

### 3.3 必须包含的负例/变异测试

- 当前 `i+2` 双槽复制实现必须 FAIL；
- 任意交换一个 P 槽必须 FAIL；
- 任意引入真邻居来源必须 FAIL；
- 固定点行置换必须 FAIL；
- 从另一个时间步或 donor bank 取值必须 FAIL；
- `same_contemporaneous_pool` 不能硬编码；应通过唯一输入 joint 的时间/状态身份记录或纯函数数据流证明；
- 对 `source_rows` 做 mutation testing，确认 gate 能杀死错误变体。

### 3.4 real-ANDES 检查定位

三步 ANDES smoke 只能证明集成路径可运行，不能替代结构证明。正确层级是：

```text
来源-ID完整证明 -> 合成 actual-output 测试 -> real-ANDES integration smoke
```

三者缺一不可。

---

## 4. 全 fresh 的低成本确认性因子设计

### 4.1 训练集合

```text
actor source  in {N,P}
critic source in {N,P}
reward        in {0,1}
seeds         = 401..406（或在重做 power 后预注册扩展）
```

对应 arms：

```text
an_cn_r0, an_cn_r1
an_cp_r0, an_cp_r1
ap_cn_r0, ap_cn_r1
ap_cp_r0, ap_cp_r1
```

总计：

```text
8 arms × 6 seeds = 48 fresh runs
```

### 4.2 与当前 60-run 方案的转换

| 动作 | runs |
|---|---:|
| 保留 fresh `an_cp`, `ap_cn`, `ap_cp` 两 reward | 36 |
| 新增 fresh `an_cn` 两 reward | 12 |
| 删除 `a0_cp`, `ap_c0` 两 reward | -24 |
| 新总数 | **48** |

旧 0-source cells 可在附录作历史描述，不进入确认性 N/P 主效应。

### 4.3 统一评估批次

所有 48 个确认性 checkpoint 必须由同一版本、同一轮的 evaluator 重评。不得把旧 R473 eval JSON 与新 R474 eval 混在主分析中。

### 4.4 bridge 用法

fresh `an_cn` 与旧 R473 `an_cn` 可做复现 bridge：

- 比较 base、half/final checkpoint、curves、manifest 与 endpoints；
- 逐位一致可证明该特定 arm/seed/runtime 路径可复现；
- bridge 只作复现证据，确认性主效应仍使用 fresh cell；
- 不得看到 bridge 结果后选择 old/fresh 中更有利者。

---

## 5. Endpoint 与对比

### 5.1 profile 聚合

首选：在每个 seed、reward、另一个 source 水平和 evaluation profile 内先计算配对日志差，再按预注册等权规则聚合。这样 P/N 使用相同 profile 配对。

例如 actor 效应：

```text
D_actor,s = average over critic∈{N,P}, reward∈{0,1}, profile:
            log(L_P,critic,reward,profile,s / L_N,critic,reward,profile,s)
```

critic 同理。

若保留 upper median，必须把 estimand 明确写成“四个 profile endpoint 的第三顺序值”，并把等权 profile-paired 对比作为主敏感性检查。

### 5.2 交互

报告 actor×critic 与 reward 交互，但默认描述性。若要把交互升级为确认性 hypothesis，必须在运行前扩展 multiplicity family 并重做 power。

---

## 6. 直接材料性推断

### 6.1 符号翻转函数

```python
from itertools import product


def signflip_p_one_sided(values, null):
    z = np.asarray(values, dtype=float) - float(null)
    observed = float(np.mean(z))
    permuted = [
        float(np.mean(z * np.asarray(signs)))
        for signs in product((-1.0, 1.0), repeat=len(z))
    ]
    return sum(v >= observed for v in permuted) / len(permuted)
```

确认性 p 值：

```python
p_actor  = signflip_p_one_sided(actor_seed_effects,  math.log(1.10))
p_critic = signflip_p_one_sided(critic_seed_effects, math.log(1.10))
```

然后只对这两个材料性 p 值执行 Holm。

### 6.2 假设声明

二选一并封存：

1. **设计型随机化**：每 seed 内预先随机分配 N/P 到运行槽，保存分配记录；采用 sharp-null 随机化解释；或
2. **模型型符号翻转**：明确假设 seed-level 中心化差值在 null 下具有符号对称性，并把正态 paired-t、wild bootstrap 等作为敏感性分析。

不能把“枚举了所有符号”本身当作 exact 性的充分条件。

### 6.3 CI 与材料性

- 主结论由直接材料性 p 值 + Holm 决定；
- 可通过同一检验反演得到单侧下界；
- percentile bootstrap CI 标记 `DESCRIPTIVE-SENSITIVITY`；
- 完全枚举 `6^6` bootstrap resamples，消除不必要的 Monte Carlo 误差；
- 输出六个 seed effect、均值、中位数、最小值、leave-one-out、方向计数。

### 6.4 power

删除 `adequate_by_normal_approximation` 作为放行布尔值。新的 power 文档必须指定：

- null 边界 `log(1.10)`；
- 材料性以上备择，例如 `log(1.20)`；
- 两检验 Holm；
- seed 差值分布/方差来源与不确定性；
- 实际离散符号翻转程序；
- 预期缺失/失败率。

若 n=6 仍因成本保留，应把研究标记为低分辨率确认/探索性混合，并避免“80% power to establish >10%”表述。

---

## 7. 分类实现

推荐把状态拆成正交字段，而不是单一字符串吞掉所有信息：

```json
{
  "design": "VALID | INVALID",
  "execution": "COMPLETE | INCOMPLETE",
  "integrity": "PASS | FAIL",
  "training_dynamics": "STABLE | UNSTABLE | NOT_ASSESSED",
  "material_effect": "ESTABLISHED | NOT_ESTABLISHED | NOT_TESTED",
  "scope": "fixed-budget finite-bank total algorithm effect"
}
```

最终 human-readable verdict 由这些字段组合。规则：

- design/execution/integrity 任一失败，不计算确认性 effect verdict；
- dynamics 不稳不自动删除固定预算估计，但禁止“optimization-resolved”措辞；
- 未通过材料性门 = `NOT_ESTABLISHED`，不是 `NO EFFECT`；
- 只有上界/等效检验支持时，才可写 `BELOW_MATERIALITY_ESTABLISHED`。

---

## 8. 证据与代码门

### 8.1 seal

`load_seal` 每次必须重新验证：

- plan、power、reuse/bridge、rehearsal、capacity、routing gate；
- 两个结构化 review；
- runner/tests/所有父脚本/agent/environment；
- exact commit/ref 与 runtime lockfile；
- shard list hash。

### 8.2 rehearsal

所有 probe 必须进入统一 required list：

```python
required = {
    "routing": ...,
    "objective_semantics": all(checks["objective_semantics_probe"].values()),
    "reward": ...,
    "terminal": ...,
    "u3_paths": all(...),
    "no_donor_cli": ...,
    "short_andes": ...,
}
checks["passed"] = all(required.values())
```

禁止“记录了 probe，但未参与 passed”。

### 8.3 review

review artifact 顶层至少包含：

```text
schema_version
reviewer_id / provenance
reviewed_commit
reviewed_file_hashes
decision = PASS|FAIL
open_p0_count
open_p1_count
findings[]
```

seal 只接受 `decision=PASS` 且 `open_p0_count=open_p1_count=0`。禁止用 Markdown 子串搜索。

### 8.4 完整 CI

在完整实验仓库执行并保存：

```text
python -m py_compile ...
pytest -q tests/test_run_r474_u2_source_factorial.py
完整父 runner diff
routing mutation suite
rehearsal
seal reload/drift negative tests
```

没有真实日志时不得写 “tests passed” 或 “review independently verified”。

---

## 9. 启动前验收清单

以下全部为真才可启动：

- [ ] P 使用 N 邻居块循环行置换，不再双槽复制对角值；
- [ ] 来源-ID、逐槽实际值、完整元组多重集全部通过；
- [ ] 当前旧映射作为负例确定失败；
- [ ] 确认性 cells 全部同轮 fresh；
- [ ] 所有确认性 checkpoint 同轮重评；
- [ ] 材料性 p 值直接在 `log(1.10)` 边界计算；
- [ ] actor/critic 材料性 p 值执行 Holm；
- [ ] power 针对“超过阈值”而非“拒绝零”重做；
- [ ] endpoint/profile 聚合定义无歧义；
- [ ] missing、integrity、dynamics、effect 状态分离；
- [ ] rehearsal 每个关键 probe 真正进入 passed；
- [ ] seal reload 重验全部证据哈希；
- [ ] 两份结构化独立 review 均无开放 P0/P1；
- [ ] 完整仓库 CI 与 real-ANDES smoke 有真实成功日志。
