# Deployment privato su una macchina

Configurazione di riferimento, non un deployment eseguito. Nessun servizio a pagamento necessario.

1. Predisponi Python 3.12, FFmpeg, ffprobe, un utente di sistema dedicato e una directory dati persistente scrivibile solo da quell'utente. Installa con `python -m pip install -r requirements.txt -c requirements.lock` in una venv.
2. Conserva la configurazione in un file protetto (0600) o nel secret store della tua infrastruttura. Non committarlo né stamparlo. Imposta:

   ```dotenv
   MAD_AUTH_MODE=basic
   MAD_AUTH_USERNAME=editor
   MAD_AUTH_PASSWORD=
   MAD_PUBLIC_ORIGIN=https://studio.tuo-dominio-interno.example
   MAD_PROVIDER=demo
   MAD_STORAGE=sqlite
   MAD_DATA_DIR=/percorso/persistente/ma-davvero
   MAD_PAID_ENABLED=false
   ```

   Inserisci una password casuale lunga (almeno 16 caratteri) tramite la configurazione sicura. Vuota impedisce l'avvio: non esiste password di default. Non usare `MAD_AUTH_MODE=local` dietro proxy, tunnel o accessi cloud.
3. Avvia dalla radice: `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers`. Usa un process manager che carichi la configurazione e riavvii il servizio. Non mettere password negli argomenti del processo. Un `.env` nella radice viene letto da pydantic-settings.
4. Esponi solo tramite rete privata e reverse proxy HTTPS con certificato verificabile dai client. Instrada il dominio a `127.0.0.1:8000`, inoltra `Authorization`, conserva `Host` e configura timeout ≥190 secondi per rendering. `MAD_PUBLIC_ORIGIN` deve coincidere con l'origine HTTPS esterna per il controllo CSRF. Non disabilitare TLS e non aprire direttamente 8000 su Internet. In cloud usa gli accessi privati della piattaforma, senza installare VPN nel container.
5. Verifica `401` senza credenziali su dashboard, API, documentazione e download; con credenziali valide prova il flusso demo. Controlla il rifiuto dei POST da origine diversa. Da smartphone entra nella stessa rete privata e usa l'origine HTTPS protetta.
6. Fai backup consistenti di tutta `MAD_DATA_DIR` (bozze, ledger, cache ed export), a servizio fermo o con strumenti di backup SQLite. Non eliminare il ledger per aggirare limiti. Un backup vecchio ripristina anche contatori vecchi: sospendi chiamate a pagamento fino a riconciliazione. Monitora spazio, CPU e login falliti. Non eseguire repliche o più worker.

Egress necessario: `api.crossref.org` e i singoli host consentiti da `app/research.py`; redirect fuori allowlist restano bloccati. Crossref non richiede chiavi. OpenAI e Supabase sono opzionali e non vengono attivati qui. Abilitare OpenAI in futuro richiede tariffe aggiornate e limiti sia applicativi sia nell'account provider.

Basic auth è per il prototipo privato a editor unico. Prima di un'esposizione pubblica o di più utenti indipendenti servono identità individuali, ruoli, MFA/SSO, logging centralizzato, protezioni al proxy e ledger/coda condivisi. L'audit applicativo non è un archivio antimanomissione.
