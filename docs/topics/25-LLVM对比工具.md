# Topic 25 — LLVM vs ScratchV 缓存对比工具

> **难度**: 高级 | **源文件**: `scratchv/standalone/llvm_cache_compare.py`

---

## 是什么？

`llvm_cache_compare.py` 是 ScratchV 的**核心对比分析工具**——它对 LLVM 生成的 RV64FD 汇编和 ScratchV 生成的 RV32IM 汇编做**并排分析**，计算两者在动态指令数、缓存行为、访存模式上的差异。

因为无法在 Python 内运行完整的 RV64FD 仿真，它使用**分析估算法**：
1. 从 LLVM 汇编中提取内层循环体的静态指令
2. 基于 CNN 层维度计算动态执行次数
3. 将访存模式输入 cache 模型估算命中率
4. 生成并排对比表

---

## 为什么？

这是 ScratchV **最重要的性能分析工具**——它告诉你：
- ScratchV 和 LLVM 的**差距到底在哪里**（哪个算子？哪类指令？）
- 每次优化后的**实际效果**（量化对比）
- Cache 层面的**深层瓶颈**（不仅仅是指令数）

---

## 核心概念

### 分析流程

```
LLVM .s 汇编                    ScratchV .s 汇编
    │                                │
    ▼                                ▼
提取内层循环体指令              提取内层循环体指令
(Conv/Gemm/MaxPool)            (Conv/Gemm/MaxPool)
    │                                │
    ▼                                ▼
按 CNN 层维度 × 循环次数       按 CNN 层维度 × 循环次数
→ 动态指令数估算               → 动态指令数估算
    │                                │
    ▼                                ▼
Cache 模型 (I$/D$)             Cache 模型 (I$/D$)
    │                                │
    └──────────┬─────────────────────┘
               ▼
       并排对比表 + JSON 输出
```

### CNN 层维度计算

```python
def compute_layer_dims():
    layers = []
    # Conv1: 3→32, 3×3, stride=1, pad=0
    macs = 32 * 248 * 248 * 3 * 3 * 3  # ~110M
    layers.append(LayerDims("Conv1", macs, ...))
    # Conv2: 32→32, 3×3
    macs2 = 32 * 122 * 122 * 32 * 3 * 3  # ~74M
    layers.append(LayerDims("Conv2", macs2, ...))
    # ... 继续计算所有层 ...
    return layers
```

### 对比维度

| 维度 | LLVM (RV64FD) | ScratchV (RV32IM) |
|------|--------------|-------------------|
| 动态 ALU 指令 | fmul/fadd (~2/MAC) | MUL+SRAI+ADD (~12/MAC) |
| 动态 Load/Store | 较少（寄存器多） | 较多（寄存器压力大） |
| 地址计算 | GEP（1条） | MUL+ADD 链（~5条） |
| I$ 行为 | 较好（指令紧凑） | 较差（指令多） |
| D$ 行为 | 接近 | 接近（数据访问模式相同） |

---

## 一步步

### 运行对比

```bash
# 生成 JSON 对比数据
python scratchv/standalone/llvm_cache_compare.py \
    --json-output output/llvm_vs_scratchv.json

# 同时生成 Markdown 报告
python scratchv/standalone/llvm_cache_compare.py \
    --json-output output/llvm_vs_scratchv.json \
    --markdown output/llvm_vs_scratchv.md
```

### 查看结果

```python
import json
with open("output/llvm_vs_scratchv.json") as f:
    data = json.load(f)

for key in data:
    print(f"{key}: {data[key]}")
```

典型输出：
```json
{
  "llvm_static_insns": 1102,
  "scratchv_static_insns": 749,
  "llvm_dynamic_insns": 1060000000,
  "scratchv_dynamic_insns": 3220000000,
  "ratio": 3.04,
  "llvm_dcache_hit_rate": 88.75,
  "scratchv_dcache_hit_rate": 88.75
}
```

### 在 CI 中使用

```bash
make bench-ci    # 自动调用 llvm_cache_compare.py → dashboard.py
```

---

## 代码走读

### 内层循环指令提取

```python
def extract_inner_loop(asm_text, op_name):
    """从汇编中识别并提取指定算子的最内层循环指令"""
    # 1. 找到算子标签（如 "conv2d_loop_ic:"）
    # 2. 提取标签到跳转之间的所有指令
    # 3. 分类每条指令（ALU/MEM/BRANCH/FP）
    # 4. 返回指令列表和分类统计
    inner_loop = []
    in_loop = False
    for line in asm_text.split("\n"):
        if f"{op_name}_loop_ic:" in line:
            in_loop = True
            continue
        if in_loop:
            if line.strip().startswith("j ") or line.strip().startswith("bne "):
                break  # 循环结束
            inner_loop.append(parse_instruction(line))
    return inner_loop
```

### 动态指令数估算

```python
def estimate_dynamic(inner_loop_insns, layer_dims):
    """内层循环指令数 × 循环迭代次数 = 动态指令数"""
    total = 0
    for layer in layer_dims:
        if layer.name.startswith("Conv"):
            # 内层循环迭代次数 = OH × OW × OC × KH × KW × IC
            iterations = layer.h_out * layer.w_out * ...
            total += len(inner_loop_insns) * iterations
    return total
```

---

## 动手练习

### 练习 1: 运行对比

运行 `llvm_cache_compare.py`，查看 JSON 输出，找出差距最大的指令类别。

### 练习 2: 添加新的对比维度

在对比脚本中添加"每 MAC 的 Load 指令数"指标，比较两种路径的数据复用效率。

### 练习 3: 对比不同模型

如果有多个 ONNX 模型（不同大小/层数），分别运行对比，看差距是否随模型规模变化。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **LLVM 汇编依赖** | 需要先生成 LLVM 汇编（通过 `llc`），如果没安装 LLVM 工具链则无法对比 |
| **内层循环识别** | 依赖汇编中的特定标签命名（如 `conv2d_loop_ic`），如果代码生成器改了标签名，提取会失败 |
| **Cache 模型参数** | 确保两边的 cache 参数一致（I$ 64:2:32, D$ 128:4:32），否则对比无意义 |

---

## 进阶阅读

- [03-指标解读指南](../03-指标解读指南.md) — 如何解读对比数据
- [ARCHITECTURE.md](../ARCHITECTURE.md) — 双路径对比详解
- 相关 topic: [Topic 23 — Cache 模型](23-Cache模型.md) | [Topic 30 — CI Dashboard](30-CI-Dashboard.md)
