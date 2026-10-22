# mneva

**你的 AI 记忆跟着你走。换了工具，每个 AI 照样认识你。**

每开一个新的 AI 对话都得从零说起，每个应用只在自己里面记得你，于是你一遍遍重新交代自己是谁、在做什么、喜欢什么样的回答。mneva 把你的记忆存成你自己电脑上的 Markdown 文件，只存一份，带进 ChatGPT、Claude、Gemini、Grok、豆包（在 Chrome 或 Edge 里），还有 Claude Code、Codex 和 Claude 桌面版。在这些工具之间来回切换，记忆一直跟着你。不用注册账号，没有 mneva 云端，每一行你都能打开、修改、删除。

[English](https://github.com/mneva-ai/mneva/blob/main/README.md) | **中文**

---

## 目录

- [一行命令安装](#一行命令安装)
- [装好以后](#装好以后)
- [在哪里能用](#在哪里能用)
- [为什么用 Markdown 文件](#为什么用-markdown-文件)
- [开发者看这里](#开发者看这里)
- [路线图](#路线图)
- [反馈与贡献](#反馈与贡献)
- [许可证](#许可证)

---

## 一行命令安装

事先不用装 Python。脚本会先装 [uv](https://docs.astral.sh/uv/)，由 uv 装好 mneva 和它要用的 Python，再运行 `mneva setup`，把 Claude Code、Codex、Claude 桌面版和浏览器都接上。重复运行不会改动任何东西。

**中国大陆**（所有文件都从国内镜像下载：uv 和软件包走清华或腾讯的 PyPI 镜像，Python 走 npmmirror，以后升级也继续走同一个镜像）：

Windows，打开 PowerShell，粘贴：

```powershell
$env:MNEVA_MIRROR='cn'; irm https://cdn.jsdelivr.net/gh/mneva-ai/mneva@main/install/install.ps1 | iex
```

macOS / Linux，打开终端，粘贴：

```bash
curl -LsSf https://cdn.jsdelivr.net/gh/mneva-ai/mneva@main/install/install.sh | MNEVA_MIRROR=cn sh
```

**其他地区：**

Windows（PowerShell）：

```powershell
irm https://raw.githubusercontent.com/mneva-ai/mneva/main/install/install.ps1 | iex
```

macOS / Linux：

```bash
curl -LsSf https://raw.githubusercontent.com/mneva-ai/mneva/main/install/install.sh | sh
```

装完以后新开一个终端，就能直接用 `mneva` 命令。

## 装好以后

三步，每步只做一次。

### 1. 写你的档案

安装时已经存好一份模板，在 `~/.mneva/profile-template.md`（Windows 上是 `C:\Users\<你的用户名>\.mneva\profile-template.md`）。用任何文本编辑器打开，写上你是谁、在做什么、希望 AI 怎么回答你。然后把它存进 mneva：

- **用 Claude Code 或 Codex 的话**，对它说：*"读取 ~/.mneva/profile-template.md，把每一节用 capture_memory 存进 mneva，scope 用 profile，lifespan 用 permanent。"*
- **不用它们的话**，在终端里一节一节存：

  ```bash
  mneva capture --scope profile --lifespan permanent "我用中文交流。回答简短一些，给具体步骤。"
  ```

运行 `mneva brief`，可以看到 AI 工具会拿到的档案内容。

### 2. 打开浏览器扩展

扩展还没上架 Chrome 和 Edge 的应用商店，所以现在要手动加载一次：

1. Chrome 里打开 `chrome://extensions`，Edge 里打开 `edge://extensions`。
2. 打开 **开发者模式**。
3. 点 **加载已解压的扩展程序**，选文件夹 `~/.mneva/extension`（Windows 上是 `C:\Users\<你的用户名>\.mneva\extension`）。

之后在 ChatGPT、Claude、Gemini、Grok、豆包开新对话，都会自动带上你的档案。在别的网站按 Alt+Shift+M 插入。扩展弹窗里可以按网站关掉。档案通过 `mneva setup` 注册的本地通道从你自己的电脑读取，不用开服务，也不用密钥。档案内容只会进入你自己开的对话。

### 3. 让档案保持最新

- 随时可以改档案：`mneva capture` 新增一条记录，也可以直接编辑 `~/.mneva/store/` 下的 Markdown 文件。
- 如果你用 Claude Code 或 Codex，`mneva learn` 会读你在里面打过的提问，对档案提出修改建议。你接受之前什么都不会改：`mneva learn --accept 1,2`（或 `all`）接受，`mneva learn --discard` 放弃。有了档案以后，它每天会在你打开 Claude Code 或 Codex 时自己跑一次，有待确认的修改时，下一次对话会提一句。设置 `MNEVA_LEARN_AUTO=0` 可以关掉。
- `mneva upgrade` 会更新 mneva 并刷新扩展，扩展会自己重新加载。

## 在哪里能用

| 你在哪里用 AI | 它怎么拿到你的档案 |
| --- | --- |
| 网页版 ChatGPT、Claude、Gemini、Grok、豆包（Chrome、Edge） | 扩展在每个新对话里自动加上 |
| 其他网站 | 按 Alt+Shift+M 插入 |
| Claude Code、Codex | `mneva setup` 已接好，每次对话开始时读取 |
| Claude 桌面版（Windows、macOS） | `mneva setup` 已接好，彻底退出 Claude 再打开一次 |
| 手机 App 和其他工具 | 运行 `mneva brief --copy`，粘贴进 App 的"关于你"设置（ChatGPT 加 `--max-chars 1500`）。复制之后档案有变化，mneva 会提醒你 |

从网页对话里学习、自动帮你填好手机 App 的设置，这两件事在计划中，见 [路线图](#路线图)。

## 为什么用 Markdown 文件

大多数 AI 记忆工具把你的记忆存在它们自己的数据库里。mneva 存在你的文件里。

- **你能读，也能改。** 每条记录是 `~/.mneva/store/` 下一个带简短 YAML 头的 Markdown 文件。AI 把你的事记错了，打开文件改掉那一行就行。
- **没有账号，没有 mneva 云端。** mneva 不会把你的任何信息发到它自己的服务器，也没有遥测。只有你自己打开的功能才会连外部服务：`mneva learn` 把你的提问交给你本机的 Claude Code，自带密钥的命令会调用你配了密钥的服务商。
- **配合你自己的工具。** 整个文件夹可以提交进 git，在 PR 里审改动，也可以和 Obsidian 仓库双向同步（`mneva sync-vault`）。
- **搜索索引可以随时删。** 删掉 `~/.mneva/mneva.sqlite`，`mneva reindex` 会从 Markdown 重建，什么都不会丢。

---

## 开发者看这里

### 其他 MCP 客户端

`mneva setup` 会自己接好 Claude Code、Codex 和 Claude 桌面版。其他客户端，把下面这样的配置粘进它的 MCP 配置，然后重启客户端。mneva 第一次启动时会自动创建 `~/.mneva/`。

**Cursor：** 新建 `~/.cursor/mcp.json`（或工作区内的 `.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["--from", "mneva", "mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "cursor" }
    }
  }
}
```

**Windsurf：** 编辑 `~/.codeium/windsurf/mcp_config.json`，结构相同（`"MNEVA_MCP_CLIENT": "windsurf"`）。

**ChatGPT 桌面版：** MCP 支持在应用设置的 **开发者模式（beta）** 里。打开它，加上同样的配置（`"MNEVA_MCP_CLIENT": "chatgpt-desktop"`）。

**Cline / Continue：** 两者都认同样的配置，作用范围是你的 VS Code 工作区。

> **第一次启动慢，之后很快。** 第一次运行会下载 mneva 和依赖并缓存。如果客户端第一次提示服务器慢或失败，重启一次客户端就好。想提前缓存，可以在终端里跑一次 `uvx --from mneva mneva-mcp`，看到它启动后按 Ctrl-C。

重启后对客户端说 *"记住我们决定了 X"*，mneva 会存一条记录，下次会话可以搜到。

### 命令行

```sh
mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"
mneva search "SQLite"
mneva replay --tool=claude-code --scope=my-project
mneva reindex   # 手动改过 Markdown 后，重建搜索索引
```

### 跟着 repo 走的记忆

在 git 仓库里捕获时，记录会把来源写进 frontmatter：

```yaml
scope: my-project
lifespan: permanent
repo: github.com/mneva-ai/mneva
branch: main
commit_sha: cd6d7af1c3a2982810799d2f023a028fc361c6dc
```

`mneva search` 默认只搜你当前所在的仓库：

```sh
mneva search "SQLite"                # 当前仓库（外加不属于任何仓库的记忆）
mneva search "SQLite" --all-repos    # 全部
mneva capture --scope p --no-git "…" # 完全不记录来源
```

`repo` 取自归一化后的 remote URL，所以把项目 clone 到别处仍然匹配。不属于任何仓库的记忆永远不会被藏起来，被过滤掉的只有属于**别的**仓库的记忆。没有 git、不是仓库、没有 remote，都只是不记来源。

### 手动安装

需要 **Python 3.11 或更新版本**，推荐再装 [uv](https://docs.astral.sh/uv/getting-started/installation/)。

```sh
uv tool install mneva
mneva setup
```

- **pipx：** `pipx install mneva`，然后 `mneva setup`。
- **不安装：** `uvx mneva setup` 和 `uvx --from mneva mneva-mcp` 每次运行都会取最新发布版。
- **从源码：** `git clone https://github.com/mneva-ai/mneva.git && cd mneva && pip install -e ".[dev]"`。

`mneva setup --dry-run` 只显示要做什么，不真正执行。如果 Claude 桌面版的配置文件解析不了，setup 不会动它，而是打印出需要手动加的配置。

### 更新

```sh
mneva upgrade
```

它会识别 mneva 当初是怎么装的（`pipx`、`uv tool`、`uvx` 或 `pip`），跑对应的更新命令，再用新版本重跑一次 `mneva setup`。这会刷新浏览器扩展的文件，扩展会自己重新加载，已经打开的 AI 网页也会生效。加 `--dry-run` 只打印命令。

### 自带密钥的功能

`mneva synthesize`、`mneva digest` 和 `mneva distill` 会用你环境变量里的密钥调用 LLM 服务商（Anthropic、OpenAI、Google 或 OpenRouter）。`mneva learn --backend` 也一样，用 API 代替本机的 Claude Code。配置方法见 [`docs/providers.md`](https://github.com/mneva-ai/mneva/blob/main/docs/providers.md)。

- `mneva synthesize --scope X --backend anthropic`：对一个 scope 做两阶段头脑风暴。
- `mneva digest --scope X --backend anthropic --write-bootstrap`：把一个 scope 压缩成 `bootstrap.md`，可以粘进新会话。
- `mneva distill --source path/to/transcript.md --scope X`：从一段对话记录里抽取永久记录。花钱之前会先问你，`--yes` 跳过确认。

### 诊断

`mneva diagnose [--share]` 打印一份脱敏的状态报告（平台、Python 版本、记录数、已配置的后端、各客户端计数、最后活动时间）。它只打印，mneva 不会把它发到任何地方。觉得哪里不对时，把结果贴进 bug 反馈。

### 技术细节

- 一个命令行（`mneva`）加一个基于官方 `mcp` SDK 的 MCP 服务器（`mneva-mcp`），提供六个工具：`capture_memory`、`search_memory`、`forget_memory`、`list_recent_memories`、`replay_context`、`get_status`。
- 存储：`~/.mneva/` 下带 YAML frontmatter 的 Markdown，用 SQLite 建索引（WAL 模式，多个客户端同时访问也安全）。
- 搜索：`rank-bm25` 关键词打分，可选 `sqlite-vec` 重排。
- 浏览器扩展：Manifest V3，通过 Chrome native messaging 和 mneva 通信。隐私政策：[`docs/privacy.md`](https://github.com/mneva-ai/mneva/blob/main/docs/privacy.md)。
- 可选 HTTP API（`mneva serve`，FastAPI）。

### 测试

```sh
pip install -e ".[dev]"
pytest
```

每个 PR 都会在 ubuntu、macOS、Windows 上用 Python 3.11 到 3.14 跑 CI（[`ci.yml`](https://github.com/mneva-ai/mneva/blob/main/.github/workflows/ci.yml)），并在干净的机器上跑两个安装脚本，开和不开镜像模式各一遍。

---

## 路线图

mneva 处于 **alpha 阶段**。

- [X] **v0.1**：命令行、Markdown 存储、BM25 和 sqlite-vec 索引、回放模板、HTTP API、四家 BYOK 服务商、Obsidian 仓库同步、`mneva distill`
- [X] **v0.2**：MCP 服务器（`mneva-mcp`，六个工具）、`uvx` 安装、多客户端并发安全的 WAL、可选的 `mneva diagnose`
- [X] **v0.3**：跟着 git 走的记忆、给不支持 MCP 的工具用的 `mneva brief`、接入 Claude Code 和 Codex 的 `mneva setup`
- [X] **v0.4**：Chrome 和 Edge 浏览器扩展，在 ChatGPT、Claude、Gemini、Grok、豆包开新对话时自动带上档案；`mneva upgrade`
- [X] **v0.5**：`mneva learn` 根据你在 Claude Code 和 Codex 里打过的提问，提出档案修改建议，你接受之前什么都不改
- [X] **v0.6**：`mneva learn` 每天自己跑一次
- [X] **v0.7**：一行命令安装，带中国大陆镜像模式；`mneva setup` 接入 Claude 桌面版
- [ ] **下一步**：扩展上架 Chrome 应用商店和 Edge 加载项商店，点一下就能装
- [ ] **再往后**：可选地记录你的网页对话，用 Claude Code、Codex 或 DeepSeek 密钥从中学习，并在扩展里审阅修改建议
- [ ] **之后**：把你确认过的档案写进各个网站自己的设置，手机 App 也能用上

---

## 反馈与贡献

- **[提 issue](https://github.com/mneva-ai/mneva/issues)**：报 bug、提问题、提需求都可以。
- **欢迎 PR。** Fork 仓库，在分支上改，跑通 `pytest`、`ruff check .` 和 `mypy src`，然后向 `main` 提 PR，说明改了什么、为什么改。

## 许可证

Apache License 2.0，见 [LICENSE](https://github.com/mneva-ai/mneva/blob/main/LICENSE)。

**链接：** [PyPI](https://pypi.org/project/mneva/) · [更新日志](https://github.com/mneva-ai/mneva/blob/main/CHANGELOG.md) · [Issues](https://github.com/mneva-ai/mneva/issues)
