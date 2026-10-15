"""Render the measured phenomenon, not a slideshow. Existing pipeline contract."""
import json
import subprocess
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw

from app.video import timestamp
from autopilot.orbital import OrbitalScene, WIDTH, HEIGHT, FPS, DURATION, CUT, BPM
from autopilot.soundtrack import compose, LICENSE

# One representative frame per shot; exported so the actual video is reviewable.
PREVIEW_TIMES = [.5, 3.25, 6.25, 8.75, 11.25, 13.75, 16.25, 18.75]


def render(fact, directory, audio=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    scene = OrbitalScene(fact['source_row'], simulation=fact.get('simulation', False))
    if fact['subject'] != fact['source_row']['pl_name']:
        raise ValueError('Identità della fonte non coerente')
    wav = directory / 'audio.wav'
    temporary = directory / 'rendering.mp4'
    if audio:
        compose(wav)
    cmd = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{WIDTH}x{HEIGHT}', '-r', str(FPS), '-i', 'pipe:0']
    if audio:
        cmd += ['-i', str(wav), '-map', '0:v:0', '-map', '1:a:0', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000']
    cmd += ['-vf', 'scale=1080:1920:flags=lanczos', '-c:v', 'libx264', '-threads', '2', '-filter_threads', '1',
            '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', '-t', str(DURATION), '-movflags', '+faststart', str(temporary)]
    try:
        # File-backed stderr cannot deadlock a full pipe; watchdog also bounds blocked writes.
        with tempfile.TemporaryFile() as errors:
            with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors) as process:
                watchdog = threading.Timer(180, process.kill)
                watchdog.start()
                try:
                    for i in range(FPS*DURATION):
                        process.stdin.write(scene.frame(i/FPS).tobytes())
                    process.stdin.close()
                    if process.wait(timeout=30):
                        raise RuntimeError('Encoding del Reel orbitale non riuscito')
                except BaseException:
                    process.kill()
                    process.wait()
                    raise
                finally:
                    watchdog.cancel()
        temporary.replace(directory / 'reel.mp4')
    finally:
        wav.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
    if audio:
        (directory / 'audio-license.txt').write_text(LICENSE, encoding='utf-8')
    else:
        (directory / 'audio-license.txt').unlink(missing_ok=True)
    (directory / 'caption.txt').write_text(fact['content']['caption'], encoding='utf-8')
    (directory / 'evidence.json').write_text(json.dumps(fact, indent=2, ensure_ascii=False), encoding='utf-8')
    (directory / 'subtitles.srt').write_text('\n'.join(
        f'{i+1}\n{timestamp(i*CUT)} --> {timestamp((i+1)*CUT)}\n' + '\n'.join(lines) + '\n'
        for i, lines in enumerate(scene.cues)), encoding='utf-8')
    (directory / 'render.json').write_text(json.dumps({
        'style': 'orbital-motion', 'duration': DURATION, 'fps': FPS, 'bpm': BPM,
        'cuts_seconds': [i*CUT for i in range(8)], 'visual_script': scene.cues,
        'scientific_value': {'orbital_period_days': scene.period, 'source_sha256': fact['source_sha256']},
        'schematic': 'Colours, sizes, viewing angle and accelerated motion are illustrative; no rotation period is inferred.',
        'audio': 'original' if audio else 'none',
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    # Extract encoded frames, not just the renderer's ideal input images.
    preview_dir = directory / 'frames'
    preview_dir.mkdir(exist_ok=True)
    sheet = Image.new('RGB', (1080, 1000), '#071322')
    for i, seconds in enumerate(PREVIEW_TIMES):
        path = preview_dir / f'{i+1:02}-{seconds:05.2f}s.jpg'
        subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-ss', str(seconds),
                        '-i', str(directory/'reel.mp4'), '-frames:v', '1', '-vf', 'scale=270:480', str(path)],
                       check=True, capture_output=True, timeout=15)
        with Image.open(path) as frame:
            sheet.paste(frame, ((i%4)*270, (i//4)*500))
        ImageDraw.Draw(sheet).text(((i%4)*270+8, (i//4)*500+482), f'{seconds:.2f}s', fill='white')
    sheet.save(directory / 'contact-sheet.jpg', quality=92)
    return directory / 'reel.mp4'
