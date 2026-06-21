# Topic 27 — RV32 全量 Benchmark

> **难度**: 中级 | **源文件**: `scratchv/standalone/rv32_bench.py`

---

## 是什么？

RV32 全量 Benchmark（`rv32_bench.py`）将 ScratchV 和 LLVM **统一到 RV32IMF 目标**进行公平对比。流程：

```
ONNX 模型
    │
    ├─→ ScratchV: RV32IM Q16.16 定点 .bin → TinyFive 仿真 → ops 统计
    │
    └─→ LLVM: LLVM IR → llvmlite → RV32IMF float32 .s → TinyFive 仿真 → ops 统计
                                                                          │
                                                          ┌───────────────┘
                                                          ▼
                                                   并排对比报告
```

与 `llvm_cache_compare.py` 的不同：这里**两边都通过 TinyFive 真实执行**，零分析估算——所有指标都来自 TinyFive 的 ops 计数器。

---

## 为什么？

- **公平对比**：之前的对比是 "RV32IM Q16.16 vs RV64FD float32"——ISA 不同、数值格式不同。这里统一到**同一个 RV32IMF 目标**
- **零估算**：所有指标来自 TinyFive 真实仿真，不是分析公式
- **发现真实差距**：消除 ISA 差异后，ScratchV 和 LLVM 的差距到底有多大？

---

## 核心概念

### 四步流水线

| 步骤 | ScratchV 路径 | LLVM 路径 |
|------|-------------|----------|
| 1. 编译 | `onnx_to_riscv_standalone.py` → RV32IM .bin | `onnx_to_llvm_standalone.py` → LLVM IR |
| 2. 后端 | 直接输出（已经是 RV32IM） | `llvmlite` → RV32IMF .s |
| 3. 仿真 | TinyFive ProfiledMachine | TinyFive ProfiledMachine |
| 4. 统计 | TinyFive ops 计数器 | TinyFive ops 计数器 |

### TinyFive ops 计数器

TinyFive 的 `ProfiledMachine` 提供精确的指令分类：
- `total`: 总执行指令数
- `load`: 内存读次数
- `store`: 内存写次数
- `mul`: 乘法指令次数
- `add`: 加法/ALU 指令次数
- `madd`: 融合乘加次数（RV32IMF 的 `fmadd.s`）
- `branch`: 分支/跳转次数

### 统一对比的意义

在相同 ISA 下对比，差距主要来自：
1. **数值格式**：Q16.16 定点 vs float32（~12 vs ~2 指令/MAC）
2. **代码生成质量**：手工内联循环 vs LLVM 的循环结构
3. **地址计算**：手动 MUL+ADD vs GEP

---

## 一步步

```bash
# 运行全量 RV32 Benchmark
python scratchv/standalone/rv32_bench.py models/graph/cnn.onnx \
    --output-dir benchmark_reports/ \
    --html report.html \
    --json report.json

# 查看报告
cat benchmark_reports/report.json | python -m json.tool | head -50
```

### Python API

```python
from scratchv.standalone.rv32_bench import compile_scratchv, compile_llvm_rv32

# 编译 ScratchV
scratchv_result = compile_scratchv(
    "models/graph/cnn.onnx",
    output_bin="/tmp/scratchv.bin",
    output_asm="/tmp/scratchv.s",
)

# 编译 LLVM（目标 RV32IMF）
llvm_result = compile_llvm_rv32(
    "models/graph/cnn.onnx",
    output_asm="/tmp/llvm_rv32.s",
)

print(f"ScratchV: {scratchv_result['static_insns']} static insns")
print(f"LLVM RV32: {llvm_result['static_insns']} static insns")
```

---

## 代码走读

### ScratchV 编译

```python
def compile_scratchv(onnx_path, output_bin, output_asm):
    rc, stdout, stderr = _run_py([
        "scratchv/standalone/onnx_to_riscv_standalone.py",
        onnx_path, "-o", output_bin, "--asm", output_asm,
    ], timeout=120)
    code_size = len(Path(output_bin).read_bytes())
    # 统计静态指令数
    static_insns = 0
    for line in Path(output_asm).read_text().splitlines():
        parts = line.split('#')[0].strip().split()
        if parts and parts[0] not in ('', '.text', '.align', ...):
            static_insns += 1
    return {"code_size": code_size, "static_insns": static_insns, ...}
```

### LLVM RV32IMF 编译（通过 llvmlite）

```python
def compile_llvm_rv32(onnx_path, output_asm):
    # 1. 生成 LLVM IR
    _run_py(["scratchv/standalone/onnx_to_llvm_standalone.py",
             onnx_path, "-o", "/tmp/_cnn.ll", "--opt-level", "2"])

    # 2. llvmlite: IR → RV32IMF 机器码
    from llvmlite import binding
    binding.initialize_all_targets()
    llmod = binding.parse_assembly(Path("/tmp/_cnn.ll").read_text())
    llmod.verify()

    # 3. 设置 target = RV32IMF
    target = binding.Target.from_triple("riscv32-unknown-elf")
    target_machine = target.create_target_machine(
        cpu="generic-rv32", features="+m,+f", ...
    )
    asm = target_machine.emit_assembly(llmod)
    return {"static_insns": count_insns(asm), ...}
```

---

## 动手练习

### 练习 1: 运行统一对比

运行 `rv32_bench.py`，对比同一 ISA 下 ScratchV 和 LLVM 的指令数差距。

### 练习 2: 分析差距来源

从 TinyFive ops 统计中找出 ScratchV 的 `mul`/`add`/`load` 分别比 LLVM 多多少，定位最大瓶颈。

### 练习 3: 调整 LLVM 优化级别

把 `--opt-level` 从 2 改为 0 和 3，对比不同优化级别下 LLVM 的指令数变化。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **llvmlite 版本** | 需要支持 RV32 目标，某些旧版本只支持 RV64 |
| **TinyFive 性能** | 全模型仿真（~30 亿指令）在 TinyFive 上不可行，需要用 `--max-instr` 限制或只仿真内层循环 |
| **LLVM IR → RV32 的兼容性** | 手工写的 LLVM IR 可能有 RV64 特定的假设（如 pointer 大小），改为 RV32 可能需要调整 |

---

## 进阶阅读

- [ARCHITECTURE.md](../ARCHITECTURE.md) — 双路径架构
- [llvmlite 文档](https://llvmlite.readthedocs.io/)
- 相关 topic: [Topic 25 — LLVM 对比工具](25-LLVM对比工具.md) | [Topic 26 — TinyFive 对比](26-TinyFive对比.md) | [Topic 19 — Standalone RISC-V](19-Standalone-RISC-V编译器.md)
