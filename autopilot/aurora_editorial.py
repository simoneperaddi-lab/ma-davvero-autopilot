"""Audited aurora editorial cut: real observations, no publishing dependency."""
import argparse
from array import array
import sys
import wave
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

from PIL import Image, ImageDraw

from . import footage_demo as media
from .editorial import validate_plan

ROOT = Path(__file__).parent
SOLAR_SCIENCE = 'https://www.nasa.gov/image-article/space-between-aurora-australis/'
SOLAR_QUOTES = [
 'charged particles (ions) streaming from the Sun (the solar wind ) interact with Earth’s magnetic field.',
 'The atoms are excited by these collisions, and they typically emit light as they return to their original energy level.',
]
SHOTS = [
 dict(source=232648, start=0, duration=4, text=['NON È', 'UN’ANIMAZIONE.'], role='hook'),
 dict(source=849432, start=4, duration=4, text=['LA TERRA.', 'VISTA DALLA ISS.'], role='earth'),
 dict(source=819232, start=12, duration=3, text=['IL SOLE ACCENDE', 'IL CIELO.'], role='sun'),
 dict(source=232648, start=8, duration=4, text=['LA CHIAMIAMO', 'AURORA.'], role='closing'),
]
# Fixed, reviewed cut. Picture ends at y=1440; narrative text never covers it.
GEOMETRY = {
 'portrait':'crop=1216:1620:2200:300,scale=1080:1440:flags=lanczos,eq=gamma=1.8:contrast=1.04:saturation=1.1,pad=1080:1920:0:0:color=black',
 'wide':'crop=600:800:600:0,scale=1080:1440:flags=lanczos,pad=1080:1920:0:0:color=black',
 'square':'scale=1080:1080:flags=lanczos,pad=1080:1920:0:180:color=black',
}


def overlay(path, shot, source):
    im=Image.new('RGBA',(1080,1920));draw=ImageDraw.Draw(im);boxes=[]
    def text(pos,value,size):
        face=media.font(size,True);box=draw.textbbox(pos,value,font=face)
        if box[0]<80 or box[2]>920 or box[1]<1290 or box[3]>1610:
            raise ValueError('Text exceeds Instagram safe area')
        draw.text(pos,value,font=face,fill='#f6f3e9');boxes.append(box)
    for i,line in enumerate(shot['text']):text((90,1458+i*70),line,56)
    if source['layout']=='square':text((90,1300),'SDO · UV, FALSI COLORI',24)
    im.save(path);return boxes


def score(path):
    """15-second original cue: soft harmonic pads, plucks and cut accents.

    No recording, third-party melody, source audio or external service.
    """
    rate=48000;pcm=array('h');duration=15
    chords=[(0,4,146.832),(4,4,116.541),(8,3,174.614),(11,4,130.813)]
    notes=[(0,293.665),(2,440),(4,349.228),(6,329.628),
           (8,523.251),(9.5,440),(11,587.330),(13,293.665)]
    def pluck(t,f):
        if t<0 or t>3:return 0
        envelope=(1-math.exp(-t*80))*math.exp(-t*2.2)
        return .07*envelope*(math.sin(2*math.pi*f*t)+.24*math.sin(4*math.pi*f*t)+.08*math.sin(6*math.pi*f*t))
    for i in range(rate*duration):
        t=i/rate;pad=0
        for start,length,root in chords:
            local=t-start
            if 0<=local<length:
                env=min(1,local/.35,(length-local)/.45)
                pad+=env*sum(.017*math.sin(2*math.pi*root*r*t)/(j+1) for j,r in enumerate([.5,1,1.5,2]))
        melody=sum(pluck(t-start,f) for start,f in notes)
        echo=sum(.28*pluck(t-start-.18,f) for start,f in notes)
        accent=0
        for start in [0,4,8,11]:
            u=t-start
            if 0<=u<.5:accent+=.08*math.sin(2*math.pi*(48*u+1.8*(1-math.exp(-u*20))))*math.exp(-u*13)
        fade=min(1,t/.035,(duration-t)/1.3)
        pcm.extend((round(32767*(pad+melody+accent)*fade),round(32767*(pad+melody*.85+echo+accent)*fade)))
    if sys.byteorder!='little':pcm.byteswap()
    with wave.open(str(path),'wb') as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm.tobytes())


