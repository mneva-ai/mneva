# mneva browser extension: privacy policy

Last updated: 2026-10-20. Applies to the mneva extension for Chrome and Microsoft Edge, version 0.3.0 and later.

## What the extension does

The extension has one purpose: keep your AI profile in sync across AI chat sites. When you start a new chat on ChatGPT (chatgpt.com), Claude (claude.ai), Gemini (gemini.google.com), Grok (grok.com) or Doubao (www.doubao.com), it puts your mneva profile into the message box, so the AI knows who you are from the first message. You can also insert the profile into any focused text field with Alt+Shift+M.

## Where your profile comes from

Your profile is a set of Markdown files on your own computer, written and kept by the mneva program. The extension reads it from that program through the browser's native messaging, which only works with a program installed on the same computer. There is no mneva server and no mneva account. The extension makes no network requests of its own.

## What leaves your computer

- **The profile text you send.** Once the profile is in the message box, it is part of your message. If you send that message, the AI site receives it like anything else you type, under that site's own privacy policy. You can edit or delete the text before sending.
- **Your per-site on/off switches.** The popup lets you turn the extension off for each site. These switches are stored with `chrome.storage.sync`, so if browser sync is on, your browser vendor syncs them between your own browsers. They contain only site names and on/off values.

Nothing else leaves your computer. The extension does not collect, sell, or share any data, does not track browsing, and contains no analytics or ads.

## What the extension reads on the AI sites

On the five sites above, the extension checks the page address to tell whether you are starting a new chat, finds the chat input box, and checks that it is empty before placing your profile in it. It does not read, record or send your conversations.

## Permissions and why each is needed

| Permission | Why |
|---|---|
| `nativeMessaging` | Read your profile from the mneva program on your computer. |
| `storage` | Remember your per-site on/off switches and avoid repeated reloads after an update. |
| `scripting`, `activeTab` | Insert the profile into the focused text field when you press Alt+Shift+M, and start working in AI tabs that were already open when the extension was installed. |
| Access to the five AI sites | Find the chat input box on those sites only. |

## Limited Use

The use of information received from these permissions adheres to the Chrome Web Store User Data Policy, including the Limited Use requirements.

## Changes

If a future version reads more than described here (for example, recording your chats to update your profile), it will ask for your consent first and this page will be updated before that version is released.

## Contact

Open an issue at https://github.com/mneva-ai/mneva/issues.
