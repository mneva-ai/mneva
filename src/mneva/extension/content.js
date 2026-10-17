// Puts the mneva profile into the empty composer of a new conversation.
// Selectors verified on 2026-10-16 (Grok on 2026-10-17); Doubao is unverified and falls back to
// the largest visible text field.
(() => {
  const SITES = {
    "chatgpt.com": {
      composer: 'form .ProseMirror[contenteditable="true"]',
      // "/" and a GPT's or project's start page; "/c/<id>" is an existing chat.
      isNewChat: (url) => url.pathname === "/" || /^\/g\/[^/]+(\/project)?\/?$/.test(url.pathname),
    },
    "claude.ai": {
      composer: '[data-testid="chat-input"]',
      isNewChat: (url) => url.pathname === "/new",
    },
    "gemini.google.com": {
      composer: 'rich-textarea .ql-editor[contenteditable="true"]',
      isNewChat: (url) => /^\/app\/?$/.test(url.pathname),
    },
    "grok.com": {
      // A plain textarea first, swapped for a ProseMirror editor once the
      // app loads; the recheck after inserting covers the swap.
      composer: 'form .ProseMirror[contenteditable="true"], form textarea',
      isNewChat: (url) => url.pathname === "/",
    },
    "www.doubao.com": {
      composer: null,
      isNewChat: (url) => /^\/chat\/?$/.test(url.pathname),
    },
  };
  const WAIT_FOR_COMPOSER_MS = 10000;
  const POLL_MS = 500;
  const RECHECK_MS = 1500;

  const site = SITES[location.hostname];
  if (!site) return;

  function visible(el) {
    const box = el.getBoundingClientRect();
    return box.width > 0 && box.height > 0;
  }

  function largestTextField() {
    const fields = [...document.querySelectorAll('textarea, [contenteditable="true"]')].filter(visible);
    fields.sort((a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight);
    return fields[0] || null;
  }

  function findComposer() {
    if (!site.composer) return largestTextField();
    // ChatGPT keeps a hidden zero-size copy of the composer in the page after
    // "New chat", ahead of the visible one, so take the first visible match.
    return [...document.querySelectorAll(site.composer)].find(visible) || null;
  }

  function isEmpty(el) {
    const text = el.tagName === "TEXTAREA" ? el.value : el.innerText;
    return text.trim() === "";
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function waitForComposer() {
    const deadline = Date.now() + WAIT_FOR_COMPOSER_MS;
    while (Date.now() < deadline) {
      const el = findComposer();
      if (el) return el;
      await sleep(POLL_MS);
    }
    return null;
  }

  function insert(composer, text) {
    composer.focus();
    document.execCommand("insertText", false, `${text}\n\n`);
  }

  async function siteDisabled() {
    const { disabled = {} } = await chrome.storage.sync.get("disabled");
    return Boolean(disabled[location.hostname]);
  }

  let handledHref = null;

  async function maybeInsert() {
    const href = location.href;
    if (handledHref === href || !site.isNewChat(new URL(href))) return;
    handledHref = href; // claim it first: two polls must not both insert
    if (await siteDisabled()) return;
    const composer = await waitForComposer();
    if (!composer || !isEmpty(composer)) return;
    const reply = await chrome.runtime.sendMessage({ type: "get_brief" });
    // The user may have started typing or left while we waited.
    if (!reply || !reply.ok || location.href !== href || !isEmpty(composer)) return;
    insert(composer, reply.text);
    // An app can swap the composer element right after navigating; check
    // once that the text is in the composer the user actually sees.
    await sleep(RECHECK_MS);
    const current = findComposer();
    if (current && current !== composer && location.href === href && isEmpty(current)) {
      insert(current, reply.text);
    }
  }

  // These sites are single-page apps: "New chat" changes the URL without a
  // page load, so watch the URL instead of relying on the initial run.
  let lastHref = null;
  setInterval(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      handledHref = null;
      maybeInsert();
    }
  }, POLL_MS);
})();
