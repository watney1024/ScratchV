# 03 扩展练习

> 这三个练习建立在 demos 01-06 的基础上。每个练习预期 30-60 分钟完成。
> 练习中没有给出完整代码实现，只有思路引导。建议先自己试，卡住再看提示。

---

## 练习 1: 不可达块删除（⭐）

**难度**: ⭐

**问题描述**: 目前 `demo04_visualize.py` 中的 `find_unreachable()` 只能**检测**不可达块——在 DOT 输出中把它们标记为灰色虚线框。但不可达块仍然留在 CFG 数据结构中，后续分析（支配树、循环检测）还是要处理它们。

你需要在 `demo02_build_cfg.py` 或新建的 `demo07_cleanup.py` 中实现一个函数 `remove_unreachable(cfg) -> CFG`，它真正从 CFG 中删除不可达的块和相关的边：

1. 调用 `find_unreachable()` 找出所有不可达块
2. 从 `cfg.blocks` 中删除这些块
3. 从剩余所有块的 `exits_to` 列表中，删除指向已删除块的边
4. 如果某个块删除所有边后变成孤块（没有边指向任何存在的块）且不是出口块？考虑这种情况是否可能发生，以及如何处理

**预期行为**:

```
# 输入：含不可达块的 CFG（unreachable 程序）
Block: entry  →  ret, exits: []
Block: dead   →  ret, exits: []  (UNREACHABLE)

# 调用 remove_unreachable(cfg) 后
Block: entry  →  ret, exits: []
# dead 块已消失
```

- 对 `if_else` 程序调用 `remove_unreachable`，结果应该和原 CFG 完全一样（因为没有不可达块）
- `reachable_from()` 的返回值应该等于 `cfg.blocks` 的 keys 集合

**提示**:

- 提示 1：先调用 `find_unreachable()`（在 `demo04_visualize.py` 里已经有了），拿到不可达块名字的集合
- 提示 2：删除块之后，需要遍历所有剩余块的 `exits_to`，移除指向已删除块的 `(target, edge_label)` 元组
- 提示 3：删除边之后，可能会出现新的不可达块吗？如果会，你可能需要迭代删除直到固定点。想想什么场景下会出现这种情况
- 提示 4：复制 CFG 再修改，不要原地修改——这样方便对比删除前后的差异

**自检用例**:

```python
from toy_cfg.demo01_build_blocks import DEMOS
from toy_cfg.demo02_build_cfg import build_cfg
from toy_cfg.demo04_visualize import find_unreachable

# 1. unreachable 程序：删除前后对比
func = DEMOS["unreachable"].functions[0]
cfg = build_cfg(func)
print("Before:", list(cfg.blocks.keys()))                 # ["entry", "dead"]
cleaned = remove_unreachable(cfg)
print("After:", list(cleaned.blocks.keys()))              # ["entry"]  — dead 已删除
assert cleaned.blocks["entry"].exits_to == []              # entry 的边不变

# 2. if_else 程序：没有不可达块，删除后不变
cfg2 = build_cfg(DEMOS["if_else"].functions[0])
cleaned2 = remove_unreachable(cfg2)
assert set(cleaned2.blocks.keys()) == set(cfg2.blocks.keys())  # 完全一致

# 3. 验证所有剩余块的 exits_to 不再指向已删除的块
for name, block in cleaned.blocks.items():
    if block.exits_to:
        for target, _ in block.exits_to:
            assert target in cleaned.blocks  # 没有悬空引用
```

---

## 练习 2: 嵌套循环深度高亮（⭐⭐）

**难度**: ⭐⭐

**问题描述**: `demo06_full.py` 已经能检测到嵌套循环——`demo_nested_for()` 会产生两个循环。但 DOT 可视化中，所有循环头（loop header）都被涂成一样的 `lightskyblue`，看不出哪层循环是外层、哪层是内层。

你的任务是增强 `cfg_to_dot_highlight()` 函数，让 DOT 输出根据循环嵌套深度使用不同深浅的蓝色：

- 深度 1（最外层）→ `lightskyblue`
- 深度 2 → `skyblue`
- 深度 3 → `deepskyblue`
- 深度 4+ → `dodgerblue`

你需要先计算每个块的循环嵌套深度。一个块如果在 N 个循环的 body 里，它的嵌套深度就是 N。循环头本身也算在它自己的循环 body 里。

**预期行为**:

```
nested_for 程序的 DOT 输出：
- entry（外层 FOR）→ lightskyblue（深度 1）
- outer_body → ... 
- inner_entry（内层 FOR）→ skyblue（深度 2）
- inner_body（同时属于两个循环）→ skyblue（深度 2）
- outer_end → ...
- end → white（不在任何循环中）

非循环程序（if_else）的所有块不受影响，颜色和原来一样。
```

**提示**:

- 提示 1：`demo05_dominators.py` 中的 `find_loops()` 返回一个 `list[tuple[str, set[str]]]`，每个元素是 `(header, body_set)`。需要从中算出每个块在多少个循环的 body_set 里
- 提示 2：遍历所有已检测到的循环，对每个循环 body 里的所有块，嵌套深度加 1。可以用一个 `defaultdict(int)` 来累加
- 提示 3：`cfg_to_dot_highlight()` 中目前用 `if is_loop_header: color = "lightskyblue"`。修改为根据嵌套深度选择颜色深浅
- 提示 4：定义一个深度到颜色的映射表，比如 `DEPTH_COLORS = {1: "lightskyblue", 2: "skyblue", 3: "deepskyblue", 4: "dodgerblue"}`。超过 4 的统一用 `dodgerblue`

**自检用例**:

