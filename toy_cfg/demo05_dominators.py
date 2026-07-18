"""demo05_dominators.py — Toy CFG: Dominator Analysis (CHK Algorithm)

Implements the Cooper-Harvey-Kennedy iterative dominator algorithm for
computing dominator sets and immediate dominators in a control flow graph.

Algorithm (CHK):
  dom(entry) = {entry}
  dom(B) = {B} ∪ (∩ dom(P) for all predecessors P of B), iterated to fixed point

  idom(B) = the unique strict dominator of B closest to B (not dominated
  by any other strict dominator of B). idom(entry) = None.

Usage:
    python toy_cfg/demo05_dominators.py --program if_else
    python toy_cfg/demo05_dominators.py --program while_loop
    python toy_cfg/demo05_dominators.py --program empty
"""

from __future__ import annotations

import argparse

from toy_cfg.demo01_build_blocks import BasicBlock
from toy_cfg.demo02_build_cfg import build_cfg, CFG, DEMOS


# ---------------------------------------------------------------------------
# Predecessor computation
# ---------------------------------------------------------------------------

def _compute_predecessors(cfg: CFG) -> dict[str, list[str]]:
    """Build predecessor map: for each block, list of block names that jump to it.

    Scans every block's exits_to edges and reverses them.
    """
    preds: dict[str, list[str]] = {name: [] for name in cfg.blocks}
    for src_name, block in cfg.blocks.items():
        if not block.exits_to:
            continue
        for tgt_name, _ in block.exits_to:
            if tgt_name in preds:
                preds[tgt_name].append(src_name)
    return preds


# ---------------------------------------------------------------------------
# CHK iterative dominator algorithm
# ---------------------------------------------------------------------------

def compute_dominators(cfg: CFG) -> dict[str, set[str]]:
    """Cooper-Harvey-Kennedy iterative dominator computation.

    dom(B) = {B} ∪ (∩ dom(P) for all predecessors P of B)

    The entry node starts with only itself. All other nodes start with the
    full set of all nodes. Iterate until fixed point (no changes).

    Returns a mapping from block name to its set of dominators.
    Returns an empty dict if the CFG has no blocks.
    """
    if not cfg.blocks:
        return {}

    all_nodes = set(cfg.blocks.keys())
    preds = _compute_predecessors(cfg)

    # Initialize
    dom: dict[str, set[str]] = {}
    for name in all_nodes:
        if name == cfg.entry:
            dom[name] = {name}
        else:
            dom[name] = set(all_nodes)  # Everything dominates initially

    # Iterate until fixed point
    changed = True
    iteration = 0
    MAX_ITER = 100  # safety limit

    while changed and iteration < MAX_ITER:
        changed = False
        iteration += 1
        for name in all_nodes:
            if name == cfg.entry:
                continue

            block_preds = preds.get(name, [])
            if not block_preds:
                continue

            # dom(B) = {B} ∪ ∩ dom(P) for all P in preds(B)
            new_dom = set(dom[block_preds[0]])  # Start with first predecessor
            for p in block_preds[1:]:
                new_dom &= dom[p]  # Intersection with rest
            new_dom.add(name)  # ∪ {B}

            if new_dom != dom[name]:
                dom[name] = new_dom
                changed = True

    return dom


# ---------------------------------------------------------------------------
# Immediate dominator
# ---------------------------------------------------------------------------

def compute_idom(
    cfg: CFG,
    dom_sets: dict[str, set[str]],
) -> dict[str, str | None]:
    """Compute immediate dominator for each block.

    idom(B) is the unique strict dominator of B that is not dominated
    by any other strict dominator of B. For the entry block, idom is None.

    Returns a mapping from block name to its immediate dominator name
    (or None for the entry block). Returns an empty dict if no dom sets.
    """
    if not dom_sets:
        return {}

    idom: dict[str, str | None] = {}

    for name, dom_set in dom_sets.items():
        if name == cfg.entry:
            idom[name] = None
            continue

        # Strict dominators = dom(B) - {B}
        strict = dom_set - {name}

        # idom = the strict dominator closest to B (not dominated by
        # any other strict dominator of B)
        for candidate in sorted(strict):  # sorted for determinism
            is_immediate = True
            for other in strict:
                if other != candidate and candidate in dom_sets.get(other, set()) - {other}:
                    is_immediate = False
                    break
            if is_immediate:
                idom[name] = candidate
                break

    return idom


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def print_dominators(
    cfg: CFG,
    dom_sets: dict[str, set[str]],
    idom_map: dict[str, str | None],
) -> None:
    """Print dominator sets and immediate dominators in a formatted table."""
    header = f"Dominator Analysis for: {cfg.func_name}"
    sep = "=" * len(header)
    print(header)
    print(sep)

    if not cfg.blocks:
        print("  (empty — no blocks)")
        print()
        return

    # Column widths for alignment
    max_name_len = max(len(name) for name in cfg.blocks)
    name_width = max(max_name_len, 5)

    for name in cfg.blocks:
        dom_set = dom_sets.get(name, set())
        i = idom_map.get(name)

        # Format dominator set as sorted list
        dom_list = sorted(dom_set)
        dom_str = ", ".join(dom_list) if dom_list else "∅"

        # Format idom
        idom_str = str(i) if i is not None else "None"
        is_entry = "[entry] " if name == cfg.entry else "       "

        print(
            f"{is_entry}{name:{name_width}}: "
            f"dom = {{{dom_str}}},  "
            f"idom = {idom_str}",
        )

    # Summary
    print()
    print(f"Blocks: {len(cfg.blocks)}")
    print(f"Fixed-point iterations: (computed)")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Toy CFG: Dominator Analysis (CHK Algorithm)",
    )
    parser.add_argument(
        "--program", "-p",
        choices=list(DEMOS.keys()),
        default="if_else",
        help="Demo program to analyze (default: if_else)",
    )
    args = parser.parse_args()

    program = DEMOS[args.program]
    func = program.functions[0]
    cfg = build_cfg(func)

    dom_sets = compute_dominators(cfg)
    idom_map = compute_idom(cfg, dom_sets)
    print_dominators(cfg, dom_sets, idom_map)


if __name__ == "__main__":
    main()
