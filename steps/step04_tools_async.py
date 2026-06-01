"""Step 4: 异步工具 + Context 上下文注入。

学习目标:
  - Context 如何自动注入到工具函数
  - ctx.info/debug/warning/error — 日志发送到客户端
  - ctx.report_progress — 进度条上报
  - 错误处理：如何优雅地失败
  - async/await 在 MCP 中的正确用法

关键规则:
  - Context 通过类型注解自动注入，参数名叫什么都行
  - 必须设默认值 None：ctx: Context = None
  - 所有 ctx 方法都是 async，必须 await
  - 不要用 time.sleep()，用 await asyncio.sleep()

运行:
  uv run steps/step04_tools_async.py                    # stdio (IDE 集成)
  uv run steps/step04_tools_async.py streamable-http    # HTTP (多客户端)

测试:
  uv run mcp dev steps/step04_tools_async.py            # Inspector 图形界面
  curl -X POST http://127.0.0.1:8000/mcp ...            # HTTP 调用
"""
import sys
import asyncio
import logging
from mcp.server.fastmcp import FastMCP, Context

logging.basicConfig(
    stream=sys.stderr, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Async Tools Demo",
    host="127.0.0.1",
    port=8000,
)


# ============================================================
# 1. Context 注入 — 日志发送到客户端
# ============================================================

@mcp.tool()
async def file_processor(file_path: str, ctx: Context = None) -> str:
    """模拟处理文件。Context 自动注入，不需要手动传。

    参数名叫 ctx/file_ctx/session 都可以，只有类型 Context 重要。
    必须设默认值 None，否则 MCP 不知道这是可注入的上下文。
    """
    # 日志会发送到客户端（LLM 在对话中能看到）
    await ctx.info(f"开始处理文件: {file_path}")
    await ctx.debug(f"调试信息: 文件路径标准化中...")

    # 验证
    if not file_path.endswith(".md"):
        await ctx.warning(f"非 Markdown 文件: {file_path}，可能无法解析")
        await ctx.error("文件格式不支持")
        raise ValueError(f"不支持的文件格式: 仅限 .md 文件")

    await ctx.info("文件验证通过 ✓")
    return f"处理完成: {file_path}"


# ============================================================
# 2. 进度上报 — 长任务的通知机制
# ============================================================

@mcp.tool()
async def batch_operation(steps: int = 10, ctx: Context = None) -> dict:
    """模拟一个耗时的批量操作，上报进度。

    ctx.report_progress(current, total):
      - current: 当前进度
      - total: 总量
      - 客户端看到进度条 (0% → 100%)
    """
    await ctx.info(f"批量操作启动，共 {steps} 步")

    for i in range(steps):
        # 模拟耗时工作
        await asyncio.sleep(0.3)

        # 上报进度 (current 从 1 开始)
        await ctx.report_progress(i + 1, steps)

        # 每 3 步发一条日志
        if (i + 1) % 3 == 0:
            await ctx.info(f"里程碑: {i + 1}/{steps} 完成")

    await ctx.report_progress(steps, steps)
    await ctx.info("批量操作全部完成 ✓")

    return {"total_steps": steps, "status": "completed", "success": True}


# ============================================================
# 3. 错误处理 — 三种错误模式
# ============================================================

@mcp.tool()
async def safe_divide(a: float, b: float, ctx: Context = None) -> dict:
    """安全除法，演示多种错误处理方式。"""
    await ctx.debug(f"计算 {a} / {b}")

    if b == 0:
        await ctx.error("被除数为 0，返回默认值")
        # 方式 1: 优雅降级，返回特殊值
        return {"result": None, "error": "除数不能为 0", "status": "degraded"}

    return {"result": a / b, "status": "success"}


@mcp.tool()
async def risky_operation(should_fail: bool = False, ctx: Context = None) -> str:
    """演示异常在 MCP 中如何传递到客户端。

    should_fail=True 时故意抛出异常，
    LLM 会收到错误信息，可以据此调整行为。
    """
    await ctx.info(f"risky_operation 启动 (should_fail={should_fail})")

    if should_fail:
        await ctx.error("操作即将失败!")
        # 方式 2: 抛异常 — LLM 会收到错误消息
        raise RuntimeError("模拟的操作失败：数据库连接超时")

    return "操作成功!"


# ============================================================
# 4. Context 方法速查
# ============================================================

@mcp.tool()
async def context_demo(ctx: Context = None) -> dict:
    """演示 Context 的所有方法。运行后在 Inspector 观察日志面板。"""
    # 不同级别的日志
    await ctx.debug("这是 debug 日志 — 调试用")
    await ctx.info("这是 info 日志 — 一般信息")
    await ctx.warning("这是 warning 日志 — 有风险")
    # 不调 error，因为这不是错误状态

    # 进度上报
    await ctx.report_progress(1, 3)
    await asyncio.sleep(0.2)
    await ctx.report_progress(2, 3)
    await asyncio.sleep(0.2)
    await ctx.report_progress(3, 3)

    return {
        "context_methods": {
            "日志": ["debug", "info", "warning", "error"],
            "进度": ["report_progress(current, total)"],
            "资源访问": ["read_resource(uri)"],
        },
        "hint": "查看 Inspector 的 Log/Trace 面板确认日志是否显示",
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