```python
from toy_cfg.demo01_build_blocks import DEMOS
from toy_cfg.demo02_build_cfg import build_cfg
from toy_cfg.demo05_dominators import compute_dominators, find_loops
from toy_cfg.demo06_full import cfg_to_dot_highlight

# nested_for 程序
func = DEMOS["nested_for"].functions[0]
cfg = build_cfg(func)
dom = compute_dominators(cfg)
loops = find_loops(cfg, dom)
print(f"Detected {len(loops)} loops")          # 应该是 2

# 计算嵌套深度
depths = compute_nest_depth(cfg, loops)  # 你实现的函数
assert depths.get("entry") == 1                # 外层循环 header
assert depths.get("inner_entry") == 2          # 内层循环 header（深度 2）
assert depths.get("inner_body") == 2           # 同时属于两个循环
assert depths.get("end") == 0                  # 不在循环中

# DOT 中深度 2 的块应该是 skyblue（不是 lightskyblue）
dot = cfg_to_dot_highlight(cfg, loop_headers={h for h, _ in loops})
assert 'fillcolor=lightskyblue' in dot  # 深度 1
assert 'fillcolor=skyblue' in dot       # 深度 2
# 具体颜色可能因你的实现而异，关键是不同的深度用不同的颜色
```

---

## 练习 3: 后支配树（Post-Dominator Tree）（⭐⭐⭐）

**难度**: ⭐⭐⭐

**问题描述**: 支配树（Dominator Tree）回答"从入口出发，哪些块是必经之路"。后支配树（Post-Dominator Tree）回答相反的问题："**到出口为止**，哪些块是必经之路"。形式上，如果从 B 到**任意出口**（出度为 0 的块）的所有路径都必须经过 A，则 A 后支配（post-dominate）B。

后支配树在以下场景中非常有用：
- **循环出口识别**：循环的"后支配边"可以帮助找到循环的单一出口
- **控制流归约**：识别 if-else 结构中的汇合点
- **死代码消除**：如果一个语句的后支配者是一个不可达块，那这个语句也可能是不可达的

你的任务是实现 `compute_post_dominators(cfg) -> dict[str, set[str]]`，使用和 `demo05_dominators.py` 中 `compute_dominators()` 相同的 CHK 迭代算法，但作用在**反向 CFG** 上。

实现步骤：
1. 构建反向 CFG（revCFG）：把原 CFG 的所有边反向，原出口变成入口
2. 如果有多个出口（比如 if-else 的两个分支都 return），需要添加一个虚拟的"exit"节点，让所有真实出口都指向它
3. 在反向 CFG 上运行 CHK 算法计算支配关系——结果就是原 CFG 的后支配关系
4. 实现 `compute_post_idom(cfg, post_dom_sets) -> dict[str, str | None]` 计算立即后支配者

**预期行为**:

```
if_else 程序：
  entry:   post-dom = {entry, end}     （从入口到出口，必须经过 end）
  then:    post-dom = {then, end}       （从 then 到出口，必须经过 end）
  else:    post-dom = {else, end}
  end:     post-dom = {end}             （出口后支配自身）

while_loop 程序：
  entry:   post-dom = {entry, end}
  body:    post-dom = {body, end}       （注意 body 的后支配者不包含 entry）
  end:     post-dom = {end}
```

**提示**:

- 提示 1：反向 CFG 不需要真的改数据结构。你可以先收集所有块的入边（`_compute_predecessors` 已经做了这个），然后对反向图做支配计算时，"前驱"在原反向图中就是后继。更简单的方法：构造一个"虚拟"的 CFG 对象，它的 `blocks` 不变但边全反向
- 提示 2：多出口问题：`compute_dominators()` 假定只有一个入口。反向 CFG 如果有多个出口就会变成多个入口。解决方法是添加一个虚拟的 exit 块，让所有真实出口（出度为 0 的块）都有一条边指向它
- 提示 3：实现时可以先创建反向邻接表。原图中 `block.exits_to` 的每条 `(target, label)` 在反向图中变成一条 `target → name` 的边
- 提示 4：用于调试：如果 `entry` 的后支配集合包含 `end`，说明所有路径都必须经过 `end` 才能退出——这是正确的。但如果 `entry` 的后支配集合只有 `entry` 和 `end`，说明存在不经过其他块也能到出口的路径

**自检用例**:

```python
from toy_cfg.demo01_build_blocks import DEMOS
from toy_cfg.demo02_build_cfg import build_cfg
from toy_cfg.demo05_dominators import compute_dominators

# if_else 程序
cfg = build_cfg(DEMOS["if_else"].functions[0])
post_dom = compute_post_dominators(cfg)  # 你实现的函数
post_idom = compute_post_idom(cfg, post_dom)

# end 块后支配所有块（因为所有路径都要经过 end 才能到出口）
for name in cfg.blocks:
    assert "end" in post_dom[name], f"{name} 应该被 end 后支配"

# entry 不被 then 或 else 后支配（因为走另一条分支就不经过它们）
assert "then" not in post_dom["entry"]
assert "else" not in post_dom["entry"]

# 立即后支配：end 的 post_idom 是 None（它是虚拟出口）
# then 的 post_idom 应该是 end
assert post_idom["then"] == "end"
assert post_idom["else"] == "end"
```

---

## 延伸思考

做完以上三个练习后，可以继续挑战：

1. **支配边界（Dominance Frontier）**：结合支配树和后支配树，计算每个块的支配边界。这是构建 SSA 形式的基石
2. **循环树（Loop Tree）**：根据循环嵌套关系构建一棵树——每个循环是一个节点，父子关系表示包含关系。这对优化 pass 的排序很有用
3. **控制流归约（Control-Flow Reduction）**：把 CFG 归约为结构化控制流（if-then-else, while-loop），用于反编译或程序理解
