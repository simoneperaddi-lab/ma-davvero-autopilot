import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.generation import GenerationError, generate
from app.media import MediaError, MediaService, caption
from app.models import Artifact, Content, ExportRequest, GenerateRequest
from app.storage import StorageError, create_store

STATIC = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None):
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = create_store(config)
        app.state.media = MediaService(config.mad_data_dir)
        yield

    app = FastAPI(title="MA DAVVERO? — Content Studio", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path == "/":
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.exception_handler(StorageError)
    async def storage_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

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
            contents = generate(config, body)
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

    @app.get("/api/contents/{content_id}/caption")
    def get_caption(content_id: UUID, request: Request):
        return Response(caption(find_content(content_id, request)), media_type="text/plain",
                        headers={"Content-Disposition": 'attachment; filename="caption.txt"'})

    @app.post("/api/contents/{content_id}/exports", response_model=Artifact, status_code=201)
    def export(content_id: UUID, body: ExportRequest, request: Request):
        content = find_content(content_id, request)
        try:
            return request.app.state.media.export(content, body.kind)
        except MediaError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/artifacts/{artifact_id}")
    def download(artifact_id: UUID, request: Request):
        result = request.app.state.media.get(artifact_id)
        if result is None:
            raise HTTPException(404, "Esportazione non trovata.")
        artifact, path = result
        return FileResponse(path, filename=artifact.filename,
                            media_type="application/zip" if artifact.kind == "carousel" else "video/mp4")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
