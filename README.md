# MA DAVVERO? — autopilota Instagram gratuito

Un processo GitHub Actions prepara ogni giorno un Reel originale in italiano da una misura del **NASA Exoplanet Archive**, lo carica direttamente tramite le **API ufficiali Instagram con Instagram Login** e conserva fonti e stato per evitare ripetizioni. **La pubblicazione è disattivata finché il proprietario non la abilita esplicitamente.** Non servono OpenAI, Supabase, hosting, immagini acquistate o musica commerciale.

**Parti da [Android: configurazione e attivazione](docs/ANDROID.md).** La PR unica integra MVP, fase 2 e issue #4. Dashboard mobile, caroselli, workflow editoriale e protezioni precedenti restano disponibili come [studio facoltativo](docs/STUDIO.md); non devono rimanere accesi per il ciclo automatico.

## Cosa fa

1. Consulta la tabella scientifica `ps` di NASA, cercando esopianeti confermati con un anno inferiore a un giorno terrestre.
2. Esclude record controversi, limiti superiori/inferiori, misure senza incertezze o riferimento bibliografico e soggetti già utilizzati. Richiede errori relativi inferiori al 10% e l'intero intervallo selezionato sotto un giorno.
3. Recupera nuovamente il record per nome e confronta i valori. Salva riga originale, URL della query riproducibile, riferimento fornito dal catalogo, data e SHA-256. Nessun DOI inventato, nessun fallback a una risposta LLM.
4. Deriva matematicamente le ore da giorni × 24; produce cinque scene, didascalia e fonti. Testi e grafiche originali; nessuna riproduzione di articoli, fotografie o loghi NASA.
5. Renderizza con Pillow/FFmpeg: MP4 verticale 1080×1920, H.264, 24 fps, 20 secondi, zoom e dissolvenze, testi impressi, SRT separato, musica sintetizzata localmente AAC 48 kHz. L'audio si può togliere con `--no-audio`. Non c'è una voce narrante. Il video per Instagram non dipende da tracce sottotitoli che la piattaforma potrebbe eliminare.
6. Registra l'intenzione **prima** di `media_publish`; carica il file direttamente su `rupload.facebook.com`, attende l'elaborazione e pubblica al massimo una volta per giorno italiano. Nessun sito pubblico per ospitare MP4.
7. Rinnova il token ogni sette giorni nel secret store GitHub. Conserva il registro nel branch `autopilot-state`; produce un riepilogo settimanale in Actions, domenica alle 18:43 UTC.

**Limite scientifico deliberato:** verifica di una misura rispetto a un catalogo scientifico autorevole, non replica dello studio né fact-checking universale. Il secondo recupero controlla coerenza, non costituisce una seconda fonte indipendente. Non vengono letti o dichiarati verificati i full text degli studi collegati. Il tema è inizialmente solo astronomico e il formato ripetibile; il sistema non inventa una nuova scoperta quotidiana. Esauriti i soggetti idonei, salta i post fino a nuovi dati. Non garantisce copertura di biologia, salute o notizie scientifiche.

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
```

`preflight` aggiunge la verifica dell'identità Instagram, ma non crea container, non carica e non pubblica. `publish` richiede sia l'opzione esplicita sia `MAD_PUBLISH_ENABLED=true`, ref `refs/heads/main`, segreti e ID dell'account. Non legge credenziali da `.env`. Il workflow espone i segreti soltanto ai passaggi che ne hanno bisogno; non esegue il publisher su pull request.

## Affidabilità, sicurezza e manutenzione

- Un solo workflow alla volta, senza cancellazione di quello precedente. Stato persistente con controllo SHA: una scrittura concorrente o fallita blocca l'operazione.
- GET: massimo tre tentativi con ritardo limitato. POST e scritture: nessun replay automatico di richieste dall'esito incerto. Elaborazione video: massimo cinque minuti di polling per ciclo.
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
| `autopilot/render.py` | Riutilizzo del renderer originale del content studio |
| `.github/workflows/autopilot.yml` | Cron e comandi manuali con opt-in esplicito |
| `tests/test_autopilot.py` | Contratti HTTP simulati, fault injection e E2E con FFmpeg reale |
| `.github/workflows/tests.yml` | Regressioni offline e verifica pubblica separata NASA |

Tutti i test pytest vietano rete e DNS e non richiedono credenziali. La verifica NASA in CI è separata e di sola lettura: dipende dalla disponibilità del servizio pubblico. I mock verificano il nostro contratto, **non dimostrano che Meta abbia concesso le autorizzazioni al tuo account**. Risultati e limiti in [docs/validation.md](docs/validation.md).

Riferimenti operativi: [NASA TAP](https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html), [colonne Planetary Systems](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html), [attribuzione NASA Archive](https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html), [Meta: content publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/), [Meta: Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/), [GitHub Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions), [scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
