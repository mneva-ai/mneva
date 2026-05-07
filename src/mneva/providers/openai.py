"""OpenAI provider — default model gpt-5 (1M context)."""
from __future__ import annotations

import os

from openai import OpenAI

from mneva.providers.base import MissingAPIKeyError

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
        # SDK content is str | None (None on refusal/length cap); we treat None as a
        # bug/upstream failure rather than a normal return — type: ignore for v0.
        return resp.choices[0].message.content  # type: ignore[return-value]
