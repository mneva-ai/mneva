"""Provider abstraction for Mneva's intelligence layer."""
from __future__ import annotations

from mneva.providers.base import MissingAPIKeyError, Provider, ProviderError

__all__ = [
    "MissingAPIKeyError",
    "Provider",
    "ProviderError",
    "get_provider",
]


def get_provider(name: str) -> Provider:
    """Construct a provider by short name. Raises on unknown name or missing key."""
    if name == "anthropic":
        from mneva.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from mneva.providers.openai import OpenAIProvider

        return OpenAIProvider()
    if name == "google":
        from mneva.providers.google import GoogleProvider

        return GoogleProvider()
    if name == "openrouter":
        from mneva.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider()
    raise ValueError(f"unknown backend {name!r} (expected: anthropic, openai, google, openrouter)")
