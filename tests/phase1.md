# Phase 1 测试文档

## 测试目标

1. 验证 MCP SDK 安装成功
2. 验证 Hello World Server 可以启动
3. 验证传输模式切换
4. 理解 stdout/stderr 分离规则

---

## 测试 1: 验证 SDK 安装

```bash
# 检查 mcp 包是否可用
uv run python -c "from mcp.server.fastmcp import FastMCP; print('OK')"
```

**预期输出**: `OK`

**如果失败**: `uv add "mcp[cli]"` 重新安装

---

## 测试 2: 验证 Hello World Server 启动

```bash
uv run steps/step01_hello.py
```

**预期行为**: 程序启动后阻塞，等待 JSON-RPC 输入（可以 Ctrl+C 退出）

**如果打印乱码或崩溃**: 检查 Python 版本 ≥ 3.12

---

## 测试 3: MCP Inspector 调试（推荐）

这是 MCP 官方的可视化调试工具，让你在浏览器里直接测试 Server：

```bash
uv run mcp dev steps/step01_hello.py
```

**预期行为**: 
- 终端打印类似 `MCP Inspector is running on http://127.0.0.1:6274`
- 浏览器打开该地址后能看到:
  - 左侧: Server 的工具列表 (`greet`, `add`, `repeat`)
  - 右侧: 工具输入/输出面板
- 点击 `greet` → 输入 `name: "你的名字"` → 点击 Run → 看到返回结果

**效果验证**:
```
Tool: greet
Input:  { "name": "测试员" }
Output: "Hello, 测试员! 欢迎来到 MCP 的世界。"
```

---

## 测试 4: 验证三种传输模式

### 4a stdio 模式（默认）
```bash
uv run steps/step02_transport.py
# 或显式指定
uv run steps/step02_transport.py stdio
```
**预期**: 阻塞等待 JSON-RPC，Ctrl+C 退出

### 4b Streamable HTTP 模式
```bash
uv run steps/step02_transport.py streamable-http
```
**预期输出**:
```
[INFO] 启动模式: streamable-http
[INFO] Streamable HTTP 模式: http://127.0.0.1:8000/mcp
```
然后可以用 curl 测试:
```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```
**预期**: 返回 JSON 格式的工具列表

### 4c SSE 模式（已弃用，仅验证能启动）
```bash
uv run steps/step02_transport.py sse
```
**预期**: 警告 "SSE 已弃用"，但仍然监听端口

---

## 测试 5: 验证 stdout/stderr 分离

这是一个概念验证 — 帮助你理解为什么 MCP Server 不能用 `print()`。

MCP Inspector 内部已经处理了这个问题，你写代码时只需记住:
- ✅ 用 `logging.getLogger(__name__).info(...)` — 走 stderr
- ❌ 用 `print(...)` — 走 stdout，破坏 JSON-RPC

如果手动测试，可以观察：
```bash
# step01 的日志只出现在终端 stderr，不影响协议
uv run steps/step01_hello.py 2> /tmp/mcp.log
# 另一个终端查看日志
tail -f /tmp/mcp.log
```

---

## Phase 1 完成检查清单

- [ ] `uv run python -c "from mcp.server.fastmcp import FastMCP; print('OK')"` 成功
- [ ] `uv run steps/step01_hello.py` 能启动
- [ ] `uv run mcp dev steps/step01_hello.py` Inspector 中能调用 `greet` 并看到返回
- [ ] `uv run steps/step02_transport.py streamable-http` 能启动 HTTP 模式
- [ ] 理解了为什么 stdout 只能有 JSON-RPC，日志必须去 stderr
- [ ] 理解了 stdio vs Streamable HTTP 的适用场景

---

## 学到的关键概念

| 概念 | 一句话总结 |
|------|-----------|
| FastMCP | 高层 API，装饰器注册 Tools/Resources/Prompts |
| @mcp.tool() | 注册一个可被 LLM 调用的函数 |
| stdio | 子进程通信，IDE 集成用 |
| Streamable HTTP | HTTP 端点，Web 和 Agent 框架用 |
| JSON-RPC 2.0 | MCP 的底层通信协议 |
| stdout 规则 | stdout = JSON-RPC 通道，绝不能污染 |
