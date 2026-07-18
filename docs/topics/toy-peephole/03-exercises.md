# 03 扩展练习

> 这三个练习建立在 demos 01-03 的基础上。每个练习预期 30-60 分钟完成。
> 练习中没有给出完整代码实现，只有思路引导。建议先自己试，卡住再看提示。

---

## 练习 1: mul→slli 乘法转移位（⭐）

**难度**: ⭐

**问题描述**: RISC-V 中乘法指令 `mul` 通常需要多个周期才能执行完毕。但如果乘数是 2 的幂（比如 1, 2, 4, 8, 16...），乘法就等价于左移：`mul rd, rs, 2^n` 等价于 `slli rd, rs, n`。移位指令只用一个周期，是免费的。

目前我们的窥孔优化器有 6 条规则，但没有关于乘法的。请添加第 7 条规则：匹配 `mul rd, rs, imm` 中的 `imm` 是 2 的幂的情况，替换为 `slli rd, rs, n`。

这条规则的模式（pattern）是 `["mul"]`（只匹配一条指令）。条件和替换逻辑：

1. 检查 mul 的第三个操作数（立即数）是否是 2 的幂（大于 0 且只有一位是 1）
2. 如果是，计算 n = log2(imm)
3. 替换为 `slli rd, rs, n`

**预期行为**:

```
# 输入
  mul x1, x2, 8
  mul x3, x4, 1
  mul x5, x6, 3    # 3 不是 2 的幂，不匹配

# 输出
  slli x1, x2, 3   # 8 = 2^3
  slli x3, x4, 0   # 1 = 2^0
  mul x5, x6, 3    # 不变
```

**提示**:

- 提示 1：检查一个数是否是 2 的幂有一个经典技巧：`x > 0 and (x & (x - 1)) == 0`。例如 8 的二进制是 1000，8-1=7 是 0111，1000 & 0111 = 0
- 提示 2：计算以 2 为底的对数可以用 `bit_length()`：`n = imm.bit_length() - 1`。例如 8 的二进制是 1000，bit_length() 返回 4，减 1 得 3
- 提示 3：操作数提取使用 `_op(w, idx)` 辅助函数，和现有规则一样。mul 的操作数格式是 `(opcode, [rd, rs, imm])`
- 提示 4：这条规则应该放在 `get_default_rules()` 返回列表的末尾。注意规则顺序影响优化结果——如果前面有规则先匹配了 mul 相关的其他模式，这条可能就不会触发

**自检用例**:

```python
from toy_peephole.demo02_engine import get_default_rules, peephole_pass, PeepholeRule
from toy_peephole.demo01_parser import parse_asm, lines_to_asm

# 测试输入
asm_text = """\
  mul x1, x2, 8
  mul x3, x4, 1
  mul x5, x6, 3
  mul x7, x8, 16
"""
lines = parse_asm(asm_text)
rules = get_default_rules() + [mul_to_slli_rule]  # 添加你的规则

optimized, changes, matches = peephole_pass(lines, rules)
output = lines_to_asm(optimized)

# 验证
assert changes == 3                    # 8, 1, 16 都被替换了
assert "slli x1, x2, 3"  in output     # 8 → 2^3
assert "slli x3, x4, 0"  in output     # 1 → 2^0
assert "mul x5, x6, 3"   in output     # 3 不是 2 的幂，保留
assert "slli x7, x8, 4"  in output     # 16 → 2^4
assert "mul" not in [line[0] for line in optimized if line[0] is not None and not isinstance(line[0], tuple)]
# 除了 3 的那个，其他 mul 应该都不见了
```

---

## 练习 2: rem→andi 取模转位与（⭐⭐）

**难度**: ⭐⭐

**问题描述**: 取模运算 `rem rd, rs, imm` 在硬件上通常比乘法还慢（18-30 个周期）。但如果除数是 2 的幂，取模等价于位与操作：`rem rd, rs, 2^n` 等价于 `andi rd, rs, (2^n - 1)`。这是因为除以 2 的幂的余数就是低 n 位的值。

例如：`rem x1, x2, 8` → 等价于 `andi x1, x2, 7`（8-1=7，二进制 0111，正好保留低 3 位）。

你的任务是添加一条 `rem → andi` 规则。注意以下细节：

