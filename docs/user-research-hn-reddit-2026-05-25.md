# Mneva 用户需求调研汇总 - HN / Reddit

日期：2026-05-25  
范围：Hacker News 与 Reddit 公开讨论  
对象：mneva - local-first, MCP-native, cross-tool AI coding memory substrate

## 1. 执行摘要

mneva 当前定位与公开讨论中的高频痛点高度匹配：AI 编码用户在 Claude Code、Cursor、Codex、Windsurf、Gemini CLI、OpenCode 等工具之间切换时，最常丢失的是架构决策、调试过程、任务状态、偏好约束、业务规则和团队上下文。用户确实在寻找跨 session、跨工具、低 token 成本、可审计的记忆层。

但市场已经出现大量相邻项目：Linggen、Hmem、paradigm-memory、Memory Bank、Recall、Engram、Core、Locus、context0、agent-recall、TeamMind、SageOx 等。mneva 不应只讲“AI memory MCP”，而应收窄到更可防守的差异：

> Markdown-owned, Git-aware, reviewable memory for developers using multiple AI coding tools.

中文定位：

> 给多 AI 编码工具共用的本地记忆底座，数据仍然是你自己的 Markdown。

## 2. 最相关关键词

### 核心关键词

- `AI coding agent memory`
- `Claude Code memory`
- `Cursor context loss`
- `Claude Code Cursor context loss`
- `persistent memory MCP`
- `local-first memory MCP`
- `cross-tool AI memory`
- `agent context persistence`
- `MCP memory server`
- `AI agent memory stale context`
- `memory.md context bloat`
- `CLAUDE.md going stale`
- `AI coding assistant forgets decisions`
- `project scoped memory`
- `debugging context across sessions`
- `team shared AI memory`
- `repo branch commit memory`
- `context engineering agent amnesia`

### 推荐组合搜索

- `site:news.ycombinator.com "Claude Code" "memory" "context"`
- `site:news.ycombinator.com "MCP" "memory" "coding agents"`
- `site:reddit.com/r/ClaudeCode "context loss" "memory"`
- `site:reddit.com/r/cursor "Claude Code" "Cursor" "context loss"`
- `site:reddit.com/r/mcp "memory layer" "AI agents"`
- `site:reddit.com/r/ContextEngineering "agent amnesia"`

## 3. 用户画像

| 用户画像 | 核心痛点 | mneva 机会 |
|---|---|---|
| 重度 AI 编码者 | 每次新 session 重新解释架构、约定、历史决策 | 自动或半自动 capture，session start replay |
| 跨工具用户 | Claude Code、Cursor、Codex、Windsurf 之间记忆割裂 | 一份本地记忆，多工具读取 |
| 团队/多机器用户 | 个人记忆无法共享，团队上下文分裂 | git/文件夹同步、团队 scope、导出包 |
| Markdown/Obsidian 用户 | 喜欢透明文件，但手动维护会 stale | Markdown source of truth + 索引、审计、过期 |
| 隐私敏感开发者 | 不愿把代码/项目知识交给第三方记忆 SaaS | local-first、zero telemetry、可解释 retrieval boundary |
| 单工具短任务用户 | 不一定需要复杂记忆系统 | 可卖 searchable history、handoff、audit，而不是强推跨工具 |

## 4. 八个访谈问题的公开讨论证据

### 4.1 用户在几个 AI 编码工具之间切换？最常丢什么？

公开讨论中已经有强信号。常见组合包括 Claude Code + Cursor + Codex，也有人加 Gemini、Windsurf、OpenCode。丢失内容集中在：

- 架构决策
- 代码约定和个人偏好
- bug 调试历史
- 下一步任务、阻塞点、测试状态
- changed files、branch、commit SHA
- 业务规则和产品上下文

证据：

