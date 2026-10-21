# Store listing: Chrome Web Store and Microsoft Edge Add-ons

Text to paste into each store's developer dashboard. Upload `dist/mneva-extension-<version>.zip` from `python store/build.py`. Privacy policy URL: https://github.com/mneva-ai/mneva/blob/main/docs/privacy.md

## Name

mneva

## Short description (132 characters max)

EN: Start every new AI chat with your own profile, read from your computer. ChatGPT, Claude, Gemini, Grok, Doubao.

ZH: 每次新开 AI 对话，自动带上你电脑里的个人档案。支持 ChatGPT、Claude、Gemini、Grok、豆包。

## Detailed description

### English

Tired of telling every AI who you are, what you work on and how you want answers?

mneva keeps one profile on your own computer, as Markdown files you can open and edit. This extension puts that profile into the message box whenever you start a new chat on ChatGPT, Claude, Gemini, Grok or Doubao, so every AI starts out knowing you. Press Alt+Shift+M to insert it into any other text field.

- Your profile stays on your computer. The extension reads it from the mneva program through the browser's native messaging. No mneva account, no mneva server.
- You see the profile before you send it, and can edit or delete it.
- Turn it off per site in the popup.

Requires the free mneva program. Install it with one line from https://github.com/mneva-ai/mneva

### 中文

每换一个 AI，都要重新说一遍你是谁、在做什么、喜欢怎样的回答？

mneva 把你的个人档案存在你自己的电脑上，是可以直接打开编辑的 Markdown 文件。装上这个扩展后，在 ChatGPT、Claude、Gemini、Grok 或豆包新开对话时，它会把档案放进输入框，每个 AI 一开始就了解你。在别的输入框里按 Alt+Shift+M 也能插入。

- 档案留在你的电脑上。扩展通过浏览器的本机通信从 mneva 程序读取，没有 mneva 账号，也没有 mneva 服务器。
- 发送之前你能看到档案内容，可以修改或删掉。
- 可以在弹出窗口里按网站单独关闭。

需要先安装免费的 mneva 程序，一行命令即可，见 https://github.com/mneva-ai/mneva

## Category

Productivity (Chrome: Workflow & Planning; Edge: Productivity)

## Single purpose (Chrome dashboard, Privacy tab)

Keep the user's AI profile in sync across AI chat sites: insert the profile, read from the mneva program on the user's computer, into new chats on ChatGPT, Claude, Gemini, Grok and Doubao.

## Permission justifications

- **nativeMessaging:** The profile lives in Markdown files managed by the mneva program on the user's computer. Native messaging is how the extension reads it without any server.
- **storage:** Stores the user's per-site on/off switches, and a marker that prevents repeated reloads after the local copy updates.
- **scripting:** Inserts the profile into the focused text field when the user presses Alt+Shift+M, and starts the content script in AI tabs that were already open at install time.
- **activeTab:** Limits the Alt+Shift+M insert to the tab the user is in.
- **Host permissions (chatgpt.com, claude.ai, gemini.google.com, grok.com, www.doubao.com):** The content script finds the chat input on these five sites to place the profile in a new chat. No other sites.
- **Remote code:** None. All code ships in the package.

## Data usage disclosures (Chrome dashboard)

- Collected data types: none. The profile is read from the user's own computer and only placed in the page the user is typing in; the extension does not transmit it anywhere.
- Certify: not sold to third parties; not used or transferred for purposes unrelated to the single purpose; not used for creditworthiness or lending.

## Still needed before submitting

- Icons: 16, 48 and 128 px PNG in the package (`icons` in the manifest), and a 128 px store icon.
- Screenshots: at least one 1280x800 (Chrome) and the same for Edge, showing a new chat with the profile inserted.
- Each store shows the extension's ID as soon as the first draft is uploaded, before review. Add both IDs to `native_host.STORE_EXTENSION_IDS` and release mneva before the listings go live, or a store install cannot reach the host (`mneva setup` writes the allowed IDs into the host manifest). After approval, switch setup's text to the store links.
