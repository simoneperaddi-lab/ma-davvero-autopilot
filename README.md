# MA DAVVERO? — autopilota Instagram gratuito

Un processo GitHub Actions prepara ogni giorno un Reel originale in italiano da un **catalogo documentario con fonti e materiali NASA tracciati**, lo carica direttamente tramite le **API ufficiali Instagram con Instagram Login** e conserva fonti e stato per evitare ripetizioni. **La pubblicazione è disattivata finché il proprietario non la abilita esplicitamente.** Non servono OpenAI, Supabase, hosting, immagini acquistate o musica commerciale.

**Parti da [Android: configurazione e attivazione](docs/ANDROID.md).** La PR unica integra MVP, fase 2 e issue #4. Dashboard mobile, caroselli, workflow editoriale e protezioni precedenti restano disponibili come [studio facoltativo](docs/STUDIO.md); non devono rimanere accesi per il ciclo automatico.

## Cosa fa

1. Seleziona una storia non utilizzata: pioggia solare, anelli di Saturno o Luna rossa.
2. Recupera le fonti istituzionali e conferma passaggi scientifici, crediti e condizioni d'uso. Se qualcosa cambia o non è disponibile, salta la storia.
3. Verifica l'hash e la risoluzione del materiale selezionato; conserva provenienza e copie testuali delle fonti. Nessuna citazione generata da LLM.
4. Monta immagini autentiche e illustrazioni animate originali, sempre distinte a schermo, con dettagli ravvicinati, movimenti e dissolvenze.
5. Esporta 1080×1920 nativo, H.264, 24 fps, 24 secondi, AAC stereo, musica originale e SRT. Controlla decodifica, movimento, audio e testi. Nessuna voce narrante nel mix.
6. Registra l'intenzione **prima** di `media_publish`; carica il file direttamente su `rupload.facebook.com`, attende l'elaborazione e pubblica al massimo una volta per giorno italiano. Nessun sito pubblico per ospitare MP4.
7. Rinnova il token ogni sette giorni nel secret store GitHub. Conserva il registro nel branch `autopilot-state`; produce un riepilogo settimanale in Actions, domenica alle 18:43 UTC.

**Limite scientifico deliberato:** tre storie selezionate editorialmente, non un fact-checker universale. Dopo averle utilizzate, il sistema salta i post: non inventa nuovi temi né ripete quelli pubblicati. Il precedente accesso al NASA Exoplanet Archive rimane disponibile per compatibilità. [Materiali, controlli, costi e limiti visivi](docs/cinematic-reels.md).

## Prova completa, senza account o rete

Python 3.12, FFmpeg/ffprobe, font DejaVu Sans. Su Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu-core`.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -c requirements.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m autopilot --mode simulate
```

In `data/autopilot/`: `reel.mp4`, `caption.txt`, `subtitles.srt`, `audio-license.txt`, `evidence.json`, `report.md`, registro simulato. La simulazione usa **dati sintetici esplicitamente marcati**, non una falsa fonte scientifica, e chiama due volte la pipeline per verificare che non replichi il post. Non usa segreti né connessioni. Per una simulazione nuova usa `--output data/nuova-simulazione`.

Per controllare NASA e generare un Reel reale **senza pubblicare né usare credenziali**:

```bash
.venv/bin/python -m autopilot --mode verify --output data/verifica-nasa
# Tutti e tre i film e una pagina locale di visione:
.venv/bin/python -m autopilot.showcase --output data/cinema-showcase
```

`preflight` aggiunge la verifica dell'identità Instagram, ma non crea container, non carica e non pubblica. `publish` richiede sia l'opzione esplicita sia `MAD_PUBLISH_ENABLED=true`, ref `refs/heads/main`, segreti e ID dell'account. Non legge credenziali da `.env`. Il workflow espone i segreti soltanto ai passaggi che ne hanno bisogno; non esegue il publisher su pull request.

Il nuovo renderer produce anche `contact-sheet.jpg` e otto frame estratti dal MP4, per verificare il risultato effettivamente codificato. [Montaggio documentario e verifica visiva](docs/cinematic-reels.md).

## Affidabilità, sicurezza e manutenzione

