"""One versioned atomic JSON snapshot behind a repository interface."""
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol
import json
import os
import tempfile

class Repository(Protocol):
    def load(self) -> dict: ...
    def save(self, snapshot: dict) -> None: ...

def empty_snapshot() -> dict:
    return {"schema_version":1,"revision":0,"profile":{},"state":None,"plans":[],"checkins":[],"records":[],"safety_latch":None,"audit":[]}

class StateManager:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.path = self.directory / "snapshot.json"

    def load(self) -> dict:
        if not self.path.exists(): return empty_snapshot()
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1: raise ValueError("Unsupported storage schema version")
        if not all(k in value for k in empty_snapshot()): raise ValueError("Incomplete snapshot; refusing reset")
        return value

    def save(self, snapshot: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        current = self.load()
        if current["revision"] != snapshot["revision"]: raise ValueError("Revision conflict")
        updated = {**snapshot, "revision":snapshot["revision"] + 1}
        fd, temp = tempfile.mkstemp(prefix="snapshot-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(updated, file, ensure_ascii=False, indent=2, allow_nan=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp, self.path)
            snapshot["revision"] = updated["revision"]
        finally:
            if os.path.exists(temp): os.unlink(temp)

    @contextmanager
    def transaction(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        lock = self.directory / ".lock"
        try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc: raise RuntimeError("Repository busy; after crash verify no active writer before removing .lock") from exc
        try:
            os.close(fd)
            snapshot = self.load()
            yield snapshot
            self.save(snapshot)
        finally:
            lock.unlink(missing_ok=True)
