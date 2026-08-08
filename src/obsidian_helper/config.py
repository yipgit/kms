from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    vault_path: Path
    api_token: str
    host: str = "127.0.0.1"
    port: int = 8080
    max_body_bytes: int = 2_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("OBSIDIAN_HELPER_API_TOKEN", "").strip()
        if not token:
            raise ValueError("OBSIDIAN_HELPER_API_TOKEN must be set")
        return cls(
            vault_path=Path(os.getenv("VAULT_PATH", "./vault")).expanduser(),
            api_token=token,
            host=os.getenv("OBSIDIAN_HELPER_HOST", "127.0.0.1"),
            port=int(os.getenv("OBSIDIAN_HELPER_PORT", "8080")),
            max_body_bytes=int(os.getenv("MAX_NOTE_BYTES", "2000000")),
        )
