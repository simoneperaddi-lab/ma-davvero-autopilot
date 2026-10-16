import hashlib
import io
import json
import subprocess
import wave

import numpy as np
import pytest
from PIL import Image

from autopilot import documentaries as docs
from autopilot.cinema import CinemaScene
from autopilot.cinema_render import quality, score
from autopilot.science import Unverified


def mock_source(monkeypatch, key='solar-rain', dimensions=(600,338), changed=None):
    story=docs.STORIES[key]
    content=' '.join(story['quotes'])+' '+story['credit']+' '+docs.POLICY_QUOTE
    body=content.encode()
    buf=io.BytesIO();Image.new('RGB',dimensions,'#da8030').save(buf,format='PNG');raw=buf.getvalue()
    monkeypatch.setitem(docs.ASSET_HASHES,key,hashlib.sha256(raw).hexdigest())
    def fetch(url,*args):
        return raw if url==story['asset'] else (changed if changed is not None else body)
    monkeypatch.setattr(docs,'fetch',fetch)
    return raw


def test_verified_evidence_is_bound_to_binary_and_claims(tmp_path,monkeypatch):
    raw=mock_source(monkeypatch)
    fact,path=docs.verify('solar-rain',tmp_path)
    assert path.read_bytes()==raw
    assert fact['asset']['sha256']==hashlib.sha256(raw).hexdigest()
    assert len(fact['claims'])==2
    assert len(list(tmp_path.glob('*-source-*.txt')))==2
    assert 'NASA' in fact['content']['caption']


@pytest.mark.parametrize('missing',['claim','credit','policy'])
def test_changed_source_rights_or_credit_fails_closed(tmp_path,monkeypatch,missing):
    story=docs.STORIES['solar-rain']
    text=' '.join(story['quotes'])+' '+story['credit']+' '+docs.POLICY_QUOTE
    remove={'claim':story['quotes'][0],'credit':story['credit'],'policy':docs.POLICY_QUOTE}[missing]
    mock_source(monkeypatch,changed=text.replace(remove,'').encode())
    with pytest.raises(Unverified):docs.verify('solar-rain',tmp_path)


def test_changed_media_and_insufficient_resolution_rejected(tmp_path,monkeypatch):
    mock_source(monkeypatch)
    monkeypatch.setitem(docs.ASSET_HASHES,'solar-rain','0'*64)
    with pytest.raises(Unverified,match='Materiale cambiato'):docs.verify('solar-rain',tmp_path)
    mock_source(monkeypatch,dimensions=(100,100))
    with pytest.raises(Unverified,match='Risoluzione'):docs.verify('solar-rain',tmp_path)


def test_exhaustion_skips_instead_of_repeating(monkeypatch,tmp_path):
    monkeypatch.setattr(docs,'verify',lambda *args:pytest.fail('Used stories must not be fetched'))
    with pytest.raises(Unverified,match='Nessuna storia nuova'):
        docs.DocumentaryArchive(None,tmp_path).select(set(docs.STORIES))


def test_fetch_rejects_unapproved_domains():
    with pytest.raises(Unverified):docs.fetch('https://example.com/image.jpg')
    with pytest.raises(Unverified):docs.fetch('http://www.nasa.gov/image.jpg')


@pytest.mark.parametrize('key',list(docs.STORIES))
def test_native_composition_safe_text_and_nontext_motion(tmp_path,key):
    asset=tmp_path/'test.png';Image.new('RGB',(1600,1600),'#a09080').save(asset)
    scene=CinemaScene(key,asset)
    first=np.asarray(scene.frame(.1));later=np.asarray(scene.frame(1.1))
    assert first.shape==(1920,1080,3)
    # Subject region only; changing words cannot satisfy this assertion.
    assert np.abs(first[600:1500].astype(float)-later[600:1500]).mean()>.2
    for shot in range(8):
        scene.frame(shot*3+.5)
        assert all(60<=b[0]<b[2]<=1000 and 130<=b[1]<b[3]<=1760 for b in scene.boxes)
    with pytest.raises(ValueError,match='zona sicura'):
        scene.text(__import__('PIL.ImageDraw',fromlist=['Draw']).Draw(Image.new('RGB',(1080,1920))),(990,300),'OVERFLOW',68,True,'white')


def test_original_stereo_score_has_headroom_and_no_silent_middle(tmp_path):
    path=tmp_path/'score.wav';score(path)
    with wave.open(str(path)) as wav:
        assert (wav.getnchannels(),wav.getframerate(),wav.getnframes())==(2,48000,24*48000)
        samples=np.frombuffer(wav.readframes(wav.getnframes()),'<i2').reshape(-1,2)/32768
    assert .1<np.abs(samples).max()<.8
    assert all(np.sqrt(np.mean(block**2))>.01 for block in np.array_split(samples[48000:-48000],22))
    assert np.abs(samples[:,0]-samples[:,1]).mean()>.005


def test_real_encoder_qc_rejects_black_static_missing_audio(tmp_path):
    path=tmp_path/'invalid.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=black:s=1080x1920:r=24:d=24',
                    '-c:v','libx264','-threads','2','-preset','ultrafast',str(path)],check=True,timeout=60)
    report=quality(path)
    assert not report['passed']
    assert 'fotogramma nero/vuoto' in report['errors']
    assert 'scena statica oltre 2 secondi' in report['errors']
    assert 'audio mancante' in report['errors']
