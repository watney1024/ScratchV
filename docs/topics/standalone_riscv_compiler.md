# Topic: Standalone RISC-V 编译器

> **源文件**: `scratchv/standalone/onnx_to_riscv_standalone.py` (2566 行)
> **依赖**: 零 (Python stdlib only)
> **输入**: ONNX `.onnx` 文件
> **输出**: RV32IM flat binary `.bin` + 可选汇编 `.s` + 性能估算

---

## 概述

完全自包含的 ONNX→RISC-V 编译器，不依赖 `onnx` 包、不依赖 `protobuf`、不依赖 `numpy`。手工实现 protobuf wire-format 解析器，直接将 ONNX 模型编译为 RV32IM 机器码。

## 组件架构

```
onnx_to_riscv_standalone.py
├── ProtoReader          ← 手工 protobuf wire-format 解析器
├── ONNXModel            ← 提取计算图、权重、形状
├── MemoryPlan           ← 权重/偏置地址分配 + Q16.16 转换
├── CNNRISCVGenerator    ← 逐算子 RISC-V 机器码生成
└── RISCVEmitter         ← RV32IM 指令编码 + label fixup
```

## 组件详解

### ProtoReader
- 手工解析 protobuf wire format (varint, length-delimited fields)
- 不需要 `protobuf` 包 — Python stdlib only
- 从 ONNX 二进制文件中提取: graph nodes, initializers (权重/偏置), tensor shapes

### ONNXModel
```python
model = ONNXModel()
model.parse("models/graph/cnn.onnx")
# model.nodes     → [Conv, MaxPool, Conv, MaxPool, Conv, MaxPool, Gemm, Relu, Gemm]
# model.weights   → {"W1": np.array(...), "B1": np.array(...), ...}
# model.shapes    → {"X": (1,3,64,64), "W1": (32,3,3,3), ...}
```

### MemoryPlan
- 为每个权重/偏置/中间结果分配内存地址
- 将 float32 权重转换为 Q16.16 定点: `int(w * 65536.0) & 0xFFFFFFFF`
- 输出布局描述供循环生成器使用

### CNNRISCVGenerator

逐算子生成内联 RISC-V 机器码（无函数调用，全部内联循环）:

```python
class CNNRISCVGenerator:
    def generate_conv2d(node, memory_plan):
        # 生成 6 层嵌套循环的 RV32IM 机器码
        # 外三层: OH, OW, OC
        # 内三层: KH, KW, IC
        # 每轮: load + load + mul (Q16.16) + srai 16 + add (累加)
        # 权重预加载到寄存器, 内层循环复用
        ...

    def generate_gemm(node, memory_plan):
        # 3 层循环: I, J, K
        # 可选 transB (通过循环交换实现)
        ...

    def generate_maxpool(node, memory_plan):
        # 5 层循环 + padding 边界检查
        ...

    def generate_relu(node, memory_plan):
        # max(a0, zero) — 两条指令
        ...

    def generate_sigmoid(node, memory_plan):
        # 查表法 (256 个 Q16.16 条目) + 线性插值
        ...
```

### RISCVEmitter
- 将 RV32IM 汇编指令编码为 32-bit 机器码 (R/I/S/B/U/J 格式)
- 两遍扫描:
  1. **第一遍**: emit 所有指令, 记录 label 位置
  2. **第二遍**: 回填分支偏移量 (PC-relative fixup)
- 输出 flat binary, position-independent

## Q16.16 定点运算

```python
def float32_to_q16(value: float) -> int:
    return int(value * 65536.0) & 0xFFFFFFFF

# 乘法: MUL → 64-bit → SRAI 16
#  (a*2^16) * (b*2^16) = a*b*2^32, 右移16位 → a*b*2^16 (Q16.16)

# 加法: 直接 ADD (小数点已对齐)
```

## 命令行

```bash
# 基本编译
python scratchv/standalone/onnx_to_riscv_standalone.py models/graph/cnn.onnx -o output.bin

# 完整输出 + 估算
python scratchv/standalone/onnx_to_riscv_standalone.py models/graph/cnn.onnx \
    -o output.bin --asm output.s --estimate --report
```

## 性能估算 (--estimate)

编译器生成代码时同时统计:
- 静态指令数 (编译时)
- 动态指令数 (基于循环边界和 tensor 形状推导)
- 估算总执行时间 (给定假设的 RISC-V 频率)

## 相关 Topic

- Standalone LLVM 编译器 (`onnx_to_llvm_standalone.py`) — float32 路径
- Benchmark Engine — `standalone/benchmark.py` (执行 + 实测)
- LLVM vs ScratchV Cache Compare — 双路径对比
- [ARCHITECTURE.md](../ARCHITECTURE.md) — 完整管线图
