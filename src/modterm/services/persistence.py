from __future__ import annotations

import json
from pathlib import Path

from modterm.core.models import CommandTemplate, ProjectData


def save_project(path: str | Path, project: ProjectData) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(destination)


def load_project(path: str | Path) -> ProjectData:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Project file must contain a JSON object.")
    return ProjectData.from_dict(data)


def save_templates(path: str | Path, templates: list[CommandTemplate]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps([template.to_dict() for template in templates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_templates(path: str | Path) -> list[CommandTemplate]:
    source = Path(path)
    if not source.exists():
        return []
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Template file must contain a JSON array.")
    return [CommandTemplate.from_dict(item) for item in data]
