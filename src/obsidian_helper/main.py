import logging
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import Settings
from .models import FolderRequest, MoveRequest, NoteRequest, NoteResponse
from .storage import VaultStorage

logger = logging.getLogger(__name__)
app = FastAPI(title="obsidian-helper", version="1.0.0")


def _settings() -> Settings:
    return Settings.from_env()


def _storage(settings: Settings = Depends(_settings)) -> VaultStorage:
    return VaultStorage(settings.vault_path)


def require_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
    settings: Settings = Depends(_settings),
) -> None:
    supplied = x_api_token
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or supplied != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid API token")


@app.get("/healthz")
def healthz(settings: Settings = Depends(_settings)) -> dict[str, str]:
    settings.vault_path.mkdir(parents=True, exist_ok=True)
    return {"status": "ok"}


@app.get("/api/v1/folders", dependencies=[Depends(require_token)])
def list_folders(storage: VaultStorage = Depends(_storage)) -> dict[str, list[str]]:
    return {"folders": storage.list_folders()}


@app.post("/api/v1/folders", dependencies=[Depends(require_token)])
def create_folder(request: FolderRequest, storage: VaultStorage = Depends(_storage)) -> dict[str, str]:
    return {"folder": storage.create_folder(request.folder)}


@app.post("/api/v1/note/move", dependencies=[Depends(require_token)])
def move_note(request: MoveRequest, storage: VaultStorage = Depends(_storage)) -> dict[str, str]:
    return {"file": storage.move(request.file, request.folder)}


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.post("/api/v1/note", response_model=NoteResponse, dependencies=[Depends(require_token)])
def save_note(
    note: NoteRequest,
    settings: Settings = Depends(_settings),
    storage: VaultStorage = Depends(_storage),
) -> NoteResponse:
    if len(note.content.encode("utf-8")) > settings.max_body_bytes:
        raise HTTPException(status_code=413, detail="note content is too large")
    relative, created = storage.save(note)
    return NoteResponse(file=relative, created=created)
