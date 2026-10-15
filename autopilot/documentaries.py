"""Small, audited editorial catalogue. Exact source passages, never generated citations.

A story is eligible only while its scientific passages, asset credit and policy
can be retrieved. Exhaustion is a safe skip, not an invitation to repeat stories.
"""
import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from PIL import Image

from autopilot.science import Unverified

POLICY = 'https://www.nasa.gov/nasa-brand-center/images-and-media/'
POLICY_QUOTE = 'NASA content used in a factual manner that does not imply endorsement may be used without needing explicit permission.'
STORIES = {
 'solar-rain': {
  'title': 'Sul Sole piove plasma', 'source': 'https://www.nasa.gov/solar-system/unexpected-rain-on-sun-links-two-solar-mysteries/',
  'quotes': ['Plasma, an electrically-charged gas, doesn’t pool like water, but instead traces the magnetic loops that emerge from the Sun’s surface like a rollercoaster on tracks.', 'As the plasma cools, it condenses and gravity lures it down the loop’s legs as coronal rain.'],
  'asset': 'https://www.nasa.gov/wp-content/uploads/2021/06/rain_earthtoscale.gif',
  'asset_page': 'https://www.nasa.gov/solar-system/unexpected-rain-on-sun-links-two-solar-mysteries/',
  'credit': 'NASA’s Solar Dynamics Observatory/Scientific Visualization Studio/Tom Bridgman, Lead Animator',
  'type': 'Osservazioni SDO: ultravioletto in falsi colori, tempo accelerato; Terra sovrapposta per confronto.',
  'cues': [['PIOVE.','SUL SOLE.'], ['Non acqua.','Plasma.'], ['Gas elettricamente','carico.'], ['Segue gli archi','magnetici.'], ['Si raffredda.','Si addensa.'], ['La gravità','lo fa ricadere.'], ['Una pioggia','di plasma.'], ['ANCHE LE STELLE','HANNO LA PIOGGIA.']],
  'caption': 'Sul Sole può piovere plasma: gas elettricamente carico che segue archi magnetici. Quando si raffredda e si addensa, la gravità lo fa ricadere lungo gli archi. La sequenza SDO mostra pioggia coronale dopo un’eruzione del 2012; non è pioggia d’acqua. Le altre scene sono illustrazioni animate originali, non simulazioni numeriche.',
 },
 'saturn-rings': {
  'title': 'Gli anelli non sono solidi', 'source': 'https://science.nasa.gov/saturn/facts/',
  'quotes': ['They are made of billions of small chunks of ice and rock coated with other materials such as dust.', 'each ring orbits at a different speed around the planet.'],
  'asset': 'https://www.nasa.gov/wp-content/uploads/2023/03/714625main_PIA14934_full_full.jpg',
  'asset_page': 'https://www.nasa.gov/image-article/splendor-seldom-seen/',
  'credit': 'NASA/JPL-Caltech/Space Science Institute',
  'type': 'Mosaico fotografico Cassini, 17 ottobre 2012; colori enfatizzati (filtri infrarosso, rosso, violetto).',
  'cues': [['NON SONO','CERCHI SOLIDI.'], ['Gli anelli','di Saturno.'], ['Miliardi','di frammenti.'], ['Ghiaccio','e roccia.'], ['Tutti in orbita.','Non un disco unico.'], ['Anelli diversi.','Velocità diverse.'], ['Da lontano,','sembrano continui.'], ['UN MONDO','DI FRAMMENTI.']],
  'caption': 'Gli anelli di Saturno sono formati da miliardi di frammenti di ghiaccio e roccia, con rivestimenti come polvere. Gli anelli orbitano a velocità diverse. Il mosaico Cassini è una vera osservazione in colori enfatizzati, non una foto nei colori percepiti dall’occhio. I sorvoli e i frammenti sono rappresentazioni artistiche originali, non riprese ravvicinate né una simulazione fisica.',
 },
 'red-moon': {
  'title': 'Perché la Luna diventa rossa', 'source': 'https://science.nasa.gov/moon/eclipses/',
  'quotes': ['The Moon moves into the inner part of Earth’s shadow, or the umbra.', 'Colors with shorter wavelengths ― the blues and violets ― scatter more easily than colors with longer wavelengths, like red and orange.', 'The same phenomenon that makes our sky blue and our sunsets red causes the Moon to turn reddish-orange during a lunar eclipse.'],
  'asset': 'https://www.nasa.gov/wp-content/uploads/2015/12/christmas2015fullmoon.jpg',
  'asset_page': 'https://www.nasa.gov/solar-system/rare-full-moon-on-christmas-day/',
  'credit': 'NASA/Goddard/Lunar Reconnaissance Orbiter',
  'type': 'Visualizzazione NASA/LRO della Luna piena del 25 dicembre 2015; non una fotografia di eclissi.',
  'cues': [['PERCHÉ','DIVENTA ROSSA?'], ['La Luna entra','nell’ombra terrestre.'], ['Ma un po’ di luce','la raggiunge.'], ['Attraversa','la nostra atmosfera.'], ['Il blu si disperde','più facilmente.'], ['Il rosso','arriva alla Luna.'], ['È la stessa fisica','dei tramonti.'], ['LA TERRA','COLORA LA LUNA.']],
  'caption': 'Durante un’eclissi lunare totale la Luna entra nell’ombra della Terra. Parte della luce solare attraversa l’atmosfera terrestre: le componenti blu si disperdono più facilmente e la luce che raggiunge la Luna può darle un colore rossastro. È lo stesso fenomeno alla base dei tramonti rossi. La visualizzazione NASA/LRO della Luna piena fornisce il dettaglio della superficie. La colorazione rossa è un’elaborazione illustrativa originale: non è una ripresa di eclissi. Il percorso della luce non è una simulazione quantitativa.',
 },
}
# Curated binary fingerprints prevent silent replacement by unrelated/poor material.
ASSET_HASHES = {'solar-rain': '5591e3d4f7f42ff58e0914909c7243f69d341060ffadadf8bcd124ebd12a2cc2', 'saturn-rings': '6e5c0996adf3b17d856858e2d88b6d269fa0bf2a4c75708eca876e94fb39eeab', 'red-moon': 'b37b6fc8bdf3a369f903ac825e9f275e6340bb83c48fa02eecdaa1a561e7ee41'}


