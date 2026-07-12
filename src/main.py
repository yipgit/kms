import sys
import os
from pathlib import Path

# Add project root to sys.path to resolve 'src' module
sys.path.append(str(Path(__file__).parent.parent))

import logging
import asyncio
from src.config import Config
from src.adapters.telegram_bot import TelegramBot
from src.adapters.filesystem import FilesystemWriter
from src.pipeline.core import Pipeline
from src.pipeline.processors import (
    ContentToNote,
    EnrichContent,
    FetchURLContent,
    RawMessageToContent,
    SaveNote,
)
from src.adapters.tag_repository import TagRepository
from src.adapters.llm import create_llm_provider
from src.domain.models import RawMessage

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # 1. Load and validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # 2. Initialize Adapters
    fs_writer = FilesystemWriter(Config.VAULT_PATH)
    tag_repo = TagRepository(os.path.join(Config.VAULT_PATH, "tags.json"))
    
    # 3. Initialize Pipeline
    pipeline = Pipeline()
    pipeline.add_step(RawMessageToContent())
    pipeline.add_step(FetchURLContent(Config.PROXY_URL))
    if Config.LLM_ENABLED:
        if Config.LLM_PROVIDER.lower() == "openai":
            provider = create_llm_provider(
                "openai",
                api_key=Config.OPENAI_API_KEY,
                model=Config.LLM_MODEL,
                base_url=Config.OPENAI_BASE_URL,
            )
        elif Config.LLM_PROVIDER.lower() in {"codex", "codex-cli"}:
            provider = create_llm_provider(
                "codex-cli",
                command=Config.CODEX_COMMAND,
                timeout=Config.CODEX_TIMEOUT_SECONDS,
            )
        elif Config.LLM_PROVIDER.lower() in {"codex-bridge", "codex_bridge"}:
            provider = create_llm_provider(
                "codex-bridge",
                bridge_url=Config.CODEX_BRIDGE_URL,
                token=Config.CODEX_BRIDGE_TOKEN,
                timeout=Config.CODEX_TIMEOUT_SECONDS,
            )
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {Config.LLM_PROVIDER}")
        pipeline.add_step(EnrichContent(provider, tag_repo))
    pipeline.add_step(ContentToNote())
    pipeline.add_step(SaveNote(fs_writer))

    # 4. Define Message Handler
    async def handle_message(msg: RawMessage):
        logger.info(f"Received message from {msg.user_id}")
        return await pipeline.run(msg)

    # 5. Initialize and Run Bot
    bot = TelegramBot(
        token=Config.TELEGRAM_BOT_TOKEN,
        allowed_user_ids=Config.ALLOWED_USER_IDS,
        message_handler=handle_message,
        tag_repo=tag_repo,
        fs_writer=fs_writer,
        proxy_url=Config.PROXY_URL
    )
    
    try:
        bot.run()
    except RuntimeError as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
