import unittest
import os
from unittest.mock import patch, mock_open, MagicMock
from src.adapters.filesystem import FilesystemWriter
from src.domain.models import Note

class TestFilesystemWriter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.vault_path = "/vault"
        
    @patch("os.makedirs")
    @patch("os.path.exists")
    def test_init_creates_dir(self, mock_exists, mock_makedirs):
        mock_exists.return_value = False
        FilesystemWriter(self.vault_path)
        mock_makedirs.assert_called_with(self.vault_path)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    async def test_write_note_new_file(self, mock_makedirs, mock_exists, mock_file):
        # Setup: Vault exists, file does not exist
        mock_exists.side_effect = lambda p: p == self.vault_path
        
        writer = FilesystemWriter(self.vault_path)
        note = Note(filename="test", content="content")
        
        path = await writer.write_note(note)
        
        expected_path = os.path.join(self.vault_path, "test.md")
        self.assertEqual(path, expected_path)
        mock_file.assert_called_with(expected_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_with("content")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    async def test_write_note_collision(self, mock_makedirs, mock_exists, mock_file):
        # Setup: Vault exists, test.md exists, test_1.md does not
        def exists_side_effect(path):
            if path == self.vault_path: return True
            if path.endswith("test.md"): return True
            return False
        mock_exists.side_effect = exists_side_effect
        
        writer = FilesystemWriter(self.vault_path)
        note = Note(filename="test", content="content")
        
        path = await writer.write_note(note)
        
        expected_path = os.path.join(self.vault_path, "test_1.md")
        self.assertEqual(path, expected_path)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    async def test_append_content(self, mock_exists, mock_file):
        mock_exists.return_value = True
        writer = FilesystemWriter(self.vault_path)
        
        await writer.append_content("/path/file.md", "more")
        
        mock_file.assert_called_with("/path/file.md", 'a', encoding='utf-8')
        mock_file().write.assert_called_with("more")

    @patch("os.makedirs")
    @patch("os.path.exists")
    async def test_append_content_missing(self, mock_exists, mock_makedirs):
        mock_exists.return_value = False
        writer = FilesystemWriter(self.vault_path)
        
        with self.assertRaises(FileNotFoundError):
            await writer.append_content("/path/missing.md", "more")