- Reddit 用户讨论从 Cursor 切到 Claude Code 时丢上下文，需要重新解释项目状态：<https://www.reddit.com/r/cursor/comments/1rp9emv/how_do_you_handle_context_loss_when_switching/>
- context0 讨论强调让 Claude Code、Cursor、Codex 共享 task state：<https://www.reddit.com/r/AI_Agents/comments/1rfe475/cli_that_lets_claude_code_cursor_and_codex_share/>
- agent-recall 讨论从“Claude Code forgets everything between sessions”切入：<https://www.reddit.com/r/ClaudeAI/comments/1rfwaxx/claude_code_forgets_everything_between_sessions_i/>
- HN Ensue 讨论以“Stop Claude Code from forgetting everything”为主题：<https://news.ycombinator.com/item?id=46426624>

产品含义：

- mneva 的 scope 不应只停留在 `project`。
- 应优先支持 `repo + branch + commit/status + task state`。
- 记忆类型应显式覆盖 `architecture`、`decision`、`debugging_lesson`、`blocker`、`preference`、`business_rule`。

### 4.2 用户愿意让 agent 自动写记忆吗？哪些类型必须人工确认？

讨论呈现分裂：

- 一派希望自动 capture/hooks，避免用户在 session 结束前忘记 handoff。
- 另一派担心 agent 写入长期事实会污染记忆，要求 review layer、approve/promote、可回滚。

适合自动写入的内容：

- transient session summary
- debug trail
- current blocker
- changed files
- test status
- next action

必须人工确认的内容：

- permanent architecture decision
- business rule
- security/compliance constraint
- team shared memory
- expensive/irreversible migration conclusion
- 用户偏好和身份相关内容

证据：

- Recall HN 讨论 passive capture 与 session history：<https://news.ycombinator.com/item?id=47189906>
- Locus 讨论 Claude Code memory：<https://www.reddit.com/r/ClaudeCode/comments/1rmi2e6/memory_for_claude_code/>
- agent-recall 作者/评论强调 review layer：<https://www.reddit.com/r/ClaudeAI/comments/1rfwaxx/claude_code_forgets_everything_between_sessions_i/>
- Claude Code auto-memory 讨论用户关心 opt-out/control：<https://www.reddit.com/r/ClaudeAI/comments/1rfkmj1/new_automemory_feature_in_claude_code_details/>

产品含义：

- 最佳默认不是全自动写 permanent。
- 建议新增 `draft -> review -> promote` 流程。
- MCP agent 写入默认进 draft/transient；用户确认后才进入 permanent。

### 4.3 用户更信任 Markdown 文件、SQLite 数据库，还是带 GUI 的本地 app？

用户偏好明显分层：

- 高级用户信 Markdown：可读、可 diff、可 grep、可手改、可 git 管理。
- SQLite 被接受为轻量本地索引或状态库，但不应成为唯一事实源。
- GUI 的需求主要是 inspect/review/audit/token visibility，而不是替代文件。

证据：

- HN 讨论 `.md` vs database，许多用户强调纯文本和可维护性：<https://news.ycombinator.com/item?id=45517078>
- mnemo 把 Markdown 作为 source of truth，SQLite/LanceDB 作为索引：<https://www.reddit.com/r/ClaudeAI/comments/1t6r3k2/mnemo_a_local_semantic_memory_for_claude_code/>
- Reddit 评论强调 plain files 方便修错和审计：<https://www.reddit.com/r/ClaudeCode/comments/1s34ckp/i_connected_claude_code_to_12_systems_heres_what/>
- ELVES GUI 讨论表明 GUI 对管理体验有吸引力：<https://www.reddit.com/r/ClaudeAI/comments/1rpzdr4/gui_for_claude_code_skills_mcp_worktrees_and/>

产品含义：

- mneva 当前“Markdown + SQLite index”方向正确。
- 应明确产品文案：Markdown 是事实源，SQLite 是可重建索引。
- GUI 可后置；短期更应做 `mneva review`、`mneva audit`、`mneva stale`、`mneva status`。

### 4.4 如果记忆和代码现状冲突，用户希望系统怎么处理？

用户担心 stale lore。常见期望：

- 先信当前代码，而不是旧记忆。
- 用 repo/branch/commit SHA 约束记忆适用范围。
- 提醒冲突，而不是自动合并。
- 保留历史，但标记 superseded。
- 支持 expire、decay、last_verified_at。

证据：

