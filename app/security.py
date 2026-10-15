import base64
import binascii
import ipaddress
import secrets
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.controls import Controls, LimitError


def validate_security(settings: Settings):
    if settings.mad_public_origin:
        origin = urlsplit(settings.mad_public_origin)
        if origin.scheme != "https" or not origin.hostname or origin.path not in {"", "/"} or origin.query or origin.fragment or origin.username or origin.password:
            raise ValueError("MAD_PUBLIC_ORIGIN deve essere un'origine HTTPS senza path, query o credenziali.")
    if settings.mad_auth_mode == "basic":
        if not settings.mad_auth_password or len(settings.mad_auth_password.get_secret_value()) < 16:
            raise ValueError("MAD_AUTH_PASSWORD deve contenere almeno 16 caratteri; per demo solo locale usare MAD_AUTH_MODE=local.")
        if not settings.mad_auth_username.strip() or ":" in settings.mad_auth_username:
            raise ValueError("MAD_AUTH_USERNAME non valido.")


def deny(message, status=401):
    headers = {"Cache-Control": "no-store"}
    if status == 401:
        headers["WWW-Authenticate"] = 'Basic realm="MA DAVVERO", charset="UTF-8"'
    if status == 429:
        headers["Retry-After"] = "60"
    return JSONResponse({"detail": message}, status_code=status, headers=headers)


def authorize(request: Request, settings: Settings, controls: Controls):
    peer = request.client.host if request.client else "unknown"
    actor = "local-editor"
    if settings.mad_auth_mode == "local":
        try:
            local = ipaddress.ip_address(peer).is_loopback
        except ValueError:
            local = False
        if not local:
            return deny("Modalità locale accessibile solo da loopback.", 403)
    else:
        try:
            scheme, encoded = request.headers.get("authorization", "").split(" ", 1)
            if scheme.lower() != "basic":
                raise ValueError()
            username, password = base64.b64decode(encoded, validate=True).decode("utf-8").split(":", 1)
        except (ValueError, binascii.Error, UnicodeError):
            controls.rate(f"auth-failure:{peer}", 20)
            return deny("Autenticazione richiesta.")
        valid_user = secrets.compare_digest(username.encode(), settings.mad_auth_username.encode())
        valid_password = secrets.compare_digest(password.encode(), settings.mad_auth_password.get_secret_value().encode())
        if not (valid_user and valid_password):
            controls.rate(f"auth-failure:{peer}", 20)
            return deny("Credenziali non valide.")
        actor = settings.mad_auth_username
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        expected = settings.mad_public_origin.rstrip("/") or str(request.base_url).rstrip("/")
        if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != expected):
            return deny("Origine della richiesta non consentita.", 403)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return deny("Le operazioni richiedono application/json.", 415)
    request.state.actor = actor
    if request.url.path.startswith("/api/"):
        controls.rate(f"api:{actor}", settings.mad_rate_per_minute)
        if request.method == "POST":
            path = request.url.path
            action = "generate" if path == "/api/generate" else "export" if path.endswith("/exports") else "research" if "/sources" in path else "editorial"
            limit = {"generate": settings.mad_generate_per_minute, "export": settings.mad_export_per_minute, "research": settings.mad_research_per_minute}.get(action, 30)
            controls.rate(f"action:{actor}:{action}", limit)
    return None
