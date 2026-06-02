"""Step 7: Prompts（提示模板）— MCP 的第三大原语。

学习目标:
  - @mcp.prompt() 如何注册提示模板
  - PromptMessage / TextContent 的用法
  - 多消息提示（system + user role）
  - 提示中引用 Resource（ResourceLink / EmbeddedResource）
  - Prompts 和 Tools / Resources 的核心区别

关键概念:
  Prompts = Server 对 Client 说"我可以帮用户生成这些类型的提示词"
  - Tools:  服务端执行代码 → 返回数据（副作用）
  - Resources: 服务端暴露数据 → 返回内容（只读）
  - Prompts:  服务端提供模板 → 返回对话结构（引导思考）

运行: uv run steps/step07_prompts.py
测试: uv run mcp dev steps/step07_prompts.py
"""
import sys
import logging
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent, EmbeddedResource, ResourceLink

logging.basicConfig(
    stream=sys.stderr, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Prompts Demo",
    host="127.0.0.1",
    port=8000,
)


# ============================================================
# 1. 最简单的 Prompt — 单条消息 + 一个参数
# ============================================================

@mcp.prompt(
    title="问候用户",
    description="根据用户名字生成一条友好的问候提示。演示最简单的 Prompt 结构。",
)
def greet_user(name: str) -> list[PromptMessage]:
    """生成问候提示词。

    最简形式: 一条 user 消息，参数直接拼接到文本中。
    LLM 看到这个 Prompt 后会用友好的语气和用户对话。
    """
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"请用友好的语气向 {name} 打招呼，并介绍 MCP 的三大原语（Tools、Resources、Prompts）各一句话。",
            ),
        ),
    ]


# ============================================================
# 2. 多消息 Prompt — system 设定角色 + user 描述任务
# ============================================================

@mcp.prompt(
    title="写作审阅",
    description="提供结构化的写作审阅模板。System 消息设定审阅标准，User 消息传入待审文本。",
)
def review_writing(text: str, focus: str = "整体质量") -> list[PromptMessage]:
    """审阅一段文字。

    多消息 Prompt 的典型用法:
      - system: 设定 AI 的角色、行为准则、输出格式
      - user:   传入具体任务和待处理数据

    参数:
      text: 待审阅的文字内容
      focus: 审阅重点（如"语法"、"逻辑"、"风格"、"整体质量"）
    """
    return [ 
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""你是一位专业的内容编辑，擅长中文写作审阅。

## 审阅重点
{focus}

## 审阅标准
- 发现并修正语法错误和拼写错误
- 评估逻辑结构和段落衔接
- 检查用词是否准确、表达是否清晰
- 给出具体的改进建议，而非笼统评价

## 输出格式
1. **总体评价**（1-2 句）
2. **具体问题**（逐条列出，标明位置）
3. **改进建议**（具体可操作）

请严格按照以上要求审阅用户提供的文字。""",
            ),
        ),
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"请审阅以下文字:\n\n---\n{text}\n---",
            ),
        ),
    ]


# ============================================================
# 3. 翻译 Prompt — 另一组 system + user 示例
# ============================================================

@mcp.prompt(
    title="内容翻译",
    description="提供内容翻译的提示模板。演示不同语言和风格参数的组合。",
)
def translate_content(
    text: str,
    target_language: str = "英文",
    style: str = "自然流畅",
) -> list[PromptMessage]:
    """将文本翻译成目标语言。

    演示 Prompt 如何通过参数控制输出风格。
    同一个模板 + 不同参数 = 不同的翻译结果。

    参数:
      text: 待翻译的文本
      target_language: 目标语言
      style: 翻译风格（"自然流畅"、"正式严谨"、"口语化"）
    """
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""你是一位专业翻译，精通多门语言。

## 翻译要求
- 目标语言: {target_language}
- 翻译风格: {style}
- 保持原文的段落结构和格式
- 专业术语翻译准确
- 如果是"正式严谨"风格，避免使用口语化表达
- 如果是"口语化"风格，使用日常自然的表达方式

## 输出格式
先输出译文，然后在末尾附上简短的「翻译说明」（1-2 句，说明处理了哪些难点）。""",
            ),
        ),
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"请翻译以下内容:\n\n---\n{text}\n---",
            ),
        ),
    ]


# ============================================================
# 4. Prompt 引用 Resource — ResourceLink 和 EmbeddedResource
# ============================================================

@mcp.prompt(
    title="分析笔记",
    description="生成分析笔记内容的提示。演示如何在 Prompt 中引用 MCP Resource。",
)
def analyze_note(note_id: str) -> list[PromptMessage]:
    """分析指定笔记的内容。

    两种引用 Resource 的方式:

    方式 A — ResourceLink（推荐）:
      只传 URI，客户端自行读取内容。
      Prompt 本身不包含数据，轻量且解耦。
      → content=ResourceLink(type="resource_link", uri=f"note://{note_id}", ...)

    方式 B — EmbeddedResource:
      在 Prompt 中直接嵌入资源内容。
      适合内容在生成 Prompt 时就已知的场景。
      → content=EmbeddedResource(type="resource", resource=...)

    这里演示方式 A — ResourceLink。
    """
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text="""你是一位知识管理专家。请分析以下笔记的内容，并给出:

1. **内容摘要**（2-3 句概括核心信息）
2. **关键知识点**（用 bullet points 列出 3-5 个要点）
3. **关联建议**（基于内容主题，建议补充哪些相关知识或标签）
4. **改进建议**（笔记结构或表达的优化建议）

请保持简洁实用，每条建议都要具体可操作。""",
            ),
        ),
        PromptMessage(
            role="user",
            content=ResourceLink(
                type="resource_link",
                uri=f"note://{note_id}",
                name=f"笔记 {note_id}",
                mimeType="text/markdown",
                description="待分析的笔记内容，请先读取此资源",
            ),
        ),
    ]


