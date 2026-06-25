from __future__ import annotations

import csv
from pathlib import Path

from modterm.core.models import LogEntry
from modterm.core.parsers import format_ascii, format_hex


class LogService:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def add(self, entry: LogEntry) -> None:
        self.entries.append(entry)

    def clear(self) -> None:
        self.entries.clear()

    @property
    def statistics(self) -> dict[str, int]:
        tx = [entry for entry in self.entries if entry.direction.startswith("TX")]
        rx = [entry for entry in self.entries if entry.direction.startswith("RX")]
        return {
            "tx_frames": len(tx),
            "rx_frames": len(rx),
            "tx_bytes": sum(len(entry.data) for entry in tx),
            "rx_bytes": sum(len(entry.data) for entry in rx),
        }

    def export_text(self, path: str | Path) -> None:
        lines = [
            (
                f"{entry.timestamp.isoformat(timespec='milliseconds')} "
                f"[{entry.direction}] [{entry.protocol}] {format_hex(entry.data)}"
                f"{' — ' + entry.note if entry.note else ''}"
            )
            for entry in self.entries
        ]
        Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def export_csv(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "direction", "protocol", "hex", "ascii", "note"])
            for entry in self.entries:
                writer.writerow(
                    [
                        entry.timestamp.isoformat(timespec="milliseconds"),
                        entry.direction,
                        entry.protocol,
                        format_hex(entry.data),
                        format_ascii(entry.data),
                        entry.note,
                    ]
                )
