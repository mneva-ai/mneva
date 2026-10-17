// Talks to the mneva native host that `mneva setup` registers. The host only
// renders the profile brief; nothing here touches the network.
const HOST = "org.mneva.brief";
const BRIEF_CHARS = 4000;
// Lets the reply that carried the new version reach the page first.
const RELOAD_DELAY_MS = 1000;

async function askHost(message) {
  try {
    return await chrome.runtime.sendNativeMessage(HOST, message);
  } catch (error) {
    // Host not registered, or Python missing: tell the user what to run.
    return {
      ok: false,
      error: "no_host",
      message: "mneva is not reachable. Run `mneva setup` in a terminal, then reload this page.",
      detail: String((error && error.message) || error),
    };
  }
}

async function showStatus(reply) {
  await chrome.action.setBadgeText({ text: reply.ok ? "" : "!" });
  await chrome.action.setTitle({ title: reply.ok ? "mneva" : `mneva: ${reply.message}` });
}

// `mneva setup` refreshes the folder this extension was loaded from, but
// Chrome keeps running the files it loaded. The host reports the version in
// that folder; when it differs from ours, reload to pick up the new files.
async function reloadIfUpdated(reply) {
  const manifest = chrome.runtime.getManifest();
  const onDisk = reply && reply.extension_version;
  // A store install has no such folder and updates itself.
  if (manifest.update_url || !onDisk || onDisk === manifest.version) return;
  // Loaded from some other folder, the versions never match. Try once per
  // version: Chrome disables an extension that keeps reloading itself.
  const { reloadedFor } = await chrome.storage.local.get("reloadedFor");
  if (reloadedFor === onDisk) return;
  await chrome.storage.local.set({ reloadedFor: onDisk });
  setTimeout(() => chrome.runtime.reload(), RELOAD_DELAY_MS);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message && message.type === "get_brief") {
    askHost({ type: "get_brief", max_chars: BRIEF_CHARS }).then(async (reply) => {
      await showStatus(reply);
      sendResponse(reply);
      await reloadIfUpdated(reply);
    });
    return true; // keeps sendResponse alive for the async reply
  }
  if (message && message.type === "ping") {
    askHost({ type: "ping" }).then(sendResponse);
    return true;
  }
  return false;
});

// Runs in the page: insert into whatever text field has focus.
function insertIntoFocused(text) {
  const el = document.activeElement;
  if (!el) return false;
  const editable =
    el.isContentEditable || el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type === "text");
  if (!editable) return false;
  el.focus();
  return document.execCommand("insertText", false, `${text}\n\n`);
}

chrome.commands.onCommand.addListener(async (command, tab) => {
  if (command !== "insert-profile" || !tab || tab.id === undefined) return;
  const reply = await askHost({ type: "get_brief", max_chars: BRIEF_CHARS });
  await showStatus(reply);
  if (reply.ok) {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: insertIntoFocused,
      args: [reply.text],
    });
  }
  await reloadIfUpdated(reply);
});

// Chrome puts content scripts only into pages loaded after an install or a
// reload. AI tabs already open would stay without one until refreshed.
chrome.runtime.onInstalled.addListener(async ({ reason }) => {
  if (reason !== "install" && reason !== "update") return;
  for (const { matches, js } of chrome.runtime.getManifest().content_scripts) {
    for (const tab of await chrome.tabs.query({ url: matches })) {
      // A tab can close or navigate away meanwhile; nothing to do then.
      chrome.scripting.executeScript({ target: { tabId: tab.id }, files: js }).catch(() => {});
    }
  }
});

chrome.runtime.onStartup.addListener(async () => {
  await reloadIfUpdated(await askHost({ type: "ping" }));
});
