import unittest
import os
from unittest.mock import patch
from src.config import Config

class TestConfig(unittest.TestCase):
    def test_validate_success(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "ALLOWED_USER_IDS": "1,2"}):
            # Reload class attributes by re-importing or mocking?
            # Config attributes are set at import time. 
            # We need to manually set them for testing since we can't easily re-import.
            Config.TELEGRAM_BOT_TOKEN = "token"
            Config.ALLOWED_USER_IDS = [1, 2]
            Config.validate() # Should not raise

    def test_validate_missing_token(self):
        Config.TELEGRAM_BOT_TOKEN = None
        with self.assertRaises(ValueError):
            Config.validate()

    def test_validate_missing_users(self):
        Config.TELEGRAM_BOT_TOKEN = "token"
        Config.ALLOWED_USER_IDS = []
        with self.assertRaises(ValueError):
            Config.validate()
