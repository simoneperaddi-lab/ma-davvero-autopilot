from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


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


class ResearchSource(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    url: HttpUrl
    origin: Literal["crossref", "suggested"]
    doi: str = ""
    publisher: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    reachable: bool = False
    checked_at: datetime | None = None
    retrieved_text: str = ""
    text_sha256: str = ""
    check_note: str = "Non ancora controllata."


class Claim(BaseModel):
    id: UUID
    label: str
    text: str
    outcome: Literal["pending", "supported", "contradicted", "uncertain"] = "pending"
    source_id: UUID | None = None
    source_sha256: str = ""
    quote: str = ""
    note: str = ""
    reviewer: str = ""
    reviewed_at: datetime | None = None


class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str
    details: str


class Content(Script):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: Literal["demo", "openai"]
    status: Literal["da_verificare", "in_revisione", "approvato", "rifiutato"] = "da_verificare"
    revision: int = 0
    research_sources: list[ResearchSource] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def seed_claims(self):
        # Deterministic IDs also support old MVP rows without rewriting them.
        if not self.claims:
            statements = [("Titolo", self.title), ("Hook", self.hook)]
            statements += [(f"Slide {i + 1}", f"{slide.title}. {slide.text}") for i, slide in enumerate(self.slides)]
            statements.append(("Caption", self.caption))
            self.claims = [Claim(id=uuid5(self.id, label), label=label, text=text) for label, text in statements]
        return self


class GenerateRequest(BaseModel):
    category: Category = Category.all
    topic: str = Field(default="", max_length=160)
    count: int = Field(default=1, ge=1, le=3)


class ScriptBatch(BaseModel):
    scripts: list[Script] = Field(min_length=1, max_length=3)


class ExportRequest(BaseModel):
    kind: Literal["carousel", "reel"]
    style: Literal["static", "dynamic"] = "static"
    audio: Literal["none", "original"] = "none"


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content_id: UUID
    kind: Literal["carousel", "reel"]
    filename: str
    download_url: str
    style: Literal["static", "dynamic"] = "static"
    audio: Literal["none", "original"] = "none"
    render_note: str = ""
    content_revision: int = 0


class SourceSearch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(min_length=3, max_length=180)
    limit: int = Field(default=3, ge=1, le=5)


class Versioned(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    revision: int = Field(ge=0)


class AttachSource(Versioned):
    research_id: UUID | None = None
    suggested_index: int | None = Field(default=None, ge=0, le=4)

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.research_id is None) == (self.suggested_index is None):
            raise ValueError("Scegli una fonte di ricerca oppure un indice suggerito.")
        return self


class ClaimReview(Versioned):
    outcome: Literal["supported", "contradicted", "uncertain"]
    source_id: UUID | None = None
    quote: str = Field(default="", max_length=2000)
    note: str = Field(min_length=10, max_length=1000)


class EditorialTransition(Versioned):
    status: Literal["da_verificare", "in_revisione", "approvato", "rifiutato"]
    note: str = Field(min_length=10, max_length=1000)
