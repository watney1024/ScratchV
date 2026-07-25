"""Tests for scratchv/ir/cfg.py — CFG Builder module.

Covers all data classes, graph construction, unreachable elimination,
dominator computation, natural-loop detection, and DOT output.
"""

from scratchv.ir.types import (
    Program,
    Function,
    BasicBlock,
    Instruction,
    OpCode,
    Value,
)
from scratchv.ir.cfg import (
    CFGNode,
    CFGEdge,
    EdgeType,
    CFG,
    CFGBuilder,
    NaturalLoop,
    to_dot,
)
from scratchv.frontend.dsl_parser import DSLParser
from scratchv.frontend.dsl_extended import ExtendedDSLParser


# ======================================================================
# Data-class construction tests
# ======================================================================


class TestCFGNode:
    """CFGNode creation and attribute defaults."""

    def test_create_node(self):
        node = CFGNode(name="entry", instructions=3, is_entry=True)
        assert node.name == "entry"
        assert node.instructions == 3
        assert node.is_entry is True
        assert node.is_exit is False
        assert node.terminator_opcode is None

    def test_exit_node(self):
        node = CFGNode(
            name="exit", instructions=1, is_exit=True,
            terminator_opcode="RETURN",
        )
        assert node.is_exit is True
        assert node.terminator_opcode == "RETURN"


class TestCFGEdge:
    """CFGEdge creation and EdgeType defaults."""

    def test_create_fallthrough_edge(self):
        edge = CFGEdge(source="A", target="B")
        assert edge.source == "A"
        assert edge.target == "B"
        assert edge.edge_type == EdgeType.FALLTHROUGH
        assert edge.condition is None

    def test_create_branch_edge(self):
        edge = CFGEdge(
            source="A", target="B",
            edge_type=EdgeType.BRANCH, condition="true",
        )
        assert edge.edge_type == EdgeType.BRANCH
        assert edge.condition == "true"

    def test_jump_edge(self):
        edge = CFGEdge(source="A", target="B", edge_type=EdgeType.JUMP)
        assert edge.edge_type == EdgeType.JUMP

    def test_call_edge(self):
        edge = CFGEdge(source="A", target="B", edge_type=EdgeType.CALL)
        assert edge.edge_type == EdgeType.CALL


# ======================================================================
# CFG graph-traversal tests
# ======================================================================


class TestCFG:
    """Successors, predecessors, reachable nodes."""

    def _make_cfg(self) -> CFG:
        """Helper: a simple 3-node diamond CFG."""
        cfg = CFG(function_name="test", entry="entry")
        cfg.nodes["entry"] = CFGNode(name="entry", instructions=1)
        cfg.nodes["then"] = CFGNode(name="then", instructions=1)
        cfg.nodes["else"] = CFGNode(name="else", instructions=1)
        cfg.nodes["merge"] = CFGNode(
            name="merge", instructions=1, is_exit=True,
            terminator_opcode="RETURN",
        )
        cfg.edges = [
            CFGEdge(source="entry", target="then",
                    edge_type=EdgeType.BRANCH, condition="true"),
            CFGEdge(source="entry", target="else",
                    edge_type=EdgeType.BRANCH, condition="false"),
            CFGEdge(source="then", target="merge",
                    edge_type=EdgeType.JUMP),
            CFGEdge(source="else", target="merge",
                    edge_type=EdgeType.JUMP),
        ]
        return cfg

    def test_successors(self):
        cfg = self._make_cfg()
        succs = cfg.successors("entry")
        assert set(succs) == {"then", "else"}
        assert cfg.successors("merge") == []

    def test_predecessors(self):
        cfg = self._make_cfg()
        preds = cfg.predecessors("merge")
        assert set(preds) == {"then", "else"}
        assert cfg.predecessors("entry") == []

    def test_reachable_nodes(self):
        cfg = self._make_cfg()
        reachable = cfg.reachable_nodes
        assert reachable == {"entry", "then", "else", "merge"}

    def test_reachable_with_unreachable_node(self):
        """Nodes not reachable from entry should be excluded."""
        cfg = self._make_cfg()
        cfg.nodes["dead"] = CFGNode(name="dead")
        reachable = cfg.reachable_nodes
        assert "dead" not in reachable

    def test_reachable_empty_cfg(self):
        cfg = CFG(function_name="empty")
        assert cfg.reachable_nodes == set()

    def test_reachable_entry_not_in_nodes(self):
        cfg = CFG(function_name="orphan", entry="missing")
        cfg.nodes["other"] = CFGNode(name="other")
        assert cfg.reachable_nodes == set()


