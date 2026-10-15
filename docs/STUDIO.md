# MA DAVVERO? — Content Studio, fase 2

Studio editoriale italiano per curiosità scientifiche: FastAPI, dashboard responsive, SQLite/Supabase, OpenAI opzionale, ricerca Crossref e video Pillow/FFmpeg. Interfaccia opzionale conservata da MVP e fase 2. La dashboard non pubblica: il nuovo autopilota separato è descritto nel [README](../README.md). Nessun servizio a pagamento attivato.

## Avvio locale senza credenziali

Python 3.12, FFmpeg con libx264/xfade/mov_text/AAC, ffprobe e font DejaVu Sans consigliati. Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu-core`.

```bash
git clone https://github.com/simoneperaddi-lab/ma-davvero-autopilot.git
cd ma-davvero-autopilot
git switch feat/zero-cost-instagram-autopilot
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -c requirements.lock
# Solo se .env non esiste già: non sovrascrivere configurazioni esistenti.
cp -n .env.example .env
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Apri la porta 8000 sul tuo computer; `/docs` espone le API. Esegui dalla radice del repository. L'esempio `.env` seleziona esplicitamente `MAD_AUTH_MODE=local`: permette accessi senza password **solo da loopback**. Senza questa opzione il default è Basic auth e l'avvio fallisce se manca una password di almeno 16 caratteri. Non usare la modalità locale dietro proxy o tunnel. Per smartphone/cloud usa la configurazione privata protetta in [docs/deployment.md](deployment.md).

## Flusso completo

1. **Genera curiosità** crea fino a tre esempi demo fissi (Venere, polpi, cervello). Nella stessa categoria si ripete l'esempio; il tema libero richiede OpenAI. I dati rimangono in `data/studio.sqlite3` dopo il riavvio.
2. Apri la scheda: titolo, hook, slide, caption, fonti suggerite e affermazioni da revisionare, inclusi titolo/hook/caption.
3. **Ricerca Crossref** consulta un registro pubblico gratuito: titolo, DOI, autori, anno, editore e abstract se disponibile. Collega un risultato alla bozza oppure una fonte suggerita. Non viene inventata una bibliografia di fallback se il registro non risponde.
4. **Recupera / ricontrolla testo** registra accesso alla pagina, testo estratto, data e SHA-256. Leggi il testo nella dashboard. Raggiungibilità, metadati e presenza di DOI **non equivalgono a verifica scientifica**.
5. Per ciascuna affermazione scegli **supportata**, **contraddetta** o **incerta**, con motivazione. Supportata/contraddetta richiedono una fonte recuperata negli ultimi 7 giorni e un passaggio di almeno 10 caratteri presente nel testo estratto. Il server verifica la corrispondenza testuale; **il revisore valuta significato, attendibilità e pertinenza**. Non c'è un classificatore automatico della verità.
6. Porta la bozza **in revisione**, quindi **approva** o **rifiuta** con motivazione. L'approvazione richiede tutte le affermazioni supportate da evidenze umane coerenti e recenti. Non basta una fonte generata da LLM o proveniente da Crossref. Per cambiare una bozza approvata/rifiutata devi riaprirla. La cronologia conserva autore, data UTC e dettagli.
7. Esporta carosello o Reel per revisione. Anche le bozze possono essere esportate: tutti i visual mantengono l'avviso di bozza. **Nessuno stato editoriale attiva una pubblicazione.**

Transizioni: `da_verificare → in_revisione → approvato/rifiutato`; da revisione, approvato o rifiutato si può tornare a `da_verificare`. Ogni modifica richiede la `revision` corrente; un aggiornamento concorrente risponde `409`. Fonti cambiate/non raggiungibili invalidano le verifiche collegate. L'approvazione è un atto editoriale alla data indicata, non un monitoraggio permanente della verità.

## Ricerca: rete e limiti

La ricerca usa `https://api.crossref.org/works`. I link arrivano dal registro DOI, non da un LLM: non garantiscono peer review o qualità. I metadati possono essere incompleti/errati e gli abstract possono mancare. Query inglesi sono spesso più efficaci.

