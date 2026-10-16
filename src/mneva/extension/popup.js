const SITES = {
  "chatgpt.com": "ChatGPT",
  "claude.ai": "Claude",
  "gemini.google.com": "Gemini",
  "www.doubao.com": "Doubao",
};

async function showStatus() {
  const status = document.getElementById("status");
  const reply = await chrome.runtime.sendMessage({ type: "ping" });
  if (reply && reply.ok) {
    status.textContent = `Connected to mneva ${reply.version}`;
  } else {
    status.textContent = (reply && reply.message) || "mneva is not reachable. Run `mneva setup`.";
    status.className = "bad";
  }
}

async function showSites() {
  const { disabled = {} } = await chrome.storage.sync.get("disabled");
  const container = document.getElementById("sites");
  for (const [host, name] of Object.entries(SITES)) {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = !disabled[host];
    box.addEventListener("change", async () => {
      const current = (await chrome.storage.sync.get("disabled")).disabled || {};
      current[host] = !box.checked;
      await chrome.storage.sync.set({ disabled: current });
    });
    label.append(box, ` ${name}`);
    container.append(label);
  }
}

showStatus();
showSites();
