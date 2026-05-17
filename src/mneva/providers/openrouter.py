"""OpenRouter provider — wraps the OpenAI client with a base_url override.

Default routes to anthropic/claude-opus-4-7. Override with MNEVA_OPENROUTER_MODEL.
"""
from __future__ import annotations

import os

from openai import OpenAI

from mneva.providers.base import MissingAPIKeyError, ProviderError

_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "anthropic/claude-opus-4-7"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self) -> None:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise MissingAPIKeyError("openrouter", "OPENROUTER_API_KEY")
        self._client = OpenAI(api_key=key, base_url=_BASE_URL)
        self._model = os.environ.get("MNEVA_OPENROUTER_MODEL", _DEFAULT_MODEL)

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = resp.choices[0]
        content = choice.message.content
        if content is None:
            raise ProviderError(
                f"openrouter: model {self._model!r} returned no content "
                f"(finish_reason={choice.finish_reason!r}, max_tokens={max_tokens}). "
                f"Some free-tier models refuse silently; try a paid model or switch backend."
            )
        return content
