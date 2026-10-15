from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from app.demo import example
from app.generation import GenerationError, generate
from app.models import Category, Content, GenerateRequest, ScriptBatch
from app.storage import StorageError, SupabaseStore
from app.models import ResearchSource


def enable_mock_paid(settings, monkeypatch):
    from decimal import Decimal
    settings.mad_paid_enabled = True
    settings.mad_openai_daily_calls = 2
    settings.mad_openai_daily_budget_usd = Decimal("1")
    settings.mad_openai_call_ceiling_usd = Decimal("0.10")
    settings.mad_openai_input_usd_per_million = Decimal("0.40")
    settings.mad_openai_output_usd_per_million = Decimal("1.60")
    source = example(Category.nature).sources[0]
    monkeypatch.setattr("app.generation.research.search", lambda *a: [ResearchSource(title=source.title, url=source.url, origin="crossref")])


def test_openai_structured_output(settings, monkeypatch):
    enable_mock_paid(settings, monkeypatch)
    settings.mad_provider = "openai"
    settings.openai_api_key = SecretStr("test-only-key")
    factory = MagicMock()
    parse = factory.return_value.__enter__.return_value.responses.parse
    parse.return_value = SimpleNamespace(output_parsed=ScriptBatch(scripts=[example(Category.nature)]))
    monkeypatch.setattr("app.generation.OpenAI", factory)
    contents = generate(settings, GenerateRequest(category="natura", topic="polpi"))
    assert contents[0].provider == "openai"
    assert contents[0].status == "da_verificare"
    assert parse.call_args.kwargs["text_format"] is ScriptBatch


def test_openai_missing_key_does_not_silently_fallback(settings):
    settings.mad_provider = "openai"
    settings.openai_api_key = None
    with pytest.raises(GenerationError, match="OPENAI_API_KEY"):
        generate(settings, GenerateRequest())


def test_openai_refusal(settings, monkeypatch):
    enable_mock_paid(settings, monkeypatch)
    settings.mad_provider = "openai"
    settings.openai_api_key = SecretStr("test-only-key")
    factory = MagicMock()
    factory.return_value.__enter__.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=None)
    monkeypatch.setattr("app.generation.OpenAI", factory)
    with pytest.raises(GenerationError):
        generate(settings, GenerateRequest())


def test_supabase_roundtrip_and_pagination(settings, monkeypatch):
    settings.supabase_url = "https://example.supabase.co"
    settings.supabase_service_role_key = SecretStr("test-only-key")
    rows = []
    calls = []
    def request(method, url, **kwargs):
        calls.append((method, kwargs))
        if method == "POST":
            rows.extend(kwargs["json"])
            return httpx.Response(201, request=httpx.Request(method, url))
        params = kwargs["params"]
        result = [r for r in rows if f'eq.{r["id"]}' == params["id"]] if "id" in params else rows[params["offset"]:params["offset"] + 1]
        return httpx.Response(200, json=result, request=httpx.Request(method, url))
    monkeypatch.setattr("app.storage.httpx.request", request)
    store = SupabaseStore(settings)
    contents = [Content(**example(c).model_dump(), provider="demo") for c in [Category.space, Category.nature]]
    store.save(contents)
    assert store.list() == contents
    assert store.get(contents[0].id) == contents[0]
    assert calls[0][1]["headers"]["Prefer"] == "return=minimal"
    assert "service_role" not in str(calls[0][1]["json"])


def test_supabase_errors_redact_response(settings, monkeypatch):
    settings.supabase_url = "https://example.supabase.co"
    settings.supabase_service_role_key = SecretStr("test-only-key")
    def denied(method, url, **kwargs):
        return httpx.Response(403, text="private diagnostic", request=httpx.Request(method, url))
    monkeypatch.setattr("app.storage.httpx.request", denied)
    with pytest.raises(StorageError) as result:
        SupabaseStore(settings).list()
    assert "private diagnostic" not in str(result.value)


def test_supabase_optimistic_update_and_legacy_rows(settings, monkeypatch):
    from app.storage import ConflictError
    settings.supabase_url = "https://example.supabase.co"
    settings.supabase_service_role_key = SecretStr("test-only-key")
    content = Content(**example(Category.space).model_dump(), provider="demo")
    payload = content.model_dump(mode="json")
    payload.pop("revision")  # Real MVP payloads lack the new revision field.
    patches = []
    def request(method, url, **kwargs):
        if method == "GET":
            return httpx.Response(200, json=[{"payload": payload}], request=httpx.Request(method, url))
        patches.append(kwargs)
        return httpx.Response(200, json=[kwargs["json"]], request=httpx.Request(method, url))
    monkeypatch.setattr("app.storage.httpx.request", request)
    store = SupabaseStore(settings)
    updated = store.mutate(content.id, 0, lambda c: c)
    assert updated.revision == 1
    assert "is.null" in patches[0]["params"]["or"]
    assert patches[0]["headers"]["Prefer"] == "return=representation"
    with pytest.raises(ConflictError):
        store.mutate(content.id, 5, lambda c: c)


def test_supabase_concurrent_change_is_not_silently_overwritten(settings, monkeypatch):
    from app.storage import ConflictError
    settings.supabase_url = "https://example.supabase.co"
    settings.supabase_service_role_key = SecretStr("test-only-key")
    content = Content(**example(Category.space).model_dump(), provider="demo")
    def request(method, url, **kwargs):
        return httpx.Response(200, json=[{"payload": content.model_dump(mode="json")}] if method == "GET" else [], request=httpx.Request(method, url))
    monkeypatch.setattr("app.storage.httpx.request", request)
    with pytest.raises(ConflictError, match="concorrente"):
        SupabaseStore(settings).mutate(content.id, 0, lambda c: c)
