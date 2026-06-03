# Phase 5 测试文档

## 测试目标

1. 理解三大原语如何在同一 Server 中协同工作
2. 验证 Tool 写 → Resource 读 → Prompt 引导的完整链路
3. 体验 Smart Notes 的完整工作流

---

## 启动 Server

```bash
uv run mcp dev src/smart_notes/server.py
```

打开 Inspector 后,浏览器中可以看到 Tools / Resources / Prompts 三个标签都有内容。

---

## 测试 1: 系统概览

### 1.1 查看功能列表

在 **Tools** 标签 → 调用 `help`（无需参数）。

**预期**: 返回完整的 Tools / Resources / Prompts 列表,以及设计原则说明。

### 1.2 确认注册数量

- **Tools**: create_note, update_note, delete_note, search_notes, list_notes, help（共 6 个）
- **Resources**: note://{note_id}, note://{note_id}/raw, notes://all, notes://tag/{tag_name}, stats://summary（共 5 个,2 静态 + 3 动态）
- **Prompts**: review_note, new_note_wizard, summarize_notes（共 3 个）

---

## 测试 2: Tool → Resource 链路（写后读）

这是 MCP 的核心设计模式：**Tool 写状态,Resource 读状态。**

### 2.1 创建笔记

**Tools** → `create_note`:
- title: "测试笔记"
- content: "这是通过 MCP 创建的测试笔记。\n\n## 测试目的\n验证 Tool 写入能力。"
- tags: ["test", "study"]

**预期**: 返回 `{"action": "created", "note": {...}}`,note.id 为 `ce-shi-bi-ji`（中文转 slug）。

### 2.2 立即通过 Resource 读取

**Resources** → 找到 `note://{note_id}` → 填入刚才的 ID → **Read**。

**预期**: Markdown 格式的笔记内容,底部有元信息（ID、标签、时间戳）。

### 2.3 对比不同视图

同一篇笔记,读取不同 URI：

| URI | 格式 | 用途 |
|-----|------|------|
| `note://{id}` | Markdown | 展示给用户 |
| `note://{id}/raw` | JSON | 程序化处理 |

**预期**: 同一数据,两种格式。LLM 可根据需要选择。

### 2.4 更新笔记

**Tools** → `update_note`:
```json
{
  "note_id": "ce-shi-bi-ji",
  "content": "# 更新后的内容\n\n笔记已通过 update_note 修改。",
  "tags": ["test", "study", "updated"]
}
```

**预期**: updated_at 时间戳更新。

### 2.5 验证更新

**Resources** → 再次读取 `note://ce-shi-bi-ji` → 确认内容和标签已变更。

### 2.6 删除笔记

**Tools** → `delete_note`:
- note_id: "ce-shi-bi-ji"

**预期**: `{"action": "deleted", ...}`

### 2.7 验证删除

- **Resources** → 读取 `note://ce-shi-bi-ji` → 返回 404
- **Tools** → `list_notes` → 确认回到 4 篇种子笔记

---

## 测试 3: 搜索和索引

### 3.1 全文搜索

**Tools** → `search_notes`:
```json
{
  "query": "Python",
  "max_results": 10,
  "case_sensitive": false
}
```

**预期**: 返回 "Python 异步编程要点" 笔记。

### 3.2 大小写敏感搜索

`case_sensitive: true`, `query: "python"`（小写）。

**预期**: 大小写不匹配时返回 0 结果。`query: "Python"` 则返回 1 结果。

### 3.3 分类过滤

`query: "Python"`, `category: "study"`。

**预期**: 只返回 study 分类的 Python 相关笔记。

### 3.4 索引资源

**Resources** → 读取 `notes://all`。

**预期**: Markdown 列表,按更新时间排序,每行包含标题和可点击的 `note://` 链接。

### 3.5 按标签过滤资源

**Resources** → 读取 `notes://tag/study` → 只显示 study 标签的笔记。

**Resources** → 读取 `notes://tag/nonexistent` → 提示没有匹配笔记。

---

## 测试 4: 统计资源

**Resources** → 读取 `stats://summary`（JSON 格式）。

**预期**: 返回统计数据:
- total_notes: 笔记总数
- total_words: 总字数
- tags: 每个标签的出现次数
- top_tags: 最常用标签
- storage_file: 持久化文件路径

---

## 测试 5: Prompt 协同

### 5.1 审阅笔记 Prompt

**Prompts** → `review_note`:
- note_id: "python-async"

**预期**: 返回 2 条消息:
- 第 1 条: TextContent — 审阅标准（4 个维度）
- 第 2 条: **ResourceLink** — uri 指向 `note://python-async`

**关键理解**: Prompt 自己不做审阅,它生成引导对话,LLM 会先读 Resource 再回复。

### 5.2 创建笔记向导 Prompt

**Prompts** → `new_note_wizard`:
- topic: "MCP 学习心得"
- category: "study"

**预期**: 系统指令包含主题和分类信息,引导流程分 4 步。

### 5.3 总结笔记 Prompt

**Prompts** → `summarize_notes`:
- tag: "study"（或留空总结全部）

**预期**: 系统指令指示 LLM 先读 Resources 获取数据,再给出总结。

---

## 测试 6: 完整工作流演练（不同启动方式）

这一部分验证的是 **Prompt 引导 + Resource 读取 + Tool 写入** 如何被真实客户端组合使用。

注意: Inspector 只能分别调用 Tools / Resources / Prompts,不能自动扮演 LLM 做多步骤决策。因此测试 6 分为三种方式:

