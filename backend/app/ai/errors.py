"""Stable failures raised when model output violates backend rules."""


class AIInvalidOutputError(ValueError):
    """The model returned structurally valid but untrusted output."""

    code = "AI_INVALID_OUTPUT"
