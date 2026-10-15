import io
import json
import shutil
import subprocess
import zipfile

import pytest
from PIL import Image

from app.media import MediaService, render_slide
from app.models import Content
from app.demo import example
from app.models import Category


def test_carousel_contains_images_caption_and_persistent_download(client, settings):
    content = client.post("/api/generate", json={}).json()[0]
    response = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "carousel"})
    assert response.status_code == 201
    artifact = response.json()
    download = client.get(artifact["download_url"])
    assert download.status_code == 200
    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        assert set(archive.namelist()) == {"caption.txt", *[f"frame-{i:02}.png" for i in range(5)]}
        for name in archive.namelist():
            if name.endswith(".png"):
                image = Image.open(io.BytesIO(archive.read(name)))
                assert image.size == (1080, 1350)
                assert image.getbbox() is not None
        assert content["sources"][0]["url"] in archive.read("caption.txt").decode()
    # Metadata on disk survives a new service instance.
    assert MediaService(settings.mad_data_dir).get(artifact["id"]) is not None


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg and ffprobe required")
def test_real_vertical_reel(client, tmp_path):
    content = client.post("/api/generate", json={"category": "spazio"}).json()[0]
    response = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "reel"})
    assert response.status_code == 201, response.text
    download = client.get(response.json()["download_url"])
    assert download.headers["content-type"] == "video/mp4"
    path = tmp_path / "download.mp4"
    path.write_bytes(download.content)
    result = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(path)], check=True, capture_output=True, text=True)
    metadata = json.loads(result.stdout)
    stream = metadata["streams"][0]
    assert (stream["width"], stream["height"]) == (1080, 1920)
    assert stream["codec_name"] == "h264"
    assert stream["pix_fmt"] == "yuv420p"
    assert not any(s["codec_type"] == "audio" for s in metadata["streams"])
    assert any(s["codec_name"] == "mov_text" for s in metadata["streams"])
    assert float(metadata["format"]["duration"]) == pytest.approx(20, abs=0.1)


def test_missing_ffmpeg_gives_actionable_error_without_artifacts(client, settings, monkeypatch):
    monkeypatch.setattr("app.media.shutil.which", lambda _: None)
    content = client.post("/api/generate", json={}).json()[0]
    result = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "reel"})
    assert result.status_code == 503
    assert "FFmpeg" in result.json()["detail"]
    assert list((settings.mad_data_dir / "exports").iterdir()) == []


def test_encoder_failure_cleans_partial_files_and_releases_lock(client, settings, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("ffmpeg", 180)
    monkeypatch.setattr("app.media.shutil.which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr("app.media.subprocess.run", fail)
    content = client.post("/api/generate", json={}).json()[0]
    url = f'/api/contents/{content["id"]}/exports'
    assert client.post(url, json={"kind": "reel"}).status_code == 503
    assert list((settings.mad_data_dir / "exports").iterdir()) == []
    assert client.post(url, json={"kind": "carousel"}).status_code == 201


def test_export_busy_rejected(client):
    content = client.post("/api/generate", json={}).json()[0]
    lock = client.app.state.media.lock
    lock.acquire()
    try:
        response = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "carousel"})
        assert response.status_code == 503
        assert "già in corso" in response.json()["detail"]
    finally:
        lock.release()


def test_maximum_text_does_not_overlap_review_footer(tmp_path):
    content = Content(**example(Category.space).model_dump(), provider="demo")
    normal = tmp_path / "normal.png"
    long = tmp_path / "long.png"
    render_slide(content, 0, 1350, normal)
    content.slides[0].title = "W" * 70
    content.slides[0].text = "W" * 320
    render_slide(content, 0, 1350, long)
    footer = (0, 1010, 1080, 1350)
    assert Image.open(normal).crop(footer).tobytes() == Image.open(long).crop(footer).tobytes()
