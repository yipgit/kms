import os
import re
from datetime import datetime
from src.domain.models import Note
import logging

logger = logging.getLogger(__name__)

class FilesystemWriter:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        if not os.path.exists(self.vault_path):
            try:
                os.makedirs(self.vault_path)
                logger.info(f"Created vault directory at {self.vault_path}")
            except OSError as e:
                logger.error(f"Failed to create vault directory: {e}")
                raise

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem safe while keeping it readable."""
        # Replace colons with dashes
        filename = filename.replace(":", "-")
        # Replace double quotes with single quotes
        filename = filename.replace('"', "'")
        # Remove other strictly invalid character: < > / \ | ? *
        filename = re.sub(r'[<>/\\|?*]', '_', filename)
        # Trim whitespace and extra underscores
        filename = filename.strip().replace("  ", " ").replace("__", "_")
        # Ensure it's not empty
        if not filename:
            filename = "Untitled"
        return filename

    def _get_unique_path(self, directory: str, filename: str) -> str:
        """Ensure the file path is unique by appending a counter if necessary."""
        base_name, ext = os.path.splitext(filename)
        if not ext:
            ext = ".md"
            
        counter = 1
        full_path = os.path.join(directory, f"{base_name}{ext}")
        
        while os.path.exists(full_path):
            full_path = os.path.join(directory, f"{base_name}_{counter}{ext}")
            counter += 1
            
        return full_path

    async def write_note(self, note: Note) -> str:
        """Writes the note to the filesystem and returns the absolute path."""
        sanitized_filename = self._sanitize_filename(note.filename)
        
        # Determine target directory (default to vault root if note.path is empty)
        target_dir = os.path.join(self.vault_path, note.path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        full_path = self._get_unique_path(target_dir, sanitized_filename)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(note.content)
            logger.info(f"Successfully wrote note to {full_path}")
            return full_path
        except IOError as e:
            logger.error(f"Failed to write note to {full_path}: {e}")
            raise

    async def append_content(self, file_path: str, content: str):
        """Appends content to an existing file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Successfully appended to {file_path}")
        except IOError as e:
            logger.error(f"Failed to append to {file_path}: {e}")
            raise

    def list_vault_directories(self) -> list[str]:
        """Recursively list all directories in the vault, relative to vault root."""
        directories = ["/"] # Represent root
        for root, dirs, _ in os.walk(self.vault_path):
            # Skip hidden directories (like .obsidian)
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for d in dirs:
                full_path = os.path.join(root, d)
                rel_path = os.path.relpath(full_path, self.vault_path).replace('\\', '/')
                directories.append(rel_path)
        return sorted(list(set(directories)))

    async def list_folders(self) -> list[str]:
        return self.list_vault_directories()

    async def create_folder(self, folder: str) -> str:
        target_dir = self._safe_directory(folder)
        os.makedirs(target_dir, exist_ok=True)
        return "/" if not folder.strip("/\\") else folder.replace("\\", "/").strip("/")

    def _safe_directory(self, folder: str) -> str:
        root = os.path.realpath(self.vault_path)
        target = os.path.realpath(os.path.join(root, folder.replace("\\", "/").strip("/")))
        if target != root and not target.startswith(root + os.sep):
            raise ValueError("folder must remain inside the vault")
        return target

    async def move_note(self, current_abs_path: str, new_rel_dir: str) -> str:
        """Moves a note to a new relative directory within the vault."""
        if not os.path.exists(current_abs_path):
            raise FileNotFoundError(f"Source file not found: {current_abs_path}")

        # Handle root specially if needed, but os.path.join handles it
        if new_rel_dir == "/":
            new_rel_dir = ""
            
        target_dir = os.path.join(self.vault_path, new_rel_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            logger.info(f"Created directory {target_dir}")

        filename = os.path.basename(current_abs_path)
        new_abs_path = os.path.join(target_dir, filename)

        # Handle collision if moving to a folder where a same-named file exists
        if os.path.exists(new_abs_path) and new_abs_path != current_abs_path:
            new_abs_path = self._get_unique_path(target_dir, filename)

        try:
            os.rename(current_abs_path, new_abs_path)
            logger.info(f"Moved note from {current_abs_path} to {new_abs_path}")
            return new_abs_path
        except OSError as e:
            logger.error(f"Failed to move note: {e}")
            raise
