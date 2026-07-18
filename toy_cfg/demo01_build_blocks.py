"""demo01_build_blocks.py — Toy CFG: Basic Block Partition

Splits a ScratchV IR Function into BasicBlocks by detecting control flow
boundaries (LABEL/BR/BR_IF/RETURN/FOR/ENDFOR). Determines exits_to for each
block: BRANCH edges (BR_IF → true/false, FOR → "body"), JUMP edges (BR, ENDFOR),
and FALLTHROUGH edges (implicit sequential flow).

Usage:
    python toy_cfg/demo01_build_blocks.py --program if_else
    python toy_cfg/demo01_build_blocks.py --program while_loop
    python toy_cfg/demo01_build_blocks.py --program empty
    python toy_cfg/demo01_build_blocks.py --program nested_for
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from scratchv.ir.types import OpCode, Function, Program, Value, DataType
from scratchv.ir.builder import IRBuilder


# ---------------------------------------------------------------------------
# Toy BasicBlock dataclass — defined locally, not imported from scratchv
# ---------------------------------------------------------------------------

@dataclass
class BasicBlock:
    """A basic block: straight-line instruction sequence with single entry/exit.

    Attributes:
        name: Block label name.
        instructions: List of scratchv IR Instructions in this block.
        exits_to: List of (target_block_name, edge_label) tuples.
            edge_label is "true"/"false" for BR_IF, "body" for FOR → body,
            None for JUMP/FALLTHROUGH.
    """
    name: str
    instructions: list = field(default_factory=list)
    exits_to: list[tuple[str, str | None]] | None = None
    # (target_block_name, edge_label)


# ---------------------------------------------------------------------------
# Block partition logic
# ---------------------------------------------------------------------------

def build_blocks(func: Function) -> dict[str, BasicBlock]:
    """Split a Function into BasicBlocks by detecting control flow boundaries.

    Iterates over the sequential blocks in the function; for each block:
    1. If the block has instructions, the LAST instruction determines exits.
    2. BR → 1 JUMP exit (no label).
    3. BR_IF → 2 BRANCH exits ("true", "false").
    4. RETURN → 0 exits.
    5. FOR → 2 exits: ("body", "body") to the next block (loop body),
       and (exit_block, None) to the block after the matching ENDFOR.
    6. ENDFOR → 1 JUMP exit back to the matching FOR header.
    7. No terminator → FALLTHROUGH to the next sequential block.
    8. Empty block (no instructions) → FALLTHROUGH to next block.
    """
    all_blocks = func.blocks
    blocks_dict: dict[str, BasicBlock] = {}

    # ---- First pass: track FOR/ENDFOR nesting ----------------------------
    for_stack: list[int] = []
    for_to_endfor: dict[int, int] = {}
    endfor_to_for: dict[int, int] = {}

    for i, ir_block in enumerate(all_blocks):
        insts = ir_block.instructions
        if not insts:
            continue
        last = insts[-1]
        if last.opcode == OpCode.FOR:
            for_stack.append(i)
        elif last.opcode == OpCode.ENDFOR:
            if for_stack:
                for_idx = for_stack.pop()
                for_to_endfor[for_idx] = i
                endfor_to_for[i] = for_idx

    # ---- Second pass: build toy BasicBlocks -------------------------------
    for i, ir_block in enumerate(all_blocks):
        name = ir_block.name
        insts = list(ir_block.instructions)

        # Check for internal LABEL instructions that would split this block
        # (rare in builder-created IR, but handled for robustness)
        label_indices = [
            j for j, instr in enumerate(insts)
            if instr.opcode == OpCode.LABEL
        ]
        if label_indices:
            _split_at_labels(blocks_dict, insts, name, label_indices)
            continue

        bb = BasicBlock(name=name, instructions=insts)

        if not insts:
            # Empty block: FALLTHROUGH to next
            bb.exits_to = _fallthrough_exit(i, all_blocks)
            blocks_dict[name] = bb
            continue

        last = insts[-1]

        if last.opcode == OpCode.BR:
            bb.exits_to = [(last.target, None)]

        elif last.opcode == OpCode.BR_IF:
            parts = last.target.split(",", 1)
            bb.exits_to = [
                (parts[0].strip(), "true"),
                (parts[1].strip(), "false"),
            ]

        elif last.opcode == OpCode.RETURN:
            bb.exits_to = []

        elif last.opcode == OpCode.FOR:
            bb.exits_to = _for_exits(i, all_blocks, for_to_endfor)

        elif last.opcode == OpCode.ENDFOR:
            bb.exits_to = _endfor_exits(i, all_blocks, endfor_to_for)

        else:
            # No terminator: FALLTHROUGH to next block
            bb.exits_to = _fallthrough_exit(i, all_blocks)

        blocks_dict[name] = bb

    return blocks_dict


def _for_exits(
    block_idx: int,
    all_blocks: list,
    for_to_endfor: dict[int, int],
) -> list[tuple[str, str | None]]:
    """Determine exits for a FOR block: body (next block) + exit (after ENDFOR)."""
    exits: list[tuple[str, str | None]] = []

    # Body is the next sequential block
    if block_idx + 1 < len(all_blocks):
        exits.append((all_blocks[block_idx + 1].name, "body"))

    # Exit is the block after the matching ENDFOR
    endfor_idx = for_to_endfor.get(block_idx)
    if endfor_idx is not None and endfor_idx + 1 < len(all_blocks):
        exits.append((all_blocks[endfor_idx + 1].name, None))

    return exits


def _endfor_exits(
    block_idx: int,
    all_blocks: list,
    endfor_to_for: dict[int, int],
) -> list[tuple[str, str | None]]:
    """Determine exits for an ENDFOR block: JUMP back to matching FOR header."""
    for_idx = endfor_to_for.get(block_idx)
    if for_idx is not None:
        return [(all_blocks[for_idx].name, None)]
    return []


def _fallthrough_exit(
    block_idx: int,
    all_blocks: list,
) -> list[tuple[str, str | None]]:
    """FALLTHROUGH: if there's a next block, flow to it."""
    if block_idx + 1 < len(all_blocks):
        return [(all_blocks[block_idx + 1].name, None)]
    return []


