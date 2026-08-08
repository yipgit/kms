from datetime import date
from typing import Any
from pydantic import BaseModel, Field, field_validator


class NoteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    folder: str = Field(default="", max_length=300)
    tags: list[str] = Field(default_factory=list, max_length=50)
    summary: str | None = Field(default=None, max_length=5000)
    content: str = Field(min_length=1)
    source: list[str] = Field(default_factory=list, max_length=20)
    note_date: date | None = None
    idempotency_key: str | None = Field(default=None, max_length=200)

    @field_validator("title", "folder", "content", "summary", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class NoteResponse(BaseModel):
    status: str = "success"
    file: str
    created: bool


class FolderRequest(BaseModel):
    folder: str = Field(min_length=1, max_length=300)


class MoveRequest(BaseModel):
    file: str = Field(min_length=1, max_length=500)
    folder: str = Field(default="", max_length=300)
