# toy-cfg-peephole - Work Plan

## TL;DR (For humans)

**What you'll get:** 两个独立的 toy 编译器模块：（1）一个能把 IR 代码变成流程图的 CFG 生成器，帮你"看到"程序的控制流；（2）一个能在汇编代码上做小手术的窥孔优化器，自动发现并替换低效指令组合。每个模块 <300 行代码，附带设计文档和可运行 demo。

**Why this approach:** CFG 先做——因为"看到代码变成图"对新手是最大的顿悟时刻。Peephole 后做——有了控制流概念后理解"优化"更自然。每个子步骤独立可运行，反馈循环短。故意留白不做高级功能（嵌套循环高亮、更多规则），作为教学扩写练习。

**What it will NOT do:** 不集成进 ScratchV 的优化管线；不用 Semi-NCA/增量更新/Known Bits/SMT 验证等高级算法；不修改现有 IR 数据结构；核心代码不超过 300 行（不含测试和 demo）。

**Effort:** Medium (6 周分步, 2 Phase)
**Risk:** Low — 已有现成的参考实现和测试框架
**Decisions to sanity-check:** (1) CFG 的边挂在块上而非独立 edges 列表；(2) Lambda 函数而非模板引擎做 peephole 替换；(3) 只检测不可达块但不删除（留给学生练习）

Your next move: 阅读下面的完整计划，确认后可在任意一步 `$start-work` 执行。

---

> TL;DR (machine): 2-phase toy implementation — Phase 1 CFG Builder (Topic 11), Phase 2 Peephole Optimizer (Topic 13). 6 Waves, ~20 todos. Medium effort, low risk. Each step produces .md + .py + visual artifact.

## Scope
### Must have
- Phase 1: CFG Builder — basic block partition, edge construction (FALLTHROUGH/BRANCH/JUMP, include FOR/ENDFOR fix), DOT visualization, unreachable block detection (DFS, read-only), simple dominators (CHK iterative algorithm), simple natural loop detection (back edges)
- Phase 2: Peephole Optimizer — assembly parser (line → opcode + operands), 6 core rules (addi+addi fusion, li+addi fusion, beq x0→j, mv swap, mv chain, addi 0→delete), sliding window + fixed-point iteration (max 10 rounds), before/after diff report
- Per-step artifacts: design doc (.md), runnable demo (.py), visual output (.png for CFG, .txt diff for peephole)
- Test coverage: each rule/module has happy + failure tests

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No integration into compiler pipeline (standalone exercises)
- No Semi-NCA / Lengauer-Tarjan / incremental dominator updates
- No Known Bits / value range analysis
- No SMT/Z3 formal verification
- No MachineInstr-level peephole (assembly text only)
- No changes to existing IR types, no pip install changes
- Each individual `.py` file in `toy_cfg/` and `toy_peephole/` < 300 lines (demo scripts, tests excluded; the core logic is embedded in the demo scripts, so each demo file stays lean)
- No nested loop highlighting (explicitly left as exercise)

## Verification strategy
- Test decision: tests-after (implement then test) + pytest
- Evidence: `.omo/evidence/toy-cfg-peephole/` — each todo produces its own subdirectory with screenshots/outputs

## Execution strategy
### Parallel execution waves
- **Wave 1** (5 todos): CFG block partition + edge construction (all control flow types including FOR/ENDFOR fix)
- **Wave 2** (4 todos): CFG DOT visualization + unreachable detection + tests on if-else/while
- **Wave 3** (3 todos): CFG dominators (CHK) + natural loop detection + combined demo
- **Wave 4** (4 todos): Peephole parser + sliding window engine + first 3 rules
- **Wave 5** (3 todos): Peephole remaining 3 rules + fixed-point iteration + diff report
- **Wave 6** (1 todo): Final documentation + extension exercise hints
- **Final Verification Wave** (4 todos, parallel): F1-F4 checks

### Dependency matrix
> References actual todo numbers (1-20). "—" means no dependency.