# ======================================================================
# CFGBuilder integration tests
# ======================================================================


class TestCFGBuilder:
    """CFG construction from parsed DSL programs."""

    def test_simple_program(self):
        """c = add(a, b); return c  →  1 block + exit."""
        dsl = """
        c = add(a, b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfgs = builder.build()
        assert "main" in cfgs
        cfg = cfgs["main"]
        assert cfg.function_name == "main"
        assert "entry" in cfg.nodes
        assert len(cfg.nodes) >= 1
        assert cfg.nodes["entry"].is_entry is True
        # The terminator should be RETURN
        assert cfg.nodes["entry"].is_exit is True
        assert cfg.nodes["entry"].terminator_opcode == "RETURN"

    def test_multiple_blocks(self):
        """FOR loop — FOR/ENDFOR inside a single block; at least 1 node."""
        dsl = """
        for i = 0, 4
            c = add(a, b)
        endfor
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfgs = builder.build()
        cfg = cfgs["main"]
        assert len(cfg.nodes) >= 1

    def test_empty_program(self):
        """Program() with no functions → empty result, no crash."""
        program = Program()
        builder = CFGBuilder(program)
        cfgs = builder.build()
        assert len(cfgs) == 0

    def test_multiple_statements(self):
        """Multiple sequential instructions produce a single block."""
        dsl = """
        a = add(x, y)
        b = mul(a, z)
        c = relu(b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        assert len(cfg.nodes) == 1
        assert cfg.nodes["entry"].instructions == 4

    def test_two_functions(self):
        """Building CFGs for a program with two functions."""
        program = Program()
        f1 = Function("f1")
        f1.add_block(BasicBlock("entry"))
        f1.blocks[0].add(Instruction(OpCode.RETURN))
        program.add_function(f1)

        f2 = Function("f2")
        f2.add_block(BasicBlock("entry"))
        f2.blocks[0].add(Instruction(OpCode.RETURN))
        program.add_function(f2)

        builder = CFGBuilder(program)
        cfgs = builder.build()
        assert "f1" in cfgs
        assert "f2" in cfgs
        assert len(cfgs) == 2

    def test_successors(self):
        """Successors list from a simple program."""
        dsl = """
        c = add(a, b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        succs = cfg.successors("entry")
        assert isinstance(succs, list)

    def test_predecessors(self):
        """Predecessors list from a simple program."""
        dsl = """
        c = add(a, b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        preds = cfg.predecessors("entry")
        assert isinstance(preds, list)

    def test_reachable_nodes(self):
        """Reachable nodes from a simple program."""
        dsl = """
        c = add(a, b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        reachable = cfg.reachable_nodes
        assert "entry" in reachable


# ======================================================================
# Unreachable code elimination
# ======================================================================


class TestUnreachable:
    """Tests for eliminate_unreachable — verifies actual deletion."""

    def _make_program_with_dead_block(self) -> tuple[Program, str]:
        """Create a program where one block is unreachable.

        Structure:
            entry: BR block_a
            block_a: RETURN
            dead: ADD (no incoming edge)

        Returns (program, dead_block_name).
        """
        program = Program()
        func = Function("main")

        entry = BasicBlock("entry")
        entry.add(Instruction(OpCode.BR, target="block_a"))
        func.add_block(entry)

        block_a = BasicBlock("block_a")
        block_a.add(Instruction(OpCode.RETURN))
        func.add_block(block_a)

        dead = BasicBlock("dead")
        dead.add(Instruction(
            OpCode.ADD,
            dest=Value(name="v1"),
            operands=[Value(name="a"), Value(name="b")],
        ))
        func.add_block(dead)

        program.add_function(func)
        return program, "dead"

    def test_eliminate_unreachable(self):
        """Unreachable block is detected and removed from func.blocks."""
        program, dead_name = self._make_program_with_dead_block()
        func = program.functions[0]
        assert len(func.blocks) == 3  # entry, block_a, dead

        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        unreachable = builder.eliminate_unreachable(cfg)

        assert dead_name in unreachable
        assert dead_name not in cfg.nodes
        # Edge from entry→block_a should remain
        assert len(cfg.edges) == 1
        assert cfg.edges[0].source == "entry"
        assert cfg.edges[0].target == "block_a"
        # Function blocks must actually be reduced
        assert len(func.blocks) == 2
        block_names = {b.name for b in func.blocks}
        assert dead_name not in block_names

    def test_all_reachable(self):
        """Simple program with no unreachable blocks."""
        dsl = """
        c = add(a, b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        unreachable = builder.eliminate_unreachable(cfg)
        assert len(unreachable) == 0

    def test_unreachable_not_in_cfg_nodes(self):
        """After elimination, cfg.nodes no longer contains dead blocks."""
        program, dead_name = self._make_program_with_dead_block()
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        before = set(cfg.nodes.keys())
        unreachable = builder.eliminate_unreachable(cfg)
        after = set(cfg.nodes.keys())
        assert dead_name in unreachable
        assert dead_name in before
        assert dead_name not in after
        assert after == before - unreachable

    def test_no_elimination_without_build(self):
        """Eliminate on a hand-constructed CFG still returns the right set."""
        cfg = CFG(function_name="orphan")
        cfg.nodes["entry"] = CFGNode(name="entry")
        cfg.nodes["dead"] = CFGNode(name="dead")
        cfg.entry = "entry"

        builder = CFGBuilder(Program())
        unreachable = builder.eliminate_unreachable(cfg)
        assert "dead" in unreachable
        assert "dead" not in cfg.nodes  # still removed from cfg


# ======================================================================
# Dominator tree tests
# ======================================================================


class TestDominators:
    """Dominator-set and immediate-dominator computation."""

    def _make_diamond_cfg(self) -> CFG:
        """Diamond CFG: entry → {then, else} → merge → exit."""
        cfg = CFG(function_name="diamond", entry="entry")
        for name in ("entry", "then", "else", "merge", "exit"):
            cfg.nodes[name] = CFGNode(name=name)
        cfg.edges = [
            CFGEdge(source="entry", target="then",
                    edge_type=EdgeType.BRANCH, condition="true"),
            CFGEdge(source="entry", target="else",
                    edge_type=EdgeType.BRANCH, condition="false"),
            CFGEdge(source="then", target="merge", edge_type=EdgeType.JUMP),
            CFGEdge(source="else", target="merge", edge_type=EdgeType.JUMP),
            CFGEdge(source="merge", target="exit", edge_type=EdgeType.JUMP),
        ]
        return cfg

    def test_entry_dominates_all(self):
        """The entry block dominates every block."""
        cfg = self._make_diamond_cfg()
        dom = CFGBuilder(Program()).compute_dominators(cfg)
        for name in cfg.nodes:
            assert "entry" in dom[name]

    def test_entry_self_dominates(self):
        """Entry dominates itself."""
        cfg = self._make_diamond_cfg()
        dom = CFGBuilder(Program()).compute_dominators(cfg)
        assert "entry" in dom["entry"]

    def test_merge_not_dominate_else(self):
        """Merge does NOT dominate 'else' (path through entry→then→merge
        never reaches 'else')."""
        cfg = self._make_diamond_cfg()
        dom = CFGBuilder(Program()).compute_dominators(cfg)
        assert "merge" not in dom["else"]

    def test_immediate_dominator_entry(self):
        """Entry block has no immediate dominator."""
        cfg = self._make_diamond_cfg()
        idom = CFGBuilder(Program()).compute_dominator_tree(cfg)
        assert idom["entry"] is None

    def test_immediate_dominator_diamond(self):
        """Both 'then' and 'else' are immediately dominated by 'entry'."""
        cfg = self._make_diamond_cfg()
        idom = CFGBuilder(Program()).compute_dominator_tree(cfg)
        assert idom["then"] == "entry"
        assert idom["else"] == "entry"

    def test_dominator_tree(self):
        """Verify all entries in the dominator tree."""
        cfg = self._make_diamond_cfg()
        idom = CFGBuilder(Program()).compute_dominator_tree(cfg)
        assert len(idom) == 5
        assert idom["entry"] is None
        assert idom["then"] == "entry"
        assert idom["else"] == "entry"
        # merge is only reached via then/else, so entry is the idom
        assert idom["merge"] == "entry"
        assert idom["exit"] in ("merge", "entry")

    def test_dominators_empty_cfg(self):
        """Empty CFG → empty dict."""
        cfg = CFG(function_name="empty")
        dom = CFGBuilder(Program()).compute_dominators(cfg)
        assert dom == {}


# ======================================================================
# Natural-loop detection tests
# ======================================================================


class TestLoopDetection:
    """Natural loop detection via dominator-based back-edge analysis."""

    def test_no_loops(self):
        """Simple straight-line program → no loops."""
        dsl = """
        c = add(a, b)
        return c
        """
        parser = DSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        loops = builder.detect_loops(cfg)
        assert len(loops) == 0

    def test_detect_single_loop(self):
        """While loop from ExtendedDSLParser should produce ≥1 loop."""
        dsl = """
        while (i < 10):
            n = add(n, 1)
        endwhile
        return n
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        loops = builder.detect_loops(cfg)
        assert len(loops) >= 1
        # Verify loop structure
        loop = loops[0]
        assert loop.header is not None
        assert len(loop.back_edges) >= 1

    def test_self_loop(self):
        """A self-loop (single block → itself) should be detected."""
        cfg = CFG(function_name="selfloop", entry="header")
        cfg.nodes["header"] = CFGNode(name="header")
        cfg.edges = [
            CFGEdge(source="header", target="header",
                    edge_type=EdgeType.JUMP),
        ]
        builder = CFGBuilder(Program())
        loops = builder.detect_loops(cfg)
        assert len(loops) >= 1
        assert loops[0].header == "header"
        assert "header" in loops[0].body

    def test_detect_loops_nested(self):
        """Nested while loops → multiple loops."""
        dsl = """
        while (i < 10):
            while (j < 5):
                acc = add(acc, x)
            endwhile
        endwhile
        return acc
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        loops = builder.detect_nested_loops(cfg)
        assert len(loops) >= 2
        # At least one loop should be the inner one (depth ≥ 1)
        depths = {l.nesting_depth for l in loops}
        assert 0 in depths  # outermost
        has_inner = any(l.nesting_depth >= 1 for l in loops)
        assert has_inner, "Expected at least one nested loop (depth >= 1)"

    def test_nested_loops_parent_child(self):
        """Nested loops should have parent/children relationships."""
        dsl = """
        while (i < 10):
            while (j < 5):
                acc = add(acc, x)
            endwhile
        endwhile
        return acc
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        loops = builder.detect_nested_loops(cfg)
        # At least one loop should be nested (depth > 0)
        assert any(l.parent is not None for l in loops), (
            "Expected at least one loop with a parent"
        )
        # For each child, its parent should list it as a child
        for child in loops:
            if child.parent is not None:
                parent = next(
                    (l for l in loops if l.header == child.parent), None
                )
                assert parent is not None, (
                    f"Parent {child.parent} not found"
                )
                assert child.header in parent.children, (
                    f"Child {child.header} not in parent {child.parent}'s children"
                )


# ======================================================================
# Extended DSL (if/else, while) CFG tests
# ======================================================================


class TestCFGWithIfElse:
    """CFG construction from ExtendedDSLParser."""

    def test_if_else_cfg(self):
        """if/else → ≥4 nodes, ≥2 JUMP edges."""
        dsl = """
        if (a > b):
            c = add(a, b)
        else:
            c = mul(a, b)
        endif
        return c
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        # if/else produces entry + then + else + merge + (possible extra)
        assert len(cfg.nodes) >= 4
        # Should have at least 2 JUMP edges (then→merge, else→merge)
        jump_edges = [e for e in cfg.edges
                      if e.edge_type == EdgeType.JUMP]
        assert len(jump_edges) >= 2
        # Should have at least 1 BRANCH edge (condition in entry)
        branch_edges = [e for e in cfg.edges
                        if e.edge_type == EdgeType.BRANCH]
        assert len(branch_edges) >= 1

    def test_while_cfg(self):
        """while loop → ≥3 nodes, ≥1 JUMP edge, at least 1 loop."""
        dsl = """
        while (i < 10):
            acc = add(acc, x)
        endwhile
        return acc
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        assert len(cfg.nodes) >= 3
        jump_edges = [e for e in cfg.edges
                      if e.edge_type == EdgeType.JUMP]
        assert len(jump_edges) >= 1
        # Should have a back edge (loop)
        loops = builder.detect_loops(cfg)
        assert len(loops) >= 1

    def test_empty_if(self):
        """if without else → at least 3 nodes."""
        dsl = """
        if (a > b):
            c = add(a, b)
        endif
        return c
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        assert len(cfg.nodes) >= 3

    def test_multi_branch_cfg(self):
        """Nested if inside while → complex CFG without crash."""
        dsl = """
        while (i < 10):
            if (i > 5):
                acc = add(acc, 1)
            else:
                acc = add(acc, 2)
            endif
        endwhile
        return acc
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        assert len(cfg.nodes) >= 5


# ======================================================================
# NaturalLoop dataclass tests
# ======================================================================


class TestNaturalLoop:
    """NaturalLoop construction and attribute access."""

    def test_create_loop(self):
        loop = NaturalLoop(
            header="loop_hdr",
            body={"loop_hdr", "loop_body"},
            back_edges=[("loop_body", "loop_hdr")],
        )
        assert loop.header == "loop_hdr"
        assert "loop_body" in loop.body
        assert len(loop.back_edges) == 1
        assert loop.nesting_depth == 0
        assert loop.parent is None
        assert loop.children == []

    def test_nested_loop_depth(self):
        inner = NaturalLoop(
            header="inner_hdr",
            nesting_depth=1,
            parent="outer_hdr",
        )
        assert inner.nesting_depth == 1
        assert inner.parent == "outer_hdr"

    def test_loop_with_children(self):
        outer = NaturalLoop(
            header="outer",
            body={"outer", "inner"},
            children=["inner"],
        )
        assert "inner" in outer.children
        assert outer.parent is None

    def test_default_attributes(self):
        loop = NaturalLoop(header="hdr")
        assert loop.body == set()
        assert loop.back_edges == []
        assert loop.nesting_depth == 0


# ======================================================================
# DOT output tests
# ======================================================================


class TestCFGToDot:
    """Graphviz DOT output generation."""

    def _make_simple_cfg(self) -> CFG:
        cfg = CFG(function_name="main", entry="entry")
        cfg.nodes["entry"] = CFGNode(
            name="entry", instructions=2, is_entry=True,
            terminator_opcode="RETURN",
        )
        return cfg

    def test_to_dot_basic(self):
        """Basic DOT output contains digraph header and node."""
        cfg = self._make_simple_cfg()
        dot = cfg.to_dot()
        assert "digraph" in dot
        assert 'CFG_main' in dot
        assert "entry" in dot
        assert "}" in dot

    def test_to_dot_highlight_loops(self):
        """Highlighting loops produces lightskyblue in output."""
        dsl = """
        while (i < 10):
            acc = add(acc, x)
        endwhile
        return acc
        """
        parser = ExtendedDSLParser()
        program = parser.parse(dsl)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        dot = to_dot(cfg, highlight_loops=True)
        assert "digraph" in dot
        # The loop header node should have lightskyblue fill
        assert "lightskyblue" in dot

    def test_to_dot_no_highlight(self):
        """Without highlighting, no lightskyblue appears."""
        cfg = self._make_simple_cfg()
        dot = cfg.to_dot()
        assert "lightskyblue" not in dot

    def test_to_dot_edge_styles(self):
        """Branch edges produce dashed blue and jump edges solid red."""
        cfg = CFG(function_name="test_edge", entry="entry")
        cfg.nodes["entry"] = CFGNode(
            name="entry", instructions=0,
            terminator_opcode="BR_IF", is_entry=True,
        )
        cfg.nodes["then"] = CFGNode(name="then", instructions=0)
        cfg.nodes["merge"] = CFGNode(
            name="merge", instructions=0, is_exit=True,
            terminator_opcode="RETURN",
        )
        cfg.edges = [
            CFGEdge(source="entry", target="then",
                    edge_type=EdgeType.BRANCH, condition="true"),
            CFGEdge(source="then", target="merge",
                    edge_type=EdgeType.JUMP),
        ]
        dot = cfg.to_dot()
        # BRANCH edge → dashed, blue
        assert "style=dashed" in dot
        assert "color=blue" in dot
        # condition label
        assert "true" in dot

    def test_to_dot_global_function(self):
        """Global to_dot() works the same as cfg.to_dot()."""
        cfg = self._make_simple_cfg()
        dot1 = cfg.to_dot()
        dot2 = to_dot(cfg)
        assert dot1 == dot2

    def test_to_dot_exit_node_colour(self):
        """Exit node has lightcoral."""
        cfg = CFG(function_name="test", entry="entry")
        cfg.nodes["entry"] = CFGNode(
            name="entry", instructions=1, is_entry=True,
        )
        cfg.nodes["exit"] = CFGNode(
            name="exit", instructions=1, is_exit=True,
            terminator_opcode="RETURN",
        )
        cfg.edges = [
            CFGEdge(source="entry", target="exit",
                    edge_type=EdgeType.FALLTHROUGH),
        ]
        dot = cfg.to_dot()
        assert "lightcoral" in dot


# ======================================================================
# Integration sanity checks
# ======================================================================


class TestExport:
    """Verify symbols are accessible via scratchv.ir."""

    def test_cfg_imported(self):
        """CFG and friends are available via scratchv.ir."""
        import scratchv.ir
        assert hasattr(scratchv.ir, "CFGBuilder")
        assert hasattr(scratchv.ir, "CFG")
        assert hasattr(scratchv.ir, "CFGNode")
        assert hasattr(scratchv.ir, "CFGEdge")
        assert hasattr(scratchv.ir, "EdgeType")
        assert hasattr(scratchv.ir, "NaturalLoop")
        assert hasattr(scratchv.ir, "to_dot")


class TestRegression:
    """Regression tests for edge cases found during development."""

    def test_empty_block_no_crash(self):
        """Empty basic block should not crash CFG building."""
        program = Program()
        func = Function("main")
        func.add_block(BasicBlock("entry"))  # empty block
        program.add_function(func)
        builder = CFGBuilder(program)
        cfg = builder.build()["main"]
        assert "entry" in cfg.nodes
        assert cfg.nodes["entry"].instructions == 0

    def test_dominator_with_missing_predecessor(self):
        """Blocks with no predecessors should not crash dominator computation."""
        cfg = CFG(function_name="orphan", entry="entry")
        cfg.nodes["entry"] = CFGNode(name="entry")
        cfg.nodes["orphan"] = CFGNode(name="orphan")  # no edges to it
        cfg.edges = []  # no edges at all
        builder = CFGBuilder(Program())
        dom = builder.compute_dominators(cfg)
        assert "entry" in dom
        assert "orphan" in dom
