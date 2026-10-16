from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from mneva.cli import app
from mneva.store import iter_records


def test_capture_stdin_utf8_chinese_through_a_real_pipe(tmp_mneva_home: Path) -> None:
    # CliRunner wraps stdin as UTF-8 itself, so only a real process pipe
    # reproduces the Windows bug: stdin decoded in the console code page
    # turned UTF-8 Chinese into lone surrogates and crashed make_record_id.
    body = "我希望 AI 说大白话中文。\n"
    env = {**os.environ, "MNEVA_HOME": str(tmp_mneva_home)}
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)

    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "from mneva.cli import app; app()",
         "capture", "--scope", "profile", "--lifespan", "permanent", "--no-git", "-"],
        input=body.encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    # The store strips trailing whitespace on read (python-frontmatter).
    assert [r.body for r in iter_records(home=tmp_mneva_home)] == [body.strip()]


def test_capture_stdin_utf8_bom_is_stripped(tmp_mneva_home: Path) -> None:
    result = CliRunner().invoke(
        app, ["capture", "--scope", "profile", "--no-git", "-"], input="﻿你好".encode()
    )

    assert result.exit_code == 0, result.output
    assert [r.body for r in iter_records(home=tmp_mneva_home)] == ["你好"]


def test_capture_stdin_not_utf8_fails_with_a_clear_message(tmp_mneva_home: Path) -> None:
    result = CliRunner().invoke(
        app, ["capture", "--scope", "profile", "--no-git", "-"], input="你好".encode("gbk")
    )

    assert result.exit_code != 0
    assert "UTF-8" in result.output
    assert list(iter_records(home=tmp_mneva_home)) == []