| Todo(s) | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1, 2, 3 | — (sequential chain: 1→2→3) | 4, 6, 7, 8, 10, 11 | — |
| 4 | 3 | 6, 7, 8 | — |
| 5 | — | — | 1, 2, 3, 4 |
| 6, 7 | 4 | 8, 12 | — |
| 8 | 7 | — | — |
| 9 | — | — | 6, 7, 8 |
| 10, 11 | 4 | 12 | — |
| 12 | 11 | 19, 20 | — |
| 13 | — | 14, 15, 16 | 1-12 (CFG phase) |
| 14 | 13 | 15, 16 | — |
| 15 | 14 | 16, 17 | — |
| 16 | 15 | 17, 18 | — |
| 17 | 16 | 18 | — |
| 18 | 17 | 19, 20 | — |
| 19 | 9, 17 | — | 18, 20 |
| 20 | 12, 18 | — | 19 |

## Todos

> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->

### Wave 1: CFG — Basic Block Partition & Edge Construction

- [x] 1. Write CFG design doc & implement basic block partition
  What to do: Create `docs/topics/toy-cfg/01-basic-blocks.md` explaining what basic blocks are (linear execution, no branches inside). Implement `toy_cfg/demo01_build_blocks.py` that takes an IR `Function` (list of instructions with LABEL/BR/BR_IF/RETURN markers) and splits them into `BasicBlock(name, instructions, exits_to)` objects. **Must handle**: BR (unconditional jump, 1 exit), BR_IF (conditional, 2 exits), RETURN (0 exits), FOR (exit to loop body), ENDFOR (exit back to FOR header), FALLTHROUGH (no terminator → next block).
  Must NOT do: No graph yet, just print block list. No FOR/ENDFOR pass — this time implement edge generation correctly.
  Parallelization: Wave 1 | Blocked by: — | Blocks: 2, 3, 4
  References: `scratchv/ir/types.py:101-122` (Instruction dataclass, target field), `scratchv/ir/types.py:125-140` (BasicBlock class), `scratchv/ir/types.py:14-72` (OpCode enum, especially BR/BR_IF/FOR/ENDFOR/RETURN/LABEL), `scratchv/analysis/cfg_builder.py:242-343` (existing CFG builder — reference, NOT modification), `tests/test_cfg_builder.py:49-77` (existing test patterns)
  Acceptance criteria: `python toy_cfg/demo01_build_blocks.py --program if_else` prints 4+ basic blocks with correct exits_to assignments. `python toy_cfg/demo01_build_blocks.py --program while_loop` prints 3+ blocks with FOR→body edge and ENDFOR→FOR edge.
  QA scenarios:
    - Happy: `--program if_else` → prints "entry → [then, else]", "then → [end]", "else → [end]", "end → []"
    - Failure: `--program empty` → prints "entry → []" (no instructions, single block)
  Commit: docs(phase1): 01-basic-blocks design doc + basic block partition demo

- [x] 2. Implement CFG data structure and edge building
  What to do: Create `toy_cfg/demo02_build_cfg.py`. Implement `CFG` dataclass with `entry: str`, `blocks: dict[str, BasicBlock]`. Implement `build_cfg(func: Function) -> CFG` that (a) calls block partition, (b) resolves target strings to block name references, (c) validates no dangling targets. Add `print_cfg(cfg)` that prints each block and its exits in readable form.
  Must NOT do: No visualization yet. No graph theory algorithms yet. Keep it as data structure only.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3, 4, 5
  References: `scratchv/ir/types.py:143-166` (Function class, new_block), `scratchv/ir/builder.py` (IRBuilder for constructing test programs)
  Acceptance criteria: `python toy_cfg/demo02_build_cfg.py --program if_else` prints clean structural output with no dangling target errors.
  QA scenarios:
    - Happy: dangling targets → raises ValueError with block name
    - Failure: `--program infinite_loop` (a single block that jumps to itself) → builds CFG with 1 block, exits_to pointing to itself
  Commit: feat(phase1): CFG data structure + edge building

