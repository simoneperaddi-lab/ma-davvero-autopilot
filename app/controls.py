"""Single-host durable limits, reservations and research cache (also with Supabase)."""
import json
import math
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.config import Settings


class LimitError(Exception):
    pass


@contextmanager
def connection(path: Path):
    db = sqlite3.connect(path, timeout=15)
    try:
        with db:
            yield db
    finally:
        db.close()


class Controls:
    def __init__(self, data_dir: Path):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "controls.sqlite3"
        with connection(self.path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS rate_limits (bucket TEXT, window INTEGER, count INTEGER, PRIMARY KEY(bucket, window));
                CREATE TABLE IF NOT EXISTS usage (id TEXT PRIMARY KEY, day TEXT, reserved_microusd INTEGER,
                    status TEXT, input_tokens INTEGER, output_tokens INTEGER);
                CREATE TABLE IF NOT EXISTS research_cache (id TEXT PRIMARY KEY, payload TEXT);
            """)

    def rate(self, bucket: str, limit: int):
        window = int(time.time()) // 60
        with connection(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM rate_limits WHERE window < ?", (window - 2,))
            row = db.execute("SELECT count FROM rate_limits WHERE bucket=? AND window=?", (bucket, window)).fetchone()
            if row and row[0] >= limit:
                raise LimitError("Troppe richieste. Riprova tra un minuto.")
            db.execute("INSERT INTO rate_limits VALUES (?, ?, 1) ON CONFLICT(bucket, window) DO UPDATE SET count=count+1", (bucket, window))

    def reserve(self, settings: Settings, input_bound: int, output_bound: int) -> str:
        if not settings.mad_paid_enabled:
            raise LimitError("Operazioni a pagamento disabilitate (MAD_PAID_ENABLED=false).")
        if settings.mad_openai_model != "gpt-4.1-mini":
            raise LimitError("Modello non abilitato nel budget: è supportato solo gpt-4.1-mini.")
        input_rate = settings.mad_openai_input_usd_per_million
        output_rate = settings.mad_openai_output_usd_per_million
        if input_rate <= 0 or output_rate <= 0:
            raise LimitError("Configurare esplicitamente le tariffe input/output prima di usare OpenAI.")
        # Microdollars: token count * USD per million tokens, rounded UP.
        reserved = math.ceil(input_bound * input_rate + output_bound * output_rate)
        if reserved > int(settings.mad_openai_call_ceiling_usd * 1_000_000):
            raise LimitError("La riserva richiesta supera il limite per chiamata.")
        day = datetime.now(timezone.utc).date().isoformat()
        reservation = str(uuid4())
        with connection(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            count, total = db.execute("SELECT count(*), coalesce(sum(reserved_microusd),0) FROM usage WHERE day=?", (day,)).fetchone()
            if count >= settings.mad_openai_daily_calls or total + reserved > int(settings.mad_openai_daily_budget_usd * 1_000_000):
                raise LimitError("Budget giornaliero o numero massimo di chiamate OpenAI esaurito.")
            db.execute("INSERT INTO usage VALUES (?, ?, ?, 'reserved', NULL, NULL)", (reservation, day, reserved))
        return reservation

    def finish(self, reservation: str, status: str, usage=None):
        # Never refund failed/uncertain calls: the provider may already have billed them.
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        with connection(self.path) as db:
            db.execute("UPDATE usage SET status=?, input_tokens=?, output_tokens=? WHERE id=?",
                       (status, input_tokens, output_tokens, reservation))

    def report(self, settings: Settings):
        day = datetime.now(timezone.utc).date().isoformat()
        with connection(self.path) as db:
            count, total, inputs, outputs = db.execute("SELECT count(*), coalesce(sum(reserved_microusd),0), coalesce(sum(input_tokens),0), coalesce(sum(output_tokens),0) FROM usage WHERE day=?", (day,)).fetchone()
            statuses = dict(db.execute("SELECT status, count(*) FROM usage WHERE day=? GROUP BY status", (day,)).fetchall())
            reported = db.execute("SELECT count(*) FROM usage WHERE day=? AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL", (day,)).fetchone()[0]
        return {"day_utc": day, "paid_enabled": settings.mad_paid_enabled, "calls": count,
                "max_calls": settings.mad_openai_daily_calls, "reserved_usd": str(Decimal(total) / 1_000_000),
                "daily_budget_usd": str(settings.mad_openai_daily_budget_usd), "input_tokens": inputs,
                "output_tokens": outputs, "usage_reported_calls": reported, "statuses": statuses, "accounting": "conservative_reservations_not_invoice"}

    def cache(self, record):
        with connection(self.path) as db:
            db.execute("INSERT OR REPLACE INTO research_cache VALUES (?, ?)", (str(record.id), record.model_dump_json()))

    def cached(self, record_id):
        with connection(self.path) as db:
            row = db.execute("SELECT payload FROM research_cache WHERE id=?", (str(record_id),)).fetchone()
        return json.loads(row[0]) if row else None
