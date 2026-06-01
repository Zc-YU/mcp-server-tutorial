# MCP 核心概念与理论知识

> 阅读提示：每个章节末尾标注了对应的实践 Phase，建议先读理论再看代码。

---

## §1 MCP 是什么？

### 1.1 背景

在 MCP 出现之前，AI 助手（如 Claude、ChatGPT）要访问外部数据或工具，每个 AI 平台、每个工具都要单独写集成代码。就像 USB 出现之前，每种外设需要自己的接口。

**MCP（Model Context Protocol）** 是 Anthropic 于 2024 年底发布的开放协议，定义了 AI 应用与外部工具/数据源之间的**标准通信接口**。它类比于：

| 领域 | 协议 | 作用 |
|------|------|------|
| 互联网 | HTTP | 浏览器 ↔ 服务器 |
| 数据库 | SQL | 应用 ↔ 数据库 |
| 外设 | USB | 电脑 ↔ 外设 |
| **AI 工具** | **MCP** | **AI 助手 ↔ 外部工具/数据** |

### 1.2 核心价值

```
之前: AI 平台 A → 集成代码 A1 → 工具 1
      AI 平台 A → 集成代码 A2 → 工具 2
      AI 平台 B → 集成代码 B1 → 工具 1    ← 每个组合都要写
      AI 平台 B → 集成代码 B2 → 工具 2

之后: AI 平台 A → MCP Client ─┐
      AI 平台 B → MCP Client ─┤              ← 只需 MCP 协议
                               ├→ MCP Server → 工具
      任意 MCP Client ────────┘
```

**一次编写 Server，所有 MCP 客户端都能用。**

### 1.3 MCP 不是什么

- 不是 AI 模型本身（它不替代 Claude/GPT）
- 不是 Agent 框架（它不编排多步任务）
- 不是向量数据库（它不管嵌入和检索）
- MCP **只做一件事**：在 AI 和外部工具之间建立标准化通信通道

> 📍 对应实践：Phase 1（理解了我们为什么要写 MCP Server）

---

## §2 架构模型

### 2.1 Client-Server 架构

```
┌──────────────┐         JSON-RPC 2.0        ┌──────────────┐
│              │ ◄══════════════════════════► │              │
│  MCP Client  │   (stdio / HTTP / SSE)       │  MCP Server  │
│              │                              │              │
│  例: Claude   │                              │  你写的代码   │
│  Code, Cursor│                              │              │
└──────────────┘                              └──────────────┘
```

- **MCP Client**: 嵌入在 AI 应用中（Claude Code、Cursor 等），负责发起请求
- **MCP Server**: 你编写的程序，暴露工具、数据和提示模板
- **通信协议**: JSON-RPC 2.0，所有消息都是 JSON 格式
- **Host**: 运行 MCP Client 的宿主应用（如 Claude Desktop、VS Code）

### 2.2 JSON-RPC 2.0 消息格式

MCP 底层走 JSON-RPC 2.0，四种消息类型：

```jsonc
// 1. 请求 (Client → Server): 要求服务器做某事
{ "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": { "name": "add", "arguments": { "a": 1, "b": 2 } } }

// 2. 响应 (Server → Client): 返回结果
{ "jsonrpc": "2.0", "id": 1, "result": { "content": [{ "type": "text", "text": "3" }] } }

// 3. 错误 (Server → Client): 出错时
{ "jsonrpc": "2.0", "id": 1, "error": { "code": -32600, "message": "Invalid Request" } }

// 4. 通知 (双向): 不需要回复的消息
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

不过 FastMCP 封装了这些细节，你不需要手写 JSON-RPC。

### 2.3 初始化握手

MCP 连接建立后有一个固定的握手流程：

```
Client ── initialize ──► Server    (客户端声明能力和协议版本)
Client ◄─ capabilities ─ Server    (服务端返回自己支持什么)
Client ── initialized ──► Server   (通知握手完成)

