"""Generate ScratchV optimization history page with version comparison.

Features:
  - Interactive SVG chart: select versions via checkboxes to compare
  - Expandable milestone cards with per-version instruction breakdown
  - Dark theme, zero external dependencies (vanilla JS only)
"""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from datetime import datetime

PROJ = Path(__file__).resolve().parent.parent.parent
HISTORY_FILE = PROJ / "benchmark_reports" / "optimization_history.json"
OUTPUT_FILE = PROJ / "benchmark_reports" / "history.html"

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;line-height:1.6}
.wrap{max-width:960px;margin:0 auto;padding:24px 20px}
h1{font-size:1.4rem;font-weight:800;color:#f8fafc}
h2{font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:12px}
.sub{font-size:.75rem;color:#64748b;margin-top:4px}
.header{background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #334155;border-radius:12px;padding:24px 28px;margin-bottom:24px}
.header h1{margin-bottom:4px}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:24px}
@media(max-width:700px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px 16px;text-align:center}
.kpi .v{font-size:1.6rem;font-weight:800}
.kpi .v.g{color:#22c55e}.kpi .v.r{color:#ef4444}.kpi .v.y{color:#f59e0b}
.kpi .l{font-size:.65rem;color:#64748b;text-transform:uppercase;letter-spacing:.4px;margin-top:2px}

/* ── Chart ── */
.chart-section{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px 20px 16px;margin-bottom:24px}
.chart-section h2{margin-bottom:4px}
.chart-section .chart-sub{font-size:.7rem;color:#64748b;margin-bottom:16px}
.chart-container{width:100%;overflow-x:auto}
.chart-legend{display:flex;gap:20px;flex-wrap:wrap;justify-content:center;margin-top:12px;font-size:.72rem;color:#94a3b8}
.chart-legend .leg-item{display:flex;align-items:center;gap:6px}
.chart-legend .leg-line{width:24px;height:2px;border-radius:1px}
.chart-legend .leg-dot{width:8px;height:8px;border-radius:50%}

/* ── Version selector ── */
.version-selector{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:16px}
.version-selector label.vs-label{display:flex;align-items:center;gap:5px;font-size:.72rem;color:#cbd5e1;cursor:pointer;padding:4px 10px;border-radius:4px;background:#0f172a;border:1px solid #334155;user-select:none}
.version-selector label.vs-label:hover{border-color:#475569}
.version-selector label.vs-label.checked{border-color:#f59e0b;background:#1e293b}
.version-selector label:not(.vs-label){font-size:.65rem;color:#64748b;cursor:pointer;padding:4px 6px}
.version-selector label:not(.vs-label):hover{color:#94a3b8}
.version-selector input[type=checkbox]{display:none}

/* ── Timeline ── */
.timeline{position:relative;padding-left:32px}
.timeline::before{content:'';position:absolute;left:11px;top:8px;bottom:8px;width:2px;background:#334155}
.milestone{position:relative;margin-bottom:28px}
.milestone::before{content:'';position:absolute;left:-24px;top:6px;width:12px;height:12px;border-radius:50%;border:2px solid #64748b;background:#1e293b}
.milestone.optimized::before{background:#22c55e;border-color:#22c55e}
.milestone.baseline::before{background:#64748b;border-color:#64748b}
.milestone .card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:18px 20px}
.milestone .card:hover{border-color:#475569}

/* ── Card header (clickable) ── */
.card summary{list-style:none;cursor:pointer;outline:none}
.card summary::-webkit-details-marker{display:none}
.card summary::marker{display:none;content:''}
.card .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px}
.card .ver{font-size:.75rem;font-weight:800;color:#f8fafc}
.card .version-cb{display:flex;align-items:center;gap:6px}
.card .version-cb label{font-size:.68rem;color:#64748b;cursor:pointer;display:flex;align-items:center;gap:4px}
.card .version-cb input[type=checkbox]{accent-color:#f59e0b}
.card .date{font-size:.7rem;color:#475569}
.card .title{font-size:.95rem;font-weight:700;color:#f1f5f9;margin-bottom:6px}
.card .desc{font-size:.78rem;color:#94a3b8;line-height:1.6;margin-bottom:12px}
.card .expand-hint{font-size:.65rem;color:#475569;margin-top:4px}

/* ── Changes list ── */
.changes-title{font-size:.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}
.changes-list{list-style:none;padding:0;margin:0 0 14px}
.changes-list li{font-size:.74rem;color:#cbd5e1;line-height:1.6;padding:3px 0 3px 16px;position:relative}
.changes-list li::before{content:'▸';position:absolute;left:0;color:#f59e0b;font-size:.65rem}

/* ── Delta bar ── */
.delta-bar{display:flex;align-items:center;gap:12px;margin-bottom:12px;font-size:.72rem;flex-wrap:wrap}
.delta-bar .delta-item{display:flex;align-items:center;gap:4px;background:#0f172a;border-radius:4px;padding:4px 10px}
.delta-bar .delta-label{color:#64748b}
.delta-bar .delta-val{font-weight:700;font-variant-numeric:tabular-nums}
.delta-bar .delta-val.up{color:#22c55e}
.delta-bar .delta-val.down{color:#ef4444}

/* ── Metrics grid ── */
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:.72rem}
@media(max-width:600px){.metrics{grid-template-columns:repeat(2,1fr)}}
.metrics .m{background:#0f172a;border-radius:4px;padding:6px 10px}
.metrics .m .mv{font-weight:700;font-variant-numeric:tabular-nums}
.metrics .m .ml{color:#64748b;font-size:.62rem}

/* ── Details panel (expanded view) ── */
.detail-section{margin-top:12px;padding-top:12px;border-top:1px solid #334155}
.detail-section h4{font-size:.72rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.3px;margin-bottom:8px}
.detail-table{width:100%;border-collapse:collapse;font-size:.7rem;margin-bottom:12px}
.detail-table th{background:#0f172a;padding:4px 8px;text-align:left;font-weight:600;color:#64748b;font-size:.6rem;text-transform:uppercase}
.detail-table td{padding:3px 8px;border-bottom:1px solid #1e293b}
.detail-table .n{text-align:right;font-variant-numeric:tabular-nums}
.detail-table tr:hover td{background:#0f172a}
.detail-badge{display:inline-block;padding:1px 6px;border-radius:4px;font-size:.6rem;font-weight:700}
.detail-badge.g{background:#064e3b;color:#22c55e}
.detail-badge.y{background:#78350f;color:#f59e0b}
.detail-badge.r{background:#7f1d1d;color:#ef4444}

/* ── Footer ── */
.ft{text-align:center;color:#475569;font-size:.65rem;padding:16px;margin-top:8px}
.ft a{color:#64748b}
"""  # noqa: E501

JS = """<script>
// Version selection for SVG chart
(function() {
  const chartSvg = document.getElementById('chart-svg');
  if (!chartSvg) return;

  // Only use checkboxes in the version-selector bar (class vs-cb)
  const chartDataEl = document.getElementById('chart-data');
  if (!chartDataEl) return;

  let milestones;
  try {
    milestones = JSON.parse(chartDataEl.textContent);
  } catch(e) {
    return;
  }

  // All checkboxes with class ver-cb (in selector AND in cards)
  function getAllCBs() {
    return document.querySelectorAll('.ver-cb');
  }

  // Sync all checkboxes with the same data-index
  function setAllIndexed(index, checked) {
    getAllCBs().forEach(cb => {
      if (parseInt(cb.dataset.index) === index) cb.checked = checked;
    });
  }

  function redrawChart() {
    // Collect selected indices from ANY checkbox (they should be synced)
    const selected = new Set();
    getAllCBs().forEach(cb => {
      if (cb.checked) selected.add(parseInt(cb.dataset.index));
    });

    const circles = chartSvg.querySelectorAll('.data-point');
    const labels = chartSvg.querySelectorAll('.data-label');
    const verLabels = chartSvg.querySelectorAll('.ver-label');
    const ratioLabels = chartSvg.querySelectorAll('.ratio-label');
    const polyline = chartSvg.querySelector('.sv-polyline');
    const visiblePoints = [];

    circles.forEach(c => {
      const idx = parseInt(c.dataset.index);
      if (selected.has(idx)) {
        c.style.display = '';
        visiblePoints.push({x: c.getAttribute('cx'), y: c.getAttribute('cy')});
      } else {
        c.style.display = 'none';
      }
    });

    labels.forEach(l => {
      l.style.display = selected.has(parseInt(l.dataset.index)) ? '' : 'none';
    });
    verLabels.forEach(l => {
      l.style.display = selected.has(parseInt(l.dataset.index)) ? '' : 'none';
    });
    ratioLabels.forEach(l => {
      l.style.display = selected.has(parseInt(l.dataset.index)) ? '' : 'none';
    });

    if (polyline && visiblePoints.length >= 2) {
      polyline.setAttribute('points', visiblePoints.map(p => p.x + ',' + p.y).join(' '));
      polyline.style.display = '';
    } else if (polyline) {
      polyline.style.display = 'none';
    }

    // Update label styling in version selector
    document.querySelectorAll('.vs-label').forEach(lbl => {
      const cb = lbl.querySelector('.ver-cb');
      if (cb && cb.checked) {
        lbl.classList.add('checked');
      } else {
        lbl.classList.remove('checked');
      }
    });
  }

  // Attach change handler to ALL checkboxes
  getAllCBs().forEach(cb => {
    cb.addEventListener('change', function() {
      // Sync all checkboxes with same index
      const idx = parseInt(this.dataset.index);
      setAllIndexed(idx, this.checked);
      redrawChart();
    });
  });

  // "全选" and "仅优化版" buttons
  const btnAll = document.getElementById('btn-select-all');
  const btnOpt = document.getElementById('btn-select-optimized');
  if (btnAll) btnAll.addEventListener('click', function(e) {
    e.preventDefault();
    getAllCBs().forEach(cb => { cb.checked = true; });
    redrawChart();
  });
  if (btnOpt) btnOpt.addEventListener('click', function(e) {
    e.preventDefault();
    getAllCBs().forEach(cb => {
      const idx = parseInt(cb.dataset.index);
      cb.checked = idx >= 2;
    });
    redrawChart();
  });

  // Initial draw
  redrawChart();
})();
</script>"""  # noqa: E501


def _f(n):
    if n is None:
        return "—"
    if isinstance(n, float) and n >= 1e9:
        return f"{n/1e9:.2f}B"
    if isinstance(n, float) and n >= 1e6:
        return f"{n/1e6:.1f}M"
    if isinstance(n, int) and n >= 1e9:
        return f"{n/1e9:.2f}B"
    if isinstance(n, int) and n >= 1e6:
        return f"{n/1e6:.1f}M"
    return f"{n:,.0f}" if isinstance(n, (int, float)) else str(n)


def _svg_chart(baseline: dict, milestones: list) -> str:
    """Generate an interactive SVG line chart with data attributes for JS manipulation."""
    W, H = 800, 360
    ML, MR, MT, MB = 100, 40, 24, 72  # margins
    PW = W - ML - MR  # plot width
    PH = H - MT - MB  # plot height

    vals = [baseline["dynamic_insns"]] + [m["dynamic_insns"] for m in milestones]
    y_min = baseline["dynamic_insns"] * 0.8
    y_max = max(vals) * 1.08

    def _fy(v):
        return MT + PH - (v - y_min) / (y_max - y_min) * PH

    def _fx(i):
        if len(milestones) <= 1:
            return ML + PW / 2
        return ML + i / (len(milestones) - 1) * PW

    # Y-axis ticks
    y_ticks = []
    step = 1e9
    for v in range(int(y_min / step) * int(step), int(y_max) + int(step), int(step)):
        if v > y_min and v < y_max:
            y_ticks.append(v)

    svg = f'<svg id="chart-svg" viewBox="0 0 {W} {H}" width="100%" height="auto" style="max-width:{W}px;font-family:system-ui,sans-serif">'

    # Grid
    base_y = _fy(baseline["dynamic_insns"])
    svg += f'\n  <line x1="{ML}" y1="{base_y}" x2="{ML+PW}" y2="{base_y}" stroke="#22c55e" stroke-dasharray="6,4" stroke-width="1.5" opacity="0.6"/>'
    svg += f'\n  <text x="{ML-10}" y="{base_y+4}" text-anchor="end" fill="#22c55e" font-size="11" font-weight="700">LLVM {_f(baseline["dynamic_insns"])}</text>'

    for yv in y_ticks:
        yp = _fy(yv)
        svg += f'\n  <line x1="{ML}" y1="{yp}" x2="{ML+PW}" y2="{yp}" stroke="#334155" stroke-width="1"/>'
        svg += f'\n  <text x="{ML-8}" y="{yp+4}" text-anchor="end" fill="#64748b" font-size="10">{_f(yv)}</text>'

    # Y-axis line
    svg += f'\n  <line x1="{ML}" y1="{MT}" x2="{ML}" y2="{MT+PH}" stroke="#475569" stroke-width="1"/>'
    # X-axis line
    svg += f'\n  <line x1="{ML}" y1="{MT+PH}" x2="{ML+PW}" y2="{MT+PH}" stroke="#475569" stroke-width="1"/>'

    # ScratchV polyline
    points = []
    for i, m in enumerate(milestones):
        x = _fx(i)
        y = _fy(m["dynamic_insns"])
        points.append(f"{x:.0f},{y:.1f}")

    if len(points) >= 2:
        svg += f'\n  <polyline class="sv-polyline" points="{" ".join(points)}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linejoin="round"/>'

    for i, m in enumerate(milestones):
        x = _fx(i)
        y = _fy(m["dynamic_insns"])
        ratio_str = f"{m['vs_llvm_ratio']:.1f}x"
        svg += f'\n  <circle class="data-point" data-index="{i}" cx="{x:.0f}" cy="{y:.1f}" r="5" fill="#f59e0b" stroke="#0f172a" stroke-width="2"/>'
        svg += f'\n  <text class="data-label" data-index="{i}" x="{x:.0f}" y="{y-10:.1f}" text-anchor="middle" fill="#f59e0b" font-size="11" font-weight="700">{_f(m["dynamic_insns"])}</text>'
        svg += f'\n  <text class="ver-label" data-index="{i}" x="{x:.0f}" y="{MT+PH+20}" text-anchor="middle" fill="#94a3b8" font-size="11">{m["version"]}</text>'
        svg += f'\n  <text class="ratio-label" data-index="{i}" x="{x:.0f}" y="{MT+PH+38}" text-anchor="middle" fill="#64748b" font-size="10">{ratio_str} vs LLVM</text>'

    svg += '\n</svg>'
    return svg


def _detail_breakdown(m: dict) -> str:
    """Generate the expanded detail panel HTML for a milestone."""
    breakdown = m.get("instruction_breakdown", {})
    if not breakdown:
        return ""

    categories = breakdown.get("categories", {})
    per_op = breakdown.get("per_operator", {})

    cat_order = [
        ("ALU R-type", "alu_r"), ("ALU I-type", "alu_i"),
        ("FP", "fp"), ("Shift", "shift"),
        ("Load", "load"), ("Store", "store"),
        ("Branch", "branch"), ("Jump", "jump"),
        ("Upper imm.", "upper"),
    ]

    h = '<div class="detail-section">'
    h += '<h4>Dynamic Instruction Breakdown</h4>'

    # Category table
    if categories:
        h += '<table class="detail-table"><tr><th>Category</th><th class="n">Count</th><th class="n">%</th></tr>'
        total = breakdown.get("dynamic_insns", sum(categories.values()))
        for name, key in cat_order:
            v = categories.get(key, 0)
            pct = v / max(total, 1) * 100
            h += f'<tr><td>{name}</td><td class="n">{_f(v)}</td><td class="n">{pct:.1f}%</td></tr>'
        h += f'<tr style="font-weight:700"><td>Total</td><td class="n">{_f(total)}</td><td class="n">100%</td></tr>'
        h += '</table>'

    # Per-operator table
    if per_op:
        h += '<h4 style="margin-top:12px">Per-Operator Type</h4>'
        h += '<table class="detail-table"><tr><th>Op Type</th><th class="n">Dynamic Insns</th><th class="n">vs LLVM</th></tr>'
        for op_name in ["conv", "gemm", "maxpool", "relu", "sigmoid"]:
            op_data = per_op.get(op_name, {})
            dyn = op_data.get("dynamic_insns", 0)
            ratio = op_data.get("ratio", 0)
            badge_cls = "g" if ratio <= 1.5 else ("y" if ratio <= 4 else "r")
            h += f'<tr><td>{op_name}</td><td class="n">{_f(dyn)}</td><td class="n"><span class="detail-badge {badge_cls}">{ratio:.2f}x</span></td></tr>'
        h += '</table>'

    h += '</div>'
    return h


def generate(history: dict | None = None) -> str:
    if history is None:
        history = json.loads(HISTORY_FILE.read_text())

    baseline = history["baseline"]
    milestones = history["milestones"]
    first = milestones[0]
    last = milestones[-1]

    # ── KPI cards ──
    dyn_reduction = (1 - last["dynamic_insns"] / first["dynamic_insns"]) * 100
    ratio_change = first["vs_llvm_ratio"] - last["vs_llvm_ratio"]
    time_reduction = (1 - last["time_100mhz_s"] / first["time_100mhz_s"]) * 100

    # ── Embed chart data as JSON for JS ──
    chart_data = []
    for i, m in enumerate(milestones):
        chart_data.append({
            "index": i,
            "version": m["version"],
            "dynamic_insns": m["dynamic_insns"],
            "vs_llvm_ratio": m["vs_llvm_ratio"],
        })

    h = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ScratchV | 优化历史</title><style>{CSS}</style></head><body><div class="wrap">
<div class="header">
<h1>ScratchV 编译器优化历史</h1>
<div class="sub">模型: {history["model"]} &nbsp;|&nbsp; Baseline: {baseline["name"]} ({_f(baseline["dynamic_insns"])} 动态指令) &nbsp;|&nbsp; 更新于 {datetime.now().strftime("%Y-%m-%d")}</div>
</div>

<div class="kpi-grid">
<div class="kpi"><div class="v g">−{dyn_reduction:.0f}%</div><div class="l">动态指令减少</div></div>
<div class="kpi"><div class="v{' g' if ratio_change>0 else ' r'}">{ratio_change:.1f}x</div><div class="l">vs LLVM 差距缩小</div></div>
<div class="kpi"><div class="v g">−{time_reduction:.0f}%</div><div class="l">推理时间减少 @100MHz</div></div>
<div class="kpi"><div class="v y">{last['vs_llvm_ratio']:.2f}x</div><div class="l">当前 vs LLVM</div></div>
</div>

<div class="chart-section">
<h2>动态指令趋势</h2>
<div class="chart-sub">绿色虚线 = LLVM float32 baseline（{_f(baseline["dynamic_insns"])}） | 橙色实线 = ScratchV 各版本 | 勾选版本框进行对比</div>

<div class="version-selector">"""

    # Version selector checkboxes
    for i, m in enumerate(milestones):
        tag = m.get("tag", "")
        dot_color = "#22c55e" if tag == "optimized" else "#64748b"
        checked = "checked" if tag == "optimized" or i == len(milestones) - 1 else ""
        h += f'<label class="vs-label checked"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{dot_color};margin-right:2px"></span><input type="checkbox" class="ver-cb" data-index="{i}" {checked}>{m["version"]}</label>'

    h += '<label id="btn-select-all" style="background:transparent;border:none;font-size:.65rem;color:#64748b;cursor:pointer">全选</label>'
    h += '<label id="btn-select-optimized" style="background:transparent;border:none;font-size:.65rem;color:#64748b;cursor:pointer">仅优化版</label>'

    h += f"""</div>
<div class="chart-container">
{_svg_chart(baseline, milestones)}
</div>
<script id="chart-data" type="application/json" data-baseline="{baseline['dynamic_insns']}">{json.dumps(chart_data)}</script>
<div class="chart-legend">
<div class="leg-item"><span class="leg-line" style="background:#22c55e;border:1px dashed #22c55e"></span> LLVM baseline ({_f(baseline["dynamic_insns"])})</div>
<div class="leg-item"><span class="leg-dot" style="background:#f59e0b"></span> ScratchV</div>
</div>
</div>

<h2 style="margin-bottom:16px">优化时间线 — 点击展开查看详情</h2>
<div class="timeline">"""

    for m in reversed(milestones):
        tag_cls = m.get("tag", "")
        # Find previous milestone for comparison
        prev = None
        for pm in milestones:
            if pm is m:
                break
            prev = pm

        # Determine if this card should be open by default (latest version)
        is_open = (m is last)

        details_attr = " open" if is_open else ""
        h += f"""<div class="milestone {tag_cls}">
<div class="card">
<details{details_attr}>
<summary>
<div class="top"><span class="ver">{m["version"]}</span>
<div class="version-cb"><label><input type="checkbox" class="ver-cb" data-index="{milestones.index(m)}" {"checked" if (tag_cls == "optimized" or m is last) else ""}> 图表显示</label></div>
<span class="date">{m["date"]}</span></div>
<div class="title">{m["title"]}</div>
<div class="desc">{m["description"]}</div>
<div class="expand-hint">{"▾ 点击收起详情" if is_open else "▸ 点击展开详情（指令分类 + 算子对比）"}</div>
</summary>"""

        # ── Optimization changes list ──
        changes = m.get("changes", [])
        if changes:
            h += '<div class="changes-title">优化要点</div><ul class="changes-list">'
            for c in changes:
                h += f"<li>{c}</li>"
            h += "</ul>"

        # ── Delta from previous version ──
        if prev:
            delta_dyn = (1 - m["dynamic_insns"] / prev["dynamic_insns"]) * 100
            delta_ratio = prev["vs_llvm_ratio"] - m["vs_llvm_ratio"]
            delta_time = (1 - m["time_100mhz_s"] / prev["time_100mhz_s"]) * 100
            h += '<div class="delta-bar">'
            h += '<span style="color:#64748b;font-weight:600">较上一版:</span>'
            if delta_dyn > 0:
                h += f'<span class="delta-item"><span class="delta-label">动态指令</span><span class="delta-val up">−{delta_dyn:.1f}%</span></span>'
            if delta_ratio > 0:
                h += f'<span class="delta-item"><span class="delta-label">vs LLVM</span><span class="delta-val up">−{delta_ratio:.2f}x</span></span>'
            if delta_time > 0:
                h += f'<span class="delta-item"><span class="delta-label">推理时间</span><span class="delta-val up">−{delta_time:.1f}%</span></span>'
            h += '</div>'

        # ── Metrics grid ──
        h += '<div class="metrics">'
        h += f'<div class="m"><div class="mv">{_f(m["dynamic_insns"])}</div><div class="ml">动态指令</div></div>'
        h += f'<div class="m"><div class="mv">{m["vs_llvm_ratio"]:.2f}x</div><div class="ml">vs LLVM 比值</div></div>'
        h += f'<div class="m"><div class="mv">{m["per_mac_insns"]} instr/MAC</div><div class="ml">内层循环效率</div></div>'
        h += f'<div class="m"><div class="mv">{m["time_100mhz_s"]:.1f}s</div><div class="ml">@100MHz 推理时间</div></div>'
        h += "</div>"

        # ── Comparison to LLVM ──
        ratio = m["vs_llvm_ratio"]
        ratio_color = "#22c55e" if ratio <= 1.5 else ("#f59e0b" if ratio <= 4 else "#ef4444")
        gap = m["dynamic_insns"] - baseline["dynamic_insns"]
        h += f'<div style="margin-top:10px;font-size:.7rem;color:#64748b">'
        h += f'与 LLVM 差距: <span style="color:{ratio_color};font-weight:700">{_f(gap)}</span> 条指令 '
        h += f'(<span style="color:{ratio_color};font-weight:700">{ratio:.2f}x</span>)'
        h += '</div>'

        # ── Detailed breakdown (in expanded section) ──
        h += _detail_breakdown(m)

        h += "</details></div></div>"

    h += f"""</div>

<div class="ft">
ScratchV Compiler | <a href="https://github.com/ScratchV-Compiler/ScratchV">GitHub</a>
&nbsp;|&nbsp; <a href="optimization_history.json">JSON data</a>
&nbsp;|&nbsp; <a href="dashboard.html">Dashboard</a>
&nbsp;|&nbsp; Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div></div>
{JS}
</body></html>"""
    return h


def main():
    import argparse
    p = argparse.ArgumentParser(description="Generate optimization history page")
    p.add_argument("-o", "--output", default=str(OUTPUT_FILE),
                   help=f"Output HTML path (default: {OUTPUT_FILE})")
    p.add_argument("--json", default=str(HISTORY_FILE),
                   help="History JSON input")
    args = p.parse_args()

    if not os.path.exists(args.json):
        print(f"ERROR: {args.json} not found", file=sys.stderr)
        return 1

    with open(args.json) as f:
        history = json.load(f)

    html = generate(history)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"→ {args.output} ({len(html):,}B)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