- [x] 3. Fix FOR/ENDFOR edge generation (current code bug)
  What to do: In `toy_cfg/demo02_build_cfg.py`, verify that FOR instructions produce **two** exits: (1) to the loop body block (branch), (2) FALLTHROUGH to the block after ENDFOR. ENDFOR produces one exit: back to the FOR header (JUMP). Write a test with a FOR loop that has 2+ instructions in the body.
  Must NOT do: Don't modify `scratchv/analysis/cfg_builder.py` — keep toy code independent.
  Parallelization: Wave 1 | Blocked by: 2 | Blocks: 5
  References: `scratchv/ir/types.py:31-32` (FOR = "for", ENDFOR = "endfor"), `scratchv/analysis/cfg_builder.py:326-332` (current `pass` bug)
  Acceptance criteria: FOR loop program produces CFG with 3 blocks: entry (FOR), body, end. Entry → body (BRANCH), entry → end (FALLTHROUGH), body → entry (JUMP back).
  QA scenarios:
    - Happy: FOR loop with body → CFG has back edge body→entry
    - Failure: FOR with single instruction in body → same structure, no edge loss
  Commit: fix(phase1): FOR/ENDFOR edge generation (was pass)

- [x] 4. Write comprehensive tests for wave 1
  What to do: Create `tests/test_toy_cfg_phase1.py` with pytest tests covering: (a) empty function, (b) single block (no branch), (c) if-else with BR_IF, (d) while loop with FOR/ENDFOR, (e) nested FOR, (f) multiple RETURN exits, (g) jump-to-self, (h) empty block between consecutive labels (LABEL a → LABEL b with no instructions), (i) divergent branches where both if/else branches RETURN and there's no shared "end" block.
  Each test: build CFG → assert block count → assert edge targets → assert edge types.
  Must NOT do: No dominator/loop tests yet — those come in wave 3.
  Parallelization: Wave 1 | Blocked by: 3 | Blocks: 7
  References: `tests/test_cfg_builder.py` (existing CFG tests as patterns)
  Acceptance criteria: `python -m pytest tests/test_toy_cfg_phase1.py -v` → 9+ tests all PASS
  QA scenarios:
    - Happy: if-else test → CFG has 4 blocks (entry, then, else, end), entry exits to then + else
    - Happy: empty block between labels → empty block created with FALLTHROUGH to next
    - Happy: divergent branches (both RETURN) → entry has 2 BRANCH exits, no end block created
    - Failure: empty function → single entry block with 0 exits
  Commit: test(phase1): comprehensive CFG edge tests (9+)

- [x] 5. Design doc for Wave 1
  What to do: Write `docs/topics/toy-cfg/00-what-is-cfg.md` explaining: what a CFG is, why it matters, basic blocks and edges, how ScratchV's IR encodes control flow (BR/BR_IF/FOR/ENDFOR). Include a hand-drawn ASCII diagram of if-else CFG. Include a "common pitfalls" section (FALLTHROUGH vs JUMP, empty blocks between labels). This doc is the conceptual intro (numbered `00`), to be read before the code docs in `01-*`.
  Must NOT do: No code in this doc. Conceptual only.
  Parallelization: Wave 1 | Blocked by: — | Blocks: —
  References: `docs/topics/11-控制流图生成器.md` (original topic doc, sections 1-3)
  Acceptance criteria: Doc reads clearly, beginner can understand "what's a basic block" in 10 minutes.
  QA scenarios: Happy — A peer who has never used a compiler can draw a CFG for a simple if-else program after reading. Failure — Doc contains code snippets or references to APIs that haven't been introduced yet.
  Commit: docs(phase1): 00-what-is-cfg tutorial

### Wave 2: CFG — Visualization & Unreachable Detection

