from __future__ import annotations

import json
import os
import secrets
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Config:
    token: str
    port: int = 7432
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    synthesize_default_backend: str = "anthropic"


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
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config(**data)
