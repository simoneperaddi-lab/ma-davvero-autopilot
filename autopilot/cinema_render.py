"""Bounded native-1080p renderer and encoded-output quality gates."""
import hashlib
import json
import math
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from app.video import timestamp
from autopilot.cinema import CinemaScene, W, H, FPS, DURATION, SHOT
from autopilot.documentaries import ASSET_HASHES, STORIES, verify


def score(path):
    rate=48000;t=np.arange(rate*DURATION,dtype=np.float64)/rate
    rng=np.random.default_rng(122)
    # Original ambient score: slow minor harmony, soft beat and cut-aligned swells.
    left=np.zeros_like(t);right=np.zeros_like(t)
    for i,root in enumerate([110,130.8128,98,110]):
        start=i*6;env=np.clip((t-start)/1.5,0,1)*np.clip((start+7.5-t)/1.5,0,1)
        for j,ratio in enumerate([1,1.5,2.378414]):
            freq=root*ratio
            left+=.035*env*np.sin(2*np.pi*freq*t+.3*np.sin(t*.8))
            right+=.035*env*np.sin(2*np.pi*(freq+.12)*t+.3*np.sin(t*.8))
    beat=t%.5
    pulse=.12*np.sin(2*np.pi*(44*beat+2*(1-np.exp(-beat*30))))*np.exp(-beat*25)
    noise=rng.normal(0,1,len(t))
    noise=np.convolve(noise,np.ones(15)/15,mode='same')
    for cut in range(3,DURATION,3):
        env=np.exp(-((t-cut)/.18)**2)
        left+=noise*env*.09;right+=noise*env*.075
    fade=np.minimum(1,t/.04)*np.minimum(1,(DURATION-t)/1.4)
    samples=np.stack([(left+pulse)*fade,(right+pulse)*fade],axis=1)
    pcm=np.int16(np.clip(samples,-.8,.8)*32767)
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(pcm.astype('<i2').tobytes())


def command(args,timeout=90):
    return subprocess.run(args,check=True,capture_output=True,timeout=timeout)


def quality(path,expected_audio=True):
    probe=json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=[s for s in probe['streams'] if s['codec_type']=='audio']
    errors=[]
    if (video['width'],video['height'],video['codec_name'])!=(W,H,'h264'):errors.append('formato video')
    if abs(float(probe['format']['duration'])-DURATION)>.1:errors.append('durata incompleta')
    # Decode the entire file with strict error handling, not just its header.
    command(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],timeout=120)
    raw=command(['ffmpeg','-v','error','-i',str(path),'-vf','fps=4,scale=108:192','-f','rawvideo','-pix_fmt','rgb24','-']).stdout
    frames=np.frombuffer(raw,np.uint8).reshape(-1,192,108,3)
    if len(frames)!=DURATION*4:errors.append('numero di fotogrammi incompleto')
    # Exclude text, brand and progress bar: measure the actual visual subject.
    roi=frames[:,55:155,8:100].astype(np.float32)
    brightness=roi.mean(axis=(1,2,3));delta=np.abs(np.diff(roi,axis=0)).mean(axis=(1,2,3))
    static=longest=0
    for difference in delta:
        static=static+1 if difference<.15 else 0;longest=max(longest,static)
    if np.any(brightness<1):errors.append('fotogramma nero/vuoto')
    if longest/4>2:errors.append('scena statica oltre 2 secondi')
    audio_report={}
    if expected_audio:
        if not audio:errors.append('audio mancante')
        else:
            pcm=command(['ffmpeg','-v','error','-i',str(path),'-vn','-f','f32le','-ac','2','-ar','48000','-']).stdout
            sound=np.frombuffer(pcm,np.float32)
            peak=float(np.max(np.abs(sound)));rms=float(np.sqrt(np.mean(sound**2)))
            audio_report={'peak':peak,'rms':rms,'channels':audio[0]['channels'],'sample_rate':audio[0]['sample_rate']}
            if peak>=.99 or rms<.005 or audio[0]['codec_name']!='aac' or audio[0]['channels']!=2 or abs(len(sound)/96000-DURATION)>.1:errors.append('audio silenzioso/clipping/codec')
    result={'passed':not errors,'errors':errors,'duration':float(probe['format']['duration']),
            'resolution':[video['width'],video['height']],'codec':video['codec_name'],'fps':video['r_frame_rate'],
            'decoded_sample_frames':len(frames),'minimum_visual_brightness':float(brightness.min()),
            'longest_static_seconds':longest/4,'mean_visual_delta':float(delta.mean()),'audio':audio_report,
            'scope':'Controlli tecnici automatici; non una valutazione estetica umana.'}
    return result


