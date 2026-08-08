from pathlib import Path
import hashlib
import os
import tempfile
from threading import Lock

from .markdown import render_note, safe_filename
from .models import NoteRequest


class VaultStorage:
    """Safe, atomic Markdown storage. Duplicate content is idempotent."""

    def __init__(self, vault_path: Path):
        self.root = vault_path.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _folder(self, folder: str) -> Path:
        clean = folder.replace("\\", "/").strip("/")
        candidate = (self.root / clean).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("folder must remain inside the vault")
        return candidate

    def save(self, note: NoteRequest) -> tuple[str, bool]:
        folder = self._folder(note.folder)
        folder.mkdir(parents=True, exist_ok=True)
        content = render_note(note)
        target = folder / safe_filename(note.title)
        with self._lock:
            if target.exists() and target.read_text(encoding="utf-8") == content:
                return target.relative_to(self.root).as_posix(), False
            if target.exists():
                digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
                target = folder / f"{target.stem}--{digest}.md"
                if target.exists() and target.read_text(encoding="utf-8") == content:
                    return target.relative_to(self.root).as_posix(), False
            fd, temp_name = tempfile.mkstemp(prefix=".note-", suffix=".tmp", dir=folder)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, target)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        return target.relative_to(self.root).as_posix(), True

    def list_folders(self) -> list[str]:
        folders = ["/"]
        for path in self.root.rglob("*"):
            if path.is_dir() and not any(part.startswith(".") for part in path.relative_to(self.root).parts):
                folders.append(path.relative_to(self.root).as_posix())
        return sorted(folders, key=lambda value: (value != "/", value.lower()))

    def create_folder(self, folder: str) -> str:
        path = self._folder(folder)
        path.mkdir(parents=True, exist_ok=True)
        return "/" if path == self.root else path.relative_to(self.root).as_posix()

    def move(self, file: str, folder: str) -> str:
        source = (self.root / file.replace("\\", "/")).resolve()
        if source.suffix.lower() != ".md" or self.root not in source.parents or not source.is_file():
            raise ValueError("file must be an existing Markdown file inside the vault")
        destination_dir = self._folder(folder)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / source.name
        if destination.exists() and destination != source:
            raise ValueError("a note with this filename already exists in the destination folder")
        os.replace(source, destination)
        return destination.relative_to(self.root).as_posix()
