from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.controls import Controls, LimitError
from app.demo import example
from app.generation import GenerationError, generate
from app.models import Category, GenerateRequest, ResearchSource, ScriptBatch


def configured(settings):
    settings.mad_paid_enabled = True
    settings.mad_openai_daily_calls = 2
    settings.mad_openai_daily_budget_usd = Decimal("0.10")
    settings.mad_openai_call_ceiling_usd = Decimal("0.05")
    settings.mad_openai_input_usd_per_million = Decimal("0.4")
    settings.mad_openai_output_usd_per_million = Decimal("1.6")
    return settings


def test_paid_disabled_before_any_network_or_sdk(settings):
    settings.mad_provider = "openai"
    settings.openai_api_key = SecretStr("synthetic-test-only")
    with pytest.raises(LimitError, match="disabilitate"):
        generate(settings, GenerateRequest())


def test_budget_and_calls_are_atomic_and_persistent(settings):
    configured(settings)
    ledger = Controls(settings.mad_data_dir)
    def reserve(_):
        try:
            return ledger.reserve(settings, 20_000, 6000)
        except LimitError:
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(reserve, range(4)))
    assert len([r for r in results if r]) == 2
    report = Controls(settings.mad_data_dir).report(settings)
    assert report["calls"] == 2
    assert Decimal(report["reserved_usd"]) == Decimal("0.0352")


def test_cost_ceiling_and_daily_spend_block_before_reservation(settings):
    configured(settings)
    ledger = Controls(settings.mad_data_dir)
    settings.mad_openai_call_ceiling_usd = Decimal("0.001")
    with pytest.raises(LimitError, match="per chiamata"):
        ledger.reserve(settings, 20_000, 6000)
    settings.mad_openai_call_ceiling_usd = Decimal("0.05")
    settings.mad_openai_daily_budget_usd = Decimal("0.0176")
    ledger.reserve(settings, 20_000, 6000)
    with pytest.raises(LimitError, match="giornaliero"):
        ledger.reserve(settings, 20_000, 6000)


def test_missing_prices_unknown_model_and_no_refund_on_failure(settings):
    configured(settings)
    ledger = Controls(settings.mad_data_dir)
    settings.mad_openai_input_usd_per_million = Decimal("0")
    with pytest.raises(LimitError, match="tariffe"):
        ledger.reserve(settings, 20_000, 6000)
    configured(settings)
    settings.mad_openai_model = "unpriced-model"
    with pytest.raises(LimitError, match="Modello"):
        ledger.reserve(settings, 20_000, 6000)
    settings.mad_openai_model = "gpt-4.1-mini"
    reservation = ledger.reserve(settings, 20_000, 6000)
    ledger.finish(reservation, "failed_or_uncertain")
    report = ledger.report(settings)
    assert report["reserved_usd"] == "0.0176"
    assert report["statuses"] == {"failed_or_uncertain": 1}
    assert report["usage_reported_calls"] == 0


def test_fabricated_ai_citation_rejected_but_attempt_counted(settings, monkeypatch):
    configured(settings)
    settings.mad_provider = "openai"
    settings.openai_api_key = SecretStr("synthetic-test-only")
    real = ResearchSource(title="Registry fixture", url="https://doi.org/10.1073/pnas.172399499", origin="crossref")
    monkeypatch.setattr("app.generation.research.search", lambda *args: [real])
    factory = MagicMock()
    factory.return_value.__enter__.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=ScriptBatch(scripts=[example(Category.nature)]), usage=SimpleNamespace(input_tokens=120, output_tokens=300))
    monkeypatch.setattr("app.generation.OpenAI", factory)
    with pytest.raises(GenerationError, match="fonte non presente"):
        generate(settings, GenerateRequest(category="natura"))
    assert factory.call_args.kwargs["max_retries"] == 0
    report = Controls(settings.mad_data_dir).report(settings)
    assert report["calls"] == 1
    assert report["input_tokens"] == 120
    assert report["statuses"] == {"failed_or_uncertain": 1}


def test_demo_is_free_and_reporting_has_no_secrets(client):
    client.post("/api/generate", json={})
    report = client.get("/api/usage")
    assert report.json()["calls"] == 0
    assert report.json()["paid_enabled"] is False
    assert "api_key" not in report.text
