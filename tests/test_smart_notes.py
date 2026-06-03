import unittest
from unittest.mock import patch

from src.smart_notes import server


class SmartNotesIdTests(unittest.TestCase):
    def test_make_id_transliterates_chinese_title_to_slug(self):
        self.assertEqual(server._make_id("测试笔记"), "ce-shi-bi-ji")

    def test_create_note_can_be_read_with_percent_encoded_resource_param(self):
        with (
            patch.object(server, "NOTES", {}),
            patch.object(server, "_save_notes"),
            patch.object(server, "_now_iso", return_value="2026-06-02T15:47:28Z"),
        ):
            result = server.create_note(
                title="测试笔记",
                content="这是通过 MCP 创建的测试笔记。",
                tags=["test", "study"],
            )

            self.assertEqual(result["action"], "created")
            self.assertEqual(result["note"]["id"], "ce-shi-bi-ji")

            text = server.get_note("ce-shi-bi-ji")
            self.assertIn("**ID:** `ce-shi-bi-ji`", text)

            server.NOTES["测试笔记"] = {
                "id": "测试笔记",
                "title": "测试笔记",
                "content": "旧数据兼容。",
                "tags": ["test"],
                "created_at": "2026-06-02T15:47:28Z",
                "updated_at": "2026-06-02T15:47:28Z",
            }
            encoded_text = server.get_note("%E6%B5%8B%E8%AF%95%E7%AC%94%E8%AE%B0")
            self.assertIn("旧数据兼容。", encoded_text)

    def test_new_note_wizard_keeps_resource_uri_template_literal(self):
        messages = server.new_note_wizard(topic="MCP 学习", category="study")

        self.assertEqual(len(messages), 1)
        self.assertIn("主题是「MCP 学习」", messages[0].content.text)
        self.assertIn("note://{note_id}", messages[0].content.text)


if __name__ == "__main__":
    unittest.main()
