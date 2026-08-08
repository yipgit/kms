"""Note destinations used by collectors."""
import httpx
from src.domain.models import Note


class HttpNoteSink:
    def __init__(self, url: str, token: str, timeout: float = 30.0):
        self.url = url.rstrip("/") + "/api/v1/note"
        self.token = token
        self.timeout = timeout

    async def write_note(self, note: Note) -> str:
        payload = {
            "title": note.filename.removesuffix(".md"),
            "folder": note.path,
            "content": note.content,
            "tags": note.tags,
            "summary": note.summary,
            "source": ["Telegram"],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url, json=payload, headers={"Authorization": f"Bearer {self.token}"})
            response.raise_for_status()
            return response.json()["file"]

    async def list_folders(self) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.url.removesuffix("/api/v1/note") + "/api/v1/folders", headers=self._headers())
            response.raise_for_status()
            return response.json()["folders"]

    async def create_folder(self, folder: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url.removesuffix("/api/v1/note") + "/api/v1/folders", json={"folder": folder}, headers=self._headers())
            response.raise_for_status()
            return response.json()["folder"]

    async def move_note(self, file: str, folder: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url + "/move", json={"file": file, "folder": folder}, headers=self._headers())
            response.raise_for_status()
            return response.json()["file"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
