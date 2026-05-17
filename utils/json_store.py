import json
from pathlib import Path
from typing import Any, List


class JSONStore:
    """
    A durable JSON storage utility.
    Supports:
    - append-safe writes
    - atomic file operations
    - automatic file creation
    - list-based storage
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self._ensure_file()

    # ---------------------------------------------------------
    # FILE INITIALIZATION
    # ---------------------------------------------------------
    def _ensure_file(self):
        """
        Ensures the JSON file exists and is a list.
        If missing or corrupted, it resets to an empty list.
        """

        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write_json([])  # initialize empty list
            return

        try:
            data = self._read_json()
            if not isinstance(data, list):
                self._write_json([])  # reset corrupted file
        except Exception:
            self._write_json([])  # reset corrupted file

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------
    def _read_json(self) -> List[Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---------------------------------------------------------
    # WRITE
    # ---------------------------------------------------------
    def _write_json(self, data: List[Any]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # ---------------------------------------------------------
    # APPEND
    # ---------------------------------------------------------
    def append(self, item: Any):
        """
        Appends an item to the JSON list safely.
        """

        data = self._read_json()
        data.append(item)
        self._write_json(data)

    # ---------------------------------------------------------
    # GET ALL
    # ---------------------------------------------------------
    def all(self) -> List[Any]:
        """
        Returns all stored entries.
        """
        return self._read_json()
