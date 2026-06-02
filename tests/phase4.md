# Phase 4 测试文档

## 测试目标

1. 理解 Prompt 是什么：服务端提供的对话模板，引导 AI 思考
2. 区分单消息 Prompt 和多消息 Prompt（system + user）
3. 理解 Prompt 如何引用 Resource（ResourceLink）
4. 理解 Prompts vs Tools vs Resources 的核心区别

---

## 测试 1: 查看 Prompts 列表

```bash
uv run mcp dev steps/step07_prompts.py
```

### 1.1 确认 Prompts 可见

打开 Inspector → 点击左侧 **Prompts** 标签页。

**预期**: 看到 5 个 Prompt 模板：
- `greet_user` — 问候用户
- `review_writing` — 写作审阅
- `translate_content` — 内容翻译
- `analyze_note` — 分析笔记
- `new_note_wizard` — 创建笔记向导

**关键理解**: 这些 Prompt 不是 Tools。LLM 看到的是"这个 Server 可以帮我生成以下类型的对话模板"。

---

## 测试 2: 最简单的 Prompt — `greet_user`

### 2.1 查看 Prompt 详情

在 Inspector 中点击 **greet_user** → 点 **Get Prompt**。

参数: `name = "测试员"`

**预期**: 返回一条消息列表，包含一条 user 角色的消息，内容是：
```
请用友好的语气向 测试员 打招呼，并介绍 MCP 的三大原语（Tools、Resources、Prompts）各一句话。
```

### 2.2 理解返回结构

观察 Inspector 的返回面板，注意：
- 返回的是 **消息列表**（`list[PromptMessage]`），不是执行结果
- 每条消息有 `role`（user/assistant）和 `content`（TextContent）
- **Prompt 本身不执行任何操作**，它只是生成了一个对话模板

---

## 测试 3: 多消息 Prompt — `review_writing`

### 3.1 基本用法

参数:
- `text = "今天天气很好，我去了公园，看到了很多花，心情非常好。我觉得春天是最美的季节。"`
- `focus = "风格"`

**预期**: 返回 2 条消息：
1. **第 1 条 (role=user)**: 系统指令——设定了编辑角色、审阅标准、输出格式
2. **第 2 条 (role=user)**: 用户输入——包含待审阅的文字

### 3.2 测试不同的 focus 参数

| focus | 预期行为 |
|-------|---------|
| `语法` | 系统指令强调语法检查 |
| `逻辑` | 系统指令强调逻辑结构 |
| `风格` | 系统指令强调用词和表达 |
| `整体质量` | 综合所有维度 |

**关键理解**: 同一个 Prompt 模板，通过参数控制不同的行为方向。这是 Prompt 的核心价值——**参数化对话模板**。

---

## 测试 4: 翻译 Prompt — `translate_content`

参数:
- `text = "人工智能正在改变我们与技术交互的方式。从语音助手到自动驾驶，AI 的应用日益广泛。"`
- `target_language = "英文"`
- `style = "正式严谨"`

**预期**: 返回 2 条消息——系统指令（含角色设定、翻译要求、输出格式）+ 用户输入（待翻译文本）。

**修改 style 测试**:
- `style = "口语化"` → 系统指令中的翻译风格要求变为"使用日常自然的表达方式"

---

## 测试 5: Prompt 引用 Resource — `analyze_note`

### 5.1 基本用法

参数: `note_id = "shopping"`

**预期**: 返回 2 条消息：
1. **第 1 条 (role=user)**: 系统指令——知识管理专家的角色和分析要求
2. **第 2 条 (role=user)**: ResourceLink——指向 `note://shopping` 的链接

### 5.2 理解 ResourceLink

观察第 2 条消息的 content 类型：
```json
{
  "type": "resource_link",
  "uri": "note://shopping",
  "name": "笔记 shopping",
  "mimeType": "text/markdown"
}
```

**关键理解**: 
- ResourceLink 只传 URI，**不包含数据本身**
- 客户端看到这个链接后，会自行调用 `resources/read` 来获取内容
- 这保持了 Prompt 的轻量和解耦——Prompt 定义"需要什么数据"，但不嵌入数据

### 5.3 ResourceLink vs EmbeddedResource

| 方式 | 内容 | 何时用 |
|------|------|--------|
| **ResourceLink** | 只传 URI | 资源在 Server 端，客户端自行获取（推荐） |
| **EmbeddedResource** | 嵌入资源内容 | 内容在生成 Prompt 时就已知，不需要额外请求 |

