"""Tests for all 6 peephole rules (Toy Peephole Optimizer).

Rules under test:
  1. addi+addi fusion:  addi rd, rs, a; addi rd, rs, b → addi rd, rs, (a+b)
  2. li+addi fusion:    li rd, a; addi rd, rd, b → li rd, (a+b)
  3. beq x0→j:          beq x0/zero, x0/zero, label → j label
  4. mv swap:           mv x,y; mv y,x → both deleted
  5. mv chain:          mv a,b; mv c,a → mv c,b
  6. addi zero:         addi rd, rs, 0 → delete

See docs/topics/toy-peephole/RULES.md for design rationale.
"""

from toy_peephole.demo01_parser import parse_asm, lines_to_asm
from toy_peephole.demo02_engine import peephole_pass, get_default_rules

RULES = get_default_rules()  # 6 peephole rules


# ---------------------------------------------------------------------------
# Rule 1: addi+addi fusion
# ---------------------------------------------------------------------------

class TestAddiAddiFusion:
    """addi rd, rs, a; addi rd, rs, b → addi rd, rs, (a+b)."""

    def test_fusion_basic(self):
        """Two consecutive addi with same rd,rs → merged immediate."""
        asm = "  addi x1, x1, 3\n  addi x1, x1, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "8" in output  # 3 + 5 = 8
        assert output.count("addi") == 1  # merged

    def test_fusion_negative_imm(self):
        """Negative immediate fusion: 3 + (-5) = -2."""
        asm = "  addi x2, x2, 3\n  addi x2, x2, -5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "-2" in output  # 3 + (-5) = -2

    def test_no_fusion_different_rd(self):
        """Different rd → no fusion (no data dependency)."""
        asm = "  addi x1, x2, 3\n  addi x3, x4, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0

    def test_no_fusion_identical_ops(self):
        """Same rd but different rs → no fusion (condition checks both)."""
        asm = "  addi x1, x2, 3\n  addi x1, x3, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0

    def test_no_fusion_separate_blocks(self):
        """Non-consecutive addi → no fusion (pattern length mismatch)."""
        asm = "  addi x1, x1, 3\n  nop\n  addi x1, x1, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0


# ---------------------------------------------------------------------------
# Rule 2: li+addi fusion
# ---------------------------------------------------------------------------

class TestLiAddiFusion:
    """li rd, a; addi rd, rd, b → li rd, (a+b)."""

    def test_fusion_basic(self):
        """li + addi with same rd → merged immediate."""
        asm = "  li x1, 10\n  addi x1, x1, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "15" in output  # 10 + 5 = 15
        assert "li" in output
        assert "addi" not in output  # addi eliminated

    def test_fusion_zero_imm(self):
        """Zero immediate: 7 + 0 = 7."""
        asm = "  li x5, 7\n  addi x5, x5, 0\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "7" in output

    def test_no_fusion_no_chain(self):
        """No data dependency → no fusion."""
        asm = "  li x1, 10\n  addi x2, x3, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0

    def test_no_fusion_diff_regs(self):
        """li.rd != addi.rd → no fusion."""
        asm = "  li x1, 10\n  addi x2, x1, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0


# ---------------------------------------------------------------------------
# Rule 3: beq x0/zero → j
# ---------------------------------------------------------------------------

class TestBeqToJ:
    """beq x0/zero, x0/zero, label → j label."""

    def test_beq_x0_to_j(self):
        """beq x0, x0 → j."""
        asm = "  beq x0, x0, loop\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "j" in output
        assert "loop" in output
        assert "beq" not in output

    def test_beq_zero_alias(self):
        """beq zero, zero → j (zero alias)."""
        asm = "  beq zero, zero, end\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "j" in output
        assert "end" in output

    def test_beq_x0_zero_mixed(self):
        """beq x0, zero → j (mixed aliases)."""
        asm = "  beq x0, zero, target\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "j target" in output

    def test_no_match_nonzero(self):
        """beq with non-zero register → no match."""
        asm = "  beq x1, x0, loop\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0

    def test_no_match_both_nonzero(self):
        """beq with both non-zero registers → no match."""
        asm = "  beq x5, x6, loop\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0


# ---------------------------------------------------------------------------
# Label preservation
# ---------------------------------------------------------------------------

class TestLabelPreservation:
    """Labels before instructions are preserved after optimization."""

    def test_label_before_fusion(self):
        """Standalone label before a fusable pair is preserved."""
        asm = "main:\n  addi x1, x1, 3\n  addi x1, x1, 5\n  ret\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "main:" in output

    def test_label_before_beq(self):
        """Label before beq→j conversion preserved."""
        asm = "start:\n  beq x0, x0, end\nend:\n  ret\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "start:" in output
        assert "end:" in output
        assert "j end" in output


# ---------------------------------------------------------------------------
# Multi-rule interaction
# ---------------------------------------------------------------------------

class TestMultiRule:
    """Multiple rules firing in a single pass."""

    def test_multiple_rules_fire(self):
        """All three rules should fire in sequence."""
        asm = (
            "  addi x1, x1, 3\n"
            "  addi x1, x1, 5\n"
            "  li x2, 10\n"
            "  addi x2, x2, 7\n"
            "  beq x0, x0, done\n"
        )
        lines = parse_asm(asm)
        result, changes, rule_matches = peephole_pass(lines, RULES)
        assert changes >= 3
        assert rule_matches["addi+addi fusion"] >= 1
        assert rule_matches["li+addi fusion"] >= 1
        assert rule_matches["beq zero-zero to j"] >= 1

    def test_no_changes_on_optimal(self):
        """Already optimal code → zero changes."""
        asm = "  addi x1, x2, 3\n  nop\n  ret\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0


# ---------------------------------------------------------------------------
# Rule 4: mv swap elimination
# ---------------------------------------------------------------------------

class TestMvSwap:
    """mv x,y; mv y,x → both deleted."""

    def test_mv_swap(self):
        """mv x,y; mv y,x → both deleted."""
        asm = "  mv t0, t1\n  mv t1, t0\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        assert "mv" not in lines_to_asm(result)

    def test_no_swap_diff_regs(self):
        """mv x,y; mv x,z (different registers) → no match."""
        asm = "  mv t0, t1\n  mv t0, t2\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0


# ---------------------------------------------------------------------------
# Rule 5: mv chain shortening
# ---------------------------------------------------------------------------

class TestMvChain:
    """mv a,b; mv c,a → mv c,b."""

    def test_mv_chain(self):
        """mv a,b; mv c,a → mv c,b."""
        asm = "  mv t0, t1\n  mv t2, t0\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        output = lines_to_asm(result)
        assert "mv t2, t1" in output

    def test_no_chain_independent(self):
        """mv a,b; mv c,d (no data dep) → no match."""
        asm = "  mv t0, t1\n  mv t3, t4\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0


# ---------------------------------------------------------------------------
# Rule 6: addi zero elimination
# ---------------------------------------------------------------------------

class TestAddiZero:
    """addi rd, rs, 0 → delete."""

    def test_addi_zero(self):
        """addi rd, rs, 0 → delete."""
        asm = "  addi x1, x1, 0\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes >= 1
        assert "addi" not in lines_to_asm(result)

    def test_addi_nonzero_not_deleted(self):
        """addi rd, rs, non-zero → kept."""
        asm = "  addi x1, x1, 5\n"
        lines = parse_asm(asm)
        result, changes, _ = peephole_pass(lines, RULES)
        assert changes == 0
