"""Control Flow Graph (CFG) builder for ScratchV IR.

Constructs CFGs from IR programs with support for:
- Basic block identification and edge construction
- Unreachable code elimination (DFS from entry, actual deletion from Function.blocks)
- Natural loop detection via dominator tree
- Graphviz DOT output for visualization (no binary dependency)
- Dominator tree computation via iterative data-flow

Edge types:
    FALLTHROUGH — Sequential transition to next block
    BRANCH      — Conditional branch (true/false)
    JUMP        — Unconditional jump
    CALL        — Function call (reserved, not yet generated)

Usage::

    from scratchv.ir.cfg import CFGBuilder

    builder = CFGBuilder(program)
    cfgs = builder.build()
    cfg = cfgs["main"]
    print(cfg.to_dot())

    # Eliminate unreachable blocks (deletes from Function.blocks)
    unreachable = builder.eliminate_unreachable(cfg)

    # Detect loops
    loops = builder.detect_loops(cfg)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from scratchv.ir.types import (
    OpCode,
    Program,
    Function,
)


# ---------------------------------------------------------------------------
# CFG edge type enum
# ---------------------------------------------------------------------------


class EdgeType(enum.Enum):
    """Types of edges in the control flow graph.

    Attributes:
        FALLTHROUGH: Sequential transition to the next basic block.
        BRANCH: Conditional branch (carries a "true"/"false" condition label).
        JUMP: Unconditional jump to a target block.
        CALL: Function call (reserved for future use).
    """
    FALLTHROUGH = "fallthrough"
    BRANCH = "branch"
    JUMP = "jump"
    CALL = "call"


# ---------------------------------------------------------------------------
# Core CFG dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CFGNode:
    """A node in the CFG, representing a single basic block.

    Attributes:
        name: Block name (corresponds to IR BasicBlock.name).
        instructions: Number of instructions in the block.
        is_entry: Whether this block is the function entry point.
        is_exit: Whether this block ends with a RETURN terminator.
        terminator_opcode: Name of the terminating instruction's opcode
            (e.g. "RETURN", "BR", "BR_IF"), or None if the block is empty
            or ends with a non-control-flow instruction.
    """
    name: str
    instructions: int = 0
    is_entry: bool = False
    is_exit: bool = False
    terminator_opcode: Optional[str] = None


@dataclass
class CFGEdge:
    """An edge connecting two basic blocks in a CFG.

    Attributes:
        source: Source basic block name.
        target: Target basic block name.
        edge_type: The type of control-flow transition.
        condition: Optional condition label (e.g. "true", "false" for
            conditional branches).
    """
    source: str
    target: str
    edge_type: EdgeType = EdgeType.FALLTHROUGH
    condition: Optional[str] = None


@dataclass
class CFG:
    """A Control Flow Graph for a single function.

    Attributes:
        function_name: Name of the function this CFG belongs to.
        nodes: Mapping from block name to CFGNode.
        edges: List of CFGEdge objects.
        entry: Name of the entry block.
    """
    function_name: str
    nodes: dict[str, CFGNode] = field(default_factory=dict)
    edges: list[CFGEdge] = field(default_factory=list)
    entry: str = "entry"

    # ------------------------------------------------------------------
    # Graph traversal
    # ------------------------------------------------------------------

    def successors(self, block_name: str) -> list[str]:
        """Return all successor block names for the given block.

        Args:
            block_name: Name of the source block.

        Returns:
            List of target block names reachable from *block_name*.
        """
        return [
            e.target for e in self.edges
            if e.source == block_name
        ]

    def predecessors(self, block_name: str) -> list[str]:
        """Return all predecessor block names for the given block.

        Args:
            block_name: Name of the target block.

        Returns:
            List of source block names that jump to *block_name*.
        """
        return [
            e.source for e in self.edges
            if e.target == block_name
        ]

    @property
    def reachable_nodes(self) -> set[str]:
        """The set of nodes reachable from the entry block via DFS.

        Complexity: O(V + E).
        """
        visited: set[str] = set()
        stack = [self.entry]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            if node not in self.nodes:
                continue
            visited.add(node)
            for succ in self.successors(node):
                if succ not in visited:
                    stack.append(succ)
        return visited

    # ------------------------------------------------------------------
    # DOT visualization (no graphviz binary required)
    # ------------------------------------------------------------------

    def to_dot(
        self,
        highlight_loops: bool = False,
        loop_headers: Optional[set[str]] = None,
    ) -> str:
        """Generate a Graphviz DOT format string for this CFG.

        Node labels show: block name, instruction count, and terminator opcode.
        Colours: entry → lightgreen, exit → lightcoral,
        loop header → lightskyblue, default → lightyellow.

        Args:
            highlight_loops: Ignored by this method; forwarded for API
                compatibility with the global :func:`to_dot`.
            loop_headers: Set of block names to highlight as loop headers.

        Returns:
            A string in Graphviz DOT format.
        """
        lines = [f'digraph "CFG_{self.function_name}" {{']
        lines.append('  rankdir=TB;')
        lines.append(
            '  node [shape=box, style=filled, fillcolor=lightyellow];'
        )

        loop_headers = loop_headers or set()

        for name, node in self.nodes.items():
            attrs: list[str] = []
            if node.is_entry:
                attrs.append('fillcolor=lightgreen')
            if node.is_exit:
                attrs.append('fillcolor=lightcoral')
            if name in loop_headers:
                attrs.append('fillcolor=lightskyblue')
            attr_str = ", ".join(attrs) if attrs else ""

            label = f"{name}\\n({node.instructions} inst)"
            if node.terminator_opcode:
                label += f"\\n[{node.terminator_opcode}]"

            attr_prefix = ", " + attr_str if attr_str else ""
            lines.append(
                f'  {name} [label="{label}"{attr_prefix}];'
            )

        for edge in self.edges:
            style = {
                EdgeType.BRANCH: 'style=dashed, color=blue',
                EdgeType.JUMP: 'style=solid, color=red',
                EdgeType.FALLTHROUGH: 'style=solid',
                EdgeType.CALL: 'style=dotted, color=purple',
            }.get(edge.edge_type, "")

            label = ""
            if edge.condition:
                label = f', label="{edge.condition}"'

            lines.append(
                f'  {edge.source} -> {edge.target} [{style}{label}];'
            )

        lines.append("}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Natural loop representation
# ---------------------------------------------------------------------------


@dataclass
class NaturalLoop:
    """A natural loop detected in a CFG.

    A natural loop has:
    - A **header** node that dominates all nodes in the loop body.
    - At least one **back edge** whose source is dominated by the header.
    - A **body** containing all nodes that can reach a back-edge source
      without passing through the header (plus the header itself).

    Attributes:
        header: The header block name (loop entry point).
        body: Set of block names in the loop body (includes *header*).
        back_edges: List of ``(source, header)`` back-edge pairs.
        nesting_depth: Nesting depth (0 = outermost).
        parent: Header of the enclosing loop, or *None*.
        children: Headers of loops directly nested inside this one.
    """
    header: str
    body: set[str] = field(default_factory=set)
    back_edges: list[tuple[str, str]] = field(default_factory=list)
    nesting_depth: int = 0
    parent: Optional[str] = None
    children: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CFGBuilder
# ---------------------------------------------------------------------------


class CFGBuilder:
    """Builds and analyzes control flow graphs from ScratchV IR Programs.

    Usage::

        builder = CFGBuilder(program)
        cfgs = builder.build()
        cfg = cfgs["main"]

        # Analysis
        unreachable = builder.eliminate_unreachable(cfg)
        idom = builder.compute_dominator_tree(cfg)
        loops = builder.detect_loops(cfg)
    """

    def __init__(self, program: Program):
        """Initialise the CFG builder.

        Args:
            program: A ScratchV IR Program containing one or more Functions.
        """
        self.program = program
        # Populated during build() so that eliminate_unreachable can find
        # the Function object to delete blocks from.
        self._func_map: dict[str, Function] = {}

    # ------------------------------------------------------------------
    # CFG construction
    # ------------------------------------------------------------------

    def build(self) -> dict[str, CFG]:
        """Build CFGs for all functions in the program.

        Returns:
            A dict mapping function name to its CFG.
        """
        cfgs: dict[str, CFG] = {}
        self._func_map = {}
        for func in self.program.functions:
            self._func_map[func.name] = func
            cfgs[func.name] = self._build_function_cfg(func)
        return cfgs

    def _build_function_cfg(self, func: Function) -> CFG:
        """Build a CFG for a single function from its basic blocks.

        Edge construction rules (see design doc §3.2):
            RETURN    → 0 outgoing edges
            BR        → 1 JUMP edge to the target
            BR_IF     → 2 BRANCH edges ("true" / "false" via comma-separated
                        target field)
            FOR/ENDFOR → pass (no edges added)
            otherwise → 1 FALLTHROUGH edge to the next block (if any)

        Args:
            func: The function to analyse.

        Returns:
            A CFG object for *func*.
        """
        cfg = CFG(function_name=func.name)

        if not func.blocks:
            return cfg

        cfg.entry = func.blocks[0].name

        # ---- Create nodes ------------------------------------------------
        for i, block in enumerate(func.blocks):
            is_entry = (i == 0)
            node = CFGNode(
                name=block.name,
                instructions=len(block.instructions),
                is_entry=is_entry,
                is_exit=False,
                terminator_opcode=None,
            )
            # Scan for a recognised control-flow terminator
            for instr in block.instructions:
                if instr.opcode in (
                    OpCode.RETURN,
                    OpCode.BR,
                    OpCode.BR_IF,
                    OpCode.FOR,
                    OpCode.ENDFOR,
                ):
                    node.terminator_opcode = instr.opcode.name
                    if instr.opcode == OpCode.RETURN:
                        node.is_exit = True

            cfg.nodes[block.name] = node

        # ---- Create edges -------------------------------------------------
        for i, block in enumerate(func.blocks):
            insts = block.instructions

            if not insts:
                # Empty block: fall through to the next (if any)
                if i + 1 < len(func.blocks):
                    cfg.edges.append(CFGEdge(
                        source=block.name,
                        target=func.blocks[i + 1].name,
                        edge_type=EdgeType.FALLTHROUGH,
                    ))
                continue

            last_instr = insts[-1]

            # BR — unconditional jump
            if last_instr.opcode == OpCode.BR:
                target = last_instr.target
                if target:
                    cfg.edges.append(CFGEdge(
                        source=block.name,
                        target=target,
                        edge_type=EdgeType.JUMP,
                    ))

            # BR_IF — conditional branch (target = "true_label,false_label")
            elif last_instr.opcode == OpCode.BR_IF:
                target = last_instr.target
                if target and "," in target:
                    true_target, false_target = target.split(",", 1)
                    cfg.edges.append(CFGEdge(
                        source=block.name,
                        target=true_target.strip(),
                        edge_type=EdgeType.BRANCH,
                        condition="true",
                    ))
                    cfg.edges.append(CFGEdge(
                        source=block.name,
                        target=false_target.strip(),
                        edge_type=EdgeType.BRANCH,
                        condition="false",
                    ))

            # RETURN — no outgoing edges
            elif last_instr.opcode == OpCode.RETURN:
                pass

            # FOR / ENDFOR — pass (no special edges)
            elif last_instr.opcode in (OpCode.FOR, OpCode.ENDFOR):
                pass

            # Everything else: fall through to the next block
            else:
                if i + 1 < len(func.blocks):
                    cfg.edges.append(CFGEdge(
                        source=block.name,
                        target=func.blocks[i + 1].name,
                        edge_type=EdgeType.FALLTHROUGH,
                    ))

        return cfg

    # ------------------------------------------------------------------
    # Unreachable code elimination  (with actual deletion)
    # ------------------------------------------------------------------

    def eliminate_unreachable(self, cfg: CFG) -> set[str]:
        """Eliminate unreachable blocks from the CFG **and** from
        ``Function.blocks`` in the original IR program.

        Uses DFS from the entry block to determine reachable nodes, then:
        1. Removes unreachable nodes from *cfg.nodes*.
        2. Removes edges involving unreachable nodes from *cfg.edges*.
        3. **Removes the corresponding BasicBlocks from the Function's
           block list** in the program.

        Args:
            cfg: The control flow graph to clean up.

        Returns:
            The set of eliminated block names (empty if all reachable).
        """
        reachable = cfg.reachable_nodes
        all_nodes = set(cfg.nodes.keys())
        unreachable = all_nodes - reachable

        if unreachable:
            # 1. Remove from cfg.nodes
            for name in unreachable:
                cfg.nodes.pop(name, None)

            # 2. Remove from cfg.edges
            cfg.edges = [
                e for e in cfg.edges
                if e.source not in unreachable
                and e.target not in unreachable
            ]

            # 3. Remove from Function.blocks in the IR program
            func = self._func_map.get(cfg.function_name)
            if func is not None:
                func.blocks = [
                    b for b in func.blocks
                    if b.name not in unreachable
                ]

        return unreachable

    # ------------------------------------------------------------------
    # Dominator tree computation  (iterative data-flow, O(V²))
    # ------------------------------------------------------------------

    def compute_dominators(self, cfg: CFG) -> dict[str, set[str]]:
        """Compute the dominator sets for every block in the CFG.

        A block *d* dominates block *b* if every path from the entry to *b*
        passes through *d*.  Uses the classic iterative data-flow algorithm.

        Args:
            cfg: The control flow graph.

        Returns:
            A dict mapping block name → set of block names it dominates.
        """
        all_nodes = set(cfg.nodes.keys())
        if not all_nodes:
            return {}

        # Initialise: entry dominates itself; all others are dominated by
        # every node (the conservative starting assumption).
        dom: dict[str, set[str]] = {}
        for name in all_nodes:
            if name != cfg.entry:
                dom[name] = all_nodes.copy()
            else:
                dom[name] = {cfg.entry}

        # Iterate until fixed point
        changed = True
        while changed:
            changed = False
            for node in all_nodes:
                if node == cfg.entry:
                    continue
                preds = cfg.predecessors(node)
                if not preds:
                    continue
                # Intersection of all predecessors' dom sets
                new_dom = dom[preds[0]].copy()
                for pred in preds[1:]:
                    new_dom &= dom[pred]
                new_dom.add(node)
                if new_dom != dom[node]:
                    dom[node] = new_dom
                    changed = True

        return dom

    def compute_dominator_tree(self, cfg: CFG) -> dict[str, Optional[str]]:
        """Compute the immediate dominator for each block.

        The **immediate dominator** of *b* (``idom(b)``) is the unique node
        that strictly dominates *b* but is not strictly dominated by any
        other strict dominator of *b*.

        Args:
            cfg: The control flow graph.

        Returns:
            A dict mapping block name → its immediate dominator name
            (or *None* for the entry block).
        """
        dom_sets = self.compute_dominators(cfg)
        idom: dict[str, Optional[str]] = {}

        for node, doms in dom_sets.items():
            if node == cfg.entry:
                idom[node] = None
                continue

            strict_doms = doms - {node}
            if not strict_doms:
                idom[node] = None
                continue

            # Find the strict dominator that does NOT strictly dominate
            # any other strict dominator — that is the "closest" one.
            idom[node] = None
            for d in strict_doms:
                is_immediate = True
                for other in strict_doms:
                    if other != d and d in (dom_sets[other] - {other}):
                        is_immediate = False
                        break
                if is_immediate:
                    idom[node] = d
                    break

        return idom

    # ------------------------------------------------------------------
    # Natural loop detection
    # ------------------------------------------------------------------

    def detect_loops(self, cfg: CFG) -> list[NaturalLoop]:
        """Detect natural loops in the CFG.

        A natural loop is identified by:
        1. A **back edge** ``m → n`` where *n* dominates *m*.
        2. The **loop body** consists of *n* plus every node that can reach
           *m* without passing through *n*.

        Self-loops (``source == header``) are also detected; their body is
        just *{header}*.

        Args:
            cfg: The control flow graph.

        Returns:
            A list of :class:`NaturalLoop` objects, one per back edge.
        """
        dom_sets = self.compute_dominators(cfg)
        back_edges: list[tuple[str, str]] = []

        # Find back edges: target dominates source (n dominates m for edge m→n)
        for edge in cfg.edges:
            if edge.target in dom_sets.get(edge.source, set()):
                back_edges.append((edge.source, edge.target))

        loops: list[NaturalLoop] = []
        for source, header in back_edges:
            # Gather body: all nodes that can reach *source* without
            # going through *header* (reverse traversal from source).
            body: set[str] = set()
            stack = [source]
            while stack:
                node = stack.pop()
                if node == header:
                    continue
                if node in body:
                    continue
                body.add(node)
                for pred in cfg.predecessors(node):
                    if pred not in body:
                        stack.append(pred)

            loop = NaturalLoop(
                header=header,
                body=body | {header},
                back_edges=[(source, header)],
            )
            loops.append(loop)

        return loops

    def detect_nested_loops(self, cfg: CFG) -> list[NaturalLoop]:
        """Detect loops and compute nesting relationships.

        A loop *L1* is nested inside *L2* when:
        - ``L1.header ∈ L2.body``
        - ``L1.body ⊆ L2.body``
        - *L1* and *L2* are different loops.
        - Their bodies are not identical (no duplicate reporting).

        Nesting depth: outer = 0, inner = outer + 1.

        Args:
            cfg: The control flow graph.

        Returns:
            A list of :class:`NaturalLoop` objects with ``parent``,
            ``children``, and ``nesting_depth`` populated.
        """
        loops = self.detect_loops(cfg)

        for i, outer in enumerate(loops):
            for j, inner in enumerate(loops):
                if i == j:
                    continue
                if (inner.header in outer.body
                        and inner.body.issubset(outer.body)):
                    if inner.body != outer.body:
                        inner.nesting_depth = outer.nesting_depth + 1
                        inner.parent = outer.header
                        outer.children.append(inner.header)

        return loops


# ---------------------------------------------------------------------------
# Standalone helper
# ---------------------------------------------------------------------------


def to_dot(
    cfg: CFG,
    highlight_loops: bool = False,
    loop_headers: Optional[set[str]] = None,
) -> str:
    """Generate a Graphviz DOT string for a CFG, with optional loop
    highlighting.

    When *highlight_loops* is *True* and *loop_headers* is *None*, loops
    are auto-detected using a temporary :class:`CFGBuilder`.

    Args:
        cfg: The CFG to visualise.
        highlight_loops: If *True*, highlight loop header nodes in blue.
        loop_headers: Explicit set of loop header block names (bypasses
            auto-detection).

    Returns:
        A Graphviz DOT format string.
    """
    if highlight_loops and loop_headers is None:
        # Auto-detect loops
        builder = CFGBuilder(Program())
        loops = builder.detect_loops(cfg)
        loop_headers = {loop.header for loop in loops}
    return cfg.to_dot(
        highlight_loops=highlight_loops, loop_headers=loop_headers
    )
