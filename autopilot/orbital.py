"""Original, schematic orbital motion graphics. No downloaded visual assets.

Screen geometry, colours, camera and motion speed are illustrative, not a fitted
orbital solution. Only the period and name come from the validated NASA record.
"""
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from autopilot.science import validate

WIDTH, HEIGHT, FPS, DURATION = 540, 960, 24, 20
BPM = 120
BEAT = 60 / BPM
CUT = 2.5  # five musical beats per shot
INK = '#071322'
WHITE = '#f4f5ef'
LIME = '#d6ff78'
TEAL = '#6cdacb'


@lru_cache(maxsize=48)
def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/' + name, size)


def fit(text, maximum, width=442, minimum=19):
    for size in range(maximum, minimum - 1, -1):
        face = font(size, True)
        if face.getlength(text) <= width:
            return face
    raise ValueError('Etichetta troppo lunga per la zona sicura del video')


def name_lines(name):
    # Identifiers may be 50 characters. Wrap even unbroken identifiers, never crop.
    lines, line = [], ''
    for char in name.upper():
        if font(22, True).getlength(line + char) > 430:
            lines.append(line.strip())
            line = ''
        line += char
    if line.strip():
        lines.append(line.strip())
    return lines


def story(row):
    period, _ = validate(row)
    hours = f'{period * 24:.1f}'.replace('.', ',')
    return [
        ('UN ANNO', f'IN ~{hours} ORE.'),
        ('UN PIANETA.', 'UNA STELLA.'),
        ('1 ORBITA', '= 1 ANNO'),
        (f'{hours} ORE', 'PER UN GIRO.'),
        ('IL SUO ANNO', '< 24 ORE'),
        ('ORBITA', '≠ ROTAZIONE'),
        ('UN DATO NASA.', 'CON UN’INCERTEZZA.'),
        ('MA DAVVERO?', 'SÌ. IN MENO DI UN GIORNO.'),
    ]


