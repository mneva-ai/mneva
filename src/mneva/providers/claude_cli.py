"""Provider over the Claude Code CLI (`claude -p`): no API key for mneva to hold.

Claude Code prefers ANTHROPIC_API_KEY over the user's claude.ai login when
both exist, so the key is removed from the child environment first and only
used when no login works. The call runs with tools, MCP servers, settings
(hooks, plugins) and session persistence off, from an empty directory, so it
is a plain completion. Persistence must stay off: otherwise every learn run
would write a Claude Code session whose prompts the next run reads back.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from mneva.providers.base import ProviderError

_SYSTEM_PROMPT = "You extract and organize facts. Answer with the requested JSON only."
_TIMEOUT_SECONDS = 900
_KEY_VAR = "ANTHROPIC_API_KEY"


class ClaudeCliProvider:
    name = "claude-code"

    def __init__(self, *, model: str) -> None:
        executable = shutil.which("claude")
        if executable is None:
            raise ProviderError(
                "Claude Code (`claude`) is not on PATH; install it, or pass --backend "
                "with an API key provider (anthropic, openai, google, openrouter)."
            )
        self._argv = [
            executable,
            "-p",
            "--model", model,
            "--output-format", "json",
            "--tools", "",
            "--strict-mcp-config",
            "--setting-sources", "",
            "--no-session-persistence",
            "--system-prompt", _SYSTEM_PROMPT,
        ]
        self._use_key = False
        self._last_failure = "no output"
        # Sum of Claude Code's own per-call estimate, so the user sees the bill.
        self.cost_usd = 0.0

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        # The CLI has no max-tokens flag; replies here are small JSON.
        del max_tokens
        if not self._use_key:
            env = {k: v for k, v in os.environ.items() if k != _KEY_VAR}
            reply = self._run(prompt, env)
            if reply is not None or _KEY_VAR not in os.environ:
                return self._result(reply)
            self._use_key = True
        return self._result(self._run(prompt, dict(os.environ)))

    def _run(self, prompt: str, env: dict[str, str]) -> dict[str, object] | None:
        with tempfile.TemporaryDirectory(prefix="mneva-learn-") as cwd:
            try:
                done = subprocess.run(  # noqa: S603
                    self._argv,
                    input=prompt,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    cwd=cwd,
                    timeout=_TIMEOUT_SECONDS,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ProviderError(f"claude -p failed: {exc}") from exc
        start = done.stdout.find("{")
        if done.returncode != 0 or start < 0:
            self._last_failure = (done.stdout + done.stderr).strip()[:300]
            return None
        try:
            reply = json.loads(done.stdout[start:])
        except ValueError:
            self._last_failure = done.stdout[:300]
            return None
        return reply if isinstance(reply, dict) else None

    def _result(self, reply: dict[str, object] | None) -> str:
        if reply is None:
            raise ProviderError(f"claude -p failed: {self._last_failure}")
        cost = reply.get("total_cost_usd")
        if isinstance(cost, int | float):
            self.cost_usd += float(cost)
        text = reply.get("result")
        if reply.get("is_error") or not isinstance(text, str):
            raise ProviderError(f"claude -p returned an error: {text}")
        return text
