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

    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not cls.ALLOWED_USER_IDS:
            raise ValueError("ALLOWED_USER_IDS is not set")
