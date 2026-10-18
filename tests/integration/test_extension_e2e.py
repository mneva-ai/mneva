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
import json
import os
import shutil
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
def extension_dir(request: pytest.FixtureRequest, tmp_path: Path, tmp_mneva_home: Path) -> Path:
    if getattr(request, "param", None) != "outdated":
        return native_host.EXTENSION_DIR
    # The browser runs one copy while `mneva setup` has put a newer one where
    # the host reports from.
    loaded = tmp_path / "loaded-extension"
    shutil.copytree(native_host.EXTENSION_DIR, loaded)
    newer = tmp_mneva_home / "extension"
    shutil.copytree(native_host.EXTENSION_DIR, newer)
    manifest = json.loads((newer / "manifest.json").read_text(encoding="utf-8"))
    (newer / "manifest.json").write_text(
        json.dumps({**manifest, "version": "99.0.0"}), encoding="utf-8"
    )
    return loaded


@pytest.fixture
def browser(tmp_path: Path, tmp_mneva_home: Path, extension_dir: Path) -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    write_record(
        Record(id="e2e1", scope="profile", lifespan="permanent", tool="cli", body="E2E-PROFILE-我"),
        home=tmp_mneva_home,
    )
    ext = str(extension_dir)
    with sync_api.sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(tmp_path / "chrome-profile"),
            channel="chromium",
            headless=True,
            args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"],
            env={**os.environ, "MNEVA_HOME": str(tmp_mneva_home)},
        )
        # As for a real "Load unpacked" user. Without it Chromium disables a
        # command-line extension the moment it reloads itself.
        settings = context.new_page()
        settings.goto("chrome://extensions")
        settings.evaluate(
            "() => new Promise(done => chrome.developerPrivate"
            ".updateProfileConfiguration({inDeveloperMode: true}, done))"
        )
        settings.close()
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


def _service_worker(context: Any) -> Any:
    if context.service_workers:
        return context.service_workers[0]
    return context.wait_for_event("serviceworker", timeout=WAIT_MS)


@pytest.mark.parametrize("extension_dir", ["outdated"], indirect=True)
def test_outdated_extension_reloads_once_and_open_tabs_keep_working(browser: Any) -> None:
    page = browser.new_page()
    page.route(
        "https://chatgpt.com/**",
        lambda route: route.fulfill(content_type="text/html", body=COMPOSER_PAGE.format(text="")),
    )
    page.goto("https://chatgpt.com/")
    page.wait_for_function(
        "() => document.querySelector('.ProseMirror').innerText.includes('E2E-PROFILE')",
        timeout=WAIT_MS,
    )
    old_worker = _service_worker(browser)
    # The brief arrived, so the reply carried 99.0.0 and a reload follows.
    for _ in range(WAIT_MS // 250):
        if browser.service_workers and browser.service_workers[0] is not old_worker:
            break
        page.wait_for_timeout(250)
    worker = _service_worker(browser)
    assert worker is not old_worker, "the extension did not reload"
    assert worker.evaluate("chrome.storage.local.get('reloadedFor')") == {"reloadedFor": "99.0.0"}

    # Same tab, "New chat" without a page load: the reloaded extension must
    # still put the profile in.
    page.evaluate(
        """() => {
            history.pushState({}, "", "/c/old-chat");
            setTimeout(() => {
                document.querySelector('.ProseMirror').innerText = "";
                history.pushState({}, "", "/");
            }, 1200);
        }"""
    )
    page.wait_for_function(
        "() => location.pathname === '/'"
        " && document.querySelector('.ProseMirror').innerText.includes('E2E-PROFILE')",
        timeout=WAIT_MS,
    )
    # The loaded copy still is not 99.0.0, and it must not reload again.
    page.wait_for_timeout(3000)
    assert browser.service_workers == [worker]
