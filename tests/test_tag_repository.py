import unittest
import json
from unittest.mock import patch, mock_open
from src.adapters.tag_repository import TagRepository

class TestTagRepository(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data='{"tag1": 5, "tag2": 3}')
    @patch("os.path.exists")
    def test_load(self, mock_exists, mock_file):
        mock_exists.return_value = True
        repo = TagRepository("tags.json")
        self.assertEqual(repo._tags, {"tag1": 5, "tag2": 3})

    @patch("os.path.exists")
    def test_load_missing(self, mock_exists):
        mock_exists.return_value = False
        repo = TagRepository("tags.json")
        self.assertEqual(repo._tags, {})

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_add_tag(self, mock_exists, mock_file):
        mock_exists.return_value = False
        repo = TagRepository("tags.json")
        
        repo.add_tag("#new")
        self.assertEqual(repo._tags["new"], 1)
        
        repo.add_tag("new")
        self.assertEqual(repo._tags["new"], 2)
        
        # Check save called
        mock_file.assert_called_with("tags.json", 'w', encoding='utf-8')

    def test_get_top_tags(self):
        repo = TagRepository("dummy")
        repo._tags = {"a": 10, "b": 5, "c": 20, "d": 1}
        
        top = repo.get_top_tags(2)
        self.assertEqual(top, ["c", "a"])
