"""OpenAI provider — default model gpt-5 (1M context)."""
from __future__ import annotations

import os

from openai import OpenAI

from mneva.providers.base import MissingAPIKeyError, ProviderError

_DEFAULT_MODEL = "gpt-5"


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise MissingAPIKeyError("openai", "OPENAI_API_KEY")
        self._client = OpenAI(api_key=key)
        self._model = os.environ.get("MNEVA_OPENAI_MODEL", _DEFAULT_MODEL)

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
                f"openai: model {self._model!r} returned no content "
                f"(finish_reason={choice.finish_reason!r}, max_tokens={max_tokens}). "
                f"Try increasing --max-tokens or switching backend."
            )
        return content
