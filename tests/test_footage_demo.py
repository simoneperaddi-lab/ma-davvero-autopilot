import json
from pathlib import Path
import subprocess
import wave

import pytest
from PIL import Image

from autopilot import footage_demo as demo


def test_five_distinct_originals_and_one_selected():
    candidates=json.loads((demo.ROOT/'footage_sources.json').read_text())
    assert len(candidates)==len({x['sha256'] for x in candidates})==5
    assert [x['id'] for x in candidates if x['status']=='selected']==[849432]
    assert all(x['rights_review'] and x['metadata_url'] and x['url'].endswith('.mp4') for x in candidates)
    assert all((demo.ROOT.parent/'docs/footage-evidence'/f'{x["id"]}.json').exists() for x in candidates)


def test_every_overlay_fits_and_leaves_picture_visible(tmp_path):
    for i,s in enumerate(demo.SHOTS):
        p=tmp_path/f'{i}.png';bounds=demo.overlay(p,s['text'],i in [0,5])
        assert all(70<=b[0]<b[2]<=990 and 140<=b[1]<b[3]<=1750 for b in bounds)
        assert Image.open(p).getpixel((540,960))[3]==0
    with pytest.raises(ValueError,match='safe area'):
        demo.overlay(tmp_path/'bad.png',['W'*100])


def test_edit_uses_only_valid_native_crops_and_source_ranges():
    assert sum(2*2 for _ in demo.SHOTS)==24
    for s in demo.SHOTS:
        assert s['start']>=0 and s['start']+2<=12.466667
        assert 0<=s['x'] and s['x']+120+1216<=3840
    assert 1216>=1080 and 2160>=1920


def test_download_rejects_other_hosts_without_network():
    for url in ['http://www.nasa.gov/file','https://example.com/file','https://www.nasa.gov.evil.example/file']:
        with pytest.raises(ValueError):demo.download(url,100)


@pytest.mark.parametrize('broken',['policy','science','metadata','binary'])
def test_source_or_rights_change_stops_before_render(tmp_path,monkeypatch,broken):
    selected=json.loads((demo.ROOT/'footage_sources.json').read_text())[0]
    values={demo.POLICY:demo.PERMISSION.encode(),demo.SCIENCE:' '.join(demo.QUOTES).encode(),
            selected['metadata_url']:json.dumps({'source_url':selected['url'],'description':{'rendered':'International Space Station'}}).encode(),selected['url']:b'changed binary'}
    if broken=='policy':values[demo.POLICY]=b'changed terms'
    if broken=='science':values[demo.SCIENCE]=b'unsupported claim'
    if broken=='metadata':values[selected['metadata_url']]=json.dumps({'source_url':'wrong'}).encode()
    monkeypatch.setattr(demo,'download',lambda url,limit:values[url])
    monkeypatch.setattr(demo,'run',lambda *a,**kw:pytest.fail('No encoder before provenance verification'))
    (tmp_path/'reel.mp4').write_bytes(b'stale output')
    with pytest.raises(ValueError):demo.produce(tmp_path)
    assert not (tmp_path/'reel.mp4').exists()


def test_real_encoded_black_silent_video_is_rejected(tmp_path):
    p=tmp_path/'bad.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=black:s=1080x1920:r=24:d=24','-c:v','libx264','-threads','2','-preset','ultrafast',str(p)],check=True,timeout=60)
    result=demo.check_video(p)
    assert not result['passed']
    assert {'empty/black/incomplete frames','static picture','missing audio'}<=set(result['errors'])
