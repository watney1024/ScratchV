# Topic 22 — Standalone LLVM 编译器

> **难度**: 高级 | **源文件**: `scratchv/standalone/onnx_to_llvm_standalone.py` (~2100行)

---

## 是什么？

Standalone LLVM 编译器是 ScratchV **float32 路径**的完整实现。它复用 Standalone RISC-V 编译器的 ONNX 解析（零依赖 protobuf 解析），但生成 float32 LLVM IR 而非 Q16.16 机器码。

```
ONNX 模型 → ONNXModel (手工解析) → LLVMCNNGenerator → LLVM IR (.ll)
                                         ↑
                                    LLVMIRBuilder (辅助)
```

---

## 为什么？

- **Baseline**: LLVM float32 路径是 ScratchV 优化的"天花板"——它使用硬件浮点指令，每条 MAC ~2 条指令
- **对比分析**: `--compare` 模式同时估算两条路径的动态指令数，量化差距
- **工具链集成**: 生成的 `.ll` 可接 `opt -O3` 和 `llc` 多目标编译

---

## 核心概念

### 四组件

| 组件 | 职责 |
|------|------|
| **ONNXModel** | 手工 protobuf 解析（复用自 RISC-V standalone） |
| **LLVMIRBuilder** | LLVM IR 文本生成辅助类 |
| **LLVMCNNGenerator** | 逐算子生成 float32 LLVM IR 循环 |
| **LLVMJITRunner** | （可选）libLLVM JIT 直接执行 |

### 支持的算子和 IR 特征

| 算子 | LLVM IR 特征 |
|------|-------------|
| Conv2D | 6层循环 + GEP + `fmul`/`fadd` MAC + padding 边界 |
| Gemm | 3层循环 + transB + GEP |
| MaxPool | 5层循环 + 边界检查 + `fcmp ogt` |
| ReLU | `fcmp ogt` + `select` |
| Sigmoid | 调用外部 `@expf` 函数 |
| Reshape | 直接 memcpy |

### 对比模式 (`--compare`)

估算 LLVM 和 ScratchV 的动态操作数差距：
- LLVM: ~5.25 亿浮点运算
- ScratchV: ~57.1 亿定点运算

---

## 一步步

```bash
# 生成 LLVM IR + 对比
python scratchv/standalone/onnx_to_llvm_standalone.py models/graph/cnn.onnx \
    -o output.ll --compare

# 用 LLVM 优化
opt -O3 output.ll -o optimized.ll

# 编译为 RISC-V 64 汇编
llc -O3 -march=rv64fd -mattr=+d,+f optimized.ll -o output.s

# JIT 执行
lli output.ll
```

---

## 代码走读

### LLVMIRBuilder

```python
class LLVMIRBuilder:
    def new_register(self) -> str:
        self._reg_counter += 1
        return f"%{self._reg_counter}"

    def emit_fmul(self, a, b):
        r = self.new_register()
        self._output.append(f"  {r} = fmul float {a}, {b}")
        return r

    def emit_gep(self, base, idx):
        r = self.new_register()
        self._output.append(
            f"  {r} = getelementptr float, float* {base}, i32 {idx}"
        )
        return r
```

### 与原生路径的关键差异

| 特性 | LLVM Standalone | ScratchV Standalone |
|------|----------------|---------------------|
| 数值 | float32 (IEEE 754) | Q16.16 定点 |
| 输出 | `.ll` 文本 | `.bin` 机器码 |
| 地址计算 | `getelementptr` | 手动 MUL+ADD |
| 每条 MAC | ~2 条（fmul+fadd） | ~12 条（MUL+SRAI+ADD+...） |
| 执行 | 需 llc/lli | 可直接加载执行 |

---

## 动手练习

### 练习 1: 阅读生成的 LLVM IR

生成 CNN 模型的 `.ll` 文件，找到 Conv2D 最内层循环，和 [Topic 16](16-LLVM代码生成.md) 的示例对比。

### 练习 2: 体验 `--compare`

运行 `--compare` 模式，理解每个算子的 LLVM vs ScratchV 指令数差异。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **llc 不可用** | 没有安装 LLVM 工具链时只能生成 `.ll`，不能编译。用 `lli` 或在线 Compiler Explorer |
| **target triple** | 固定为 `riscv64-unknown-elf`，编译到其他平台需修改 |

---

## 进阶阅读

- [ARCHITECTURE.md](../ARCHITECTURE.md) — 双路径对比详解
- [LLVM Language Reference](https://llvm.org/docs/LangRef.html)
- 相关 topic: [Topic 16 — LLVM 代码生成](16-LLVM代码生成.md) | [Topic 19 — Standalone RISC-V](19-Standalone-RISC-V编译器.md)
