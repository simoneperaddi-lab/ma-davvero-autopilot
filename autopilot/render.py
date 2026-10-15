"""Reuse the studio's original graphic and animation engine for verified facts."""
import json
import subprocess
from pathlib import Path

from app.media import render_slide
from app.models import Content
from app.video import render_video


def render(fact, directory, audio=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    content = Content.model_validate(fact["content"])
    for i in range(len(content.slides)):
        render_slide(content, i, 1920, directory / f"frame-{i:02}.png", verified_catalogue=True, simulation=fact.get("simulation", False))
    style, note = render_video(directory, content, "dynamic", "original" if audio else "none")
    # Instagram receives only H.264/AAC. Slide text is already burned into pixels;
    # retain SRT separately rather than relying on a platform to preserve mov_text.
    upload = directory / "instagram.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(directory / "reel.mp4"),
                    "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy", "-movflags", "+faststart", str(upload)],
                   check=True, capture_output=True, timeout=30)
    upload.replace(directory / "reel.mp4")
    (directory / "caption.txt").write_text(content.caption, encoding="utf-8")
    (directory / "evidence.json").write_text(json.dumps(fact, indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "render.json").write_text(json.dumps({"style": style, "note": note}), encoding="utf-8")
    for frame in directory.glob("frame-*.png"):
        frame.unlink()
    return directory / "reel.mp4"
