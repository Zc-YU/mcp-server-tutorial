"""Smart Notes — 完整的 MCP Server,整合三大原语。

三大原语协同:
  Tools     → 创建、修改、删除、搜索笔记（副作用操作）
  Resources → 读取笔记内容、列表、统计（只读数据）
  Prompts   → 审阅、向导、摘要等对话模板（引导思考）

数据层:
  - 内存 dict + JSON 文件持久化
  - 4 篇种子笔记,开箱即用

架构设计原则:
  - Tool 负责写（create/update/delete/search）
  - Resource 负责读（note://, notes://, stats://）
  - Prompt 提供对话起点（review_note, new_note_wizard）
  - 三原语各司其职,不越界

运行:
  uv run python src/smart_notes/server.py                   # stdio (IDE 集成)
  uv run python src/smart_notes/server.py streamable-http   # HTTP (多客户端)
  uv run mcp dev src/smart_notes/server.py                  # Inspector 调试
"""
import sys
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import PromptMessage, TextContent, ResourceLink

logging.basicConfig(
    stream=sys.stderr, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("smart-notes")

mcp = FastMCP("Smart Notes", host="127.0.0.1", port=8000)

# ============================================================
# 数据层
# ============================================================

STORAGE_FILE = Path.home() / ".smart_notes.json"


def _load_notes() -> dict[str, dict]:
    if STORAGE_FILE.exists():
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # 种子数据
    return {
        "welcome": {
            "id": "welcome",
            "title": "欢迎使用 Smart Notes",
            "content": "这是你的第一篇笔记。Smart Notes 是一个基于 MCP 协议的智能笔记系统。\n\n## 核心设计\n- **Tools** 负责创建和修改笔记\n- **Resources** 负责读取和查询笔记\n- **Prompts** 提供审阅、向导等对话模板\n\n开始你的笔记之旅吧！",
            "tags": ["help", "meta"],
            "created_at": "2026-06-01T08:00:00Z",
            "updated_at": "2026-06-01T08:00:00Z",
        },
        "shopping": {
            "id": "shopping",
            "title": "周末购物清单",
            "content": "1. 牛奶（低脂）\n2. 鸡蛋 x12\n3. 全麦面包\n4. 香蕉\n5. 鸡胸肉\n6. 西兰花\n7. 酸奶\n8. 橄榄油",
            "tags": ["todo", "生活"],
            "created_at": "2026-06-01T10:00:00Z",
            "updated_at": "2026-06-01T10:30:00Z",
        },
        "python-async": {
            "id": "python-async",
            "title": "Python 异步编程要点",
            "content": """# Python 异步编程核心要点

## async/await
- `async def` 定义协程函数
- `await` 挂起当前协程,等待结果
- 只能在 `async` 函数内使用 `await`

## 事件循环
- `asyncio.run()` 启动事件循环
- 事件循环调度协程的执行
- 不要阻塞事件循环：用 `await asyncio.sleep()` 而非 `time.sleep()`

## Task 并发
- `asyncio.create_task()` 创建并发任务
- `asyncio.gather()` 等待多个任务完成
- Task 是协程的轻量级包装

## 常见陷阱
- 在 async 函数中用 `time.sleep()` 会阻塞整个事件循环
- 忘记 `await` 协程不会执行
- 在同步代码中直接调用 async 函数会报错""",
            "tags": ["study", "python", "编程"],
            "created_at": "2026-06-01T14:00:00Z",
            "updated_at": "2026-06-02T09:00:00Z",
        },
        "project-plan": {
            "id": "project-plan",
            "title": "Q3 项目规划",
            "content": """# Q3 项目规划 (2026)

## 目标
1. 完成 MCP Server 教程项目
2. 上线 Smart Notes v1.0
3. 编写技术文档

## 里程碑
| 时间 | 事项 |
|------|------|
| 6月 | MCP 三大原语学习 |
| 7月 | Smart Notes 功能完善 |
| 8月 | 测试 + 文档 + 发布 |

## 风险
- 时间紧张，需合理分配精力
- 新技术栈学习曲线""",
            "tags": ["work", "plan", "project"],
            "created_at": "2026-06-02T08:00:00Z",
            "updated_at": "2026-06-02T08:00:00Z",
        },
    }


NOTES: dict[str, dict] = _load_notes()


def _save_notes() -> None:
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(NOTES, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存失败: {e}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_id(title: str) -> str:
    """从标题生成 URL 友好的 ID。"""
    import re
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug if slug else hex(abs(hash(title)) % 10**8)[2:]


# ============================================================
# 枚举定义
# ============================================================

class NoteCategory(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    STUDY = "study"
    TODO = "todo"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================
# Pydantic 模型
# ============================================================

class SearchParams(BaseModel):
    """结构化搜索参数。"""

    query: str = Field(description="搜索关键词,支持多词用空格分隔")
    max_results: int = Field(default=10, ge=1, le=100, description="最大结果数 1-100")
    category: Optional[NoteCategory] = Field(default=None, description="按分类过滤,None 表示全部")
    case_sensitive: bool = Field(default=False, description="是否区分大小写")


class UpdateNoteParams(BaseModel):
    """更新笔记参数。所有字段可选,只传要修改的字段。"""

    note_id: str = Field(description="要更新的笔记 ID")
    title: Optional[str] = Field(default=None, description="新标题（可选）")
    content: Optional[str] = Field(default=None, description="新内容（可选）")
    tags: Optional[list[str]] = Field(default=None, description="新标签列表（可选,会替换全部标签）")


# ============================================================
# Tools（执行操作,有副作用）
# ============================================================

@mcp.tool()
def create_note(
    title: str,
    content: str,
    tags: list[str] = [],
    ctx: Context = None,
) -> dict:
    """创建一篇新笔记。

    Args:
        title: 笔记标题（必填,会用来生成 ID）
        content: 笔记内容,支持 Markdown 格式
        tags: 标签列表,如 ["study", "python"]。留空则不加标签
    """
    note_id = _make_id(title)

    # 处理 ID 冲突:追加序号
    base_id = note_id
    counter = 1
    while note_id in NOTES:
        note_id = f"{base_id}-{counter}"
        counter += 1

    now = _now_iso()
    note = {
        "id": note_id,
        "title": title,
        "content": content,
        "tags": tags,
        "created_at": now,
        "updated_at": now,
    }
    NOTES[note_id] = note
    _save_notes()

    logger.info(f"笔记已创建: {note_id} ({title})")
    return {"action": "created", "note": note}


@mcp.tool()
def update_note(params: UpdateNoteParams, ctx: Context = None) -> dict:
    """更新笔记的标题、内容或标签。

    只需要传要修改的字段,未传的字段保持不变。
    要删除所有标签时传 tags=[]。

    Args:
        params: UpdateNoteParams { note_id, title?, content?, tags? }
    """
    note_id = params.note_id
    if note_id not in NOTES:
        return {"error": "not_found", "id": note_id, "hint": f"笔记不存在。可用 ID: {list(NOTES.keys())}"}

    note = NOTES[note_id]
    if params.title is not None:
        note["title"] = params.title
    if params.content is not None:
        note["content"] = params.content
    if params.tags is not None:
        note["tags"] = params.tags
    note["updated_at"] = _now_iso()

    _save_notes()
    logger.info(f"笔记已更新: {note_id}")
    return {"action": "updated", "note": note}


@mcp.tool()
def delete_note(note_id: str, ctx: Context = None) -> dict:
    """删除一篇笔记。此操作不可撤销！

    Args:
        note_id: 要删除的笔记 ID
    """
    if note_id not in NOTES:
        return {"error": "not_found", "id": note_id, "hint": f"笔记不存在。可用 ID: {list(NOTES.keys())}"}

    deleted = NOTES.pop(note_id)
    _save_notes()
    logger.info(f"笔记已删除: {note_id} ({deleted['title']})")
    return {"action": "deleted", "note_id": note_id, "title": deleted["title"]}


@mcp.tool()
def search_notes(params: SearchParams) -> dict:
    """在笔记中全文搜索。支持关键词、分类过滤、大小写敏感。

    Args:
        params: SearchParams { query, max_results, category?, case_sensitive? }
    """
    results = []
    for note in NOTES.values():
        # 分类过滤
        if params.category is not None and params.category.value not in note.get("tags", []):
            continue
        # 文本匹配
        search_text = f"{note['title']} {note['content']} {' '.join(note.get('tags', []))}"
        if params.case_sensitive:
            match = params.query in search_text
        else:
            match = params.query.lower() in search_text.lower()
        if match:
            results.append({
                "id": note["id"],
                "title": note["title"],
                "tags": note["tags"],
                "updated_at": note["updated_at"],
                "snippet": note["content"][:120] + ("..." if len(note["content"]) > 120 else ""),
            })
        if len(results) >= params.max_results:
            break
    logger.info(f"搜索完成: query={params.query!r}, results={len(results)}")
    return {"query": params.query, "total": len(results), "results": results}


@mcp.tool()
def list_notes(tag: Optional[str] = None) -> dict:
    """列出所有笔记,可按标签过滤。

    Args:
        tag: 可选,按标签过滤。留空则返回全部笔记。
    """
    results = []
    for note in sorted(NOTES.values(), key=lambda n: n["updated_at"], reverse=True):
        if tag and tag.lower() not in [t.lower() for t in note.get("tags", [])]:
            continue
        results.append({
            "id": note["id"],
            "title": note["title"],
            "tags": note["tags"],
            "updated_at": note["updated_at"],
        })
    logger.info(f"列出笔记: tag={tag!r}, count={len(results)}")
    return {"filter": tag, "total": len(results), "notes": results}


# ============================================================
# Resources（暴露只读数据,URI 寻址）
# ============================================================

@mcp.resource("note://{note_id}")
def get_note(note_id: str) -> str:
    """获取笔记的 Markdown 版本。适合 LLM 向用户展示。

    URI: note://{note_id}
    示例: note://shopping
    """
    note = NOTES.get(note_id)
    if not note:
        return f"# 404: 笔记不存在\n\nID `{note_id}` 未找到。可用 ID: {', '.join(f'`{k}`' for k in NOTES.keys())}"

    tags_str = ", ".join(f"`{t}`" for t in note["tags"])
    return f"""# {note['title']}

{note['content']}

---
**ID:** `{note['id']}`
**标签:** {tags_str}
**创建:** {note['created_at']}
**更新:** {note['updated_at']}
"""


@mcp.resource("note://{note_id}/raw", mime_type="application/json")
def get_note_raw(note_id: str) -> dict:
    """获取笔记的原始 JSON 数据。适合 LLM 程序化处理。

    URI: note://{note_id}/raw
    """
    note = NOTES.get(note_id)
    if not note:
        return {"error": "not_found", "id": note_id, "available_ids": list(NOTES.keys())}
    return note


@mcp.resource("notes://all")
def list_all_notes_resource() -> str:
    """所有笔记的索引列表。LLM 可先读此资源了解全貌。

    URI: notes://all
    """
    if not NOTES:
        return "暂无笔记。"

    lines = [f"# 全部笔记 ({len(NOTES)} 篇)\n"]
    for note in sorted(NOTES.values(), key=lambda n: n["updated_at"], reverse=True):
        tags = ", ".join(note["tags"])
        lines.append(f"- **{note['title']}** [{tags}] → `note://{note['id']}`")
    return "\n".join(lines)


@mcp.resource("notes://tag/{tag_name}")
def list_notes_by_tag_resource(tag_name: str) -> str:
    """按标签过滤笔记列表。

    URI: notes://tag/{tag_name}
    示例: notes://tag/study
    """
    matches = [
        note for note in NOTES.values()
        if tag_name.lower() in [t.lower() for t in note["tags"]]
    ]
    if not matches:
        return f"没有找到标签为 `{tag_name}` 的笔记。"

    lines = [f"# {len(matches)} 篇笔记 (标签: {tag_name})\n"]
    for note in matches:
        lines.append(f"- **{note['title']}** → `note://{note['id']}` ({note['updated_at']})")
    return "\n".join(lines)


@mcp.resource("stats://summary", mime_type="application/json")
def get_stats_resource() -> dict:
    """笔记统计数据。

    URI: stats://summary
    """
    total = len(NOTES)
    total_words = sum(len(n["content"].split()) for n in NOTES.values())
    all_tags: dict[str, int] = {}
    for note in NOTES.values():
        for tag in note["tags"]:
            all_tags[tag] = all_tags.get(tag, 0) + 1
    most_used = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_notes": total,
        "total_words": total_words,
        "avg_words_per_note": round(total_words / total, 1) if total > 0 else 0,
        "tags": {tag: count for tag, count in most_used},
        "top_tags": [tag for tag, _ in most_used[:5]],
        "storage_file": str(STORAGE_FILE),
    }


# ============================================================
# Prompts（对话模板,引导 AI 思考）
# ============================================================

@mcp.prompt(
    title="审阅笔记",
    description="提供结构化审阅模板。System 消息设定审阅标准,并引用笔记 Resource。",
)
def review_note(note_id: str) -> list[PromptMessage]:
    """审阅一篇笔记的内容、结构和表达。

    结合了 system 消息（角色+标准）、user 消息（任务）和 ResourceLink（引数据）。
    """
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text="""你是一位专业的内容编辑。请审阅以下笔记,从以下维度给出反馈:

1. **内容质量**: 信息是否准确、完整、有价值？
2. **结构组织**: 层次是否清晰？Markdown 格式是否恰当？
3. **表达风格**: 语言是否简洁易懂？有无冗余？
4. **改进建议**: 具体的优化方案（至少 3 条）

对于每条建议,请具体指出修改位置和修改方式。""",
            ),
        ),
        PromptMessage(
            role="user",
            content=ResourceLink(
                type="resource_link",
                uri=f"note://{note_id}",
                name=f"笔记 {note_id}",
                mimeType="text/markdown",
                description="待审阅的笔记内容",
            ),
        ),
    ]


