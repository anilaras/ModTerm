from __future__ import annotations

from modterm.core.models import CommandTemplate, ProjectData, RepeatSettings, UserPreferences
from modterm.services.persistence import load_project, load_templates, save_project, save_templates


def test_project_round_trip(tmp_path) -> None:
    path = tmp_path / "factory.modterm"
    project = ProjectData(
        name="Factory Line",
        serial={"port": "/dev/ttyUSB0", "baudrate": 19200},
        templates=[
            CommandTemplate(
                name="Read temperature",
                mode="Modbus RTU",
                payload="01 03 00 00 00 02 C4 0B",
                auto_checksum=True,
                repeat=RepeatSettings(interval_ms=500, count=10),
                parameters={"slave_id": 1, "function_code": 3},
            )
        ],
        preferences=UserPreferences(language="tr", theme="dark"),
    )

    save_project(path, project)
    loaded = load_project(path)

    assert loaded.name == "Factory Line"
    assert loaded.serial["baudrate"] == 19200
    assert loaded.templates[0].repeat.interval_ms == 500
    assert loaded.preferences.language == "tr"


def test_template_library_round_trip(tmp_path) -> None:
    path = tmp_path / "templates.json"
    templates = [CommandTemplate(name="Ping", mode="Raw ASCII", payload="PING\\r")]

    save_templates(path, templates)

    assert load_templates(path)[0].payload == "PING\\r"
