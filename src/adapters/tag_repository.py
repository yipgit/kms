import json
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TagRepository:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._tags: Dict[str, int] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self._tags = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load tags from {self.storage_path}: {e}")
                self._tags = {}

    def _save(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._tags, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tags to {self.storage_path}: {e}")

    def add_tag(self, tag: str):
        """Adds a tag or increments its usage count."""
        tag = tag.strip().lstrip('#')
        if not tag:
            return
        self._tags[tag] = self._tags.get(tag, 0) + 1
        self._save()

    def get_top_tags(self, limit: int = 10) -> List[str]:
        """Returns the top N most used tags."""
        sorted_tags = sorted(self._tags.items(), key=lambda item: item[1], reverse=True)
        return [tag for tag, count in sorted_tags[:limit]]
