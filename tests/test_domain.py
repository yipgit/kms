import unittest
from datetime import datetime
from src.domain.models import RawMessage, Content, Note

class TestDomainModels(unittest.TestCase):
    def test_raw_message_instantiation(self):
        now = datetime.now()
        msg = RawMessage(
            chat_id=1,
            message_id=2,
            user_id=3,
            text="hello",
            date=now
        )
        self.assertEqual(msg.chat_id, 1)
        self.assertEqual(msg.text, "hello")
        self.assertEqual(msg.date, now)
        self.assertEqual(msg.original_json, {})

    def test_content_instantiation(self):
        content = Content(title="Test", body="Body")
        self.assertEqual(content.title, "Test")
        self.assertEqual(content.body, "Body")
        self.assertEqual(content.tags, [])
        self.assertIsInstance(content.created_at, datetime)

    def test_note_instantiation(self):
        note = Note(filename="file.md", content="# Hi")
        self.assertEqual(note.filename, "file.md")
        self.assertEqual(note.content, "# Hi")
        self.assertEqual(note.path, "")
        self.assertIsNone(note.absolute_path)
