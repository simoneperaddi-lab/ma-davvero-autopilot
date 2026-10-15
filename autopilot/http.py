"""Bounded network calls with redacted errors and explicit retry policy."""
import time
import httpx


class RemoteError(RuntimeError):
    def __init__(self, status=0):
        self.status = status
        super().__init__(f"Servizio remoto non disponibile (HTTP {status or 'rete'}); nessun segreto nei log")


class HTTP:
    def __init__(self, client=None, sleep=time.sleep):
        self.client = client or httpx.Client(timeout=httpx.Timeout(45, connect=15), follow_redirects=False)
        self.sleep = sleep

    def json(self, method, url, *, retry=None, **kwargs):
        # Never replay a mutating request automatically after an ambiguous response.
        attempts = 3 if (method == "GET" if retry is None else retry) else 1
        for attempt in range(attempts):
            try:
                response = self.client.request(method, url, **kwargs)
                if response.status_code >= 300:
                    raise RemoteError(response.status_code)
                if len(response.content) > 8_000_000:
                    raise RemoteError(413)
                return response.json()
            except (httpx.HTTPError, ValueError, RemoteError) as exc:
                status = exc.status if isinstance(exc, RemoteError) else 0
                if attempt + 1 == attempts or (status and status != 429 and status < 500):
                    raise RemoteError(status) from None
                # Cap retry delay even if a server requests an excessive Retry-After.
                self.sleep(2 ** attempt)
        raise RemoteError()
