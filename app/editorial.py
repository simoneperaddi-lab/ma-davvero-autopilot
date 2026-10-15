from datetime import datetime, timedelta, timezone

from app.models import AuditEvent, ClaimReview, Content, EditorialTransition, ResearchSource
from app.research import normalized


class EditorialError(Exception):
    pass


def event(content: Content, actor: str, action: str, details: str):
    content.audit.append(AuditEvent(actor=actor, action=action, details=details))
    return content


def editable(content: Content):
    if content.status not in {"da_verificare", "in_revisione"}:
        raise EditorialError("Riaprire la bozza prima di modificare fonti o verifiche.")


def attach(content: Content, source: ResearchSource, actor: str):
    editable(content)
    if len(content.research_sources) >= 8:
        raise EditorialError("Massimo 8 fonti per contenuto.")
    if any(str(s.url) == str(source.url) for s in content.research_sources):
        raise EditorialError("Fonte già collegata.")
    content.research_sources.append(source)
    return event(content, actor, "source_attached", f"{source.id} | {source.origin} | {source.url}")


def checked(content: Content, source: ResearchSource, actor: str):
    editable(content)
    index = next((i for i, s in enumerate(content.research_sources) if s.id == source.id), None)
    if index is None:
        raise EditorialError("Fonte non collegata al contenuto.")
    previous = content.research_sources[index]
    content.research_sources[index] = source
    if previous.text_sha256 != source.text_sha256 or not source.reachable:
        for claim in content.claims:
            if claim.source_id == source.id:
                claim.outcome = "pending"
                claim.note = "Riscontro invalidato: fonte cambiata o non più raggiungibile."
    return event(content, actor, "source_checked", f"{source.id} | reachable={source.reachable} | sha256={source.text_sha256}")


def review_claim(content: Content, claim_id, body: ClaimReview, actor: str):
    editable(content)
    claim = next((c for c in content.claims if c.id == claim_id), None)
    if claim is None:
        raise EditorialError("Affermazione non trovata.")
    source = next((s for s in content.research_sources if s.id == body.source_id), None)
    if body.source_id is not None and source is None:
        raise EditorialError("Fonte non collegata al contenuto.")
    if body.outcome in {"supported", "contradicted"}:
        if source is None or not source.reachable or not source.checked_at:
            raise EditorialError("Serve una fonte collegata e recuperata con successo.")
        if source.checked_at < datetime.now(timezone.utc) - timedelta(days=7):
            raise EditorialError("Controllo fonte scaduto: ripetere il recupero (validità 7 giorni).")
        if len(body.quote.strip()) < 10 or normalized(body.quote) not in normalized(source.retrieved_text):
            raise EditorialError("Il passaggio citato deve comparire nel testo recuperato dal server (almeno 10 caratteri).")
    claim.outcome = body.outcome
    claim.source_id = body.source_id
    claim.source_sha256 = source.text_sha256 if source else ""
    claim.quote = body.quote
    claim.note = body.note
    claim.reviewer = actor
    claim.reviewed_at = datetime.now(timezone.utc)
    return event(content, actor, "claim_reviewed", f"{claim.id} | {body.outcome} | source={body.source_id} | sha256={claim.source_sha256} | quote={body.quote} | note={body.note}")


def transition(content: Content, body: EditorialTransition, actor: str):
    allowed = {"da_verificare": {"in_revisione"}, "in_revisione": {"approvato", "rifiutato", "da_verificare"},
               "approvato": {"da_verificare"}, "rifiutato": {"da_verificare"}}
    if body.status not in allowed[content.status]:
        raise EditorialError("Transizione editoriale non consentita.")
    if body.status == "approvato":
        if not content.claims or any(c.outcome != "supported" for c in content.claims):
            raise EditorialError("Approvazione bloccata: tutte le affermazioni richiedono verifica umana supportata da evidenza.")
        for claim in content.claims:
            source = next((s for s in content.research_sources if s.id == claim.source_id), None)
            if source is None or not source.reachable or not source.checked_at or source.checked_at < datetime.now(timezone.utc) - timedelta(days=7):
                raise EditorialError("Approvazione bloccata: manca una fonte recuperata negli ultimi 7 giorni.")
            if claim.source_sha256 != source.text_sha256 or normalized(claim.quote) not in normalized(source.retrieved_text):
                raise EditorialError("Approvazione bloccata: evidenza non coerente con l'ultima fonte recuperata.")
    previous = content.status
    content.status = body.status
    return event(content, actor, "status_changed", f"{previous} -> {body.status} | {body.note}")
