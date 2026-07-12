import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    VAULT_PATH = os.getenv("VAULT_PATH", "./vault")
    ALLOWED_USER_IDS: List[int] = [
        int(uid.strip()) for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") if uid.strip()
    ]
    PROXY_URL = os.getenv("PROXY_URL")
    LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-mini")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    CODEX_COMMAND = os.getenv("CODEX_COMMAND", "codex")
    CODEX_TIMEOUT_SECONDS = float(os.getenv("CODEX_TIMEOUT_SECONDS", "120"))
    CODEX_BRIDGE_URL = os.getenv("CODEX_BRIDGE_URL")
    CODEX_BRIDGE_TOKEN = os.getenv("CODEX_BRIDGE_TOKEN")

    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not cls.ALLOWED_USER_IDS:
            raise ValueError("ALLOWED_USER_IDS is not set")
        if cls.LLM_ENABLED and cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_ENABLED is true")
        if cls.LLM_ENABLED and cls.LLM_PROVIDER.lower() in {"codex", "codex-cli"} and not cls.CODEX_COMMAND:
            raise ValueError("CODEX_COMMAND must not be empty when using the Codex CLI provider")
        if cls.LLM_ENABLED and cls.LLM_PROVIDER.lower() in {"codex-bridge", "codex_bridge"}:
            if not cls.CODEX_BRIDGE_URL:
                raise ValueError("CODEX_BRIDGE_URL is required when using the Codex bridge provider")
            if not cls.CODEX_BRIDGE_TOKEN:
                raise ValueError("CODEX_BRIDGE_TOKEN is required when using the Codex bridge provider")
