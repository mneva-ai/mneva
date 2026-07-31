"""Google provider — default model gemini-2.0-pro (1M context)."""
from __future__ import annotations

import os

from google import genai
from google.genai import types

from mneva.providers.base import MissingAPIKeyError

_DEFAULT_MODEL = "gemini-2.0-pro"


class GoogleProvider:
    name = "google"

    def __init__(self) -> None:
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise MissingAPIKeyError("google", "GOOGLE_API_KEY")
        self._client = genai.Client(api_key=key)
        self._model_name = os.environ.get("MNEVA_GOOGLE_MODEL", _DEFAULT_MODEL)

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        resp = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=max_tokens),
        )
        # google-genai types response.text as str | None; the other providers
        # all return str, so normalize a None response to the empty string.
        return resp.text or ""
