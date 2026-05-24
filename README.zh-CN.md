<div id="top">

<!-- HEADER STYLE: MODERN -->
<div align="left" style="position: relative; width: 100%; height: 100%; ">

# MNEVA

<em>持久化的智能体上下文底座。本地优先的 Markdown 仓库，任何 AI 工具都能查询。</em>

<!-- BADGES -->
<!-- local repository, no metadata badges. -->

<em>构建所用的工具与技术：</em>

<img src="https://img.shields.io/badge/Anthropic-191919.svg?style=flat-square&logo=Anthropic&logoColor=white" alt="Anthropic">
<img src="https://img.shields.io/badge/TOML-9C4121.svg?style=flat-square&logo=TOML&logoColor=white" alt="TOML">
<img src="https://img.shields.io/badge/Ruff-D7FF64.svg?style=flat-square&logo=Ruff&logoColor=black" alt="Ruff">
<img src="https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square&logo=FastAPI&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Pytest-0A9EDC.svg?style=flat-square&logo=Pytest&logoColor=white" alt="Pytest">
<br>
<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat-square&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=flat-square&logo=GitHub-Actions&logoColor=white" alt="GitHub%20Actions">
<img src="https://img.shields.io/badge/OpenAI-412991.svg?style=flat-square&logo=OpenAI&logoColor=white" alt="OpenAI">
<img src="https://img.shields.io/badge/Google%20Gemini-8E75B2.svg?style=flat-square&logo=Google-Gemini&logoColor=white" alt="Google%20Gemini">

</div>
</div>
<br clear="right">

[English](./README.md) | **中文**

---

## 目录

