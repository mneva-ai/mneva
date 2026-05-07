from __future__ import annotations

from mneva.providers import Provider
from mneva.providers.base import MissingAPIKeyError, ProviderError


def test_provider_protocol_runtime_checkable() -> None:
    class Stub:
        name = "stub"

        def complete(self, prompt: str, *, max_tokens: int) -> str:
            return "ok"

    assert isinstance(Stub(), Provider)


def test_missing_api_key_error_is_provider_error() -> None:
    err = MissingAPIKeyError("anthropic", "ANTHROPIC_API_KEY")
    assert isinstance(err, ProviderError)
    assert "ANTHROPIC_API_KEY" in str(err)
    assert err.provider == "anthropic"
    assert err.env_var == "ANTHROPIC_API_KEY"
