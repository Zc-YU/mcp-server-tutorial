"""Step 6: 动态资源模板（Dynamic Resource Templates）。

学习目标:
  - URI 模板: @mcp.resource("note://{note_id}") 的花括号语法
  - {param} 如何自动绑定到函数参数
  - 动态资源 vs 静态资源的使用场景
  - 一个函数 = 无限个资源（每个 note_id 一个 URI）

关键概念:
  静态资源: 固定 URI，固定内容（如配置、状态）
  动态资源: URI 模板，内容取决于参数（如按 ID 查数据）

运行: uv run steps/step06_resources_dynamic.py
测试: uv run mcp dev steps/step06_resources_dynamic.py
"""
import sys
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")

mcp = FastMCP("Resources Dynamic Demo", host="0.0.0.0", port=8000)

# ============================================================
# 模拟数据库
# ============================================================

NOTES = {
    "welcome": {
        "id": "welcome",
        "title": "欢迎使用 Smart Notes",
        "content": "这是你的第一篇笔记。Smart Notes 是一个基于 MCP 的智能笔记系统。",
        "tags": ["help", "meta"],
        "created_at": "2026-05-01T08:00:00Z",
        "updated_at": "2026-05-30T10:00:00Z",
    },
    "shopping": {
        "id": "shopping",
        "title": "周末购物清单",
        "content": "牛奶、鸡蛋、面包、水果、酸奶、纸巾",
        "tags": ["todo", "生活"],
        "created_at": "2026-05-28T12:00:00Z",
        "updated_at": "2026-05-29T09:00:00Z",
    },
    "python-intro": {
        "id": "python-intro",
        "title": "Python 入门笔记",
        "content": """# Python 基础

## 变量
动态类型，不需要声明。

## 函数
def 关键字定义。

## 列表
最常用的数据结构。""",
        "tags": ["study", "python"],
        "created_at": "2026-05-20T14:00:00Z",
        "updated_at": "2026-05-25T16:30:00Z",
    },
    "meeting-q3": {
        "id": "meeting-q3",
        "title": "Q3 项目规划会议",
        "content": "讨论 Q3 路线图: 1.用户模块重构 2.性能优化 3.新功能上线排期",
        "tags": ["work", "meeting"],
        "created_at": "2026-05-15T09:00:00Z",
        "updated_at": "2026-05-15T10:30:00Z",
    },
}


# ============================================================
# 1. 基础动态资源 — 一个 URI 参数
# ============================================================

@mcp.resource("note://{note_id}")
def get_note(note_id: str) -> str:
    """获取指定笔记的 Markdown 版本。

    URI 中的 {note_id} 绑定到函数的 note_id 参数。
    LLM 调用时: 读 note://shopping → 函数收到 note_id="shopping"
    """
    note = NOTES.get(note_id)
    if not note:
        return f"# 404: 笔记不存在\n\nID `{note_id}` 未找到。"

    tags_str = ", ".join(f"`{t}`" for t in note["tags"])
    return f"""# {note['title']}

{note['content']}

---
**ID:** `{note['id']}`
**标签:** {tags_str}
**创建:** {note['created_at']}
**更新:** {note['updated_at']}
"""


# ============================================================
# 2. 同一数据的不同视图 — 多 URI 指向同一对象
# ============================================================

@mcp.resource("note://{note_id}/raw")
def get_note_raw(note_id: str) -> dict:
    """获取笔记的原始 JSON 数据。

    对比 note://{note_id} 返回 Markdown，这个返回 JSON。
    不同 URI 提供不同"视图"——LLM 根据需要选择。
    """
    note = NOTES.get(note_id)
    if not note:
        return {"error": "not_found", "id": note_id}
    return note


@mcp.resource("note://{note_id}/summary")
def get_note_summary(note_id: str) -> str:
    """获取笔记的一句话摘要。"""
    note = NOTES.get(note_id)
    if not note:
        return f"笔记 {note_id} 不存在"
    # 取第一行作为摘要
    first_line = note["content"].strip().split("\n")[0]
    return f"**{note['title']}**: {first_line[:80]}{'...' if len(first_line) > 80 else ''}"


# ============================================================
# 3. 聚合资源 — 按条件筛选
# ============================================================

@mcp.resource("notes://tag/{tag_name}")
def list_notes_by_tag(tag_name: str) -> str:
    """列出所有带指定标签的笔记（Markdown 列表）。

    例如: notes://tag/study → 返回所有 study 标签的笔记
    """
    matches = [
        note for note in NOTES.values()
        if tag_name.lower() in [t.lower() for t in note["tags"]]
    ]

    if not matches:
        return f"没有找到标签为 `{tag_name}` 的笔记。"

    lines = [f"# {len(matches)} 篇笔记 (标签: {tag_name})\n"]
    for note in matches:
        lines.append(f"- **[{note['title']}](note://{note['id']})** — {note['created_at']}")

    return "\n".join(lines)


@mcp.resource("notes://all")
def list_all_notes() -> str:
    """列出所有笔记的索引。

    LLM 可以先读这个获取全貌，再按需读具体笔记。
    这是常见的 MCP 资源模式: 索引 → 详情。
    """
    if not NOTES:
        return "暂无笔记。"

    lines = [f"# 全部笔记 ({len(NOTES)} 篇)\n"]
    for note in sorted(NOTES.values(), key=lambda n: n["updated_at"], reverse=True):
        tags = ", ".join(note["tags"])
        lines.append(f"- **{note['title']}** [{tags}] → `note://{note['id']}`")

    return "\n".join(lines)


# ============================================================
# 配合 Tool — 通过 Tool 查看可用资源
# ============================================================

@mcp.tool()
def list_resource_uris() -> dict:
    """列出本 Server 提供的所有资源 URI。

    这是一个 Tool（不是 Resource），
    LLM 可以通过它快速了解有哪些资源可用。
    """
    return {
        "resources": [
            "note://{note_id}",
            "note://{note_id}/raw",
            "note://{note_id}/summary",
            "notes://tag/{tag_name}",
            "notes://all",
        ],
        "available_note_ids": list(NOTES.keys()),
    }


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