- WorkFullCircle 明确提到 repo/branch/commit SHA、forget/expire，避免 stale lore：<https://www.reddit.com/r/mcp/comments/1rflpbe/built_an_mcp_memory_layer_to_persist_ai_debugging/>
- Core 讨论旧 REST 事实被 GraphQL 取代时应 supersede：<https://www.reddit.com/r/mcp/comments/1shnxs3/your_claude_codex_cursor_doesnt_need_a_better/>
- agent-recall 讨论 bitemporal slots/staleness：<https://www.reddit.com/r/ClaudeAI/comments/1rfwaxx/claude_code_forgets_everything_between_sessions_i/>
- nan-forget 使用 decay/half-life 思路：<https://www.reddit.com/r/ClaudeAI/comments/1s8ed6o/claude_code_memory_that_fits_in_a_single_sqlite/>

产品含义：

- 新增元数据：`source_commit`、`source_branch`、`last_verified_at`、`stale_after`、`supersedes`、`confidence`。
- 检索结果应提示“历史事实，需读当前文件确认”。
- 冲突策略：提示 + 保留历史 + 手动 supersede；不要默认自动合并。

### 4.5 用户能接受每次 session 开始消耗多少 token？

用户对 token 成本敏感。公开讨论没有统一阈值，但有明显区间：

- 几百 token 的 brief/index 被认为好。
- 约 800 token/query 被当成优势。
- 小于 3K 的 session context 通常可接受。
- 3K-8K 是用户原本手动 re-context 的典型成本。
- 30K/15% 或 80K/40% startup overhead 被认为严重。

证据：

- Engram 用约 800 token 对比 5K token memory dump：<https://www.reddit.com/r/ClaudeAI/comments/1rgoyao/i_built_an_opensource_memory_layer_for_claude/>
- 用户分享把 context window 控制在 3K tokens 以下：<https://www.reddit.com/r/ClaudeAI/comments/1tcl813/how_i_keep_my_ais_context_window_under_3k_tokens/>
- LoreConvo 讨论节省 3K-8K token re-context：<https://www.reddit.com/r/ClaudeAI/comments/1sa643r/i_built_a_persistent_memory_system_for_claude/>
- Claude Code setup audit 指出 30K tokens / 15% overhead：<https://www.reddit.com/r/ClaudeAI/comments/1sm66h8/psa_audited_my_claude_code_setup_30000_tokens_15/>
- Claude Code context window 讨论提到极高启动开销：<https://www.reddit.com/r/ClaudeAI/comments/1q7h2pj/understanding_claude_codes_context_window/>

产品含义：

- 新增 `replay --budget 500|1000|3000|full`。
- 默认不要全量注入。
- MCP tool descriptions 也要控制长度，避免 schema 自身吃上下文。

### 4.6 “跨工具”是否真有价值，还是用户主要只用一个工具？

答案分裂：

- 有真实跨工具需求：Claude 写、Codex review、Cursor debugging、Claude.ai mobile thinking。
- 也有用户认为不该频繁切工具，应保持 context 接近 0、每个 bug 新 chat，或只用一个主工具。

证据：

- context0 讨论 Claude Code、Cursor、Codex 共享 context：<https://www.reddit.com/r/AI_Agents/comments/1rfe475/cli_that_lets_claude_code_cursor_and_codex_share/>
- 用户问 Claude、Gemini、Codex 等通用 context：<https://www.reddit.com/r/ClaudeCode/comments/1rg2odm/common_context_across_claude_gemini_codex_etc/>
- Claude AI 与 Claude Code 共享 context 需求：<https://www.reddit.com/r/ClaudeAI/comments/1sd9cpj/claude_ai_and_claude_code_sharing_context/>
- r/cursor 对切工具必要性有质疑：<https://www.reddit.com/r/cursor/comments/1rp9emv/how_do_you_handle_context_loss_when_switching/>

产品含义：

- mneva 的 ICP 应明确为 `2+ AI tools / 2+ machines / long-lived projects`。
- 对单工具短任务用户，不要硬卖跨工具；卖 searchable history、handoff、reviewable memory。

### 4.7 团队共享记忆是否有需求？哪些内容不能共享？

