from __future__ import annotations

import json
import os
import secrets
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


class ConfigError(Exception):
    """Recoverable config-file problem (missing, malformed, schema-drift)."""


@dataclass(frozen=True, slots=True)
class Config:
    token: str
    port: int = 7432
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    synthesize_default_backend: str = "anthropic"
    vault_path: str | None = None  # absolute path to an Obsidian vault


def generate_token() -> str:
    return secrets.token_hex(16)


def _config_path(home: Path) -> Path:
    return home / "config.json"


def save_config(config: Config, home: Path) -> None:
    path = _config_path(home)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    if not sys.platform.startswith("win"):
        os.chmod(path, 0o600)


def load_config(home: Path) -> Config:
    path = _config_path(home)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise ConfigError(
            f"mneva config not found at {path}; run `mneva init` first."
        ) from e
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"mneva config at {path} is not valid JSON: {e.msg} (line {e.lineno}, "
            f"column {e.colno}). Fix the file or delete it and re-run `mneva init`."
        ) from e
    if not isinstance(data, dict):
        raise ConfigError(
            f"mneva config at {path} must be a JSON object; got {type(data).__name__}."
        )
    try:
        return Config(**data)
    except TypeError as e:
        raise ConfigError(
            f"mneva config at {path} has unexpected or missing fields: {e}. "
            f"Run `mneva init` to regenerate."
        ) from e
