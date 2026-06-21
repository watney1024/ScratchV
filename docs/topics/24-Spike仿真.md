# Topic 24 — Spike 仿真集成

> **难度**: 高级 | **源文件**: `scratchv/standalone/spike_sim.py`

---

## 是什么？

Spike 仿真器集成将 ScratchV 编译出的 RV32IM flat binary 包装为最小 ELF32 格式，交给 **Spike**（RISC-V 官方黄金参考仿真器）执行，收集精确的动态指令数、I$/D$ 缓存命中率和指令热点。

```
output.bin (flat binary)
    │
    ▼
spike_sim.py  ← 包装为 ELF32 + 设置栈/堆/输入输出buffer
    │
    ▼
Spike (外部 C++ 仿真器, ~100-500 KIPS)
    │
    ▼
spike-log-parser  ← 解析提交指令日志
    │
    ▼
动态指令数 + I$/D$ stats + PC 热点 + 指令trace
```

---

## 为什么？

ScratchV 内置的估算器（`--estimate`）是**分析估算**——用 `CONV_INSNS_PER_MAC=12` 乘以 MAC 数，速度快但不精确。TinyFive 仿真器是**逐条仿真**但很慢（~1 KIPS）。

Spike 是**工业级 RISC-V 黄金参考模型**——结果权威、速度快 100-500 倍、自带 cache 模拟和指令日志。

---

## 核心概念

### ELF32 包装

ScratchV 输出是 flat binary（position-independent，无 header）。Spike 需要 ELF 格式。`spike_sim.py` 手工构造最小 ELF32：

```python
ELF_BASE = 0x80000000       # RISC-V DRAM 基地址
STACK_TOP = 0x85000000      # 栈顶（80MB）
INPUT_BUF  = 0x86000000     # a0 = 输入 buffer
OUTPUT_BUF = 0x87000000     # a1 = 输出 buffer
```

构造过程：手工编码 5 条启动指令（LUI + JAL）→ 拼接 ScratchV 代码 → 写 ELF header。

### Spike Cache 配置

```bash
# I-cache: 64 组, 2 路, 32B/块
# D-cache: 128 组, 4 路, 32B/块
--ic 64:2:32 --dc 128:4:32
```

与 `cache_model.py` 使用相同的参数，确保结果可比。

### 收集的指标

| 指标 | 来源 | 精度 |
|------|------|------|
| 动态指令数（提交） | Spike commit log | 精确 |
| 指令分类统计 | spike-dasm + 分类器 | 精确 |
| I$ 命中率 | Spike cache stats | 精确 |
| D$ 命中率 | Spike cache stats | 精确 |
| PC 热点 | 指令 trace 聚合 | 采样 |
| 执行时间 | Spike wall time | 参考 |

---

## 一步步

```bash
# 1. 编译 ScratchV binary
python scratchv/standalone/onnx_to_riscv_standalone.py models/graph/cnn.onnx \
    -o output.bin --asm output.s

# 2. 用 Spike 仿真（限制 5000 万指令）
python scratchv/standalone/spike_sim.py \
    --binary output.bin --code-size 3140 \
    --max-instr 50000000 \
    --ic 64:2:32 --dc 128:4:32
```

---

## 代码走读

### 最小 ELF32 构造

```python
def build_minimal_elf32(code: bytes) -> bytes:
    """手工构造包含启动代码 + ScratchV 代码的最小 ELF32"""
    # 启动代码（5 条指令）:
    startup = [
        rv_lui(2, 0x85000),   # sp = 0x85000000（栈顶）
        rv_lui(10, 0x86000),  # a0 = input buffer
        rv_lui(11, 0x87000),  # a1 = output buffer
        rv_jal(0, 5 * 4),     # 跳转到 ScratchV 代码（跳过启动）
        rv_ecall(),           # 程序退出
    ]
    payload = encode_instructions(startup) + code

    # 构造 ELF header + program header + section headers
    return build_elf(payload, entry=ELF_BASE, load_addr=ELF_BASE)
```

### Spike 调用

```python
def run_spike(elf_path, max_instr, ic_config, dc_config):
    cmd = [
        SPIKE,
        f"--ic={ic_config}",
        f"--dc={dc_config}",
        f"-m{max_instr}",
        "--log-commits",
        "--log-cache",
        elf_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return parse_spike_output(result.stdout, result.stderr)
```

---

## 动手练习

### 练习 1: 对比 Spike vs 估算

对同一个 CNN 模型，分别用 `--estimate`（分析估算）和 Spike 仿真（真实执行）统计动态指令数，对比差异。

### 练习 2: 调整 cache 参数

把 D-cache 从 `128:4:32` 改为 `256:8:64`，重新仿真，观察命中率变化。

### 练习 3: 分析 PC 热点

从 Spike 的指令 trace 中提取 PC 热点，确认 >99% 执行时间确实在 Conv2D 最内层循环。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **Spike 二进制路径** | 当前硬编码为 `/home/kinsomwang/workspace/coralnpu-spike-rv32/bin/spike`，需要自己编译 Spike RV32 版本 |
| **内存限制** | Spike 默认内存模型可能不够大，CNN 模型需要 `-m512`（512MB） |
| **执行时间** | 全量 CNN（32 亿指令）在 Spike 上可能跑数小时，用 `--max-instr` 限制 |
| **ELF 兼容性** | 最小 ELF32 只包含必要 header，某些 Spike 版本可能要求更完整的 ELF |

---

## 进阶阅读

- [Spike RISC-V ISA Simulator](https://github.com/riscv-software-src/riscv-isa-sim)
- ELF 格式规范: `man 5 elf`
- 相关 topic: [Topic 23 — Cache 模型](23-Cache模型.md) | [Topic 19 — Standalone RISC-V](19-Standalone-RISC-V编译器.md)