- [目录](#目录)
- [概览](#概览)
- [你能得到什么](#你能得到什么)
- [项目结构](#项目结构)
    - [项目索引](#项目索引)
- [快速开始](#快速开始)
    - [环境要求](#环境要求)
    - [接入你的 AI 助手（主推路径）](#接入你的-ai-助手主推路径)
    - [命令行试用](#命令行试用)
    - [在浏览器网页版 AI 里使用](#在浏览器网页版-ai-里使用)
    - [其他安装方式](#其他安装方式)
    - [更新 mneva](#更新-mneva)
    - [进阶 — 自带密钥（BYOK）的 LLM 功能](#进阶--自带密钥byok的-llm-功能)
    - [可观测性（可选）](#可观测性可选)
    - [测试](#测试)
- [路线图](#路线图)
- [参与贡献](#参与贡献)
- [许可证](#许可证)
- [链接](#链接)

---

## 概览

**问题在哪：** 每个 AI 助手都健忘。开个新对话，你就得把项目从头解释一遍；从 Claude 换到 Cursor，上下文又跟不过去。你花时间教给一个工具的那些决定、约束和事实，下一个工具完全看不到。

**mneva 就是来解决这个的。** 它是一个本地优先的记忆层，能跟随你穿梭于各个 AI 助手之间。在 Claude Desktop 里记下一个决定，明天在 Cursor 里就能问到它。所有记录都以纯 Markdown 文件的形式存放在 `~/.mneva/` 下——数据归你所有，mneva 负责让它跨工具持久存在。

**v0.2 — mneva 现在会说 MCP 了。** 把 `mneva-mcp` 接进任何支持模型上下文协议（Model Context Protocol，MCP）的客户端（Claude Desktop、Claude Code、Cursor、Windsurf、Cline、Continue，以及开发者模式下的 ChatGPT Desktop），只需 30 秒。AI 客户端负责智能，mneva 负责记忆。记忆层本身不需要任何 API 密钥。

---

## 你能得到什么

- **🧠 跨工具的记忆。** 在一个 AI 客户端里记下，在另一个里就能调出。你的上下文不再困死在单个聊天窗口里。
- **⚡ 零密钥、30 秒配好。** MCP 记忆层不需要任何 API 密钥——智能由你的 AI 客户端提供。粘一段配置、重启、搞定。
- **🏠 数据在你自己硬盘上。** 记录就是 `~/.mneva/` 下的纯 `.md` 文件。用任何编辑器打开、通过你自己的 Obsidian 仓库同步、用 git 做版本管理。没有服务器、没有账号、不上传。
- **🔍 搜得准。** BM25 关键词排序 + 可选的 `sqlite-vec` 向量重排，可按项目范围（scope）和记忆该存多久（临时 / 永久）过滤。
- **🔒 默认私密。** 除非你主动启用进阶的 BYOK 功能，否则 mneva 不发起任何对外网络请求。永不遥测——唯一会“吐”东西的是可选的 `mneva diagnose --share`，而且它只把结果给到你的剪贴板，不是发给我们。

### 用之前 / 用之后

**没有 mneva 时**，每个新会话都这样开头：

> “先交代下背景：我们用的是 SQLite 不是 Postgres，鉴权在 `auth.ts` 里，websocket 那个方案我们已经否了……”

**有了 mneva**，你只说一次。之后你接入的任何 AI 客户端都直接知道——跨对话、跨工具、跨天。

### 技术细节（实打实）

- **Python 3.11+**，一个独立命令行（`mneva`）加一个 MCP 服务器（`mneva-mcp`）。
- **MCP 服务器** 基于官方 `mcp` SDK（FastMCP），暴露 6 个会被你的 AI 客户端自动发现的工具：`capture_memory`、`search_memory`、`forget_memory`、`list_recent_memories`、`replay_context`、`get_status`。
- **存储：** `~/.mneva/` 下的纯 Markdown + YAML frontmatter，用 SQLite 建索引（WAL 模式，支持多个 AI 客户端并发安全访问）。
- **搜索：** `rank-bm25` 关键词打分 + 可选的 `sqlite-vec` 向量重排。
- **可选 HTTP API**（`mneva serve`，FastAPI）和 **BYOK 服务商**（Anthropic / OpenAI / Google / OpenRouter）支撑进阶的 `synthesize` / `digest` / `distill` 命令。

---

## 项目结构

```sh
└── mneva/
    ├── .github
    │   └── workflows
    ├── CHANGELOG.md
    ├── docs
    │   ├── alpha-onboarding.md
    │   ├── manual-smoke-m6.md
    │   └── providers.md
    ├── LICENSE
    ├── mypy.ini
    ├── pyproject.toml
    ├── pytest.ini
    ├── README.md
    ├── src
    │   └── mneva
    └── tests
        ├── __init__.py
        ├── __pycache__
        ├── conftest.py
        ├── integration
        └── unit
```

### 项目索引

> 详细的逐文件说明，请参见英文版 [README.md 的 Project Index 小节](./README.md#project-index)（文件名为代码标识符，保持英文）。下面给出每个核心模块的简要中文说明：

- **`src/mneva/api.py`** — 定义 FastAPI Web 应用，暴露捕获、遗忘、搜索、回放记录的接口；通过 token 中间件做鉴权，并与索引器、存储层、回放模块协作。外部工具主要通过这个 HTTP 接口与 mneva 知识库交互。
- **`src/mneva/cli.py`** — 基于 Click 的命令行入口。提供初始化数据根目录、捕获与搜索记录、为各类 AI 编码工具生成上下文回放、启动本地 API 服务、以及两阶段综合/bootstrap 摘要等命令。
- **`src/mneva/config.py`** — 用一个冻结的 dataclass 管理设置（如 API token、嵌入向量服务商），并提供从 JSON 文件读写配置的工具。
- **`src/mneva/indexer.py`** — 实现混合搜索索引：BM25 排序 + 可选的 sqlite-vec 重排，支持按 scope 和 lifespan 过滤，返回最相关的前 k 条记录。
- **`src/mneva/paths.py`** — 管理 mneva 主目录：优先读 `$MNEVA_HOME` 环境变量，否则默认 `~/.mneva`，并幂等地创建所需子目录。
- **`src/mneva/replay.py`** — 为支持的工具生成上下文回放块，把模板和已捕获的永久记录组合起来，可按 scope 过滤。CLI 的 `replay` 命令和 `GET /replay` 接口共用这段逻辑。
- **`src/mneva/store.py`** — 把结构化记录以带 frontmatter 元数据的 Markdown 文件形式持久化，是基于文件的存储层，提供增删改查与遍历操作。
- **`src/mneva/synth.py`** — 实现两阶段头脑风暴与批判性分析流水线，以及生成 L1 bootstrap 摘要的 digest 生成器。所有 LLM 调用都通过 Provider 协议路由，保持模块与具体服务商解耦。
- **`src/mneva/mcp_server.py`** — FastMCP 服务器，暴露 6 个 MCP 工具（捕获/搜索/遗忘/列出最近/回放/状态），是 v0.2 接入各 AI 客户端的主路径。
- **`src/mneva/providers/`** — 每个 AI 服务（Anthropic / OpenAI / Google / OpenRouter）一个适配模块，统一实现 Provider 协议；密钥仅从环境变量读取。
- **`.github/workflows/`** — `ci.yml`（多系统多 Python 版本的检查、类型检查、测试），`install-verify.yml`（发布后跨系统安装验证）。

---

## 快速开始

### 环境要求

- **Python 3.11 或更新版本**
- **uv**（推荐）。如果你还没有 uv：
  - **macOS / Linux：** `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - **Windows（PowerShell）：** `irm https://astral.sh/uv/install.ps1 | iex`
  - 如果在 Windows 上装完后 `uv` 命令不被识别，关掉终端重新打开一个（uv 安装时会把自己写进 PATH，但只有新开的终端才会读到这个改动 — 这和 pipx 是同一个坑）。

`pipx` 仍然作为备选方案受支持，见下方 *其他安装方式*。

### 接入你的 AI 助手（主推路径）

挑一个你最常用的 AI 客户端，把下面的片段粘进它的 MCP 配置里，然后重启客户端。mneva-mcp 第一次启动时会自动创建 `~/.mneva/` — 不需要先跑 `mneva init`。

**Claude Desktop** — 编辑 `claude_desktop_config.json`：

- **macOS：** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows：** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "claude-desktop" }
    }
  }
}
```

**Claude Code** — 编辑 `~/.claude.json`（或运行 `claude mcp add`）：

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "claude-code" }
    }
  }
}
```

**Cursor** — 新建 `~/.cursor/mcp.json`（或工作区内的 `.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "mneva": {
      "command": "uvx",
      "args": ["mneva-mcp"],
      "env": { "MNEVA_MCP_CLIENT": "cursor" }
    }
  }
}
```

**Windsurf** — 编辑 `~/.codeium/windsurf/mcp_config.json`，结构相同（`"MNEVA_MCP_CLIENT": "windsurf"`）。

**ChatGPT Desktop** — MCP 支持目前在应用内设置的 **开发者模式（beta）** 后面；开启它，然后加上同样的配置块（`"MNEVA_MCP_CLIENT": "chatgpt-desktop"`）。

**Cline / Continue** — 两者都认同样的配置，作用范围是你的 VS Code 工作区。

重启之后，对 AI 客户端说一句 *“记住我们决定了 X”*，看着 mneva 追加一条记录。下次会话就能搜到它。

### 命令行试用

命令行是更底层的入口 — 适合写脚本，或者在没有 MCP 客户端的场景下使用。

```sh
uvx mneva init
uvx mneva capture --scope my-project --lifespan permanent \
    "decision: use SQLite over Postgres for v0 because zero-ops"
uvx mneva search "SQLite"
uvx mneva replay --tool=claude-code --scope=my-project
```

### 在浏览器网页版 AI 里使用

MCP 这条路覆盖的是桌面 AI 客户端。纯网页版的 AI 聊天界面（claude.ai 网页版、chatgpt.com、gemini.google.com、chat.deepseek.com）没法用 MCP，因为浏览器不允许网页启动本地进程。在 v0.3 的浏览器扩展上线之前，变通办法如下：

| 你的 AI                                | v0.2 原生支持                    | 变通办法                                                |
| -------------------------------------- | -------------------------------- | ------------------------------------------------------- |
| Claude Desktop / Claude Code           | ✅ MCP                            | —                                                       |
| Cursor / Windsurf / Cline / Continue   | ✅ MCP                            | —                                                       |
| ChatGPT Desktop                        | ⚠️ MCP（开发者模式 beta）        | 在应用里开启开发者模式                                  |
| claude.ai 网页版                       | ❌                                | 装 Claude Desktop（同一账号，同一份记忆）               |
| chatgpt.com 网页版                     | ❌                                | 装 ChatGPT Desktop + 开发者模式                         |
| gemini.google.com                      | ❌                                | 用命令行手动流程（见下）                                |
| DeepSeek 网页版                        | ❌                                | 用命令行手动流程（见下）                                |

**命令行手动流程：**
1. 在聊天里出现一个值得记的决定后，跑 `uvx mneva capture --scope myproj "..."`。
2. 在向新的 AI 提后续问题之前，跑 `uvx mneva search "话题"`。
3. 把终端里匹配到的记录复制进新的聊天，作为上下文。

### 其他安装方式

- **`pipx install mneva`** — 仍然受支持。已有的 v0.1.x 用户跑 `pipx upgrade mneva` 后，会同时得到 `mneva` 和 `mneva-mcp` 两个命令。
- **`uv tool install mneva` + `uv tool upgrade mneva`** — 如果你想要一个固定的、由你显式升级的安装，这种方式比裸跑 `uvx mneva` 更合适（`uvx` 在首次运行时解析并缓存；`uvx mneva@latest` 会强制重新解析到最新版）。
- **从源码安装：** `git clone https://github.com/mneva-ai/mneva.git && cd mneva && pip install -e ".[dev]"`。

### 更新 mneva

```sh
mneva upgrade
```

`mneva upgrade` 会自动识别你当初是怎么装的 mneva（`pipx` / `uv tool` / `uvx` / `pip`），然后跑对应的更新命令，这样你就不用记自己用的是哪种方式了。加上 `--dry-run` 可以只打印命令、不真正执行。如果你是用裸 `uvx mneva-mcp` 运行的，uvx 每次运行本来就会拉取最新发布版，所以没有需要“更新”的东西。

### 进阶 — 自带密钥（BYOK）的 LLM 功能

`mneva synthesize`、`mneva digest` 和 `mneva distill` 会调用外部 LLM 服务商来做摘要和记录抽取。它们需要你在环境变量里配一个密钥（Anthropic / OpenAI / Google / OpenRouter — 任选其一）。这些是面向高级用户的功能，不属于主打的 MCP 路径。

- `mneva synthesize --scope X --backend anthropic` — 对某个 scope 做两阶段（Stage 1 / Stage 2）头脑风暴。
- `mneva digest --scope X --backend anthropic --write-bootstrap` — 把一个 scope 提炼成 `bootstrap.md`，你可以粘进新的工具会话里。
- `mneva distill --source path/to/transcript.md --scope X` — 从一段原始对话记录里抽取永久记录。会有费用确认；加 `--yes` 跳过确认提示。

各服务商的配置说明见 [`docs/providers.md`](./docs/providers.md)。

### 可观测性（可选）

`mneva diagnose [--share]` 会打印一份脱敏的状态报告（平台、Python 版本、按生命周期统计的记录数、已配置的后端、各 MCP 客户端的归属计数、最后活动时间戳）。输出只到标准输出 — mneva 绝不会把它发到任何地方。当感觉哪里不对劲时，跑一下它，把结果粘进 bug 反馈里。

### 测试

测试用 **pytest**，配合 `pytest-asyncio` 和 `pytest-cov`。在装好开发依赖的源码检出里：

```sh
pytest
```

每个 PR 都会通过 [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) 跑完整矩阵（ubuntu / macos / windows × Python 3.11 / 3.12 / 3.13 / 3.14）。

---

## 路线图

mneva 处于 **alpha 阶段**。v0.2 交付了 MCP 层以及 uvx 优先的安装方式。里程碑：

- [X] **v0.1.0** — CLI + 存储 + BM25/sqlite-vec 索引 + 回放模板 + HTTP API + 四服务商 BYOK
- [X] **v0.1.x** — 漏洞修复、Obsidian 仓库读写集成、`mneva distill`、CI 矩阵前向防御
- [X] **v0.2** — MCP 服务器（`mneva-mcp` 命令 + 6 个 FastMCP 工具）、`uvx` 优先安装、跨进程安全的 WAL 并发、可选的 `mneva diagnose --share` 可观测性
- [ ] **v0.3** — 浏览器扩展（Chrome / Firefox / Edge，Manifest V3），让那些无法启动 MCP 子进程的网页聊天界面（chatgpt.com、claude.ai 网页版、gemini.google.com、DeepSeek）也能用上 mneva。启动条件：≥10 个真实用户 + ≥3 个通过 `mneva diagnose --share` 提出的明确请求。
- [ ] **v1+** — 面向非技术用户的原生图形化安装程序；可选的托管版 `mneva.app` SaaS，用于手机/多设备同步。

---

## 参与贡献

- **💬 [加入讨论](https://github.com/mneva-ai/mneva/discussions)**：分享见解、提供反馈或提问。
- **🐛 [报告问题](https://github.com/mneva-ai/mneva/issues)**：提交发现的 bug，或记录对 `mneva` 项目的功能需求。
- **💡 [提交 Pull Request](https://github.com/mneva-ai/mneva/blob/main/CONTRIBUTING.md)**：审阅开放的 PR，并提交你自己的 PR。

<details closed>
<summary>贡献指南</summary>

1. **Fork 仓库**：先把项目仓库 fork 到你自己的 GitHub 账号。
2. **克隆到本地**：用 git 客户端把 fork 后的仓库克隆到本地。
   ```sh
   git clone https://github.com/mneva-ai/mneva.git
   ```
3. **新建分支**：始终在新分支上工作，给它起一个有描述性的名字。
   ```sh
   git checkout -b new-feature-x
   ```
4. **做你的改动**：在本地开发并测试你的改动。
5. **提交改动**：用清晰的信息描述你的更新。
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **推送到 GitHub**：把改动推送到你 fork 的仓库。
   ```sh
   git push origin new-feature-x
   ```
7. **提交 Pull Request**：针对原项目仓库创建 PR，清楚说明改动内容及其动机。
8. **审阅**：你的 PR 通过审阅并被批准后，就会被合并进 main 分支。恭喜你的贡献！
</details>

<details closed>
<summary>贡献者图谱</summary>
<br>
<p align="left">
   <a href="https://github.com/mneva-ai/mneva/graphs/contributors">
      <img src="https://contrib.rocks/image?repo=mneva-ai/mneva">
   </a>
</p>
</details>

---

## 许可证

Mneva 基于 [Apache License 2.0](./LICENSE) 授权。

---

## 链接

- 官网：https://mneva.org
- 仓库：https://github.com/mneva-ai/mneva
- PyPI：https://pypi.org/project/mneva/
- 问题反馈：https://github.com/mneva-ai/mneva/issues
- 更新日志：[`CHANGELOG.md`](./CHANGELOG.md)

<div align="right">

[![][back-to-top]](#top)

</div>


[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-151515?style=flat-square


---