def plain(body):
    body = re.sub(r'<(script|style)\b.*?</\1>', '', body, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', body))).strip()


def fetch(url, limit=16_000_000):
    if urlsplit(url).scheme != 'https' or urlsplit(url).hostname not in {'www.nasa.gov', 'science.nasa.gov'}:
        raise Unverified('Dominio editoriale non autorizzato')
    for attempt in range(3):
        try:
            with httpx.stream('GET', url, timeout=45, follow_redirects=False) as response:
                response.raise_for_status()
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > limit:
                        raise Unverified('Risorsa troppo grande')
                return bytes(chunks)
        except (httpx.HTTPError, OSError):
            if attempt == 2:
                raise Unverified('Fonte o materiale NASA non disponibile') from None
            time.sleep(2**attempt)


def verify(key, cache):
    story = STORIES[key]
    pages = {}
    for url in dict.fromkeys([story['source'], story['asset_page'], POLICY]):
        raw = fetch(url, 2_000_000)
        pages[url] = {'sha256': hashlib.sha256(raw).hexdigest(), 'text': plain(raw.decode('utf-8'))}
    for quote in story['quotes']:
        if quote not in pages[story['source']]['text']:
            raise Unverified('Passaggio scientifico modificato: revisione necessaria')
    if story['credit'] not in pages[story['asset_page']]['text'] or POLICY_QUOTE not in pages[POLICY]['text']:
        raise Unverified('Crediti o condizioni d’uso non confermati')
    raw = fetch(story['asset'])
    digest = hashlib.sha256(raw).hexdigest()
    if digest != ASSET_HASHES[key]:
        raise Unverified('Materiale cambiato: revisione della provenienza necessaria')
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    target = cache / (key + Path(urlsplit(story['asset']).path).suffix)
    target.write_bytes(raw)
    with Image.open(target) as im:
        dimensions = list(im.size)
        required = {'solar-rain': (600,338), 'saturn-rings': (960,446), 'red-moon': (1400,1400)}[key]
        if im.width < required[0] or im.height < required[1]:
            raise Unverified('Risoluzione insufficiente per la composizione prevista')
    evidence = {'subject': key, 'fingerprint': hashlib.sha256(key.encode()).hexdigest(),
        'checked_at': datetime.now(timezone.utc).isoformat(), 'source_url': story['source'],
        'reference_url': story['source'], 'source_row': {'editorial_story': key},
        'source_sha256': hashlib.sha256(json.dumps(story['quotes'], ensure_ascii=False).encode()).hexdigest(), 'documentary': key,
        'content': {'caption': story['caption'] + '\n\nFonte: ' + story['source'] + '\nImmagini: ' + story['credit'] + '\n' + story['asset_page'] + '\nProduzione automatica MA DAVVERO?: illustrazioni procedurali. NASA non ha revisionato né approvato questo video ed è citata esclusivamente per le risorse originali.\n#MaDavvero #Scienza #Spazio'},
        'claims': [{'quote': q, 'source': story['source']} for q in story['quotes']],
        'source_pages': {url: {'sha256': p['sha256']} for url,p in pages.items()},
        'asset': {'url': story['asset'], 'page': story['asset_page'], 'sha256': digest, 'dimensions': dimensions,
                  'credit': story['credit'], 'type': story['type'], 'policy': POLICY,
                  'permission_quote': POLICY_QUOTE, 'use': 'Divulgazione fattuale; nessuna approvazione NASA implicita.'}}
    # Exact cited passages and source snapshots travel with the deliverable.
    for i,(url,p) in enumerate(pages.items()):
        (cache / f'{key}-source-{i}.txt').write_text(url+'\n\n'+p['text'], encoding='utf-8')
    return evidence, target


class DocumentaryArchive:
    def __init__(self, http, cache='data/editorial-cache'):
        self.cache = cache

    def select(self, used):
        failures = []
        for key in STORIES:
            if key in used:
                continue
            try:
                fact, _ = verify(key, self.cache)
                return fact
            except Unverified as exc:
                failures.append(str(exc))
        raise Unverified('Nessuna storia nuova verificata nel catalogo editoriale. ' + '; '.join(failures))
