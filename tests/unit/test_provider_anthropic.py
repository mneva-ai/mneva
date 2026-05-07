from __future__ import annotations

from types import SimpleNamespace

import pytest

from mneva.providers.base import MissingAPIKeyError


def test_anthropic_provider_complete_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubMessages:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text="hello world")])

    class StubAnthropic:
        def __init__(self, **kw: object) -> None:
            captured["client_kwargs"] = kw
            self.messages = StubMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-anthropic")
    monkeypatch.delenv("MNEVA_ANTHROPIC_MODEL", raising=False)
    monkeypatch.setattr("mneva.providers.anthropic.Anthropic", StubAnthropic)

    from mneva.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    out = provider.complete("hi", max_tokens=128)

    assert out == "hello world"
    assert provider.name == "anthropic"
    assert captured["model"] == "claude-opus-4-7"
    assert captured["max_tokens"] == 128
    assert captured["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["client_kwargs"] == {"api_key": "test-key-anthropic"}


def test_anthropic_provider_respects_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class StubMessages:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text="ok")])

    class StubAnthropic:
        def __init__(self, **kw: object) -> None:
            self.messages = StubMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("MNEVA_ANTHROPIC_MODEL", "claude-haiku-4-5")
    monkeypatch.setattr("mneva.providers.anthropic.Anthropic", StubAnthropic)

    from mneva.providers.anthropic import AnthropicProvider

    AnthropicProvider().complete("hi", max_tokens=64)
    assert captured["model"] == "claude-haiku-4-5"


def test_anthropic_provider_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from mneva.providers.anthropic import AnthropicProvider

    with pytest.raises(MissingAPIKeyError) as exc:
        AnthropicProvider()
    assert exc.value.env_var == "ANTHROPIC_API_KEY"
