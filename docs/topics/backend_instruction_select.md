# Topic: 后端指令选择 (Backend Instruction Selection)

> **源文件**: `scratchv/backend/instruction_select.py`, `scratchv/backend/inst_select_ext.py`
> **输入**: IR `Program`
> **输出**: `MachineInstruction` 列表 (虚拟寄存器)

---

## 概述

指令选择器将平台无关的 IR 指令转换为 RISC-V 特定的 `MachineInstr`。每个 IR 操作码有 `_select_*()` 方法。

## 映射表

| IR OpCode | RISC-V MachineOp | 映射 |
|-----------|-----------------|------|
| `ADD`, `SUB`, `MUL`, `DIV` | `ADD`, `SUB`, `MUL`, `DIV` | 1:1 |
| `RELU` | `MAX rd, rs, x0` | 降级 |
| `GELU` | 内联多项式序列 (~8 条) | 降级 |
| `SIGMOID` | 查表法 + 线性插值 | 降级 |
| `SOFTMAX` | identity passthrough (占位) | 待完善 |
| `CONV` | 6 层嵌套循环 | 降级 |
| `GEMM` | 3 层循环 + transB | 降级 |
| `MAXPOOL` | 5 层循环 + 边界检查 | 降级 |
| `MATMUL` | 2 层循环 + 点积 | 降级 |
| `BR` | `J target` | 1:1 |
| `BR_IF cond,t,f` | `BNEZ cond, t` + `J f` | 展开 |
| `LABEL` | `name:` | 1:1 |
| `RETURN` | `JALR x0, ra, 0` (ret) | 降级 |

## ExtendedInstructionSelector (`inst_select_ext.py`)

扩展支持: `FSQRT`, `FMIN`, `FMAX`, `FABS` (F/D extension), `DIV`, `REM`

## 管线位置

```
IR Program → [InstructionSelector] → MachineInstr[] (vregs)
               → [RegisterAllocator] → MachineInstr[] (phys regs)
                 → [AsmEmitter] → RISC-V assembly text
```

## 相关 Topic

- Topic 28: 完善后端指令选择 (`inst_select_ext.py`)
- Topic 17: 寄存器分配 — 线性扫描 (`regalloc_linear.py`)
- `machine_types.py` — 所有 RISC-V MachineOp 定义