`analyze_note` 使用的是 ResourceLink。如果要用 EmbeddedResource，代码会是这样：
```python
PromptMessage(
    role="user",
    content=EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=f"note://{note_id}",
            mimeType="text/markdown",
            text=note_content,  # 直接嵌入内容
        ),
    ),
)
```

---

## 测试 6: 结构化引导 Prompt — `new_note_wizard`

### 6.1 不带参数

参数: 全部留空

**预期**: 
- 系统指令中提示 "请先引导用户确定笔记主题"
- 系统指令中提示 "根据内容推荐合适的分类"

### 6.2 带参数

参数: `topic = "Python 异步编程"`, `category = "study"`

**预期**:
- 系统指令中提示 "主题是「Python 异步编程」"
- 系统指令中提示 "分类为「study」。所有笔记统一使用该分类。"

**关键理解**: 
- Prompt 的参数控制模板内容，但不执行任何操作
- 这和 Tool 完全不同——Tool 会真正"创建笔记"，Prompt 只是"生成引导对话"
- **Prompts 引导思考，Tools 执行操作**

---

## 测试 7: 工具辅助 — `list_available_prompts` 和 `compare_primitives`

### 7.1 list_available_prompts

切换到 **Tools** 标签 → 调用 `list_available_prompts`（无需参数）。

**预期**: 返回所有 5 个 Prompt 的摘要信息（名称、描述、参数、适用场景）。

**关键理解**: 这是用 Tool 来描述 Prompt，展示了 Tool 和 Prompt 可以互相配合。

### 7.2 compare_primitives

调用 `compare_primitives`（无需参数）。

**预期**: 返回三大原语的对比表，包含：
- Tools / Resources / Prompts 的定义
- 返回内容类型
- 是否有副作用
- REST API 类比
- LLM 视角
- 决策指南

---

## Phase 4 完成检查清单

- [ ] 在 Inspector 中看到了 5 个 Prompt 模板
- [ ] 成功 Get Prompt `greet_user`，理解了返回消息结构
- [ ] 成功 Get Prompt `review_writing`，区分了 system 和 user 消息的角色
- [ ] 理解了参数如何影响 Prompt 模板的内容（测试不同的 focus/style 值）
- [ ] 成功 Get Prompt `analyze_note`，看到了 ResourceLink 的 URI 引用
- [ ] 理解了 ResourceLink (传 URI) vs EmbeddedResource (嵌入内容) 的区别
- [ ] 成功 Get Prompt `new_note_wizard`，理解了 Prompt 的"引导"作用
- [ ] 理解了 Prompts 和 Tools 的核心区别：生成对话模板 vs 执行操作返回数据
- [ ] 能用自己的话解释三大原语各自的定位和适用场景

---

## 学到的关键概念

| 概念 | 一句话总结 |
|------|-----------|
| Prompt | 服务端预定义的对话模板，引导 AI 或用户启动特定工作流 |
| @mcp.prompt() | 注册一个 Prompt 模板，可设置 name/title/description |
| PromptMessage | Prompt 返回的消息单元，包含 role 和 content |
| TextContent | 文本类型的消息内容，type="text" |
| ResourceLink | 在 Prompt 中引用 Resource URI，客户端自行获取内容 |
| EmbeddedResource | 在 Prompt 中直接嵌入资源内容 |
| system vs user | system 设定 AI 角色和规则，user 传入具体任务 |
| Prompts vs Tools | Prompts 返回对话模板（引导思考），Tools 执行代码返回数据（完成操作） |
| Prompts vs Resources | Prompts 返回消息列表（模板），Resources 返回只读数据（内容） |
| 参数化模板 | 同一个 Prompt 通过不同参数生成不同的对话起点 |

---

## 三大原语对比速查

```
              ┌──────────┬──────────────┬─────────────┐
              │  Tools   │  Resources   │   Prompts   │
┌─────────────┼──────────┼──────────────┼─────────────┤
│ 做什么       │ 执行操作  │ 暴露数据      │ 提供模板     │
│ 返回         │ 执行结果  │ 数据内容      │ 消息列表     │
│ 副作用       │ 有        │ 无           │ 无          │
│ 类比         │ POST/PUT │ GET          │ 邮件模板     │
│ LLM 说了什么  │ "我调用"  │ "我读取"      │ "我引导"     │
│ 谁触发       │ LLM      │ LLM          │ 用户/LLM     │
└─────────────┴──────────┴──────────────┴─────────────┘
```
