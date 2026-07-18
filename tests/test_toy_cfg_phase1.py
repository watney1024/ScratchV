"""Tests for toy CFG phase 1: basic block partition and edge construction.

Covers all control flow patterns handled by build_blocks/build_cfg:
empty function, single block, if-else, while loop, nested FOR,
multiple RETURN exits, jump-to-self, empty block between labels,
divergent branches, and dangling target validation.
"""

import pytest

from scratchv.ir.builder import IRBuilder
from toy_cfg.demo01_build_blocks import BasicBlock, build_blocks, DEMOS
from toy_cfg.demo02_build_cfg import build_cfg, validate_cfg, CFG
from toy_cfg.demo04_visualize import cfg_to_dot, find_unreachable


class TestCFGEdgeBuilding:
    """Tests for block partition and CFG edge construction."""

    # ------------------------------------------------------------------
    # (a) empty function
    # ------------------------------------------------------------------

    def test_empty_function(self):
        """Empty function → single empty block, 0 exits."""
        builder = IRBuilder()
        builder.new_function("empty")
        builder.new_block("entry")
        cfg = build_cfg(builder.program.functions[0])
        assert len(cfg.blocks) == 1
        assert cfg.entry == "entry"
        block = cfg.blocks["entry"]
        assert len(block.instructions) == 0
        # No terminator and no next block → exits_to == []
        assert block.exits_to == []

    # ------------------------------------------------------------------
    # (b) single block (straight-line, no branch)
    # ------------------------------------------------------------------

    def test_single_block(self):
        """No control flow → single block with no terminator (exits_to = [])."""
        builder = IRBuilder()
        builder.new_function("single")
        builder.new_block("entry")
        a = builder.make_value("a")
        b = builder.make_value("b")
        builder.add(a, b)
        builder.sub(a, b)
        cfg = build_cfg(builder.program.functions[0])
        assert len(cfg.blocks) == 1
        assert cfg.entry == "entry"
        block = cfg.blocks["entry"]
        # 2 non-terminator instructions, no next block → empty exits
        assert len(block.instructions) == 2
        assert block.exits_to == []

    # ------------------------------------------------------------------
    # (c) if-else with BR_IF (4 blocks)
    # ------------------------------------------------------------------

    def test_if_else(self):
        """BR_IF → 4 blocks with correct edge types (true/false)."""
        builder = IRBuilder()
        builder.new_function("if_else")
        builder.new_block("entry")
        cond = builder.make_value("cond")
        builder.br_if(cond, "then", "else")
        builder.new_block("then")
        v = builder.load_const(1)
        builder.br("end")
        builder.new_block("else")
        w = builder.load_const(2)
        builder.br("end")
        builder.new_block("end")
        result = builder.make_value("result")
        builder.ret(result)
        cfg = build_cfg(builder.program.functions[0])
        # 4 blocks: entry, then, else, end
        assert len(cfg.blocks) == 4
        assert cfg.entry == "entry"
        # entry: BR_IF → then (true), else (false)
        assert cfg.blocks["entry"].exits_to == [
            ("then", "true"),
            ("else", "false"),
        ]
        # then: BR → end
        assert cfg.blocks["then"].exits_to == [("end", None)]
        # else: BR → end
        assert cfg.blocks["else"].exits_to == [("end", None)]
        # end: RETURN → no exits
        assert cfg.blocks["end"].exits_to == []
        # validate passes without error
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (d) while loop with FOR/ENDFOR (3 blocks)
    # ------------------------------------------------------------------

    def test_while_loop(self):
        """FOR/ENDFOR → 3 blocks, FOR has body+exit, ENDFOR jumps back."""
        builder = IRBuilder()
        builder.new_function("while_loop")
        builder.new_block("entry")
        iv = builder.for_loop(0, 10, 1)
        builder.new_block("body")
        v = builder.add(iv, iv)
        builder.endfor()
        builder.new_block("end")
        result = builder.make_value("result")
        builder.ret(result)
        cfg = build_cfg(builder.program.functions[0])
        # 3 blocks: entry, body, end
        assert len(cfg.blocks) == 3
        assert cfg.entry == "entry"
        # entry (FOR): next block = body (body), after ENDFOR = end (None)
        assert cfg.blocks["entry"].exits_to == [
            ("body", "body"),
            ("end", None),
        ]
        # body (ENDFOR): jump back to entry
        assert cfg.blocks["body"].exits_to == [("entry", None)]
        # end (RETURN): no exits
        assert cfg.blocks["end"].exits_to == []
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (e) nested FOR (correct FOR/ENDFOR matching)
    # ------------------------------------------------------------------

    def test_nested_for(self):
        """Nested FOR → correct FOR/ENDFOR matching, no cross-nesting."""
        builder = IRBuilder()
        builder.new_function("nested_for")
        builder.new_block("entry")
        iv1 = builder.for_loop(0, 5, 1)
        builder.new_block("outer_body")
        x = builder.make_value("x")
        builder.add(x, x)
        builder.new_block("inner_entry")
        iv2 = builder.for_loop(0, 3, 1)
        builder.new_block("inner_body")
        y = builder.make_value("y")
        builder.add(y, y)
        builder.endfor()
        builder.new_block("outer_end")
        z = builder.make_value("z")
        builder.add(z, z)
        builder.endfor()
        builder.new_block("end")
        builder.ret()
        cfg = build_cfg(builder.program.functions[0])
        # 6 blocks: entry, outer_body, inner_entry, inner_body, outer_end, end
        assert len(cfg.blocks) == 6
        assert cfg.entry == "entry"
        # entry (FOR outer): body = outer_body, exit = outer_end's successor = end
        assert cfg.blocks["entry"].exits_to == [
            ("outer_body", "body"),
            ("end", None),
        ]
        # outer_body (ADD): FALLTHROUGH to inner_entry
        assert cfg.blocks["outer_body"].exits_to == [("inner_entry", None)]
        # inner_entry (FOR inner): body = inner_body, exit = outer_end
        assert cfg.blocks["inner_entry"].exits_to == [
            ("inner_body", "body"),
            ("outer_end", None),
        ]
        # inner_body (ENDFOR inner): jump back to inner_entry
        assert cfg.blocks["inner_body"].exits_to == [("inner_entry", None)]
        # outer_end (ENDFOR outer): jump back to entry
        assert cfg.blocks["outer_end"].exits_to == [("entry", None)]
        # end (RETURN): no exits
        assert cfg.blocks["end"].exits_to == []
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (f) multiple RETURN exits
    # ------------------------------------------------------------------

    def test_multiple_returns(self):
        """Function with 2 RETURN blocks — both branch targets end with RETURN."""
        builder = IRBuilder()
        builder.new_function("multi_ret")
        builder.new_block("entry")
        cond = builder.make_value("cond")
        builder.br_if(cond, "ret1", "ret2")
        builder.new_block("ret1")
        v = builder.load_const(1)
        builder.ret(v)
        builder.new_block("ret2")
        w = builder.load_const(2)
        builder.ret(w)
        cfg = build_cfg(builder.program.functions[0])
        # 3 blocks: entry, ret1, ret2
        assert len(cfg.blocks) == 3
        assert cfg.entry == "entry"
        # entry: BR_IF → ret1 (true), ret2 (false)
        assert cfg.blocks["entry"].exits_to == [
            ("ret1", "true"),
            ("ret2", "false"),
        ]
        # ret1: RETURN → no exits
        assert cfg.blocks["ret1"].exits_to == []
        # ret2: RETURN → no exits
        assert cfg.blocks["ret2"].exits_to == []
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (g) jump-to-self
    # ------------------------------------------------------------------

    def test_jump_to_self(self):
        """BR to its own block → 1 block with self-loop edge."""
        builder = IRBuilder()
        builder.new_function("self_loop")
        builder.new_block("loop")
        builder.br("loop")
        cfg = build_cfg(builder.program.functions[0])
        assert len(cfg.blocks) == 1
        assert cfg.entry == "loop"
        block = cfg.blocks["loop"]
        # BR to itself → [(target, None)] where target == own name
        assert block.exits_to == [("loop", None)]
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (h) empty block between consecutive labels
    # ------------------------------------------------------------------

    def test_empty_block_between_labels(self):
        """Consecutive LABELs (empty IR block before non-empty) → FALLTHROUGH."""
        builder = IRBuilder()
        builder.new_function("empty_between")
        builder.new_block("empty_block")
        # No instructions in empty_block — just a label
        builder.new_block("next_block")
        a = builder.make_value("a")
        b = builder.make_value("b")
        builder.add(a, b)
        cfg = build_cfg(builder.program.functions[0])
        # 2 blocks: empty_block (empty), next_block (with ADD)
        assert len(cfg.blocks) == 2
        assert cfg.entry == "empty_block"
        # empty_block: no instructions, FALLTHROUGH to next_block
        empty = cfg.blocks["empty_block"]
        assert len(empty.instructions) == 0
        assert empty.exits_to == [("next_block", None)]
        # next_block: has ADD, no terminator, no next block → exits_to = []
        next_b = cfg.blocks["next_block"]
        assert len(next_b.instructions) == 1
        assert next_b.exits_to == []
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (i) divergent branches — both if/else branches RETURN
    # ------------------------------------------------------------------

    def test_divergent_branches(self):
        """Both if/else branches RETURN → no shared end block."""
        builder = IRBuilder()
        builder.new_function("divergent")
        builder.new_block("entry")
        cond = builder.make_value("cond")
        builder.br_if(cond, "then", "else")
        builder.new_block("then")
        v = builder.load_const(42)
        builder.ret(v)
        builder.new_block("else")
        w = builder.load_const(-1)
        builder.ret(w)
        cfg = build_cfg(builder.program.functions[0])
        # 3 blocks: entry, then, else — no end block
        assert len(cfg.blocks) == 3
        assert cfg.entry == "entry"
        # entry: BR_IF → then (true), else (false)
        assert cfg.blocks["entry"].exits_to == [
            ("then", "true"),
            ("else", "false"),
        ]
        # then: RETURN → no exits
        assert cfg.blocks["then"].exits_to == []
        # else: RETURN → no exits
        assert cfg.blocks["else"].exits_to == []
        validate_cfg(cfg)

    # ------------------------------------------------------------------
    # (j) dangling target validation
    # ------------------------------------------------------------------

    def test_dangling_target(self):
        """Nonexistent target in BR → ValueError from validate_cfg."""
        builder = IRBuilder()
        builder.new_function("dangling")
        builder.new_block("entry")
        builder.br("nonexistent")
        with pytest.raises(ValueError, match="dangling target"):
            build_cfg(builder.program.functions[0])


