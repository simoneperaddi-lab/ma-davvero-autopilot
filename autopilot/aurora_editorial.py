"""Audited aurora editorial cut: real observations, no publishing dependency."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

from PIL import Image, ImageDraw, ImageStat, ImageChops

from . import footage_demo as media
from .editorial import choose_opening, topic_hook, validate_plan

ROOT = Path(__file__).parent
SOLAR_SCIENCE = 'https://www.nasa.gov/image-article/space-between-aurora-australis/'
SOLAR_QUOTES = [
 'charged particles (ions) streaming from the Sun (the solar wind ) interact with Earth’s magnetic field.',
 'The atoms are excited by these collisions, and they typically emit light as they return to their original energy level.',
]
SHOTS = [
 dict(source=849432, start=8, duration=2, text=topic_hook('aurora'), role='hook'),
 dict(source=232648, start=0, duration=3, text=['MA NON È FUOCO.'], role='surprise'),
 dict(source=819232, start=12, duration=3, text=['TUTTO PARTE', 'DAL SOLE.'], role='cause'),
 dict(source=849432, start=0, duration=3, text=['Particelle cariche.', 'Incontrano l’atmosfera.'], role='interaction'),
 dict(source=849432, start=3, duration=3, text=['L’aria restituisce', 'energia. In luce.'], role='light'),
 dict(source=232648, start=7, duration=4, text=['Verde ossigeno.', 'A 100–250 km da terra.'], role='revelation'),
 dict(source=849432, start=6, duration=2, text=['LA TERRA RISPONDE.'], role='closing'),
]


def overlay(path, shot, source):
    im = Image.new('RGBA', (1080, 1920)); draw = ImageDraw.Draw(im); boxes = []
    if source['layout'] == 'portrait':
        for y in range(1260, 1630):
            draw.line((0,y,1080,y), fill=(0,0,0,round(145*math.sin(math.pi*(y-1260)/370)**2)))
    def text(pos, value, size, color='white'):
        face = media.font(size, True); box = draw.textbbox(pos, value, font=face, stroke_width=1)
        if box[0]<80 or box[2]>920 or box[1]<170 or box[3]>1570:
            raise ValueError('Text exceeds Instagram safe area')
        draw.text(pos, value, font=face, fill=color, stroke_width=1, stroke_fill='#101711'); boxes.append(box)
    text((90,190), 'MA DAVVERO?', 27, '#e9e1cc')
    size = 64 if shot['role']=='hook' else 50
    for i,line in enumerate(shot['text']): text((90,1340+i*78), line, size)
    label = {'portrait':'NASA / ISS · RIPRESE REALI', 'wide':'NASA / ISS · TIME-LAPSE', 'square':'NASA / SDO · UV, FALSI COLORI'}[source['layout']]
    text((90,1530), label, 23, '#cad4cd')
    im.save(path); return boxes


def opening_measurements(originals, work):
    candidates = []
    for source, start in [(849432,8),(849432,10),(232648,3),(232648,4)]:
        pictures=[]
        for offset in [0,.5,1]:
            path=work/f'opening-{source}-{start}-{offset}.png'
            media.run(['ffmpeg','-v','error','-y','-ss',str(start+offset),'-i',str(originals[source]),'-frames:v','1',
                       '-vf',('crop=1216:2160:2200:0,scale=180:320' if source==849432 else 'scale=180:120'),str(path)])
            with Image.open(path) as image: pictures.append(image.convert('RGB'))
        contrast = sum(ImageStat.Stat(pictures[1]).stddev)/3
        color = ImageStat.Stat(pictures[1].convert('HSV')).mean[1]
        motion = sum(ImageStat.Stat(ImageChops.difference(pictures[0],pictures[2])).mean)/3
        candidates.append(dict(source=source,start=start, contrast=contrast,color=color,motion=motion,relevant=True,reviewed=True))
    return candidates


def plan_with_opening(winner):
    shots=[dict(s) for s in SHOTS]
    shots[0].update(source=winner['source'],start=winner['start'])
    if winner['source']==232648:
        # Keep the immediate reverse shot genuinely different and nonoverlapping.
        shots[1].update(source=849432,start=8)
    return shots


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
        opening=opening_measurements(originals,work)
        winner=choose_opening(opening)
        shots=plan_with_opening(winner)
        plan=validate_plan(shots,sources)
        for i,shot in enumerate(shots):
            source=next(s for s in sources if s['id']==shot['source'])
            png=work/f'text-{i}.png';bounds.append(overlay(png,shot,source))
            # Preserve the wide Earth horizon and full solar disk at native detail.
            # No repeated/blurred background and no invented camera movement.
            geometry={'portrait':'crop=1216:2160:2200:0,scale=1080:1920:flags=lanczos,eq=gamma=1.35:contrast=1.03:saturation=1.02',
                      'wide':'scale=1080:720:flags=lanczos,pad=1080:1920:0:500:color=0x050807',
                      'square':'pad=1080:1920:28:260:color=0x050807'}[source['layout']]
            filters=f'[0:v]trim=duration={shot["duration"]},setpts=PTS-STARTPTS,{geometry},setsar=1,fps=24[film];[film][1:v]overlay=0:0:shortest=1,format=yuv420p[out]'
            media.run(['ffmpeg','-v','error','-y','-ss',str(shot['start']),'-i',str(originals[shot['source']]),'-loop','1','-i',str(png),
                       '-filter_complex_threads','1','-filter_complex',filters,'-map','[out]','-an','-t',str(shot['duration']),'-r','24',
                       '-c:v','libx264','-threads','2','-preset','fast','-crf','18',str(work/f'shot-{i}.mp4')])
        media.soundtrack(work/'score.wav',plan['duration'])
        (work/'concat.txt').write_text(''.join(f"file 'shot-{i}.mp4'\n" for i in range(len(shots))))
        media.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-i',str(work/'score.wav'),
                   '-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','160k','-t',str(plan['duration']),'-movflags','+faststart',str(work/'final.mp4')])
        report=media.check_video(work/'final.mp4',plan['duration'])
        report.update(plan);report.update(text_bounds=bounds,render_seconds=round(time.monotonic()-started,2),opening_candidates=opening,upscaled=False)
        (output/'technical-report.json').write_text(json.dumps(report,indent=2))
        if not report['passed']:raise ValueError('Technical checks failed: '+str(report['errors']))
        (work/'final.mp4').replace(output/'reel.mp4')
    finally:shutil.rmtree(work,ignore_errors=True)
    (output/'evidence.json').write_text(json.dumps(dict(sources=sources,proofs=proofs,shots=shots,disclosure='Different observations, dates and instruments; not a single event or proof of a specific Sun–aurora causal link. Solar data: extreme UV 131 Å, false colors. No original audio. No temporal slowdown.'),indent=2,ensure_ascii=False))
    (output/'caption.txt').write_text('Sembra fuoco. È l’atmosfera che emette luce.\nIl vento solare interagisce con il campo magnetico terrestre: particelle energetiche possono trasferire energia agli atomi dell’alta atmosfera, che la rilasciano come luce. Il verde dell’ossigeno si osserva a circa 100–250 km di quota.\n\nMontaggio di osservazioni diverse, non dello stesso evento: aurora NASA/ISS (due riprese); Sole NASA/SDO, ultravioletto a 131 Å in falsi colori. Il brillamento mostrato non viene identificato come causa delle aurore mostrate. Le luci puntiformi al suolo sono città, non particelle o aurore. Filmati alla velocità dei file originali; alcuni sono time-lapse. Ritaglio verticale e moderata correzione dell’esposizione solo sulla ripresa 4K. Musica originale locale, nessun audio delle fonti. Nessun endorsement NASA.\n\nFonti scientifiche:\n'+media.SCIENCE+'\n'+SOLAR_SCIENCE+'\n\nFilmati e crediti:\n'+'\n'.join(s['credit']+' — '+s['url']+'\n'+s['metadata_url'] for s in sources)+'\nCondizioni NASA: '+media.POLICY+'\n',encoding='utf-8')
    cursor=0;subtitles=[]
    for i,shot in enumerate(shots):
        end=cursor+shot['duration'];subtitles.append(f'{i+1}\n00:00:{cursor:02d},000 --> 00:00:{end:02d},000\n'+ '\n'.join(shot['text'])+'\n');cursor=end
    (output/'subtitles.srt').write_text('\n'.join(subtitles),encoding='utf-8')
    (output/'audio-license.txt').write_text('Original MA DAVVERO? procedural composition; sine oscillators, no external samples. Generated score CC0 1.0 https://creativecommons.org/publicdomain/zero/1.0/ . This does not relicense NASA footage.\n')
    frames=output/'frames';frames.mkdir(exist_ok=True);sheet=Image.new('RGB',(1440,1280),'#050807');cursor=0
    for i,shot in enumerate(shots):
        path=frames/f'{i+1:02d}.jpg';media.run(['ffmpeg','-v','error','-y','-ss',str(cursor+.75),'-i',str(output/'reel.mp4'),'-frames:v','1','-vf','scale=360:640',str(path)])
        with Image.open(path) as im:sheet.paste(im,((i%4)*360,(i//4)*640))
        cursor+=shot['duration']
    sheet.save(output/'preview.jpg',quality=95)
    shutil.copyfile(ROOT.parent/'docs/aurora-editorial.md',output/'review.md')
    (output/'index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Aurora — MA DAVVERO?</title><style>body{background:#050807;color:white;max-width:540px;margin:auto;font:18px system-ui}video,img{width:100%}a{color:#dfd7bd}</style><h1>MA DAVVERO?</h1><video src="reel.mp4" controls playsinline poster="frames/01.jpg"></video><p><a href="caption.txt">Fonti</a> · <a href="review.md">Limiti e controlli</a></p><img src="preview.jpg" alt="Fotogrammi del montaggio">',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('data/aurora-editorial'));args=parser.parse_args();produce(args.output)
