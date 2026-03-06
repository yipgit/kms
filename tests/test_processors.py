import unittest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from src.pipeline.processors import RawMessageToContent, ContentToNote, SaveNote, FetchURLContent
from src.domain.models import RawMessage, Content, Note

class TestProcessors(unittest.IsolatedAsyncioTestCase):
    async def test_raw_message_to_content(self):
        processor = RawMessageToContent()
        now = datetime.now()
        msg = RawMessage(
            chat_id=1, message_id=1, user_id=1,
            text="Check https://google.com\nLine 2 #tag1 #tag2",
            date=now
        )
        
        content = await processor.process(msg)
        
        self.assertEqual(content.source_url, "https://google.com")
        self.assertEqual(content.title, "Check https://google.com")
        self.assertEqual(content.tags, ["tag1", "tag2"])
        self.assertEqual(content.body, msg.text)

    async def test_raw_message_to_content_url_only(self):
        processor = RawMessageToContent()
        now = datetime.now()
        msg = RawMessage(
            chat_id=1, message_id=1, user_id=1,
            text="https://google.com",
            date=now
        )
        
        content = await processor.process(msg)
        
        self.assertEqual(content.source_url, "https://google.com")
        # Should NOT be the URL
        self.assertNotEqual(content.title, "https://google.com")
        self.assertTrue(content.title.startswith("Note "))

    async def test_content_to_note(self):
        processor = ContentToNote()
        content = Content(
            title="My Note",
            body="Body text",
            source_url="http://example.com",
            tags=["foo", "bar"],
            created_at=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        note = await processor.process(content)
        
        self.assertEqual(note.filename, "My Note")
        self.assertIn("---", note.content)
        self.assertIn('title: "My Note"', note.content)
        self.assertIn("source: http://example.com", note.content)
        self.assertIn("  - foo", note.content)
        self.assertIn("  - bar", note.content)
        self.assertIn("# My Note", note.content)
        self.assertIn("Body text", note.content)

    async def test_save_note(self):
        mock_writer = MagicMock()
        mock_writer.write_note = AsyncMock(return_value="/abs/path/file.md")
        
        processor = SaveNote(mock_writer)
        note = Note(filename="file.md", content="content")
        
        result = await processor.process(note)
        
        mock_writer.write_note.assert_called_once_with(note)
        self.assertEqual(result.absolute_path, "/abs/path/file.md")

    async def test_fetch_url_content_jina_success(self):
        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_response = MagicMock()
            mock_response.text = "# Test Page\nClean Markdown Content"
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            
            processor = FetchURLContent(proxy_url="http://proxy:8080")
            content = Content(source_url="http://example.com", title="Note 2023-01-01", body="Original body")
            
            result = await processor.process(content)
            
            # Verify Jina Reader was tried first
            mock_client.get.assert_called_once_with("https://r.jina.ai/http://example.com")
            self.assertEqual(result.title, "Test Page")
            self.assertIn("Clean Markdown Content", result.body)

    async def test_fetch_url_content_x_api_fallback(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            
            # 1. Jina Reader response (fail)
            jina_response = MagicMock()
            jina_response.raise_for_status.side_effect = Exception("Jina Down")
            
            # 2. X.com JSON API response (success)
            api_response = MagicMock()
            api_response.json.return_value = {
                "text": "Tweet content here",
                "user_screen_name": "testuser"
            }
            api_response.raise_for_status = MagicMock()
            
            mock_client.get.side_effect = [jina_response, api_response]
            
            processor = FetchURLContent()
            content = Content(source_url="https://x.com/user/status/123", title="Note", body="Original body")
            
            result = await processor.process(content)
            
            self.assertEqual(mock_client.get.call_count, 2)
            # Verify it called api.vxtwitter.com
            self.assertIn("api.vxtwitter.com", mock_client.get.call_args_list[1][0][0])
            self.assertEqual(result.title, "testuser on X: \"Tweet content here\"")
            self.assertIn("Tweet content here", result.body)

    async def test_fetch_url_content_meta_fallback(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            
            # Jina fail
            jina_fail = MagicMock()
            jina_fail.raise_for_status.side_effect = Exception("Fail")
            
            # Direct success with meta tags
            direct_success = MagicMock()
            direct_success.text = '<html><title>Page Title</title><meta property="og:description" content="Meta Description Content"></html>'
            direct_success.raise_for_status = MagicMock()
            
            mock_client.get.side_effect = [jina_fail, direct_success]
            
            processor = FetchURLContent()
            content = Content(source_url="http://example.com", title="Note 2023", body="Original body")
            
            result = await processor.process(content)
            
            self.assertEqual(mock_client.get.call_count, 2)
            self.assertEqual(result.title, "Page Title")
            self.assertIn("Meta Description Content", result.body)
