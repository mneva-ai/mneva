"""Provider Protocol + error types.

Adapters in this subpackage call out to LLM SDKs. Keys are read from
environment variables only — never from config files.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class ProviderError(Exception):
    """Base class for all provider-side failures."""


class MissingAPIKeyError(ProviderError):
    """Raised when the env var holding the provider's API key is unset."""

    def __init__(self, provider: str, env_var: str) -> None:
        super().__init__(
            f"missing API key for {provider}: set {env_var} in your environment"
        )
        self.provider = provider
        self.env_var = env_var


@runtime_checkable
class Provider(Protocol):
    """One-shot non-streaming LLM completion surface.

    Implementations hard-code their default model. Callers supply only
    the prompt and a max_tokens budget. Streaming, token-usage reporting,
    and retry policy are intentionally deferred to v0.1.
    """

    name: str

    def complete(self, prompt: str, *, max_tokens: int) -> str: ...