@lru_cache(maxsize=1)
def background():
    canvas = Image.new('RGB', (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(canvas)
    for y in range(HEIGHT):
        q = y / HEIGHT
        draw.line((0, y, WIDTH, y), fill=(int(5 + 11*q), int(17 - 5*q), int(30 + 4*q)))
    glow = Image.new('RGBA', canvas.size)
    pen = ImageDraw.Draw(glow)
    for r in range(500, 10, -10):
        pen.ellipse((-240-r, 470-r, -240+r, 470+r), fill=(12, 91, 108, int(18*(1-r/510))))
        pen.ellipse((610-r, 720-r, 610+r, 720+r), fill=(120, 39, 27, int(26*(1-r/510))))
    return Image.alpha_composite(canvas.convert('RGBA'), glow).convert('RGB')


@lru_cache(maxsize=1)
def stars():
    rng = random.Random(91)
    return [(rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.uniform(.2, 1), rng.uniform(0, 6)) for _ in range(130)]


@lru_cache(maxsize=1)
def sun():
    sprite = Image.new('RGBA', (320, 320))
    pen = ImageDraw.Draw(sprite)
    for r in range(159, 58, -1):
        a = int(65 * ((160-r)/102)**2)
        pen.ellipse((160-r, 160-r, 160+r, 160+r), fill=(255, 111, 33, a))
    for r in range(60, 0, -1):
        q = 1-r/60
        pen.ellipse((160-r, 160-r, 160+r, 160+r), fill=(255, int(144+102*q), int(50+164*q), 255))
    return sprite


@lru_cache(maxsize=32)
def planet(phase):
    """An original shaded sphere, with an illustrative blue palette."""
    size, radius = 120, 56
    sprite = Image.new('RGBA', (size, size))
    pixels = sprite.load()
    angle = phase * 2*math.pi/32
    light = (-math.cos(angle)*.88, -math.sin(angle)*.45, .4)
    for y in range(size):
        for x in range(size):
            nx, ny = (x-60)/radius, (y-60)/radius
            square = nx*nx + ny*ny
            if square > 1:
                continue
            z = math.sqrt(1-square)
            brightness = max(0, nx*light[0] + ny*light[1] + z*light[2])
            rim = .15*(1-z)**3
            shade = .13 + .83*brightness
            pixels[x,y] = (int(30*shade+40*rim), int(160*shade+60*rim), int(199*shade+50*rim), 255)
    return sprite


def paste_center(canvas, sprite, x, y, size):
    item = sprite.resize((round(size), round(size)), Image.Resampling.LANCZOS)
    canvas.paste(item, (round(x-size/2), round(y-size/2)), item)


def orbit_position(t, shot):
    """Two-second illustrated revolutions; not the physical orbital timescale."""
    angle = 2*math.pi*t/2 + .3
    # Different views and scale on each cut; gentle motion within shots.
    cameras = [(250, 467, 225, 114, 174), (250, 470, 190, 140, 125),
               (250, 466, 207, 100, 135), (250, 460, 182, 145, 116),
               (250, 438, 175, 93, 110), (190, 475, 215, 110, 138),
               (250, 460, 195, 119, 130), (250, 465, 205, 121, 165)]
    cx, cy, rx, ry, size = cameras[shot]
    drift = 1 + .045*math.sin((t % CUT)/CUT*math.pi)
    rx, ry = rx*drift, ry*drift
    return cx, cy, rx, ry, size, angle, (cx+rx*math.cos(angle), cy+ry*math.sin(angle))


class OrbitalScene:
    def __init__(self, row, simulation=False):
        self.period, _ = validate(row)
        self.row, self.simulation = row, simulation
        self.cues = story(row)
        self.hours = f'{self.period*24:.1f}'.replace('.', ',')

    def frame(self, t):
        t = max(0, min(DURATION - 1/FPS, t))
        shot = min(7, int(t / CUT))
        local = t % CUT
        pulse = math.exp(-12*(t % BEAT))
        canvas = background().copy()
        draw = ImageDraw.Draw(canvas)
        for x, y, brightness, phase in stars():
            xx = (x + t*(.7+brightness)) % WIDTH
            yy = (y + 3*math.sin(t*.3+phase)) % HEIGHT
            light = int(60+110*brightness*(.75+.25*math.sin(t+phase)))
            draw.ellipse((xx, yy, xx+1.2, yy+1.2), fill=(light, light, min(255,light+22)))
        # Brand and progress are inside mobile UI safe areas.
        draw.rounded_rectangle((36, 64, 62, 90), radius=8, fill=LIME)
        draw.text((42, 64), '?', font=font(20, True), fill=INK)
        draw.text((74, 65), 'MA DAVVERO?', font=font(20, True), fill=WHITE)
        draw.text((403, 68), f'{shot+1:02}/08', font=font(14), fill=TEAL)
        draw.line((36, 108, 474, 108), fill='#29434b', width=2)
        draw.line((36, 108, 36+438*t/DURATION, 108), fill=LIME, width=3)
        top, bottom = self.cues[shot]
        # Kinetic arrival lasts 0.2s and stays fully readable thereafter.
        offset = round(7*math.exp(-local*16))
        draw.text((36, 145+offset), top, font=fit(top, 44), fill=WHITE)
        draw.text((36, 201+offset), bottom, font=fit(bottom, 40), fill=LIME)

        cx, cy, rx, ry, star_size, theta, (px, py) = orbit_position(t, shot)
        if shot == 5:
            # Track the planet: a genuine camera close-up without inventing a spin period.
            dx, dy = 320-px, 470-py
            cx, cy, px, py = cx+dx, cy+dy, 320, 470
        draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), outline='#406b78', width=2)
        # Directional luminous wake visibly traces the orbit on every frame.
        for j in range(56):
            a = theta - 1.65 + j*1.65/56
            b = a + 1.65/56
            color = (int(50+j*2.5), int(95+j*2.5), int(95+j*.8))
            draw.line((cx+rx*math.cos(a), cy+ry*math.sin(a), cx+rx*math.cos(b), cy+ry*math.sin(b)), fill=color, width=4)
        if shot == 0:
            star_size *= 1 + .55*math.exp(-local*2.2)
        phase = int((theta % (2*math.pi))/(2*math.pi)*32) % 32
        planet_size = (74 if shot == 0 else 56) if shot != 5 else 210
        if math.sin(theta) < 0:
            paste_center(canvas, planet(phase), px, py, planet_size)
        paste_center(canvas, sun(), cx, cy, star_size*(1+.025*pulse)*2)
        if math.sin(theta) >= 0:
            paste_center(canvas, planet(phase), px, py, planet_size)
        draw = ImageDraw.Draw(canvas)
        # Small beat-synchronised graphic rings, not claims of stellar pulsation.
        radius = star_size*.40 + (t % BEAT)*22
        draw.arc((cx-radius, cy-radius, cx+radius, cy+radius), 210, 310,
                 fill=(int(70+110*pulse), int(65+90*pulse), 45), width=2)

        if shot == 1:
            draw.text((cx-37, cy+65), 'STELLA', font=font(17, True), fill='#ffd294')
            lx = min(382, max(38, px-35))
            draw.text((lx, py+37), 'PIANETA', font=font(17, True), fill=TEAL)
        if shot == 2:
            progress = (t % 2)/2
            draw.rounded_rectangle((62, 645, 438, 704), radius=15, fill='#102f3a')
            draw.text((83, 657), f'GIRO  {round(progress*100):02}%', font=font(25, True), fill=LIME)
            draw.line((245, 676, 418, 676), fill='#456371', width=5)
            draw.line((245, 676, 245+173*progress, 676), fill=LIME, width=5)
        elif shot == 4:
            draw.text((40, 608), f'ANNO DEL PIANETA  ~{self.hours} h', font=font(19, True), fill=LIME)
            draw.rounded_rectangle((40, 640, 40+420*self.period, 657), radius=7, fill=LIME)
            draw.text((40, 677), '24 ORE TERRESTRI', font=font(19, True), fill=TEAL)
            draw.rounded_rectangle((40, 709, 460, 726), radius=7, fill=TEAL)
        else:
            if shot == 0:
                lines = name_lines(self.row['pl_name'])
            elif shot == 3:
                lines = ['CIRCA • ORE TERRESTRI']
            elif shot == 5:
                lines = ['Il giorno è un’altra cosa.']
            elif shot == 6:
                lines = [f'PERIODO MISURATO: ~{self.hours} h', 'Valore arrotondato, con incertezza.']
            elif shot == 7:
                lines = ['Fonti nella didascalia.']
            else:
                lines = name_lines(self.row['pl_name'])
            for i, line in enumerate(lines):
                draw.text((38, 656+i*33), line, font=fit(line, 26, minimum=18), fill=WHITE if i == 0 else TEAL)

        draw.line((36, 773, 474, 773), fill='#35505a', width=1)
        draw.text((36, 792), 'SCHEMA • NON IN SCALA', font=font(20, True), fill=LIME)
        draw.text((36, 822), 'Colori illustrativi • tempo accelerato', font=font(17), fill='#c0d4d8')
        draw.text((36, 853), 'NASA EXOPLANET ARCHIVE', font=font(15, True), fill=TEAL)
        if self.simulation:
            draw.rectangle((0, 911, WIDTH, HEIGHT), fill='#59210d')
            draw.text((35, 925), 'SIMULAZIONE • NON PUBBLICARE', font=font(20, True), fill=WHITE)
        return canvas
