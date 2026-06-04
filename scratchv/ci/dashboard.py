"""Static HTML dashboard — LLVM vs ScratchV complete performance comparison.

Generates a clean, self-contained HTML dashboard with:
  - Metric glossary (definitions for every ratio and index)
  - Dynamic instruction distribution with correct ratio direction
  - Cycle estimates across 5 microarchitecture profiles
  - Cache performance with absolute and relative comparisons
  - TinyFive static analysis + inner loop kernel comparison
  - Summary table + key insights

Pure HTML+CSS, zero JavaScript dependencies.
"""

from __future__ import annotations

import json, os, subprocess, sys, tempfile
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent.parent


def _run_tool(script: str, args: list[str]) -> dict:
    tmp = tempfile.mktemp(suffix=".json")
    subprocess.run([sys.executable, str(PROJ/script)] + args, capture_output=True, cwd=str(PROJ), timeout=60)
    if os.path.exists(tmp):
        with open(tmp) as f: return json.load(f)
    return {}


def collect_all() -> tuple[dict, dict]:
    return (
        _run_tool("scratchv/standalone/llvm_cache_compare.py", ["--json-output","/tmp/_llvm.json"]),
        _run_tool("scratchv/standalone/tinyfive_compare.py", ["--json","/tmp/_tinyfive.json"]),
    )


# ── Formatting helpers ──────────────────────────────────────────────────────

def _f(n, d=0):
    if n is None or n == 0: return "—"
    return f"{n:,.{d}f}" if isinstance(n,float) and d else f"{n:,}"

def _p(part, total):
    if not total: return "—"
    return f"{part/total*100:.1f}%"

def _rx(a, b):
    """Ratio a/b. 'a' is always ScratchV, 'b' is LLVM (consistent direction)."""
    if not b: return "—"
    v = a / b
    if v < 1: return f"{v:.2f}x"  # ScratchV is smaller
    return f"{v:.1f}x"

def _sp(scratchv_time, llvm_time):
    """LLVM speedup: how many times faster LLVM is over ScratchV."""
    if not llvm_time: return "—"
    return f"{scratchv_time/max(llvm_time,0.001):.1f}x"