| 启动方式 | 适合验证 | 是否能模拟 LLM 自动编排 |
|----------|----------|-------------------------|
| `uv run mcp dev src/smart_notes/server.py` | Inspector 中手动调用三大原语 | 否,只能手动模拟 |
| `uv run python src/smart_notes/server.py` | Claude Desktop / Cursor 等 stdio MCP Client | 是,由客户端 LLM 决策 |
| `uv run python src/smart_notes/server.py streamable-http` | HTTP MCP endpoint 是否可连接 | 取决于连接它的客户端 |

### 6.1 Inspector 手动模拟

启动:

```bash
uv run mcp dev src/smart_notes/server.py
```

在 Inspector 中按下面顺序手动执行,模拟真实 AI 辅助笔记场景:

```
用户: "帮我审阅 Python 异步编程的笔记"
  → Prompts 调用 review_note(note_id="python-async")
  → Resources 读取 note://python-async
  → 根据 Prompt 返回的审阅标准,手动检查 LLM 应如何给反馈

用户: "把这段内容创建为一篇新笔记"
  → Prompts 调用 new_note_wizard(topic="MCP 学习心得", category="study")
  → Tools 调用 create_note 写入笔记
  → Resources 读取 note://{new_id} 确认写入成功

用户: "这周我学了哪些东西？总结一下"
  → Resources 读取 notes://all 索引获取全貌
  → Prompts 调用 summarize_notes(tag="study")
  → 根据 Prompt 返回的总结模板,手动检查应输出的结构化总结
```

**预期**:
- Inspector 中能分别完成 Prompt / Resource / Tool 调用
- 能看到 `review_note` 返回的 `ResourceLink` 指向 `note://python-async`
- `create_note` 写入后,能通过 `note://{new_id}` 立即读到新笔记
- 理解 Inspector 的限制: 它验证原语是否可用,不验证 LLM 是否会自动选择这些原语

### 6.2 stdio Client 真实编排

启动:

```bash
uv run python src/smart_notes/server.py
```

这种方式适合接入支持 MCP stdio 的真实 AI 客户端,例如 Claude Desktop、Cursor 或其他 MCP Client。

在客户端中配置该命令后,用自然语言测试:

```
帮我审阅 Python 异步编程的笔记
```

**预期**:
- 客户端 LLM 能发现 `review_note` Prompt
- LLM 能根据 Prompt 中的 `ResourceLink` 读取 `note://python-async`
- LLM 最终给出包含总体评价、具体问题、改进建议的审阅反馈

继续测试:

```
把这段内容创建为一篇新笔记:
今天学习了 MCP 的三大原语: Tools 负责动作,Resources 负责数据读取,Prompts 负责对话模板。
```

**预期**:
- LLM 可以先用 `new_note_wizard` 引导补充标题、标签等信息
- 信息确认后调用 `create_note`
- 写入后读取 `note://{new_id}` 或 `notes://all` 确认结果

最后测试:

```
这周我学了哪些东西？总结一下
```

**预期**:
- LLM 读取 `notes://all` 或相关标签资源
- LLM 使用 `summarize_notes` 的结构要求
- 输出按主题、关键收获、后续建议组织的总结

### 6.3 streamable-http 启动检查

启动:

```bash
uv run python src/smart_notes/server.py streamable-http
```

HTTP endpoint:

```text
http://localhost:8000/mcp
```

如果要从其他机器访问,需要把 Server 的 host 配置为 `0.0.0.0`,并使用服务器 IP:

```text
http://<server-ip>:8000/mcp
```

**预期**:
- HTTP MCP 客户端可以连接 `/mcp`
- 连接成功后应能看到同样的 Tools / Resources / Prompts
- 自动编排能力仍取决于客户端是否带 LLM,不是 HTTP 启动方式本身决定的

---

## 测试 7: 数据持久化

### 7.1 检查存储文件

```bash
uv run python -m json.tool --no-ensure-ascii ~/.smart_notes.json
```

**预期**: 包含当前所有笔记的 JSON 数组,中文内容正常显示,不会变成 `\uXXXX` 编码。

### 7.2 重启后数据保留

1. 创建一篇新笔记
2. Ctrl+C 停止 Inspector
3. 重新启动 `uv run mcp dev src/smart_notes/server.py`
4. 读取刚才创建的笔记 → 确认数据还在

---

## Phase 5 完成检查清单

- [ ] 在 Inspector 中看到 6 个 Tools / 5 个 Resources / 3 个 Prompts
- [ ] 完成了 create_note → Resource 读 → update_note → delete_note 完整链路
- [ ] 理解了同一笔记的 Markdown / JSON 两种视图
- [ ] 使用 search_notes 测试了全文搜索和分类过滤
- [ ] 读取了 notes://all 索引和 notes://tag/{tag} 过滤资源
- [ ] 读取了 stats://summary 统计资源
- [ ] 在 review_note Prompt 中看到了 ResourceLink 引用
- [ ] 理解了 "Tool 写 → Resource 读 → Prompt 引导" 的协作模式
- [ ] 验证了数据持久化（重启后笔记不丢失）

---

## 学到的关键概念

| 概念 | 一句话总结 |
|------|-----------|
| 三原语协同 | Tool 写 / Resource 读 / Prompt 引导,各司其职不越界 |
| 写后读 | create_note (Tool) + note://{id} (Resource) = 完整链路 |
| 索引模式 | notes://all (全览) → note://{id} (详情),先粗后细 |
| 多视图 | 同一数据 Markdown/JSON 适应不同消费场景 |
| ResourceLink | Prompt 引用 Resource URI,客户端按需获取,解耦 |
| 数据持久化 | JSON 文件存储,跨重启保留 |
