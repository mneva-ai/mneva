// Talks to the mneva native host that `mneva setup` registers. The host only
// renders the profile brief; nothing here touches the network.
const HOST = "org.mneva.brief";
const BRIEF_CHARS = 4000;

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

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message && message.type === "get_brief") {
    askHost({ type: "get_brief", max_chars: BRIEF_CHARS }).then(async (reply) => {
      await showStatus(reply);
      sendResponse(reply);
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
  if (!reply.ok) return;
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: insertIntoFocused,
    args: [reply.text],
  });
});