@mcp.prompt(
    title="创建笔记向导",
    description="交互式引导用户创建一篇结构化笔记。",
)
def new_note_wizard(
    topic: str = "",
    category: str = "",
) -> list[PromptMessage]:
    """引导用户完成结构化笔记创建流程。

    不直接创建笔记（那是 Tool 的职责）,而是生成引导对话。
    """
    topic_hint = f"主题是「{topic}」。" if topic else "请先和用户讨论确定主题。"
    category_hint = f"分类为「{category}」。\n- 所有内容统一使用该分类。" if category else "根据内容推荐合适的分类和标签。"

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""你是一位笔记创作助手,帮助用户创建高质量的结构化笔记。

## 当前状态
- {topic_hint}
- {category_hint}

## 引导流程
1. 如果主题未确定,先和用户讨论确定主题
2. 引导用户提供笔记核心内容（关键信息、想法、要点）
3. 帮助组织为清晰的结构:
   - 标题: 简洁有信息量
   - 内容: 分段,适当使用 Markdown 标题层级
   - 标签: 3-5 个关键词
4. 确认信息后,提醒用户使用 `create_note` 工具保存

## 可用的分类和工具
- 分类: work / personal / study / todo
- 保存: 使用 create_note(title, content, tags) 工具
- 查看: 读取 note://{note_id} 或 notes://all 资源

