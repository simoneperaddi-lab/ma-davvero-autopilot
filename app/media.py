import json
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont

from app.models import Artifact, Content
from app.video import render_video


class MediaError(Exception):
    pass


def font(size: int):
    path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default(size=size)


def wrapped_lines(draw, text, size, width=904):
    face = font(size)
    lines, line = [], ""
    # Break at character boundaries when a single word exceeds the canvas.
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=face) <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = ""
        for char in word:
            if line and draw.textlength(line + char, font=face) > width:
                lines.append(line)
                line = ""
            line += char
    if line:
        lines.append(line)
    return lines


def paragraph(draw, text, y, size, fill, width=904, gap=14):
    face = font(size)
    for line in wrapped_lines(draw, text, size, width):
        draw.text((88, y), line, font=face, fill=fill)
        y += size + gap
    return y


def render_slide(content: Content, index: int, height: int, target: Path):
    slide = content.slides[index]
    image = Image.new("RGB", (1080, height), "#10251e")
    draw = ImageDraw.Draw(image)
    draw.ellipse((680, -250, 1350, 420), fill="#243e2b")
    draw.text((88, 105), "MA DAVVERO?", font=font(42), fill="#cefc83")
    draw.text((88, 175), f"SCIENZA DA SCOPRIRE  /  {content.category.value.upper()}", font=font(23), fill="#acbfb1")
    top = 390 if height == 1920 else 300
    title_size, body_size = 62, 43
    while (top + len(wrapped_lines(draw, slide.title, title_size)) * (title_size + 14)
           + 48 + len(wrapped_lines(draw, slide.text, body_size)) * (body_size + 14) > height - 340):
        title_size -= 2
        body_size -= 1
        if body_size < 20:
            raise MediaError("Testo troppo lungo per il formato selezionato.")
    end = paragraph(draw, slide.title, top, title_size, "#cefc83")
    paragraph(draw, slide.text, end + 48, body_size, "#f6f3e9")
    draw.line((88, height - 280, 992, height - 280), fill="#57735d", width=2)
    draw.text((88, height - 240), "BOZZA • DA VERIFICARE", font=font(28), fill="#cefc83")
    draw.text((88, height - 180), "Fonti e note nella caption allegata", font=font(25), fill="#acbfb1")
    draw.text((890, height - 130), f"{index + 1:02}/{len(content.slides):02}", font=font(25), fill="#f6f3e9")
    image.save(target, "PNG")


def caption(content: Content):
    sources = "\n".join(f"- {s.title}: {s.url}" for s in content.sources)
    evidence = "\n".join(f"- {c.label}: {c.outcome} | revisore: {c.reviewer or 'nessuno'} | {c.note}" for c in content.claims)
    research = "\n".join(f"- {s.title}: {s.url} | raggiungibile={s.reachable} | {s.check_note}" for s in content.research_sources)
    return f"BOZZA — DA VERIFICARE PRIMA DI QUALSIASI PUBBLICAZIONE\nStato editoriale: {content.status} | revisione {content.revision}\n\n{content.caption}\n\nFonti suggerite (non verificate automaticamente):\n{sources}\n\nRicerca e recupero:\n{research}\n\nVerifiche umane:\n{evidence}\n\nControlli editoriali:\n{content.verification_notes}\n"


class MediaService:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "exports"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def export(self, content: Content, kind: str, *, style="static", audio="none") -> Artifact:
        if not self.lock.acquire(blocking=False):
            raise MediaError("Un'esportazione è già in corso. Riprova tra poco.")
        target = self.root / str(uuid4())
        try:
            if kind == "reel" and not shutil.which("ffmpeg"):
                raise MediaError("FFmpeg non disponibile. Installarlo per esportare i Reel.")
            target.mkdir()
            height = 1350 if kind == "carousel" else 1920
            for i in range(len(content.slides)):
                render_slide(content, i, height, target / f"frame-{i:02}.png")
            (target / "caption.txt").write_text(caption(content), encoding="utf-8")
            if kind == "carousel":
                filename = "carosello.zip"
                with zipfile.ZipFile(target / filename, "w", zipfile.ZIP_DEFLATED) as archive:
                    for item in sorted(target.glob("*.png")):
                        archive.write(item, item.name)
                    archive.write(target / "caption.txt", "caption.txt")
            else:
                filename = "reel.mp4"
                try:
                    style, note = render_video(target, content, style, audio)
                except (subprocess.SubprocessError, OSError) as exc:
                    raise MediaError("Esportazione FFmpeg non riuscita. Controllare installazione e risorse disponibili.") from exc
            artifact = Artifact(id=UUID(target.name), content_id=content.id, kind=kind, filename=filename,
                                download_url=f"/api/artifacts/{target.name}", style=style if kind == "reel" else "static",
                                audio=audio if kind == "reel" else "none", render_note=note if kind == "reel" else "",
                                content_revision=content.revision)
            (target / "artifact.json").write_text(artifact.model_dump_json(), encoding="utf-8")
            # Intermediate frames are not needed after the final export.
            for frame in target.glob("*.png"):
                frame.unlink()
            return artifact
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
        finally:
            self.lock.release()

    def get(self, artifact_id: UUID) -> tuple[Artifact, Path] | None:
        directory = self.root / str(artifact_id)
        meta = directory / "artifact.json"
        if not meta.exists():
            return None
        artifact = Artifact.model_validate(json.loads(meta.read_text(encoding="utf-8")))
        # Derive filenames from the enum, never from arbitrary metadata.
        path = directory / ("carosello.zip" if artifact.kind == "carousel" else "reel.mp4")
        return (artifact, path) if path.is_file() else None
