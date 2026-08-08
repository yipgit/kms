from pathlib import Path
import shutil
from fastapi.testclient import TestClient

from src.obsidian_helper.main import app


def test_folder_list_create_and_move(monkeypatch):
    vault = Path.cwd() / ".test-folder-api"
    shutil.rmtree(vault, ignore_errors=True)
    monkeypatch.setenv("OBSIDIAN_HELPER_API_TOKEN", "secret")
    monkeypatch.setenv("VAULT_PATH", str(vault))
    client = TestClient(app)
    headers = {"X-API-Token": "secret"}

    created = client.post("/api/v1/folders", json={"folder": "History/Geopolitics"}, headers=headers)
    assert created.status_code == 200
    assert created.json()["folder"] == "History/Geopolitics"

    note = client.post("/api/v1/note", json={"title": "Malaysia", "folder": "History/Geopolitics", "content": "analysis"}, headers=headers)
    assert note.status_code == 200
    moved = client.post("/api/v1/note/move", json={"file": note.json()["file"], "folder": "History"}, headers=headers)
    assert moved.status_code == 200
    assert moved.json()["file"] == "History/Malaysia.md"
    assert "History/Geopolitics" in client.get("/api/v1/folders", headers=headers).json()["folders"]
    shutil.rmtree(vault, ignore_errors=True)
