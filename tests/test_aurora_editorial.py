import copy
import json

import pytest
from PIL import Image
from autopilot import aurora_editorial as cut
from autopilot.editorial import choose_opening, topic_hook, validate_plan


def sources():
    return json.loads((cut.ROOT/'aurora_sources.json').read_text())


def test_actual_story_has_three_observations_without_replayed_intervals():
    result=validate_plan(cut.SHOTS,sources())
    assert result['duration']==15
    assert len(cut.SHOTS)==4
    assert result['distinct_capture_groups']==3
    assert not result['creative_quality_certified']



@pytest.mark.parametrize('change,match',[
 ('repeat','Repeated'),('alias','Insufficient'),('hash','Insufficient'),
 ('rights','Unreviewed'),('range','Invalid'),('nan','Invalid'),('short','Reject')])
def test_rejects_invalid_or_insufficient_material(change,match):
    shots=copy.deepcopy(cut.SHOTS);pool=sources()
    if change=='repeat':shots[-1]['start']=1
    if change=='alias':pool[1]['group']=pool[2]['group']
    if change=='hash':pool[1]['sha256']=pool[2]['sha256']
    if change=='rights':pool[0]['reviewed']=False
    if change=='range':shots[0]['start']=100
    if change=='nan':shots[0]['start']=float('nan')
    if change=='short':shots=[shots[0],shots[1],shots[2]]
    with pytest.raises(ValueError,match=match):validate_plan(shots,pool)


def test_opening_excludes_unrelated_spectacular_material():
    good=dict(relevant=True,reviewed=True,contrast=10,color=20,motion=4)
    better=dict(good,contrast=20)
    irrelevant=dict(good,relevant=False,contrast=1000)
    assert choose_opening([good,irrelevant,better])==better
    with pytest.raises(ValueError):choose_opening([irrelevant])
    with pytest.raises(ValueError):topic_hook('unsupported topic')


def test_safe_text_without_hiding_picture(tmp_path):
    pool={s['id']:s for s in sources()}
    for i,shot in enumerate(cut.SHOTS):
        path=tmp_path/f'{i}.png';boxes=cut.overlay(path,shot,pool[shot['source']])
        assert all(80<=b[0]<b[2]<=920 and 1290<=b[1]<b[3]<=1610 for b in boxes)
        image=Image.open(path)
        assert image.crop((0,0,1080,1290)).getchannel('A').getbbox() is None
        assert all(b[1]>1440 for b in boxes[:2])
    with pytest.raises(ValueError,match='safe area'):
        cut.overlay(tmp_path/'bad.png',dict(cut.SHOTS[0],text=['W'*100]),pool[849432])


def test_policy_failure_removes_stale_video_before_encoding(tmp_path,monkeypatch):
    (tmp_path/'reel.mp4').write_bytes(b'stale')
    monkeypatch.setattr(cut.media,'download',lambda *a:b'changed policy')
    monkeypatch.setattr(cut.media,'run',lambda *a,**k:pytest.fail('Must stop before encoding'))
    with pytest.raises(ValueError,match='policy changed'):cut.produce(tmp_path)
    assert not (tmp_path/'reel.mp4').exists()
    assert not (tmp_path/'work').exists()
