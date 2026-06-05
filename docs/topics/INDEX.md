# ScratchV Topic 索引 — 模块文档地图

> 按 Topic 编号组织的完整项目模块文档索引。每个 Topic 对应一组源文件。

---

## 前端 (Frontend)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 1 | DSL 前端增强器 | `frontend/dsl_extended.py` | [topic01_dsl_enhancer_guide.md](topic01_dsl_enhancer_guide.md) |
| 2 | ONNX 解析器 | `frontend/onnx_parser.py` | [frontend_onnx_parser.md](frontend_onnx_parser.md) |
| 9 | DSL 错误提示 | `frontend/dsl_errors.py` | [topic09_dsl_errors_guide.md](topic09_dsl_errors_guide.md) |

## 中间表示 (IR)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 3 | IR 系统 | `ir/types.py`, `ir/builder.py`, `ir/printer.py` | [ir_system.md](ir_system.md) |
| - | IR 验证器 | `analysis/ir_verifier.py` | [topic21_ir_verifier_guide.md](topic21_ir_verifier_guide.md) |

## 优化器 (Optimizer)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 4 | IR 优化器框架 | `optimizer/` (5 passes) | [optimizer_framework.md](optimizer_framework.md) |

## 后端 — RISC-V 代码生成 (Backend)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 8 | 指令选择 | `backend/instruction_select.py` | [backend_instruction_select.md](backend_instruction_select.md) |
| 28 | 扩展指令选择 | `backend/inst_select_ext.py` | [backend_inst_select_ext.md](backend_inst_select_ext.md) |
| 17 | 寄存器分配 (线性扫描) | `backend/regalloc_linear.py` | [backend_regalloc_linear.md](backend_regalloc_linear.md) |
| - | 寄存器分配 (naive/greedy) | `backend/register_alloc.py` | (见 instruction_select 管线) |
| - | 汇编发射 | `backend/asm_emit.py` | (见 ARCHITECTURE.md) |

## 后端 — 汇编后优化 (Post-codegen)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 5 | 汇编美化器 | `backend/asm_beautifier.py` | [backend_asm_beautifier.md](backend_asm_beautifier.md) |
| 12 | 指令计数统计器 | `backend/inst_counter.py` | [backend_inst_counter.md](backend_inst_counter.md) |
| 13 | 窥孔优化器 | `backend/asm_peephole.py` | [backend_asm_peephole.md](backend_asm_peephole.md) |
| 14 | 常量加载合并 | `backend/const_merge.py` | [backend_const_merge.md](backend_const_merge.md) |
| 18 | 指令调度器 | `backend/inst_scheduler.py` | [backend_inst_scheduler.md](backend_inst_scheduler.md) |
| - | 流水线周期估算 | `backend/cycle_estimator.py` | (见 ARCHITECTURE.md) |
| - | RISC-V 编码器 | `backend/riscv_encoder.py` | (见 ARCHITECTURE.md) |

## 后端 — LLVM 路径

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 16 | LLVM 代码生成后端 | `backend/llvm_codegen.py` | [backend_llvm_codegen.md](backend_llvm_codegen.md) |

## 独立工具 (Standalone)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 19 | Standalone RISC-V 编译器 | `standalone/onnx_to_riscv_standalone.py` | [standalone_riscv_compiler.md](standalone_riscv_compiler.md) |
| 22 | Standalone LLVM 编译器 | `standalone/onnx_to_llvm_standalone.py` | [standalone_llvm_compiler.md](standalone_llvm_compiler.md) |
| 6 | 性能基准套件 | `standalone/benchmark.py`, `benchmarks/` | [topic06_bench_suite_guide.md](topic06_bench_suite_guide.md) |
| 23 | Cache 模型 | `standalone/cache_model.py` | (见 ARCHITECTURE.md) |
| 24 | Spike 仿真 | `standalone/spike_sim.py`, `run_spike_bench.py` | (见 ARCHITECTURE.md) |
| 25 | LLVM vs ScratchV 对比 | `standalone/llvm_cache_compare.py` | (见 ARCHITECTURE.md) |
| 26 | TinyFive 对比 | `standalone/tinyfive_compare.py` | (见 ARCHITECTURE.md) |
| 27 | RV32 全量 Benchmark | `standalone/rv32_bench.py` | (见 ARCHITECTURE.md) |

