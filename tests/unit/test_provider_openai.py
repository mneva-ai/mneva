from __future__ import annotations

from types import SimpleNamespace

import pytest

from mneva.providers.base import MissingAPIKeyError


def test_openai_provider_complete_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubCompletions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content="hi from openai"))
                ]
            )

    class StubChat:
        def __init__(self) -> None:
            self.completions = StubCompletions()

    class StubOpenAI:
        def __init__(self, **kw: object) -> None:
            captured["client_kwargs"] = kw
            self.chat = StubChat()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-openai")
    monkeypatch.delenv("MNEVA_OPENAI_MODEL", raising=False)
    monkeypatch.setattr("mneva.providers.openai.OpenAI", StubOpenAI)

    from mneva.providers.openai import OpenAIProvider

    provider = OpenAIProvider()
    out = provider.complete("hi", max_tokens=128)

    assert out == "hi from openai"
    assert provider.name == "openai"
    assert captured["model"] == "gpt-5"
    assert captured["max_tokens"] == 128
    assert captured["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["client_kwargs"] == {"api_key": "test-key-openai"}


def test_openai_provider_respects_model_env_override(
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

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MNEVA_OPENAI_MODEL", "gpt-4o")
    monkeypatch.setattr("mneva.providers.openai.OpenAI", StubOpenAI)

    from mneva.providers.openai import OpenAIProvider

    OpenAIProvider().complete("hi", max_tokens=64)
    assert captured["model"] == "gpt-4o"


def test_openai_provider_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from mneva.providers.openai import OpenAIProvider

    with pytest.raises(MissingAPIKeyError) as exc:
        OpenAIProvider()
    assert exc.value.env_var == "OPENAI_API_KEY"
