# ScratchV Topic 索引 — 30 个模块文档地图

> 🔰 **新手？** 先看总文档：[00-环境搭建指南](../00-环境搭建指南.md) → [01-编译器概念入门](../01-编译器概念入门.md) → [02-快速上手教程](../02-快速上手教程.md)
>
> 📊 **指标不懂？** [03-指标解读指南](../03-指标解读指南.md)
>
> 🐛 **报错了？** [04-故障排除FAQ](../04-故障排除FAQ.md)

---

## 文档状态说明

| 标记 | 含义 |
|------|------|
| ✅ | 新版中文文档已完成 |
| 📄 | 旧版英文文档可用（待重写） |
| ⬜ | 尚未编写 |

---

## 入门级（7 个）— 从这里开始

| 编号 | 模块 | 难度 | 状态 |
|------|------|------|------|
| [05](05-汇编代码美化器.md) | RISC-V 汇编代码美化器 | 入门 | ✅ |
| [07](07-编译器日志增强器.md) | 编译器日志增强器 | 入门 | ✅ |
| [09](09-DSL错误提示美化器.md) | DSL 错误提示美化器 | 入门 | ✅ |
| [11](11-控制流图生成器.md) | 控制流图（CFG）生成器 | 入门 | ✅ |
| [12](12-指令计数统计器.md) | RISC-V 后端指令计数统计器 | 入门 | ✅ |
| [13](13-窥孔优化器.md) | 窥孔优化器 | 入门 | ✅ |
| [18](18-指令调度器.md) | 指令调度（基本块内列表调度） | 入门 | ✅ |

---

## 中级（14 个）— 核心管线

| 编号 | 模块 | 难度 | 状态 |
|------|------|------|------|
| [01](01-DSL前端增强器.md) | DSL 前端增强器（if/while） | 中级 | ✅ |
| [02](02-ONNX解析器.md) | ONNX 解析器 | 中级 | ✅ |
| [03](03-IR系统.md) | 中间表示系统 (IR) | 中级 | ✅ |
| [04](04-IR优化器框架.md) | IR 优化器框架 | 中级 | ✅ |
| [06](archive/topic06_bench_suite_guide.md) | 编译器性能测试套件 | 中级 | 📄 |
| [08](08-指令选择.md) | 后端指令选择 | 中级 | ✅ |
| 10 | （预留） | — | ⬜ |
| [14](backend_const_merge.md) | 常量加载合并优化 | 中级 | 📄 |
| 15 | （预留） | — | ⬜ |
| [16](16-LLVM代码生成.md) | LLVM 代码生成后端 | 中级 | ✅ |
| [17](17-寄存器分配.md) | 寄存器分配（线性扫描） | 中级 | ✅ |
| [19](19-Standalone-RISC-V编译器.md) | Standalone RISC-V 编译器 | 中级 | ✅ |
| [20](archive/topic20_code_standards_guide.md) | 项目代码规范与格式化 | 中级 | 📄 |
| 27 | RV32 全量 Benchmark | — | ⬜ |

---

## 高级（9 个）— 深入优化

| 编号 | 模块 | 难度 | 状态 |
|------|------|------|------|
| [21](archive/topic21_ir_verifier_guide.md) | IR 验证器 | 高级 | 📄 |
| [22](standalone_llvm_compiler.md) | Standalone LLVM 编译器 | 高级 | 📄 |
| 23 | Cache 模型 | 高级 | ⬜ |
| 24 | Spike 仿真集成 | 高级 | ⬜ |
| 25 | LLVM vs ScratchV 对比工具 | 高级 | ⬜ |
| 26 | TinyFive 对比工具 | 高级 | ⬜ |
| [28](backend_inst_select_ext.md) | 完善后端指令选择（扩展） | 高级 | 📄 |
| 29 | （预留） | — | ⬜ |
| 30 | CI 基准编排 + Dashboard | 高级 | ⬜ |

---

## 其他模块文档（英文，待迁移）

这些是旧版英文模块文档，内容完整但不符合新模板格式。后续将逐步迁移为统一格式的中文文档。

| 文件 | 说明 |
|------|------|
| [frontend_onnx_parser.md](archive/frontend_onnx_parser.md) | ONNX 解析器（旧版）→ 新版见 [02](02-ONNX解析器.md) |
| [ir_system.md](ir_system.md) | IR 系统（旧版）→ 新版见 [03-IR系统.md](03-IR系统.md) |
| [optimizer_framework.md](archive/optimizer_framework.md) | 优化器框架（旧版）→ 新版见 [04](04-IR优化器框架.md) |
| [backend_instruction_select.md](backend_instruction_select.md) | 指令选择（旧版）→ 新版见 [08-指令选择.md](08-指令选择.md) |
| [backend_inst_select_ext.md](backend_inst_select_ext.md) | 扩展指令选择（F/D） |
| [backend_regalloc_linear.md](archive/backend_regalloc_linear.md) | 寄存器分配（旧版）→ 新版见 [17](17-寄存器分配.md) |
| [backend_llvm_codegen.md](archive/backend_llvm_codegen.md) | LLVM IR 代码生成（旧版）→ 新版见 [16](16-LLVM代码生成.md) |
| [backend_asm_beautifier.md](backend_asm_beautifier.md) | 汇编美化器（旧版）→ 新版见 [05](05-汇编代码美化器.md) |
| [backend_asm_peephole.md](backend_asm_peephole.md) | 窥孔优化（旧版）→ 新版见 [13](13-窥孔优化器.md) |
| [backend_inst_counter.md](backend_inst_counter.md) | 指令计数（旧版）→ 新版见 [12](12-指令计数统计器.md) |
| [backend_inst_scheduler.md](backend_inst_scheduler.md) | 指令调度（旧版）→ 新版见 [18](18-指令调度器.md) |
| [backend_const_merge.md](backend_const_merge.md) | 常量加载合并 |
| [standalone_riscv_compiler.md](standalone_riscv_compiler.md) | Standalone RISC-V（旧版）→ 新版见 [19](19-Standalone-RISC-V编译器.md) |
| [standalone_llvm_compiler.md](standalone_llvm_compiler.md) | Standalone LLVM 编译器 |

---

## 归档文件

旧的课题提案和英文 guide 已归档到 [archive/](archive/) 目录。

---

> 📖 **总文档入口**: [00-环境搭建](../00-环境搭建指南.md) | [01-概念入门](../01-编译器概念入门.md) | [02-快速上手](../02-快速上手教程.md) | [03-指标解读](../03-指标解读指南.md) | [04-FAQ](../04-故障排除FAQ.md)
>
> 🏗️ **架构总览**: [ARCHITECTURE.md](../ARCHITECTURE.md)