之后才能正常调用 tools/list, resources/read 等
```

`FastMCP` 自动处理这个流程，你不需要手动实现。

> 📍 对应实践：Phase 1（理解 server.py 启动后发生了什么）

---

## §3 三大原语（Primitives）

这是 MCP 最核心的概念。一个 MCP Server 可以提供三种资源：

### 3.1 Tools（工具）— "让 AI 做事"

**定义**: 服务端暴露的可调用函数。AI 可以调用它们来执行操作、计算、修改数据。

**类比**: REST API 的 POST/PUT/DELETE 端点

**特点**:
- 有输入参数（类型安全，带 JSON Schema）
- 有返回值
- 会产生**副作用**（创建、修改、删除数据）
- 可以上报进度（长时间运行的任务）
- 可以写日志（供调试）

**LLM 视角**: 服务器说"我有这些函数，参数是...，你可以调用来完成用户的任务"。LLM 决定何时调用、传什么参数。

```python
@mcp.tool()
def create_note(title: str, content: str, tags: list[str] = []) -> dict:
    """创建一篇笔记。"""
    return {"id": "abc", "title": title}
```

**关键规则**:
| 规则 | 原因 |
|------|------|
| 工具名用 snake_case | 惯例，`create_note` 而非 `createNote` |
| Docstring 写清楚 | LLM 读 docstring 来决定是否调用 |
| 类型提示要完整 | 类型 → JSON Schema，影响 LLM 传参 |
| 副作用要明确 | 创建/删除类工具要写清楚后果 |

> 📍 对应实践：Phase 2（step03/step04）

### 3.2 Resources（资源）— "让 AI 读数据"

**定义**: 服务端暴露的只读数据，通过 URI 寻址。AI 可以读取它们来获取上下文。

**类比**: REST API 的 GET 端点

**特点**:
- 只读（不允许修改数据）
- 通过 URI 寻址（类似 URL）
- 可以返回文本或二进制（JSON、Markdown、图片等）
- 支持 URI 模板（动态参数）

**LLM 视角**: 服务器说"我有这些数据资源，URI 是...，你需要时可以读"。

```python
@mcp.resource("note://{note_id}")
def get_note(note_id: str) -> str:
    """读取指定笔记的内容。"""
    return f"# {title}\n\n{content}"
```

**URI 设计约定**:
```
scheme://authority/path        (类似 URL)
note://abc123                  (获取笔记 abc123)
note://abc123/raw              (获取原始 JSON)
notes://tag/work               (获取 work 标签的笔记列表)
config://app                   (获取应用配置)
```

**静态 vs 动态资源**:
| 类型 | URI | 何时用 |
|------|-----|--------|
| 静态 | `stats://summary` | 固定内容，如配置、状态 |
| 动态 | `note://{note_id}` | 参数化内容，如按 ID 查数据 |

> 📍 对应实践：Phase 3（step05/step06）

### 3.3 Prompts（提示模板）— "引导 AI 思考"

**定义**: 服务端预定义的提示词模板。用户/AI 可以选择一个模板来启动特定工作流。

**类比**: 邮件模板、文档模板 — 提供结构化的起点

**特点**:
- 在服务端定义，客户端执行
- 可以带参数（如 `topic`、`count`）
- 可以包含多条消息（system + user + assistant 角色）
- 可以引用 Resources 的 URI

**LLM 视角**: 服务器说"我可以帮用户生成这些类型的提示词"。

```python
@mcp.prompt()
def review_note(note_id: str) -> list[PromptMessage]:
    return [
        PromptMessage(role="system", content=TextContent(
            type="text", text="你是专业编辑。"
        )),
        PromptMessage(role="user", content=TextContent(
            type="text", text=f"请审阅笔记 {note_id}"
        )),
    ]
```

**Prompts 与 Tools 的区别**:
| | Tools | Prompts |
|---|---|---|
| 谁执行 | 服务端执行代码 | 客户端用模板生成对话 |
| 返回值 | 数据 | 提示词文本 |
| 作用 | 完成操作 | 引导思考 |
| 时机 | AI 需要做某事 | 用户启动工作流 |

> 📍 对应实践：Phase 4（step07）

### 3.4 三大原语决策图

```
你需要什么？
  │
  ├── AI 需要执行操作（创建/修改/删除/计算）？ → Tool
  │
  ├── AI 需要读取已有数据（获取上下文）？ → Resource
  │
  └── 用户需要一个结构化的对话起点？ → Prompt
```

> 📍 对应实践：Phase 5（设计 Smart Notes 时分配 Tools/Resources/Prompts）

---

## §4 传输层（Transport）

传输层决定 Client 和 Server 之间**怎么连**。

### 4.1 stdio（标准输入输出）

