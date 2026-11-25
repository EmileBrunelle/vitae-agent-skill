"""Adapter: Claude Code (`claude -p`).

Env: CFG   (required) isolated CLAUDE_CONFIG_DIR containing skills/vitae and credentials
     MODEL (default claude-sonnet-5-5)
Fixed: --effort low --max-turns 1 (a one-turn cap cannot see past first-turn file exploration).
"""

import json
import os
from pathlib import Path


def command(query: str, workdir: Path) -> list[str]:
    return [
        "claude", "-p", query, "--model", os.environ.get("MODEL", "claude-sonnet-5-5"),
        "--effort", "low", "--max-turns", "1", "--strict-mcp-config",
        "--output-format", "stream-json", "--verbose",
    ]  # fmt: skip


def env() -> dict[str, str | None]:
    """Overrides for the child environment (None unsets the variable)."""
    return {
        "CLAUDE_CONFIG_DIR": os.environ["CFG"],
        "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "CLAUDE_EFFORT": None,
        "CLAUDE_CODE_EFFORT_LEVEL": None,
    }


def triggered(transcript: str) -> bool:
    """A Skill tool_use naming vitae, or a Read of skills/vitae/SKILL.md."""
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            args = block.get("input") or {}
            if block.get("name") == "Skill" and "vitae" in str(args.get("skill", "")):
                return True
            path = str(args.get("file_path", "")).replace("\\", "/")
            if block.get("name") == "Read" and "skills/vitae/SKILL.md" in path:
                return True
    return False
