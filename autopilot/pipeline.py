"""Crash-safe daily publication state machine; no paid calls, no hidden activation."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from autopilot.http import Blocked
from autopilot.science import Unverified

ROME = ZoneInfo("Europe/Rome")
TERMINAL = {"published", "abandoned"}


class PendingPublication(RuntimeError):
    pass


def day(now):
    return now.astimezone(ROME).date().isoformat()


def event(state, now, kind, message):
    state["events"].append({"at": now.isoformat(), "kind": kind, "message": message})
    state["events"] = state["events"][-730:]


class Pipeline:
    def __init__(self, store, archive, instagram, render, secrets=None, now=None):
        self.store, self.archive, self.ig, self.render, self.secrets = store, archive, instagram, render, secrets
        self.now = now or datetime.now(timezone.utc)

    def tokens(self, state):
        self.ig.identity()
        token = state.setdefault("token", {})
        if not token.get("last_refresh"):
            token["last_refresh"] = self.now.isoformat()
            token["expiry_note"] = "Scadenza iniziale sconosciuta; richiesto token Instagram long-lived"
            self.store.save(state)
        elif self.now - datetime.fromisoformat(token["last_refresh"]) >= timedelta(days=7):
            if self.secrets is None:
                raise Blocked("Secret store per il rinnovo automatico assente")
            result = self.ig.refresh()
            # Persist the rotated value ONLY to GitHub Secrets before recording success.
            self.secrets.save_token(result["access_token"])
            self.ig.token = result["access_token"]
            token.update(last_refresh=self.now.isoformat(),
                         expires_at=(self.now + timedelta(seconds=result["expires_in"])).isoformat())
            token.pop("expiry_note", None)
            self.store.save(state)

    def finish(self, state, entry, media_id=None):
        entry.update(status="published", published_at=self.now.isoformat(), media_id=media_id)
        # The evidence/measurement remains durable; discard transient slide/claim data.
        content = entry["fact"].pop("content", None)
        if content:
            entry["fact"]["caption"] = content["caption"]
        entry.pop("upload_uri", None)
        event(state, self.now, "published", f"Pubblicato: {entry['fact']['subject']}")
        self.store.save(state)
        return "published"

    def run(self, directory):
        state = self.store.load()
        if state.get("account_id") not in (None, self.ig.user_id):
            raise Blocked("Registro associato a un altro account: operazione bloccata")
        state["account_id"] = self.ig.user_id
        self.tokens(state)
        pending = [x for x in state["entries"] if x["status"] not in TERMINAL]
        if len(pending) > 1:
            raise PendingPublication("Registro con più operazioni pendenti: controllo necessario")
        if pending and pending[0]["status"] == "publishing":
            entry = pending[0]
            status = self.ig.wait_ready(entry["container_id"])
            if status == "PUBLISHED":
                return self.finish(state, entry)
            # Never retry media_publish, even if FINISHED; previous response was ambiguous.
            raise PendingPublication("Esito della precedente pubblicazione incerto: nessun nuovo tentativo")
        if any(x.get("published_at") and day(datetime.fromisoformat(x["published_at"])) == day(self.now)
               for x in state["entries"]):
            return "already_published_today"
        if pending:
            entry = pending[0]
            if self.now - datetime.fromisoformat(entry["fact"]["checked_at"]) > timedelta(hours=24):
                entry["status"] = "abandoned"
                event(state, self.now, "skipped", "Operazione non pubblicata scaduta; nuova verifica al prossimo ciclo")
                self.store.save(state)
                return "skipped"
        else:
            try:
                fact = self.archive.select({x["fact"]["subject"] for x in state["entries"]})
            except Unverified as exc:
                event(state, self.now, "skipped", str(exc))
                self.store.save(state)
                return "skipped"
            entry = {"date": day(self.now), "status": "prepared", "fact": fact}
            state["entries"].append(entry)
            self.store.save(state)
        if entry["status"] == "prepared":
            video = self.render(entry["fact"], directory)
            container, uri = self.ig.create(entry["fact"]["content"]["caption"])
            entry.update(status="container", container_id=container, upload_uri=uri)
            self.store.save(state)  # MUST succeed before upload or publication.
            self.ig.upload(uri, video)
            entry["status"] = "uploaded"
            self.store.save(state)
        status = self.ig.wait_ready(entry["container_id"])
        if status == "PUBLISHED":
            return self.finish(state, entry)
        if status in {"ERROR", "EXPIRED"}:
            entry["status"] = "abandoned"
            event(state, self.now, "skipped", f"Container Instagram {status}; nessuna ripubblicazione")
            self.store.save(state)
            return "skipped"
        if status != "FINISHED":
            raise PendingPublication("Elaborazione Instagram ancora in corso")
        entry["status"] = "publishing"
        self.store.save(state)  # The durable intent is the at-most-once boundary.
        media_id = self.ig.publish(entry["container_id"])
        return self.finish(state, entry, media_id)


def weekly_report(state, now=None):
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    events = [x for x in state["events"] if datetime.fromisoformat(x["at"]) >= since]
    lines = ["# MA DAVVERO? — ultimi 7 giorni", "", f"Aggiornamento: {now.isoformat()}", "",
             f"Pubblicati: {sum(x['kind'] == 'published' for x in events)}",
             f"Saltati: {sum(x['kind'] == 'skipped' for x in events)}",
             f"Errori: {sum(x['kind'] == 'error' for x in events)}", "",
             f"Operazioni pendenti: {sum(x['status'] not in TERMINAL for x in state['entries'])}",
             f"Ultimo rinnovo token: {state.get('token', {}).get('last_refresh', 'non disponibile')}", ""]
    lines += [f"- {x['at']}: {x['kind']} — {x['message']}" for x in events]
    return "\n".join(lines) + "\n"
