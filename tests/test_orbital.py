import json
import math
import subprocess
import wave
from array import array

import pytest
from PIL import Image, ImageChops, ImageStat

from autopilot.orbital import OrbitalScene, orbit_position, name_lines, story, CUT, BEAT
from autopilot.render import render, PREVIEW_TIMES
from autopilot.simulation import ROW, SimulatedArchive
from autopilot.soundtrack import compose


def test_first_second_contains_visible_star_and_moving_planet():
    scene = OrbitalScene(ROW)
    frame = scene.frame(0)
    pixels = list(frame.crop((10, 290, 520, 630)).getdata())
    assert sum(r > 210 and g > 100 and b < 170 for r, g, b in pixels) > 5000
    assert sum(b > r*2 and g > r*2 and g > 65 for r, g, b in pixels) > 300
    p0, p1 = orbit_position(0, 0)[-1], orbit_position(.75, 0)[-1]
    assert math.dist(p0, p1) > 200
    # Motion persists within a shot, beyond the initial title/camera arrival.
    delta = ImageChops.difference(scene.frame(1).crop((10,290,520,630)), scene.frame(1.5).crop((10,290,520,630)))
    # Thousands of foreground pixels move; a sparse twinkling starfield cannot pass.
    assert sum(max(pixel) > 35 for pixel in delta.getdata()) > 3000


def test_scientific_comparison_uses_measured_period_and_not_rotation():
    row = dict(ROW, pl_orbper=.7365474)
    scene = OrbitalScene(row)
    frame = scene.frame(11.25)
    edge = 40 + 420*row['pl_orbper']
    assert frame.getpixel((int(edge)-5, 649)) == (214,255,120)
    assert frame.getpixel((int(edge)+5, 649)) != (214,255,120)
    assert '17,7 ORE' in scene.cues[3]
    assert scene.cues[5] == ('ORBITA', '≠ ROTAZIONE')


def test_scene_cuts_are_on_beats_and_geometry_changes():
    assert CUT/BEAT == 5
    scene = OrbitalScene(ROW)
    frames = [scene.frame(t).crop((10,290,520,740)) for t in PREVIEW_TIMES]
    for left, right in zip(frames, frames[1:]):
        assert sum(ImageStat.Stat(ImageChops.difference(left, right)).mean)/3 > 3


def test_all_identifiers_fit_and_evidence_legend_stays_visible():
    assert len(name_lines('W'*50)) <= 3
    scene = OrbitalScene(dict(ROW, pl_name='W'*50))
    legend = scene.frame(.5).crop((32, 775, 478, 875))
    for t in PREVIEW_TIMES:
        assert scene.frame(t).size == (540, 960)
        # The high-contrast schematic label remains visible in every shot.
        pixels = scene.frame(t).crop((32, 775, 478, 818)).getdata()
        assert sum(r > 150 and g > 200 and b < 160 for r,g,b in pixels) > 500
    assert ImageStat.Stat(legend).stddev[1] > 30


def test_invalid_scientific_measurement_cannot_be_visualized():
    with pytest.raises(ValueError):
        story(dict(ROW, pl_orbper=None))


def test_original_score_has_headroom_and_onbeat_accents(tmp_path):
    path = tmp_path/'score.wav'
    compose(path)
    with wave.open(str(path)) as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getnframes()) == (48000,1,960000)
        samples = array('h', wav.readframes(wav.getnframes()))
    assert max(abs(x) for x in samples) < 20000
    def rms(start, length=.04):
        part = samples[int(start*48000):int((start+length)*48000)]
        return math.sqrt(sum(x*x for x in part)/len(part))
    assert rms(2.51) > rms(2.81)*2


def test_silent_video_and_actual_encoded_frame_review(tmp_path):
    fact = SimulatedArchive().select(set())
    path = render(fact, tmp_path, audio=False)
    result = subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],
                            capture_output=True, text=True, check=True)
    streams = json.loads(result.stdout)['streams']
    assert len(streams) == 1 and streams[0]['codec_type'] == 'video'
    assert streams[0]['r_frame_rate'] == '24/1'
    assert not (tmp_path/'audio-license.txt').exists()
    assert len(list((tmp_path/'frames').glob('*.jpg'))) == 8
    with Image.open(tmp_path/'contact-sheet.jpg') as sheet:
        assert sheet.size == (1080,1000)
    metadata = json.loads((tmp_path/'render.json').read_text())
    assert metadata['scientific_value']['source_sha256'] == fact['source_sha256']
    assert metadata['style'] == 'orbital-motion'
    assert len(metadata['visual_script']) == 8
    assert 'SIMULAZIONE' in (tmp_path/'caption.txt').read_text()
    assert '00:00:20,000' in (tmp_path/'subtitles.srt').read_text()