## 注意事项
- 对话式引导,一次问 1-2 个问题
- 根据已提供的信息灵活推进
- 最终笔记简洁、结构化、易于检索""",
            ),
        ),
    ]


@mcp.prompt(
    title="总结笔记",
    description="生成笔记摘要或周报。可指定标签过滤,或留空涵盖全部笔记。",
)
def summarize_notes(tag: str = "") -> list[PromptMessage]:
    """总结笔记内容。

    参数:
      tag: 按标签过滤要总结的笔记。留空则涵盖全部。
    """
    scope = f"标签为「{tag}」的所有笔记" if tag else "所有笔记"
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""你是个人知识管理助手。请总结{scope}的内容。

## 总结要求
1. **概览**: 总体涉及哪些主题和领域？
2. **要点**: 提炼关键信息和行动项
3. **关联**: 笔记之间有什么联系？
4. **建议**: 还应该补充哪些方面的笔记？

## 数据获取
- 先读取 `notes://all` 资源获取笔记索引
- 如果需要了解某篇笔记的详细内容,读取 `note://{{note_id}}` 资源
{"- 或直接读取 `notes://tag/" + tag + "` 资源按标签过滤" if tag else ""}

请在开始前先通过 Resources 获取笔记数据,然后给出总结。""",
            ),
        ),
    ]


