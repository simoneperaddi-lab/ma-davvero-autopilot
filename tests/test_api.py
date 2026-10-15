from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_dashboard_and_health(client):
    page = client.get("/")
    assert page.status_code == 200
    assert '<html lang="it">' in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/static/app.js").status_code == 200
    status = client.get("/api/health").json()
    assert status["instagram_publishing"] is False
    assert status["provider"] == "demo"


def test_generate_persist_and_reopen(client, settings):
    assert client.get("/api/contents").json() == []
    response = client.post("/api/generate", json={"count": 3})
    assert response.status_code == 201
    contents = response.json()
    assert len(contents) == 3
    assert {c["category"] for c in contents} == {"spazio", "natura", "corpo"}
    assert len({c["id"] for c in contents}) == 3
    for content in contents:
        assert content["status"] == "da_verificare"
        assert content["provider"] == "demo"
        assert len(content["slides"]) == 5
        assert content["sources"][0]["url"].startswith("https://")
        assert client.get(f'/api/contents/{content["id"]}').json() == content
    with TestClient(create_app(settings), client=("127.0.0.1", 50000)) as reopened:
        assert len(reopened.get("/api/contents").json()) == 3


@pytest.mark.parametrize("body", [{"count": 0}, {"count": 4}, {"category": "fake"}, {"topic": "x" * 161}])
def test_invalid_generation(client, body):
    assert client.post("/api/generate", json=body).status_code == 422
    assert client.get("/api/contents").json() == []


def test_selected_category_and_caption(client):
    content = client.post("/api/generate", json={"category": "natura"}).json()[0]
    assert content["category"] == "natura"
    caption = client.get(f'/api/contents/{content["id"]}/caption')
    assert caption.status_code == 200
    assert "DA VERIFICARE" in caption.text
    assert content["sources"][0]["url"] in caption.text


def test_unknown_and_malformed_ids(client):
    assert client.get(f"/api/contents/{uuid4()}").status_code == 404
    assert client.get(f"/api/artifacts/{uuid4()}").status_code == 404
    assert client.get("/api/artifacts/not-a-uuid").status_code == 422
    assert client.post(f"/api/contents/{uuid4()}/exports", json={"kind": "carousel"}).status_code == 404
    assert client.post(f"/api/contents/{uuid4()}/exports", json={"kind": "publish"}).status_code == 422


def test_no_instagram_publish_route(client):
    assert client.post("/api/publish", json={}).status_code == 404


def test_original_mvp_payload_can_be_reopened_and_edited(settings):
    import json
    from app.demo import example
    from app.models import Category, Content
    from app.storage import SQLiteStore
    content = Content(**example(Category.space).model_dump(), provider="demo")
    payload = content.model_dump(mode="json", exclude={"revision", "claims", "research_sources", "audit"})
    store = SQLiteStore(settings.mad_data_dir)
    with store.connect() as db:
        db.execute("INSERT INTO contents VALUES (?, ?, ?)", (str(content.id), content.created_at.isoformat(), json.dumps(payload)))
    first, second = store.get(content.id), store.get(content.id)
    assert first.revision == 0
    assert first.claims == second.claims
    assert len(first.claims) == len(first.slides) + 3
    updated = store.mutate(content.id, 0, lambda c: c)
    assert updated.revision == 1
    assert store.get(content.id).claims == first.claims
