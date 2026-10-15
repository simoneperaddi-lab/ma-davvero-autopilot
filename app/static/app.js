/* All generated content is inserted as text, never interpreted as HTML. */
const $ = (selector) => document.querySelector(selector);
let contents = [];
let selectedId = null;
let exporting = false;

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function notice(message, error = false) {
  $('#notice').textContent = message;
  $('#notice').className = error ? 'error' : '';
}
async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Richiesta non valida. Controlla i campi e riprova.');
  return body;
}
function post(body) {
  return {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
}
function renderList() {
  $('#total').textContent = contents.length;
  $('#pending').textContent = contents.length;
  $('#library-count').textContent = `${contents.length} contenuti`;
  const list = $('#content-list');
  list.replaceChildren();
  if (!contents.length) list.append(node('p', 'muted', 'Il laboratorio è pronto. Genera la prima curiosità.'));
  for (const content of contents) {
    const card = node('button', `content-card${content.id === selectedId ? ' selected' : ''}`);
    card.type = 'button';
    card.setAttribute('aria-pressed', String(content.id === selectedId));
    const top = node('div', 'card-top');
    top.append(node('span', '', content.category), node('span', '', content.provider === 'demo' ? 'DEMO' : 'OPENAI'));
    card.append(top, node('h3', '', content.title), node('p', '', content.hook), node('span', 'review-badge', '◌ Da verificare'));
    card.addEventListener('click', () => { selectedId = content.id; renderList(); renderDetail(content); });
    list.append(card);
  }
}
function renderDetail(content) {
  const detail = $('#detail');
  detail.replaceChildren();
  detail.append(node('p', 'eyebrow', `SCENEGGIATURA / ${content.category.toUpperCase()}`), node('h3', '', content.title), node('p', 'hook', content.hook), node('span', 'review-badge', 'Bozza · revisione umana necessaria'), node('h4', '', 'La storia, slide per slide'));
  const slides = node('ol', 'slides');
  content.slides.forEach((slide, i) => {
    const item = node('li', 'slide');
    const body = node('div');
    body.append(node('strong', '', slide.title), node('p', '', slide.text));
    item.append(node('span', 'slide-num', String(i + 1).padStart(2, '0')), body);
    slides.append(item);
  });
  detail.append(slides, node('h4', '', 'Fonti suggerite'));
  const sources = node('ul', 'sources');
  content.sources.forEach((source) => {
    const li = node('li');
    const link = node('a', '', source.title);
    const url = new URL(source.url);
    if (['https:', 'http:'].includes(url.protocol)) link.href = url.href;
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    li.append(link); sources.append(li);
  });
  detail.append(sources, node('p', 'verification', `DA CONTROLLARE — ${content.verification_notes} Le fonti non sono verificate automaticamente.`), node('h4', '', 'Caption'), node('p', 'caption', content.caption), node('h4', '', 'Porta la storia fuori dal laboratorio'));
  const actions = node('div', 'export-actions');
  const downloads = node('div', 'downloads');
  downloads.setAttribute('aria-live', 'polite');
  for (const [kind, label] of [['carousel', '↓ Carosello PNG'], ['reel', '↓ Reel verticale']]) {
    const button = node('button', 'secondary', label);
    button.disabled = exporting;
    button.addEventListener('click', async () => {
      exporting = true;
      document.querySelectorAll('.export-actions button').forEach((b) => { b.disabled = true; });
      button.textContent = 'Preparazione…';
      notice('Esportazione in corso. Il Reel può richiedere fino a 3 minuti.');
      try {
        const artifact = await api(`/api/contents/${content.id}/exports`, post({kind}));
        const link = node('a', 'download', `Scarica ${artifact.filename} ↗`);
        link.href = artifact.download_url; link.download = artifact.filename;
        // Keep the completed download accessible even if selection changed meanwhile.
        const completed = node('a', 'download', `Scarica ${artifact.filename} ↗`);
        completed.href = artifact.download_url; completed.download = artifact.filename;
        downloads.append(link);
        notice('File pronto. Nessuna pubblicazione effettuata. ');
        $('#notice').append(completed);
      } catch (error) { notice(error.message, true); }
      finally {
        exporting = false;
        document.querySelectorAll('.export-actions button').forEach((b) => { b.disabled = false; });
        button.textContent = label;
      }
    });
    actions.append(button);
  }
  const caption = node('a', 'secondary', '↓ Caption e fonti');
  caption.href = `/api/contents/${content.id}/caption`; caption.download = 'caption.txt';
  actions.append(caption);
  detail.append(actions, downloads, node('p', 'export-note', 'Carosello: PNG 1080 × 1350 in ZIP. Reel: MP4 1080 × 1920, 4 secondi per slide, senza audio. Tutti i visual includono “bozza · da verificare”.'));
}
$('#generate-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = $('#generate-button');
  button.disabled = true; button.textContent = 'Il laboratorio è al lavoro…';
  notice('Generazione in corso…');
  try {
    const generated = await api('/api/generate', post({category: $('#category').value, topic: $('#topic').value, count: Number($('#count').value)}));
    contents = [...generated, ...contents];
    selectedId = generated[0].id;
    renderList(); renderDetail(generated[0]);
    notice(`${generated.length} bozze create. Verifica sempre le fonti prima di condividere.`);
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; button.textContent = '✦ Genera curiosità ↗'; }
});
async function init() {
  try {
    const health = await api('/api/health');
    $('#mode').textContent = `${health.provider === 'demo' ? '● MODALITÀ DEMO' : '● OPENAI'} · ${health.storage.toUpperCase()}`;
    if (health.provider === 'demo') {
      $('#topic').disabled = true;
      $('#topic').placeholder = 'Tema libero disponibile con OpenAI';
      $('#provider-note').textContent = 'Demo: 3 esempi fissi, selezionabili per categoria. Più idee nella stessa categoria ripetono l’esempio.';
    } else {
      $('#provider-note').textContent = 'Generazione tramite OpenAI. I testi prodotti richiedono revisione editoriale e verifica delle fonti.';
    }
    contents = await api('/api/contents');
    selectedId = contents[0]?.id;
    renderList();
    if (contents.length) renderDetail(contents[0]);
  } catch (error) { $('#mode').textContent = 'CONNESSIONE NON DISPONIBILE'; notice(error.message, true); }
}
init();