- [x] 6. Implement DOT format output
  What to do: Create `toy_cfg/demo03_visualize.py`. Implement `cfg_to_dot(cfg) -> str` that produces Graphviz DOT format. Each node = a box showing block name and instruction summary. Edges colored by type (blue dashed = BRANCH with label, red solid = JUMP, black solid = FALLTHROUGH). Entry node = green background. Exit nodes = coral background. Save to `.dot` file. Add CLI: `--output cfg.dot` and optionally `--render cfg.png` (calls `dot -Tpng`).
  Must NOT do: No loop highlighting yet. No interactive visualization. Not handling graphviz not installed gracefully.
  Parallelization: Wave 2 | Blocked by: 4 | Blocks: 7
  References: Graphviz DOT language (node shapes, colors, edge styles), `scratchv/analysis/cfg_builder.py:142-198` (existing to_dot)
  Acceptance criteria: `python toy_cfg/demo03_visualize.py --program if_else --render cfg.png` generates cfg.dot + cfg.png. Opening cfg.png shows correctly laid out graph with 4 colored nodes.
  QA scenarios:
    - Happy: DOT file opens in Graphviz, renders without errors
    - Failure: `--program empty` → generates single entry node with no edges
  Commit: feat(phase1): CFG visualization via Graphviz DOT

- [x] 7. Implement unreachable block detection
  What to do: In `toy_cfg/demo03_visualize.py`, add `find_unreachable(cfg) -> set[str]` using DFS from entry block. Mark unreachable blocks in DOT output with dashed border + gray fill. Add CLI flag `--show-unreachable`.
  Must NOT do: Only **detect** — do NOT delete. Deletion is left as exercise for students.
  Parallelization: Wave 2 | Blocked by: 6 | Blocks: 8
  References: `scratchv/analysis/cfg_builder.py:126-140` (CFG.reachable_nodes property — DFS algorithm reference)
  Acceptance criteria: Feed a program with dead code after RETURN → unreachable blocks detected and visually marked in DOT output.
  QA scenarios:
    - Happy: Code after RETURN in same block → CFG has 1 reachable block, 0 unreachable (because single block)
    - Happy: Code in a block after RETURN in predecessor → that block is marked as unreachable (gray dashed)
    - Failure: All blocks reachable → no unreachable markers
  Commit: feat(phase1): unreachable block detection + visualization

- [ ] 8. Test Wave 2 functionality
  What to do: Add tests to `tests/test_toy_cfg_phase1.py` for: (a) DOT output contains correct node/edge count, (b) unreachable detection on multi-block programs with dead code after RETURN, (c) DOT rendering with --show-unreachable marks unreachable blocks as gray, (d) if-else produces exactly 4 nodes in DOT, (e) empty program produces 1 node 0 edges.
  Must NOT do: No dominator tests yet.
  Parallelization: Wave 2 | Blocked by: 7 | Blocks: —
  References: `tests/test_cfg_builder.py:101-284` (DOT and unreachable tests)
  Acceptance criteria: `python -m pytest tests/test_toy_cfg_phase1.py -v` → all previous + new tests pass
  QA scenarios:
    - Happy: if-else → DOT output contains exactly 4 node definitions and 4 edge definitions
    - Happy: unreachable detection → DOT with --show-unreachable, unreachable blocks have gray fillcolor
    - Failure: all blocks reachable → no unreachable markers in DOT output
  Commit: test(phase1): visualization + unreachable tests

- [x] 9. Design doc for Wave 2
  What to do: Write `docs/topics/toy-cfg/02-visualizing-cfg.md` explaining: why visualization matters, Graphviz DOT syntax basics (nodes, edges, colors, shapes), how to interpret CFG diagrams (entry→exit flow, branch edges). Include a "reading CFG diagrams" section showing 3 example diagrams with explanation.
  Must NOT do: No dominator/loop content yet.
  Parallelization: Wave 2 | Blocked by: — | Blocks: —
  References: `docs/topics/11-控制流图生成器.md` sections 4-5 (visualization)
  Acceptance criteria: Doc includes 3 CFG diagrams (entry→exit, if-else, while-loop) with explanations. Beginner can read a DOT file after reading.
  QA scenarios: Happy — A peer reads the doc and can explain what a dashed blue edge means. Failure — Doc uses Graphviz features not yet supported by the toy implementation (subgraphs, HTML labels, etc.).
  Commit: docs(phase1): visualizing-cfg tutorial

### Wave 3: CFG — Dominators & Loop Detection

