"""One authentic-footage editorial demo. No publisher, API key or synthetic imagery."""
import argparse
from array import array
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import wave

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent
POLICY = 'https://www.nasa.gov/nasa-brand-center/images-and-media/'
PERMISSION = 'NASA content used in a factual manner that does not imply endorsement may be used without needing explicit permission.'
SCIENCE = 'https://www.nasa.gov/image-article/red-green-aurora-australis/'
QUOTES = [
 'Auroras are caused when high-energy electrons pour down from the Earth’s magnetosphere and collide with atoms.',
 'Green aurora occurs from about 100 km to 250 km altitude and is caused by the emission of 5577 Angstrom wavelength light from oxygen atoms.',
 'The light is emitted when the atoms return to their original unexcited state.',
]
# Original chronology is rearranged as an editorial montage; no event timeline inferred.
SHOTS = [
 {'start':4,'x':2000,'text':['SAI COSA','STA BRILLANDO?']},
 {'start':0,'x':1800,'text':['È un’aurora.','Vista dalla ISS.']},
 {'start':2,'x':2200,'text':['Particelle cariche','colpiscono gli atomi.']},
 {'start':6,'x':2100,'text':['Gli atomi rilasciano','energia come luce.']},
 {'start':8,'x':2500,'text':['Quel verde?','Viene dall’ossigeno.']},
 {'start':3,'x':2500,'text':['LA NOTTE,','VISTA DA QUI.']},
]
DURATION = 24


def plain(body):
    body = re.sub(r'<(script|style)\b.*?</\1>', '', body, flags=re.S|re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', body))).strip()


def download(url, limit):
    from urllib.parse import urlsplit
    if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != 'www.nasa.gov':
        raise ValueError('Only the audited NASA host is allowed')
    for attempt in range(3):
        try:
            with httpx.stream('GET',url,timeout=60,follow_redirects=False) as response:
                response.raise_for_status(); result=bytearray()
                for chunk in response.iter_bytes():
                    result.extend(chunk)
                    if len(result)>limit:raise ValueError('Resource exceeds size limit')
                return bytes(result)
        except httpx.HTTPError:
            if attempt==2:raise RuntimeError('NASA resource unavailable; no substitute') from None
            time.sleep(2**attempt)


def run(args, timeout=180):
    return subprocess.run(args,check=True,capture_output=True,timeout=timeout)


def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)


def font(size,bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)


def overlay(path, lines, hook=False):
    im=Image.new('RGBA',(1080,1920));draw=ImageDraw.Draw(im);boxes=[]
    # Small local scrim for legibility; the moving picture fills the entire frame.
    for y in range(1280,1770):
        alpha=int(115*math.sin(math.pi*(y-1280)/490)**2)
        draw.line((0,y,1080,y),fill=(0,0,0,alpha))
    def text(xy,value,size,bold=False,fill='white'):
        face=font(size,bold);box=draw.textbbox(xy,value,font=face,stroke_width=1)
        if box[0]<70 or box[2]>990 or box[1]<140 or box[3]>1750:raise ValueError('Text exceeds safe area')
        boxes.append(box);draw.text(xy,value,font=face,fill=fill,stroke_width=1,stroke_fill='#18201d')
    text((90,175),'MA DAVVERO?',28,True,'#f2e5cf')
    for i,line in enumerate(lines):text((90,1390+i*86),line,70 if hook else 56,True)
    text((90,1660),'NASA / ISS · RIPRESE REALI',25,False,'#e2e9e5')
    im.save(path)
    return boxes


def soundtrack(path):
    """Original local ambient composition, no external samples or source audio."""
    rate=48000;pcm=array('h')
    for i in range(rate*DURATION):
        t=i/rate;root=[110,130.8128,98][min(2,int(t/8))]
        pad=sum(math.sin(2*math.pi*root*r*t)*a for r,a in [(1,.035),(1.5,.025),(2,.018)])
        beat=t%.5;kick=.1*math.sin(2*math.pi*(44*beat+2*(1-math.exp(-beat*25))))*math.exp(-beat*25)
        sparkle=.012*math.sin(2*math.pi*880*t)*math.exp(-(t%4)*3)
        fade=min(1,t/.1,(DURATION-t)/1.5)
        left=(pad+kick+sparkle)*fade
        right=(pad*.97+kick+sparkle*math.sin(t*.5))*fade
        pcm.extend((round(left*32767),round(right*32767)))
    if sys.byteorder!='little':pcm.byteswap()
    with wave.open(str(path),'wb') as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm.tobytes())