Il recupero usa la allowlist fissa di `app/research.py`: Crossref, NASA Science, Smithsonian Ocean, doi.org, PNAS, PubMed/PMC, Nature, Science e PLOS (host esatti). Solo HTTPS, niente credenziali o porte alternative; ogni redirect viene rivalidato. Massimo 4 richieste, 12 secondi per richiesta e 500 KB decodificati per risposta; al massimo 100.000 caratteri conservati per fonte e 8 fonti per contenuto. Niente PDF, paywall o login dei publisher. Redirect fuori allowlist vengono bloccati, senza aggirare restrizioni del sito.

In cloud vanno consentiti i domini effettivamente utilizzati. Le prove iniziali live di Crossref e NASA hanno ricevuto `403` dalla rete; nella bozza delle impostazioni sono state salvate le aggiunte necessarie. I test offline non provano raggiungibilità nel deployment.

## Reel e caroselli

- Caroselli: ZIP con PNG RGB 1080×1350 per slide e `caption.txt` con fonti, stato e riepilogo delle verifiche.
- Reel statici compatibili con l'MVP o dinamici: MP4 H.264, yuv420p, 1080×1920, 24 fps, 4 secondi per slide. Il dinamico aggiunge zoom leggero e dissolvenze incrociate di 0,4 secondi.
- Sottotitoli italiani temporizzati: traccia MP4 `mov_text` e SRT scaricabile. Sono il testo delle slide, non una trascrizione vocale. Il lettore deve supportare/attivare la traccia; non sono impressi nel video.
- Audio opzionale **originale** sintetizzato localmente con onde sinusoidali, senza campioni o download esterni; AAC e dichiarazione CC0 scaricabile. Nessuna voce/TTS, servizio a pagamento o musica commerciale. Codice e dichiarazione in `app/video.py`.
- Se il filtro dinamico fallisce rapidamente, viene provato il fallback statico, dichiarato in `render_note` e nella dashboard. Timeout condiviso di 180 secondi, due thread di encoding e uno di filtri; una sola esportazione per processo.

Export, SRT e licenze richiedono autenticazione e il contenuto associato deve esistere. I file rimangono in `data/exports/` con versione e metadati: non c'è pulizia automatica. Gli export già creati rappresentano quella revisione e non vengono riscritti quando cambia lo stato editoriale.

## OpenAI e budget (opzionale, spento per default)

La demo non richiede chiavi. Per un uso futuro servono **tutti esplicitamente**: `MAD_PROVIDER=openai`, `OPENAI_API_KEY` lato server, `MAD_PAID_ENABLED=true`, limiti giornalieri di chiamate e costo, limite per chiamata e tariffe positive input/output per milione di token. Le variabili sono in `.env.example`, senza credenziali o valori che attivino pagamenti. Richiede `api.openai.com` oltre a Crossref. Solo `gpt-4.1-mini` è abilitato; altri modelli richiedono aggiornamento e verifica della policy.

Prima dell'API a pagamento vengono cercate fonti in Crossref. Senza risultati o con ricerca fallita non viene chiamato OpenAI. Il prompt include metadati disponibili; gli URL restituiti devono coincidere con il registro e i titoli vengono canonicalizzati. Output con URL/DOI nei campi narrativi vengono scartati. I testi rimangono bozze: il vincolo bibliografico non garantisce la correttezza scientifica delle affermazioni o di nomi/riferimenti testuali eventualmente generati.

L'SDK usa Structured Outputs, timeout 45 secondi e **zero retry automatici**. Prompt troppo grandi vengono rifiutati. Prima dell'invio si prenota atomicamente il costo conservativo di 20.000 token input e 6.000 output alle tariffe configurate. Numero di richieste e somma delle riserve non possono superare i limiti giornalieri UTC. Nessun rimborso delle riserve per timeout, rifiuti, parsing fallito o crash: il provider potrebbe avere già addebitato l'operazione. Quando disponibili vengono riportati separatamente i token reali.

`GET /api/usage` e dashboard mostrano chiamate, riserve, budget, token riportati e stati. È **contabilità applicativa conservativa, non una fattura OpenAI**: dipende da tariffe corrette e non copre altri client/account o variazioni di listino. Imposta anche i limiti nell'account provider prima di un uso reale. Nessuna chiamata pagata è stata effettuata durante sviluppo e test.

