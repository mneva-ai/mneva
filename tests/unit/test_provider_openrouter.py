from __future__ import annotations

from types import SimpleNamespace

import pytest

from mneva.providers.base import MissingAPIKeyError


def test_openrouter_provider_uses_base_url_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class StubCompletions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content="hi via openrouter"))
                ]
            )

    class StubChat:
        def __init__(self) -> None:
            self.completions = StubCompletions()

    class StubOpenAI:
        def __init__(self, **kw: object) -> None:
            captured["client_kwargs"] = kw
            self.chat = StubChat()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-openrouter")
    monkeypatch.delenv("MNEVA_OPENROUTER_MODEL", raising=False)
    monkeypatch.setattr("mneva.providers.openrouter.OpenAI", StubOpenAI)

    from mneva.providers.openrouter import OpenRouterProvider

    provider = OpenRouterProvider()
    out = provider.complete("hi", max_tokens=128)

    assert out == "hi via openrouter"
    assert provider.name == "openrouter"
    assert captured["client_kwargs"] == {
        "api_key": "test-key-openrouter",
        "base_url": "https://openrouter.ai/api/v1",
    }
    assert captured["model"] == "anthropic/claude-opus-4-7"
    assert captured["max_tokens"] == 128
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


def test_openrouter_provider_respects_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class StubCompletions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )

    class StubOpenAI:
        def __init__(self, **kw: object) -> None:
            self.chat = SimpleNamespace(completions=StubCompletions())

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MNEVA_OPENROUTER_MODEL", "google/gemini-2.0-pro")
    monkeypatch.setattr("mneva.providers.openrouter.OpenAI", StubOpenAI)

    from mneva.providers.openrouter import OpenRouterProvider

    OpenRouterProvider().complete("hi", max_tokens=64)
    assert captured["model"] == "google/gemini-2.0-pro"


def test_openrouter_provider_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from mneva.providers.openrouter import OpenRouterProvider

    with pytest.raises(MissingAPIKeyError) as exc:
        OpenRouterProvider()
    assert exc.value.env_var == "OPENROUTER_API_KEY"
