#!/usr/bin/env python3
"""Benchmark single-operator ONNX models — collect static/dynamic instruction data.

For each single-op model in models/single_op/:
  1. Compile with ScratchV → static instruction count
  2. Map to per-layer dynamic instruction estimates (ScratchV + LLVM)
  3. Aggregate by operator type

Output: benchmark_reports/single_op_bench.json
"""

from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

PROJ = Path(__file__).resolve().parent.parent
SINGLE_OP_DIR = PROJ / "models" / "single_op"
OUTPUT_FILE = PROJ / "benchmark_reports" / "single_op_bench.json"


# ── Mapping: single-op model name → layer name in estimation functions ──
# These correspond to the per-layer keys in estimate_cnn_model() output
# and the compute_layer_dims() from llvm_cache_compare.py
# (op_type, sv_layer_name, llvm_layer_name)
MODEL_TO_LAYER = {
    "cnn_layer1.0_Conv":      ("conv",     "Conv1",    "Conv1 (3→32, 3×3)"),
    "cnn_layer1.1_Relu":      ("relu",     "ReLU1",    "ReLU1"),
    "cnn_layer1.2_MaxPool":   ("maxpool",  "MaxPool1", "MaxPool1 (2×2)"),
    "cnn_layer2.0_Conv":      ("conv",     "Conv2",    "Conv2 (32→32, 3×3)"),
    "cnn_layer2.1_Relu":      ("relu",     "ReLU2",    "ReLU2"),
    "cnn_layer2.2_MaxPool":   ("maxpool",  "MaxPool2", "MaxPool2 (2×2)"),
    "cnn_layer3.0_Conv":      ("conv",     "Conv3",    "Conv3 (32→64, 3×3)"),
    "cnn_layer3.1_Relu":      ("relu",     "ReLU3",    "ReLU3"),
    "cnn_layer3.2_MaxPool":   ("maxpool",  "MaxPool3", "MaxPool3 (2×2)"),
    "cnn_fc1_Gemm":           ("gemm",     "FC1",      "FC1 (53824→128)"),
    "cnn_relu1_Relu":         ("relu",     "ReLU (after FC1)", "ReLU4"),
    "cnn_fc2_Gemm":           ("gemm",     "FC2",      "FC2 (128→1)"),
    "cnn_sigmoid1_Sigmoid":   ("sigmoid",  "Sigmoid",  "Sigmoid"),
}


def _compile_scratchv(model_path: str) -> dict:
    """Compile a single-op model with ScratchV, return static instruction count."""
    t0 = time.perf_counter()
    bin_out = f"/tmp/_singleop_{os.path.basename(model_path)}.bin"
    cmd = [
        sys.executable,
        str(PROJ / "scratchv" / "standalone" / "onnx_to_riscv_standalone.py"),
        model_path, "-o", bin_out,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(PROJ),
        )
        elapsed = time.perf_counter() - t0
        output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "static_insns": 0, "code_size_bytes": 0, "elapsed_s": 30}
    except Exception as e:
        return {"status": "error", "static_insns": 0, "code_size_bytes": 0, "elapsed_s": 0, "error": str(e)}

    # Parse static instruction count from output
    static_insns = 0
    code_size = 0
    for line in output.splitlines():
        if "instructions" in line and "Code size:" in line:
            try:
                parts = line.split("(")[1].split()[0]
                static_insns = int(parts.replace(",", ""))
            except (ValueError, IndexError):
                pass
        if "Code size:" in line and "bytes" in line:
            try:
                parts = line.split("Code size:")[1].split()
                code_size = int(parts[0].replace(",", ""))
            except (ValueError, IndexError):
                pass

    if proc.returncode != 0:
        return {"status": "failed", "static_insns": static_insns,
                "code_size_bytes": code_size, "elapsed_s": elapsed,
                "stderr": proc.stderr[:200]}

    return {"status": "ok", "static_insns": static_insns,
            "code_size_bytes": code_size, "elapsed_s": elapsed}


def _get_layer_data() -> tuple[dict, dict]:
    """Get per-layer dynamic instruction estimates for ScratchV and LLVM."""
    # ScratchV per-layer data from benchmark.py
    from scratchv.standalone.benchmark import estimate_cnn_model
    sv_est = estimate_cnn_model()
    sv_per_layer = sv_est.get("per_layer", {})

    # LLVM per-layer data: compute using llvm_cache_compare formulas
    from scratchv.standalone.llvm_cache_compare import (
        compute_layer_dims, LLVM_CONV_PER_MAC, LLVM_FC_PER_MAC,
        LLVM_MAXPOOL_PER_EL, LLVM_RELU_PER_EL, LLVM_SIGMOID_PER_EL,
        LLVM_RESHAPE_PER_EL,
    )
    layers = compute_layer_dims()

    llvm_per_layer = {}
    for layer in layers:
        name = layer.name
        if name.startswith("Conv"):
            for cat, ratio in LLVM_CONV_PER_MAC.items():
                llvm_per_layer[name] = llvm_per_layer.get(name, 0) + layer.macs * ratio
        elif name.startswith("FC"):
            for cat, ratio in LLVM_FC_PER_MAC.items():
                llvm_per_layer[name] = llvm_per_layer.get(name, 0) + layer.macs * ratio
        elif name.startswith("MaxPool"):
            for cat, ratio in LLVM_MAXPOOL_PER_EL.items():
                llvm_per_layer[name] = llvm_per_layer.get(name, 0) + layer.elements * ratio
        elif name.startswith("ReLU"):
            for cat, ratio in LLVM_RELU_PER_EL.items():
                llvm_per_layer[name] = llvm_per_layer.get(name, 0) + layer.elements * ratio
        elif name.startswith("Sigmoid"):
            for cat, ratio in LLVM_SIGMOID_PER_EL.items():
                llvm_per_layer[name] = llvm_per_layer.get(name, 0) + layer.elements * ratio
        elif name.startswith("Reshape"):
            for cat, ratio in LLVM_RESHAPE_PER_EL.items():
                llvm_per_layer[name] = llvm_per_layer.get(name, 0) + layer.elements * ratio
        llvm_per_layer[name] = int(llvm_per_layer[name])

    return sv_per_layer, llvm_per_layer