## 分析 (Analysis)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 11 | CFG 构建器 | `analysis/cfg_builder.py` | [topic11_cfg_builder_guide.md](topic11_cfg_builder_guide.md) |
| 21 | IR 验证器 | `analysis/ir_verifier.py` | [topic21_ir_verifier_guide.md](topic21_ir_verifier_guide.md) |

## CI / Dashboard

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 30 | CI 基准编排 + Dashboard | `ci/ci_benchmark.py`, `ci/dashboard.py` | (见 ARCHITECTURE.md 第6节) |

## 基础设施 (Infrastructure)

| Topic | 模块 | 源文件 | 文档 |
|------|------|--------|------|
| 7 | 日志增强器 | `utils/logger.py` | [topic07_logger_guide.md](topic07_logger_guide.md) |
| 20 | 代码规范 | 项目级 | [topic20_code_standards_guide.md](topic20_code_standards_guide.md) |
| - | 编译器驱动 + PassManager | `compiler.py`, `pass_interface.py` | (见 ARCHITECTURE.md) |

---

## 文档索引

### 总文档
- **[ARCHITECTURE.md](../ARCHITECTURE.md)** — ONNX → RISC-V 双路径完整说明 (必读)

### 核心管线文档 (推荐阅读顺序)
1. [frontend_onnx_parser.md](frontend_onnx_parser.md) — ONNX 模型如何解析
2. [ir_system.md](ir_system.md) — IR 数据结构与构造
3. [optimizer_framework.md](optimizer_framework.md) — IR 层优化 pass
4. [backend_instruction_select.md](backend_instruction_select.md) — RISC-V 指令选择
5. [backend_llvm_codegen.md](backend_llvm_codegen.md) — LLVM IR 代码生成
6. [standalone_riscv_compiler.md](standalone_riscv_compiler.md) — 零依赖 RISC-V 编译器
7. [standalone_llvm_compiler.md](standalone_llvm_compiler.md) — LLVM IR 编译器 + JIT

### 所有 Topic 文档列表 (字母序)
- [backend_asm_beautifier.md](backend_asm_beautifier.md)
- [backend_asm_peephole.md](backend_asm_peephole.md)
- [backend_const_merge.md](backend_const_merge.md)
- [backend_inst_counter.md](backend_inst_counter.md)
- [backend_inst_scheduler.md](backend_inst_scheduler.md)
- [backend_inst_select_ext.md](backend_inst_select_ext.md)
- [backend_instruction_select.md](backend_instruction_select.md)
- [backend_llvm_codegen.md](backend_llvm_codegen.md)
- [backend_regalloc_linear.md](backend_regalloc_linear.md)
- [frontend_onnx_parser.md](frontend_onnx_parser.md)
- [ir_system.md](ir_system.md)
- [optimizer_framework.md](optimizer_framework.md)
- [standalone_llvm_compiler.md](standalone_llvm_compiler.md)
- [standalone_riscv_compiler.md](standalone_riscv_compiler.md)
- [topic01_dsl_enhancer_guide.md](topic01_dsl_enhancer_guide.md)
- [topic06_bench_suite_guide.md](topic06_bench_suite_guide.md)
- [topic07_logger_guide.md](topic07_logger_guide.md)
- [topic09_dsl_errors_guide.md](topic09_dsl_errors_guide.md)
- [topic11_cfg_builder_guide.md](topic11_cfg_builder_guide.md)
- [topic20_code_standards_guide.md](topic20_code_standards_guide.md)
- [topic21_ir_verifier_guide.md](topic21_ir_verifier_guide.md)
