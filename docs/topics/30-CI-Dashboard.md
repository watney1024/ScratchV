# 课题30：CI 基准编排 + Dashboard

> **难度**：高 | **类型**：参考分析 | **源文件**：`scratchv/ci/ci_benchmark.py`, `scratchv/ci/dashboard.py`
> **状态**：✅ 已完成

---

## 概述

CI 基准系统自动运行 ScratchV vs LLVM 的性能对比，生成纯静态 HTML 仪表盘。Dashboard 展示静态/动态指令数对比、缓存命中率、趋势折线图，是评估 ScratchV 编译优化进展的核心可视化工具。

---

## 理解背景

### 是什么？

CI 基准系统自动运行 ScratchV vs LLVM 的性能对比，生成**纯静态 HTML 仪表盘**，展示：

- **静态指令数对比**：按算子和指令类别拆分
- **动态指令数对比**：带百分比差异
- **缓存命中率 & 缺失字节**
- **趋势折线图**（history.html）：历次提交的性能变化
- **综合评分**：绿/黄/红 badge 标记差距大小

```
make bench-ci
    │
    ├─→ ci_benchmark.py     ← 编排器：运行 LLVM 对比 + TinyFive 对比
    │       ├─→ llvm_cache_compare.py
    │       └─→ tinyfive_compare.py
    │
    └─→ dashboard.py        ← 可视化：JSON → HTML dashboard
            └─→ benchmark_reports/dashboard.html (纯静态, 零依赖)
```

### 为什么？

- **持续监控**：每次 push 自动运行，防止性能衰退
- **决策依据**：优化是否有效？数据说话
- **可视化**：好看的图表比一页数字更有说服力

### 核心概念

#### 两层粒度

| 层级 | 维度 | 用途 |
|------|------|------|
| **指令级** | 按类别：ALU, FP, Load, Store, Branch, Jump | 了解哪类指令是瓶颈 |
| **算子级** | 按类型：Conv, Gemm, MaxPool, ReLU, Sigmoid | 了解哪个算子差距最大 |

#### Badge 评分

```python
def _badge(ratio):
    if ratio <= 1.5:   return '<span class="badge g">'  # 绿色：接近 LLVM
    elif ratio <= 4:   return '<span class="badge y">'  # 黄色：有差距
    else:              return '<span class="badge r">'  # 红色：差距大
```

ScratchV/LLVM 比值越低越好（目标是 ≤1.0，即超越 LLVM）。

#### 数据流

```
llvm_cache_compare.py → llvm_vs_scratchv.json
tinyfive_compare.py   → tinyfive_compare.json
                              │
                     dashboard.py
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
         dashboard.html              history.html
         (静态指令+Cache)            (趋势折线图)
```

---

## 理解要点

1. 理解 CI 基准编排的完整流程：llvm_cache_compare → tinyfive_compare → dashboard
2. 掌握 Dashboard 的两层粒度（指令级 / 算子级）和 Badge 评分标准
3. 能够独立运行 `make bench-ci` 并解读 dashboard.html 中的各项指标
4. 理解纯静态 HTML 的生成方式（CSS 内嵌，零外部依赖，可直接托管 GitHub Pages）
5. 了解 history.html 的趋势追踪机制

---

## 交付产物

- 一次完整的 `make bench-ci` 运行输出（dashboard.html + history.html）
- Dashboard 指标解读笔记（标注各项指标的含义和当前 ScratchV vs LLVM 差距）
- 至少一个自定义指标的实验（修改 dashboard.py 添加新列）

---

## 代码走读

### ci_benchmark.py 编排

```python
def run_ci():
    # 1. LLVM 对比
    subprocess.run([
        "python", "scratchv/standalone/llvm_cache_compare.py",
        "--json-output", "llvm_vs_scratchv.json",
    ])
    # 2. TinyFive 对比
    subprocess.run([
        "python", "scratchv/standalone/tinyfive_compare.py",
        "--json", "tinyfive_compare.json",
    ])
    # 3. 生成 Dashboard
    subprocess.run([
        "python", "scratchv/ci/dashboard.py",
        "--llvm-json", "llvm_vs_scratchv.json",
        "--tinyfive-json", "tinyfive_compare.json",
        "-o", "dashboard.html",
    ])
```

### dashboard.py 数据收集

```python
def collect():
    return _run("scratchv/standalone/llvm_cache_compare.py",
                ["--json-output", "/tmp/_llvm_bench.json"])

def _ratio(sv, ll):
    """ScratchV / LLVM"""
    v = sv / ll
    return f"{v:.1f}×" if v >= 10 else f"{v:.2f}×"
```

### HTML 生成（纯静态）

Dashboard 输出的是**纯静态 HTML**——零外部依赖，CSS 内嵌，直接用浏览器打开即可。无需 Web 服务器，可托管到 GitHub Pages。

---

## 动手练习

### 练习 1: 生成自己的 Dashboard

运行 `make bench-ci`，打开 `dashboard.html`，找出 ScratchV 和 LLVM 差距最大的算子和指令类别。

### 练习 2: 添加新指标

在 `dashboard.py` 中添加一个新指标列（比如"每 MAC 指令数"），重新生成 dashboard。

### 练习 3: 自定义样式

修改 `dashboard.py` 中的 `CSS` 变量，改变 dashboard 的颜色主题。

---

## 常见坑

| 坑 | 说明 |
|----|------|
| **CI 超时** | `bench-ci` 可能运行较久（TinyFive 仿真慢），CI 要设置足够的 timeout（当前 20min） |
| **JSON 缓存** | 如果之前的 JSON 文件存在，dashboard 可能用旧数据。`make bench-ci` 默认 `--skip-cache` |
| **Python 版本** | CI 固定用 Python 3.12，本地开发如果用其他版本可能结果略有差异 |

---

## 进阶阅读

- [03-指标解读指南](../03-指标解读指南.md) — 如何解读 Dashboard 中的数据
- GitHub Actions 文档：[Workflow syntax](https://docs.github.com/en/actions/writing-workflows)
- 相关 topic: [课题6 — 性能基准套件](06-性能基准套件.md) | [课题19 — Standalone RISC-V](19-Standalone-RISC-V编译器.md)

---

## 自学路线

- **第 1 周**：运行 `make bench-ci`，打开生成的 `dashboard.html` 和 `history.html`。逐项理解每个指标的含义（静态指令、动态指令、I$/D$ 命中率、MPKI）。对照 [03-指标解读指南](../03-指标解读指南.md) 做笔记。
- **第 2 周**：阅读 `ci_benchmark.py` 和 `dashboard.py` 源码。理解编排逻辑（如何依次运行对比工具）和数据收集→HTML 生成的流程。画出数据流图。
- **第 3 周**：为 Dashboard 添加一个新指标（如"每个算子的代码体积"或"寄存器溢出次数"）。修改 `dashboard.py` 的数据收集和 HTML 生成逻辑。
- **第 4 周**：研究 GitHub Actions CI workflow（`.github/workflows/ci.yml`），理解 `bench-ci` 在 CI 中的触发条件和超时配置。尝试在本地模拟 CI 环境运行完整的 bench-ci 流程。
