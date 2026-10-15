# Verifica della fase 2

Riferimento: issue #2; branch `feat/phase2-editorial-studio` derivato da `feat/mvp-dashboard-content-studio` (`540a346`). Nessun merge e nessuna pubblicazione Instagram.

## Risultati locali

- Baseline MVP: **20 test passati**, nessuno saltato.
- Suite finale `python -m pytest -q`: **67 test passati**, nessuno saltato, in circa 31 secondi. Un warning di deprecazione proviene da Starlette TestClient/AnyIO, non da un fallimento applicativo.
- Test offline obbligatori: socket e DNS bloccati dalla fixture; OpenAI, Crossref/publisher e Supabase simulati. Nessuna credenziale reale o operazione pagata.
- FFmpeg e ffprobe reali: Reel statico e dinamico H.264 1080×1920, 24 fps, durata 20 secondi per 5 slide. Il test dinamico confronta due frame diversi e verifica tracce AAC e mov_text, SRT e dichiarazione CC0. Fallback statico verificato provocando un errore del filtro dinamico.
- Persistenza SQLite, payload legacy MVP, compare-and-swap SQLite/Supabase, conflitti concorrenti, quote inventate, fonti scadute/cambiate, transizioni vietate e audit verificati.
- Autenticazione su dashboard/API/asset/docs/export, blocchi CSRF/body, rate limit persistente, prenotazioni concorrenti del budget, costi massimi e assenza di retry verificati.
- Browser Chromium/Playwright: flusso MVP, ZIP scaricabile, collegamento fonte, revisione, approvazione prematura rifiutata, esito umano incerto, rifiuto editoriale e cronologia. Persistenza dopo reload, nessun errore JavaScript o overflow a 320/390/1440 px.
- Server Uvicorn reale con password **sintetica temporanea**: anonimi `401`, dashboard e API autorizzate `200`, demo generata `201`, zero chiamate OpenAI. Il server del test è stato terminato.
- `pip check` e `git diff --check` superati. OpenAPI versione 0.2.0, nessun endpoint di pubblicazione.

## Limiti della verifica

I tentativi live di Crossref e NASA hanno ricevuto HTTP 403 nell'ambiente iniziale. Non è dimostrata la raggiungibilità live delle fonti: i domini necessari sono salvati nella bozza di configurazione e vanno applicati nelle impostazioni. L'implementazione gestisce questi errori senza inventare risultati o verifiche.

OpenAI e Supabase sono validati con mock, non con account live. Non sono stati attivati servizi, aggiunte chiavi reali, eseguite migrazioni remote o configurati Instagram/TLS pubblico. Le verifiche umane registrano decisioni del revisore e corrispondenza delle citazioni, non certificano automaticamente la verità scientifica. La protezione cloud richiede una configurazione privata HTTPS appropriata, come descritto in deployment.md.

I risultati della CI GitHub sono separati da quelli locali e vanno letti nei check della PR.
