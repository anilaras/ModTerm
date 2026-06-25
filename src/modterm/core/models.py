from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from modterm.core.serial_models import SerialConfig


@dataclass(slots=True)
class RepeatSettings:
    interval_ms: int = 1000
    count: int = 1
    infinite: bool = False


@dataclass(slots=True)
class CommandTemplate:
    name: str
    description: str = ""
    mode: str = "Raw HEX"
    payload: str = ""
    auto_checksum: bool = False
    repeat: RepeatSettings = field(default_factory=RepeatSettings)
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandTemplate:
        repeat_data = data.get("repeat", {})
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            mode=str(data.get("mode", "Raw HEX")),
            payload=str(data.get("payload", "")),
            auto_checksum=bool(data.get("auto_checksum", False)),
            repeat=RepeatSettings(
                interval_ms=int(repeat_data.get("interval_ms", 1000)),
                count=int(repeat_data.get("count", 1)),
                infinite=bool(repeat_data.get("infinite", False)),
            ),
            parameters=dict(data.get("parameters", {})),
        )


@dataclass(slots=True)
class UserPreferences:
    language: str = "en"
    theme: str = "dark"
    display_mode: str = "Mixed"
    timestamp: bool = True


@dataclass(slots=True)
class ProjectData:
    version: int = 1
    name: str = "Untitled"
    serial: dict[str, Any] = field(default_factory=dict)
    templates: list[CommandTemplate] = field(default_factory=list)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    log_settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "serial": self.serial,
            "templates": [template.to_dict() for template in self.templates],
            "preferences": asdict(self.preferences),
            "log_settings": self.log_settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectData:
        preferences = data.get("preferences", {})
        return cls(
            version=int(data.get("version", 1)),
            name=str(data.get("name", "Untitled")),
            serial=dict(data.get("serial", {})),
            templates=[CommandTemplate.from_dict(item) for item in data.get("templates", [])],
            preferences=UserPreferences(
                language=str(preferences.get("language", "en")),
                theme=str(preferences.get("theme", "dark")),
                display_mode=str(preferences.get("display_mode", "Mixed")),
                timestamp=bool(preferences.get("timestamp", True)),
            ),
            log_settings=dict(data.get("log_settings", {})),
        )


@dataclass(frozen=True, slots=True)
class LogEntry:
    timestamp: datetime
    direction: str
    data: bytes
    protocol: str = "RAW"
    note: str = ""


def serial_config_to_dict(config: SerialConfig | None) -> dict[str, Any]:
    if config is None:
        return {}
    return {
        "port": config.port,
        "baudrate": config.baudrate,
        "bytesize": config.bytesize,
        "stopbits": config.stopbits,
        "parity": config.parity,
        "timeout": config.timeout,
        "write_timeout": config.write_timeout,
    }