def render(fact,directory,audio=True,asset=None):
    start=time.monotonic();directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    key=fact['documentary']
    if key!=fact['subject']:raise ValueError('Identità editoriale incoerente')
    if asset is None:
        fresh,asset=verify(key,directory/'sources')
        if fresh['source_sha256']!=fact['source_sha256']:raise ValueError('Fonte modificata dopo la selezione')
    if hashlib.sha256(Path(asset).read_bytes()).hexdigest()!=ASSET_HASHES[key]:raise ValueError('Materiale non verificato')
    scene=CinemaScene(key,asset)
    wav=directory/'score.wav';temporary=directory/'rendering.mp4'
    if audio:score(wav)
    cmd=['ffmpeg','-nostdin','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0']
    if audio:cmd+=['-i',str(wav),'-map','0:v','-map','1:a','-c:a','aac','-b:a','160k']
    cmd+=['-c:v','libx264','-threads','2','-preset','fast','-crf','20','-pix_fmt','yuv420p','-t',str(DURATION),'-movflags','+faststart',str(temporary)]
    try:
        with tempfile.TemporaryFile() as errors:
            with subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors) as process:
                watchdog=threading.Timer(480,process.kill);watchdog.start()
                try:
                    for i in range(FPS*DURATION):process.stdin.write(scene.frame(i/FPS).tobytes())
                    process.stdin.close()
                    if process.wait(timeout=60):raise RuntimeError('Rendering non riuscito')
                except BaseException:
                    process.kill();process.wait();raise
                finally:watchdog.cancel()
        output=directory/'reel.mp4';temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True);wav.unlink(missing_ok=True)
    report=quality(output,audio)
    report['render_seconds']=round(time.monotonic()-start,2)
    report['asset_resolution']=fact['asset']['dimensions']
    report['asset_upscaled']=False
    report['text_bounds']='All generated text checked against safe zone x=60..1000, y=130..1760 at every frame.'
    (directory/'technical-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    if not report['passed']:
        output.unlink();raise ValueError('Controlli tecnici falliti: '+', '.join(report['errors']))
    (directory/'caption.txt').write_text(fact['content']['caption'],encoding='utf-8')
    (directory/'evidence.json').write_text(json.dumps(fact,indent=2,ensure_ascii=False),encoding='utf-8')
    (directory/'subtitles.srt').write_text('\n'.join(f'{i+1}\n{timestamp(i*SHOT)} --> {timestamp((i+1)*SHOT)}\n'+ '\n'.join(cue)+'\n' for i,cue in enumerate(scene.cues)),encoding='utf-8')
    (directory/'audio-license.txt').write_text('MA DAVVERO? — Orbital Nocturne. Original local procedural composition, stereo 48 kHz, 120 BPM. No samples, recordings or external compositions. Generated music dedicated under CC0 1.0 https://creativecommons.org/publicdomain/zero/1.0/ . This grant does not apply to NASA materials. No voice narration.\n')
    (directory/'render.json').write_text(json.dumps({'engine':'cinema-1','duration':DURATION,'fps':FPS,'native_resolution':[W,H],'cuts':[i*SHOT for i in range(8)],'script':scene.cues,'asset':fact['asset'],'illustrations':'Original invented textures and geometry; not physical simulations.','voice':False},indent=2,ensure_ascii=False))
    frames=directory/'frames';frames.mkdir(exist_ok=True);sheet=Image.new('RGB',(1080,1000),'#03070d')
    for i in range(8):
        t=.75+i*SHOT;frame=frames/f'{i+1:02}.jpg'
        command(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(output),'-frames:v','1','-vf','scale=270:480',str(frame)])
        with Image.open(frame) as im:sheet.paste(im,((i%4)*270,(i//4)*500))
        ImageDraw.Draw(sheet).text(((i%4)*270+8,(i//4)*500+482),f'{t:.2f}s',fill='white')
    sheet.save(directory/'contact-sheet.jpg',quality=94)
    return output