需求存在，但安全/合规门槛高。团队想共享：

- bug gotchas
- deployment notes
- architecture decisions
- project conventions
- team-level onboarding knowledge
- agent/discussion handoff

不能共享或必须严格控制：

- secrets、`.env`、API keys、凭据
- 私有业务信息
- 用户 persona 和个人偏好
- 客户数据
- 安全/合规敏感内容
- 未确认的 agent 推断

证据：

- TeamMind 讨论 shared memory layer for Claude Code teams：<https://www.reddit.com/r/ClaudeAI/comments/1s7pig6/built_a_shared_memory_layer_for_claude_code_teams/>
- SageOx HN 讨论 shared memory / multi-agent：<https://news.ycombinator.com/item?id=47075973>
- multi-agent workspace shared memory：<https://www.reddit.com/r/AI_Agents/comments/1sihpbj/we_gave_our_multiagent_workspaces_a_shared_memory/>
- SOC review 帖显示企业会问 audit logging、encryption-at-rest、SIEM：<https://www.reddit.com/r/ClaudeAI/comments/1rspjb8/my_opensource_mcp_memory_server_got_formally/>
- `.env` 安全讨论表明 agent 访问敏感文件是明确担忧：<https://www.reddit.com/r/ClaudeAI/comments/1lgudw2/security_claude_code_reads_env_files_by_default/>

产品含义：

- 不要过早做团队 SaaS。
- 先做本地 team scope + allowlist + redaction + audit log。
- visibility 分层：`personal`、`project`、`team`。

### 4.8 什么证据会让用户相信 memory layer 值得安装？

用户需要证据，而不是“又一个 memory MCP”。有效证据类型：

- 可复现 benchmark
- token savings 数字
- re-context 时间节省
- 真实项目 before/after
- 可运行 demo
- 与普通 Markdown / full dump 的对比
- 检索命中率和错误率

证据：

- HN Ensue 讨论中有人质疑是否有 benchmark/test 证明改善：<https://news.ycombinator.com/item?id=46426624>
- Engram 使用 LOCOMO 等指标对比：<https://www.reddit.com/r/ClaudeAI/comments/1rgoyao/i_built_an_opensource_memory_layer_for_claude/>
- Semble 以 token reduction 和 benchmark 做卖点：<https://www.reddit.com/r/ClaudeAI/comments/1szvo7t/open_source_we_built_a_local_code_search_mcp_for/>
- Genesys-memory 给出 LOCOMO 脚本和长周期投入：<https://www.reddit.com/r/ClaudeAI/comments/1sp22el/spent_3_months_building_an_mcp_memory_server_for/>
- Project Memory 强调 save tokens：<https://www.reddit.com/r/ClaudeCode/comments/1shp98n/save_tokens_save_more_with_your_claude_code/>

产品含义：

- mneva 需要 3 类证据资产：
  - benchmark：retrieval relevance、token budget、session recovery。
  - dogfood case：Claude Code -> Cursor/Codex 切换，同一 repo 恢复上下文。
  - 5 分钟 demo：安装、capture、replay、跨工具读取、Markdown 文件可见。

## 5. 需求矩阵

| 优先级 | 需求/痛点 | 当前 mneva 覆盖 | 主要缺口 | 建议动作 |
|---|---|---|---|---|
| P0 | 跨 session 不再从零开始 | capture/search/replay/MCP | 默认流程不够明确 | agent workflow snippets + session start replay |
| P0 | 跨工具共享记忆 | MCP 多客户端 | 文案差异化不足 | 强化“不是单工具插件” |
| P0 | 避免 MEMORY.md / CLAUDE.md 上下文膨胀 | BM25 + scope/lifespan | token budget replay | `replay --budget` |
| P0 | stale memory / contradiction control | forget + lifespan | git 元数据、过期、supersede | Git-aware metadata + stale review |
| P1 | 自动 capture 但不污染长期事实 | MCP capture 可被 agent 调用 | review queue | draft/review/promote |
| P1 | 可审计和可管理 | Markdown 文件透明 | audit/review CLI | `mneva audit`, `mneva review` |
| P1 | 证明有效 | 工程测试多 | 产品效果证据少 | benchmark + dogfood demo |
| P2 | 浏览器聊天 UI 支持 | 路线图已有 | 需求需继续验证 | 等真实 pull signal |
| P2 | 团队共享 | local-first 单机强 | visibility/redaction/audit | local team scope first |

