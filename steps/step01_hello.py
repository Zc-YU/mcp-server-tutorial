"""Step 1: 最小 MCP Server — 一个工具 + stdio 传输层。

学习目标:
  - FastMCP 是什么
  - @mcp.tool() 如何注册工具
  - 类型提示如何变成 JSON Schema
  - stdio 传输层如何工作
  - 为什么日志只能去 stderr

运行: uv run steps/step01_hello.py
测试: mcp dev steps/step01_hello.py
"""
import sys
import logging
from mcp.server.fastmcp import FastMCP

# 关键: 所有日志去 stderr，stdout 是 JSON-RPC 通道
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Hello World Server")

# --- 基础工具 ---
@mcp.tool()
def greet(name: str) -> str:
    """返回一句问候语。参数 name 是你要问候的人的名字。"""
    logger.info(f"greet 被调用, name={name}")
    return f"Hello, {name}! 欢迎来到 MCP 的世界。"


# --- 带多个参数的工具 ---
@mcp.tool()
def add(a: int, b: int) -> int:
    """计算两个整数的和。"""
    return a + b


# --- 带默认值的工具 ---
@mcp.tool()
def repeat(message: str, times: int = 3) -> str:
    """将消息重复指定次数。times 默认为 3。"""
    return (message + "\n") * times


if __name__ == "__main__":
    logger.info("Hello World Server 启动中...")
    # stdio: 标准输入输出传输
    #   - 客户端将 Server 作为子进程启动
    #   - stdin/stdout 走 JSON-RPC 消息
    #   - 所有 print() 都会破坏协议！
    mcp.run(transport="stdio")
