import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from src.obsidian_helper.main import app


def test_note_api_is_authenticated_and_idempotent(monkeypatch):
    tmp_path = Path.cwd() / ".test-obsidian-helper-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    monkeypatch.setenv("OBSIDIAN_HELPER_API_TOKEN", "secret")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    client = TestClient(app)
    payload = {"title": "GCP IAM权限继承", "folder": "Technology/GCP", "tags": ["GCP"], "content": "正文", "source": ["ChatGPT"]}
    assert client.post("/api/v1/note", json=payload).status_code == 401
    response = client.post("/api/v1/note", json=payload, headers={"Authorization": "Bearer secret"})
    assert response.status_code == 200
    assert response.json()["created"] is True
    second = client.post("/api/v1/note", json=payload, headers={"X-API-Token": "secret"})
    assert second.json()["created"] is False
    assert (tmp_path / "Technology" / "GCP" / "GCP IAM权限继承.md").read_text(encoding="utf-8").startswith("---")
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_folder_traversal_is_rejected(monkeypatch):
    tmp_path = Path.cwd() / ".test-obsidian-helper-traversal"
    shutil.rmtree(tmp_path, ignore_errors=True)
    monkeypatch.setenv("OBSIDIAN_HELPER_API_TOKEN", "secret")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    client = TestClient(app)
    response = client.post("/api/v1/note", json={"title": "x", "folder": "../outside", "content": "x"}, headers={"X-API-Token": "secret"})
    assert response.status_code == 400
    shutil.rmtree(tmp_path, ignore_errors=True)
