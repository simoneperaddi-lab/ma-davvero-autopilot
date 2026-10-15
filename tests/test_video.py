import json
import shutil
import subprocess

import pytest

from app.video import subtitles
from app.models import Content
from app.demo import example
from app.models import Category


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg and ffprobe required")
def test_dynamic_reel_audio_subtitles_and_motion(client, tmp_path):
    content = client.post("/api/generate", json={}).json()[0]
    response = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "reel", "style": "dynamic", "audio": "original"})
    assert response.status_code == 201, response.text
    artifact = response.json()
    assert artifact["style"] == "dynamic", artifact
    path = tmp_path / "dynamic.mp4"
    path.write_bytes(client.get(artifact["download_url"]).content)
    result = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(path)], check=True, capture_output=True, text=True)
    metadata = json.loads(result.stdout)
    streams = {s["codec_type"]: s for s in metadata["streams"]}
    assert (streams["video"]["width"], streams["video"]["height"]) == (1080, 1920)
    assert streams["audio"]["codec_name"] == "aac"
    assert streams["subtitle"]["codec_name"] == "mov_text"
    assert float(metadata["format"]["duration"]) == pytest.approx(20, abs=.1)
    checksums = subprocess.run(["ffmpeg", "-v", "error", "-ss", "1", "-i", str(path), "-map", "0:v:0", "-frames:v", "2", "-f", "framemd5", "-"], check=True, capture_output=True, text=True)
    frames = [line for line in checksums.stdout.splitlines() if not line.startswith("#")]
    assert len(frames) == 2
    assert frames[0].split(",")[-1].strip() != frames[1].split(",")[-1].strip()
    srt = client.get(artifact["download_url"] + "/subtitles")
    assert "00:00:00,000 -->" in srt.text
    assert "00:00:20,000" in srt.text
    license = client.get(artifact["download_url"] + "/audio-license")
    assert "CC0" in license.text


def test_dynamic_filter_failure_uses_declared_static_fallback(client, monkeypatch):
    real_run = subprocess.run
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, command, stderr=b"Filter unavailable")
        return real_run(command, **kwargs)
    monkeypatch.setattr("app.video.subprocess.run", run)
    content = client.post("/api/generate", json={}).json()[0]
    response = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "reel", "style": "dynamic"})
    assert response.status_code == 201, response.text
    assert response.json()["style"] == "static"
    assert "fallback" in response.json()["render_note"]
    assert len(calls) == 2


def test_subtitle_cues_are_plain_text_and_timed():
    content = Content(**example(Category.space).model_dump(), provider="demo")
    content.slides[0].text = "<script>not executable</script> text for captions"
    srt = subtitles(content)
    assert "<script>" not in srt
    assert "00:00:00,000" in srt and "00:00:20,000" in srt
