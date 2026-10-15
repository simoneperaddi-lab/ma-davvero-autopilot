from pathlib import Path
from typing import Literal
from decimal import Decimal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mad_provider: Literal["demo", "openai"] = "demo"
    mad_storage: Literal["sqlite", "supabase"] = "sqlite"
    mad_data_dir: Path = Path("data")
    mad_openai_model: str = "gpt-4.1-mini"
    openai_api_key: SecretStr | None = None
    supabase_url: str = ""
    supabase_service_role_key: SecretStr | None = None
    # Secure by default. Local mode is an explicit, loopback-only opt-out.
    mad_auth_mode: Literal["basic", "local"] = "basic"
    mad_auth_username: str = "editor"
    mad_auth_password: SecretStr | None = None
    mad_public_origin: str = ""
    mad_rate_per_minute: int = Field(default=120, ge=1, le=10000)
    mad_generate_per_minute: int = Field(default=6, ge=1, le=100)
    mad_export_per_minute: int = Field(default=4, ge=1, le=60)
    mad_research_per_minute: int = Field(default=10, ge=1, le=100)
    mad_paid_enabled: bool = False
    mad_openai_daily_calls: int = Field(default=0, ge=0)
    mad_openai_daily_budget_usd: Decimal = Field(default=Decimal("0"), ge=0)
    mad_openai_input_usd_per_million: Decimal = Field(default=Decimal("0"), ge=0)
    mad_openai_output_usd_per_million: Decimal = Field(default=Decimal("0"), ge=0)
    mad_openai_call_ceiling_usd: Decimal = Field(default=Decimal("0"), ge=0)
