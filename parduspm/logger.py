"""Activity logging shared by both frontends.

Every meaningful action goes through an ``ActivityLog``. It keeps an in-memory
ring of recent entries (so a UI can render the activity panel), appends to a
persistent log file, and notifies subscribers so the GUI/TUI can update live.

The format matches the spec, e.g.:

    [12:03:41] Detected Flatpak
"""

from __future__ import annotations

import enum
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class Level(enum.Enum):
    INFO = "INFO"
    ACTION = "ACTION"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Entry:
    level: Level
    message: str
    timestamp: float

    def formatted(self) -> str:
        clock = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[{clock}] {self.message}"


def _default_log_path() -> Path:
    # Respect XDG; fall back to ~/.local/state. We never require root to log.
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "pardus-pm" / "activity.log"


class ActivityLog:
    def __init__(self, path: Path | None = None, keep: int = 500):
        self.path = path or _default_log_path()
        self.keep = keep
        self.entries: list[Entry] = []
        self._subscribers: list[Callable[[Entry], None]] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, callback: Callable[[Entry], None]) -> Callable[[], None]:
        """Register a listener; returns an unsubscribe function."""
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

    def log(self, message: str, level: Level = Level.INFO) -> Entry:
        entry = Entry(level=level, message=message, timestamp=time.time())
        self.entries.append(entry)
        if len(self.entries) > self.keep:
            self.entries = self.entries[-self.keep:]
        self._persist(entry)
        for callback in list(self._subscribers):
            # A misbehaving subscriber must never break logging for the rest.
            callback(entry)
        return entry

    def info(self, message: str) -> Entry:
        return self.log(message, Level.INFO)

    def action(self, message: str) -> Entry:
        return self.log(message, Level.ACTION)

    def success(self, message: str) -> Entry:
        return self.log(message, Level.SUCCESS)

    def error(self, message: str) -> Entry:
        return self.log(message, Level.ERROR)

    def _persist(self, entry: Entry) -> None:
        line = f"{entry.formatted()} [{entry.level.value}]\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
