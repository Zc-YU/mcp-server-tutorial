"""Smart Notes Manager — 完整的 MCP Server 示例。

整合了 MCP 三大原语:
- Tools → create_note, update_note, delete_note, search_notes, list_notes
- Resources → note://{id}, notes://all, notes://tag/{tag}, stats://summary
- Prompts → review_note, new_note_wizard, summarize_notes

运行:
  uv run python src/smart_notes/server.py
  uv run mcp dev src/smart_notes/server.py
"""

from src.smart_notes.server import mcp

__all__ = ["mcp"]
