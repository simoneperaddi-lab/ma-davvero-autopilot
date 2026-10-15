import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.controls import Controls, LimitError
from app import editorial, research
from app.generation import GenerationError, generate
from app.media import MediaError, MediaService, caption
from app.models import (Artifact, AttachSource, ClaimReview, Content, EditorialTransition,
                        ExportRequest, GenerateRequest, ResearchSource, SourceSearch, Versioned)
from app.security import authorize, deny, validate_security
from app.storage import ConflictError, StorageError, create_store

STATIC = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None):
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        validate_security(config)
        app.state.controls = Controls(config.mad_data_dir)
        app.state.store = create_store(config)
        app.state.media = MediaService(config.mad_data_dir)
        yield

    app = FastAPI(title="MA DAVVERO? — Content Studio", version="0.2.0", lifespan=lifespan)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        try:
            response = authorize(request, config, request.app.state.controls)
        except LimitError as exc:
            response = deny(str(exc), 429)
        if response is None:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                chunks, length = [], 0
                async for chunk in request.stream():
                    length += len(chunk)
                    if length > 32_768:
                        response = deny("Corpo richiesta troppo grande (32 KB).", 413)
                        break
                    chunks.append(chunk)
                if response is None:
                    request._body = b"".join(chunks)
            if response is None:
                response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path == "/":
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.exception_handler(StorageError)
    async def storage_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_error(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(editorial.EditorialError)
    async def editorial_error(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(research.ResearchError)
    async def research_error(request, exc):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(LimitError)
    async def limit_error(request, exc):
        return deny(str(exc), 429)

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "provider": config.mad_provider, "storage": config.mad_storage,
                "ffmpeg_available": shutil.which("ffmpeg") is not None, "instagram_publishing": False}

    @app.get("/api/contents", response_model=list[Content])
    def list_contents(request: Request):
        return request.app.state.store.list()

    @app.post("/api/generate", response_model=list[Content], status_code=201)
    def generate_contents(body: GenerateRequest, request: Request):
        try:
            contents = generate(config, body, request.app.state.controls)
        except (GenerationError, ValueError) as exc:
            message = str(exc) if isinstance(exc, GenerationError) else "Risposta AI non valida. Riprova la generazione."
            raise HTTPException(502, message) from exc
        request.app.state.store.save(contents)
        return contents

    def find_content(content_id, request):
        content = request.app.state.store.get(content_id)
        if content is None:
            raise HTTPException(404, "Contenuto non trovato.")
        return content

    @app.get("/api/contents/{content_id}", response_model=Content)
    def get_content(content_id: UUID, request: Request):
        return find_content(content_id, request)

    def versioned(content_id, revision, request):
        content = find_content(content_id, request)
        if content.revision != revision:
            raise ConflictError("Versione superata: ricaricare il contenuto.")
        return content

    @app.get("/api/usage")
    def usage(request: Request):
        return request.app.state.controls.report(config)

    @app.post("/api/sources/search", response_model=list[ResearchSource])
    def source_search(body: SourceSearch, request: Request):
        results = research.search(body.query, body.limit)
        for source in results:
            request.app.state.controls.cache(source)
        return results

    @app.post("/api/contents/{content_id}/sources", response_model=Content)
    def attach_source(content_id: UUID, body: AttachSource, request: Request):
        content = versioned(content_id, body.revision, request)
        if body.research_id is not None:
            cached = request.app.state.controls.cached(body.research_id)
            if cached is None:
                raise HTTPException(404, "Risultato di ricerca non trovato; ripetere la ricerca.")
            source = ResearchSource.model_validate(cached)
        else:
            if body.suggested_index >= len(content.sources):
                raise HTTPException(422, "Indice fonte non valido.")
            suggestion = content.sources[body.suggested_index]
            source = ResearchSource(title=suggestion.title, url=suggestion.url, origin="suggested")
        return request.app.state.store.mutate(content_id, body.revision,
            lambda current: editorial.attach(current, source, request.state.actor))

    @app.post("/api/contents/{content_id}/sources/{source_id}/check", response_model=Content)
    def check_source(content_id: UUID, source_id: UUID, body: Versioned, request: Request):
        content = versioned(content_id, body.revision, request)
        editorial.editable(content)
        source = next((s for s in content.research_sources if s.id == source_id), None)
        if source is None:
            raise HTTPException(404, "Fonte non trovata.")
        checked = research.check(source)
        return request.app.state.store.mutate(content_id, body.revision,
            lambda current: editorial.checked(current, checked, request.state.actor))

    @app.post("/api/contents/{content_id}/claims/{claim_id}/review", response_model=Content)
    def review_claim(content_id: UUID, claim_id: UUID, body: ClaimReview, request: Request):
        versioned(content_id, body.revision, request)
        return request.app.state.store.mutate(content_id, body.revision,
            lambda current: editorial.review_claim(current, claim_id, body, request.state.actor))

    @app.post("/api/contents/{content_id}/editorial", response_model=Content)
    def editorial_transition(content_id: UUID, body: EditorialTransition, request: Request):
        versioned(content_id, body.revision, request)
        return request.app.state.store.mutate(content_id, body.revision,
            lambda current: editorial.transition(current, body, request.state.actor))

    @app.get("/api/contents/{content_id}/caption")
    def get_caption(content_id: UUID, request: Request):
        return Response(caption(find_content(content_id, request)), media_type="text/plain",
                        headers={"Content-Disposition": 'attachment; filename="caption.txt"'})

    @app.post("/api/contents/{content_id}/exports", response_model=Artifact, status_code=201)
    def export(content_id: UUID, body: ExportRequest, request: Request):
        content = find_content(content_id, request)
        try:
            return request.app.state.media.export(content, body.kind, style=body.style, audio=body.audio)
        except MediaError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/artifacts/{artifact_id}")
    def download(artifact_id: UUID, request: Request):
        result = request.app.state.media.get(artifact_id)
        if result is None:
            raise HTTPException(404, "Esportazione non trovata.")
        artifact, path = result
        find_content(artifact.content_id, request)
        return FileResponse(path, filename=artifact.filename,
                            media_type="application/zip" if artifact.kind == "carousel" else "video/mp4")

    @app.get("/api/artifacts/{artifact_id}/subtitles")
    def download_subtitles(artifact_id: UUID, request: Request):
        result = request.app.state.media.get(artifact_id)
        if result is None or result[0].kind != "reel":
            raise HTTPException(404, "Sottotitoli non trovati.")
        artifact, path = result
        find_content(artifact.content_id, request)
        subtitles = path.parent / "subtitles.srt"
        if not subtitles.is_file():
            raise HTTPException(404, "Sottotitoli non trovati per questo export MVP.")
        return FileResponse(subtitles, media_type="text/plain", filename="subtitles.srt")

    @app.get("/api/artifacts/{artifact_id}/audio-license")
    def download_audio_license(artifact_id: UUID, request: Request):
        result = request.app.state.media.get(artifact_id)
        if result is None or result[0].audio != "original":
            raise HTTPException(404, "Licenza audio non trovata.")
        find_content(result[0].content_id, request)
        return FileResponse(result[1].parent / "audio-license.txt", media_type="text/plain", filename="audio-license.txt")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