def _split_at_labels(
    blocks_dict: dict[str, BasicBlock],
    insts: list,
    default_name: str,
    label_indices: list[int],
) -> None:
    """Split a block at internal LABEL instructions into sub-blocks."""
    start = 0
    for li in label_indices:
        sub_insts = insts[start:li]
        label_name = insts[li].target or f"{default_name}_sub"
        bb = BasicBlock(name=label_name, instructions=sub_insts)
        blocks_dict[label_name] = bb
        start = li + 1
    remaining = insts[start:]
    bb = BasicBlock(name=default_name, instructions=remaining)
    blocks_dict[default_name] = bb


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def print_blocks(blocks: dict[str, BasicBlock], func_name: str) -> None:
    """Print each block with its instructions and exits in a box format."""
    print(f"CFG for: {func_name}")
    for bb in blocks.values():
        # Header
        header = f"┌──── {bb.name} "
        padding = "─" * max(1, 46 - len(header))
        print(f"{header}{padding}┐")

        # Instructions
        if bb.instructions:
            for instr in bb.instructions:
                line = f"│  {instr}"
                line = line.ljust(48)
                print(f"{line}│")
        else:
            print(f"│  (no instructions) {'':>28}│")

        # Footer
        exits_str = str(bb.exits_to) if bb.exits_to is not None else "None"
        footer = f"└──── exits: {exits_str} "
        padding = "─" * max(1, 48 - len(footer))
        print(f"{footer}{padding}┘")
        print()


# ---------------------------------------------------------------------------
# Demo program builders using IRBuilder
# ---------------------------------------------------------------------------

def demo_if_else() -> Program:
    """Build an if-else program: entry → then/else → end."""
    builder = IRBuilder()
    func = builder.new_function("if_else_demo")

    # entry: conditional branch
    builder.new_block("entry")
    cond = builder.make_value("cond")
    builder.br_if(cond, "then", "else")

    # then: do something and jump to end
    builder.new_block("then")
    v1 = builder.load_const(42)
    builder.br("end")

    # else: do something else and jump to end
    builder.new_block("else")
    v2 = builder.load_const(-1)
    builder.br("end")

    # end: return
    builder.new_block("end")
    result = builder.make_value("result")
    builder.ret(result)

    return builder.program


def demo_while_loop() -> Program:
    """Build a while-loop program: entry(FOR) → body → end."""
    builder = IRBuilder()
    func = builder.new_function("while_loop_demo")

    # entry: for loop start
    builder.new_block("entry")
    iv = builder.for_loop(0, 10, 1)

    # body: some work then endfor
    builder.new_block("body")
    v1 = builder.add(iv, iv)
    builder.endfor()

    # end: return
    builder.new_block("end")
    result = builder.make_value("result")
    builder.ret(result)

    return builder.program


def demo_empty() -> Program:
    """Build an empty program: single block with no instructions."""
    builder = IRBuilder()
    func = builder.new_function("empty_demo")
    builder.new_block("entry")
    return builder.program


def demo_nested_for() -> Program:
    """Build a nested-for program: outer FOR → inner FOR → ENDFOR → ENDFOR."""
    builder = IRBuilder()
    func = builder.new_function("nested_for_demo")

    # entry: outer FOR
    builder.new_block("entry")
    iv1 = builder.for_loop(0, 5, 1)

    # outer_body: computation, falls through to inner
    builder.new_block("outer_body")
    x = builder.make_value("x")
    builder.add(x, x)

    # inner_entry: inner FOR
    builder.new_block("inner_entry")
    iv2 = builder.for_loop(0, 3, 1)

    # inner_body: work + endfor
    builder.new_block("inner_body")
    y = builder.make_value("y")
    builder.add(y, y)
    builder.endfor()

    # outer_end: more work + endfor
    builder.new_block("outer_end")
    z = builder.make_value("z")
    builder.add(z, z)
    builder.endfor()

    # end: return
    builder.new_block("end")
    builder.ret()

    return builder.program


# ---------------------------------------------------------------------------
# Demo registry
# ---------------------------------------------------------------------------

DEMOS: dict[str, Program] = {
    "if_else": demo_if_else(),
    "while_loop": demo_while_loop(),
    "empty": demo_empty(),
    "nested_for": demo_nested_for(),
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Toy CFG: Basic Block Partition Demo",
    )
    parser.add_argument(
        "--program", "-p",
        choices=list(DEMOS.keys()),
        default="if_else",
        help="Demo program to analyze (default: if_else)",
    )
    args = parser.parse_args()

    program = DEMOS[args.program]

    # Take the first function in the program
    func = program.functions[0]
    blocks = build_blocks(func)
    print_blocks(blocks, func.name)


if __name__ == "__main__":
    main()
