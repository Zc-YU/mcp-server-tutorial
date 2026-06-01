"""Step 3: Tools 参数类型系统。

学习目标:
  - 基础类型 (str/int/bool) 如何自动转为 JSON Schema
  - Enum 如何限制参数可选值
  - Pydantic BaseModel 如何生成结构化参数表单
  - Optional 和默认值的区别

运行:
  uv run steps/step03_tools_basic.py                    # stdio (IDE 集成)
  uv run steps/step03_tools_basic.py streamable-http    # HTTP (多客户端)

测试:
  uv run mcp dev steps/step03_tools_basic.py            # Inspector 图形界面
  curl -X POST http://127.0.0.1:8000/mcp ...            # HTTP 调用
"""
import sys
import logging
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Tools Type System Demo",
    host="127.0.0.1",
    port=8000,
)


# ============================================================
# 1. 基础类型 — str, int, bool + 默认值
# ============================================================

@mcp.tool()
def calculator(a: int, b: int, operation: str = "add") -> dict:
    """基础计算器。支持 add / subtract / multiply / divide。

    operation 有默认值 "add"，所以是可选的。
    a 和 b 没有默认值，所以是必填的。
    """
    ops = {
        "add": lambda: a + b,
        "subtract": lambda: a - b,
        "multiply": lambda: a * b,
        "divide": lambda: a / b if b != 0 else None,
    }
    if operation not in ops:
        return {"error": f"未知操作: {operation}", "valid": list(ops.keys())}
    result = ops[operation]()
    if result is None:
        return {"error": "除数不能为 0"}
    return {"a": a, "b": b, "operation": operation, "result": result}


@mcp.tool()
def format_text(text: str, uppercase: bool = False, max_length: int = 100) -> str:
    """格式化文本。演示 bool 和 int 默认值。

    uppercase=True → 全大写
    max_length    → 截断长度
    """
    result = text.upper() if uppercase else text
    return result[:max_length]


# ============================================================
# 2. Enum — 限制参数只能选几个值
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


@mcp.tool()
def create_task(title: str, category: NoteCategory, priority: Priority = Priority.MEDIUM) -> dict:
    """创建一个任务。

    category: 从 NoteCategory 枚举中选一个值
    priority: 从 Priority 枚举中选一个，默认 medium

    LLM 会在枚举值列表里选择，不会乱传。
    """
    return {
        "id": abs(hash(title)) % 10000,
        "title": title,
        "category": category.value,
        "priority": priority.value,
        "status": "created",
    }


# ============================================================
# 3. Pydantic BaseModel — 结构化参数，最推荐
# ============================================================

class SearchParams(BaseModel):
    """搜索参数模型。每个字段的 Field(description=) LLM 都能看到。"""

    query: str = Field(description="搜索关键词，支持多词用空格分隔")
    max_results: int = Field(default=10, ge=1, le=100, description="最大结果数 1-100")
    category: Optional[NoteCategory] = Field(default=None, description="按分类过滤，None 表示全部")
    case_sensitive: bool = Field(default=False, description="是否区分大小写")


@mcp.tool()
def search_notes(params: SearchParams) -> dict:
    """用结构化参数搜索笔记。

    这是最推荐的工具定义方式:
    - BaseModel → 完整 JSON Schema
    - Field(description=) → LLM 看到每个字段的说明
    - Field(ge=, le=) → 参数约束自动纳入 Schema
    - Optional[X] → 可选字段
    """
    logger.info(f"搜索: query={params.query}, max={params.max_results}")

    # 模拟搜索结果
    mock_notes = [
        {"id": 1, "title": "Python 入门", "category": "study"},
        {"id": 2, "title": "购物清单", "category": "todo"},
        {"id": 3, "title": "项目周报模板", "category": "work"},
        {"id": 4, "title": "Pydantic 使用笔记", "category": "study"},
    ]

    results = []
    for note in mock_notes:
        # 大小写敏感匹配
        if params.case_sensitive:
            match = params.query in note["title"]
        else:
            match = params.query.lower() in note["title"].lower()
        # 分类过滤
        if match and (params.category is None or note["category"] == params.category.value):
            results.append(note)
        if len(results) >= params.max_results:
            break

    return {"query": params.query, "results": results, "total": len(results)}


# ============================================================
# 4. 对比：不同参数定义方式的 Schema 差异
# ============================================================

@mcp.tool()
def flat_params(query: str, max_results: int = 10, category: str = None) -> dict:
    """扁平参数方式 — 没有 Pydantic 的约束和描述。

    对比 search_notes，看 Inspector 里 Schema 的区别。
    category 的类型 LLM 看不到具体的允许值。
    """
    return {"query": query, "max_results": max_results, "category": category}


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    logger.info(f"启动模式: {transport} → {'stdio (IDE 子进程)' if transport == 'stdio' else 'HTTP (多客户端)'}")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        logger.info("HTTP 端点: http://127.0.0.1:8000/mcp")
        mcp.run(transport="streamable-http")
    else:
        logger.error(f"未知模式: {transport}，可选: stdio | streamable-http")
        sys.exit(1)
