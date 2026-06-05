# Topic: 中间表示系统 (IR System)

> **源文件**: `scratchv/ir/types.py`, `scratchv/ir/builder.py`, `scratchv/ir/printer.py`
> **依赖**: 无
> **层级**: 整个编译器的核心数据结构

---

## 概述

ScratchV 使用自定义的三地址码 IR，介于 ONNX/DSL 前端与 RISC-V/LLVM 后端之间。所有前端产出 IR，所有优化在 IR 层面执行，所有后端消费 IR。

## IR 层次结构

```
Program                          ← 顶层: 整个程序
  └── Function[]                 ← 函数列表 (每个 ONNX 算子对应一个 function)
        └── BasicBlock[]         ← 基本块列表 (CFG 节点)
              └── Instruction[]  ← 指令列表 (三地址码)
                    ├── dest: Value    (目标操作数, SSA)
                    ├── op: OpCode     (操作码)
                    └── operands: Value[]  (源操作数)
```

## 核心类型

### OpCode (36 种操作码)

| 类别 | 操作码 |
|------|--------|
| **算术** | `ADD`, `SUB`, `MUL`, `DIV`, `NEG`, `EXP` |
| **访存** | `LOAD`, `STORE`, `LOAD_CONST`, `ALLOCA` |
| **控制流** | `FOR`, `ENDFOR`, `BR`, `BR_IF`, `LABEL`, `RETURN` |
| **神经网络** | `MATMUL`, `RELU`, `MAXPOOL`, `SOFTMAX`, `GELU`, `DOT`, `CONV`, `GEMM`, `SIGMOID` |
| **形状** | `TRANSPOSE`, `RESHAPE`, `CONCAT` |

### Value (SSA 值)

```python
@dataclass
class Value:
    name: str           # SSA 名称, 如 "%1", "%conv_result"
    dtype: DataType     # FLOAT32, INT32, FLOAT64, INT64
    constant: bool      # 是否为编译时常量
    const_value: Any    # 常量值 (如 3.14)
    shape: tuple        # Tensor 形状 (如 [1, 32, 64, 64])
```

### Instruction (三地址码指令)

```python
@dataclass
class Instruction:
    opcode: OpCode         # 操作码
    dest: Optional[Value]  # 目标操作数 (可能为 None, 如 BR)
    operands: list[Value]  # 源操作数列表
    attrs: dict            # 额外属性 (如 Conv 的 kernel_shape)
    target: Optional[str]  # 分支目标 (BR/BR_IF 使用)
```

### BasicBlock (基本块)

```python
@dataclass
class BasicBlock:
    name: str                # 块标签, 如 "entry", "loop_body"
    instructions: list[Instruction]
    # 必须满足: 除最后一条外, 不允许有控制流指令
    # 最后一条必须是 RETURN, BR, 或 BR_IF
```

### Function

```python
@dataclass
class Function:
    name: str
    params: list[Value]     # 函数参数
    returns: list[Value]    # 返回值
    blocks: list[BasicBlock]
    locals: list[Value]     # 局部变量
```

## IRBuilder (三地址码构造器)

提供类型安全的方法构造 IR 指令:

```python
builder = IRBuilder()
builder.start_function("main")
builder.start_block("entry")

# 算术运算
v1 = builder.add(v_a, v_b)      # %1 = add %a, %b
v2 = builder.mul(v1, v_c)       # %2 = mul %1, %c
v3 = builder.relu(v2)           # %3 = relu %2

# 控制流
builder.start_block("loop")
builder.for_loop("i", 0, 10)    # for i in range(10):
builder.add(x, y)               #   body
builder.endfor()                # endfor

# 分支
builder.br_if(v_cmp, "true_bb", "false_bb")

program = builder.finish()
```

## IRPrinter (文本输出)

将 IR Program 输出为可读文本:

```
function main:
  entry:
    %1 = load_const 3.140000
    %2 = alloca [1, 32, 64, 64]
    %3 = conv %2, %1, kernel_shape=[3,3]
    ...
```

## 设计要点

1. **三地址码形式**: 每条指令最多 2 个源操作数 + 1 个目标操作数，简化后端代码生成
2. **SSA 风格**: 每个 Value 只赋值一次，便于优化 pass 编写
3. **显式控制流**: FOR/ENDFOR/BR/BR_IF 而非隐式 CFG，IR 文本可直接阅读
4. **NN 算子为一级操作码**: Conv/Gemm/MaxPool 等不作为库调用，而是 IR 原生指令 → 后端可跨算子优化

## 相关 Topic

- Topic 4: 优化器框架 → 所有优化 pass 操作 IR
- Topic 21: IR 验证器 → 验证 IR 正确性
- [ARCHITECTURE.md](../ARCHITECTURE.md) — 完整管线
