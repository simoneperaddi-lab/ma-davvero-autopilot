from pathlib import Path
from typing import Literal

from pydantic import SecretStr
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