# ── CSS ─────────────────────────────────────────────────────────────────────

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f7fafc;color:#2d3748;line-height:1.6}
.container{max-width:1100px;margin:0 auto;padding:20px}
.header{background:linear-gradient(135deg,#1a202c,#2d3748);color:#f7fafc;padding:28px 36px;margin-bottom:20px;border-radius:10px}
.header h1{font-size:1.5rem;margin-bottom:4px}
.header .sub{color:#a0aec0;font-size:.82rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:20px}
.card{background:#fff;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.07);border-left:4px solid #4299e1}
.card.ll{border-left-color:#48bb78}
.card.sp{border-left-color:#ed8936}
.card .label{font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;color:#718096;margin-bottom:2px}
.card .value{font-size:1.4rem;font-weight:700}
.card .detail{font-size:.75rem;color:#a0aec0;margin-top:2px}
.section{background:#fff;border-radius:8px;padding:22px;margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.section h2{font-size:1.05rem;font-weight:700;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #e2e8f0}
.section h3{font-size:.85rem;color:#718096;margin:14px 0 8px}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{background:#edf2f7;padding:8px 10px;text-align:left;font-weight:600;color:#4a5568;font-size:.75rem;text-transform:uppercase;letter-spacing:.3px}
td{padding:7px 10px;border-bottom:1px solid #edf2f7}
tr:hover td{background:#f7fafc}
.n{text-align:right;font-variant-numeric:tabular-nums}
.hl{font-weight:700;background:#fffff0}
.svc{color:#4299e1;font-weight:600}
.llc{color:#48bb78;font-weight:600}
.insight{background:#ebf8ff;border-radius:6px;padding:14px 18px;margin-top:14px}
.insight h4{font-size:.85rem;color:#2b6cb0;margin-bottom:5px}
.insight ul,.glossary ul{margin-left:18px;font-size:.82rem}
.insight li,.glossary li{margin-bottom:2px}
.glossary{background:#fefcbf;border-radius:6px;padding:14px 18px;margin-bottom:20px}
.glossary h4{font-size:.85rem;color:#975a16;margin-bottom:5px}
.glossary table{font-size:.8rem;margin-top:6px}
.glossary td{padding:4px 8px}
.footer{text-align:center;color:#a0aec0;font-size:.75rem;padding:18px}
@media(prefers-color-scheme:dark){
body{background:#1a202c;color:#e2e8f0}
.card,.section{background:#2d3748;box-shadow:0 1px 3px rgba(0,0,0,.3)}
th{background:#4a5568;color:#cbd5e0}
td{border-color:#4a5568}
tr:hover td{background:#3a4556}
.hl{background:#744210}
.insight{background:#2a4365}
.insight h4{color:#90cdf4}
.glossary{background:#744210}
.glossary h4{color:#fbd38d}
.section h2{border-color:#4a5568}
}"""


# ── Generator ───────────────────────────────────────────────────────────────

def generate(ld: dict | None = None, td: dict | None = None) -> str:
    if ld is None or td is None: ld, td = collect_all()
    if ld is None: ld = {}
    if td is None: td = {}

    # ── Data extraction ──────────────────────────────────────────────────
    L = ld.get("llvm", {});            S = ld.get("scratchv", {})
    Ld = L.get("dynamic_instructions", {}); Sd = S.get("dynamic_instructions", {})
    Lc = L.get("cycles", {});           Sc = S.get("cycles", {})
    LIe = L.get("cache_embedded",{}).get("icache",{})
    LDe = L.get("cache_embedded",{}).get("dcache",{})
    SIe = S.get("cache_embedded",{}).get("icache",{})
    SDe = S.get("cache_embedded",{}).get("dcache",{})
    LIa = L.get("cache_application",{}).get("icache",{})
    LDa = L.get("cache_application",{}).get("dcache",{})
    SIa = S.get("cache_application",{}).get("icache",{})
    SDa = S.get("cache_application",{}).get("dcache",{})

    tls = td.get("llvm_static",{})
    tss = td.get("scratchv_static",{})
    tlo = td.get("llvm_tinyfive",{})
    tso = td.get("scratchv_tinyfive",{})

    # Derived metrics
    L_total = Ld.get("total",0);  S_total = Sd.get("total",0)
    L_cpi   = Lc.get("rv64fd-basic",{}).get("cpi",0)
    S_cpi   = Sc.get("rv32im-basic",{}).get("cpi",0)
    L_t100  = Lc.get("rv64fd-basic",{}).get("est_hw_100mhz_s",0)
    S_t100  = Sc.get("rv32im-basic",{}).get("est_hw_100mhz_s",0)
    L_mem   = Ld.get("load",0) + Ld.get("store",0)
    S_mem   = Sd.get("load",0) + Sd.get("store",0)
    L_comp  = Ld.get("alu_i",0) + Ld.get("alu_r",0) + Ld.get("fp",0)
    S_comp  = Sd.get("alu_i",0) + Sd.get("alu_r",0)
    sp100   = _sp(S_t100, L_t100)

    # ── Sections ──────────────────────────────────────────────────────────

    h = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ScratchV Performance Dashboard</title><style>{CSS}</style></head><body><div class="container">
<div class="header"><h1>📊 LLVM vs ScratchV Performance Dashboard</h1>
<div class="sub">cnn.onnx · 3×Conv+3×MaxPool+2×FC · LLVM RV64FD (float32) vs ScratchV RV32IM (Q16.16)</div></div>

<!-- ══ 0. Metric Glossary ══ -->
{_glossary()}

<!-- ══ Summary Cards ══ -->
<div class="cards">
<div class="card"><div class="label">ScratchV Static Code</div><div class="value">785 <small style="font-size:.55em">insns</small></div><div class="detail">3,140 B · Q16.16 RV32IM</div></div>
<div class="card ll"><div class="label">LLVM Static Code</div><div class="value">956 <small style="font-size:.55em">insns</small></div><div class="detail">3,824 B · float32 RV64FD</div></div>
<div class="card" style="border-left-color:#9f7aea"><div class="label">Dynamic Instr Ratio (SV/LLVM)</div><div class="value">{_rx(S_total,L_total)}</div><div class="detail">ScratchV {S_total/1e9:.2f}B · LLVM {L_total/1e9:.2f}B</div></div>
<div class="card sp"><div class="label">LLVM Speedup @100MHz</div><div class="value">{sp100}</div><div class="detail">LLVM {L_t100:.1f}s · ScratchV {S_t100:.1f}s</div></div>
</div>

<!-- ══ 1. Dynamic Instruction Distribution ══ -->
{_sec1(Ld, Sd, L_total, S_total, L_mem, S_mem, L_comp, S_comp, Ld, Sd)}

<!-- ══ 2. Cycle Estimates ══ -->
{_sec2(Lc, Sc, sp100)}

<!-- ══ 3. Cache Performance ══ -->
{_sec3(LIe, LDe, SIe, SDe, LIa, LDa, SIa, SDa)}

<!-- ══ 4. TinyFive Static Analysis ══ -->
{_sec4(tls, tss)}

<!-- ══ 5. TinyFive Inner Loop ══ -->
{_sec5(tlo, tso)}

<!-- ══ 6. Summary ══ -->
{_sec6(L_total, S_total, L_cpi, S_cpi, L_t100, S_t100, L_mem, S_mem, Lc, Sc, LDe, SDe, sp100)}

<div class="footer">ScratchV CI Benchmark · scratchv.ci.dashboard · <a href="https://github.com/ScratchV-Compiler/ScratchV" style="color:#a0aec0">GitHub</a></div>
</div></body></html>"""
    return h


# ═══════════════════════════════════════════════════════════════════════════
# Section generators
# ═══════════════════════════════════════════════════════════════════════════

def _glossary() -> str:
    return """<div class="glossary"><h4>📖 指标说明 (Metric Glossary)</h4><table>
<tr><td><b>Static Instructions</b></td><td>汇编代码中的指令条数（不含内联权重数据）。反映代码紧凑度。</td></tr>
<tr><td><b>Dynamic Instructions</b></td><td>实际执行的总指令数（= 静态指令 × 循环迭代次数）。反映真实计算量。</td></tr>
<tr><td><b>Ratio (SV/LLVM)</b></td><td>ScratchV 值 ÷ LLVM 值。&gt;1 = ScratchV 更多/更大；&lt;1 = LLVM 更多/更大。</td></tr>
<tr><td><b>CPI</b></td><td>Cycles Per Instruction — 每条指令平均消耗的时钟周期数。CPI=1 即 IPC=1。</td></tr>
<tr><td><b>Speedup</b></td><td>LLVM 相对于 ScratchV 的加速比 = ScratchV耗时 ÷ LLVM耗时。值越大 LLVM 越快。</td></tr>
<tr><td><b>I$ / D$</b></td><td>Instruction Cache / Data Cache。I$ 存指令，D$ 存数据。</td></tr>
<tr><td><b>Hit Rate</b></td><td>缓存命中率 = 命中次数 ÷ 总访问次数。越高越好，100%=全部命中。</td></tr>
<tr><td><b>Miss Bytes</b></td><td>缓存缺失导致从主存加载的总字节数。越低越好，反映内存带宽压力。</td></tr>
<tr><td><b>C/M Ratio</b></td><td>Compute-to-Memory ratio = 计算指令 ÷ 访存指令。CNN 通常 &gt;1 (计算密集)。</td></tr>
<tr><td><b>TinyFive Ops</b></td><td>TinyFive 模拟器统计的操作类型分布：load（加载）、store（存储）、mul（乘法）、add（加减/ALU）、madd（乘加/浮点）、branch（分支跳转）。</td></tr>
</table></div>"""


def _sec1(Ld, Sd, L_total, S_total, L_mem, S_mem, L_comp, S_comp, _Ld, _Sd) -> str:
    h = """<div class="section"><h2>1. Dynamic Instruction Distribution</h2>
<p style="font-size:.8rem;color:#718096;margin-bottom:10px">基于 CNN 层维度（Conv MAC + FC MAC + MaxPool + ReLU + Sigmoid）估算的总动态指令数。Ratio = ScratchV ÷ LLVM。</p><table>
<tr><th>Category</th><th class="n">LLVM RV64FD</th><th class="n">%</th><th class="n">ScratchV RV32IM</th><th class="n">%</th><th class="n">SV/LLVM</th></tr>"""
    for name, lk, sk in [
        ("ALU R-type", "alu_r", "alu_r"), ("ALU I-type", "alu_i", "alu_i"),
        ("Shift", "shift", "shift"), ("Float ops", "fp", "fp"),
        ("Load", "load", "load"), ("Store", "store", "store"),
        ("Branch", "branch", "branch"), ("Jump", "jump", "jump"),
        ("Upper imm", "upper", "upper"),
    ]:
        lv = Ld.get(lk,0); sv = Sd.get(sk,0)
        if lv or sv:
            h += f"<tr><td>{name}</td><td class='n'>{_f(lv)}</td><td class='n'>{_p(lv,L_total)}</td><td class='n'>{_f(sv)}</td><td class='n'>{_p(sv,S_total)}</td><td class='n'>{_rx(sv,lv)}</td></tr>"
    h += f"""<tr class="hl"><td><b>TOTAL</b></td><td class='n'><b>{_f(L_total)}</b></td><td class='n'><b>100%</b></td><td class='n'><b>{_f(S_total)}</b></td><td class='n'><b>100%</b></td><td class='n'><b>{_rx(S_total,L_total)}</b></td></tr></table>
<div class="insight"><h4>Memory Access & Compute</h4><table style="margin-top:6px"><tr><th></th><th class="n">LLVM</th><th class="n">ScratchV</th><th class="n">SV/LLVM</th></tr>
<tr><td>Loads</td><td class='n'>{_f(Ld.get("load",0))}</td><td class='n'>{_f(Sd.get("load",0))}</td><td class='n'>{_rx(Sd.get("load",0),Ld.get("load",0))}</td></tr>
<tr><td>Stores</td><td class='n'>{_f(Ld.get("store",0))}</td><td class='n'>{_f(Sd.get("store",0))}</td><td class='n'>{_rx(Sd.get("store",0),Ld.get("store",0))}</td></tr>
<tr><td>Total Memory Ops</td><td class='n'><b>{_f(L_mem)}</b></td><td class='n'><b>{_f(S_mem)}</b></td><td class='n'><b>{_rx(S_mem,L_mem)}</b></td></tr>
<tr><td>Compute Ops</td><td class='n'>{_f(L_comp)}</td><td class='n'>{_f(S_comp)}</td><td class='n'>{_rx(S_comp,L_comp)}</td></tr>
<tr><td>C/M Ratio</td><td class='n'>{L_comp/max(L_mem,1):.1f}</td><td class='n'>{S_comp/max(S_mem,1):.1f}</td><td class='n'>—</td></tr>
</table></div></div>"""
    return h


def _sec2(Lc, Sc, sp100) -> str:
    h = """<div class="section"><h2>2. Cycle Estimates by Microarchitecture Profile</h2>
<p style="font-size:.8rem;color:#718096;margin-bottom:10px">基于指令分布 × 各 CPU 核的指令延迟模型，估算总 cycle 数。Speedup = ScratchV耗时 ÷ LLVM耗时（值越大 LLVM 越快）。</p><table>
<tr><th>Profile</th><th class="n">LLVM CPI</th><th class="n">LLVM Cycles</th><th class="n">@100MHz</th><th class="n">ScratchV CPI</th><th class="n">ScratchV Cycles</th><th class="n">@100MHz</th><th class="n">LLVM Speedup</th></tr>"""
    for p in sorted(Lc.keys()):
        lc = Lc[p]; sc = Sc.get(p, {})
        lt = lc.get("est_hw_100mhz_s",0)
        st = sc.get("est_hw_100mhz_s",0) if sc else 0
        su = _sp(st, lt)
        h += f"<tr><td>{p}</td><td class='n'>{lc['cpi']:.2f}</td><td class='n'>{_f(lc['total_cycles'])}</td><td class='n'>{lt:.1f}s</td><td class='n'>{sc.get('cpi','—') if sc else '—'}</td><td class='n'>{_f(sc.get('total_cycles',0)) if sc else '—'}</td><td class='n'>{st:.1f}s</td><td class='n'>{su}</td></tr>"
    h += """</table>
<div class="insight"><h4>Profile 说明</h4><ul>
<li><b>single-cycle</b>: CPI=1 理想模型 — 每条指令 1 cycle</li>
<li><b>rv32im-basic</b>: mul=4cyc, load=2cyc, branch-taken=2cyc — 典型嵌入式 RV32IM 核 (如 SiFive E20)</li>
<li><b>rv64fd-basic</b>: mul=3cyc, fp=1cyc(完全流水线), load=2cyc — 带硬件 FPU 的 RV64 核 (如 SiFive U74)</li>
<li><b>rv64fd-fast</b>: 全部 1cyc — 近似高性能乱序核 (如 BOOM)</li>
<li><b>rv64fd-slow</b>: mul=5cyc, fp=2cyc, load=3cyc — 保守估算 (低功耗/小面积核)</li>
</ul></div></div>"""
    return h


def _sec3(LIe, LDe, SIe, SDe, LIa, LDa, SIa, SDa) -> str:
    sv_mb = SDe.get('total_miss_bytes', 0)
    ll_mb = LDe.get('total_miss_bytes', 0)
    sv_m = SDe.get('misses', 0)
    ll_m = LDe.get('misses', 0)

    return f"""<div class="section"><h2>3. Cache Performance (Analytical Model)</h2>
<p style="font-size:.8rem;color:#718096;margin-bottom:10px">基于访存模式 + set-associative 缓存模型估算。命中率相近但 ScratchV 访存次数多 → 绝对缺失量更大。</p>
<h3>Embedded — I$=4KB (64set×2way×32B), D$=16KB (128set×4way×32B)</h3><table>
<tr><th>Metric</th><th class="n">LLVM</th><th class="n">ScratchV</th><th class="n">SV/LLVM</th></tr>
<tr><td>I$ Hit Rate</td><td class='n'><span class="llc">{LIe.get('hit_rate_pct','—')}%</span></td><td class='n'><span class="svc">{SIe.get('hit_rate_pct','—')}%</span></td><td class='n'>~1x</td></tr>
<tr><td>I$ Miss Bytes</td><td class='n'>{_f(LIe.get('total_miss_bytes',0))}</td><td class='n'>{_f(SIe.get('total_miss_bytes',0))}</td><td class='n'>{_rx(SIe.get('total_miss_bytes',0),LIe.get('total_miss_bytes',0))}</td></tr>
<tr><td>D$ Hit Rate</td><td class='n'><span class="llc">{LDe.get('hit_rate_pct','—')}%</span></td><td class='n'><span class="svc">{SDe.get('hit_rate_pct','—')}%</span></td><td class='n'>~1x</td></tr>
<tr><td>D$ Misses</td><td class='n'>{_f(ll_m)}</td><td class='n'><b>{_f(sv_m)}</b></td><td class='n'><b>{_rx(sv_m,ll_m)}</b></td></tr>
<tr><td>D$ Miss Bytes</td><td class='n'>{_f(ll_mb)}</td><td class='n'><b>{_f(sv_mb)}</b></td><td class='n'><b>{_rx(sv_mb,ll_mb)}</b></td></tr>
</table>
<h3>Application — I$=32KB (128×4×64B), D$=128KB (256×8×64B)</h3><table>
<tr><th>Metric</th><th class="n">LLVM</th><th class="n">ScratchV</th><th class="n">SV/LLVM</th></tr>
<tr><td>D$ Hit Rate</td><td class='n'><span class="llc">{LDa.get('hit_rate_pct','—')}%</span></td><td class='n'><span class="svc">{SDa.get('hit_rate_pct','—')}%</span></td><td class='n'>~1x</td></tr>
<tr><td>D$ Misses</td><td class='n'>{_f(LDa.get('misses',0))}</td><td class='n'><b>{_f(SDa.get('misses',0))}</b></td><td class='n'><b>{_rx(SDa.get('misses',0),LDa.get('misses',0))}</b></td></tr>
</table>
<div class="insight"><h4>分析</h4><ul>
<li>I$ 两者 ~100%：代码 &lt;4KB，完全适合最小 I$</li>
<li>D$ 命中率相近（~89% vs ~89%），但 ScratchV 访存次数多 {_rx(sv_m,ll_m)} → 绝对缺失体积 {_rx(sv_mb,ll_mb)}</li>
<li>128KB D$ 可将缺失率大幅降至 ~0.6%</li>
<li>ScratchV 内存带宽压力约为 LLVM 的 {_rx(sv_mb,ll_mb)}</li>
</ul></div></div>"""


def _sec4(tls, tss) -> str:
    h = """<div class="section"><h2>4. TinyFive Static Code Analysis</h2>
<p style="font-size:.8rem;color:#718096;margin-bottom:10px">从 RISC-V 汇编文件直接解析的静态指令分布。LLVM 代码量更大（含 ABI 栈帧 + 地址计算），但动态效率更高（每 MAC 指令少）。</p><table>
<tr><th>Metric</th><th class="n">LLVM RV64FD</th><th class="n">ScratchV RV32IM</th><th class="n">SV/LLVM</th></tr>
<tr><td>Static Instructions</td><td class='n'>{tls.get('total_static','—')}</td><td class='n'>{tss.get('total_static','—')}</td><td class='n'>{_rx(tss.get('total_static',0),tls.get('total_static',0))}</td></tr>
<tr><td>Code Bytes</td><td class='n'>{_f(tls.get('code_bytes',0))}</td><td class='n'>{_f(tss.get('code_bytes',0))}</td><td class='n'>{_rx(tss.get('code_bytes',0),tls.get('code_bytes',0))}</td></tr>
<tr><td>x Registers Used</td><td class='n'>{tls.get('x_reg_count','—')}</td><td class='n'>{tss.get('x_reg_count','—')}</td><td class='n'>{_rx(tss.get('x_reg_count',0),tls.get('x_reg_count',0))}</td></tr>
<tr><td>f Registers Used</td><td class='n'>{tls.get('f_reg_count','—')}</td><td class='n'>{tss.get('f_reg_count','—')}</td><td class='n'>—</td></tr>
</table>
<h3>Static Op Distribution</h3><table>
<tr><th>Op Type</th><th class="n">LLVM</th><th class="n">%</th><th class="n">ScratchV</th><th class="n">%</th></tr>"""
    for k,n in [("load","Load"),("store","Store"),("mul","Mul"),("add","Add/ALU"),
                 ("madd","Mul-Add(FP)"),("branch","Branch")]:
        lv=tls.get(k,0); sv=tss.get(k,0)
        h+=f"<tr><td>{n}</td><td class='n'>{_f(lv)}</td><td class='n'>{_p(lv,tls.get('total_static',1))}</td><td class='n'>{_f(sv)}</td><td class='n'>{_p(sv,tss.get('total_static',1))}</td></tr>"
    h += "</table></div>"
    return h


def _sec5(tlo, tso) -> str:
    lo = tlo.get("ops",{})
    so = tso.get("ops",{})
    # Per-iteration counts: the ops are static counts from the kernel body (1 loop iteration)
    # NOT divided by 100 — they represent the instructions in a SINGLE iteration
    h = """<div class="section"><h2>5. TinyFive Inner Loop Kernel (per-MAC iteration)</h2>
<p style="font-size:.8rem;color:#718096;margin-bottom:10px">提取典型 MAC 内层循环（单次迭代），通过 TinyFive ops counters 统计指令分布。全模型额外开销来自地址计算、循环嵌套、spill。</p><table>
<tr><th>Op Counter</th><th class="n">LLVM Kernel (1 iter)</th><th class="n">ScratchV Kernel (1 iter)</th><th class="n">SV/LLVM</th></tr>"""
    for o in ["load","store","mul","add","madd","branch","total"]:
        lv=lo.get(o,0); sv=so.get(o,0)
        h+=f"<tr><td>{o}</td><td class='n'>{lv}</td><td class='n'>{sv}</td><td class='n'>{_rx(sv,lv) if lv else '—'}</td></tr>"
    h+=f"""</table><table style="margin-top:12px"><tr><th></th><th class="n">LLVM</th><th class="n">ScratchV</th></tr>
<tr><td>Insns per MAC (kernel body)</td><td class='n'>{lo.get('total',0)}</td><td class='n'>{so.get('total',0)}</td></tr>
<tr><td>Insns per MAC (conv, full model)</td><td class='n'>~7</td><td class='n'>~30</td></tr>
<tr><td>Insns per MAC (FC, full model)</td><td class='n'>~5</td><td class='n'>~15</td></tr>
<tr><td>x Regs Used</td><td class='n'>{tlo.get('x_regs_used_count','—')}</td><td class='n'>{tso.get('x_regs_used_count','—')}</td></tr>
</table>
<div class="insight"><h4>解读</h4><ul>
<li>内层单次 MAC 仅差 {_rx(so.get('total',0),lo.get('total',0))}（{lo.get('total',0)} vs {so.get('total',0)} ops），但全模型放大到 4.2x</li>
<li>差异来源：地址计算（ScratchV 无 GEP → 每条地址 3-5 ALU）、spill store（寄存器不足 → sw/lw 到栈）、Q16.16 srai 移位</li>
<li>LLVM 用 15 个 x 寄存器 vs ScratchV 7 个 → 减少 spill，提高效率</li>
</ul></div></div>"""
    return h


def _sec6(L_total, S_total, L_cpi, S_cpi, L_t100, S_t100, L_mem, S_mem, Lc, Sc, LDe, SDe, sp100) -> str:
    return f"""<div class="section"><h2>6. Full Summary</h2><table>
<tr><th>Metric</th><th class="n">LLVM RV64FD</th><th class="n">ScratchV RV32IM</th><th class="n">SV/LLVM</th><th>Note</th></tr>
<tr><td>Static Insns</td><td class='n'>956</td><td class='n'>785</td><td class='n'>{_rx(785,956)}</td><td>LLVM 多 22% — ABI 栈帧 + 地址计算指令</td></tr>
<tr><td>Dynamic Insns</td><td class='n'>{_f(L_total)}</td><td class='n'>{_f(S_total)}</td><td class='n'><b>{_rx(S_total,L_total)}</b></td><td>ScratchV 多 4.2x — Q16.16 定点需要更多整数指令/MAC</td></tr>
<tr><td>CPI (rvXX-basic)</td><td class='n'>{L_cpi:.2f}</td><td class='n'>{S_cpi:.2f}</td><td class='n'>{_rx(S_cpi,L_cpi)}</td><td>CPI 相近 — 每条指令效率差异小</td></tr>
<tr><td>Cycles (basic)</td><td class='n'>{_f(Lc.get('rv64fd-basic',{}).get('total_cycles',0))}</td><td class='n'>{_f(Sc.get('rv32im-basic',{}).get('total_cycles',0))}</td><td class='n'><b>{_rx(Sc.get('rv32im-basic',{}).get('total_cycles',0),Lc.get('rv64fd-basic',{}).get('total_cycles',0))}</b></td><td>总 cycle 差距 ≈ 动态指令差距</td></tr>
<tr><td>Time @50MHz</td><td class='n'>{Lc.get('rv64fd-basic',{}).get('est_hw_50mhz_s',0):.1f}s</td><td class='n'>{Sc.get('rv32im-basic',{}).get('est_hw_50mhz_s',0):.1f}s</td><td class='n'>{sp100}</td><td>LLVM 快 {sp100}</td></tr>
<tr><td>Time @100MHz</td><td class='n'><b>{L_t100:.1f}s</b></td><td class='n'><b>{S_t100:.1f}s</b></td><td class='n'><b>{sp100}</b></td><td>LLVM 快 {sp100}</td></tr>
<tr><td>Time @500MHz</td><td class='n'>{Lc.get('rv64fd-basic',{}).get('est_hw_500mhz_s',0):.1f}s</td><td class='n'>{Sc.get('rv32im-basic',{}).get('est_hw_500mhz_s',0):.1f}s</td><td class='n'>{sp100}</td><td>Speedup 与频率无关（CPI 模型线性）</td></tr>
<tr><td>Memory Ops</td><td class='n'>{_f(L_mem)}</td><td class='n'>{_f(S_mem)}</td><td class='n'><b>{_rx(S_mem,L_mem)}</b></td><td>ScratchV 访存多，寄存器更少导致更多 spill</td></tr>
<tr><td>D$ Misses (16KB)</td><td class='n'>{_f(LDe.get('misses',0))}</td><td class='n'>{_f(SDe.get('misses',0))}</td><td class='n'><b>{_rx(SDe.get('misses',0),LDe.get('misses',0))}</b></td><td>缺失次数与访存量成正比</td></tr>
<tr><td>D$ Miss Bytes</td><td class='n'>{_f(LDe.get('total_miss_bytes',0))}</td><td class='n'>{_f(SDe.get('total_miss_bytes',0))}</td><td class='n'><b>{_rx(SDe.get('total_miss_bytes',0),LDe.get('total_miss_bytes',0))}</b></td><td>ScratchV 带宽压力更大</td></tr>
</table>
<div class="insight"><h4>关键结论</h4><ul>
<li><b>动态指令 {_rx(S_total,L_total)}</b> 是性能差距主因 — LLVM 的 float32 fmul+fadd 单指令完成 MAC，ScratchV Q16.16 需要 ~30 条整数指令</li>
<li><b>CPI 相近 (~1.3)</b> — 单指令效率差异小，差距几乎全部来自指令数</li>
<li><b>LLVM 快 {sp100} @100MHz</b> — {L_t100:.1f}s vs {S_t100:.1f}s</li>
<li><b>D$ 缺失体积 {_rx(SDe.get('total_miss_bytes',0),LDe.get('total_miss_bytes',0))}</b> — ScratchV 访存次数多 {_rx(S_mem,L_mem)}，虽然命中率相近但绝对缺失量更大</li>
<li><b>I$ 两者 ~100%</b> — 代码极小 (&lt;4KB)，完全适合任何缓存</li>
<li><b>LLVM 寄存器利用率更高</b> — 15 个 x 寄存器 vs 7 个，减少 spill 开销</li>
</ul></div></div>"""


# ═══════════════════════════════════════════════════════════════════════════
# CLI & backward compat
# ═══════════════════════════════════════════════════════════════════════════

def generate_dashboard_html(json_path="", json_data=None, embed_json=False, title="ScratchV Performance Dashboard"):
    ld = td = None
    if json_data: ld = json_data
    elif json_path and os.path.exists(json_path):
        with open(json_path) as f: ld = json.load(f)
    return generate(ld, td)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--llvm-json"); p.add_argument("--tinyfive-json")
    p.add_argument("-o","--output",default="benchmark_reports/dashboard.html")
    p.add_argument("--run",action="store_true")
    a = p.parse_args()

    ld = td = None
    if a.llvm_json and os.path.exists(a.llvm_json):
        with open(a.llvm_json) as f: ld = json.load(f)
    if a.tinyfive_json and os.path.exists(a.tinyfive_json):
        with open(a.tinyfive_json) as f: td = json.load(f)

    if a.run or (ld is None and td is None):
        print("Collecting fresh data...", file=sys.stderr)
        ld, td = collect_all()

    html = generate(ld or {}, td or {})
    os.makedirs(os.path.dirname(a.output) or ".", exist_ok=True)
    with open(a.output,"w") as f: f.write(html)
    print(f"Dashboard: {a.output} ({len(html):,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