# ============================================================
# 5. 笔记创建引导 Prompt — 引导用户提供结构化信息
# ============================================================

@mcp.prompt(
    title="创建笔记向导",
    description="交互式引导用户创建一篇新笔记。演示如何用 Prompt 引导结构化输入。",
)
def new_note_wizard(
    topic: str = "",
    category: str = "",
) -> list[PromptMessage]:
    """引导用户创建一篇结构化笔记。

    这是 Prompt 的典型用途 —— 不是执行操作（那是 Tool 的职责），
    而是提供一个结构化的对话起点，引导用户补充必要信息。

    参数:
      topic: 笔记主题（可选，留空表示需要引导用户确定）
      category: 笔记分类（可选）
    """
    topic_hint = f"主题是「{topic}」。" if topic else "请先引导用户确定笔记主题。"
    category_hint = f"分类为「{category}」。\n- 所有笔记统一使用该分类。" if category else "根据内容推荐合适的分类。"

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""你是一位笔记创作助手，帮助用户创建高质量的结构化笔记。

## 当前状态
- {topic_hint}
- {category_hint}

## 引导流程
1. 如果主题未确定，先和用户讨论确定主题
2. 引导用户提供笔记的核心内容（关键信息、想法、要点）
3. 帮助用户将内容组织为清晰的结构:
   - 标题（简洁有信息量）
   - 核心内容（分段，适当使用标题层级）
   - 标签（3-5 个关键词）
4. 确认所有信息后，提醒用户使用 create_note 工具保存

## 注意事项
- 用对话式引导，不要一次问太多问题
- 根据用户已提供的信息灵活推进流程
- 最终笔记应该简洁、结构化、易于检索""",
            ),
        ),
    ]


# ============================================================
# Tool: 查看当前 Server 有哪些 Prompts
# ============================================================

@mcp.tool()
def list_available_prompts() -> dict:
    """列出本 Server 提供的所有 Prompt 模板及其用途。

    这是一个 Tool（不是 Prompt），
    LLM 可以通过它快速了解有哪些 Prompt 模板可用。
    """
    return {
        "prompts": [
            {
                "name": "greet_user",
                "description": "问候用户并介绍 MCP 三大原语",
                "parameters": ["name: str"],
                "use_case": "用户初次接触 MCP 时",
            },
            {
                "name": "review_writing",
                "description": "审阅文字内容",
                "parameters": ["text: str", "focus: str = '整体质量'"],
                "use_case": "用户需要编辑/审阅文章时",
            },
            {
                "name": "translate_content",
                "description": "翻译文本到目标语言",
                "parameters": ["text: str", "target_language: str = '英文'", "style: str = '自然流畅'"],
                "use_case": "用户需要翻译内容时",
            },
            {
                "name": "analyze_note",
                "description": "分析指定笔记的内容（引用 Resource）",
                "parameters": ["note_id: str"],
                "use_case": "用户需要深入分析某篇笔记时",
            },
            {
                "name": "new_note_wizard",
                "description": "引导用户创建新笔记",
                "parameters": ["topic: str = ''", "category: str = ''"],
                "use_case": "用户想创建笔记但不知道如何组织时",
            },
        ],
        "tip": "在 Claude Code 中可以用 /prompt <name> 或让 LLM 自动选择合适的 Prompt",
    }


# ============================================================
# Tool: Prompts vs Tools vs Resources 对比实验
# ============================================================

@mcp.tool()
def compare_primitives() -> dict:
    """对比 MCP 三大原语的设计意图和适用场景。

    帮助理解什么时候用 Tool、什么时候用 Resource、什么时候用 Prompt。
    """
    return {
        "三大原语": {
            "Tools": {
                "做什么": "服务端执行代码，完成操作",
                "返回": "执行结果（数据）",
                "副作用": "有（创建、修改、删除）",
                "类比": "POST / PUT / DELETE",
                "示例": "create_note, search_notes, calculator",
                "LLM视角": "\"我可以调用这个函数来完成用户要的操作\"",
            },
            "Resources": {
                "做什么": "服务端暴露只读数据",
                "返回": "资源内容（文本/JSON/二进制）",
                "副作用": "无（只读）",
                "类比": "GET",
                "示例": "note://shopping, config://app, stats://summary",
                "LLM视角": "\"我可以读取这个 URI 获取上下文数据\"",
            },
            "Prompts": {
                "做什么": "服务端提供对话模板",
                "返回": "结构化消息列表（system/user/assistant）",
                "副作用": "无（不修改数据）",
                "类比": "邮件模板 / 文档模板",
                "示例": "review_writing, translate_content, new_note_wizard",
                "LLM视角": "\"服务器建议我这样引导用户或组织对话\"",
            },
        },
        "决策指南": {
            "AI 需要执行操作（创建/修改/删除/计算）": "→ Tool",
            "AI 需要读取已有数据（获取上下文）": "→ Resource",
            "用户需要结构化的对话起点（引导工作流）": "→ Prompt",
        },
    }


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