def check_video(path):
    info=probe(path);video=next(s for s in info['streams'] if s['codec_type']=='video')
    audios=[s for s in info['streams'] if s['codec_type']=='audio']
    errors=[]
    if (video['width'],video['height'],video['codec_name'],video['r_frame_rate'])!=(1080,1920,'h264','24/1'):errors.append('video format')
    if abs(float(info['format']['duration'])-24)>.08:errors.append('duration')
    run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],120)
    raw=run(['ffmpeg','-v','error','-i',str(path),'-vf','fps=4,scale=108:192','-pix_fmt','rgb24','-f','rawvideo','-']).stdout
    stride=108*192*3;previous=None;static=longest=0;brightness=[];motion=[]
    for i in range(0,len(raw),stride):
        frame=Image.frombytes('RGB',(108,192),raw[i:i+stride]).crop((5,30,103,130))
        brightness.append(sum(ImageStat.Stat(frame).mean)/3)
        if previous is not None:
            delta=sum(ImageStat.Stat(ImageChops.difference(frame,previous)).mean)/3;motion.append(delta)
            static=static+1 if delta<.3 else 0;longest=max(longest,static)
        previous=frame
    if len(brightness)!=96 or min(brightness)<2:errors.append('empty/black/incomplete frames')
    if longest/4>1.5:errors.append('static picture')
    audio_report={}
    if len(audios)!=1:errors.append('missing audio')
    else:
        samples=array('h');samples.frombytes(run(['ffmpeg','-v','error','-i',str(path),'-vn','-f','s16le','-ac','2','-ar','48000','-']).stdout)
        if sys.byteorder!='little':samples.byteswap()
        peak=max(abs(v) for v in samples)/32768;rms=math.sqrt(sum(v*v for v in samples)/len(samples))/32768
        if peak>=.98 or rms<.005 or abs(len(samples)/96000-24)>.1:errors.append('audio level/duration')
        audio_report={'peak':peak,'rms':rms,'codec':audios[0]['codec_name'],'channels':audios[0]['channels']}
    report={'passed':not errors,'errors':errors,'duration':float(info['format']['duration']),'width':video['width'],'height':video['height'],'codec':video['codec_name'],'fps':video['r_frame_rate'],'audio':audio_report,'sampled_frames':len(brightness),'minimum_subject_brightness':min(brightness),'mean_subject_motion':sum(motion)/len(motion),'longest_static_seconds':longest/4,'limitation':'Technical checks sample image at 4 fps and do not certify aesthetics; audio fully decoded.'}
    return report


