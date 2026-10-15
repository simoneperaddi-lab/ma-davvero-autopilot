"""Original cinematic illustrations + explicitly identified NASA observations.
No generated picture is described as a photograph or a physical simulation.
"""
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageSequence

from autopilot.documentaries import STORIES

W, H, FPS, DURATION, SHOT = 1080, 1920, 24, 24, 3
ACCENT = '#e3c091'

@lru_cache(maxsize=64)
def font(size, bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf', size)


def noise(size, seed):
    rng = np.random.default_rng(seed)
    result = np.zeros((size,size),np.float32)
    for grid, amplitude in [(5,.4),(13,.25),(32,.17),(83,.1),(211,.055)]:
        tile = Image.fromarray((rng.random((grid,grid))*255).astype('uint8')).resize((size,size),Image.Resampling.BICUBIC)
        result += np.asarray(tile)/255*amplitude
    return result


@lru_cache(maxsize=3)
def planet(kind):
    n=1100
    y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]
    r2=x*x+y*y; z=np.sqrt(np.maximum(0,1-r2)); tex=noise(n,71)
    if kind=='moon':
        # Crater-like relief is invented, clearly labelled as an illustration.
        relief=Image.fromarray(np.uint8(np.clip(tex*255,0,255)))
        d=ImageDraw.Draw(relief);rng=random.Random(41)
        for _ in range(950):
            px,py=rng.randrange(n),rng.randrange(n);r=rng.randrange(2,45)
            d.ellipse((px-r,py-r,px+r,py+r),outline=160,width=max(1,r//6))
            d.arc((px-r+2,py-r+2,px+r-2,py+r-2),80,250,fill=45,width=max(1,r//5))
        tex=np.asarray(relief.filter(ImageFilter.GaussianBlur(.7)))/255
        albedo=np.stack([tex*.82+.18]*3,-1)
    elif kind=='earth':
        land=(tex>.51)&(np.abs(y)<.85)
        albedo=np.empty((n,n,3));albedo[:]=[.025,.15,.28];albedo[land]=[.16,.28,.16]
        clouds=np.clip((noise(n,122)-.51)*7,0,.8)[...,None]
        albedo=albedo*(1-clouds)+clouds
    else:
        bands=.55+.13*np.sin(y*70+tex*8)+.07*np.sin(y*190)
        albedo=np.stack([bands*1.1,bands*.92,bands*.65],-1)
    light=np.clip(x*-.55+y*-.25+z*.8,0,1)*.92+.045
    rgb=np.uint8(np.clip(albedo*light[...,None]*255,0,255));alpha=np.uint8(r2<1)*255
    return Image.fromarray(np.dstack([rgb,alpha]),'RGBA')


@lru_cache(maxsize=1)
def starfield():
    im=Image.new('RGB',(W,H),'#03070d');d=ImageDraw.Draw(im);rng=random.Random(29)
    for _ in range(700):
        x,y=rng.randrange(W),rng.randrange(H);v=rng.randrange(35,170);r=1 if rng.random()<.96 else 2
        d.ellipse((x-r,y-r,x+r,y+r), fill=(v,v,min(255,v+15)))
    return im


@lru_cache(maxsize=1)
def sun_surface():
    n=1400;y,x=np.mgrid[0:n,0:n];tex=noise(n,54)
    ridge=710+110*np.sin(x/n*3.2)
    inside=y>ridge
    intensity=np.clip(tex*.95+.22,0,1)
    glow=np.exp(-np.abs(y-ridge)/38)
    c=np.zeros((n,n,3),np.float32)
    c[:,:,0]=inside*intensity*220+glow*70
    c[:,:,1]=inside*intensity**3*150+glow*25
    c[:,:,2]=inside*intensity**7*55
    return Image.fromarray(np.uint8(np.clip(c,0,255)))


def paste(im, sprite, center, size):
    sprite=sprite.resize((int(size),int(size)),Image.Resampling.BICUBIC)
    im.paste(sprite,(round(center[0]-size/2),round(center[1]-size/2)),sprite)


def label(draw, xy, text, size=25, fill='#bfcbd4'):
    draw.text(xy,text,font=font(size),fill=fill)


class CinemaScene:
    def __init__(self,key,asset):
        self.key=key;self.cues=STORIES[key]['cues'];self.boxes=[]
        self.images=[]
        with Image.open(asset) as source:
            for frame in ImageSequence.Iterator(source):
                self.images.append(frame.convert('RGB').copy())
        if key=='red-moon':
            self.moon_source=self.images[0].resize((1100,1100),Image.Resampling.LANCZOS)
        self.rng=random.Random(64)
        self.particles=[(self.rng.random(),self.rng.random(),self.rng.random()) for _ in range(430)]

    def archive(self,t,shot):
        im=starfield().copy();source=self.images[int(t*8)%len(self.images)]
        if self.key=='red-moon':
            # NASA/LRO full-Moon visualization, unaltered colour in the archive shot.
            size=1100+int(120*math.sin(t*.4))
            frame=source.resize((size,size),Image.Resampling.LANCZOS)
            im.paste(frame,((W-size)//2,570))
        else:
            # Native-resolution archive inset, not a blurred full-screen enlargement.
            scale=min(960/source.width,1.0)
            size=(round(source.width*scale),round(source.height*scale))
            frame=source.resize(size,Image.Resampling.LANCZOS)
            y=700+int(24*math.sin(t*.5));im.paste(frame,((W-size[0])//2,y))
            d=ImageDraw.Draw(im);d.line((90,y-30,990,y-30),fill=ACCENT,width=2)
            label(d,(90,y-78),'ARCHIVIO / '+('SDO · 2012' if self.key=='solar-rain' else 'CASSINI · 2012'),28)
        return im

    def solar(self,t,shot):
        base=sun_surface()
        zoom=1.05+.06*math.sin(t*.3)
        frame=base.resize((int(1400*zoom),int(1400*zoom)),Image.Resampling.BICUBIC)
        im=Image.new('RGB',(W,H),'#050306');im.paste(frame,(-160+int(30*math.sin(t*.3)),430))
        glow=Image.new('RGB',(W,H));d=ImageDraw.Draw(glow)
        cx=540+80*math.sin(t*.2); floor=1250; radius=270 if shot<4 else 370
        for j in range(30):
            points=[];rr=radius+j*2
            for k in range(90):
                a=math.pi*k/89
                points.append((cx+rr*math.cos(a)+j*.7,floor-rr*1.65*math.sin(a)))
            d.line(points,fill=(110+j*3,30+j*2,8),width=2)
        for p,depth,phase in self.particles:
            a=math.pi*((phase+t*(.12+depth*.08))%1)
            r=radius+depth*60;x=cx+r*math.cos(a);y=floor-r*1.65*math.sin(a)
            d.ellipse((x-2,y-3,x+2,y+3),fill=(255,175+int(depth*70),90))
        from PIL import ImageChops
        im=ImageChops.add(im,glow.filter(ImageFilter.GaussianBlur(9)),scale=1)
        im=ImageChops.add(im,glow,scale=1)
        if shot in [4,5]:
            # A closer tracking view of descending plasma, not just changing titles.
            im=im.crop((110,500,970,1810)).resize((W,H),Image.Resampling.BICUBIC)
        return im

    def saturn(self,t,shot):
        im=starfield().copy();d=ImageDraw.Draw(im)
        if shot in [2,3,6]:
            # Travelling through a particulate ring: depth and individual motion.
            horizon=800;d.line((0,horizon,W,horizon-100),fill='#6c6151',width=2)
            for p,depth,phase in self.particles:
                z=(phase-t*.16)%1
                scale=1/(.15+z*2.8)
                x=540+(p-.5)*1900*scale;y=horizon+depth*850*scale
                r=2+12*scale
                if -80<x<W+80 and 450<y<H:
                    v=int(80+120*(1-z));d.polygon([(x-r,y),(x-r*.2,y-r*.8),(x+r,y-r*.3),(x+r*.6,y+r*.5),(x-r*.6,y+r)],fill=(v,min(255,v+7),min(255,v+12)))
                    d.line((x-r*.2,y-r*.8,x+r,y-r*.3),fill='#dce7eb',width=2)
            paste(im,planet('saturn'),(900,610),400)
        else:
            cx=540+50*math.sin(t*.27);cy=1040;rx=800+80*math.sin(t*.23);tilt=(.65 if shot==4 else .31)+.08*math.sin(t*.2)
            # Hundreds of concentric bands + independently moving orbit particles.
            def rings(front):
                for r in range(450,820,2):
                    if 610<r<635:continue
                    c=int(90+50*math.sin(r*1.7)+30*math.sin(r*.12));c=max(35,c)
                    points=[]
                    for a in np.linspace(0,math.pi,90):
                        a=a if front else a+math.pi
                        points.append((cx+r*rx/800*math.cos(a),cy+r*tilt*math.sin(a)))
                    ImageDraw.Draw(im).line(points,fill=(c,int(c*.87),int(c*.65)),width=2)
            rings(False);paste(im,planet('saturn'),(cx,cy),730);rings(True)
            d=ImageDraw.Draw(im)
            for p,depth,phase in self.particles[:150]:
                r=455+p*360;a=phase*math.tau+t*(.2+.2*(1-p));x=cx+r*rx/800*math.cos(a);y=cy+r*tilt*math.sin(a)
                if math.sin(a)>0 or abs(x-cx)>365:d.ellipse((x-2,y-2,x+2,y+2),fill='#e3d6b7')
        return im

    def lunar(self,t,shot):
        im=starfield().copy()
        if shot in [2,3,4,5]:
            # Side-on explanatory ray diagram, explicitly not to scale.
            d=ImageDraw.Draw(im);earth=(540,930);moon=(770,1380)
            for i in range(12):
                x=240+i*50
                d.line((x,480,x,780),fill=(160,140,90),width=2)
            atmosphere=Image.new('RGBA',(W,H));ad=ImageDraw.Draw(atmosphere)
            ad.ellipse((318,708,762,1152),outline=(80,150,255,180),width=18)
            atmosphere=atmosphere.filter(ImageFilter.GaussianBlur(6));im.paste(atmosphere,(0,0),atmosphere)
            paste(im,planet('earth'),earth,410)
            d=ImageDraw.Draw(im)
            for sign in [-1,1]:
                points=[(540+sign*235,700),(540+sign*218,980),(moon[0]+sign*65,moon[1])]
                d.line(points,fill='#e07046',width=4)
                p=(t*.6)%1;seg=0 if p<.5 else 1;u=(p*2)%1
                x=points[seg][0]*(1-u)+points[seg+1][0]*u;y=points[seg][1]*(1-u)+points[seg+1][1]*u
                d.ellipse((x-7,y-7,x+7,y+7),fill='#ffe0a1')
            for i in range(7):
                p=(t*.5+i/7)%1;x=315-p*220;y=790-p*200+i*13
                d.ellipse((x-3,y-3,x+3,y+3),fill='#70baff')
            paste(im,self.redmoon(),moon,230)
        else:
            size=960+90*math.sin(t*.3);center=(540+70*math.sin(t*.21),1050)
            paste(im,self.redmoon(),center,size)
        if shot==3:
            im=im.crop((250,600,850,1667)).resize((W,H),Image.Resampling.BICUBIC)
        elif shot==4:
            im=im.crop((80,470,800,1750)).resize((W,H),Image.Resampling.BICUBIC)
        elif shot==5:
            im=im.crop((430,900,1030,1867)).resize((W,H),Image.Resampling.BICUBIC)
        return im

    @lru_cache(maxsize=4)
    def redmoon(self):
        rgb=np.asarray(self.moon_source).copy()
        alpha=np.uint8(rgb.max(axis=2)>12)*255
        rgb=(rgb*np.array([1.0,.40,.19])).astype('uint8')
        return Image.fromarray(np.dstack([rgb,alpha]))

    def visual(self,t,shot):
        if shot==1:return self.archive(t,shot)
        return {'solar-rain':self.solar,'saturn-rings':self.saturn,'red-moon':self.lunar}[self.key](t,shot)

    def frame(self,t):
        shot=min(7,int(t/SHOT));im=self.visual(t,shot)
        # Six-frame cross-dissolve; no fade from black at opening.
        if shot>0 and t%SHOT<.25:
            previous=self.visual(t,shot-1);im=Image.blend(previous,im,(t%SHOT)/.25)
        overlay=Image.new('RGBA',(W,H));d=ImageDraw.Draw(overlay)
        for y in range(600):
            d.line((0,y,W,y),fill=(3,6,11,int(210*(1-y/600))))
        for y in range(1520,H):
            d.line((0,y,W,y),fill=(3,6,11,int(220*(y-1520)/(H-1520))))
        im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB');d=ImageDraw.Draw(im)
        self.boxes=[]
        self.text(d,(90,170),'MA DAVVERO?',27,False,'#e3c091')
        self.text(d,(90,232),{'solar-rain':'01 / FISICA DEL SOLE','saturn-rings':'02 / MONDI LONTANI','red-moon':'03 / LUCE E OMBRA'}[self.key],24,False,'#b7bdc7')
        for i,line in enumerate(self.cues[shot]):
            self.text(d,(86,330+i*86),line,68,True,'#f4f0e9')
        mode=('SDO · FALSI COLORI · TEMPO ACCELERATO' if self.key=='solar-rain' else 'CASSINI · COLORI ENFATIZZATI' if self.key=='saturn-rings' else 'NASA / LRO · VISUALIZZAZIONE') if shot==1 else 'ILLUSTRAZIONE ANIMATA · NON IN SCALA'
        self.text(d,(90,1620),mode,23,False,'#d6d3cd')
        self.text(d,(90,1664),'Fonti e crediti nella didascalia',25,False,'#aab6c3')
        d.line((90,1740,950,1740),fill='#33404b',width=2)
        d.line((90,1740,90+860*t/DURATION,1740),fill=ACCENT,width=3)
        return im

    def text(self,draw,xy,value,size,bold,fill):
        face=font(size,bold);box=draw.textbbox(xy,value,font=face)
        if box[0]<60 or box[2]>1000 or box[1]<130 or box[3]>1760:
            raise ValueError('Testo fuori dalla zona sicura: '+value)
        self.boxes.append(box);draw.text(xy,value,font=face,fill=fill)
