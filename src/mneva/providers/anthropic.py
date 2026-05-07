"""Anthropic provider — default model claude-opus-4-7 (1M context)."""
from __future__ import annotations

import os

from anthropic import Anthropic

from mneva.providers.base import MissingAPIKeyError

_DEFAULT_MODEL = "claude-opus-4-7"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise MissingAPIKeyError("anthropic", "ANTHROPIC_API_KEY")
        self._client = Anthropic(api_key=key)
        self._model = os.environ.get("MNEVA_ANTHROPIC_MODEL", _DEFAULT_MODEL)

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # SDK content is list[TextBlock | ToolUseBlock]; we never request tools,
        # so the first block is always a TextBlock with a .text attribute.
        return msg.content[0].text  # type: ignore[union-attr]