- Un solo workflow alla volta, senza cancellazione di quello precedente. Stato persistente con controllo SHA: una scrittura concorrente o fallita blocca l'operazione.
- GET: massimo tre tentativi con ritardo limitato. POST e scritture: nessun replay automatico di richieste dall'esito incerto. Elaborazione video: massimo 20 controlli distanziati di 15 secondi, oltre ai tempi HTTP; timeout del job di 20 minuti.
- Se la risposta a `media_publish` si perde, il successivo ciclo controlla il container. `PUBLISHED` chiude l'operazione; ogni altro esito resta bloccato, senza rischiare un secondo post. In questo raro caso serve riconciliazione manuale: [procedura](docs/ANDROID.md#se-un-run-fallisce).
- Errori di fonte/rete/token/permessi fermano il ciclo. Dati insufficienti producono un salto registrato. Nessuna sostituzione con citazioni inventate.
- Un token scaduto o revocato non si può rinnovare magicamente: il sistema si ferma e segnala errore. Il rinnovo richiede il PAT GitHub limitato ai Secrets; anche quel PAT ha una scadenza da mantenere. Non salvare token nei file, negli artifact o nel ledger.
- I log applicativi non stampano risposte remote, URL con token o traceback potenzialmente sensibili. Il registro è pubblico in questo repository pubblico: contiene solo contenuti, evidenze, identificativi e date.
- Non cancellare/reset/rebase il branch `autopilot-state`: perdere la memoria può consentire ripetizioni. Amministratori del repository restano autorità fidate. Il registro non è antimanomissione contro l'owner.
- Actions non è un servizio 24/7: cron può ritardare o saltare. Per repository pubblici GitHub può disabilitare schedule dopo 60 giorni senza attività; controllare eventuali avvisi. Nessun recupero di più post arretrati in una giornata.
- Abilitare le notifiche dei workflow falliti su GitHub. Il riepilogo settimanale è nel tab Actions, **non una email o un messaggio WhatsApp automatico**. Se il cron stesso non parte, non può inviare un allarme: non è incluso un monitor esterno indipendente.

## Costo

**Configurazione proposta: €0/mese di servizi**, finché il repository resta pubblico e si usano runner standard GitHub gratuiti e le condizioni gratuite correnti dei servizi. NASA e le chiamate Instagram non richiedono API a pagamento; FFmpeg/Pillow e l'audio locale non hanno canoni. Non viene attivato alcun piano o budget a pagamento.

Il rendering richiede decine di secondi più installazione/coda; stimare 2–5 minuti per esecuzione (~60–150 minuti/mese, oltre CI e report), non un SLA. Artifact trattenuti un giorno, cache riutilizzata, nessun archivio di video permanente su Git. Un repository privato dipenderebbe dalle quote del proprio piano (GitHub Free normalmente 2.000 minuti/mese e 500 MB artifact): non assumere gratuità illimitata. Mantenere gli eventuali budget a consumo a zero; non selezionare larger runners. Restano il costo della connessione e il tempo personale per account, autorizzazioni e manutenzione occasionale.

## Codice e verifiche

| Percorso | Funzione |
|---|---|
| `autopilot/science.py` | Recupero e controlli delle misure NASA, derivazione dei testi |
| `autopilot/pipeline.py` | Stato durevole, deduplicazione, rinnovo e riepiloghi |
| `autopilot/instagram.py` | API ufficiale, upload diretto, polling e pubblicazione |
| `autopilot/state.py` | Registro GitHub e aggiornamento cifrato dei Secrets |
| `autopilot/cinema.py`, `cinema_render.py`, `documentaries.py` | Montaggio documentario, musica originale, fonti, diritti e controlli |
| `autopilot/render.py`, `orbital.py`, `soundtrack.py` | Dispatch e compatibilità con fatti esopianetari/fixture precedenti |
| `.github/workflows/autopilot.yml` | Cron e comandi manuali con opt-in esplicito |
| `tests/test_autopilot.py` | Contratti HTTP simulati, fault injection e E2E con FFmpeg reale |
| `.github/workflows/tests.yml` | Regressioni offline e verifica pubblica separata NASA |

Tutti i test pytest vietano rete e DNS e non richiedono credenziali. La verifica NASA in CI è separata e di sola lettura: dipende dalla disponibilità del servizio pubblico. I mock verificano il nostro contratto, **non dimostrano che Meta abbia concesso le autorizzazioni al tuo account**. Risultati e limiti in [docs/validation.md](docs/validation.md).

Riferimenti operativi: [NASA TAP](https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html), [colonne Planetary Systems](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html), [attribuzione NASA Archive](https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html), [Meta: content publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/), [Meta: Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/), [GitHub Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions), [scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
