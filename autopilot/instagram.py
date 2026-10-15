"""Official Instagram API with Instagram Login; no browser automation.

Resumable upload removes the need for a publicly hosted video URL.
The real account/permissions contract must be validated during owner onboarding.
"""
import re
import time
from urllib.parse import urlparse

from autopilot.http import RemoteError


class Instagram:
    def __init__(self, http, user_id, token, version="v24.0", sleep=time.sleep):
        if not re.fullmatch(r"[0-9]+", user_id) or not re.fullmatch(r"v[0-9]+\.0", version):
            raise ValueError("ID Instagram o versione Graph non validi")
        self.http, self.user_id, self.token, self.sleep = http, user_id, token, sleep
        self.root = f"https://graph.instagram.com/{version}"
        self.version = version

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def identity(self):
        me = self.http.json("GET", self.root + "/me", params={"fields": "user_id,username"}, headers=self.headers)
        if str(me.get("user_id", "")) != self.user_id:
            raise ValueError("Il token non appartiene all'account Instagram configurato")
        return me

    def refresh(self):
        result = self.http.json("GET", "https://graph.instagram.com/refresh_access_token", retry=False,
            params={"grant_type": "ig_refresh_token", "access_token": self.token})
        if not isinstance(result.get("access_token"), str) or result.get("expires_in", 0) < 86400:
            raise ValueError("Rinnovo del token non confermato")
        return result

    def create(self, caption):
        result = self.http.json("POST", self.root + f"/{self.user_id}/media", headers=self.headers,
            data={"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true"})
        container = str(result.get("id", ""))
        if not re.fullmatch(r"[0-9]+", container):
            raise ValueError("ID container Instagram non valido")
        uri = result.get("uri", "")
        parsed = urlparse(uri)
        if (parsed.scheme != "https" or parsed.netloc != "rupload.facebook.com"
                or parsed.path != f"/ig-api-upload/{self.version}/{container}" or parsed.query or parsed.fragment):
            raise ValueError("Destinazione upload Instagram inattesa")
        return container, uri

    def upload(self, uri, path):
        # URI was validated at creation, and is revalidated on persisted recovery.
        parsed = urlparse(uri)
        if (parsed.scheme != "https" or parsed.netloc != "rupload.facebook.com"
                or not re.fullmatch(rf"/ig-api-upload/{re.escape(self.version)}/[0-9]+", parsed.path)
                or parsed.query or parsed.fragment):
            raise ValueError("Destinazione upload non autorizzata")
        size = path.stat().st_size
        if not 0 < size < 50_000_000:
            raise ValueError("Dimensione del Reel non valida")
        result = self.http.json("POST", uri,
            headers={"Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(size),
                     "Content-Type": "application/octet-stream"}, content=path.read_bytes())
        if result.get("success") is not True:
            raise ValueError("Caricamento del video non confermato")

    def status(self, container):
        result = self.http.json("GET", self.root + f"/{container}", headers=self.headers,
                               params={"fields": "status_code"})
        status = result.get("status_code")
        if status not in {"IN_PROGRESS", "FINISHED", "PUBLISHED", "ERROR", "EXPIRED"}:
            raise ValueError("Stato del container sconosciuto")
        return status

    def wait_ready(self, container):
        for _ in range(20):
            status = self.status(container)
            if status != "IN_PROGRESS":
                return status
            self.sleep(15)
        raise RemoteError(504)

    def publish(self, container):
        # Exactly one attempt. A timeout/5xx is ambiguous and must be reconciled.
        result = self.http.json("POST", self.root + f"/{self.user_id}/media_publish", headers=self.headers,
                               data={"creation_id": container})
        media_id = str(result.get("id", ""))
        if not re.fullmatch(r"[0-9]+", media_id):
            raise ValueError("Pubblicazione con esito incerto")
        return media_id
