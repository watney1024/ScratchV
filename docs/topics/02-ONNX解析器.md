# Topic 02 — ONNX 模型解析器

> **难度**: 中级 | **源文件**: `scratchv/frontend/onnx_parser.py`

---

## 是什么？

ONNX 解析器将 `.onnx` 模型文件（protobuf 二进制格式）解析为 ScratchV 的内部 IR。支持 15 种 ONNX 算子：Conv、Gemm、MatMul、MaxPool、ReLU、Sigmoid、Softmax 等。

```
.onnx 文件 (protobuf 二进制)
        │
   ONNXParser (onnx.load)
        │
        ▼
   IR Program (Function → BasicBlock → Instruction)
```

---

## 为什么？

- ONNX 是 AI 模型的标准交换格式，PyTorch/TensorFlow/Keras 都能导出
- 解析器的存在让 ScratchV 能**编译真实的训练好的模型**，而不只是手写 DSL 程序
- 两条路径共享解析逻辑：库路径（用 `onnx` 包）和 Standalone 路径（手工 protobuf 解析）

---

## 核心概念

### 1. ONNX 模型结构

```
ModelProto
  └── GraphProto
        ├── input[]      ← 模型输入（名称、形状、类型）
        ├── initializer[] ← 权重/偏置（常量 tensor）
        ├── output[]     ← 模型输出
        └── node[]       ← 计算节点列表
              ├── op_type      ← 算子类型: "Conv", "ReLU", ...
              ├── input[]      ← 输入名称: ["X", "W", "B"]
              ├── output[]     ← 输出名称: ["Y"]
              └── attribute[]  ← 属性: kernel_shape, strides, pads
```

### 2. 15 种已支持的 ONNX 算子

| 类别 | 算子 | ONNX Op | IR OpCode |
|------|------|---------|-----------|
| 算术 | Add, Sub, Mul, Div | `Add`, `Sub`, `Mul`, `Div` | `ADD`, `SUB`, `MUL`, `DIV` |
| 激活 | ReLU, GELU, Sigmoid | `Relu`, `Gelu`, `Sigmoid` | `RELU`, `GELU`, `SIGMOID` |
| 归一化 | Softmax | `Softmax` | `SOFTMAX` |
| 池化 | MaxPool | `MaxPool` | `MAXPOOL` |
| 卷积 | Conv | `Conv` | `CONV` |
| 全连接 | Gemm, MatMul | `Gemm`, `MatMul` | `GEMM`, `MATMUL` |
| 形状 | Reshape | `Reshape` | `RESHAPE` |
| 一元 | Neg, Exp | `Neg`, `Exp` | `NEG`, `EXP` |

### 3. 两条路径对比

| | 库路径 (`onnx_parser.py`) | Standalone 路径 |
|------|--------------------------|----------------|
| 依赖 | `onnx` 包 | 零依赖 (手工 protobuf) |
| 输出 | IR Program | ONNXModel → 直接机器码 |
| 精度 | 跟随 ONNX（float32 等） | Q16.16 定点 |
| 用途 | 主管线编译 | 零依赖独立编译 |

---

## 一步步

### Step 1: 加载并查看 ONNX 模型

```python
import onnx

model = onnx.load("models/graph/cnn.onnx")
graph = model.graph

print(f"Inputs: {[i.name for i in graph.input]}")
print(f"Nodes: {[(n.op_type, n.name) for n in graph.node]}")
```

### Step 2: 用 ScratchV 解析器解析

```python
from scratchv.frontend.onnx_parser import ONNXParser

parser = ONNXParser()
program = parser.parse("models/graph/cnn.onnx")

print(f"Functions: {len(program.functions)}")
for func in program.functions:
    print(f"  {func.name}: {len(func.basic_blocks)} blocks, "
          f"{sum(len(b.instructions) for b in func.basic_blocks)} instrs")
```

### Step 3: 查看解析出的权重

