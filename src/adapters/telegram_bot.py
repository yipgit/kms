import logging
import os
import re
from typing import Callable, Awaitable, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, filters, Application
from telegram.error import Conflict
from src.domain.models import RawMessage, Note
from src.adapters.tag_repository import TagRepository
from src.adapters.filesystem import FilesystemWriter

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, allowed_user_ids: List[int], 
                 message_handler: Callable[[RawMessage], Awaitable[Note]],
                 tag_repo: TagRepository,
                 fs_writer: FilesystemWriter,
                 proxy_url: Optional[str] = None,
                 pid_file: str = ".bot.pid"):
        self.token = token
        self.allowed_user_ids = allowed_user_ids
        self.process_message = message_handler
        self.tag_repo = tag_repo
        self.fs_writer = fs_writer
        self.pid_file = pid_file
        
        builder = ApplicationBuilder().token(self.token)
        if proxy_url:
            builder = builder.proxy(proxy_url)
        self.application = builder.build()
        self.application.add_error_handler(self._handle_error)
        
        # Configure heartbeat file path
        self.heartbeat_file = os.environ.get("HEARTBEAT_FILE", "/tmp/bot_heartbeat")

    async def _handle_error(self, update: Optional[object], context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the telegram.ext.Application."""
        if isinstance(context.error, Conflict):
            logger.error("Conflict error: Another instance of the bot is already running. Please ensure only one instance is active.")
        else:
            logger.error(f"Error occurred: {context.error}", exc_info=context.error)

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or update.effective_user.id not in self.allowed_user_ids:
            logger.warning(f"Unauthorized access attempt from user {update.effective_user.id if update.effective_user else 'Unknown'}")
            return

        if not update.message:
            return

        forward_from = None
        forward_date = None
        if update.message.forward_origin:
            origin = update.message.forward_origin
            forward_date = origin.date
            if origin.type == "user":
                forward_from = origin.sender_user.username or origin.sender_user.full_name
            elif origin.type == "hidden_user":
                forward_from = origin.sender_user_name
            elif origin.type in ["chat", "channel"]:
                sender = getattr(origin, "sender_chat", getattr(origin, "chat", None))
                if sender:
                    forward_from = getattr(sender, "title", getattr(sender, "username", "Unknown"))

        raw_msg = RawMessage(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            user_id=update.effective_user.id,
            text=update.message.text or update.message.caption,
            date=update.message.date,
            forward_from=forward_from,
            forward_date=forward_date,
            original_json=update.to_dict()
        )

        try:
            # Extract tags from the original message and add to repo for future use
            if raw_msg.text:
                found_tags = re.findall(r'#(\w+)', raw_msg.text)
                for tag in found_tags:
                    self.tag_repo.add_tag(tag)
            
            note = await self.process_message(raw_msg)
            
            # Auto-move if 'target:' keyword is present
            target_match = re.search(r'target:\s*(\S+)', raw_msg.text, re.IGNORECASE) if raw_msg.text else None
            if target_match:
                folder_path = target_match.group(1).strip()
                try:
                    new_abs_path = await self.fs_writer.move_note(note.absolute_path, folder_path)
                    note.absolute_path = new_abs_path
                    logger.info(f"Auto-moved note to {folder_path} based on keyword")
                except Exception as e:
                    logger.error(f"Failed to auto-move note: {e}")
            
            # Update tags from the note content (if any were extracted)
            # We need to re-extract them or pass them through. 
            # Ideally the Note object would have the tags, but it doesn't.
            # But we can just rely on the user adding more tags via UI.
            
            top_tags = self.tag_repo.get_top_tags(10)
            keyboard = self._get_note_keyboard_markup(top_tags)
            
            sent_msg = await update.message.reply_text(
                self._format_saved_message(note), reply_markup=keyboard
            )
            
            # Store file path in chat_data context mapped by message ID
            if context.chat_data is not None:
                context.chat_data[f"msg_{sent_msg.message_id}"] = note.absolute_path
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")

    @staticmethod
    def _format_saved_message(note: Note) -> str:
        """Create a compact Telegram confirmation with optional LLM enrichment."""
        lines = [f"✅ Saved: {note.filename}"]
        if note.summary:
            summary = " ".join(note.summary.split())
            if len(summary) > 900:
                summary = f"{summary[:897]}..."
            lines.extend(["", f"📝 Summary: {summary}"])
        if note.tags:
            lines.append(f"🏷 Tags: {' '.join(f'#{tag}' for tag in note.tags)}")
        return "\n".join(lines)

    def _get_tag_keyboard(self, file_path: str) -> InlineKeyboardMarkup:
        # Deprecated, logic moved to _handle_message and _get_tag_keyboard_markup
        return InlineKeyboardMarkup([])

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data == "cmd:show_folders":
            # Show list of folders
            msg_id = query.message.message_id
            file_path = context.chat_data.get(f"msg_{msg_id}")
            if not file_path:
                await query.edit_message_text(text="❌ Session expired for this note.")
                return

            folders = self.fs_writer.list_vault_directories()
            keyboard = self._get_folder_keyboard_markup(folders)
            await query.edit_message_text(text=f"{query.message.text}\nSelect folder:", reply_markup=keyboard)

        elif data.startswith("move:"):
            folder_path = data.split(":", 1)[1]
            msg_id = query.message.message_id
            file_path = context.chat_data.get(f"msg_{msg_id}")
            
            if file_path:
                try:
                    new_abs_path = await self.fs_writer.move_note(file_path, folder_path)
                    # Update the tracked path
                    context.chat_data[f"msg_{msg_id}"] = new_abs_path
                    
                    # Clean up message text to show new location
                    base_text = query.message.text.split("\nSelect folder:")[0].split("\nAdded #")[0]
                    display_path = folder_path if folder_path != "/" else "Root"
                    await query.edit_message_text(text=f"{base_text}\n📂 Moved to: {display_path}")
                    
                    # Optional: Show tags again? Or just leave it. 
                    # Let's show tags again so they can still add tags after moving.
                    top_tags = self.tag_repo.get_top_tags(10)
                    keyboard = self._get_note_keyboard_markup(top_tags)
                    await query.edit_message_reply_markup(reply_markup=keyboard)
                    
                except Exception as e:
                    logger.error(f"Failed to move note: {e}")
                    await query.edit_message_text(text=f"Failed to move: {e}")
            else:
                await query.edit_message_text(text="❌ Session expired for this note.")

        elif data.startswith("tag:"):
            tag = data.split(":", 1)[1]
            # Retrieve file path from context
            # We need to know WHICH file.
            # The message containing the buttons is `query.message`.
            msg_id = query.message.message_id
            file_path = context.chat_data.get(f"msg_{msg_id}")
            
            if file_path:
                try:
                    await self.fs_writer.append_content(file_path, f"\n#{tag}")
                    self.tag_repo.add_tag(tag)
                    # Keep existing message text but maybe update it?
                    # Current text usually starts with "✅ Saved: ..." or includes "📂 Moved to: ..."
                    # Let's just keep adding tags to the bottom.
                    await query.edit_message_text(text=f"{query.message.text}\n# Added #{tag}")
                    
                    # Re-show keyboard
                    top_tags = self.tag_repo.get_top_tags(10)
                    keyboard = self._get_note_keyboard_markup(top_tags)
                    await query.edit_message_reply_markup(reply_markup=keyboard)
                except Exception as e:
                    logger.error(f"Failed to add tag: {e}")
                    await query.edit_message_text(text=f"Failed to add tag: {e}")
            else:
                await query.edit_message_text(text="❌ Session expired for this note.")

    def _get_note_keyboard_markup(self, top_tags: List[str]) -> InlineKeyboardMarkup:
        """Main keyboard for a saved note, including tags and move button."""
        keyboard = []
        # Tag rows
        row = []
        for tag in top_tags:
            row.append(InlineKeyboardButton(f"#{tag}", callback_data=f"tag:{tag}"))
            if len(row) >= 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        # Action row
        keyboard.append([InlineKeyboardButton("📁 Move To...", callback_data="cmd:show_folders")])
        return InlineKeyboardMarkup(keyboard)

    def _get_folder_keyboard_markup(self, folders: List[str]) -> InlineKeyboardMarkup:
        """Keyboard listing available folders for moving a note."""
        keyboard = []
        row = []
        # Limit to reasonable number of folders for UI
        for folder in folders[:15]: 
            label = folder if folder != "/" else "🏠 Root"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"move:{folder}")])
            
        # Add a back button
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="move:/")]) # Or maybe just a cancel
        return InlineKeyboardMarkup(keyboard)

    def _get_tag_keyboard_markup(self, top_tags: List[str]) -> InlineKeyboardMarkup:
        # Deprecated by _get_note_keyboard_markup
        return self._get_note_keyboard_markup(top_tags)

    def _check_and_create_pid(self):
        """Check if a PID file exists and create one if not."""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process with that PID is actually running
                if os.name == 'nt':
                    # Windows specific check
                    import ctypes
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                    if handle:
                        ctypes.windll.kernel32.CloseHandle(handle)
                        raise RuntimeError(f"Bot is already running (PID: {pid}). Delete {self.pid_file} if this is an error.")
                else:
                    # Unix specific check
                    os.kill(pid, 0)
                    raise RuntimeError(f"Bot is already running (PID: {pid}). Delete {self.pid_file} if this is an error.")
            except (OSError, ValueError, ProcessLookupError):
                # Process not running or invalid PID file, proceed
                pass

        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))

    def _remove_pid(self):
        """Remove the PID file."""
        if os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
            except OSError as e:
                logger.error(f"Failed to remove PID file: {e}")
        
        if os.path.exists(self.heartbeat_file):
            try:
                os.remove(self.heartbeat_file)
            except OSError as e:
                logger.error(f"Failed to remove heartbeat file: {e}")

    async def _update_heartbeat(self, context: ContextTypes.DEFAULT_TYPE):
        """Update the heartbeat file to indicate the bot is alive."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.heartbeat_file), exist_ok=True)
            with open(self.heartbeat_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")

    def run(self):
        """Starts the bot polling."""
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self._handle_message)
        cb_handler = CallbackQueryHandler(self._handle_callback)
        
        self.application.add_handler(msg_handler)
        self.application.add_handler(cb_handler)
        
        # Run heartbeat job every 60 seconds
        if self.application.job_queue:
            self.application.job_queue.run_repeating(self._update_heartbeat, interval=60, first=1)
        else:
            logger.warning("JobQueue not available, heartbeat will not be updated.")
        
        try:
            self._check_and_create_pid()
            logger.info("Starting Telegram bot polling...")
            # drop_pending_updates=True ensures we don't process old messages on restart
            self.application.run_polling(drop_pending_updates=True)
        finally:
            self._remove_pid()