def main():
    print("Collecting per-layer analytical data...")
    sv_per_layer, llvm_per_layer = _get_layer_data()

    print(f"  ScratchV layers: {list(sv_per_layer.keys())}")
    print(f"  LLVM layers: {list(llvm_per_layer.keys())}")

    # Discover all single-op models
    models = {}
    for op_dir in SINGLE_OP_DIR.iterdir():
        if not op_dir.is_dir():
            continue
        op_type = op_dir.name
        for onnx_file in op_dir.glob("*.onnx"):
            model_name = onnx_file.stem  # e.g., "cnn_layer1.0_Conv"
            models[model_name] = {
                "path": str(onnx_file),
                "op_type": op_type,
            }

    print(f"\nFound {len(models)} single-op models in {SINGLE_OP_DIR}")

    # Compile each model with ScratchV and collect data
    results = {}
    for model_name in sorted(models.keys()):
        info = models[model_name]
        path = info["path"]
        op_type = info["op_type"]

        print(f"  Compiling: {model_name} ({op_type})...", end=" ", flush=True)
        comp = _compile_scratchv(path)
        print(f"static={comp['static_insns']} insns, {comp['status']}")

        # Map to per-layer dynamic data
        layer_info = MODEL_TO_LAYER.get(model_name, (op_type, None, None))
        sv_layer = layer_info[1] if len(layer_info) > 1 else None
        llvm_layer = layer_info[2] if len(layer_info) > 2 else None

        sv_dyn = sv_per_layer.get(sv_layer, 0) if sv_layer else 0
        llvm_dyn = llvm_per_layer.get(llvm_layer, 0) if llvm_layer else 0

        results[model_name] = {
            "op_type": op_type,
            "network": "cnn",
            "path": path,
            "scratchv_static_insns": comp["static_insns"],
            "scratchv_code_size_bytes": comp["code_size_bytes"],
            "scratchv_dynamic_insns": int(sv_dyn),
            "llvm_dynamic_insns": int(llvm_dyn),
            "dynamic_ratio": round(sv_dyn / max(llvm_dyn, 1), 2) if llvm_dyn else 0,
            "compile_status": comp["status"],
        }

    # ── Aggregate by operator type ──
    by_op_type = defaultdict(lambda: {
        "models": [],
        "total_sv_static": 0,
        "total_sv_dynamic": 0,
        "total_llvm_dynamic": 0,
    })

    for model_name, data in results.items():
        ot = data["op_type"]
        by_op_type[ot]["models"].append(model_name)
        by_op_type[ot]["total_sv_static"] += data["scratchv_static_insns"]
        by_op_type[ot]["total_sv_dynamic"] += data["scratchv_dynamic_insns"]
        by_op_type[ot]["total_llvm_dynamic"] += data["llvm_dynamic_insns"]

    # Compute aggregate ratios
    aggregates = {}
    for ot, agg in by_op_type.items():
        total_sv = agg["total_sv_dynamic"]
        total_llvm = agg["total_llvm_dynamic"]
        aggregates[ot] = {
            "model_count": len(agg["models"]),
            "models": agg["models"],
            "total_scratchv_static_insns": agg["total_sv_static"],
            "total_scratchv_dynamic_insns": total_sv,
            "total_llvm_dynamic_insns": total_llvm,
            "dynamic_ratio": round(total_sv / max(total_llvm, 1), 2),
        }

    # ── Build output ──
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": "ScratchV",
        "source_model": "cnn.onnx (3×Conv + 3×MaxPool + 2×FC)",
        "models": results,
        "aggregates": aggregates,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n→ {OUTPUT_FILE} ({len(json.dumps(output)):,} bytes)")

    # ── Print summary ──
    print(f"\n{'='*60}")
    print("Operator-type aggregates:")
    print(f"{'Op Type':<12} {'Count':>5} {'SV Dynamic':>15} {'LLVM Dynamic':>15} {'Ratio':>8}")
    print("-" * 60)
    for ot in ["conv", "gemm", "maxpool", "relu", "sigmoid"]:
        if ot in aggregates:
            a = aggregates[ot]
            print(f"{ot:<12} {a['model_count']:>5} {a['total_scratchv_dynamic_insns']:>15,} "
                  f"{a['total_llvm_dynamic_insns']:>15,} {a['dynamic_ratio']:>7.2f}x")

    return 0


if __name__ == "__main__":
    sys.exit(main())
