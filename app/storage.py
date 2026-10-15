from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

import httpx

from app.config import Settings
from app.models import Content


class StorageError(Exception):
    pass


class SQLiteStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "studio.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS contents (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def list(self) -> list[Content]:
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM contents ORDER BY created_at DESC").fetchall()
        return [Content.model_validate_json(row[0]) for row in rows]

    def get(self, content_id: UUID) -> Content | None:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM contents WHERE id = ?", (str(content_id),)).fetchone()
        return Content.model_validate_json(row[0]) if row else None

    def save(self, contents: list[Content]):
        with self.connect() as db:
            db.executemany("INSERT INTO contents VALUES (?, ?, ?)", [
                (str(c.id), c.created_at.isoformat(), c.model_dump_json()) for c in contents
            ])


class SupabaseStore:
    def __init__(self, settings: Settings):
        if not settings.supabase_url.startswith("https://") or not settings.supabase_service_role_key or not settings.supabase_service_role_key.get_secret_value():
            raise StorageError("Configurare SUPABASE_URL HTTPS e SUPABASE_SERVICE_ROLE_KEY, oppure MAD_STORAGE=sqlite.")
        self.url = settings.supabase_url.rstrip("/") + "/rest/v1/contents"
        self.key = settings.supabase_service_role_key.get_secret_value()

    def request(self, method: str, **kwargs):
        try:
            response = httpx.request(method, self.url, headers={
                "apikey": self.key, "Authorization": f"Bearer {self.key}", "Prefer": "return=minimal",
            }, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise StorageError("Supabase non disponibile. Controllare configurazione, schema SQL e accesso di rete.") from exc

    def list(self) -> list[Content]:
        # Supabase paginates responses: read every page instead of silently truncating.
        result = []
        offset = 0
        while True:
            rows = self.request("GET", params={"select": "payload", "order": "created_at.desc,id.asc", "limit": 100, "offset": offset}).json()
            result.extend(Content.model_validate(row["payload"]) for row in rows)
            if not rows:
                return result
            offset += len(rows)

    def get(self, content_id: UUID) -> Content | None:
        rows = self.request("GET", params={"id": f"eq.{content_id}", "select": "payload"}).json()
        return Content.model_validate(rows[0]["payload"]) if rows else None

    def save(self, contents: list[Content]):
        self.request("POST", json=[{"id": str(c.id), "created_at": c.created_at.isoformat(), "payload": c.model_dump(mode="json")} for c in contents])


def create_store(settings: Settings):
    return SupabaseStore(settings) if settings.mad_storage == "supabase" else SQLiteStore(settings.mad_data_dir)
