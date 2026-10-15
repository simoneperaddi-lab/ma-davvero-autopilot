"""Conservative facts derived from NASA's published exoplanet measurements.

The archive is the authority, not an LLM. This is verification against a scientific
catalogue, not independent replication of the underlying astronomical research.
"""
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.models import Category, Content, Slide, Source

TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
COLUMNS = "pl_name,hostname,pl_orbper,pl_orbpererr1,pl_orbpererr2,pl_orbperlim,pl_controv_flag,default_flag,pl_refname"
QUERY = (f"select {COLUMNS} from ps where default_flag=1 and pl_controv_flag=0 "
         "and pl_orbperlim=0 and pl_orbper>0.05 and pl_orbper<1 order by pl_name")


class Unverified(ValueError):
    pass


def source_url(query):
    return TAP + "?" + urlencode({"query": query, "format": "json"})


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise Unverified("Misura numerica assente o non finita")
    return float(value)


def validate(row):
    for key in ("pl_name", "hostname"):
        if not isinstance(row.get(key), str) or not re.fullmatch(r"[A-Za-z0-9 .+()_-]{1,50}", row[key]):
            raise Unverified("Nome scientifico non riconosciuto")
    if row.get("default_flag") != 1 or row.get("pl_controv_flag") != 0 or row.get("pl_orbperlim") != 0:
        raise Unverified("Record controverso, non predefinito o solo limite")
    period = number(row.get("pl_orbper"))
    upper, lower = number(row.get("pl_orbpererr1")), number(row.get("pl_orbpererr2"))
    if not (0.05 < period < 1 and 0 < upper < period * .1 and -period * .1 < lower < 0):
        raise Unverified("Periodo o incertezza non sufficientemente affidabile")
    if period + upper >= 1:
        raise Unverified("Intervallo del periodo attraversa un giorno")
    # Real publication link supplied by NASA, never generated from a guessed DOI.
    reference = row.get("pl_refname", "")
    match = re.search(r'href=[\"\'](https://(?:ui\.adsabs\.harvard\.edu|doi\.org|arxiv\.org)/[^\"\'<>\s]+)', reference)
    if not match:
        raise Unverified("Riferimento bibliografico NASA mancante")
    return period, match.group(1)


class Archive:
    def __init__(self, http):
        self.http = http

    def rows(self, query):
        rows = self.http.json("GET", source_url(query))
        if not isinstance(rows, list) or len(rows) > 5000:
            raise Unverified("Risposta del catalogo inattesa")
        return rows

    def select(self, used):
        for row in self.rows(QUERY):
            if not isinstance(row, dict) or row.get("pl_name") in used:
                continue
            try:
                validate(row)
            except Unverified:
                continue
            # Separate retrieval by identifier guards against inconsistent snapshots.
            query = f"select {COLUMNS} from ps where default_flag=1 and pl_name='{row['pl_name']}'"
            verified = self.rows(query)
            if len(verified) != 1 or verified[0] != row:
                continue
            return make_fact(row, query)
        raise Unverified("Nessun nuovo esopianeta con misure e riferimenti sufficienti")


def make_fact(row, query):
    period, reference = validate(row)
    hours = f"{period * 24:.1f}".replace(".", ",")
    name = row["pl_name"]
    url = source_url(query)
    body = (f"Secondo il NASA Exoplanet Archive, {name} completa un'orbita attorno "
            f"alla propria stella in circa {hours} ore terrestri.")
    caption = (f"Un anno in meno di un giorno? Su {name}, sì.\n\n{body}\n"
               "Qui ‘anno’ significa periodo orbitale: non la durata del giorno sul pianeta. "
               "Il valore è arrotondato; la misura ha un'incertezza.\n\n"
               f"Fonte: NASA Exoplanet Archive (tabella ps)\n{url}\n"
               f"Pubblicazione indicata dal catalogo: {reference}\n\n"
               "#MaDavvero #Scienza #Astronomia #Esopianeti")
    content = Content(
        title=f"Un anno lampo: {name}", category=Category.space,
        hook="Un anno più corto di un giorno terrestre?", provider="demo",
        slides=[
            Slide(title="UN ANNO IN MENO DI UN GIORNO?", text=f"Il caso di {name}."),
            Slide(title=f"CIRCA {hours} ORE", text="È il tempo per un'orbita attorno alla sua stella, secondo il catalogo NASA."),
            Slide(title="ANNO ≠ GIORNO", text="Il periodo orbitale non è la durata del giorno sul pianeta."),
            Slide(title="IL NUMERO HA UN'INCERTEZZA", text="Questa è una misura astronomica arrotondata, non un valore esatto."),
            Slide(title="MA DAVVERO?", text="Sì: fonti e riferimento scientifico nella didascalia. Torna per un altro dato verificabile."),
        ], caption=caption, sources=[Source(title="NASA Exoplanet Archive — Planetary Systems", url=url)],
        verification_notes="Autopilota: derivazione deterministica da catalogo NASA; non una revisione umana dello studio.",
    )
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=False).encode()
    return {"subject": name, "fingerprint": hashlib.sha256(name.encode()).hexdigest(),
            "source_url": url, "reference_url": reference, "source_row": row,
            "source_sha256": hashlib.sha256(encoded).hexdigest(),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "content": content.model_dump(mode="json", include={"title", "category", "hook", "provider", "slides", "caption", "sources", "verification_notes"})}
