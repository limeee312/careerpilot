"""Stable failures at the AI provider and validation trust boundaries."""


class AIInputError(ValueError):
    """The requested AI operation has no valid, processable input."""

    code = "AI_INVALID_INPUT"
    retryable = False


class AIConfigurationError(RuntimeError):
    """Required server-side provider configuration is missing."""

    code = "AI_PROVIDER_ERROR"
    retryable = False


class AITimeoutError(TimeoutError):
    """The provider did not finish within the configured request timeout."""

    code = "AI_TIMEOUT"
    retryable = True


class AIProviderError(RuntimeError):
    """The provider failed before producing trusted structured output."""

    code = "AI_PROVIDER_ERROR"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class AIInvalidOutputError(ValueError):
    """The model returned invalid or deterministically untrusted output."""

    code = "AI_INVALID_OUTPUT"
    retryable = True
