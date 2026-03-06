import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from src.adapters.telegram_bot import TelegramBot
from src.domain.models import RawMessage, Note

class TestTelegramBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_handler = AsyncMock()
        self.mock_repo = MagicMock()
        self.mock_repo.get_top_tags.return_value = ["tag1"]
        self.mock_writer = MagicMock()
        
        # Completely mock ApplicationBuilder and the Application it builds
        self.mock_app = MagicMock()
        self.mock_storage = MagicMock() # Mock storage for chat_data
        
        # Setup mock context
        self.context = MagicMock()
        self.context.chat_data = {}
        
        # Mock Persistence to avoid internal errors if accessed
        self.mock_app.persistence = MagicMock()
        
        with patch("src.adapters.telegram_bot.ApplicationBuilder") as mock_builder:
            mock_builder.return_value.token.return_value.persistence.return_value.build.return_value = self.mock_app
            # Simplified build chain mocking
            mock_builder.return_value.token.return_value.build.return_value = self.mock_app

            self.bot = TelegramBot(
                token="token",
                allowed_user_ids=[123],
                message_handler=self.mock_handler,
                tag_repo=self.mock_repo,
                fs_writer=self.mock_writer
            )
            # Inject our mock app directly to avoid internal build logic issues
            self.bot.app = self.mock_app

    async def test_handle_message_authorized(self):
        update = MagicMock()
        update.effective_user.id = 123
        update.effective_chat.id = 111
        update.message.text = "hello"
        update.message.date = "now"
        context = MagicMock()
        context.chat_data = {}
        
        # Mock handler return
        note = Note(filename="file.md", content="content", absolute_path="/path/file.md")
        self.mock_handler.return_value = note
        
        # Mock reply
        update.message.reply_text = AsyncMock()
        update.message.reply_text.return_value.message_id = 999
        
        await self.bot._handle_message(update, context)
        
        self.mock_handler.assert_called_once()
        update.message.reply_text.assert_called_once()
        self.assertEqual(context.chat_data["msg_999"], "/path/file.md")

    async def test_handle_message_unauthorized(self):
        update = MagicMock()
        update.effective_user.id = 999 # Not allowed
        context = MagicMock()
        
        await self.bot._handle_message(update, context)
        
        self.mock_handler.assert_not_called()

    async def test_handle_callback_add_tag(self):
        update = MagicMock()
        query = update.callback_query
        query.data = "tag:newtag"
        query.message.message_id = 999
        query.message.text = "Saved"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        
        context = MagicMock()
        context.chat_data = {"msg_999": "/path/file.md"}
        
        self.mock_writer.append_content = AsyncMock()
        
        await self.bot._handle_callback(update, context)
        
        self.mock_writer.append_content.assert_called_with("/path/file.md", "\n#newtag")
        self.mock_repo.add_tag.assert_called_with("newtag")
        query.edit_message_text.assert_called()

    async def test_handle_message_forwarded(self):
        update = MagicMock()
        update.effective_user.id = 123
        update.effective_chat.id = 111
        update.message.text = "forwarded message"
        update.message.date = datetime.now()
        
        # Mock forward_origin for a user
        origin = MagicMock()
        origin.type = "user"
        origin.sender_user.username = "sender_user"
        origin.date = datetime.now()
        update.message.forward_origin = origin
        
        context = MagicMock()
        context.chat_data = {}
        
        note = Note(filename="file.md", content="content", absolute_path="/path/file.md")
        self.mock_handler.return_value = note
        update.message.reply_text = AsyncMock()
        update.message.reply_text.return_value.message_id = 999
        
        await self.bot._handle_message(update, context)
        
        # Verify that RawMessage was constructed with forward info
        call_args = self.mock_handler.call_args[0][0]
        self.assertEqual(call_args.forward_from, "sender_user")
        self.assertEqual(call_args.forward_date, origin.date)

    async def test_handle_message_not_forwarded(self):
        update = MagicMock()
        update.effective_user.id = 123
        update.effective_chat.id = 111
        update.message.text = "normal message"
        update.message.date = datetime.now()
        update.message.forward_origin = None # Explicitly not forwarded
        
        context = MagicMock()
        context.chat_data = {}
        
        note = Note(filename="file.md", content="content", absolute_path="/path/file.md")
        self.mock_handler.return_value = note
        update.message.reply_text = AsyncMock()
        
        await self.bot._handle_message(update, context)
        
        call_args = self.mock_handler.call_args[0][0]
        self.assertIsNone(call_args.forward_from)
        self.assertIsNone(call_args.forward_date)
