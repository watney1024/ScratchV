---
slug: toy-cfg-peephole
status: review-passed
intent: clear
review_required: false
pending-action: deliver .omo/plans/toy-cfg-peephole.md
review_results:
  momus: APPROVED (with 4 recommendations — all fixed in plan)
  oracle: APPROVED (with 4 caveats — all fixed in plan)
approach: two-phase toy implementation — Phase 1 = CFG Builder (Topic 11), Phase 2 = Peephole Optimizer (Topic 13). Each phase produces step-by-step artifacts (design doc, demo script, tests, visualization). Max <300 lines per core module. Preserve compiler essence: graph visualization, fixed-point iteration, before/after feedback.
---

# Draft: toy-cfg-peephole

## Components (topology ledger)

| id | outcome | status | evidence path |
|----|---------|--------|--------------|
| C1 | CFG Builder — build CFG from IR, basic block partition, edge construction, DOT visualization, unreachable detection, simple dominators (iterative CHK), simple loop detection | active | `scratchv/analysis/cfg_builder.py:584行`, `tests/test_cfg_builder.py:284行/21测试` |
| C2 | Peephole Optimizer — assembly parser, 4-6 sliding-window rules, fixed-point iteration, before/after diff report | deferred (Phase 2) | `scratchv/backend/asm_peephole.py:586行`, `tests/test_asm_peephole.py:148行/17测试` |

## Open assumptions (announced defaults)

| assumption | adopted default | rationale | reversible? |
|------------|----------------|-----------|-------------|
| 先做哪个 Topic | **Topic 11 (CFG) 先做** — CFG 是更基础的概念、可视化的"啊哈时刻"更强、当前实现有 FOR/ENDFOR bug 可立即改进 | 新手先"看到"控制流图再"优化"汇编，教学顺序更自然 | 可调换顺序 |
| CFG 边存储方式 | **exits_to 直接挂在基本块上**而非独立的 edges 列表 | 对新手更直观"块就是知道它要跳到哪"；代码量减少 40% | 是 — 未来可重构为邻接表 |
| 支配树算法 | **Cooper-Harvey-Kennedy 迭代算法**而非 Semi-NCA | Toy 项目 ≤ 50 个块，迭代算法代码 15 行即可读懂，O(N²) 足够快 | 是 — 可升级为 Semi-NCA |
| Peephole 规则数 | **6 条核心规则**而非原文档的 5 条（增加 `mv x,y; mv y,z → mv x,z` 链式传递） | 展示"链式优化"的概念，同时保持简单 | 是 — 规则可增删 |
| Peephole 替换方式 | **lambda 函数**而非模板字符串 `{rd} {imm_sum}` | 每规则一行函数，去掉 50 行 `_apply_replacement` 模板引擎 | 是 |
| 文档产物格式 | **每步输出独立的 .md + 可运行 demo 脚本** | 新手可以"跟着文档一步步做"而非一次性看大代码 | 否 — 这是项目约定 |

## Findings (cited - path:lines)

- **IR 数据结构** (`scratchv/ir/types.py:91-167`): `Instruction.opcode` 枚举含 FOR/ENDFOR/BR/BR_IF/LABEL/RETURN 等控制流操作码，`target: Optional[str]` 用字符串存储基本块名，`BR_IF` 的两个目标编码为逗号分隔的 `"true,false"` 字符串。`BasicBlock` 含 `name: str`, `instructions: list[Instruction]`, `phi_nodes: list[Instruction]`。
- **CFG 构建器现状** (`scratchv/analysis/cfg_builder.py:326-332`): FOR/ENDFOR 的边构建代码为 `pass`（未实现），导致循环结构的 CFG 永远无法正确构建。`edges: list[CFGEdge]` 线性存储导致 successors/predecessors 查询为 O(E)。CFG 节点与 IR 的 BasicBlock 对象无反向链接。
- **测试覆盖** (`tests/test_cfg_builder.py:284行`): 21 个测试，涵盖基础构建但无多块 CFG 的实际边验证，无 FOR/ENDFOR 循环测试，dominator/loop 测试仅在平凡情况（单块）运行。
- **Peephole 现状** (`scratchv/backend/asm_peephole.py`): 586 行，含 5 条默认规则、CLI、固定点迭代、报告。已有较好的代码基础。IR 级 peephole (`scratchv/optimizer/peephole.py`: 117 行) 含 4 条块内规则。
- **现有优化管线** (`scratchv/compiler.py:364-382`): Pass 顺序为 constant-folding → DCE → peephole → muladd-fusion → LICM。所有 pass 为块内线性扫描，CFG 构建器无人调用。
- **开源参考** (研究阶段发现): PyCOOLC (aalhour/PyCOOLC) 的 CFG 构建器以 ~150 行实现完整的 toy CFG；angr 使用 NetworkX 做图分析后端; LLVM 用分层窥孔架构 (InstCombine → DAGCombine → PeepholeOptimizer → MachineCombiner)，但 toy 项目直接对标太复杂。

