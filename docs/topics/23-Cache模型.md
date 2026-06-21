# Topic 23 — Cache 模型（组相联 + LRU）

> **难度**: 高级 | **源文件**: `scratchv/standalone/cache_model.py`

---

## 是什么？

Cache 模型（`cache_model.py`）模拟 **L1 指令缓存（I$）和数据缓存（D$）** 的行为。它是 RV32IM 仿真器的"附件"——每条访存指令都经过 cache 模型，统计命中/缺失次数。

```
CPU 执行指令
    ↓ 每次 fetch         ↓ 每次 load/store
┌──────────┐       ┌──────────┐
│  I$ Cache │       │  D$ Cache │
│ 64×2×32B │       │128×4×32B │
└──────────┘       └──────────┘
    ↓ miss             ↓ miss
    主内存 (无限容量，固定延迟)
```

---

## 为什么？

只统计动态指令数不够——两条指令序列可能指令数相同但 cache 行为截然不同。Cache 模型让你看到：
- 内存访问模式是否友好（空间局部性、时间局部性）
- ScratchV 和 LLVM 的缓存效率差距
- 为什么相同指令数下某个版本更快

---

## 核心概念

### 组相联 Cache 参数

| 参数 | I$ | D$ | 含义 |
|------|-----|-----|------|
| sets | 64 | 128 | 组数 |
| ways | 2 | 4 | 每组的路数（相联度） |
| block_size | 32B | 32B | 每块 8 个 32-bit 字 |
| **总容量** | **4KB** | **16KB** | sets × ways × block_size |

### 地址分解（32 位）

```
|     tag (剩余位)    | index (log2 sets) | offset (log2 block_size) |
|     20 位 (I$)      |      6 位 (64)    |        5 位 (32B)       |
```

### LRU 替换策略

每组有 `ways` 个位置。当所有位置都满了又有新数据要进来时，淘汰**最久没被访问**的那个（Least Recently Used）。

### Miss 分类

| 类型 | 含义 | 能优化吗？ |
|------|------|----------|
| **Compulsory miss** | 第一次访问某地址 | ❌ 不可避免 |
| **Conflict miss** | 不同地址映射到同一组，互相踢出 | ✅ 改数据布局 |

---

## 一步步

### 使用

```python
from scratchv.standalone.cache_model import CacheSim

# 创建 I-cache 和 D-cache
icache = CacheSim(name="I$", sets=64, ways=2, block_size=32)
dcache = CacheSim(name="D$", sets=128, ways=4, block_size=32)

# 每次取指
icache.access(addr=pc, is_read=True)

# 每次数据访问
dcache.access(addr=mem_addr, is_read=True)    # load
dcache.access(addr=mem_addr, is_read=False)   # store

# 查看统计
icache.print_stats()
dcache.print_stats()
```

输出：
```
I$: hits=3220000000, misses=16000000, hit_rate=99.50%
D$: hits=2860000000, misses=748000000, hit_rate=79.27%
```

### 指标速查

```python
stats = dcache.stats
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"Miss rate: {stats.miss_rate:.2%}")
print(f"MPKI: {stats.mpki:.1f}")     # Misses Per 1000 accesses
print(f"Compulsory: {stats.compulsory_misses}")
print(f"Conflict: {stats.conflict_misses}")
```

---

## 代码走读

### CacheLine 结构

```python
class CacheLine:
    __slots__ = ("tag", "valid", "lru")
    def __init__(self):
        self.tag: int = 0        # 地址高位
        self.valid: bool = False # 有效位（初始无效）
        self.lru: int = 0        # 最后访问时间戳
```

### access 核心逻辑

```python
def access(self, addr, is_read):
    index = (addr >> self.offset_bits) & (self.sets - 1)
    tag = addr >> (self.offset_bits + self.index_bits)

    set_lines = self.sets_lines[index]  # 该组的所有路

    # 1. 先检查是否命中
    for line in set_lines:
        if line.valid and line.tag == tag:
            line.lru = self._timestamp
            self.stats.hits += 1
            return True

    # 2. Miss — 需要替换
    self.stats.misses += 1
    # 找空位或淘汰 LRU 最老的
    victim = min(set_lines, key=lambda l: l.lru if l.valid else -1)
    if not victim.valid:
        self.stats.compulsory_misses += 1
    else:
        self.stats.conflict_misses += 1
    victim.tag = tag
    victim.valid = True
    victim.lru = self._timestamp
    return False
```

---

## 动手练习

### 练习 1: 分析 CNN 模型的 cache 行为

运行 `llvm_cache_compare.py`，查看 ScratchV 和 LLVM 的 I$/D$ 命中率差异。

### 练习 2: 调整 cache 参数

把 D$ 的 ways 从 4 改为 8，重新运行对比。命中率提升多少？

### 练习 3: 实现 FIFO 替换策略

在 CacheSim 中添加 FIFO（先进先出）替换策略，和 LRU 对比命中率差异。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **写策略** | 当前使用 write-allocate + write-back，store miss 会先加载再写 |
| **地址对齐** | Cache 按 block 对齐，32B block 意味着低 5 位地址被忽略 |
| **LRU 精度** | 时间戳实现简单但数字可能溢出（对 32 亿次访问需要 64 位） |

---

## 进阶阅读

- Hennessy & Patterson: Computer Architecture, 附录 B（Cache 原理）
- [03-指标解读指南](../03-指标解读指南.md) — 如何解读 Cache 指标
- 相关 topic: [Topic 19 — Standalone RISC-V](19-Standalone-RISC-V编译器.md) | [Topic 25 — LLVM vs ScratchV 对比](25-LLVM对比工具.md)
