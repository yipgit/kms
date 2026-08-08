from datetime import date
import re
from .models import NoteRequest


def _yaml_scalar(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def safe_filename(title: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    return (value or "Untitled")[:200] + ".md"


def render_note(note: NoteRequest, written_date: date | None = None) -> str:
    day = written_date or note.note_date or date.today()
    lines = ["---", f"title: {_yaml_scalar(note.title)}", f"date: {day.isoformat()}"]
    if note.tags:
        lines += ["tags:"] + [f"  - {_yaml_scalar(tag)}" for tag in note.tags]
    if note.summary:
        lines += [f"summary: {_yaml_scalar(note.summary)}"]
    if note.source:
        lines += ["source:"] + [f"  - {_yaml_scalar(source)}" for source in note.source]
    lines += ["---", "", note.content.rstrip(), ""]
    return "\n".join(lines)
