"""Google provider — default model gemini-2.0-pro (1M context)."""
from __future__ import annotations

import os

import google.generativeai as genai

from mneva.providers.base import MissingAPIKeyError

_DEFAULT_MODEL = "gemini-2.0-pro"


class GoogleProvider:
    name = "google"

    def __init__(self) -> None:
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise MissingAPIKeyError("google", "GOOGLE_API_KEY")
        # google-generativeai exports these at runtime but does not declare
        # them in __all__; suppress mypy attr-defined for the public API.
        genai.configure(api_key=key)  # type: ignore[attr-defined]
        model_name = os.environ.get("MNEVA_GOOGLE_MODEL", _DEFAULT_MODEL)
        self._model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        resp = self._model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return resp.text  # type: ignore[no-any-return]  # resp.text is Any
