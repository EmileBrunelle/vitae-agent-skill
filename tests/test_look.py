#!/usr/bin/env python3
"""Offline parser tests for scripts/look.py (run by hand: python3 tests/test_look.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import look

IDS = ["L1", "L2", "L3"]
def run(content: str) -> tuple[list[str], int]:
    return look.render(IDS, look.parse_verdicts(content, IDS), "m")

def check(name: str, content: str, want_bad: int, want_lines: list[str]) -> None:
    lines, bad = run(content)
    assert bad == want_bad, (name, lines)
    for w in want_lines:
        assert w in lines, (name, w, lines)
    assert lines[-1] == "Visual pass: local m"

check("clean", "PASS L1 — header\nPASS L2 — body\nPASS L3 — footer", 0, ["PASS L1 — header"])
check("think block", "<think>FAIL L1 — nope\nreasoning</think>\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c", 0, ["PASS L1 — a"])
check("unopened think", "reasoning...\n</think>\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c", 0, [])
check("missing item", "PASS L1 — a\nPASS L3 — c", 1, ["FAIL L2 — no answer from model (missing or unparsable)"])
check("chatter+markdown", "Sure! Here you go:\n**FAIL** L1 - band: text clipped\n- PASS L2 — body\n`PASS L3` — foot\nHope it helps", 1,
      ["FAIL L1 — band: text clipped", "PASS L2 — body", "PASS L3 — foot"])
check("unknown id ignored", "PASS L1 — a\nPASS L2 — b\nPASS L3 — c\nFAIL L9 — x", 0, [])
check("no zone", "PASS L1\nPASS L2\nFAIL L3", 1, ["FAIL L3 — (no zone given)"])
check("garbage", "I can't see any image.", 3, [])
assert look.checklist_ids("1. **L1** a\nL2: b\n- L3 c\nL1 again") == ["L1", "L2", "L3"]
print("test_look: all ok")
