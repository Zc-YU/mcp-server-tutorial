"""Step 5: 静态资源（Static Resources）。

学习目标:
  - Resource 是什么: MCP Server 暴露的只读数据
  - @mcp.resource("scheme://path") 如何定义 URI
  - 返回 str → 文本资源，返回 dict → JSON 资源
  - Resources 和 Tools 的区别: 读数据 vs 做操作

关键概念:
  Resources = Server 对 LLM 说"我有这些数据你可以读"
  就像网站给搜索引擎暴露 sitemap —— 列出有哪些页面可访问

运行: uv run steps/step05_resources_static.py
测试: uv run mcp dev steps/step05_resources_static.py
"""
import logging
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")

mcp = FastMCP("Resources Static Demo", host="0.0.0.0", port=8000)

COUNTER = {"value": 0}


# ============================================================
# 1. 文本资源 — 返回 str
# ============================================================

@mcp.resource("config://app")
def get_app_config() -> str:
    """应用配置，返回纯文本。

    resource URI: config://app
    LLM 可以"打开"这个 URI 读取配置。
    """
    return """
    ===== Smart Notes 配置 =====
    版本: 1.0.0
    最大笔记长度: 10,000 字
    支持格式: Markdown, 纯文本
    标签上限: 10 个/篇
    存储路径: ~/.mcp_smart_notes.json
    """


@mcp.resource("info://status")
def get_status() -> str:
    """服务器运行状态。"""
    return "状态: 运行中 | 协议: MCP/JSON-RPC 2.0 | 传输: stdio"


# ============================================================
# 2. JSON 资源 — 返回 dict，自动序列化
# ============================================================

@mcp.resource("stats://summary", mime_type="application/json")
def get_stats() -> dict:
    """返回统计数据。FastMCP 自动把 dict 序列化为 JSON。

    resource URI: stats://summary
    返回类型 dict → Content-Type: application/json
    """
    return {
        "notes": {"total": 42, "today": 3, "this_week": 12},
        "words": {"total": 3150, "average_per_note": 75},
        "tags": {"most_used": ["work", "study", "todo"]},
        "last_modified": "2026-05-30T10:00:00Z",
    }


# ============================================================
# 3. Markdown 资源 — 结合结构化 + 可读
# ============================================================

@mcp.resource("help://quickstart")
def get_quickstart() -> str:
    """快速入门指南，Markdown 格式。

    LLM 读取后可以直接向用户展示或解释。
    """
    return """# Smart Notes 快速入门

## 创建笔记
使用 `create_note` 工具，传入标题、内容和标签。

## 搜索笔记
使用 `search_notes` 工具，支持关键词搜索和分类过滤。

## 管理笔记
- `list_notes` — 列出所有笔记
- `get_note` — 读取单篇笔记
- `update_note` — 修改笔记
- `delete_note` — 删除笔记

## 查看统计
读取 `stats://summary` 资源获取使用统计。
"""


# ============================================================
# 4. Tool + Resource 协作 — Tool 写状态，Resource 读状态
# ============================================================

@mcp.resource("state://counter", mime_type="application/json")
def get_counter_state() -> dict:
    """读取当前计数器状态。

    Resource 只负责读数据，不修改状态。
    """
    return {"counter": COUNTER["value"]}


@mcp.tool()
def increment_counter(by: int = 1) -> dict:
    """增加计数器数值。

    这是一个 Tool，会修改服务端状态。修改后可以通过
    state://counter 资源读取最新值。
    """
    COUNTER["value"] += by
    return {"counter": COUNTER["value"]}


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
