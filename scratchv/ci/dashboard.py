"""Performance dashboard — LLVM baseline vs ScratchV (instruction-set focus).

Two granularities:
  1. Instruction-level (by category): ALU R/I, FP, Shift, Load, Store, Branch, Jump, Upper
  2. Operator-level (by type): Conv, Gemm, MaxPool, ReLU, Sigmoid

Removed: cycle estimates, CPI profiles, memory ops, TinyFive kernel (not needed for
instruction-level analysis).
"""

from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

PROJ = Path(__file__).resolve().parent.parent.parent
SINGLE_OP_BENCH = PROJ / "benchmark_reports" / "single_op_bench.json"


def _run(script, args):
    """Run tool, return parsed JSON."""
    tmp = None
    for i, a in enumerate(args):
        if a == "--json-output" and i + 1 < len(args):
            tmp = args[i + 1]; break
        if a == "--json" and i + 1 < len(args) and not args[i + 1].startswith("--"):
            tmp = args[i + 1]; break
    if not tmp:
        tmp = "/tmp/_bench_tmp.json"
        args = args + ["--json-output", tmp]
    subprocess.run([sys.executable, str(PROJ / script)] + args,
                   capture_output=True, cwd=str(PROJ), timeout=60)
    if os.path.exists(tmp):
        with open(tmp) as f:
            return json.load(f)
    return {}


def collect():
    """Collect LLVM vs ScratchV comparison data."""
    llvm_path = "/tmp/_llvm_bench.json"
    return _run("scratchv/standalone/llvm_cache_compare.py", ["--json-output", llvm_path])


def _f(n):
    if not n:
        return "—"
    if isinstance(n, float):
        n = int(n)
    return f"{n:,}"


def _ratio(sv, ll):
    """ScratchV / LLVM. Always appends × suffix."""
    if not ll:
        return "—"
    v = sv / ll
    return f"{v:.1f}×" if v >= 10 else f"{v:.2f}×"


def _ratio_float(sv, ll):
    """Return raw ratio float for comparisons."""
    if not ll:
        return 0
    return sv / ll


def _badge(v):
    try:
        fv = float(v.replace("×", ""))
    except (ValueError, TypeError):
        return v
    if fv <= 1.5:
        return f'<span class="badge g">{v}</span>'
    if fv <= 4:
        return f'<span class="badge y">{v}</span>'
    return f'<span class="badge r">{v}</span>'


CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;line-height:1.5}
.wrap{max-width:960px;margin:0 auto;padding:20px}
.hdr{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #334155;border-radius:12px;padding:20px 28px;margin-bottom:18px}
.hdr h1{font-size:1.15rem;color:#f1f5f9}
.hdr .sub{font-size:.75rem;color:#94a3b8;margin-top:3px}
.hdr .sub b{color:#e2e8f0}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:18px}
@media(max-width:600px){.grid2{grid-template-columns:1fr}}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;text-align:center}
.kpi .v{font-size:1.8rem;font-weight:800;color:#f59e0b}
.kpi .v.g{color:#22c55e}
.kpi .v.y{color:#f59e0b}
.kpi .v.r{color:#ef4444}
.kpi .l{font-size:.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.4px;margin-top:3px}
.kpi .d{font-size:.65rem;color:#94a3b8;margin-top:2px}
.sec{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px}
.sec h2{font-size:.9rem;font-weight:700;margin-bottom:12px;color:#f1f5f9}
.sec .sec-sub{font-size:.7rem;color:#64748b;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:.78rem}
th{background:#334155;padding:6px 10px;text-align:left;font-weight:600;color:#94a3b8;font-size:.65rem;text-transform:uppercase;letter-spacing:.3px}
td{padding:5px 10px;border-bottom:1px solid #334155}
tr:hover td{background:#1e293b}
.n{text-align:right;font-variant-numeric:tabular-nums}
.hl td{font-weight:700;background:#450a0a}
.hl td:first-child{color:#ef4444}
.ll{color:#22c55e;font-weight:600}
.badge{display:inline-block;padding:1px 7px;border-radius:6px;font-size:.65rem;font-weight:700}
.badge.r{background:#fee2e2;color:#dc2626}
.badge.y{background:#ffedd5;color:#ea580c}
.badge.g{background:#dcfce7;color:#16a34a}
.note{font-size:.68rem;color:#94a3b8;margin-top:10px;padding:10px 14px;background:#0f172a;border-radius:6px;line-height:1.6}
.hist{font-size:.68rem;color:#94a3b8;margin-top:8px;text-align:center}
.ft{text-align:center;color:#475569;font-size:.65rem;padding:16px}
.ft a{color:#64748b}
"""


# ── History ────────────────────────────────────────────────────────────
HISTORY_FILE = PROJ / "benchmark_reports" / "history.json"


def _update_history(costs: dict):
    try:
        hist = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {"runs": []}
    except Exception:
        hist = {"runs": []}
    hist["runs"].append({"ts": datetime.now(timezone.utc).isoformat(), "costs": costs})
    hist["runs"] = hist["runs"][-50:]
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(hist, indent=2))


def _history_html() -> str:
    try:
        if not HISTORY_FILE.exists():
            return ""
        hist = json.loads(HISTORY_FILE.read_text())
        runs = hist.get("runs", [])
        if len(runs) < 2:
            return (f'<div class="hist">{len(runs)} run recorded · '
                    f'<a href="history.json" style="color:#94a3b8">history.json</a></div>')
        cur = runs[-1]["costs"]
        prev = runs[-2]["costs"]

        def delta(k):
            try:
                cv = float(cur[k].replace("×", ""))
                pv = float(prev[k].replace("×", ""))
                d = cv - pv
                if abs(d) < 0.01:
                    return "—"
                return f"{'+' if d > 0 else ''}{d:.2f}"
            except Exception:
                return "?"
        return (f'<div class="hist">Δ prev → curr: insn {delta("insn")} | '
                f'static {delta("static")} · {len(runs)} runs · '
                f'<a href="history.json" style="color:#94a3b8">history.json</a></div>')
    except Exception:
        return ""


# ── SVG Operator Bar Chart ──────────────────────────────────────────────


def _op_bar_chart(aggregates: dict) -> str:
    """Generate SVG horizontal bar chart for operator-type comparison.

    Shows ScratchV/LLVM dynamic instruction ratio per operator type.
    Lower = better (target: <1.5x).
    """
    if not aggregates:
        return '<div class="note">No single-operator data available. Run `make bench-single-ops` first.</div>'

    # Sort by ratio descending
    items = sorted(aggregates.items(), key=lambda x: x[1].get("dynamic_ratio", 0), reverse=True)

    W, H = 700, 40 + len(items) * 44
    ML, MR, MT, MB = 110, 120, 10, 20
    PW = W - ML - MR
    bar_h = 24
    gap = 20

    # Find max ratio for scaling (cap at 5x)
    max_ratio = max((v.get("dynamic_ratio", 0) for _, v in items), default=1)
    chart_max = max(max_ratio * 1.2, 1.5)

    svg = f'<svg viewBox="0 0 {W} {H}" width="100%" height="auto" style="max-width:{W}px;font-family:system-ui,sans-serif">'

    y = MT
    for name, data in items:
        ratio = data.get("dynamic_ratio", 0)
        bar_w = max(ratio / chart_max * PW, 2) if ratio > 0 else 0

        # Color coding
        if ratio <= 1.5:
            color = "#22c55e"
        elif ratio <= 4:
            color = "#f59e0b"
        else:
            color = "#ef4444"

        # Label (left)
        svg += f'\n  <text x="{ML - 8}" y="{y + bar_h - 8}" text-anchor="end" fill="#e2e8f0" font-size="13" font-weight="600">{name}</text>'

        # Bar
        svg += f'\n  <rect x="{ML}" y="{y}" width="{bar_w:.0f}" height="{bar_h}" rx="4" fill="{color}" opacity="0.85"/>'

        # Ratio text on bar
        ratio_text = f"{ratio:.2f}x"
        svg += f'\n  <text x="{ML + bar_w + 6:.0f}" y="{y + bar_h - 8}" fill="{color}" font-size="12" font-weight="700">{ratio_text}</text>'

        # LLVM baseline line at 1.0x
        baseline_x = ML + (1.0 / chart_max) * PW
        if ratio > 1.0:
            svg += f'\n  <line x1="{baseline_x:.0f}" y1="{y}" x2="{baseline_x:.0f}" y2="{y + bar_h}" stroke="#22c55e" stroke-dasharray="3,3" stroke-width="1" opacity="0.5"/>'

        # Dynamic insn count (right side, small)
        sv_dyn = data.get("total_scratchv_dynamic_insns", 0)
        svg += f'\n  <text x="{ML + PW + 6}" y="{y + bar_h - 8}" fill="#64748b" font-size="10">{_f(sv_dyn)}</text>'

        y += bar_h + gap

    # Legend
    ly = y + 8
    svg += f'\n  <text x="{ML}" y="{ly}" fill="#64748b" font-size="10">Bar width = ScratchV / LLVM dynamic instruction ratio · Green &lt;1.5x · Yellow 1.5–4x · Red &gt;4x</text>'
    svg += f'\n  <text x="{ML}" y="{ly + 16}" fill="#475569" font-size="9">Green dashed line = LLVM baseline (1.0x) · Numbers on right = ScratchV dynamic instruction count</text>'

    svg += '\n</svg>'
    return svg


# ═══════════════════════════════════════════════════════════════════════


def generate(ld=None, single_op_data=None):
    if ld is None:
        ld = collect()
    ld = ld or {}

    L = ld.get("llvm", {})
    S = ld.get("scratchv", {})

    Ld = L.get("dynamic_instructions", {})
    Sd = S.get("dynamic_instructions", {})

    Lt = Ld.get("total", 0)
    St = Sd.get("total", 0)

    # Static instruction counts
    Ls = L.get("static_insns", 0)  # may be in comparison data
    Ss = S.get("static_insns", 0)

    R_insn = _ratio(St, Lt)
    R_static = "—"

    # History
    _update_history({"insn": R_insn, "static": R_static})

    # ── Build HTML ──
    h = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ScratchV · Dashboard</title><style>{CSS}</style></head><body><div class="wrap">
<div class="hdr"><h1>ScratchV vs LLVM &nbsp;·&nbsp; cnn.onnx &nbsp;·&nbsp; 3×Conv + 3×MaxPool + 2×FC</h1>
<div class="sub"><b>LLVM RV64FD (float32)</b> — baseline &nbsp;|&nbsp; <b>ScratchV RV32IM (Q16.16)</b> — target</div></div>

<div class="grid2">
<div class="kpi"><div class="v{" g" if _ratio_float(St, Lt) <= 1.5 else (" y" if _ratio_float(St, Lt) <= 4 else " r")}">{R_insn}</div><div class="l">Dynamic Instructions</div><div class="d">LLVM {_f(Lt)} · ScratchV {_f(St)}</div></div>
<div class="kpi"><div class="v y">{R_static}</div><div class="l">Static Instructions</div><div class="d">LLVM {_f(Ls)} · ScratchV {_f(Ss)}</div></div>
</div>
{_history_html()}"""

    # ── Section 1: Dynamic Instruction Distribution ──
    h += """
<div class="sec"><h2>1. Dynamic Instruction Distribution · 指令粒度</h2>
<div class="sec-sub">Per-category breakdown — identifies compilation instruction bottlenecks (e.g., excessive loads for address calc, branch overhead)</div><table>
<tr><th>Category</th><th class="n">LLVM (baseline)</th><th class="n">ScratchV</th><th class="n">ScratchV / LLVM</th></tr>"""

    rows = [
        ("ALU R-type", "alu_r", "alu_r"),
        ("ALU I-type", "alu_i", "alu_i"),
        ("FP", "fp", "fp"),
        ("Shift", "shift", "shift"),
        ("Load", "load", "load"),
        ("Store", "store", "store"),
        ("Branch", "branch", "branch"),
        ("Jump", "jump", "jump"),
        ("Upper immediate", "upper", "upper"),
    ]
    max_ratio_cat = ("", 0)
    for name, lk, sk in rows:
        lv = Ld.get(lk, 0)
        sv = Sd.get(sk, 0)
        if lv or sv:
            r = _ratio(sv, lv) if lv else "—"
            r_float = _ratio_float(sv, lv) if lv else 0
            if r_float > max_ratio_cat[1]:
                max_ratio_cat = (name, r_float)
            h += f"<tr><td>{name}</td><td class='n'><span class='ll'>{_f(lv)}</span></td><td class='n'>{_f(sv)}</td><td class='n'>{_badge(r)}</td></tr>"

    h += f"""<tr class="hl"><td><b>Total</b></td><td class='n'><b class='ll'>{_f(Lt)}</b></td><td class='n'><b>{_f(St)}</b></td><td class='n'><b>{_badge(R_insn)}</b></td></tr></table>
<div class="note"><b>Biggest bottleneck:</b> {max_ratio_cat[0]} ({max_ratio_cat[1]:.2f}x vs LLVM). "
Store ratio {_ratio(Sd.get('store', 0), Ld.get('store', 0))}: LLVM keeps accumulators in FP registers (few stores). ScratchV spills to stack every MAC due to limited registers.</div></div>"""

    # ── Section 2: Operator Granularity ──
    h += """
<div class="sec"><h2>2. Operator Comparison · 算子粒度</h2>
<div class="sec-sub">Per-operator-type dynamic instruction ratio (ScratchV / LLVM) — identifies which operator types have the most optimization headroom</div>"""

    # Load single-op benchmark data
    if single_op_data is None and SINGLE_OP_BENCH.exists():
        try:
            single_op_data = json.loads(SINGLE_OP_BENCH.read_text())
        except Exception:
            single_op_data = None

    if single_op_data:
        aggregates = single_op_data.get("aggregates", {})
        h += _op_bar_chart(aggregates)

        # Add per-model breakdown table
        models = single_op_data.get("models", {})
        if models:
            h += '<table style="margin-top:16px"><tr><th>Model</th><th>Op Type</th><th class="n">SV Static</th><th class="n">SV Dynamic</th><th class="n">LLVM Dynamic</th><th class="n">Ratio</th></tr>'
            for model_name in sorted(models.keys()):
                m = models[model_name]
                r = m.get("dynamic_ratio", 0)
                ratio_str = f"{r:.2f}x" if r else "—"
                h += f"<tr><td>{model_name}</td><td>{m['op_type']}</td><td class='n'>{m.get('scratchv_static_insns', 0)}</td><td class='n'>{_f(m.get('scratchv_dynamic_insns', 0))}</td><td class='n'>{_f(m.get('llvm_dynamic_insns', 0))}</td><td class='n'>{_badge(ratio_str)}</td></tr>"
            h += "</table>"
    else:
        h += '<div class="note">No single-operator data available. Run <code>make bench-single-ops</code> to generate per-operator benchmarks.</div>'

    h += "</div>"

    # ── Footer ──
    h += f"""
<div class="ft">ScratchV CI · LLVM RV64FD baseline · <a href="https://github.com/ScratchV-Compiler/ScratchV">GitHub</a> · <a href="history.html">Optimization History</a> · Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
</div></body></html>"""
    return h


def generate_dashboard_html(json_path="", json_data=None, embed_json=False, title="ScratchV"):
    """Backward-compatible entry point called by ci_benchmark.py."""
    ld = None
    single_op_data = None

    if json_data and isinstance(json_data, dict):
        ld = json_data
    elif json_path and os.path.exists(json_path):
        with open(json_path) as f:
            ld = json.load(f)

    # Load single-op data if available
    if SINGLE_OP_BENCH.exists():
        try:
            single_op_data = json.loads(SINGLE_OP_BENCH.read_text())
        except Exception:
            pass

    return generate(ld, single_op_data)


def main():
    import argparse
    p = argparse.ArgumentParser(description="ScratchV vs LLVM instruction dashboard")
    p.add_argument("--llvm-json", help="Path to llvm_cache_compare JSON output")
    p.add_argument("--single-op-json", default=str(SINGLE_OP_BENCH),
                   help="Path to single_op_bench.json")
    p.add_argument("-o", "--output", default="benchmark_reports/dashboard.html")
    p.add_argument("--run", action="store_true",
                   help="Auto-collect data via subprocess calls")
    a = p.parse_args()

    ld = None
    single_op_data = None

    if a.llvm_json and os.path.exists(a.llvm_json):
        with open(a.llvm_json) as f:
            ld = json.load(f)

    if os.path.exists(a.single_op_json):
        try:
            single_op_data = json.loads(open(a.single_op_json).read())
        except Exception:
            pass

    if a.run or ld is None:
        print("collecting data...", file=sys.stderr)
        ld = collect()

    html = generate(ld, single_op_data)
    os.makedirs(os.path.dirname(a.output) or ".", exist_ok=True)
    with open(a.output, "w") as f:
        f.write(html)
    print(f"→ {a.output} ({len(html):,}B)", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
