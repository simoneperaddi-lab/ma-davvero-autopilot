/* Research, human decisions and audit. No API credentials are stored in the client. */
function statusLabel(status) {
  return {da_verificare: 'Bozza · da verificare', in_revisione: 'In revisione', approvato: 'Approvato editorialmente', rifiutato: 'Rifiutato'}[status] || status;
}
async function refreshUsage() {
  try {
    const usage = await api('/api/usage');
    document.querySelector('#usage-report').textContent = `OpenAI: ${usage.paid_enabled ? 'abilitato con limiti' : 'pagamenti disabilitati'} · ${usage.calls}/${usage.max_calls} chiamate · riserve $${usage.reserved_usd} / $${usage.daily_budget_usd} · giorno UTC ${usage.day_utc}. Le riserve non sono una fattura.`;
  } catch (error) { document.querySelector('#usage-report').textContent = `Limiti non disponibili: ${error.message}`; }
}
function field(label, input) {
  const wrapper = node('label', '', label); wrapper.append(input); return wrapper;
}
function option(value, label) {
  const el = node('option', '', label); el.value = value; return el;
}
function replaceContent(updated) {
  contents = contents.map((c) => c.id === updated.id ? updated : c);
  if (selectedId === updated.id) renderDetail(updated);
  renderList();
}
async function mutate(content, suffix, body, button) {
  button.disabled = true;
  try {
    const updated = await api(`/api/contents/${content.id}${suffix}`, post({revision: content.revision, ...body}));
    replaceContent(updated);
    notice('Decisione registrata. La cronologia conserva autore, data e versione.');
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
}
function renderEditorial(content, detail) {
  const section = node('section', 'editorial');
  section.append(node('h4', '', 'Ricerca fonti & verifica umana'), node('p', 'export-note', 'Crossref restituisce metadati reali. Una pagina raggiungibile non verifica una notizia. Il revisore deve confrontare ogni affermazione con un passaggio del testo recuperato.'));
  const editable = ['da_verificare', 'in_revisione'].includes(content.status);
  const searchForm = node('form', 'editorial-form');
  const query = node('input'); query.required = true; query.minLength = 3; query.maxLength = 180; query.placeholder = 'Es. Venus rotation · query scientifica, anche in inglese';
  const searchButton = node('button', 'secondary', 'Cerca in Crossref');
  searchForm.append(field('Ricerca bibliografica gratuita', query), searchButton);
  const results = node('div', 'research-results'); results.setAttribute('aria-live', 'polite');
  searchForm.addEventListener('submit', async (event) => {
    event.preventDefault(); searchButton.disabled = true;
    results.replaceChildren(node('p', 'muted', 'Ricerca in corso…'));
    try {
      const sources = await api('/api/sources/search', post({query: query.value, limit: 3}));
      results.replaceChildren();
      if (!sources.length) results.append(node('p', 'muted', 'Nessun risultato. Prova una query più precisa.'));
      for (const source of sources) {
        const row = node('div', 'research-result');
        const link = node('a', '', source.title); link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
        const attach = node('button', 'secondary', 'Collega alla bozza'); attach.type = 'button'; attach.disabled = !editable;
        attach.addEventListener('click', () => mutate(content, '/sources', {research_id: source.id}, attach));
        row.append(link, node('p', 'muted', `${source.authors.join(', ')} · ${source.year || 'data non disponibile'} · ${source.publisher} · DOI ${source.doi}`), attach);
        results.append(row);
      }
    } catch (error) { results.replaceChildren(node('p', 'error-text', error.message)); }
    finally { searchButton.disabled = false; }
  });
  section.append(searchForm, results);
  const suggestions = node('div', 'export-actions');
  content.sources.forEach((source, index) => {
    if (content.research_sources.some((s) => s.url === source.url)) return;
    const attach = node('button', 'secondary', `Collega fonte suggerita ${index + 1}`);
    attach.type = 'button'; attach.disabled = !editable;
    attach.addEventListener('click', () => mutate(content, '/sources', {suggested_index: index}, attach));
    suggestions.append(attach);
  });
  section.append(suggestions);
  for (const source of content.research_sources) {
    const row = node('div', 'research-result');
    row.append(node('strong', '', source.title), node('p', 'muted', `${source.origin} · ${source.reachable ? 'Pagina recuperata' : 'Non recuperata'} · ${source.checked_at ? new Date(source.checked_at).toLocaleString('it-IT') : 'nessun controllo'}`), node('p', 'export-note', source.check_note));
    const check = node('button', 'secondary', 'Recupera / ricontrolla testo'); check.disabled = !editable;
    check.addEventListener('click', () => mutate(content, `/sources/${source.id}/check`, {}, check));
    row.append(check);
    if (source.retrieved_text) {
      const text = node('details', 'source-text');
      text.append(node('summary', '', 'Leggi testo recuperato e copia un passaggio'), node('pre', '', source.retrieved_text));
      row.append(text);
    }
    section.append(row);
  }
  section.append(node('h4', '', 'Affermazioni da revisionare'));
  for (const claim of content.claims) {
    const record = node('details', 'claim-record');
    const labels = {pending: 'Da verificare', supported: 'Supportata · verifica umana', contradicted: 'Contraddetta', uncertain: 'Incerta'};
    record.append(node('summary', '', `${claim.label} — ${labels[claim.outcome]}`), node('p', 'claim-text', claim.text));
    const form = node('form', 'editorial-form');
    const outcome = node('select'); outcome.append(option('uncertain', 'Incerta'), option('supported', 'Supportata dal passaggio'), option('contradicted', 'Contraddetta dal passaggio'));
    outcome.value = claim.outcome === 'pending' ? 'uncertain' : claim.outcome;
    const source = node('select'); source.append(option('', 'Seleziona una fonte recuperata'));
    for (const s of content.research_sources.filter((s) => s.reachable)) source.append(option(s.id, s.title));
    source.value = claim.source_id || '';
    const quote = node('textarea'); quote.maxLength = 2000; quote.rows = 3; quote.value = claim.quote; quote.placeholder = 'Copia un passaggio dal testo recuperato. Non inventare citazioni.';
    const note = node('textarea'); note.required = true; note.minLength = 10; note.maxLength = 1000; note.rows = 2; note.value = claim.note; note.placeholder = 'Spiega il confronto tra il passaggio e questa affermazione.';
    const save = node('button', 'secondary', 'Registra verifica umana'); save.disabled = !editable;
    form.append(field('Esito', outcome), field('Fonte', source), field('Passaggio testuale', quote), field('Motivazione del revisore', note), save);
    form.addEventListener('submit', (event) => { event.preventDefault(); mutate(content, `/claims/${claim.id}/review`, {outcome: outcome.value, source_id: source.value || null, quote: quote.value, note: note.value}, save); });
    record.append(form);
    if (claim.reviewer) record.append(node('p', 'muted', `Ultima verifica: ${claim.reviewer} · ${new Date(claim.reviewed_at).toLocaleString('it-IT')}`));
    section.append(record);
  }
  section.append(node('h4', '', 'Decisione editoriale'));
  const transition = node('form', 'editorial-form');
  const status = node('select');
  const transitions = {da_verificare: ['in_revisione'], in_revisione: ['approvato', 'rifiutato', 'da_verificare'], approvato: ['da_verificare'], rifiutato: ['da_verificare']};
  for (const value of transitions[content.status]) status.append(option(value, statusLabel(value)));
  const reason = node('textarea'); reason.rows = 2; reason.required = true; reason.minLength = 10; reason.maxLength = 1000; reason.placeholder = 'Motivazione obbligatoria, salvata nella cronologia.';
  const decide = node('button', 'primary', 'Registra decisione');
  transition.append(field('Prossimo stato', status), field('Motivazione', reason), decide);
  transition.addEventListener('submit', (event) => { event.preventDefault(); mutate(content, '/editorial', {status: status.value, note: reason.value}, decide); });
  section.append(transition);
  const audit = node('details', 'audit-trail'); audit.append(node('summary', '', `Cronologia decisioni (${content.audit.length})`));
  const events = node('ol');
  for (const entry of [...content.audit].reverse()) {
    const item = node('li');
    item.append(node('strong', '', `${entry.action} · ${entry.actor}`), node('p', '', `${new Date(entry.at).toLocaleString('it-IT')} — ${entry.details}`));
    events.append(item);
  }
  audit.append(events); section.append(audit); detail.append(section);
}
document.addEventListener('DOMContentLoaded', refreshUsage);