- [ ] 10. Implement dominator computation (CHK algorithm)
  What to do: Create `toy_cfg/demo04_dominators.py`. Implement `compute_dominators(cfg) -> dict[str, set[str]]` using the Cooper-Harvey-Kennedy iterative algorithm: (1) entry dominates itself; (2) all other blocks initially dominated by all blocks; (3) iterate: dom(B) = {B} ∪ ∩ dom(P) for all predecessors P, until fixed point. Then implement `compute_idom(cfg, dom_sets) -> dict[str, str | None]` by finding the unique strict dominator not dominated by any other strict dominator. Print results: for each block, show dom set and idom.
  Must NOT do: No DFS numbering (O(1) queries). No Semi-NCA. Print-based output, not visualized yet.
  Parallelization: Wave 3 | Blocked by: 4 | Blocks: 11
  References: `scratchv/analysis/cfg_builder.py:370-453` (existing dominator reference, but we implement iteratively from scratch)
  Acceptance criteria: `python toy_cfg/demo04_dominators.py --program if_else` shows entry dominates all blocks, else/then dominated by entry, end dominated by all.
  QA scenarios:
    - Happy: entry dominates all blocks in any CFG
    - Happy: idom(then) == entry, idom(end) == entry (in simple if/else)
    - Failure: Empty CFG → empty dominator sets
  Commit: feat(phase1): CHK iterative dominator algorithm

- [ ] 11. Implement natural loop detection
  What to do: In `toy_cfg/demo04_dominators.py`, add `find_loops(cfg, dom_sets) -> list[tuple[str, set[str]]]`. Find back edges: edge (A→B) is a back edge if B ∈ dom_sets[A] (B dominates A). For each back edge (src→header), collect loop body by reverse DFS from src to (but not including) header. Print loops with header, body blocks, and back edges.
  Must NOT do: No nested loop hierarchy. No loop depth calculation. Print-based output.
  Parallelization: Wave 3 | Blocked by: 10 | Blocks: 12
  References: `scratchv/analysis/cfg_builder.py:459-536` (existing loop detection reference)
  Acceptance criteria: `python toy_cfg/demo04_dominators.py --program while_loop` detects at least 1 natural loop (header, {header, body}, back edge body→header).
  QA scenarios:
    - Happy: while loop → 1 loop with header, body includes block inside loop
    - Failure: if/else (no loop) → 0 loops detected
    - Happy: nested FOR → 2 loops detected (inner and outer), each with correct body
  Commit: feat(phase1): natural loop detection via back edges

- [ ] 12. Combined CFG demo + Wave 3 tests
  What to do: Create `toy_cfg/demo05_full.py` that takes a program and in one run: (a) builds CFG, (b) generates DOT with unreachable marking, (c) computes dominators, (d) detects loops, (e) highlights loop headers in DOT (light blue). Add all tests to `tests/test_toy_cfg_phase2.py`: dominator tests (5+), loop detection tests (3+), full pipeline test. Include a test for the addi+addi fusion rule's condition: the pattern `addi rd1, rs1, a; addi rd2, rs2, b` only fuses when `rd1 == rs2` (data dependency chain) — not when registers are unrelated.
  Must NOT do: No nested loop hierarchy/complex nesting detection.
  Parallelization: Wave 3 | Blocked by: 11 | Blocks: 19, 20
  References: (none beyond previous todos)
  Acceptance criteria: `python toy_cfg/demo05_full.py --program while_loop` prints all analysis results and generates demo.png with loop header highlighted. `python -m pytest tests/test_toy_cfg_phase2.py -v` → 8+ tests pass.
  QA scenarios:
    - Happy: while-loop program → CFG has 3 blocks, 1 loop detected, loop header blue in DOT
    - Happy: dominator test → entry dominates `then` block in if-else
    - Failure: no-loop program (if-else without while) → 0 loops detected
    - Failure: addi+addi with unrelated registers (addi x1,x2,3; addi x3,x4,5) → no fusion
  Commit: feat(phase1): combined CFG analysis demo + wave 3 tests

### Wave 4: Peephole — Parser + Engine + First Rules

