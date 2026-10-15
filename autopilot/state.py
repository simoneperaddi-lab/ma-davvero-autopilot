"""Durable non-secret ledger: independent branch, optimistic GitHub SHA writes."""
import base64
import json
from pathlib import Path

from autopilot.http import Blocked, RemoteError


def empty_state():
    return {"version": 1, "account_id": None, "entries": [], "events": [], "token": {}}


def check_state(value):
    if not isinstance(value, dict) or value.get("version") != 1:
        raise Blocked("Registro assente o incompatibile: non azzerarlo per riprovare")
    if not isinstance(value.get("entries"), list) or not isinstance(value.get("events"), list):
        raise Blocked("Registro corrotto")
    return value


class LocalState:
    """Simulation only. A live run always uses GitHubState."""
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        return check_state(json.loads(self.path.read_text())) if self.path.exists() else empty_state()

    def save(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
        temp.replace(self.path)


class GitHubState:
    branch = "autopilot-state"

    def __init__(self, http, repo, token):
        self.http = http
        self.root = f"https://api.github.com/repos/{repo}"
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"}
        self.sha = None

    def load(self):
        try:
            data = self.http.json("GET", self.root + "/contents/ledger.json", headers=self.headers,
                                  params={"ref": self.branch})
        except RemoteError as exc:
            if exc.status != 404:
                raise
            # A preexisting branch without ledger is corruption, not a fresh install.
            try:
                self.http.json("GET", self.root + f"/git/ref/heads/{self.branch}", headers=self.headers)
            except RemoteError as branch_error:
                if branch_error.status != 404:
                    raise
            else:
                raise Blocked("Branch del registro esistente senza ledger.json")
            # Bootstrap from current workflow SHA, never reset or modify main.
            import os
            commit = os.environ["GITHUB_SHA"]
            self.http.json("POST", self.root + "/git/refs", headers=self.headers,
                           json={"ref": f"refs/heads/{self.branch}", "sha": commit})
            value = empty_state()
            self.save(value)
            return value
        self.sha = data["sha"]
        if data.get("encoding") == "none":
            # Contents API omits inline content above 1 MB. Raw media supports up to 100 MB.
            value = self.http.json("GET", self.root + "/contents/ledger.json",
                headers={**self.headers, "Accept": "application/vnd.github.raw+json"},
                params={"ref": self.branch})
            latest = self.http.json("GET", self.root + "/contents/ledger.json", headers=self.headers,
                                    params={"ref": self.branch})
            if latest["sha"] != self.sha:
                raise Blocked("Registro modificato durante la lettura")
            return check_state(value)
        return check_state(json.loads(base64.b64decode(data["content"])))

    def save(self, value):
        check_state(value)
        body = {"message": "autopilot: persist publication ledger [skip ci]", "branch": self.branch,
                "content": base64.b64encode(json.dumps(value, ensure_ascii=False, indent=2).encode()).decode()}
        if self.sha:
            body["sha"] = self.sha
        result = self.http.json("PUT", self.root + "/contents/ledger.json", headers=self.headers, json=body)
        self.sha = result["content"]["sha"]


class SecretStore:
    """Rotate only IG_ACCESS_TOKEN using a separately scoped GitHub credential."""
    def __init__(self, http, repo, token):
        self.http, self.repo, self.token = http, repo, token

    def save_token(self, token):
        from nacl.public import PublicKey, SealedBox
        url = f"https://api.github.com/repos/{self.repo}/actions/secrets"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"}
        key = self.http.json("GET", url + "/public-key", headers=headers)
        encrypted = SealedBox(PublicKey(base64.b64decode(key["key"]))).encrypt(token.encode())
        # GitHub responds 201/204 with an empty body for this endpoint.
        response = self.http.client.put(url + "/IG_ACCESS_TOKEN", headers=headers,
            json={"key_id": key["key_id"], "encrypted_value": base64.b64encode(encrypted).decode()})
        if response.status_code not in (201, 204):
            raise RemoteError(response.status_code)
