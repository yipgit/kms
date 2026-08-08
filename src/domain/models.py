from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class RawMessage:
    """Represents the raw incoming message from Telegram."""
    chat_id: int
    message_id: int
    user_id: int
    text: Optional[str]
    date: datetime
    forward_from: Optional[str] = None
    forward_date: Optional[datetime] = None
    original_json: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Content:
    """Intermediate representation of the content to be saved."""
    source_url: Optional[str] = None
    title: Optional[str] = None
    body: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    enrichment: Optional["Enrichment"] = None


@dataclass
class Enrichment:
    """Structured, model-generated metadata kept separate from source content."""
    abstract: str
    key_points: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    suggested_title: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: str = "enrichment-v1"

@dataclass
class Note:
    """Final representation of the note to be written to the filesystem."""
    filename: str
    content: str
    path: str = ""  # Relative path within the vault
    absolute_path: Optional[str] = None # Set after writing
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    path: str = ""
