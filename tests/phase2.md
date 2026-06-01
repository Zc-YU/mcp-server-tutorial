# Phase 2 测试文档

## 测试目标

1. 理解 Python 类型提示 → JSON Schema 的映射关系
2. 理解 Enum / Pydantic BaseModel 如何生成结构化 Schema
3. 理解 Context 注入和日志/进度机制
4. 理解 async 工具的正确写法

---

## 测试 1: 参数类型系统

```bash
uv run mcp dev steps/step03_tools_basic.py
```

### 1.1 基础类型 — `calculator`

在 Inspector 中选择 **calculator**，观察参数面板：
- `a` 和 `b` 显示为 number 输入框（来自 `int`）
- `operation` 显示为文本输入框，标注了默认值 `add`（来自 `str = "add"`）

**测试用例**:
| a | b | operation | 预期 result |
|---|---|-----------|-------------|
| 10 | 5 | add | 15 |
| 10 | 5 | multiply | 50 |
| 10 | 0 | divide | error: 除数不能为 0 |
| 10 | 5 | invalid | error: 未知操作 |

### 1.2 Enum 参数 — `create_task`

选择 **create_task**，观察 `category` 参数 — 应该显示为下拉菜单，选项是 `work / personal / study / todo`。

**测试**: category=study, priority=high, title="学习 MCP"
**预期**: 返回 JSON，category 和 priority 为枚举值

**关键理解**: `Enum` 的子类自动变成 JSON Schema 的 `enum` 约束，LLM 只能从这 4 个值里选。

### 1.3 Pydantic BaseModel — `search_notes`

选择 **search_notes**，观察参数面板 — 应该是一个**结构化表单**：
- `query` — 文本框，description 显示提示文字
- `max_results` — 数字框，范围 1-100，默认 10
- `category` — 下拉框（Optional[NoteCategory]，选了 "全部" 或枚举值）
- `case_sensitive` — 复选框，默认 false

**测试用例**:

| 测试场景 | query | max_results | category | case_sensitive |
|---------|-------|-------------|----------|----------------|
| 搜全部 | Python | 10 | (留空) | false |
| 搜+分类过滤 | Python | 100 | study | false |
| 搜+大小写敏感 | python | 10 | (留空) | true |

**预期**: 结果里只返回匹配的笔记。大小写敏感时搜 `python` (小写) 匹配不到 `Python` (大写)。

### 1.4 对比 `flat_params` vs `search_notes`

选择 **flat_params**，观察参数面板和 **search_notes** 的区别：
- `flat_params` 的 `category` 是普通文本框（LLM 不知道有哪些可选值）
- `search_notes` 的 `category` 是下拉框（Schema 里定义了 enum）

**关键理解**: 这就是为什么推荐用 Pydantic BaseModel —— 约束越精确，LLM 越不容易传错参数。

---

## 测试 2: 异步 + Context

```bash
uv run mcp dev steps/step04_tools_async.py
```

### 2.1 文件和进度 — `file_processor`

**测试**: file_path = "test.md"
**预期**: 返回 "处理完成"，Inspector 日志面板显示 info 和 debug 消息

**测试错误**: file_path = "test.txt"
**预期**: Inspector 日志显示 warning → error，工具返回 ValueError

### 2.2 进度上报 — `batch_operation`

**测试**: steps = 5
**预期**:

- Inspector 的进度条从 0 → 5（20% → 40% → 60% → 80% → 100%）
- 日志面板在 3/5 时显示 "里程碑: 3/5 完成"

**调大 steps 观察进度条**: steps = 15

### 2.3 错误处理 — `safe_divide`

**测试**: a=10, b=2（正常除法）
**预期**: result=5, status=success

**测试**: a=10, b=0（除零）
**预期**: result=null, error="除数不能为 0", status=degraded — 没有抛异常

### 2.4 异常传递 — `risky_operation`

**测试**: should_fail = false
**预期**: 返回 "操作成功!"

**测试**: should_fail = true
**预期**: 工具调用失败，Inspector 显示 RuntimeError 错误消息

### 2.5 Context 方法速查 — `context_demo`

**测试**: 直接调用，不需要参数
**预期**: Inspector 日志面板依次出现 debug → info → warning 三条日志

---

## Phase 2 完成检查清单

- [x] 理解了 `int/str/bool` 如何在 Inspector 中变成不同的输入控件
- [x] 理解了 Enum 如何变成下拉菜单
- [x] 理解了 Pydantic BaseModel 如何变成结构化表单
- [x] 能解释 `flat_params` 和 Pydantic 方式的 Schema 差异
- [x] 理解了 `ctx = None` 默认值的必要性
- [x] 在 Inspector 中观察到了 `ctx.info()` 的日志输出
- [x] 在 Inspector 中观察到了 `ctx.report_progress()` 的进度条
- [x] 理解了异常如何传递到客户端

---

## 学到的关键概念

| 概念 | 一句话总结 |
|------|-----------|
| 类型 → Schema | Python 类型提示自动生成 JSON Schema，决定 LLM 看到什么 |
| Enum | 限制可选值，LLM 只能在列出的值里选 |
| Pydantic BaseModel | 完整结构化 Schema，Field(description=) 给 LLM 提示 |
| Context | 自动注入的上下文，传日志和进度到客户端 |
| ctx.info() | 发送 info 级别日志，LLM 能追踪服务器在做什么 |
| ctx.report_progress() | 进度上报，客户端显示进度条 |
| async + asyncio.sleep | MCP 里的异步必须是 await asyncio.sleep()，不能用 time.sleep |