## 6. 竞品与相邻项目信号

| 项目/方向 | 公开定位信号 | 对 mneva 的启发或威胁 |
|---|---|---|
| Linggen | local-first, MCP, Cursor/Zed/Claude, Team Memory, visual map | mneva 需解释 local-first 与云模型边界 |
| Hmem | SQLite `.hmem`, hierarchical memory, 避免 MEMORY.md 全量注入 | mneva 可学习 L1/L2/L3 分层 replay |
| paradigm-memory | SQLite, MCP-native, multi-agent, audit log, review queue, desktop inspectable | 直接威胁，mneva 应补 review/audit |
| Memory Bank / memori / Recall / Engram / Locus / agent-recall / Core | 大量项目围绕 Claude memory MCP、decay、benchmarks、review | 市场拥挤，必须差异化 |
| 纯 Markdown / handoff workflows | 高级用户仍偏好 git-versioned Markdown 和明确 handoff | mneva 应拥抱 Markdown，不要替代它 |
| TeamMind / SageOx | 团队共享记忆、多 agent workspace | 团队需求存在，但安全和权限必须先设计 |

## 7. 产品机会排序

### P0 - 近期最该做

1. Git-aware scope
   - 自动记录 repo path、branch、commit SHA、dirty state、changed files。
   - 搜索和 replay 默认按当前 repo/branch 过滤。

2. Review queue
   - agent 写入默认为 draft/transient。
   - 用户 approve 后 promote 到 permanent。
   - 支持 reject/edit/promote。

3. Token-budgeted replay
   - `--budget 500|1000|3000|full`。
   - 默认不全量注入。
   - 输出按 relevance + freshness + lifespan 排序。

4. Stale / supersede
   - `last_verified_at`、`stale_after`、`supersedes`。
   - 冲突时提示而不是自动合并。

### P1 - 巩固差异化

5. Memory hygiene CLI
   - `mneva stale`
   - `mneva audit`
   - `mneva review`
   - `mneva promote`

6. Agent workflow snippets
   - Claude Code / Cursor / Codex rules：
     - session start search/replay
     - decision capture
     - debug lesson capture
     - session end handoff

7. Evidence assets
   - dogfood demo
   - benchmark script
   - token savings comparison
   - real project case study

### P2 - 后续验证

8. Browser extension
   - 用真实用户请求触发，不要现在抢跑。

9. Team sharing
   - 先做 local/git/Obsidian sync + visibility + redaction。
   - 不急于 SaaS。

## 8. 建议路线图

### v0.3 候选方向

- Git-aware metadata
- token-budgeted replay
- draft/review/promote
- stale/supersede basics
- improved Claude Code / Cursor / Codex workflow templates

### v0.4 候选方向

- audit/review CLI
- Obsidian-friendly review views
- benchmark/demo package
- session transcript distill defaults
- browser extension validation prototype

### v1+ 候选方向

- GUI memory inspector
- team/shared scope
- redaction policies
- optional sync / hosted service

## 9. 建议产品文案

### 英文

> Local-first, Markdown-owned memory substrate for developers using multiple AI coding tools.

### 中文

> 给多 AI 编码工具共用的本地记忆底座，数据仍然是你自己的 Markdown。

### 差异化要点

- Markdown is the source of truth.
- SQLite is a rebuildable local index.
- Git-aware memories avoid stale lore.
- Agents can suggest memories, but users approve permanent truth.
- Replay is token-budgeted, not a context dump.
- Built for developers who use more than one AI coding tool.

## 10. 参考来源

### Hacker News

