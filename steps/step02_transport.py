"""Step 2: 三种传输模式演示。

学习目标:
  - stdio: 子进程通信 (Claude Code / VS Code / Cursor 用这个)
  - SSE (Server-Sent Events): 已弃用，了解即可
  - Streamable HTTP: 新式 HTTP 传输，Web 和多客户端场景

关键区别:
  - stdio: 客户端启动 Server 作为子进程，每客户端一个进程
  - Streamable HTTP: Server 独立运行在端口上，多客户端共享一个进程

用法:
  uv run steps/step02_transport.py                # 默认 stdio
  uv run steps/step02_transport.py streamable-http # HTTP 模式 (监听 :8000)
  uv run steps/step02_transport.py sse             # SSE 模式 (已弃用)
"""
import sys
import logging
from mcp.server.fastmcp import FastMCP

# 所有日志去 stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

def create_mcp(transport: str) -> FastMCP:
    """根据传输模式创建 FastMCP 实例。

    host/port 在 FastMCP 构造时指定（不是 run()），
    它们只对 SSE/Streamable HTTP 有效，stdio 模式下被忽略。
    """
    return FastMCP(
        "Transport Demo Server",
        host="127.0.0.1",
        port=8000,
    )


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def echo(message: str) -> str:
        """回显输入的消息。"""
        logger.info(f"echo: {message}")
        return f"Echo: {message}"

    @mcp.tool()
    def server_info() -> dict:
        """返回当前服务器信息。"""
        return {
            "name": "Transport Demo Server",
            "version": "1.0.0",
            "protocol": "MCP (JSON-RPC 2.0)",
        }


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    logger.info(f"启动模式: {transport}")

    mcp = create_mcp(transport)

    if transport == "stdio":
        # stdio: AI IDE 通过子进程启动
        #   - 写 stdout = 发 JSON-RPC 响应
        #   - 读 stdin  = 收 JSON-RPC 请求
        #   - 写 stderr = 日志（客户端会显示）
        register_tools(mcp)
        mcp.run(transport="stdio")

    elif transport == "streamable-http":
        # Streamable HTTP: 独立进程监听端口
        #   多客户端可共享一个 Server 进程
        logger.info("Streamable HTTP 模式: http://127.0.0.1:8000/mcp")
        register_tools(mcp)
        mcp.run(transport="streamable-http")

    elif transport == "sse":
        # SSE: 已被 streamable-http 取代
        logger.warning("SSE 已弃用，建议使用 streamable-http")
        register_tools(mcp)
        mcp.run(transport="sse")

    else:
        logger.error(f"未知传输模式: {transport}")
        logger.info("可用: stdio | streamable-http | sse")
        sys.exit(1)