1. **有符号问题**：`rem` 在 RISC-V 中是有符号取模，而 `andi` 是位与操作。对于正数两者等价，但对于负数，`rem` 的结果和被除数符号相同。你可以先假设操作数都是正数来处理（简化版），或者在条件检查中添加对符号的处理
2. **立即数范围**：`andi` 的立即数是 12 位有符号数（范围 -2048 到 2047）。因此 `2^n - 1` 必须小于等于 2047（即 n <= 11）。超过这个范围可以用 `li` + `and` 的组合，但作为练习，先处理 n <= 11 的情况即可
3. **n=0**：`rem rd, rs, 1` 等价于 `andi rd, rs, 0` —— 任何数除以 1 的余数都是 0。但 `andi rd, rs, 0` 也是合法的，只是它相当于把结果置 0

**预期行为**:

```
# 输入
  rem x1, x2, 8
  rem x3, x4, 2
  rem x5, x6, 7     # 7 不是 2 的幂，不匹配
  rem x7, x8, 2048  # 2^11，andi 范围边界

# 输出
  andi x1, x2, 7    # 8 → 8-1 = 7
  andi x3, x4, 1    # 2 → 2-1 = 1
  rem x5, x6, 7     # 不变
  andi x7, x8, 2047 # 2048 → 2047（需要检查 12 位范围）
```

**提示**:

- 提示 1：判断 power-of-2 直接复用练习 1 中的方法。取模的除数（rem 的第三个操作数）是 2 的幂就走优化路径
- 提示 2：掩码值 = 2^n - 1。需要确保这个值在 12 位有符号范围内。可以加一个检查：`mask <= 2047`（因为 2047 = 0x7FF，是正数最大 12 位有符号值）
- 提示 3：如果掩码超过 2047（n >= 12），可以分两步：先用 `li rd, mask` 加载常量，再用 `and rd, rs, rd`。或者直接跳过不优化——练习中先用简单版本
- 提示 4：规则顺序建议放在 `mul→slli` 之后，避免干扰

**自检用例**:

```python
from toy_peephole.demo02_engine import get_default_rules, peephole_pass
from toy_peephole.demo01_parser import parse_asm, lines_to_asm

asm_text = """\
  rem x1, x2, 8
  rem x3, x4, 1
  rem x5, x6, 7
  rem x7, x8, 2048
  rem x9, x10, 4
"""
lines = parse_asm(asm_text)
rules = get_default_rules() + [mul_to_slli_rule, rem_to_andi_rule]

optimized, changes, matches = peephole_pass(lines, rules)
output = lines_to_asm(optimized)

assert changes == 4                    # 8, 1, 2048, 4 都被替换
assert "andi x1, x2, 7"   in output    # 8-1 = 7
assert "andi x3, x4, 0"   in output    # 1-1 = 0
assert "rem x5, x6, 7"    in output    # 7 不是 2 的幂，不变
assert "andi x7, x8, 2047" in output   # 2048-1 = 2047
assert "andi x9, x10, 3"  in output    # 4-1 = 3
```

---

## 练习 3: 指令级成本模型（⭐⭐⭐）

**难度**: ⭐⭐⭐

**问题描述**: 目前窥孔优化器的报告只统计了**指令数量**的减少：`Instructions before / after / saved`。但不同指令的"成本"不一样——一条 `mul` 可能花 3-5 个周期，一条 `rem` 可能花 18-30 个周期，而一条 `addi` 只要 1 个周期。只统计指令数会误导优化方向：你可能会优先消除 `addi`（因为多，容易消除），而不是优先消除 `mul` 和 `rem`（虽然少，但省下的周期多）。

你的任务是给窥孔优化器增加一个**指令级成本模型**：

1. 在 `PeepholeRule` 中添加一个 `cost_saved: int` 字段，表示每次该规则触发节省的周期数
2. 为每条规则设置合理的成本值：
   - `addi+addi fusion`：节省 1 个周期（省了一条 addi）
   - `li+addi fusion`：节省 1 个周期
   - `beq zero-zero to j`：节省 0 个周期（相同成本，但指令编码更短——可设置小值如 0）
   - `mv swap elimination`：节省 2 个周期（删了两条 mv）
   - `mv chain shortening`：节省 1 个周期
   - `addi zero elimination`：节省 1 个周期
   - `mul → slli`（练习 1）：节省 3 个周期（mul 约 4 周期，slli 约 1 周期）
   - `rem → andi`（练习 2）：节省 17 个周期（rem 约 18 周期，andi 约 1 周期）