class TestCFGVisualization:
    """Tests for DOT format output and unreachable detection."""

    # ------------------------------------------------------------------
    # (a) / (f) DOT node count for if_else
    # ------------------------------------------------------------------

    def test_if_else_dot_has_4_nodes(self):
        """if-else → DOT has exactly 4 node definitions."""
        cfg = build_cfg(DEMOS["if_else"].functions[0])
        dot = cfg_to_dot(cfg)
        # Count only node lines (have 'label=' but no '->')
        node_lines = [l for l in dot.split('\n') if 'label=' in l and '->' not in l]
        assert len(node_lines) == 4, f"expected 4 nodes, got {len(node_lines)}"

    # ------------------------------------------------------------------
    # (b) show-unreachable on clean program → no gray
    # ------------------------------------------------------------------

    def test_clean_program_no_gray_nodes(self):
        """--show-unreachable on normal if-else → no gray blocks."""
        cfg = build_cfg(DEMOS["if_else"].functions[0])
        dot = cfg_to_dot(cfg, show_unreachable=True)
        assert 'lightgray' not in dot, "clean program should have no gray nodes"

    # ------------------------------------------------------------------
    # (c) show-unreachable on dead code → gray unreachable block
    # ------------------------------------------------------------------

    def test_unreachable_marked_gray_in_dot(self):
        """Unreachable blocks get gray fill + dashed in DOT."""
        cfg = build_cfg(DEMOS["unreachable"].functions[0])
        dot = cfg_to_dot(cfg, show_unreachable=True)
        assert 'lightgray' in dot, "unreachable block should be lightgray"
        assert 'dashed' in dot, "unreachable block should have dashed border"
        assert 'dead' in dot
        assert 'UNREACHABLE' in dot

    # ------------------------------------------------------------------
    # (d) unreachable set empty for normal programs
    # ------------------------------------------------------------------

    def test_if_else_no_unreachable(self):
        """Normal if-else → no unreachable blocks."""
        cfg = build_cfg(DEMOS["if_else"].functions[0])
        unreachable = find_unreachable(cfg)
        assert len(unreachable) == 0

    def test_empty_program_no_unreachable(self):
        """Empty program (single block) → no unreachable."""
        cfg = build_cfg(DEMOS["empty"].functions[0])
        unreachable = find_unreachable(cfg)
        assert len(unreachable) == 0

    def test_while_loop_no_unreachable(self):
        """While loop → no unreachable blocks."""
        cfg = build_cfg(DEMOS["while_loop"].functions[0])
        unreachable = find_unreachable(cfg)
        assert len(unreachable) == 0

    # ------------------------------------------------------------------
    # (e) unreachable set contains "dead"
    # ------------------------------------------------------------------

    def test_unreachable_demo_has_dead_block(self):
        """Program with dead code → 'dead' block is unreachable."""
        cfg = build_cfg(DEMOS["unreachable"].functions[0])
        unreachable = find_unreachable(cfg)
        assert "dead" in unreachable
        assert len(unreachable) == 1

    # ------------------------------------------------------------------
    # (g) empty program DOT: 1 node 0 edges
    # ------------------------------------------------------------------

    def test_empty_dot_one_node_zero_edges(self):
        """Empty program → 1 node, 0 edges in DOT."""
        cfg = build_cfg(DEMOS["empty"].functions[0])
        dot = cfg_to_dot(cfg)
        node_lines = [l for l in dot.split('\n') if 'label=' in l and '->' not in l]
        assert len(node_lines) == 1, f"expected 1 node, got {len(node_lines)}"
        assert '->' not in dot, "empty program should have no edges"

    # ------------------------------------------------------------------
    # DOT node styling: entry green, exit coral, edge colors
    # ------------------------------------------------------------------

    def test_entry_node_is_green(self):
        """Entry node has lightgreen fillcolor in DOT."""
        cfg = build_cfg(DEMOS["if_else"].functions[0])
        dot = cfg_to_dot(cfg)
        assert 'fillcolor=lightgreen' in dot

    def test_exit_node_is_coral(self):
        """Exit node (0 exits) has lightcoral fillcolor in DOT."""
        cfg = build_cfg(DEMOS["if_else"].functions[0])
        dot = cfg_to_dot(cfg)
        assert 'fillcolor=lightcoral' in dot

    def test_dot_edge_styling(self):
        """BRANCH edges are blue dashed with labels; JUMP edges are red solid."""
        cfg = build_cfg(DEMOS["if_else"].functions[0])
        dot = cfg_to_dot(cfg)
        assert 'color=blue' in dot
        assert 'style=dashed' in dot
        assert 'label="true"' in dot
        assert 'label="false"' in dot
        assert 'color=red' in dot
        assert 'style=solid' in dot

    def test_unreachable_without_flag_omits_gray(self):
        """Unreachable blocks NOT shown without --show-unreachable flag."""
        cfg = build_cfg(DEMOS["unreachable"].functions[0])
        dot = cfg_to_dot(cfg, show_unreachable=False)
        assert 'lightgray' not in dot
        assert 'UNREACHABLE' not in dot
