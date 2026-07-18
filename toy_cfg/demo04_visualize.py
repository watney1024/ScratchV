"""demo04_visualize.py — Toy CFG: Graphviz DOT Format Output and PNG Rendering

Generates Graphviz DOT format from a CFG data structure, with colored
nodes and edges to visualize control flow. Optionally renders to PNG
via the `dot` command-line tool (Graphviz).

Node colors:
  - Entry block:        lightgreen
  - Exit blocks (no outgoing edges): lightcoral
  - Unreachable blocks: lightgray (dashed border, with --show-unreachable)
  - Normal blocks:      white

Edge colors:
  - BRANCH edges ("true"/"false"/"body"): blue dashed with label
  - JUMP edges (none label): red solid

Usage:
    python toy_cfg/demo04_visualize.py --program if_else --output cfg.dot
    python toy_cfg/demo04_visualize.py --program while_loop --render cfg.png
    python toy_cfg/demo04_visualize.py --program if_else --output cfg.dot --render cfg.png
    python toy_cfg/demo04_visualize.py --program unreachable --show-unreachable
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from toy_cfg.demo01_build_blocks import BasicBlock
from toy_cfg.demo02_build_cfg import build_cfg, CFG, DEMOS


# ---------------------------------------------------------------------------
# DOT generation
# ---------------------------------------------------------------------------

def find_unreachable(cfg: CFG) -> set[str]:
    """Return set of block names that are NOT reachable from entry.

    Uses DFS from entry block. Any block not visited is unreachable.
    Returns an empty set if the CFG has no blocks.
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
        block = cfg.blocks.get(name)
        if block and block.exits_to:
            for target, _ in block.exits_to:
                if target in cfg.blocks and target not in visited:
                    stack.append(target)

    all_blocks = set(cfg.blocks.keys())
    return all_blocks - visited


def cfg_to_dot(cfg: CFG, show_unreachable: bool = False) -> str:
    """Generate Graphviz DOT format string from a CFG.

    Produces a 'digraph' with:
      - Box-shaped nodes, each labeled with block name + instruction summary.
      - Entry node shaded lightgreen.
      - Exit nodes (no outgoing exits) shaded lightcoral.
      - BRANCH edges ("true"/"false"/"body") as blue dashed lines with label.
      - JUMP/FALLTHROUGH edges (no label) as red solid lines.
      - When *show_unreachable* is True, unreachable blocks are marked with
        gray fill and dashed border.

    Returns an empty graph (no nodes) if the CFG has no blocks.
    """
    lines = [f'digraph "CFG_{cfg.func_name}" {{', '  rankdir=TB;']

    # Pre-compute unreachable blocks if requested
    unreachable: set[str] = set()
    if show_unreachable:
        unreachable = find_unreachable(cfg)

    # --- Node definitions ---
    for name, block in cfg.blocks.items():
        # Determine fill color
        if show_unreachable and name in unreachable:
            color = "lightgray"
        elif name == cfg.entry:
            color = "lightgreen"
        elif block.exits_to is not None and len(block.exits_to) == 0:
            color = "lightcoral"
        else:
            color = "white"

        # Determine style: unreachable blocks get "filled,dashed"
        if show_unreachable and name in unreachable:
            dot_style = '"filled,dashed"'
        else:
            dot_style = "filled"

        # Build label: name + instruction count (+ exit count if set)
        inst_count = len(block.instructions)
        label = f"{name}\\n({inst_count} inst"
        if block.exits_to is not None:
            label += f", {len(block.exits_to)} exit(s)"
        if show_unreachable and name in unreachable:
            label += ", UNREACHABLE"
        label += ")"

        lines.append(
            f'  "{name}" [label="{label}", shape=box, style={dot_style}, '
            f'fillcolor={color}];'
        )

    # --- Edge definitions ---
    for name, block in cfg.blocks.items():
        if not block.exits_to:
            continue
        for target, edge_label in block.exits_to:
            if edge_label in ("true", "false", "body"):
                # BRANCH edge: blue dashed with condition label
                lines.append(
                    f'  "{name}" -> "{target}" '
                    f'[style=dashed, color=blue, label="{edge_label}"];'
                )
            else:
                # JUMP or FALLTHROUGH edge (None label): red solid
                lines.append(
                    f'  "{name}" -> "{target}" '
                    f'[style=solid, color=red];'
                )

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output / rendering
# ---------------------------------------------------------------------------

def render_dot(dot_content: str, dot_path: str, png_path: str | None = None) -> None:
    """Write DOT content to a file and optionally render to PNG via ``dot``.

    The ``.dot`` file is always written. If *png_path* is provided and the
    ``dot`` binary is available, it is additionally rendered to a PNG image.
    """
    # Always write the .dot file
    with open(dot_path, "w") as f:
        f.write(dot_content)
    print(f"DOT file saved: {dot_path}")

    if png_path is None:
        return

    # Check whether the dot binary is available
    try:
        subprocess.run(["dot", "-V"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(
            f"Warning: 'dot' (Graphviz) is not installed. "
            f"Skipping PNG rendering.\n"
            f"  To render manually: dot -Tpng {dot_path} -o {png_path}",
        )
        return

    result = subprocess.run(
        ["dot", "-Tpng", dot_path, "-o", png_path],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"PNG rendered: {png_path}")
    else:
        print(f"Error rendering PNG:\n{result.stderr}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Toy CFG: Graphviz DOT Format Output and PNG Rendering",
    )
    parser.add_argument(
        "--program", "-p",
        choices=list(DEMOS.keys()),
        default="if_else",
        help="Demo program to analyze (default: if_else)",
    )
    parser.add_argument(
        "--output", "-o",
        default="cfg.dot",
        help="Output DOT file path (default: cfg.dot)",
    )
    parser.add_argument(
        "--render", "-r",
        nargs="?",
        const="cfg.png",
        default=None,
        metavar="PNG_PATH",
        help="Render PNG via dot (default: cfg.png)",
    )
    parser.add_argument(
        "--show-unreachable", action="store_true",
        help="Highlight unreachable blocks in DOT output",
    )
    args = parser.parse_args()

    program = DEMOS[args.program]
    func = program.functions[0]
    cfg = build_cfg(func)

    dot_content = cfg_to_dot(cfg, show_unreachable=args.show_unreachable)
    render_dot(dot_content, args.output, args.render)


if __name__ == "__main__":
    main()