- Linggen local-first memory layer: <https://news.ycombinator.com/item?id=46328769>
- Hmem persistent hierarchical memory: <https://news.ycombinator.com/item?id=47103237>
- Stop Claude Code from forgetting everything: <https://news.ycombinator.com/item?id=46426624>
- Ask HN continuous context: <https://news.ycombinator.com/item?id=46626639>
- Recall / passive memory: <https://news.ycombinator.com/item?id=47189906>
- `.md` vs database discussion: <https://news.ycombinator.com/item?id=45517078>
- SageOx / shared memory: <https://news.ycombinator.com/item?id=47075973>

### Reddit

- Context loss when switching tools: <https://www.reddit.com/r/cursor/comments/1rp9emv/how_do_you_handle_context_loss_when_switching/>
- Claude Code / Cursor / Codex shared context: <https://www.reddit.com/r/AI_Agents/comments/1rfe475/cli_that_lets_claude_code_cursor_and_codex_share/>
- Claude Code forgets between sessions: <https://www.reddit.com/r/ClaudeAI/comments/1rfwaxx/claude_code_forgets_everything_between_sessions_i/>
- Memory for Claude Code / Locus: <https://www.reddit.com/r/ClaudeCode/comments/1rmi2e6/memory_for_claude_code/>
- Claude Code auto-memory: <https://www.reddit.com/r/ClaudeAI/comments/1rfkmj1/new_automemory_feature_in_claude_code_details/>
- mnemo local semantic memory: <https://www.reddit.com/r/ClaudeAI/comments/1t6r3k2/mnemo_a_local_semantic_memory_for_claude_code/>
- WorkFullCircle debugging memory: <https://www.reddit.com/r/mcp/comments/1rflpbe/built_an_mcp_memory_layer_to_persist_ai_debugging/>
- Core memory contradiction/supersede: <https://www.reddit.com/r/mcp/comments/1shnxs3/your_claude_codex_cursor_doesnt_need_a_better/>
- nan-forget decay memory: <https://www.reddit.com/r/ClaudeAI/comments/1s8ed6o/claude_code_memory_that_fits_in_a_single_sqlite/>
- Engram benchmark/token discussion: <https://www.reddit.com/r/ClaudeAI/comments/1rgoyao/i_built_an_opensource_memory_layer_for_claude/>
- Keep context under 3K tokens: <https://www.reddit.com/r/ClaudeAI/comments/1tcl813/how_i_keep_my_ais_context_window_under_3k_tokens/>
- LoreConvo token savings: <https://www.reddit.com/r/ClaudeAI/comments/1sa643r/i_built_a_persistent_memory_system_for_claude/>
- Claude Code setup 30K token overhead: <https://www.reddit.com/r/ClaudeAI/comments/1sm66h8/psa_audited_my_claude_code_setup_30000_tokens_15/>
- Common context across Claude/Gemini/Codex: <https://www.reddit.com/r/ClaudeCode/comments/1rg2odm/common_context_across_claude_gemini_codex_etc/>
- Claude AI and Claude Code sharing context: <https://www.reddit.com/r/ClaudeAI/comments/1sd9cpj/claude_ai_and_claude_code_sharing_context/>
- TeamMind shared memory: <https://www.reddit.com/r/ClaudeAI/comments/1s7pig6/built_a_shared_memory_layer_for_claude_code_teams/>
- Multi-agent workspace shared memory: <https://www.reddit.com/r/AI_Agents/comments/1sihpbj/we_gave_our_multiagent_workspaces_a_shared_memory/>
- SOC review for MCP memory server: <https://www.reddit.com/r/ClaudeAI/comments/1rspjb8/my_opensource_mcp_memory_server_got_formally/>
- `.env` security concern: <https://www.reddit.com/r/ClaudeAI/comments/1lgudw2/security_claude_code_reads_env_files_by_default/>
- Semble benchmark/token reduction: <https://www.reddit.com/r/ClaudeAI/comments/1szvo7t/open_source_we_built_a_local_code_search_mcp_for/>
- Genesys LOCOMO benchmark: <https://www.reddit.com/r/ClaudeAI/comments/1sp22el/spent_3_months_building_an_mcp_memory_server_for/>
- Project Memory token savings: <https://www.reddit.com/r/ClaudeCode/comments/1shp98n/save_tokens_save_more_with_your_claude_code/>
