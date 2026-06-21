# Topic 16 — LLVM 代码生成后端

> **难度**: 中级 | **源文件**: `scratchv/backend/llvm_codegen.py`, `scratchv/standalone/onnx_to_llvm_standalone.py`

---

## 是什么？

LLVM 代码生成器将 ScratchV IR / ONNX 模型翻译为 **LLVM IR 文本**（`.ll` 文件）。这是 ScratchV 的 **float32 路径**，与 Q16.16 定点路径互补，生成的 LLVM IR 可以接入 LLVM 全套工具链（`opt`、`llc`、`lli`）。

```
ONNX 模型
    │
    ├─→ 原生路径: RV32IM 定点机器码 (.bin)
    │
    └─→ LLVM 路径: LLVM IR (.ll) → llc → RISC-V 64 浮点汇编 (.s)
                    这条就是你正在看的
```

---

## 为什么？

1. **基准对比**: LLVM 路径使用 float32 + 硬件浮点指令（`fmul`, `fadd`），每条 MAC ~2 条指令；原生路径使用 Q16.16，每条 MAC ~12 条。对比两边的差距，找到优化方向
2. **LLVM 全套优化**: 生成的 `.ll` 可以接 `opt -O3` 享受 LLVM 的循环展开、向量化、指令合并等
3. **多目标**: LLVM IR 可以编译到 RV64、x86-64、ARM 等多个平台

---

## 核心概念

### 两条 LLVM 路径

| | 路径 A (库路径) | 路径 B (Standalone) |
|------|---------------|-------------------|
| 文件 | `backend/llvm_codegen.py` | `standalone/onnx_to_llvm_standalone.py` |
| 输入 | IR Program | ONNXModel (手工解析) |
| 状态 | 框架完整，NN 算子占位 | 完整的 float32 循环生成 |
| 依赖 | 可选 llvmlite | Python stdlib only |

### LLVM IR 关键特性

与 ScratchV 原生路径的差异：

| 特性 | LLVM IR | ScratchV 原生 |
|------|---------|-------------|
| 地址计算 | `getelementptr` 单指令 | 手动 `MUL + ADD` 链 (~5条) |
| 浮点运算 | `fmul`, `fadd` 原生 | `MUL + SRAI 16` (Q16.16) |
| 循环结构 | `phi` 节点 + `icmp` + `br` | 手动 label + jump |
| 类型系统 | LLVM 类型系统 | 原始 32-bit 整数 |
| 优化 | `opt -O3` 全套 pass | 无后优化 |

### LLVM IR 示例：Conv2D 内层循环

```llvm
define void @conv2d(float* %input, float* %weight, float* %bias, float* %output) {
entry:
  br label %oh_loop

oh_loop:
  %oh = phi i32 [0, %entry], [%oh_next, %oh_inc]
  %oh_cond = icmp slt i32 %oh, 32
  br i1 %oh_cond, label %ow_loop, label %exit

ow_loop:
  ; ... 嵌套到最内层 ...
  %in_ptr = getelementptr float, float* %input, i32 %in_offset
  %in_val = load float, float* %in_ptr
  %w_val = load float, float* %w_ptr
  %mul = fmul float %in_val, %w_val       ; 浮点乘法
  %acc_new = fadd float %acc, %mul         ; 浮点累加
  br label %ic_inc

exit:
  ret void
}
```

---

## 一步步

### Step 1: 生成 LLVM IR

```bash
# 使用 Standalone 路径（推荐，完整 float32）
python scratchv/standalone/onnx_to_llvm_standalone.py models/graph/cnn.onnx \
    -o output.ll --compare

# --compare 会估算 LLVM 和 ScratchV 的动态指令数差距
```

### Step 2: 优化 LLVM IR

```bash
# 用 LLVM 优化器
opt -O3 output.ll -o optimized.ll

# 查看优化效果
diff <(wc -l output.ll) <(wc -l optimized.ll)
```

### Step 3: 编译为 RISC-V 汇编

