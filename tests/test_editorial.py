from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.models import ResearchSource
from app.storage import ConflictError, SQLiteStore


def create(client):
    return client.post("/api/generate", json={"category": "spazio"}).json()[0]


def link_and_check(client, content, monkeypatch):
    url = f'/api/contents/{content["id"]}'
    response = client.post(url + "/sources", json={"revision": content["revision"], "suggested_index": 0})
    assert response.status_code == 200, response.text
    content = response.json()
    monkeypatch.setattr("app.research.fetch_public", lambda _: ("Venus takes about 243 Earth days to rotate once. A source for human review.", "text/plain", "https://science.nasa.gov/venus/facts/"))
    response = client.post(url + f'/sources/{content["research_sources"][0]["id"]}/check', json={"revision": content["revision"]})
    assert response.status_code == 200, response.text
    return response.json()


def test_complete_human_workflow_and_immutable_audit(client, monkeypatch):
    content = link_and_check(client, create(client), monkeypatch)
    url = f'/api/contents/{content["id"]}'
    assert all(c["outcome"] == "pending" for c in content["claims"])
    content = client.post(url + "/editorial", json={"revision": content["revision"], "status": "in_revisione", "note": "Richiesta revisione editoriale umana."}).json()
    blocked = client.post(url + "/editorial", json={"revision": content["revision"], "status": "approvato", "note": "Tentativo senza revisione dei claim."})
    assert blocked.status_code == 422
    for claim in content["claims"]:
        response = client.post(url + f'/claims/{claim["id"]}/review', json={
            "revision": content["revision"], "outcome": "supported", "source_id": content["research_sources"][0]["id"],
            "quote": "Venus takes about 243 Earth days to rotate once.", "note": "Valutazione umana di test sul passaggio citato.",
        })
        assert response.status_code == 200, response.text
        content = response.json()
    response = client.post(url + "/editorial", json={"revision": content["revision"], "status": "approvato", "note": "Revisione umana completata, approvazione editoriale."})
    assert response.status_code == 200, response.text
    approved = response.json()
    assert approved["status"] == "approvato"
    assert approved["audit"][-1]["actor"] == "local-editor"
    assert approved["audit"][:len(content["audit"])] == content["audit"]
    assert client.post(url + "/sources", json={"revision": approved["revision"], "suggested_index": 0}).status_code == 422
    reopened = client.post(url + "/editorial", json={"revision": approved["revision"], "status": "da_verificare", "note": "Riapertura esplicita per nuove verifiche."})
    assert reopened.json()["status"] == "da_verificare"


def test_fake_quotes_unknown_claim_and_revision_conflict(client, monkeypatch):
    content = link_and_check(client, create(client), monkeypatch)
    url = f'/api/contents/{content["id"]}'
    body = {"revision": content["revision"], "outcome": "supported", "source_id": content["research_sources"][0]["id"], "quote": "Invented evidence absent from source.", "note": "This is deliberately invalid evidence."}
    assert client.post(url + f'/claims/{content["claims"][0]["id"]}/review', json=body).status_code == 422
    body["revision"] = 0
    assert client.post(url + f'/claims/{content["claims"][0]["id"]}/review', json=body).status_code == 409


def test_invalid_transitions_and_forged_source_metadata(client):
    content = create(client)
    url = f'/api/contents/{content["id"]}'
    assert client.post(url + "/editorial", json={"revision": 0, "status": "approvato", "note": "Skip mandatory review phase."}).status_code == 422
    assert client.post(url + "/sources", json={"revision": 0, "suggested_index": 0, "reachable": True, "origin": "crossref"}).status_code == 422
    result = client.post(url + "/editorial", json={"revision": 0, "status": "in_revisione", "note": "Revisione iniziata correttamente."})
    assert result.status_code == 200
    assert client.post(url + "/editorial", json={"revision": 0, "status": "in_revisione", "note": "Versione ormai superata."}).status_code == 409


def test_source_change_invalidates_previous_human_evidence(client, monkeypatch):
    content = link_and_check(client, create(client), monkeypatch)
    url = f'/api/contents/{content["id"]}'
    content = client.post(url + f'/claims/{content["claims"][0]["id"]}/review', json={"revision": content["revision"], "outcome": "supported", "source_id": content["research_sources"][0]["id"], "quote": "Venus takes about 243 Earth days to rotate once.", "note": "Verifica umana del passaggio della fonte."}).json()
    monkeypatch.setattr("app.research.fetch_public", lambda _: ("A changed source body with different statements entirely.", "text/plain", "https://science.nasa.gov/venus/facts/"))
    changed = client.post(url + f'/sources/{content["research_sources"][0]["id"]}/check', json={"revision": content["revision"]}).json()
    assert changed["claims"][0]["outcome"] == "pending"


def test_sqlite_concurrent_updates_do_not_lose_audit(client, settings):
    content = create(client)
    store = SQLiteStore(settings.mad_data_dir)
    def update(_):
        try:
            store.mutate(content["id"], 0, lambda c: c)
            return "saved"
        except ConflictError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, range(2))) == ["conflict", "saved"]


def test_registry_search_attach_and_no_auto_verification(client, monkeypatch):
    source = ResearchSource(title="Registry fixture", url="https://doi.org/10.1073/pnas.172399499", origin="crossref", doi="10.1073/pnas.172399499", publisher="PNAS", year=2002)
    monkeypatch.setattr("app.research.search", lambda *args: [source])
    results = client.post("/api/sources/search", json={"query": "brain energy"})
    assert results.status_code == 200
    content = create(client)
    attached = client.post(f'/api/contents/{content["id"]}/sources', json={"revision": 0, "research_id": results.json()[0]["id"]})
    assert attached.status_code == 200
    content = attached.json()
    assert content["research_sources"][0]["origin"] == "crossref"
    assert not content["research_sources"][0]["reachable"]
    assert all(c["outcome"] == "pending" for c in content["claims"])
    assert content["status"] == "da_verificare"


def test_expired_evidence_cannot_be_approved(client, monkeypatch):
    from app.editorial import transition, EditorialError
    from app.models import Content, EditorialTransition
    import pytest
    content = Content.model_validate(link_and_check(client, create(client), monkeypatch))
    content.status = "in_revisione"
    for claim in content.claims:
        claim.outcome = "supported"
        claim.source_id = content.research_sources[0].id
    content.research_sources[0].checked_at = datetime.now(timezone.utc) - timedelta(days=8)
    with pytest.raises(EditorialError, match="7 giorni"):
        transition(content, EditorialTransition(revision=content.revision, status="approvato", note="Revisione di test con fonte scaduta."), "test-editor")
