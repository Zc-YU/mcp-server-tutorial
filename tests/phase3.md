# Phase 3 测试文档

## 测试目标

1. 理解 Resource 是什么：只读数据、URI 寻址
2. 区分静态资源（固定 URI）和动态资源（URI 模板）
3. 理解同一数据的不同视图（Markdown / JSON / Summary）
4. 理解 "索引 → 详情" 的资源组织模式

---

## 测试 1: 静态资源

```bash
uv run mcp dev steps/step05_resources_static.py
```

### 1.1 查看所有资源

打开 Inspector → 点击左侧 **Resources** 标签页。

**预期**: 看到 5 个资源 URI：
- `config://app`
- `info://status`
- `stats://summary`
- `help://quickstart`
- `state://counter`

### 1.2 阅读资源内容

逐个点击每个资源 → 点 **Read** 按钮：

| 资源 | 类型 | 内容 |
|------|------|------|
| `config://app` | 文本 | 应用配置信息 |
| `info://status` | 文本 | 服务器状态 |
| `stats://summary` | JSON | 笔记统计数据 |
| `help://quickstart` | Markdown | 快速入门指南 |
| `state://counter` | JSON | 当前计数器值 |

### 1.3 验证 Tool + Resource 协作

1. 先读 `state://counter` → 看到 `{"counter": 0}`
2. 切到 **Tools** → 调用 `increment_counter` (by=5) → 返回 `{"counter": 5}`
3. 再读 `state://counter` → 看到 `{"counter": 5}`

**关键理解**: Tool 写、Resource 读，各司其职。这就是 MCP 的核心设计哲学。

---

## 测试 2: 动态资源模板

```bash
uv run mcp dev steps/step06_resources_dynamic.py
```

### 2.1 查看资源列表模板

打开 Inspector → **Resources** 标签页。

**预期**: 看到动态资源模板（带 `{param}` 占位符）：
- `note://{note_id}`
- `note://{note_id}/raw`
- `note://{note_id}/summary`
- `notes://tag/{tag_name}`
- `notes://all`

注意 `notes://all` 没有 `{param}`，它是静态的。

### 2.2 读取具体资源

先调用 `list_resource_uris` 工具（在 Tools 标签），拿到所有 note_id。

**读 `notes://all`**（索引）:
- 预期: Markdown 列表，显示所有 4 篇笔记，按更新时间排序

**读 `note://shopping`**（详情）:
- 预期: Markdown 格式的完整笔记内容

**读 `note://shopping/raw`**（原始 JSON）:
- 预期: JSON 格式的笔记数据，包含所有字段

**读 `note://shopping/summary`**（摘要）:
- 预期: 一句话摘要 "周末购物清单: 牛奶、鸡蛋..."

**读 `notes://tag/study`**（按标签过滤）:
- 预期: Markdown 列表，只显示 study 标签的笔记

**读 `note://nonexistent`**（不存在的 ID）:
- 预期: 404 信息，而非崩溃

### 2.3 对比不同视图

同一个 `note_id="python-intro"`，读三个不同的 URI：

| URI | 返回格式 | 用途 |
|-----|---------|------|
| `note://python-intro` | Markdown | LLM 向用户展示 |
| `note://python-intro/raw` | JSON | LLM 解析结构化数据 |
| `note://python-intro/summary` | 短文本 | LLM 快速了解内容 |

**关键理解**: 同一个数据，不同格式对应不同使用场景。LLM 会根据需要选择合适的 URI。

---

## Phase 3 完成检查清单

- [x] 理解了 Resource 是只读数据（读），Tool 是操作（写）
- [x] 在 Inspector 中成功读取了静态资源
- [x] 观察到了 `increment_counter` (Tool) + `state://counter` (Resource) 的协作
- [ ] 在 Inspector 中成功读取了动态资源的不同 note_id
- [x] 理解了 URI 模板中 `{param}` 如何绑定函数参数
- [ ] 对比了同一笔记的 Markdown / JSON / Summary 三种视图
- [ ] 理解了 "先读索引（notes://all），再读详情（note://xxx）" 的资源组织模式

---

## 学到的关键概念

| 概念 | 一句话总结 |
|------|-----------|
| Resource | MCP Server 暴露的只读数据，通过 URI 寻址 |
| @mcp.resource(uri) | 注册一个资源，URI 即地址 |
| 静态 vs 动态 | 固定 URI = 固定内容；URI 模板 = 参数化内容 |
| {param} 绑定 | URI 中的 `{xxx}` 自动绑定到同名函数参数 |
| 多视图 | 同一数据提供不同格式（Markdown/JSON/Summary） |
| 索引资源 | `notes://all` 先列出概览，`note://{id}` 再读详情 |
| Tool+Resource | Tool 写数据，Resource 读数据，各司其职 |