## Sicurezza

In cloud Basic auth protegge dashboard, asset, API, documentazione, file e report; compare il prompt del browser. Nessuna password in JavaScript/localStorage. Usa TLS e rete privata: [docs/deployment.md](deployment.md).

Limiti persistenti su finestre di minuto: API totali (default 120), generazione (6), export (4), ricerca/collegamento/controllo fonti (10), operazioni editoriali (30). Login falliti: 20/minuto per IP diretto, senza fidarsi di `X-Forwarded-For`. Un proxy può far condividere questo limite ai client: non è un WAF. Mutazioni solo JSON, corpo ≤32 KB e origine coerente; browser cross-site rifiutati. Risposte `no-store`, `nosniff`, frame vietati e CSP sulla dashboard. Nessuna interpretazione HTML dei testi generati.

Account editor unico, senza separazione autore/revisore, RBAC, MFA, sessioni revocabili o multi-tenant. L'audit è append-only **attraverso l'API**, non antimanomissione contro chi controlla database/filesystem.

## Supabase e compatibilità

SQLite è il default. Supabase REST richiede `MAD_STORAGE=supabase`, URL HTTPS e service role key backend. Applica manualmente `supabase/schema.sql` anche a progetti esistenti: la fase 2 aggiunge `UPDATE` al ruolo di servizio. RLS resta attiva senza policy pubbliche; non eseguiamo migrazioni sul tuo account. Le PATCH editoriali sono condizionate alla revisione corrente.

I payload MVP senza nuovi campi restano leggibili, con affermazioni a ID deterministici e revisione 0. Non cancelliamo o migriamo automaticamente dati originali. Cache di ricerca, rate limiting e budget rimangono nel database locale `data/controls.sqlite3` anche con Supabase. Export su disco locale. Supportata **una sola macchina e un solo worker** con disco persistente: niente repliche con ledger separati. Backup di tutta `data/`, non solo delle bozze. OpenAI e Supabase non verificati con credenziali live.

## Test

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

Una fixture automatica vieta connessioni reali: Crossref, publisher, OpenAI e Supabase usano mock, senza segreti o costi. SQLite, HTTP in-process e FFmpeg/ffprobe sono reali. Verifiche video: dimensioni/durata/codec, fotogrammi differenti, sottotitoli/audio e fallback. CI installa FFmpeg; senza FFmpeg/ffprobe i test video marcati vengono saltati. Sono mantenuti anche i test MVP.

Browser reale facoltativo, server demo attivo sulla porta 8000:

```bash
npm install --prefix /tmp/ma-browser playwright
NODE_PATH=/tmp/ma-browser/node_modules node /tmp/ma-browser/node_modules/playwright/cli.js install chromium
NODE_PATH=/tmp/ma-browser/node_modules node tests/browser_smoke.cjs
# Se Chromium è già nel sistema: CHROMIUM_PATH=/usr/bin/chromium.
```

Il test crea tre bozze nell'archivio corrente e verifica creazione, selezione, fonti, download, workflow e persistenza. Screenshot in `/tmp/ma-davvero-*.png`; usa un archivio demo di prova. Con Basic auth il test può ricevere `MAD_BROWSER_USERNAME` e `MAD_BROWSER_PASSWORD` come variabili d'ambiente, mai stampate.

## Struttura

```text
app/main.py, config.py, models.py    API, contratti, configurazione
app/generation.py, demo.py          provider e demo
app/research.py, editorial.py       fonti, evidenze, workflow
app/security.py, controls.py        accessi, limiti, budget
app/storage.py                     SQLite/Supabase con revisioni
app/media.py, video.py              caroselli, Reel, SRT, audio
app/static/                        dashboard mobile senza build JS
supabase/schema.sql                schema e permessi
tests/                             regressioni e fase 2
docs/deployment.md                  deployment privato
.github/workflows/tests.yml         CI
.env.example                       opzioni senza segreti
requirements.txt, requirements.lock dipendenze validate
```

Fuori scope: revisione sistematica della letteratura, fact-checking semantico automatico, PDF, editing del testo, immagini AI/TTS, calendario, analytics, pubblicazione dalla dashboard e architettura distribuita. Nessuno stato editoriale attiva effetti esterni.