```python
# 在 standalone 路径中使用 ONNXModel
from scratchv.standalone.onnx_to_riscv_standalone import ONNXModel

model = ONNXModel()
model.parse("models/graph/cnn.onnx")
for name, weight in model.weights.items():
    print(f"{name}: shape={weight.shape}, dtype={weight.dtype}")
```

---

## 代码走读

### ONNXParser 核心流程

```python
class ONNXParser:
    def parse(self, filepath: str) -> Program:
        model = onnx.load(filepath)
        graph = model.graph

        program = Program()
        func = Function(name="main")

        # 1. 注册所有权重/常量
        self._register_initializers(graph.initializer)

        # 2. 逐节点解析
        for node in graph.node:
            handler = self._HANDLERS.get(node.op_type)
            if handler is None:
                raise NotImplementedError(
                    f"Unsupported ONNX op: {node.op_type}"
                )
            instrs = handler(self, node)
            for instr in instrs:
                self.builder.add_instruction(instr)

        func.basic_blocks.append(self.builder.current_block)
        program.functions.append(func)
        return program
```

### 算子处理示例：Conv

```python
def _handle_conv(self, node):
    """Conv 节点 → CONV IR 指令"""
    # 提取属性
    kernel_shape = self._get_attr(node, "kernel_shape")
    strides = self._get_attr(node, "strides", [1, 1])
    pads = self._get_attr(node, "pads", [0, 0, 0, 0])

    # 创建 IR 指令
    instr = Instruction(
        dest=self._make_value(node.output[0]),
        op=OpCode.CONV,
        operands=[
            self._get_value(node.input[0]),   # 输入
            self._get_value(node.input[1]),   # 权重
            self._get_value(node.input[2]),   # 偏置
        ],
        attrs={
            "kernel_shape": kernel_shape,
            "strides": strides,
            "pads": pads,
        },
    )
    return [instr]
```

### 关键细节：属性提取

ONNX 的属性有类型——可能是 `int`、`ints`（整数列表）、`float` 等：
```python
def _get_attr(self, node, name, default=None):
    for attr in node.attribute:
        if attr.name == name:
            if attr.type == onnx.AttributeProto.INTS:
                return list(attr.ints)
            elif attr.type == onnx.AttributeProto.INT:
                return attr.i
            elif attr.type == onnx.AttributeProto.FLOAT:
                return attr.f
    return default
```

---

## 动手练习

### 练习 1: 添加新算子的支持

在 `onnx_parser.py` 中添加 `Tanh` 算子的处理。ONNX 定义 `Tanh` 输入一个 tensor，输出一个 tensor（逐元素 tanh）。

### 练习 2: 可视化 ONNX 模型图

用 [Netron](https://netron.app) 打开 `models/graph/cnn.onnx`，对照解析器的输出，理解模型的拓扑结构。

### 练习 3: 对比解析前后的权重

用 `onnxruntime` 直接推理模型，和 ScratchV 编译后的结果对比，验证解析的正确性。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **ONNX opset 版本** | 不同 opset 版本的算子属性可能不同，注意兼容性 |
| **属性类型多态** | ONNX 属性可能是 int/ints/float/floats/string，需要分别处理 |
| **initializer vs input** | 权重在 `initializer` 中（常量），输入在 `input` 中（变量），不要混淆 |
| **不支持的操作** | 遇到不支持的算子会抛 `NotImplementedError`，需要手动添加 handler |

---

## 进阶阅读

- [ONNX 算子规范](https://github.com/onnx/onnx/blob/main/docs/Operators.md) — 所有标准算子的定义
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Standalone 路径的 ONNXModel 手工 protobuf 解析原理
- 相关 topic: [Topic 01 — DSL 前端增强器](01-DSL前端增强器.md) | [Topic 08 — 指令选择](08-指令选择.md) | [Topic 19 — Standalone RISC-V 编译器](19-Standalone-RISC-V编译器.md)
