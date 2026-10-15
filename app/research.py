"""Free Crossref discovery and bounded retrieval from a fixed public allowlist."""
import hashlib
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit

import httpx

from app.models import ResearchSource

ALLOWED_HOSTS = frozenset({
    "science.nasa.gov", "www.nasa.gov", "ocean.si.edu", "doi.org", "api.crossref.org",
    "www.pnas.org", "pnas.org", "pmc.ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov",
    "www.nature.com", "nature.com", "www.science.org", "journals.plos.org",
})
MAX_BYTES = 500_000


class ResearchError(Exception):
    pass


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(html: str):
    parser = TextParser()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def normalized(text: str):
    return " ".join(text.casefold().split())


def validate_url(url: str):
    parsed = urlsplit(url)
    try:
        allowed = parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS and parsed.port in {None, 443}
    except ValueError:
        allowed = False
    if not allowed or parsed.username or parsed.password:
        raise ResearchError("Destinazione non consentita: sono ammessi solo host scientifici HTTPS della allowlist, anche nei redirect.")


def fetch_public(url: str):
    # Fixed hosts only: no arbitrary domains, IPs, credentials or redirects to internal services.
    for _ in range(4):
        validate_url(url)
        try:
            with httpx.Client(timeout=12, follow_redirects=False) as client:
                with client.stream("GET", url, headers={"User-Agent": "MaDavveroResearch/0.2 (editorial source review)"}) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ResearchError("Redirect senza destinazione.")
                        url = urljoin(url, location)
                        continue
                    response.raise_for_status()
                    chunks, length = [], 0
                    for chunk in response.iter_bytes():
                        length += len(chunk)
                        if length > MAX_BYTES:
                            raise ResearchError("Risposta troppo grande per il controllo automatico (500 KB).")
                        chunks.append(chunk)
                    return b"".join(chunks).decode("utf-8", errors="replace"), response.headers.get("content-type", ""), url
        except httpx.HTTPError as exc:
            raise ResearchError("Fonte non recuperabile: controllare rete, accesso o restrizioni del sito.") from exc
    raise ResearchError("Troppi redirect nella fonte.")


def search(query: str, limit: int) -> list[ResearchSource]:
    # Parameters are encoded, never interpolated as a new host or arbitrary URL.
    import json
    from urllib.parse import urlencode
    body, _, _ = fetch_public("https://api.crossref.org/works?" + urlencode({"query.bibliographic": query, "rows": limit}))
    try:
        items = json.loads(body)["message"]["items"]
        results = []
        for item in items:
            doi = item.get("DOI", "")
            titles = item.get("title", [])
            if not re.fullmatch(r"10\.\d{4,9}/\S+", doi) or not titles:
                continue
            date = item.get("published", {}).get("date-parts", [[]])[0]
            results.append(ResearchSource(
                title=plain_text(titles[0])[:500], url="https://doi.org/" + quote(doi, safe="/"),
                origin="crossref", doi=doi, publisher=item.get("publisher", "")[:300],
                authors=[f'{a.get("given", "")} {a.get("family", "")}'.strip() for a in item.get("author", [])[:10]],
                year=date[0] if date else None, abstract=plain_text(item.get("abstract", ""))[:6000],
                check_note="Metadati restituiti da Crossref; pertinenza e affermazioni ancora da verificare.",
            ))
        return results
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise ResearchError("Risposta Crossref non valida; nessuna citazione è stata inventata o sostituita.") from exc


def check(source: ResearchSource) -> ResearchSource:
    result = source.model_copy(deep=True)
    result.checked_at = datetime.now(timezone.utc)
    result.reachable = False
    result.retrieved_text = ""
    result.text_sha256 = ""
    try:
        body, mime, final_url = fetch_public(str(source.url))
        if "text/html" not in mime and "text/plain" not in mime:
            raise ResearchError("Formato non supportato. Il controllo accetta HTML o testo, non PDF o immagini.")
        text = plain_text(body) if "html" in mime else " ".join(body.split())
        if len(text) < 30:
            raise ResearchError("Testo insufficiente; non è possibile estrarre un riscontro.")
        result.reachable = True
        result.retrieved_text = text[:100_000]
        result.text_sha256 = hashlib.sha256(result.retrieved_text.encode()).hexdigest()
        result.check_note = f"Pagina recuperata da {final_url}. Raggiungibilità e testo non dimostrano la verità delle affermazioni."
    except ResearchError as exc:
        result.check_note = str(exc)
    return result
