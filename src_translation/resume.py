from __future__ import annotations

import json
from pathlib import Path

from .models import TranslationItem


class ResumeManager:
    def __init__(self, resume_path: str, save_interval: int = 25) -> None:
        self.resume_path = Path(resume_path)
        self.save_interval = save_interval
        self.entries: dict[str, dict] = {}
        self.pending_entries: list[dict] = []

    @staticmethod
    def _key(item: TranslationItem) -> str:
        parts = (
            item.kind,
            item.owner_form,
            item.owner_component,
            item.owner_unit,
            item.name,
            item.item_id,
            item.stringid,
        )
        return "|".join(parts)

    def load(self) -> int:
        if not self.resume_path.exists():
            self.entries = {}
            return 0

        loaded: dict[str, dict] = {}
        with self.resume_path.open("r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                key = row.get("resume_key")
                if key:
                    loaded[str(key)] = row

        self.entries = loaded
        return len(self.entries)

    def contains(self, item: TranslationItem) -> bool:
        entry = self.entries.get(self._key(item))
        return bool(entry and entry.get("source_text") == item.source_text)

    def get(self, item: TranslationItem) -> dict:
        return self.entries[self._key(item)]

    def add_entry(self, item: TranslationItem) -> int:
        entry = {
            "resume_key": self._key(item),
            "item_id": item.item_id,
            "source_text": item.source_text,
            "translated_protected_text": item.translated_protected_text,
            "final_text": item.final_text,
            "status": item.status,
        }
        self.pending_entries.append(entry)

        if len(self.pending_entries) >= self.save_interval:
            return self.flush()
        return 0

    def flush(self) -> int:
        if not self.pending_entries:
            return 0

        self.resume_path.parent.mkdir(parents=True, exist_ok=True)

        with self.resume_path.open("a", encoding="utf-8") as file_handle:
            for entry in self.pending_entries:
                file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self.entries[entry["resume_key"]] = entry

        written = len(self.pending_entries)
        self.pending_entries.clear()
        return written