3. 修改 `print_report()` 函数，在原有统计基础上增加成本统计：总节省周期数、每规则节省周期数

**预期行为**:

```
# 优化前
  mul x1, x2, 8     # 4 cycles
  rem x3, x4, 16    # 18 cycles
  addi x5, x5, 3    # 1 cycle
  addi x5, x5, 5    # 1 cycle

# 优化后
  slli x1, x2, 3    # 1 cycle (saved 3)
  andi x3, x4, 15   # 1 cycle (saved 17)
  addi x5, x5, 8    # 1 cycle (saved 1)

# 报告输出
Instructions before: 4
Instructions after:  3
Saved:               1 (25%)

Cycles before:       24
Cycles after:        3
Cycles saved:        21 (87.5%)

Per-rule cost savings:
  rem → andi:       17 cycles
  mul → slli:        3 cycles
  addi+addi fusion:  1 cycle
```

**提示**:

- 提示 1：修改 `PeepholeRule` 数据类，添加 `cost_saved: int = 0` 字段。注意 `get_default_rules()` 中创建规则的地方都需要给这个字段赋值
- 提示 2：成本累加逻辑在 `peephole_pass()` 和 `peephole_optimize()` 中。需要用 `cost_saved * count` 来计算总节省。可以把成本信息加入 `rule_matches` 字典，或者单独传一个成本字典
- 提示 3：计算"优化前总周期数"需要一个函数 `estimate_cycles(lines) -> int`，遍历所有指令，通过操作码估算周期。可以维护一个简单的成本表，把 `mul` → 4, `rem` → 18, `div` → 18, `addi/add/mv/sub/and/or/slli/srli/li/j` → 1。没有在成本表中的指令统一算 1
- 提示 4：成本模型只是估值，不同处理器上不同指令的实际周期不一样。可以在报告末尾加一行注释：`* Cycle estimates are approximate; actual values depend on the specific processor implementation.`

**自检用例**:

```python
from toy_peephole.demo03_full import peephole_optimize, print_report
from toy_peephole.demo02_engine import get_default_rules, PeepholeRule
from toy_peephole.demo01_parser import parse_asm

# --- 第一步：验证成本数据能正确累加 ---
asm_text = """\
  mul x1, x2, 8      # saved 3 (mul → slli)
  rem x3, x4, 16     # saved 17 (rem → andi)
  addi x5, x5, 3
  addi x5, x5, 5     # saved 1 (addi+addi fusion)
"""
lines = parse_asm(asm_text)
rules = get_default_rules()  # 需要已经更新了 cost_saved 字段

after, changes, matches = peephole_optimize(lines, rules)

# 总节省周期数 = 3 + 17 + 1 = 21
# 这个值取决于你的具体实现，关键是准确累加

# --- 第二步：验证报告输出包含成本信息 ---
print_report(lines, after, changes, matches)
# 输出中应该包含 "Cycles saved" 和每规则的周期节省

# --- 第三步：验证没有优化机会时成本为 0 ---
asm_optimal = """\
  addi x1, x0, 1
  j done
done:
  ret
"""
opt_lines = parse_asm(asm_optimal)
after2, changes2, matches2 = peephole_optimize(opt_lines, rules)
assert changes2 == 0

# --- 第四步：验证 estimate_cycles 函数 ---
from your_implementation import estimate_cycles
input_cost = estimate_cycles(lines)
output_cost = estimate_cycles(after)
assert input_cost == 24       # 4 + 18 + 1 + 1 = 24
assert output_cost == 3       # 1 + 1 + 1 = 3
assert input_cost - output_cost == 21  # 节省 21 周期
```

---

## 延伸思考

做完以上三个练习后，可以继续挑战：

1. **负立即数的 mul→slli**：`mul rd, rs, -8` 等价于 `slli rd, rs, 3` 后接 `neg rd, rd`，或者直接移位后取负。想一想怎么处理
2. **div→srai**：`div rd, rs, 2^n` 等价于 `srai rd, rs, n`（仅适用于正数）。对于负数，算术右移和除法的舍入规则不同，需要额外修正
3. **动态成本模型**：当前成本是固定的。真实编译器中，成本取决于目标处理器的流水线深度、有无硬件除法器、缓存延迟等。实现一个可配置的 `CostModel` 类，允许传入不同处理器的成本表