```
Client ──启动子进程──► Server
   │                    │
   │  stdin ──── JSON ─►│
   │◄─── stdout ─ JSON ─│
   │  stderr ── logs ──►│ (日志单独通道)
```

- Client 将 Server 作为**子进程**启动
- 通信走进程的 stdin/stdout
- 最常用、最可靠的方式
- 不需要网络、端口、认证
- **致命规则**：stdout 只能输出 JSON-RPC，任何 `print()` 都会破坏协议

### 4.2 Streamable HTTP（推荐替代 SSE）

```
Client ── HTTP POST ──► http://localhost:8000/mcp
   │
   │  请求体: JSON-RPC
   │  响应: JSON-RPC + 可选流式
```

- 单一 HTTP 端点
- 支持流式响应（大结果逐块返回）
- 多客户端可以共享同一个 Server 进程
- 适合 Web 客户端和 Agent 框架

### 4.3 SSE（Server-Sent Events，已弃用）

旧版方案，已被 Streamable HTTP 取代。新项目不需要关注。

### 4.4 传输层对比

| 维度 | stdio | Streamable HTTP |
|------|-------|-----------------|
| 连接方式 | 子进程 | HTTP 端点 |
| 网络访问 | 不支持 | 支持 |
| 多客户端 | 否（每客户端一个进程） | 是（共享进程） |
| 部署难度 | 最低 | 需要启动独立服务 |
| 适用场景 | IDE 集成 | Web/Agent 框架/远程 |
| Claude Code | 原生 | 支持 |
| Cursor/VS Code | 原生 | 不支持 |

> 📍 对应实践：Phase 1 step02（传输层实验）, Phase 6（多客户端集成）

---

## §5 请求生命周期

以一个 Tool 调用为例，看完整流程：

```
1. 用户: "帮我创建一篇标题为'购物清单'的笔记"
               │
2. LLM:  我理解用户意图，但需要 Notebook 工具
         检查可用的 MCP Tools 列表
         发现 create_note(title, content, tags) 匹配
               │
3. Client ── tools/call ──────────────► Server
           {                              │
             "name": "create_note",       4. Server 解析参数
             "arguments": {               5. 执行 create_note()
               "title": "购物清单",        6. 返回结果
               "content": "牛奶...",
               "tags": ["生活"]
             }
           }                              │
          ◄── result ────────────────────┘
           {
             "id": "abc123",
             "title": "购物清单",
             ...
           }
               │
7. LLM:  笔记已创建 (ID: abc123)
         向用户汇报结果
```

同样的流程适用于 Resources（`resources/read`）和 Prompts（`prompts/get`）。

### 工具发现流程

```
Client ── tools/list ──► Server
Client ◄── [                         Server 返回所有工具的 Schema
             {                         (名称、描述、参数 JSON Schema)
               "name": "create_note",
               "description": "创建一篇笔记",
               "inputSchema": {
                 "type": "object",
                 "properties": {
                   "title": { "type": "string" },
                   ...
                 }
               }
             },
             ...
           ]
```

LLM 根据这些 Schema 判断何时调用哪个工具。所以**类型提示和 docstring 的质量直接影响 AI 的判断**。

> 📍 对应实践：Phase 5（完整 Demo 中观察完整请求链路）

---

## §6 类型提示与 JSON Schema 的映射

FastMCP 自动将 Python 类型提示转换为 JSON Schema：

| Python 类型 | JSON Schema | 备注 |
|------------|-------------|------|
| `str` | `{"type": "string"}` | |
| `int` | `{"type": "integer"}` | |
| `float` | `{"type": "number"}` | |
| `bool` | `{"type": "boolean"}` | |
| `list[str]` | `{"type": "array", "items": {"type": "string"}}` | |
| `dict` | `{"type": "object"}` | 不推荐，没有具体字段 |
| `Enum` | `{"type": "string", "enum": [...]}` | 约束可选值 |
| `BaseModel` | `{"type": "object", "properties": {...}}` | **最推荐**，完整 Schema |
| `Optional[X]` | 字段变为非必填 | |
| `X = default` | 字段非必填，有默认值 | |

**对比示例**：

