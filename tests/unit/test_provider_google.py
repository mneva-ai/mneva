from __future__ import annotations

from types import SimpleNamespace

import pytest

from mneva.providers.base import MissingAPIKeyError


def test_google_provider_complete_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def stub_configure(**kw: object) -> None:
        captured["configure_kwargs"] = kw

    class StubModel:
        def __init__(self, model_name: str) -> None:
            captured["model_name"] = model_name

        def generate_content(
            self, prompt: str, generation_config: dict[str, object]
        ) -> SimpleNamespace:
            captured["prompt"] = prompt
            captured["generation_config"] = generation_config
            return SimpleNamespace(text="hi from google")

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-google")
    monkeypatch.delenv("MNEVA_GOOGLE_MODEL", raising=False)
    monkeypatch.setattr("mneva.providers.google.genai.configure", stub_configure)
    monkeypatch.setattr(
        "mneva.providers.google.genai.GenerativeModel", StubModel
    )

    from mneva.providers.google import GoogleProvider

    provider = GoogleProvider()
    out = provider.complete("hi", max_tokens=128)

    assert out == "hi from google"
    assert provider.name == "google"
    assert captured["model_name"] == "gemini-2.0-pro"
    assert captured["prompt"] == "hi"
    assert captured["generation_config"] == {"max_output_tokens": 128}
    assert captured["configure_kwargs"] == {"api_key": "test-key-google"}


def test_google_provider_respects_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def stub_configure(**kw: object) -> None:
        pass

    class StubModel:
        def __init__(self, model_name: str) -> None:
            captured["model_name"] = model_name

        def generate_content(
            self, prompt: str, generation_config: dict[str, object]
        ) -> SimpleNamespace:
            return SimpleNamespace(text="ok")

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("MNEVA_GOOGLE_MODEL", "gemini-1.5-pro")
    monkeypatch.setattr("mneva.providers.google.genai.configure", stub_configure)
    monkeypatch.setattr("mneva.providers.google.genai.GenerativeModel", StubModel)

    from mneva.providers.google import GoogleProvider

    GoogleProvider().complete("hi", max_tokens=64)
    assert captured["model_name"] == "gemini-1.5-pro"


def test_google_provider_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from mneva.providers.google import GoogleProvider

    with pytest.raises(MissingAPIKeyError) as exc:
        GoogleProvider()
    assert exc.value.env_var == "GOOGLE_API_KEY"
