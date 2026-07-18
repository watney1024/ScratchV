"""demo03_verify_for.py — Verify FOR/ENDFOR edge generation is correct.

Checks that:
  - FOR header block has exactly 2 exits: (1) BRANCH "body" to the loop body,
    (2) FALLTHROUGH to the block after the matching ENDFOR.
  - ENDFOR block has exactly 1 exit: JUMP back to the FOR header.
  - Nested FOR loops: each FOR matches its own ENDFOR, no cross-nesting confusion.

Usage:
    python toy_cfg/demo03_verify_for.py
    PYTHONPATH=. python toy_cfg/demo03_verify_for.py
"""

from __future__ import annotations

import sys

from toy_cfg.demo01_build_blocks import build_blocks, DEMOS
from toy_cfg.demo02_build_cfg import build_cfg, CFG

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

checks_passed = 0
checks_failed = 0


def check(name: str, condition: bool) -> None:
    global checks_passed, checks_failed
    if condition:
        checks_passed += 1
        print(f"  ✓ {name}")
    else:
        checks_failed += 1
        print(f"  ✗ {name}")


# ---------------------------------------------------------------------------
# Test 1: while_loop — basic FOR/ENDFOR
# ---------------------------------------------------------------------------

print("=" * 48)
print("Test 1: while_loop — basic FOR/ENDFOR")
print("=" * 48)

cfg = build_cfg(DEMOS["while_loop"].functions[0])
entry = cfg.blocks["entry"]
body = cfg.blocks["body"]
end = cfg.blocks["end"]

check("FOR block has 2 exits", len(entry.exits_to) == 2)

# First exit: BRANCH "body" to loop body
check("FOR → body [body]", entry.exits_to[0] == ("body", "body"))

# Second exit: FALLTHROUGH to block after ENDFOR
check("FOR → end (FALLTHROUGH)", entry.exits_to[1][0] == "end")
check("FOR → end has no edge label", entry.exits_to[1][1] is None)

# ENDFOR block: exactly 1 exit — JUMP back to FOR header
check("ENDFOR has 1 exit", len(body.exits_to) == 1)
check("ENDFOR → entry (JUMP back)", body.exits_to[0][0] == "entry")
check("ENDFOR → entry has no edge label", body.exits_to[0][1] is None)

# End block: no exits (RETURN)
check("End block has 0 exits", len(end.exits_to) == 0)

print()

# ---------------------------------------------------------------------------
# Test 2: nested_for — nested FOR/ENDFOR, no cross-nesting confusion
# ---------------------------------------------------------------------------

print("=" * 48)
print("Test 2: nested_for — nested FOR/ENDFOR")
print("=" * 48)

cfg2 = build_cfg(DEMOS["nested_for"].functions[0])
inner_entry = cfg2.blocks["inner_entry"]
inner_body = cfg2.blocks["inner_body"]
outer_end = cfg2.blocks["outer_end"]
outer_body = cfg2.blocks["outer_body"]
entry2 = cfg2.blocks["entry"]

# -- Outer FOR (entry) --
check("Outer FOR has 2 exits", len(entry2.exits_to) == 2)
check("Outer FOR → outer_body [body]", entry2.exits_to[0] == ("outer_body", "body"))
check("Outer FOR → end (FALLTHROUGH)", entry2.exits_to[1][0] == "end")

# -- Inner FOR (inner_entry) --
check("Inner FOR has 2 exits", len(inner_entry.exits_to) == 2)
check("Inner FOR → inner_body [body]", inner_entry.exits_to[0] == ("inner_body", "body"))
check("Inner FOR → outer_end (FALLTHROUGH)", inner_entry.exits_to[1][0] == "outer_end")
check("Inner FOR → outer_end has no edge label", inner_entry.exits_to[1][1] is None)

# -- Inner ENDFOR (inner_body) —
check("Inner ENDFOR has 1 exit", len(inner_body.exits_to) == 1)
check("Inner ENDFOR → inner_entry (JUMP back)", inner_body.exits_to[0][0] == "inner_entry")
check("Inner ENDFOR → inner_entry has no edge label", inner_body.exits_to[0][1] is None)

# -- Outer ENDFOR (outer_end) —
check("Outer ENDFOR has 1 exit", len(outer_end.exits_to) == 1)
check("Outer ENDFOR → entry (JUMP back)", outer_end.exits_to[0][0] == "entry")
check("Outer ENDFOR → entry has no edge label", outer_end.exits_to[0][1] is None)

# -- Outer_body: no FOR/ENDFOR, just FALLTHROUGH to inner_entry --
check("Outer body has 1 exit (FALLTHROUGH to inner_entry)", len(outer_body.exits_to) == 1)
check("Outer body → inner_entry", outer_body.exits_to[0][0] == "inner_entry")
check("Outer body edge has no label", outer_body.exits_to[0][1] is None)

# Verify no dangling cross-nesting: inner FOR targets are NOT outer blocks
check("Inner FOR does NOT jump to outer_body (no cross-nesting)", inner_entry.exits_to[0][0] != "outer_body")
check("Inner ENDFOR does NOT jump to entry (no cross-nesting)", inner_body.exits_to[0][0] != "entry")

print()

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("=" * 48)
print(f"Passed: {checks_passed}, Failed: {checks_failed}")
print("=" * 48)

sys.exit(0 if checks_failed == 0 else 1)
