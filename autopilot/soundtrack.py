"""Original 120 BPM procedural soundtrack, synchronised to orbital.py's timeline."""
import math
import wave
from array import array
import sys

from autopilot.orbital import BEAT, DURATION

LICENSE = '''MA DAVVERO? — Orbital Pulse
Original procedural composition: local sine oscillators, synthesized kick and
seeded noise percussion. No recordings, external samples, commercial music or
third-party composition. 120 BPM; scene cuts fall every five beats.
The contributors dedicate this generated soundtrack to the public domain under
CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/
This does not license scientific articles or third-party material.
'''


def compose(path):
    rate = 48000
    notes = [0, 7, 12, 3, 10, 7, 5, 12]
    pcm = array('h')
    noise_state = 41
    for i in range(rate*DURATION):
        t = i/rate
        beat = int(t/BEAT)
        local = t % BEAT
        note = 174.614 * 2**(notes[beat % len(notes)]/12)
        tone = math.sin(2*math.pi*note*t) * math.exp(-local*5) * .07
        bass = math.sin(2*math.pi*87.307*t) * .045
        kick = math.sin(2*math.pi*(42*local+3*(1-math.exp(-local*22)))) * math.exp(-local*23) * .23
        noise_state = (1664525*noise_state + 1013904223) & 0xffffffff
        noise = noise_state/0xffffffff*2-1
        hat = noise * math.exp(-(t % (BEAT/2))*110) * .025
        snare = noise * math.exp(-local*40) * (.07 if beat % 4 == 2 else 0)
        fade = min(1, t/.015, (DURATION-t)/.35)
        pcm.append(round((tone+bass+kick+hat+snare)*fade*32767))
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(pcm.tobytes())