```python
# 差: LLM 不知道参数格式
@mcp.tool()
def search(query: str) -> list[str]:
    """搜索"""
    ...

# 好: LLM 知道每个参数的约束
@mcp.tool()
def search(
    query: str,
    max_results: int = 10,
    case_sensitive: bool = False,
) -> list[str]:
    """在笔记中搜索。max_results控制返回数量，case_sensitive控制大小写。"""
    ...

# 最好: Pydantic 模型提供完整的结构化 Schema
class SearchParams(BaseModel):
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=10, ge=1, le=100, description="最大结果数")
    case_sensitive: bool = Field(default=False, description="是否区分大小写")

@mcp.tool()
def search(params: SearchParams) -> list[str]:
    """在笔记中全文搜索。"""
    ...
```

> 📍 对应实践：Phase 2 step03（参数类型实验）

---

## §7 MCP 在 AI 生态中的位置

### 7.1 技术栈全景

```
┌────────────────────────────────────────┐
│              AI 应用层                  │
│  Claude Code / Cursor / VS Code / ...  │
├────────────────────────────────────────┤
│           Agent 框架层 (可选)           │
│  LangChain / CrewAI / AutoGen / ...    │
├────────────────────────────────────────┤
│           MCP 协议层 ★我们在这里        │
│  ┌──────────┐  ┌──────────────────┐    │
│  │ MCP Client│  │  MCP Server ★    │    │
│  └──────────┘  └──────────────────┘    │
├────────────────────────────────────────┤
│           AI 模型层 (LLM)              │
│  Claude / GPT / Gemini / ...          │
├────────────────────────────────────────┤
│           数据与工具层                  │
│  数据库 / API / 文件系统 / ...         │
└────────────────────────────────────────┘
```

### 7.2 MCP 和其他方案的关系

| 方案 | 定位 | 和 MCP 的关系 |
|------|------|-------------|
| **Function Calling** (OpenAI/Anthropic API) | 模型级别的工具调用 | MCP 是传输层，FC 是模型能力。MCP Server 最终会被 LLM 通过 FC 调用 |
| **LangChain Tools** | Agent 框架的工具抽象 | LangChain 可以包装 MCP Server 作为 Tool 使用 |
| **REST API** | 通用 Web API | MCP 专为 AI 优化（自动 Schema 发现、流式、进度），REST 是通用的 |
| **A2A (Agent-to-Agent)** | Google 的 Agent 间通信协议 | A2A = Agent ↔ Agent，MCP = Agent ↔ Tool。互补关系 |

### 7.3 哪些产品支持 MCP？

**AI 编程工具**（均支持 MCP）:
- Claude Code / Claude Desktop（Anthropic，协议发起者）
- Cursor / VS Code Copilot / GitHub Copilot
- Windsurf / Continue / Cline
- JetBrains AI Assistant

**Agent 框架**（可以将 MCP Server 作为工具集成）:
- LangChain `langchain_mcp_adapters`
- CrewAI MCP 集成
- AutoGen MCP 工具

**自建应用**（通过 MCP SDK 构建 Client）:
- 任何 Python/TS 应用都可以引入 MCP Client
- Web Chat UI 可以通过 Streamable HTTP 连接

> 📍 对应实践：Phase 6（多客户端配置）

---

## §8 常见陷阱

### 8.1 stdout 污染

```python
# 错误! 会破坏 JSON-RPC
print("Server started!")
print(f"User requested: {something}")

# 正确: 去 stderr
import sys, logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logging.info("Server started!")
```

### 8.2 同步阻塞

```python
# 错误! 在 async 工具里用同步阻塞
@mcp.tool()
async def my_tool(ctx: Context = None):
    time.sleep(5)  # 阻塞整个事件循环!
    return "done"

# 正确: 用 asyncio.sleep
@mcp.tool()
async def my_tool(ctx: Context = None):
    await asyncio.sleep(5)  # 不阻塞
    return "done"
```

### 8.3 Context 忘记默认值

```python
# 错误! Context 是必填参数
@mcp.tool()
async def my_tool(ctx: Context):  # MCP 无法注入!
    ...

# 正确: 默认值 None
@mcp.tool()
async def my_tool(ctx: Context = None):
    ...
```

### 8.4 .mcp.json 路径错误

```jsonc
// 错误: 相对路径、不带 venv
{ "command": "python", "args": ["server.py"] }

// 正确: uv run 自动处理环境
{ "command": "uv", "args": ["run", "--directory", "/absolute/path/to/project", "server.py"] }
```

> 📍 对应实践：Phase 6（调试排错）
