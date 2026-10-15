from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class Category(str, Enum):
    all = "tutte"
    space = "spazio"
    nature = "natura"
    body = "corpo"


class Source(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    url: HttpUrl


class Slide(BaseModel):
    title: str = Field(min_length=1, max_length=70)
    text: str = Field(min_length=1, max_length=320)


class Script(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    category: Category
    hook: str = Field(min_length=1, max_length=180)
    slides: list[Slide] = Field(min_length=3, max_length=6)
    caption: str = Field(min_length=1, max_length=1800)
    sources: list[Source] = Field(min_length=1, max_length=5)
    verification_notes: str = Field(min_length=1, max_length=600)


class Content(Script):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: Literal["demo", "openai"]
    status: Literal["da_verificare"] = "da_verificare"


class GenerateRequest(BaseModel):
    category: Category = Category.all
    topic: str = Field(default="", max_length=160)
    count: int = Field(default=1, ge=1, le=3)


class ScriptBatch(BaseModel):
    scripts: list[Script] = Field(min_length=1, max_length=3)


class ExportRequest(BaseModel):
    kind: Literal["carousel", "reel"]


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content_id: UUID
    kind: Literal["carousel", "reel"]
    filename: str
    download_url: str
