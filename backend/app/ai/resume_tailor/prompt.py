"""Versioned Resume Tailor prompt loading."""

from pathlib import Path

PROMPT_PATH = Path(__file__).with_name("prompt_v1.md")
RESUME_TAILOR_PROMPT_V1 = PROMPT_PATH.read_text(encoding="utf-8").strip()
