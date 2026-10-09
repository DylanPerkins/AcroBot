import json
from pathlib import Path


class AcronymStore:
    def __init__(self, path: str = "data/acronyms.json", suggestions_path: str = "data/suggestions.json"):
        self.path = Path(path)
        self.suggestions_path = Path(suggestions_path)
        self.acronyms: dict[str, dict] = json.loads(self.path.read_text())

    def get(self, key: str) -> dict | None:
        return self.acronyms.get(key.strip().lower())

    def keys(self):
        return self.acronyms.keys()

    def _load_suggestions(self) -> list[dict]:
        if not self.suggestions_path.exists():
            return []
        return json.loads(self.suggestions_path.read_text())

    def has_pending_suggestion(self, key: str) -> bool:
        key = key.strip().lower()
        return any(s["acronym"] == key for s in self._load_suggestions())

    def get_suggestion(self, key: str) -> dict | None:
        key = key.strip().lower()
        return next((s for s in self._load_suggestions() if s["acronym"] == key), None)

    def remove_suggestion(self, key: str) -> None:
        key = key.strip().lower()
        pending = [s for s in self._load_suggestions() if s["acronym"] != key]
        self.suggestions_path.write_text(json.dumps(pending, indent=2))

    def upsert_acronym(self, key: str, entry: dict) -> None:
        key = key.strip().lower()
        self.acronyms[key] = entry
        self.path.write_text(json.dumps(self.acronyms, indent=2))

    def add_suggestion(self, acronym: str, title: str, url: str, suggested_by: int) -> str:
        """Queues a suggestion for manual review, returns a status string."""
        key = acronym.strip().lower()

        if key in self.acronyms:
            return "duplicate_acronym"
        if self.has_pending_suggestion(key):
            return "duplicate_suggestion"

        pending = self._load_suggestions()
        pending.append({
            "acronym": key,
            "title": title,
            "url": url,
            "suggested_by": suggested_by,
        })
        self.suggestions_path.write_text(json.dumps(pending, indent=2))
        return "added"
