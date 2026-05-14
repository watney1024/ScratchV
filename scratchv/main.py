#!/usr/bin/env python3
"""ScratchV CLI: ONNX model → RISC-V assembly compiler.

Usage:
    scratchv model.onnx -o output.s
    scratchv model.onnx -o output.s --optimize --reg-alloc greedy
    scratchv --dsl source.dsl -o output.s
"""

from __future__ import annotations

import argparse
import sys


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ScratchV: ONNX model to RISC-V assembly compiler",
    )
    parser.add_argument("input", nargs="?", help="Input file (.onnx or .dsl)")
    parser.add_argument("-o", "--output", default="output.s", help="Output assembly file")
    parser.add_argument("--dsl", help="Use DSL parser instead of ONNX (or pass .dsl file as input)")
    parser.add_argument("--dump-ir", action="store_true", help="Dump IR before codegen")
    parser.add_argument("--optimize", choices=["none", "basic", "all"], default="none",
                        help="Optimization level: basic (fold+dce), all (+peephole+fuse+licm)")
    parser.add_argument("--reg-alloc", choices=["naive", "greedy"], default="greedy",
                        help="Register allocation strategy (default: greedy)")
    parser.add_argument("--version", action="version", version="ScratchV 0.1.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # --- Parse input ---
    input_path = args.input
    use_dsl = args.dsl is not None or (input_path and input_path.endswith(".dsl"))

    if input_path is None and args.dsl is None:
        parser.print_help()
        return 1

    try:
        if use_dsl:
            from scratchv.frontend.dsl_parser import DSLParser
            with open(input_path or args.dsl) as f:
                source = f.read()
            dsl_parser = DSLParser()
            program = dsl_parser.parse(source)
        else:
            from scratchv.frontend.onnx_parser import ONNXParser
            onnx_parser = ONNXParser()
            program = onnx_parser.parse(input_path)

    except Exception as e:
        print(f"Error parsing input: {e}", file=sys.stderr)
        return 1

    # --- Dump IR if requested ---
    if args.dump_ir:
        from scratchv.ir.printer import IRPrinter
        printer = IRPrinter(program)
        print("; --- IR Dump ---", file=sys.stderr)
        print(printer.dump(), file=sys.stderr)

    # --- Optimize ---
    if args.optimize != "none":
        from scratchv.optimizer.constant_folding import ConstantFolder
        from scratchv.optimizer.dead_code import DeadCodeEliminator

        folder = ConstantFolder(program)
        folded = folder.run()
        elim = DeadCodeEliminator(program)
        eliminated = elim.run()

        stats_str = f"{folded} folded, {eliminated} eliminated"

        if args.optimize == "all":
            from scratchv.optimizer.peephole import PeepholeOptimizer
            from scratchv.optimizer.muladd_fusion import MulAddFusion
            from scratchv.optimizer.licm import LICM

            peep = PeepholeOptimizer(program)
            peeped = peep.run()
            fuse = MulAddFusion(program)
            fused = fuse.run()
            licm = LICM(program)
            hoisted = licm.run()
            stats_str += f", {peeped} peep-hole, {fused} fused, {hoisted} hoisted"

        if args.dump_ir:
            print(f"; --- After optimization: {stats_str} ---",
                  file=sys.stderr)
            printer = IRPrinter(program)
            print(printer.dump(), file=sys.stderr)

    # --- Instruction selection ---
    from scratchv.backend.instruction_select import InstructionSelector
    selector = InstructionSelector(program)
    machine_instrs = selector.run()

    # --- Register allocation ---
    from scratchv.backend.register_alloc import RegisterAllocator
    alloc = RegisterAllocator(machine_instrs, mode=args.reg_alloc)
    allocated = alloc.run()

    # --- Assembly emission ---
    from scratchv.backend.asm_emit import AsmEmitter
    emitter = AsmEmitter(allocated)
    asm_text = emitter.emit()

    with open(args.output, "w") as f:
        f.write(asm_text)

    print(f"✓ Assembly written to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