def produce(output):
    started=time.monotonic();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    # An unsuccessful regeneration must never leave a stale deliverable.
    (output/'reel.mp4').unlink(missing_ok=True)
    sources=output/'sources';sources.mkdir(exist_ok=True)
    candidates=json.loads((ROOT/'footage_sources.json').read_text())
    selected=next(x for x in candidates if x['status']=='selected')
    proofs={}
    for name,url in [('policy',POLICY),('science',SCIENCE),('metadata',selected['metadata_url'])]:
        raw=download(url,3_000_000);(sources/(name+'.'+('json' if name=='metadata' else 'html'))).write_bytes(raw)
        proofs[name]={'url':url,'sha256':hashlib.sha256(raw).hexdigest()}
        if name=='policy' and PERMISSION not in plain(raw.decode()):raise ValueError('Reuse policy changed')
        if name=='science' and not all(q in plain(raw.decode()) for q in QUOTES):raise ValueError('Scientific source changed')
        if name=='metadata':
            meta=json.loads(raw)
            if meta['source_url']!=selected['url'] or 'International Space Station' not in plain(meta['description']['rendered']):raise ValueError('Provenance changed')
    raw=download(selected['url'],32_000_000)
    if hashlib.sha256(raw).hexdigest()!=selected['sha256']:raise ValueError('Footage changed; re-review required')
    original=sources/'nasa-original.mp4';original.write_bytes(raw)
    v=next(s for s in probe(original)['streams'] if s['codec_type']=='video')
    if (v['width'],v['height'])!=(3840,2160):raise ValueError('Insufficient native resolution')
    work=output/'work';work.mkdir(exist_ok=True);bounds=[]
    try:
        for i,shot in enumerate(SHOTS):
            png=work/f'text-{i}.png';bounds.append(overlay(png,shot['text'],i in [0,5]))
            # Two source seconds become four. Frame blending is disclosed, not claimed as new observations.
            filters=(f'[0:v]trim=duration=2,setpts=PTS-STARTPTS,crop=1216:2160:x={shot["x"]}+60*t:y=0,'
                     'scale=1080:1920:flags=lanczos,setsar=1,eq=gamma=1.6:contrast=1.03:saturation=1.06,'
                     'setpts=2*PTS,fps=24,tblend=all_mode=average,tpad=stop_mode=clone:stop_duration=0.1[film];'
                     '[film][1:v]overlay=0:0:shortest=1,format=yuv420p[out]')
            run(['ffmpeg','-nostdin','-y','-v','error','-ss',str(shot['start']),'-i',str(original),'-loop','1','-i',str(png),
                 '-filter_complex_threads','1','-filter_complex',filters,'-map','[out]','-an','-t','4','-r','24',
                 '-c:v','libx264','-threads','2','-preset','fast','-crf','18',str(work/f'shot-{i}.mp4')],180)
        soundtrack(work/'score.wav')
        (work/'concat.txt').write_text(''.join(f"file 'shot-{i}.mp4'\n" for i in range(6)))
        run(['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-i',str(work/'score.wav'),
             '-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','160k','-t','24','-movflags','+faststart',str(work/'final.mp4')])
        report=check_video(work/'final.mp4')
        report.update({'render_seconds':round(time.monotonic()-started,2),'source_resolution':[3840,2160],'crop_resolution':[1216,2160],'upscaled':False,'text_bounds':bounds})
        (output/'technical-report.json').write_text(json.dumps(report,indent=2))
        if not report['passed']:raise ValueError('Encoded video failed quality gates: '+', '.join(report['errors']))
        (work/'final.mp4').replace(output/'reel.mp4')
    finally:
        shutil.rmtree(work,ignore_errors=True)
        original.unlink(missing_ok=True)  # Do not redistribute the unused source audio.
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'original':selected,'proofs':proofs,'claims':[{'quote':q,'url':SCIENCE} for q in QUOTES],
              'edits':{'shot_list':SHOTS,'speed':0.5,'grading':'Gamma 1.6, contrast 1.03, saturation 1.06; no generated features.','temporal_processing':'24 fps, adjacent-frame blend; half-speed playback of the source file; original acquisition cadence is not stated in the catalogue.','audio':'Original source audio discarded; local procedural score only.'},'credit':'NASA / International Space Station; individual camera operator not identified by the catalogue.'}
    (output/'evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
    shutil.copyfile(ROOT/'footage_sources.json',output/'five-candidates.json')
    shutil.copytree(ROOT.parent/'docs/footage-evidence',sources/'candidate-research',dirs_exist_ok=True)
    (output/'caption.txt').write_text('L’aurora, vista dalla Stazione Spaziale Internazionale. Elettroni energetici provenienti dalla magnetosfera urtano gli atomi dell’atmosfera. Gli atomi emettono luce tornando allo stato non eccitato: il verde dell’aurora è legato all’ossigeno.\n\nRiprese: NASA / ISS, “Aurora borealis over the US and Canada”. Filmato rimontato, riprodotto a metà velocità e corretto nell’esposizione; non è una simulazione. Le luci puntiformi al suolo sono città, non aurora. Musica originale MA DAVVERO?. Nessuna approvazione NASA implicita.\n\nFilmato: '+selected['url']+'\nScheda originale: '+selected['metadata_url']+'\nFonte scientifica: '+SCIENCE+'\nCondizioni immagini: '+POLICY+'\n#MaDavvero #Aurora #Scienza #ISS\n',encoding='utf-8')
    (output/'subtitles.srt').write_text('\n'.join(f'{i+1}\n00:00:{i*4:02d},000 --> 00:00:{(i+1)*4:02d},000\n'+ '\n'.join(s['text'])+'\n' for i,s in enumerate(SHOTS)),encoding='utf-8')
    (output/'audio-license.txt').write_text('Original procedural composition by MA DAVVERO? contributors. Sine oscillators only, no sampled recording or borrowed composition. Generated audio dedicated under CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/ . NASA video is not relicensed under CC0. No source audio included.\n')
    frames=output/'frames';frames.mkdir(exist_ok=True);sheet=Image.new('RGB',(1080,1280),'#050706')
    for i,t in enumerate([.5,4.5,8.5,12.5,16.5,20.5]):
        p=frames/f'{i+1:02}.jpg';run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(output/'reel.mp4'),'-frames:v','1','-vf','scale=360:640',str(p)])
        with Image.open(p) as im:sheet.paste(im,((i%3)*360,(i//3)*640))
    sheet.save(output/'preview.jpg',quality=94)
    shutil.copyfile(ROOT.parent/'docs/authentic-footage.md',output/'rights-and-review.md')
    (output/'index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>MA DAVVERO? — Aurora</title><style>body{background:#080c0a;color:#eee;font:18px system-ui;max-width:560px;margin:24px auto;padding:16px}video,img{width:100%}a{color:#e1c79b}</style><h1>MA DAVVERO?</h1><video src="reel.mp4" poster="frames/01.jpg" controls playsinline></video><p><a href="caption.txt">Fonti e caption</a> · <a href="rights-and-review.md">Diritti e limiti</a> · <a href="technical-report.json">Controlli</a></p><img src="preview.jpg" alt="Sei fotogrammi estratti dal video">',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('data/authentic-footage'));args=parser.parse_args();produce(args.output)
