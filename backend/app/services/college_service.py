"""Search over the compact AICTE institutions dataset."""
from __future__ import annotations

import json
from pathlib import Path

from backend.app.config import DATA_DIR

COLLEGES_FILE = DATA_DIR / "aicte_colleges.json"
VALID_TYPES = ("engineering", "diploma", "pharmacy", "management")


class CollegeService:
    def __init__(self, path: Path = COLLEGES_FILE):
        self.path = path
        self._mtime = 0.0
        self._rows: list[dict] = []
        self._meta: dict = {}

    def _load(self) -> list[dict]:
        mtime = self.path.stat().st_mtime if self.path.exists() else 0.0
        if mtime != self._mtime:
            if self.path.exists():
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                self._rows = payload.get("colleges", [])
                self._meta = {k: payload.get(k) for k in ("source", "generated", "count")}
            else:
                self._rows, self._meta = [], {}
            self._mtime = mtime
        return self._rows

    def states(self) -> list[str]:
        return sorted({r["state"] for r in self._load() if r["state"]})

    def search(self, state: str | None = None, type: str | None = None, branch: str | None = None,
               district: str | None = None, ownership: str | None = None, q: str | None = None,
               limit: int = 20, offset: int = 0) -> dict:
        if type and type not in VALID_TYPES:
            raise ValueError(f"type must be one of {', '.join(VALID_TYPES)}")
        rows = self._load()
        s, d, o, b, text = (v.lower().strip() if v else None for v in (state, district, ownership, branch, q))

        def match(r: dict) -> bool:
            if s and r["state"].lower() != s:
                return False
            if type and type not in r["kinds"]:
                return False
            if d and d not in r["district"].lower():
                return False
            if o and o not in r["ownership"].lower():
                return False
            if text and text not in r["name"].lower():
                return False
            if b:
                pool = r["branches"].get(type, []) if type else [x for v in r["branches"].values() for x in v]
                if not any(b in x.lower() for x in pool):
                    return False
            return True

        hits = [r for r in rows if match(r)]
        # Government institutions first, then larger intake. Stable for pagination.
        hits.sort(key=lambda r: (0 if r["ownership"].lower().startswith("gov") else 1, -r["intake"], r["name"]))
        return {"total": len(hits), "limit": limit, "offset": offset, "source": self._meta.get("source"),
                "results": hits[offset:offset + limit]}


college_service = CollegeService()
