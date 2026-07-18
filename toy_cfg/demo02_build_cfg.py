"""demo02_build_cfg.py — Toy CFG: Data Structure and Edge Building

Builds on demo01's BasicBlock partition to construct a full CFG data
structure: validates edges, detects unreachable blocks via DFS, and
prints structural analysis of the control flow graph.

Usage:
    python toy_cfg/demo02_build_cfg.py --program if_else
    python toy_cfg/demo02_build_cfg.py --program while_loop
    python toy_cfg/demo02_build_cfg.py --program empty
    python toy_cfg/demo02_build_cfg.py --program nested_for
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from toy_cfg.demo01_build_blocks import BasicBlock, build_blocks, DEMOS
from scratchv.ir.types import Function


# ---------------------------------------------------------------------------
# CFG data structure
# ---------------------------------------------------------------------------

@dataclass
class CFG:
    """Control Flow Graph: entry point + blocks indexed by name.

    Attributes:
        entry: Name of the entry (first) block.
        blocks: Mapping from block name to BasicBlock.
        func_name: Original function name (for display purposes).
    """
    entry: str
    blocks: dict[str, BasicBlock]
    func_name: str = ""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_cfg(cfg: CFG) -> None:
    """Check every block's exits_to targets exist in blocks.

    Raises ValueError with a descriptive message if any target references
    a block that is not present in the CFG.
    """
    for name, block in cfg.blocks.items():
        if not block.exits_to:
            continue
        for target, _edge_label in block.exits_to:
            if target not in cfg.blocks:
                raise ValueError(
                    f"Block '{name}' has dangling target '{target}' — "
                    f"no block named '{target}' exists in the function"
                )


# ---------------------------------------------------------------------------
# CFG construction
# ---------------------------------------------------------------------------

def build_cfg(func: Function) -> CFG:
    """Build a CFG from a scratchv IR Function.

    1. Calls demo01's build_blocks to partition into BasicBlocks.
    2. Validates that every edge target references an existing block.
    3. Sets entry to the first block's name.

    Returns an empty CFG (entry="", blocks={}) if the function has no blocks.
    """
    blocks = build_blocks(func)

    # Edge case: empty function → empty CFG
    if not blocks:
        return CFG(entry="", blocks={}, func_name=func.name)

    cfg = CFG(entry=next(iter(blocks)), blocks=blocks, func_name=func.name)

    validate_cfg(cfg)
    return cfg


# ---------------------------------------------------------------------------
# Reachability analysis (DFS from entry)
# ---------------------------------------------------------------------------

def reachable_from(cfg: CFG) -> set[str]:
    """Return the set of block names reachable from the entry block via DFS.

    A block is unreachable if there is no path from entry following any
    sequence of exits_to edges.

    Returns an empty set if cfg.blocks is empty.
    """
    if not cfg.blocks or not cfg.entry:
        return set()

    visited: set[str] = set()
    stack: list[str] = [cfg.entry]

    while stack:
        name = stack.pop()
        if name in visited:
            continue
        visited.add(name)
        block = cfg.blocks[name]
        if block.exits_to:
            for target, _edge_label in block.exits_to:
                if target in cfg.blocks and target not in visited:
                    stack.append(target)

    return visited


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def print_cfg(cfg: CFG) -> None:
    """Print structural information about a CFG.

    Includes: function name, total block count, entry block marker,
    per-block details (instruction count, exits), and unreachable
    block detection via DFS.
    """
    header = f"CFG for: {cfg.func_name}"
    sep = "=" * len(header)
    print(header)
    print(sep)

    if not cfg.blocks:
        print("  (empty — no blocks)")
        print()
        return

    reachable = reachable_from(cfg)

    for name, block in cfg.blocks.items():
        is_entry = name == cfg.entry
        is_unreachable = name not in reachable

        # Block header
        prefix = "[entry] " if is_entry else "        "
        unreachable_mark = " [UNREACHABLE]" if is_unreachable else ""
        print(f"{prefix}Block: {name}{unreachable_mark}")

        # Instruction count
        n_insts = len(block.instructions)
        inst_label = "instruction" if n_insts == 1 else "instructions"
        print(f"        Instructions: {n_insts} {inst_label}")

        # Exits
        if block.exits_to:
            for target, label in block.exits_to:
                edge_info = f"  -> {target}"
                if label:
                    edge_info += f"  [{label}]"
                print(f"        {edge_info}")
        else:
            print(f"        exits: []")

        print()

    # Summary
    n_total = len(cfg.blocks)
    n_reachable = len(reachable)
    n_unreachable = n_total - n_reachable
    summary = (
        f"Summary: {n_total} block{'s' if n_total != 1 else ''}, "
        f"{n_reachable} reachable, "
        f"{n_unreachable} unreachable"
    )
    print(summary)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Toy CFG: Data Structure and Edge Building Demo",
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
    cfg = build_cfg(func)
    print_cfg(cfg)


if __name__ == "__main__":
    main()
