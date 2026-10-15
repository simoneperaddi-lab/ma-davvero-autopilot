# MA DAVVERO? — Content Studio

MVP per creare contenuti di divulgazione scientifica in italiano: FastAPI, dashboard responsive senza build JavaScript, generazione demo o OpenAI, archivio SQLite o Supabase, rendering Pillow e FFmpeg.

**Non pubblica su Instagram.** Nessun token Meta, scheduler o endpoint di pubblicazione. Ogni contenuto rimane una **bozza da verificare**: citare una fonte non certifica una notizia. Le esportazioni includono un avviso di revisione.

## Avvio rapido

Richiede Python 3.12, FFmpeg con encoder libx264 e, consigliato, font DejaVu Sans. Su Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu-core`.

```bash
git clone https://github.com/simoneperaddi-lab/ma-davvero-autopilot.git
cd ma-davvero-autopilot
# Per provare la PR prima del merge:
git switch feat/mvp-dashboard-content-studio
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -c requirements.lock
cp .env.example .env
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Apri `http://127.0.0.1:8000` sul tuo computer. La documentazione interattiva delle API è in `/docs`. Esegui i comandi dalla radice del repository. La demo non richiede API key, servizi esterni o migrazioni: crea `data/studio.sqlite3` al primo avvio e conserva le bozze dopo il riavvio.

### Provare il flusso completo

1. Nella dashboard premi **Genera curiosità**. La demo contiene tre esempi fissi: Venere, polpi e cervello. La categoria filtra l'esempio; richieste multiple nella stessa categoria ripetono quell'esempio. Il tema libero è disponibile solo con OpenAI.
2. Seleziona una scheda per leggere hook, sceneggiatura, caption, fonti e note di verifica.
3. Esporta **Carosello PNG**: ZIP con una PNG 1080 × 1350 per slide e `caption.txt` con fonti e avvisi.
4. Esporta **Reel verticale**: MP4 H.264 1080 × 1920, 24 fps, 4 secondi per slide. È un montaggio statico senza audio, voce o musica: 5 slide producono 20 secondi. Scarica separatamente **Caption e fonti**.
5. Ricarica la pagina: le bozze devono essere ancora presenti. Controlla le fonti manualmente prima di qualsiasi condivisione.

L'esportazione è sincrona con un solo render alla volta per processo, timeout FFmpeg di 180 secondi e due thread di encoding. Il pulsante segnala l'attesa; il download appare al termine. File e metadati degli export rimangono in `data/exports/`, esclusa da Git. Non è prevista pulizia automatica: sorveglia lo spazio disco. Non avviare più worker per questa versione.

## OpenAI (opzionale)

Imposta nella tua `.env` o nelle variabili d'ambiente, senza committare credenziali:

```dotenv
MAD_PROVIDER=openai
OPENAI_API_KEY=
MAD_OPENAI_MODEL=gpt-4.1-mini
```

Inserisci la chiave esclusivamente nella configurazione sicura dell'ambiente. Il backend usa la Responses API con output strutturato e validazione Pydantic. Richiede accesso HTTPS a `api.openai.com`, un account con credito e un modello compatibile con Structured Outputs. Il tema viene inviato a OpenAI e può generare costi. Riavvia dopo aver cambiato configurazione.

Non viene eseguita ricerca web o verifica automatica delle fonti: anche gli URL e le affermazioni prodotti da OpenAI devono essere controllati. Se mancano credenziali o l'API fallisce, viene restituito un errore esplicito, senza sostituire di nascosto l'output con dati demo.

## Supabase (opzionale)

1. Crea un progetto Supabase e applica manualmente `supabase/schema.sql` nell'editor SQL.
2. Imposta `MAD_STORAGE=supabase`, `SUPABASE_URL=https://<progetto>.supabase.co` e `SUPABASE_SERVICE_ROLE_KEY` nell'ambiente backend.
3. Consenti HTTPS verso il dominio del progetto e riavvia il server.

L'adapter usa le API REST Supabase; RLS è attiva e non ci sono policy pubbliche. Solo il backend usa la service role key, mai il browser. Le bozze SQLite esistenti **non** vengono migrate automaticamente. Gli export rimangono su disco locale anche con Supabase; il bucket Storage non è ancora implementato. La chiave deve essere disponibile al backend attraverso la configurazione supportata dall'ambiente; non è necessario per la demo.

## Test

```bash
.venv/bin/python -m pytest -q
```

La suite verifica API, validazione, persistenza dopo riapertura, caption, file PNG/ZIP, MP4 reale con ffprobe, errori di encoding, concorrenza ed adapter esterni con risposte simulate. Il test MP4 viene saltato solo se FFmpeg o ffprobe non sono installati; installali per la verifica completa. Nessun test chiama API a pagamento. La CI GitHub Actions installa anche FFmpeg ed esegue la suite.

Test facoltativo del browser reale (server demo già avviato sulla porta 8000):

```bash
npm install --prefix /tmp/ma-browser playwright
# Se Chromium non è già installato, installare il browser tramite Playwright:
NODE_PATH=/tmp/ma-browser/node_modules node /tmp/ma-browser/node_modules/playwright/cli.js install chromium
NODE_PATH=/tmp/ma-browser/node_modules node tests/browser_smoke.cjs
# Per usare Chromium di sistema, aggiungere CHROMIUM_PATH=/usr/bin/chromium.
```

Il test browser crea tre bozze demo nell'archivio corrente e verifica generazione, selezione, download ZIP, persistenza e layout a 320, 390 e 1440 pixel. Salva screenshot in `/tmp/ma-davvero-*.png`. Usa un archivio demo di prova se vuoi conservare intatta la tua libreria. `requirements.lock` conserva le versioni Python transitive effettivamente validate su Python 3.12.

Smoke test API con server in esecuzione:

```bash
curl --fail http://127.0.0.1:8000/api/health
curl --fail -X POST http://127.0.0.1:8000/api/generate \
  -H 'Content-Type: application/json' -d '{"category":"spazio","count":1}'
curl --fail http://127.0.0.1:8000/api/contents
```

## Struttura

```text
app/
  main.py              # FastAPI, dashboard, API e download
  config.py            # Configurazione .env / ambiente
  models.py            # Contratti e validazione
  generation.py        # Provider demo e OpenAI
  demo.py              # Esempi scientifici con fonti suggerite
  storage.py           # SQLite / Supabase REST
  media.py             # Caroselli PNG e Reel FFmpeg
  static/              # Dashboard HTML, CSS e JavaScript
supabase/schema.sql    # Schema e RLS
tests/                 # Suite automatica
.github/workflows/     # CI
.env.example
requirements.txt
```

## Limiti del prototipo

Questa versione è per **sviluppo locale o ambiente privato con un solo utente**. Non include login, autorizzazioni, quote, limitazione delle richieste o isolamento tra utenti: non esporla direttamente su Internet, soprattutto con chiavi API configurate. Per accedere da smartphone usa un accesso privato protetto alla macchina che esegue il server; il layout si adatta allo schermo, ma l'MVP non configura hosting o autenticazione. In cloud usa solo gli strumenti di accesso privato forniti dalla piattaforma.

Non sono implementati: raccolta automatica di fonti, fact-checking, approvazione editoriale, editing delle bozze, immagini AI, TTS, montaggio animato, calendario, analytics e pubblicazione Instagram. I dati demo non sono presentati come verificati. OpenAI e Supabase richiedono una verifica live con le credenziali dell'utente; i test automatici verificano i loro contratti con mock.
