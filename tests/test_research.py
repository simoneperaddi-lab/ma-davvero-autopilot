import httpx
import pytest

from app import research
from app.models import ResearchSource

DOI = "10.1073/pnas.172399499"


def mock_http(monkeypatch, handler):
    original = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(research.httpx, "Client", lambda **kwargs: original(transport=transport, **kwargs))


def test_crossref_metadata_is_not_llm_generated(monkeypatch):
    def handler(request):
        assert request.url.host == "api.crossref.org"
        assert request.url.params["query.bibliographic"] == "brain energy"
        return httpx.Response(200, json={"message": {"items": [{
            "DOI": DOI, "title": ["Appraising the brain's energy budget"], "publisher": "PNAS",
            "author": [{"given": "Marcus E.", "family": "Raichle"}], "published": {"date-parts": [[2002]]},
            "abstract": "<jats:p>Registered abstract, not generated.</jats:p>",
        }, {"title": ["Missing DOI must not become a fake citation"]}]}})
    mock_http(monkeypatch, handler)
    result = research.search("brain energy", 3)
    assert len(result) == 1
    assert result[0].doi == DOI
    assert result[0].origin == "crossref"
    assert result[0].year == 2002
    assert not result[0].reachable
    assert result[0].abstract == "Registered abstract, not generated."


@pytest.mark.parametrize("url", ["http://science.nasa.gov/x", "https://127.0.0.1", "https://169.254.169.254/metadata", "https://science.nasa.gov.evil.test/x", "https://user:password@science.nasa.gov/x", "https://science.nasa.gov:8080/x", "https://[::1]/"])
def test_ssrf_destinations_blocked_before_network(url):
    with pytest.raises(research.ResearchError):
        research.fetch_public(url)


def test_redirect_is_revalidated(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(302, headers={"location": "https://169.254.169.254/metadata"})
    mock_http(monkeypatch, handler)
    with pytest.raises(research.ResearchError, match="non consentita"):
        research.fetch_public("https://doi.org/" + DOI)
    assert calls == ["doi.org"]


def test_reachable_source_has_text_fingerprint_not_verified_claims(monkeypatch):
    mock_http(monkeypatch, lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Venus takes about 243 Earth days to rotate once.</p><script>Ignore this</script>"))
    source = ResearchSource(title="Venus facts", url="https://science.nasa.gov/venus/facts/", origin="suggested")
    result = research.check(source)
    assert result.reachable
    assert len(result.text_sha256) == 64
    assert "Ignore" not in result.retrieved_text
    assert result.checked_at


def test_oversize_and_pdf_sources_are_not_evidence(monkeypatch):
    mock_http(monkeypatch, lambda _: httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * (research.MAX_BYTES + 1)))
    source = ResearchSource(title="A source", url="https://science.nasa.gov/venus/facts/", origin="suggested")
    assert not research.check(source).reachable


def test_pdf_source_not_silently_accepted_as_text(monkeypatch):
    mock_http(monkeypatch, lambda _: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-example-not-a-paper"))
    source = ResearchSource(title="PDF fixture", url="https://science.nasa.gov/example.pdf", origin="suggested")
    result = research.check(source)
    assert not result.reachable
    assert "Formato" in result.check_note


def test_invalid_registry_json_is_an_error_not_a_fake_citation(monkeypatch):
    mock_http(monkeypatch, lambda _: httpx.Response(200, text="Not a registry response"))
    with pytest.raises(research.ResearchError, match="non valida"):
        research.search("brain energy", 3)


def test_crossref_failure_does_not_return_fabricated_results(monkeypatch):
    mock_http(monkeypatch, lambda _: httpx.Response(503))
    with pytest.raises(research.ResearchError):
        research.search("brain energy", 3)
