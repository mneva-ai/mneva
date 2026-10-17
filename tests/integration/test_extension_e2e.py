"""The real extension, the real native host, a real browser.

Opt-in (MNEVA_E2E_EXTENSION=1) because it needs Playwright's Chromium and a
host registered for Chromium on this machine by `mneva setup`. Page content
is served by Playwright under the real hostnames, so the content script's
match patterns, the service worker and native messaging all run for real
while no account or network is involved. The browser passes MNEVA_HOME on
to the host it starts, so the brief comes from a throwaway profile.
"""
from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mneva import native_host
from mneva.store import Record, write_record

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("MNEVA_E2E_EXTENSION") != "1", reason="set MNEVA_E2E_EXTENSION=1"
    ),
]

COMPOSER_PAGE = """<!doctype html><html><body>
<form><div class="ProseMirror" contenteditable="true" style="width:600px;height:80px">{text}</div></form>
</body></html>"""
WAIT_MS = 6000


@pytest.fixture
def browser(tmp_path: Path, tmp_mneva_home: Path) -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    write_record(
        Record(id="e2e1", scope="profile", lifespan="permanent", tool="cli", body="E2E-PROFILE-我"),
        home=tmp_mneva_home,
    )
    ext = str(native_host.EXTENSION_DIR)
    with sync_api.sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(tmp_path / "chrome-profile"),
            channel="chromium",
            headless=True,
            args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"],
            env={**os.environ, "MNEVA_HOME": str(tmp_mneva_home)},
        )
        yield context
        context.close()


HIDDEN_FIRST_PAGE = """<!doctype html><html><body>
<form><div class="ProseMirror" contenteditable="true" style="display:none"></div></form>
<form><div class="ProseMirror" id="visible" contenteditable="true" style="width:600px;height:80px"></div></form>
</body></html>"""


def _composer_text(
    context: Any, url: str, prefilled: str = "", page_html: str = "", selector: str = ".ProseMirror"
) -> str:
    page = context.new_page()
    body = page_html or COMPOSER_PAGE.format(text=prefilled)
    page.route(
        "https://chatgpt.com/**",
        lambda route: route.fulfill(content_type="text/html", body=body),
    )
    page.goto(url)
    # Absence is the expected outcome in two of the tests, so a timeout is fine.
    with contextlib.suppress(Exception):
        page.wait_for_function(
            f"() => document.querySelector('{selector}').innerText.includes('E2E-PROFILE')",
            timeout=WAIT_MS,
        )
    text: str = page.inner_text(selector)
    page.close()
    return text


def test_hidden_composer_ahead_of_the_visible_one_is_skipped(browser: Any) -> None:
    # Found in real ChatGPT on 2026-10-16: after "New chat" a zero-size copy
    # of the composer precedes the visible one, and the profile never arrived.
    text = _composer_text(
        browser, "https://chatgpt.com/", page_html=HIDDEN_FIRST_PAGE, selector="#visible"
    )

    assert text.count("E2E-PROFILE-我") == 1


def test_new_chat_gets_the_profile_through_native_messaging(browser: Any) -> None:
    text = _composer_text(browser, "https://chatgpt.com/")

    assert text.count("E2E-PROFILE-我") == 1


def test_existing_chat_is_left_alone(browser: Any) -> None:
    assert "E2E-PROFILE" not in _composer_text(browser, "https://chatgpt.com/c/some-chat")


def test_composer_with_text_is_left_alone(browser: Any) -> None:
    text = _composer_text(browser, "https://chatgpt.com/", prefilled="my own question")

    assert text == "my own question"