```bash
# 静态编译
llc -O3 -march=rv64fd -mattr=+d,+f optimized.ll -o output_llvm.s

# JIT 执行（调试用）
lli output.ll
```

### Step 4: 完整对比流程

```bash
# 一键生成对比数据
python scratchv/standalone/llvm_cache_compare.py \
    --json-output output/llvm_vs_scratchv.json

# 生成仪表盘
python scratchv/ci/dashboard.py --run -o benchmark_reports/dashboard.html
```

---

## 代码走读

### LLVMIRBuilder 辅助类

```python
class LLVMIRBuilder:
    def __init__(self):
        self._reg_counter = 0
        self._output = []

    def new_register(self) -> str:
        self._reg_counter += 1
        return f"%{self._reg_counter}"

    def emit_fmul(self, a: str, b: str) -> str:
        r = self.new_register()
        self._output.append(f"  {r} = fmul float {a}, {b}")
        return r

    def emit_gep(self, base: str, idx: str) -> str:
        r = self.new_register()
        self._output.append(
            f"  {r} = getelementptr float, float* {base}, i32 {idx}"
        )
        return r

    def emit_header(self):
        self._output.extend([
            'target triple = "riscv64-unknown-elf"',
            'target datalayout = "e-m:e-p:64:64-..."',
            "",
        ])
```

### Conv2D 的 LLVM IR 生成

与原生路径的差异：
- 用 `phi` 节点实现循环（无需手动 `br` + label）
- 用 `getelementptr` 做地址计算（替代 MUL+ADD 链）
- 用 `fmul`/`fadd` 做浮点乘加（替代 Q16.16 的 MUL+SRAI）

```python
def gen_conv2d(self, node, model):
    # 外层循环用 phi 节点
    self.emit("br label %oh_loop")
    self.emit("oh_loop:")
    self.emit("  %oh = phi i32 [0, %entry], [%oh_next, %oh_inc]")
    # ... 6 层嵌套 phi 循环 ...

    # 最内层 MAC
    in_val = builder.emit_load(in_ptr)
    w_val = builder.emit_load(w_ptr)
    mul = builder.emit_fmul(in_val, w_val)
    acc = builder.emit_fadd(acc, mul)
```

---

## 动手练习

### 练习 1: 阅读 LLVM IR

生成 CNN 模型的 LLVM IR，找到 Conv2D 的最内层循环代码，和 Q16.16 版本对比指令数。

### 练习 2: 体验 opt -O3 的效果

对一个 LLVM IR 文件分别用 `-O0`、`-O2`、`-O3` 优化，用 `diff` 对比优化后的 IR 有什么不同。

### 练习 3: 多目标编译

用 `llc -march=x86-64` 把 LLVM IR 编译为 x86 汇编，看看和 RISC-V 版本有什么不同。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **llvmlite 安装** | 路径 A 需要 `llvmlite`，在某些平台（ARM Mac、非 x86）可能安装失败。路径 B 不需要 |
| **Target triple** | 当前是 `riscv64-unknown-elf`，如果要编译到其他平台需要修改 |
| **float32 vs Q16.16 精度差异** | LLVM 路径用原生 float32，和 Q16.16 路径结果有微小差异（~1.5e-5 相对误差） |
| **phi 节点的复杂性** | 写 phi 节点比写 label+jump 更难，循环嵌套深时容易写错 |

---

## 进阶阅读

- [LLVM Language Reference](https://llvm.org/docs/LangRef.html) — LLVM IR 完整语法
- [ARCHITECTURE.md](../ARCHITECTURE.md) — 双路径对比详解
- [03-指标解读指南](../03-指标解读指南.md) — 如何解读 LLVM vs ScratchV 的性能差距
- 相关 topic: [Topic 08 — 指令选择](08-指令选择.md) | [Topic 19 — Standalone RISC-V 编译器](19-Standalone-RISC-V编译器.md) | [Topic 22 — Standalone LLVM 编译器](22-Standalone-LLVM编译器.md)