# ============================================================
# Tool: 系统帮助
# ============================================================

@mcp.tool()
def help() -> dict:
    """查看 Smart Notes 系统的完整功能列表。

    包括所有可用的 Tools、Resources、Prompts 及其用途。
    """
    return {
        "app": "Smart Notes v1.0",
        "primitives": {
            "Tools (执行操作)": {
                "create_note(title, content, tags)": "创建新笔记",
                "update_note(params)": "更新笔记的标题/内容/标签",
                "delete_note(note_id)": "删除笔记（不可撤销）",
                "search_notes(params)": "全文搜索笔记",
                "list_notes(tag?)": "列出笔记,可按标签过滤",
            },
            "Resources (读取数据)": {
                "note://{note_id}": "Markdown 格式笔记",
                "note://{note_id}/raw": "JSON 格式笔记",
                "notes://all": "全部笔记索引",
                "notes://tag/{tag_name}": "按标签过滤笔记",
                "stats://summary": "笔记统计数据",
            },
            "Prompts (对话模板)": {
                "review_note(note_id)": "审阅笔记内容",
                "new_note_wizard(topic?, category?)": "引导创建新笔记",
                "summarize_notes(tag?)": "总结笔记内容",
            },
        },
        "design_principle": "Tool 写 → Resource 读 → Prompt 引导。三原语各司其职。",
        "storage": str(STORAGE_FILE),
        "total_notes": len(NOTES),
    }


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    logger.info(f"Smart Notes 启动 — 传输: {transport} | 笔记: {len(NOTES)} 篇 | 存储: {STORAGE_FILE}")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        logger.info("HTTP 端点: http://127.0.0.1:8000/mcp")
        mcp.run(transport="streamable-http")
    else:
        logger.error(f"未知模式: {transport},可选: stdio | streamable-http")
        sys.exit(1)
