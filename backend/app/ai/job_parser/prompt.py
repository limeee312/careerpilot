"""Versioned Job Parser prompt loading."""

from pathlib import Path

PROMPT_PATH = Path(__file__).with_name("prompt_v1.md")
JOB_PARSER_PROMPT_V1 = PROMPT_PATH.read_text(encoding="utf-8").strip()
