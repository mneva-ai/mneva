from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

from mneva.store import Record, write_record


def _frame(message: Any) -> bytes:
    body = json.dumps(message).encode("utf-8")
    return struct.pack("<I", len(body)) + body


def _talk(home: Path, payload: bytes) -> tuple[list[dict[str, Any]], int]:
    # A real process and a real pipe: only this catches stdio opened in text
    # mode, where Windows turns \n into \r\n and corrupts the length prefix.
    env = {**os.environ, "MNEVA_HOME": str(home)}
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "mneva.native_host"],
        input=payload,
        capture_output=True,
        env=env,
        timeout=60,
        check=False,
    )
    out, replies = proc.stdout, []
    while out:
        (length,) = struct.unpack("<I", out[:4])
        replies.append(json.loads(out[4 : 4 + length].decode("utf-8")))
        out = out[4 + length :]
    return replies, proc.returncode


def _profile(home: Path, rid: str, body: str) -> None:
    write_record(
        Record(id=rid, scope="profile", lifespan="permanent", tool="cli", body=body), home=home
    )


def test_ping_and_get_brief_over_a_real_pipe(tmp_mneva_home: Path) -> None:
    _profile(tmp_mneva_home, "n1", "我说中文。\nSecond line.")

    replies, code = _talk(
        tmp_mneva_home, _frame({"type": "ping"}) + _frame({"type": "get_brief", "max_chars": 4000})
    )

    assert code == 0
    assert replies[0]["ok"] is True and replies[0]["version"]
    assert replies[1]["ok"] is True
    assert "我说中文。\nSecond line." in replies[1]["text"]
    assert replies[1]["records"] == 1


def test_get_brief_without_a_profile_says_how_to_add_one(tmp_mneva_home: Path) -> None:
    replies, _ = _talk(tmp_mneva_home, _frame({"type": "get_brief"}))

    assert replies == [
        {"ok": False, "error": "no_profile", "message": replies[0]["message"]}
    ]
    assert "--scope profile" in replies[0]["message"]


def test_unknown_type_and_non_json_are_rejected_and_the_host_keeps_going(
    tmp_mneva_home: Path,
) -> None:
    garbage = b"not json"
    payload = (
        _frame({"type": "run_shell", "cmd": "dir"})
        + struct.pack("<I", len(garbage)) + garbage
        + _frame({"type": "ping"})
    )

    replies, code = _talk(tmp_mneva_home, payload)

    assert code == 0
    assert [r.get("error") for r in replies[:2]] == ["bad_request", "bad_request"]
    assert replies[2]["ok"] is True


def test_oversized_length_is_rejected_and_the_host_exits(tmp_mneva_home: Path) -> None:
    # After a bogus length the stream cannot be resynchronized; answering
    # once and exiting is the only safe move.
    replies, code = _talk(tmp_mneva_home, struct.pack("<I", 50 * 1024 * 1024) + b"x" * 10)

    assert replies == [{"ok": False, "error": "bad_request", "message": replies[0]["message"]}]
    assert code == 0


def test_max_chars_is_clamped(tmp_mneva_home: Path) -> None:
    _profile(tmp_mneva_home, "n2", "short")

    replies, _ = _talk(tmp_mneva_home, _frame({"type": "get_brief", "max_chars": -5}))

    # Clamped to the minimum: nothing fits, which is reported, not a crash.
    assert replies[0]["ok"] is False