- [ ] 13. Write Peephole design doc & implement assembly parser
  What to do: Create `docs/topics/toy-peephole/01-peephole-intro.md` explaining: what peephole optimization is, the "keyhole" metaphor, sliding window concept, fixed-point iteration. Then implement `toy_peephole/demo01_parser.py` with `parse_line(line) -> (opcode, [operands]) | None` and `parse_asm(text) -> list[tuple]`. Handle: labels ("main:" → `(None, ["main"])`), comments (# ...), empty lines, operands with register names and immediates.
  Must NOT do: No optimization yet. Parser only.
  Parallelization: Wave 4 | Blocked by: — | Blocks: 14, 15
  References: `scratchv/backend/asm_peephole.py:87-165` (existing _parse_line, _parse_asm), `docs/topics/13-窥孔优化器.md` (original topic doc)
  Acceptance criteria: `python toy_peephole/demo01_parser.py --file test.s` prints parsed lines. Round-trip test: parse → unparse → identical.
  QA scenarios:
    - Happy: `"addi x1, x2, 3"` → `("addi", ["x1", "x2", "3"])`
    - Happy: `"main:"` → `(None, ["main"])`
    - Failure: `""` → skipped
  Commit: docs(phase2): peephole-intro + assembly parser

- [ ] 14. Implement peephole rule engine + sliding window
  What to do: Create `toy_peephole/demo02_rules.py`. Implement `PeepholeRule(name, pattern, condition, replacement)` dataclass where `replacement` is a callable `(window_ops) -> [new_instruction_strings]`. Implement `peephole_pass(lines, rules)` that scans with sliding window: for i in range(len(lines)), try each rule, if match → replace i:i+window_size with replacement result, restart from i. Return (new_lines, changes_count, rule_matches).
  Must NOT do: No fixed-point iteration yet. Single pass only.
  Parallelization: Wave 4 | Blocked by: 13 | Blocks: 15
  References: `scratchv/backend/asm_peephole.py:363-418` (existing optimize loop as pattern reference)
  Acceptance criteria: `python toy_peephole/demo02_rules.py` runs a single pass on test asm, reports changes.
  QA scenarios:
    - Happy: "addi x1, x1, 3\naddi x1, x1, 5" → single pass merges to "addi x1, x1, 8"
    - Failure: "addi x1, x1, 3\nadd x2, x3, x4" → no match, unchanged
  Commit: feat(phase2): peephole rule engine + sliding window

- [ ] 15. Implement first 3 peephole rules with tests
  What to do: Add rules to `toy_peephole/demo02_rules.py`: Rule 1 `addi+addi fusion`: addi rd, rs, a; addi rd, rs, b → addi rd, rs, (a+b) (check 12-bit overflow). Rule 2 `li+addi fusion`: li rd, a; addi rd, rd, b → li rd, (a+b). Rule 3 `beq x0/x0 to j`: beq x0/x0/zero, x0/x0/zero, label → j label. Create `tests/test_toy_peephole.py` with pytest tests: each rule has happy + failure tests.
  Must NOT do: No fixed point yet. Single pass only.
  Parallelization: Wave 4 | Blocked by: 14 | Blocks: 16
  References: `scratchv/backend/asm_peephole.py:194-237` (existing 5 default rules as patterns), `tests/test_asm_peephole.py:40-73` (existing test patterns)
  Acceptance criteria: `python -m pytest tests/test_toy_peephole.py -v -k "first_three"` → 6+ tests pass. Each rule has 1 happy + 1 failure test.
  QA scenarios:
    - Rule 1 happy: addi x1,x1,3 + addi x1,x1,5 → addi x1,x1,8
    - Rule 1 failure: addi x1,x2,3 + addi x3,x4,5 (different dest) → no match
    - Rule 2 happy: li x1,10 + addi x1,x1,5 → li x1,15
    - Rule 3 happy: beq x0,x0,label → j label
    - Rule 3 failure: beq x1,x0,label (non-zero first operand) → no match
  Commit: feat(phase2): first 3 peephole rules (addi+addi, li+addi, beq→j)

### Wave 5: Peephole — More Rules + Fixed Point + Report

- [ ] 16. Implement remaining 3 peephole rules
  What to do: Add to `toy_peephole/demo02_rules.py`: Rule 4 `mv swap elimination`: mv x,y; mv y,x → delete both. Rule 5 `mv chain shortening`: mv a,b; mv c,a → mv c,b. Rule 6 `addi zero elimination`: addi rd, rs, 0 → delete (no-op). Add tests: each rule happy + failure.
  Must NOT do: No fixed point yet.
  Parallelization: Wave 5 | Blocked by: 15 | Blocks: 17
  References: `scratchv/backend/asm_peephole.py:206-211` (mv swap rule), `scratchv/backend/asm_peephole.py:229-236` (mv chain rule), `scratchv/optimizer/peephole.py:77-84` (addi zero IR rule → adapt to asm level)
  Acceptance criteria: `python -m pytest tests/test_toy_peephole.py -v -k "second_three"` → 6+ tests pass.
  QA scenarios:
    - Rule 4: mv t0,t1 + mv t1,t0 → both deleted
    - Rule 5: mv t0,t1 + mv t2,t0 → mv t2,t1
    - Rule 6: addi x1,x1,0 → deleted entirely
  Commit: feat(phase2): remaining 3 peephole rules (mv swap, mv chain, addi zero)

- [ ] 17. Implement fixed-point iteration + diff report
  What to do: Create `toy_peephole/demo03_full.py`. Implement `peephole_optimize(lines, rules, max_iter=10)` that calls peephole_pass repeatedly until no changes or max_iter. Implement `report(before_lines, after_lines, changes)` that prints: instruction count before/after, percentage saved, per-rule match counts, and a side-by-side diff of changed lines. Add CLI: `--input test.s --output optimized.s --report`.
  Must NOT do: No pipeline integration.
  Parallelization: Wave 5 | Blocked by: 16 | Blocks: 18
  References: `scratchv/backend/asm_peephole.py:363-418` (existing optimize loop), `scratchv/backend/asm_peephole.py:513-526` (existing report)
  Acceptance criteria: `python toy_peephole/demo03_full.py --input test_multi.s --report` prints before/after counts and per-rule stats. `test_multi.s` with 3 addi chain + 1 beq → 2 instructions saved.
  QA scenarios:
    - Happy: 3 consecutive addi instructions → 2 passes, ends with 1 addi, saved=2
    - Happy: no optimization opportunities → 0 saved, "No changes" message
    - Iteration limit: artificially long chain → max_iter reached, warning printed
  Commit: feat(phase2): fixed-point iteration + diff report

- [ ] 18. Comprehensive peephole tests
  What to do: Add to `tests/test_toy_peephole.py`: (a) fixed-point on multi-rule chain (addi+addi → first pass, then li+addi → second pass), (b) max_iter termination (artificially long chain prints warning), (c) combined rules (chain that triggers addi+addi then mv chain), (d) 10-line program with no optimization opportunities → 0 changes, (e) report output contains expected strings, (f) label preservation across optimization.
  Must NOT do: No simulation/correctness verification.
  Parallelization: Wave 5 | Blocked by: 17 | Blocks: 19, 20
  References: (none beyond previous todos)
  Acceptance criteria: `python -m pytest tests/test_toy_peephole.py -v` → 12+ tests pass.
  QA scenarios:
    - Happy: 3-addi chain → optimized to 1 addi in 2 fixed-point passes
    - Happy: no optimization opportunities → 0 saved, "No changes" in output
    - Failure: max_iter=1 on 3-addi chain → only 1 pass, saves 1 (not 2)
  Commit: test(phase2): fixed-point + combined rules + report tests

- [ ] 19. Design doc for Wave 4-5
  What to do: Write `docs/topics/toy-peephole/02-rules-and-iteration.md` explaining: the 6 rules and why each works, sliding window algorithm, fixed-point iteration concept (why one pass isn't enough), how to read optimization reports. Include a hand-worked example showing multi-pass iteration on a 3-addi chain.
  Must NOT do: No advanced topics (known bits, cost models, verification).
  Parallelization: Wave 5 | Blocked by: 17 | Blocks: —
  References: `docs/topics/13-窥孔优化器.md` sections 3-4
  Acceptance criteria: Doc includes a hand-worked 3-addi → 1-addi example showing 2 passes. Beginner can trace the fixed-point iteration manually.
  QA scenarios: Happy — A peer who read the doc can predict how many passes a `addi,addi,addi` chain needs. Failure — Doc references optimization theory (e.g., "lattice", "meet-over-paths") that a beginner wouldn't know.
  Commit: docs(phase2): rules-and-iteration tutorial

### Wave 6: Final Documentation

- [ ] 20. Write final documentation and extension exercises
  What to do: Create `docs/topics/toy-cfg/03-exercises.md` with 3 extension exercises: (1) implement unreachable block deletion (not just detection), (2) add nested loop highlighting in DOT output, (3) implement a post-dominator tree. Create `docs/topics/toy-peephole/03-exercises.md` with 3 exercises: (1) add `addi x, x, 0 → (delete)` rule, (2) add `mul x, 2^n → slli x, n` rule, (3) add instruction-level cost model.
  Must NOT do: No solutions provided — exercises only.
  Parallelization: Wave 6 | Blocked by: 12, 18 | Blocks: —
  References: `docs/topics/11-控制流图生成器.md:140-152` (existing exercises), `docs/topics/13-窥孔优化器.md:207-222` (existing exercises)
  Acceptance criteria: Each exercise has: (a) clear problem statement, (b) expected behavior, (c) hints, (d) known-good test case for self-checking.
  QA scenarios: Happy — Each exercise has exactly 4 sections (problem, expected, hints, test case). Failure — Any exercise assumes knowledge of concepts not covered in previous docs (e.g., doesn't require dominator knowledge for an exercise that's labeled "beginner").
  Commit: docs(phase1+2): extension exercises for both topics

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — verify all 20 todos deliver what's promised in Scope IN
- [ ] F2. Code quality review — each core module < 300 lines, no dead code, naming consistent
- [ ] F3. Real manual QA — run CFG demo on if-else+while program → correct DOT, correct dom/loop output. Run peephole on 3-addi chain → 2 saves
- [ ] F4. Scope fidelity — confirm Must NOT have items are absent: no pipeline integration, no advanced algos, no IR changes

## Commit strategy

Each todo commits independently with structured messages. Per-phase branch merges.

**Branch structure:**
```
main ← toy-cfg-phase1 ← wave-1-cfg-core
                          wave-2-cfg-vis
                          wave-3-cfg-dom-loop
main ← toy-peephole-phase2 ← wave-4-peephole-core
                              wave-5-peephole-rules
```

**Commit message format:**
```
<type>(<scope>): <present-tense summary>
<blank line>
<details, especially for design decisions>
```

Types: `feat` (new capability), `docs` (documentation), `test` (tests only), `fix` (bug fix), `chore` (infra)

**Each todo's Commit line shows the message to use.**

**Examples:**
```
feat(cfg): implement basic block partition from IR instructions
- Split by LABEL/BR/BR_IF/RETURN/FOR/ENDFOR boundaries
- Each block stores exits_to with target name + edge type
- 9 tests covering all control flow patterns
```

## Success criteria

**Phase 1 complete when:**
1. `python toy_cfg/demo05_full.py --program if_else` produces:
   - CFG DOT with 4+ colored nodes (green entry, coral exits, colored edges)
   - Dominator sets for each block printed
   - Loop detection output (0 loops for if_else, 1+ for while)
   - `demo_cfg.png` visualizing all of the above
2. `python -m pytest tests/test_toy_cfg_phase1.py tests/test_toy_cfg_phase2.py -v` → 16+ tests all PASS
3. Core module in `toy_cfg/` < 300 lines

**Phase 2 complete when:**
1. `python toy_peephole/demo03_full.py --input test_multi.s --report` produces:
   - Optimized assembly with 2+ instructions saved
   - Per-rule match statistics
   - Before/after instruction count comparison
2. `python -m pytest tests/test_toy_peephole.py -v` → 12+ tests all PASS
3. Core module in `toy_peephole/` < 300 lines

**Project-wide complete when:**
1. All 6 `docs/topics/toy-*/` documents written and readable
2. All 6 exercise descriptions are clear and self-contained
3. Final verification wave (F1-F4) all APPROVE
