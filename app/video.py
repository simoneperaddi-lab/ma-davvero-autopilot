"""Local-only video assembly; no samples, downloads, TTS or paid services."""
import math
import struct
import subprocess
import textwrap
import time
import wave
from pathlib import Path

from app.models import Content

AUDIO_LICENSE = """MA DAVVERO? procedural audio bed
Generated locally using mathematical sine waves; no third-party samples.
The contributors dedicate this generated audio to the public domain under CC0 1.0.
https://creativecommons.org/publicdomain/zero/1.0/
This does not license any source article or third-party material.
"""


def timestamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def subtitles(content: Content):
    cues = []
    for i, slide in enumerate(content.slides):
        text = " ".join(f"{slide.title}. {slide.text}".split()).replace("<", "‹").replace(">", "›")
        chunks = textwrap.wrap(text, 72)
        for j, chunk in enumerate(chunks):
            start, end = i * 4 + j * 4 / len(chunks), i * 4 + (j + 1) * 4 / len(chunks)
            cues.append(f"{len(cues) + 1}\n{timestamp(start)} --> {timestamp(end)}\n{chunk}\n")
    return "\n".join(cues)


def original_audio(path: Path, seconds: int):
    rate = 22050
    # A quiet, simple two-note bed. No external recording, voice or copyright sample.
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        for second in range(seconds):
            samples = bytearray()
            for i in range(rate):
                t = second + i / rate
                fade = min(1, t / 0.5, (seconds - t) / 0.5)
                value = 900 * fade * (math.sin(2 * math.pi * 220 * t) + 0.5 * math.sin(2 * math.pi * 330 * t))
                samples.extend(struct.pack("<h", int(value)))
            output.writeframes(samples)


def encode(directory: Path, count: int, style: str, audio: str):
    base = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-filter_complex_threads", "1"]
    if style == "dynamic":
        for i in range(count):
            duration = "4.4" if i < count - 1 else "4"
            base += ["-loop", "1", "-framerate", "24", "-t", duration, "-i", str(directory / f"frame-{i:02}.png")]
        filters = []
        for i in range(count):
            filters.append(f"[{i}:v]zoompan=z='1+0.00035*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=24,setsar=1,format=yuv420p[v{i}]")
        previous = "v0"
        for i in range(1, count):
            label = f"mix{i}"
            filters.append(f"[{previous}][v{i}]xfade=transition=fade:duration=0.4:offset={4 * i}[{label}]")
            previous = label
        base += ["-filter_complex", ";".join(filters)]
        video_map = f"[{previous}]"
        next_input = count
    else:
        base += ["-framerate", "1/4", "-i", str(directory / "frame-%02d.png")]
        video_map, next_input = "0:v:0", 1
    base += ["-i", str(directory / "subtitles.srt")]
    subtitle_index = next_input
    if audio == "original":
        base += ["-i", str(directory / "audio.wav")]
    base += ["-map", video_map, "-map", f"{subtitle_index}:0"]
    if audio == "original":
        base += ["-map", f"{subtitle_index + 1}:a:0", "-c:a", "aac", "-b:a", "96k", "-ar", "48000"]
    return base + [
        "-c:v", "libx264", "-threads", "2", "-preset", "fast", "-r", "24", "-pix_fmt", "yuv420p",
        "-c:s", "mov_text", "-metadata:s:s:0", "language=ita", "-disposition:s:0", "default",
        "-t", str(count * 4), "-movflags", "+faststart", str(directory / "reel.mp4"),
    ]


def render_video(directory: Path, content: Content, style: str, audio: str):
    (directory / "subtitles.srt").write_text(subtitles(content), encoding="utf-8")
    if audio == "original":
        original_audio(directory / "audio.wav", len(content.slides) * 4)
        (directory / "audio-license.txt").write_text(AUDIO_LICENSE, encoding="utf-8")
    started = time.monotonic()

    def run(selected_style):
        remaining = 180 - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired("ffmpeg", 180)
        subprocess.run(encode(directory, len(content.slides), selected_style, audio), check=True,
                       capture_output=True, timeout=remaining)

    note = ""
    try:
        run(style)
    except subprocess.CalledProcessError:
        if style != "dynamic":
            raise
        # Only a quick filter/encoder failure can fall back within the same deadline.
        run("static")
        style = "static"
        note = "Filtri dinamici non disponibili: esportato fallback statico con sottotitoli."
    finally:
        (directory / "audio.wav").unlink(missing_ok=True)
    return style, note