## Decisions (with rationale)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **CFG 先做，Peephole 后做** | CFG 是基础设施概念，可视化给新手的冲击力更大，且现有代码有真实 bug 可立即修复 |
| D2 | **核心模块 < 300 行** | 新手 30 分钟能读完的极限；超出的内容放到 exercise/extension 中 |
| D3 | **每个子步骤独立可运行** | 每完成一小步都能 `python demo.py` 看到输出，保持反馈循环短 |
| D4 | **"空白留白"策略** | 某些功能（嵌套循环高亮、更多 peephole 规则）故意不实现，作为教学扩写练习 |
| D5 | **产物即文档** | 每个步骤输出 .md 说明 + .py demo + .png 图，三位一体 |

## Scope IN

- CFG Builder (Topic 11, Phase 1):
  - 基本块划分（以 LABEL/BR/RETURN 为边界）
  - 有向图构建（FALLTHROUGH/BRANCH/JUMP 三种边类型，exits_to 挂在块上）
  - FOR/ENDFOR 循环边构建（修复当前 bug）
  - DOT 格式输出 → Graphviz PNG
  - 不可达块检测（DFS 标记，但**不**做删除，留做练习）
  - 支配树（Cooper-Harvey-Kennedy 迭代算法）
  - 自然循环检测（回边法）
  - 简单的 if-else / while / nested-if 测试程序
- Peephole Optimizer (Topic 13, Phase 2):
  - 汇编解析器（一行 → opcode + operands）
  - 6 条核心规则（addi+addi fusion, li+addi fusion, beq x0→j, mv/mv swap, mv chain, addi 0→delete）
  - 滑动窗口 + 固定点迭代（max 10 轮）
  - 优化前后 diff 对比报告
  - 5 个测试汇编片段
- 全过程文档和产物：
  - 每步设计说明.md
  - 每步可运行 demo.py
  - 最终产物清单
  - 教学扩写练习提示

## Scope OUT (Must NOT have)

- ❌ 不集成到现有多 pass 优化管线（保持为独立模块，留给学生做练习）
- ❌ 不做 Semi-NCA / Lengauer-Tarjan / 增量更新等高级支配树算法
- ❌ 不做 Known Bits / 值域分析
- ❌ 不做 SMT/Z3 形式化验证
- ❌ 不做 MachineInstr 层面的窥孔优化（仅汇编文本层面）
- ❌ 不做 pip install / 构建系统修改
- ❌ 不超过 300 行核心代码（不含测试和 demo）
- ❌ 不修改现有 IR 数据结构（保持 `target: str` 不变，只在 CFG 层做字符串到整数索引的映射）

## Open questions

（无 — 基于已有研究和 toy 原则，所有决策已明确。）

## Approval gate
status: awaiting-approval

**Brief:**

我会分两个 Phase 来实现。首先做 **CFG Builder (Topic 11)**，再做 **Peephole Optimizer (Topic 13)**。

**为什么 CFG 先做？**
1. 可视化"啊哈时刻"更强——新手第一次看到代码变成图时最兴奋
2. 更基础的概念——理解程序结构后再理解"优化"更自然
3. 当前代码有真实 bug（FOR/ENDFOR 边是 `pass`），修复有实际价值

**设计哲学：**
- 每个核心模块 < 300 行代码
- 每步产出 **文档(.md) + demo(.py) + 图(.png)** 三位一体
- 故意留一些功能不完成，作为教学扩写练习
- 反馈循环短——每完成一小步都能 `python demo.py` 看到效果

**两组件时间投入：** CFG Phase 约 3-4 周，Peephole Phase 约 2-3 周（按周粒度分步）

同意这个方向后，我会创建完整的计划文件 `.omo/plans/toy-cfg-peephole.md`，包含所有步骤、交付产物、里程碑。
