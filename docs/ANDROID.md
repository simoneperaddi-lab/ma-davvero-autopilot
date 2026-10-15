# Android: dalla PR alla pubblicazione

Questa guida si legge in meno di 10 minuti. **Non è realistico garantire la creazione/verifica dell'account sviluppatore e le eventuali approvazioni Meta in 10 minuti.** Con account e token già disponibili, inserire le impostazioni GitHub richiede pochi minuti. I nomi delle voci Meta possono variare per lingua/account.

Nessun passaggio richiede computer, server, carta di credito o chiavi OpenAI. Usa Chrome Android, menu ⋮ → **Sito desktop** per Meta e GitHub; l'app GitHub non espone tutte le impostazioni. Non incollare token in chat, issue, repository, schermate condivise o input dei workflow.

## 1. Account Instagram e Meta — operazioni personali

1. Nell'app Instagram apri il profilo MA DAVVERO? → ☰ → **Impostazioni e attività** → **Tipo di account e strumenti** → **Passa a un account professionale**, Creator o Business. Il profilo deve essere pubblico e in regola con le policy.
2. In Chrome apri [Meta for Developers](https://developers.facebook.com/apps/), accedi con il tuo account e completa l'eventuale registrazione/verifica sviluppatore. Crea un'app per gestire il tuo Instagram professionale, aggiungendo il prodotto/use case **Instagram**. Non selezionare API pubblicitarie o servizi a pagamento.
3. Apri **Instagram → API setup with Instagram login** (configurazione API con accesso Instagram). Questo progetto usa **Instagram Login**, non il vecchio Basic Display e non il flusso Facebook Login. Non serve aggiungere una Pagina Facebook soltanto per questo flusso.
4. Aggiungi il tuo account professionale. Se Meta richiede un tester/ruolo, aggiungilo nell'app e accetta l'invito dal tuo Instagram; la sezione può essere in **Autorizzazioni del sito web → App e siti web → Inviti tester**, anche da [Instagram web](https://www.instagram.com/accounts/manage_access/).
5. Autorizza **`instagram_business_basic`** e **`instagram_business_content_publish`**. Genera dal pannello un **token Instagram long-lived**, normalmente valido 60 giorni, e annota il relativo **Instagram user ID**. Usa un token appena generato. Un token di un'ora non basta. Se il pannello offre soltanto un token breve, seguire lo scambio long-lived della [documentazione Meta](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/); non inserire un token breve fingendo che sia permanente.
6. Per account propri aggiunti con ruolo/tester può essere disponibile Standard Access. Se Meta richiede Advanced Access, App Review, verifica business, privacy policy o altri requisiti, completarli nel pannello: il codice non li aggira. Non dichiarare l'app pronta finché i permessi del tuo account non sono concessi. Non pagare servizi terzi per “sbloccare” il token.

Il sistema può rinnovare un token long-lived valido, non ricreare il consenso revocato. Prima del primo post resta da verificare il contratto sul tuo account: identità, permessi di pubblicazione e supporto upload diretto. I test senza account non possono confermarli.

## 2. GitHub — segreti e variabili

Apri [il repository](https://github.com/simoneperaddi-lab/ma-davvero-autopilot) → **Settings → Secrets and variables → Actions**.

Nella scheda **Secrets**, crea:

| Nome | Valore personale |
|---|---|
| `IG_ACCESS_TOKEN` | Token Instagram long-lived appena generato |
| `GH_SECRET_UPDATER` | Fine-grained PAT GitHub descritto qui sotto |

Nella scheda **Variables**, crea:

| Nome | Valore |
|---|---|
| `IG_USER_ID` | ID numerico dell'account associato al token |
| `MAD_PUBLISH_ENABLED` | **`false`**, fino all'attivazione esplicita |
| `IG_API_VERSION` | `v24.0` (default del codice; modificare solo dopo verifica del contratto) |

Per `GH_SECRET_UPDATER`: GitHub → avatar → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Resource owner: `simoneperaddi-lab`; **Only select repositories**: soltanto `ma-davvero-autopilot`. Repository permissions: **Secrets → Read and write** (Metadata read è automatico). Niente accesso ad altri repository, codice, amministrazione o organizzazione. Scegli una scadenza esplicita, ad esempio un anno se consentito, e annotala nel calendario. Se l'organizzazione richiede approvazione, attendila. Incolla il valore direttamente nel Secret `GH_SECRET_UPDATER`.

Perché serve: il `GITHUB_TOKEN` automatico del workflow può scrivere il registro, ma non modificare i Secrets. Questo PAT salva il token Instagram rinnovato, cifrato con la chiave pubblica GitHub. Il rinnovo è settimanale; il valore non entra mai nel ledger o negli artifact. Il PAT va sostituito prima della sua scadenza; la manutenzione non è quotidiana ma non è zero per sempre.

Non devi creare manualmente `GITHUB_TOKEN`, database, Supabase, hosting o storage. Il branch del registro verrà creato dal workflow alla prima esecuzione che ne ha bisogno. Non cancellarlo.

## 3. Integra e prova senza pubblicare

1. Apri la PR unica, leggi i risultati e integra in `main` **solo quando decidi tu**. L'assistente non esegue il merge. Il cron e il pulsante del nuovo workflow diventano operativi sul branch predefinito dopo il merge.
2. Repository → **Actions → MA DAVVERO autopilot → Run workflow** → branch `main`, mode **`simulate`**. Attendi il verde. Apri il run e scarica l'artifact: contiene un MP4 marcato simulazione e il riepilogo; scade dopo un giorno.
3. Esegui **`verify`**: controlla NASA e genera il primo Reel con fonte reale, senza credenziali Instagram.
4. Esegui **`preflight`** dopo avere aggiunto i segreti: controlla l'identità del token più la fonte e il rendering. **Non crea container, non carica e non pubblica.** Non verifica ancora il permesso effettivo di pubblicazione: questo potrà essere provato solo con l'attivazione autorizzata.
5. In GitHub **Settings → Notifications → System → Actions**, abilita notifiche/email per workflow falliti secondo le opzioni del tuo account. Controlla anche spam e preferenze del repository. Il report settimanale è nella pagina del relativo run Actions, non viene inviato su WhatsApp.

Se la policy del repository blocca le scritture del workflow (403 sul ledger), controlla **Settings → Actions → General → Workflow permissions** e consenti le scritture necessarie. Non servono permessi per creare o approvare PR.

## 4. Attivazione esplicita — questo può pubblicare davvero

**Fallo solo quando autorizzi una pubblicazione reale sul profilo.** Cambia la variabile `MAD_PUBLISH_ENABLED` da `false` a **`true`**. Da quel momento il prossimo cron potrà pubblicare; non esiste una conferma giornaliera.

Per il primo post puoi usare subito **Actions → MA DAVVERO autopilot → Run workflow → `publish`**, su `main`. È una pubblicazione reale, non una prova. Il ciclo schedulato parte alle **10:23 UTC** (11:23 in Italia con ora solare, 12:23 con ora legale), con possibili ritardi GitHub. Se hai già pubblicato quel giorno attraverso il sistema, il cron non ripete il post. Un post pubblicato manualmente fuori dal sistema non viene importato nel registro.

Stop: rimetti **`MAD_PUBLISH_ENABLED=false`**. Il ciclo già avviato va anche cancellato da Actions, se non ha ancora pubblicato; nessun toggle può annullare una chiamata già completata. La disattivazione sospende anche il rinnovo: dopo circa 60 giorni può servire un nuovo token prima del riavvio. Non cancellare il registro per “ripartire”.

## Se un run fallisce

- **Fonte non disponibile o dati insufficienti:** nessun post inventato. Leggi `report.md`; `skipped` significa salto intenzionale. Il ciclo successivo riprova la ricerca. Un errore di rete/servizio fallisce il workflow e deve attivare le notifiche GitHub.
- **401/403 o token scaduto/revocato:** genera nuovamente il token long-lived, aggiorna `IG_ACCESS_TOKEN`; verifica ID, permessi, scadenza del PAT e `preflight`. La sostituzione deve restare per lo stesso account: il ledger rifiuta cambi silenziosi di identità.
- **Rinnovo fallito:** controlla permesso Secrets/scadenza del PAT. Se il token Instagram è già invalido, rigeneralo: nessun codice può rinnovare un token revocato o scaduto.
- **Operazione `publishing` pendente:** il sistema non ripete il POST. Il ciclo successivo controlla il container: se `PUBLISHED`, riconcilia automaticamente. Se resta ambiguo, disattiva l'autopilota e controlla Instagram. **Non cancellare l'entry, non cambiare lo stato in `prepared`, non rieseguire alla cieca.** Un responsabile tecnico deve confrontare container, post effettivo e registro; solo dopo può registrare `published` con data reale oppure `abandoned` se la mancata pubblicazione è certa. In questo caso raro l'intervento umano è necessario per privilegiare l'assenza di duplicati.
- **GitHub non avvia i cron:** verifica workflow abilitato, branch `main`, variabile, disponibilità Actions ed eventuale disabilitazione per inattività. Non c'è un monitor esterno a pagamento.

## Costi e dati pubblici

Con questo repository **pubblico**, runner standard e le attuali condizioni gratuite, i servizi previsti costano **€0/mese**. Non vengono attivati abbonamenti o API pagate. Mantieni a zero eventuali budget a consumo; evita larger runners e non rendere privato il repository assumendo quote illimitate. I file Reel restano negli artifact per un giorno; il registro pubblico conserva caption, misure, fonti, ID dei post e date, mai token. Il costo reale residuo è la tua connessione e la manutenzione occasionale di account/token/permessi/policy.