def produce(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'reel.mp4').unlink(missing_ok=True)
    sources=json.loads((ROOT/'aurora_sources.json').read_text())
    shots=[dict(s) for s in SHOTS]; plan=validate_plan(shots,sources)
    work=output/'work';work.mkdir(exist_ok=True)
    evidence=output/'sources';evidence.mkdir(exist_ok=True)
    started=time.monotonic();proofs={};originals={};bounds=[]
    try:
        for name,url,quotes in [('policy',media.POLICY,[media.PERMISSION]),('science',media.SCIENCE,media.QUOTES),('solar-science',SOLAR_SCIENCE,SOLAR_QUOTES)]:
            raw=media.download(url,3_000_000)
            if not all(q in media.plain(raw.decode()) for q in quotes):raise ValueError(f'{name} changed; re-review required')
            (evidence/f'{name}.html').write_bytes(raw)
            proofs[name]=dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),verified_quotes=quotes)
        for source in sources:
            raw=media.download(source['metadata_url'],3_000_000);metadata=json.loads(raw)
            baseline=json.loads((ROOT.parent/f'docs/footage-evidence/{source["id"]}.json').read_text())
            for field in ['source_url','credits','description','caption']:
                if metadata.get(field)!=baseline.get(field):raise ValueError('Source description or rights changed; re-review required')
            (evidence/f'{source["id"]}.json').write_bytes(raw)
            raw=media.download(source['url'],32_000_000)
            if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Footage changed; re-review required')
            path=work/f'{source["id"]}.mp4';path.write_bytes(raw);originals[source['id']]=path
            v=next(s for s in media.probe(path)['streams'] if s['codec_type']=='video')
            if [v['width'],v['height']]!=source['dimensions']:raise ValueError('Native resolution changed')
        for i,shot in enumerate(shots):
            source=next(s for s in sources if s['id']==shot['source'])
            png=work/f'text-{i}.png';bounds.append(overlay(png,shot,source))
            geometry=GEOMETRY[source['layout']]
            filters=(f"[0:v]trim=duration={shot['duration']},setpts=PTS-STARTPTS,{geometry},setsar=1,fps=24[film];"
                     "[film][1:v]overlay=0:0:shortest=1:enable='gte(t,0.35)',format=yuv420p[out]")
            media.run(['ffmpeg','-v','error','-y','-ss',str(shot['start']),'-i',str(originals[shot['source']]),'-loop','1','-i',str(png),
                       '-filter_complex_threads','1','-filter_complex',filters,'-map','[out]','-an','-t',str(shot['duration']),'-r','24',
                       '-c:v','libx264','-threads','2','-preset','fast','-crf','18',str(work/f'shot-{i}.mp4')])
        score(work/'score.wav')
        (work/'concat.txt').write_text(''.join(f"file 'shot-{i}.mp4'\n" for i in range(len(shots))))
        media.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-i',str(work/'score.wav'),
                   '-map','0:v','-map','1:a','-c:v','copy','-af','loudnorm=I=-18:TP=-1.5:LRA=9',
                   '-ar','48000','-c:a','aac','-b:a','160k','-t',str(plan['duration']),'-movflags','+faststart',str(work/'final.mp4')])
        report=media.check_video(work/'final.mp4',plan['duration'])
        report.update(plan);report.update(text_bounds=bounds,render_seconds=round(time.monotonic()-started,2),upscaled=True,source_crop_sizes={"232648":[600,800],"849432":[1216,1620],"819232":[1024,1024]},picture_bounds=[0,0,1080,1440],narrative_phrases=4,opening_logo=False)
        (output/'technical-report.json').write_text(json.dumps(report,indent=2))
        if not report['passed']:raise ValueError('Technical checks failed: '+str(report['errors']))
        (work/'final.mp4').replace(output/'reel.mp4')
    finally:shutil.rmtree(work,ignore_errors=True)
    (output/'evidence.json').write_text(json.dumps(dict(sources=sources,proofs=proofs,shots=shots,disclosure='Different observations, dates and instruments; not a single event or proof of a specific Sun–aurora causal link. Solar data: extreme UV 131 Å, false colors. No original audio. No temporal slowdown. ISS wide source: 600x800 crop enlarged 1.8x; SDO disk enlarged 1.055x; 4K crop downscaled. No synthesized detail.'),indent=2,ensure_ascii=False))
    (output/'caption.txt').write_text('Non è un’animazione. È l’aurora vista dalla ISS.\nIl vento solare interagisce con il campo magnetico terrestre: particelle energetiche possono trasferire energia agli atomi dell’alta atmosfera, che la rilasciano come luce. Il verde dell’ossigeno si osserva a circa 100–250 km di quota.\n\nMontaggio di osservazioni diverse, non dello stesso evento: aurora NASA/ISS (due riprese); Sole NASA/SDO, ultravioletto a 131 Å in falsi colori. Il brillamento mostrato non viene identificato come causa delle aurore mostrate. Le luci puntiformi al suolo sono città, non particelle o aurore. Filmati alla velocità dei file originali; alcuni sono time-lapse. Ritaglio verticale: la ripresa panoramica è ingrandita 1,8 volte e il Sole 1,055 volte; la ripresa 4K è ridotta e schiarita (gamma 1,8). Nessun dettaglio generato. Musica originale locale, nessun audio delle fonti. Nessun endorsement NASA.\n\nFonti scientifiche:\n'+media.SCIENCE+'\n'+SOLAR_SCIENCE+'\n\nFilmati e crediti:\n'+'\n'.join(s['credit']+' — '+s['url']+'\n'+s['metadata_url'] for s in sources)+'\nCondizioni NASA: '+media.POLICY+'\n',encoding='utf-8')
    cursor=0;subtitles=[]
    for i,shot in enumerate(shots):
        end=cursor+shot['duration'];subtitles.append(f'{i+1}\n00:00:{cursor:02d},000 --> 00:00:{end:02d},000\n'+ '\n'.join(shot['text'])+'\n');cursor=end
    (output/'subtitles.srt').write_text('\n'.join(subtitles),encoding='utf-8')
    (output/'audio-license.txt').write_text('Original MA DAVVERO? procedural composition; sine oscillators, no external samples. Generated score CC0 1.0 https://creativecommons.org/publicdomain/zero/1.0/ . This does not relicense NASA footage.\n')
    frames=output/'frames';shutil.rmtree(frames,ignore_errors=True);frames.mkdir(exist_ok=True);sheet=Image.new('RGB',(1440,640),'#000000');cursor=0
    for i,shot in enumerate(shots):
        path=frames/f'{i+1:02d}.jpg';media.run(['ffmpeg','-v','error','-y','-ss',str(cursor+.75),'-i',str(output/'reel.mp4'),'-frames:v','1','-vf','scale=360:640',str(path)])
        with Image.open(path) as im:sheet.paste(im,((i%4)*360,(i//4)*640))
        cursor+=shot['duration']
    sheet.save(output/'preview.jpg',quality=95)
    media.run(['ffmpeg','-v','error','-y','-i',str(output/'reel.mp4'),'-frames:v','1',str(output/'first-frame.jpg')])
    shutil.copyfile(ROOT.parent/'docs/aurora-editorial.md',output/'review.md')
    (output/'index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Aurora — MA DAVVERO?</title><style>body{background:#050807;color:white;max-width:540px;margin:auto;font:18px system-ui}video,img{width:100%}a{color:#dfd7bd}</style><h1>MA DAVVERO?</h1><video src="reel.mp4" controls playsinline poster="frames/01.jpg"></video><p><a href="caption.txt">Fonti</a> · <a href="review.md">Limiti e controlli</a></p><img src="preview.jpg" alt="Fotogrammi del montaggio">',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('data/aurora-editorial'));args=parser.parse_args();produce(args.output)
