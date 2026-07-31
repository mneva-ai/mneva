from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from mneva.providers.base import MissingAPIKeyError


def _stub_client(captured: dict[str, object], *, text: str | None) -> type:
    """Build a stub google.genai.Client that records what it was called with."""

    class StubModels:
        def generate_content(
            self, *, model: str, contents: str, config: Any
        ) -> SimpleNamespace:
            captured["model_name"] = model
            captured["prompt"] = contents
            captured["max_output_tokens"] = config.max_output_tokens
            return SimpleNamespace(text=text)

    class StubClient:
        def __init__(self, **kw: object) -> None:
            captured["client_kwargs"] = kw
            self.models = StubModels()

    return StubClient


def test_google_provider_complete_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-google")
    monkeypatch.delenv("MNEVA_GOOGLE_MODEL", raising=False)
    monkeypatch.setattr(
        "mneva.providers.google.genai.Client",
        _stub_client(captured, text="hi from google"),
    )

    from mneva.providers.google import GoogleProvider

    provider = GoogleProvider()
    out = provider.complete("hi", max_tokens=128)

    assert out == "hi from google"
    assert provider.name == "google"
    assert captured["model_name"] == "gemini-2.0-pro"
    assert captured["prompt"] == "hi"
    assert captured["max_output_tokens"] == 128
    assert captured["client_kwargs"] == {"api_key": "test-key-google"}


def test_google_provider_respects_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("MNEVA_GOOGLE_MODEL", "gemini-1.5-pro")
    monkeypatch.setattr(
        "mneva.providers.google.genai.Client", _stub_client(captured, text="ok")
    )

    from mneva.providers.google import GoogleProvider

    GoogleProvider().complete("hi", max_tokens=64)
    assert captured["model_name"] == "gemini-1.5-pro"


def test_google_provider_empty_response_returns_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """google-genai can return response.text is None; callers expect str."""
    captured: dict[str, object] = {}

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("MNEVA_GOOGLE_MODEL", raising=False)
    monkeypatch.setattr(
        "mneva.providers.google.genai.Client", _stub_client(captured, text=None)
    )

    from mneva.providers.google import GoogleProvider

    assert GoogleProvider().complete("hi", max_tokens=64) == ""


def test_google_provider_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from mneva.providers.google import GoogleProvider

    with pytest.raises(MissingAPIKeyError) as exc:
        GoogleProvider()
    assert exc.value.env_var == "GOOGLE_API_KEY"
