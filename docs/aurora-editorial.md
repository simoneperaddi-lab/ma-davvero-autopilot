# Aurora — taglio finale, 15 secondi

`python -m autopilot.aurora_editorial --output data/aurora-editorial`

Il comando esistente produce un solo Reel. Nessuna nuova architettura, servizio,
chiave o API. Nessun cambiamento a Instagram, token, registro o pubblicazione.

## Montaggio

| Nel Reel | Fonte e intervallo originale | Testo |
|---|---|---|
| 0–4 s | NASA 232648, 0–4 s | NON È UN’ANIMAZIONE. |
| 4–8 s | NASA 849432, 4–8 s | LA TERRA. VISTA DALLA ISS. |
| 8–11 s | NASA 819232, 12–15 s | IL SOLE ACCENDE IL CIELO. |
| 11–15 s | NASA 232648, 8–12 s | LA CHIAMIAMO AURORA. |

Primo fotogramma: aurora verde e rossa, orizzonte terrestre, nessun logo o testo.
Ogni frase arriva 0,35 s dopo il taglio. Quattro cartigli complessivi, sotto la
ripresa, senza coprire il fenomeno. Nessuna schermata introduttiva, transizione,
loop, rallentamento o interpolazione. Il Sole mantiene l'etichetta UV/falsi colori
sotto il disco. I due estratti della ripresa panoramica non si sovrappongono.

Rispetto alla versione precedente sono stati rimossi selezione euristica
dell'apertura, testi didattici, logo e scrim sovrapposti. Il piano è fisso e
revisionato per questa consegna; i controlli esistenti di provenienza, intervalli,
decodifica e audio rimangono. Non si aggiunge un nuovo template generico.

## Immagine e limiti

Output 1080×1920, 24 fps, H.264; AAC stereo. L'immagine ISS occupa 1080×1440,
seguita dalla fascia riservata al testo. Non è un video a pieno schermo senza bordi.

- 232648: originale 1200×800; ritaglio destro 600×800 ingrandito 1,8× a 1080×1440.
  Consente di vedere l'aurora senza il pannello ISS davanti al centro dell'immagine,
  ma perde dettaglio rispetto a un originale verticale ad alta risoluzione.
- 849432: originale 3840×2160; ritaglio 1216×1620, ridotto a 1080×1440.
  Gamma 1,8, contrasto 1,04, saturazione 1,1 per rendere leggibile l'aurora tenue.
  Non sono sintetizzati nuovi dettagli. Rimane rumore nella ripresa notturna.
- 819232: disco SDO 1024×1024 ingrandito a 1080×1080, senza tagliarlo.
  Osservazione reale in ultravioletto a 131 Å, in falsi colori; non è una simulazione.

La composizione del campo largo viene ritagliata: non si pretende di conservare
l'intero originale. Il Sole mostrato **non è identificato come la causa dello
specifico evento aurorale**: sono osservazioni di date diverse. «Il Sole accende
il cielo» sintetizza il ruolo del vento solare nell'interazione con la magnetosfera
e nell'emissione di luce dell'alta atmosfera. La spiegazione e le fonti complete
sono nella caption. Le luci puntiformi al suolo sono città.

L'audio è un nuovo breve brano originale sintetizzato localmente: accordi morbidi,
note pizzicate, accenti sui tagli a 0/4/8/11 s, coda e dissolvenza finale.
Normalizzazione a obiettivo −18 LUFS e limite true peak −1,5 dBTP, AAC a 48 kHz. Nessun
campione, registrazione esterna, voce o audio dei file NASA. Brano CC0 1.0; questo
non modifica i diritti dei filmati NASA.

## Provenienza e diritti

URL diretti, hash SHA-256, attribuzioni e schede: `autopilot/aurora_sources.json` e
`docs/footage-evidence/{232648,849432,819232}.json`. Le condizioni NASA per uso
fattuale informativo senza endorsement sono verificate durante ogni rendering:
https://www.nasa.gov/nasa-brand-center/images-and-media/

Non sono identificati crediti o avvisi di copyright di terzi nelle tre schede
revisionate. Non si assume che tutti i contenuti NASA o ESA siano riutilizzabili.
Le descrizioni e i crediti devono coincidere con le prove revisionate; modifiche
ai file, ai metadati o alle affermazioni richieste bloccano la produzione.

Fonti scientifiche:
- https://www.nasa.gov/image-article/space-between-aurora-australis/
- https://www.nasa.gov/image-article/red-green-aurora-australis/

## Verifica e consegna

Il job esistente genera l'artifact `aurora-final-reel` (conservato 7 giorni):
`reel.mp4`, primo fotogramma, anteprima di quattro frame, caption, sottotitoli,
fonti e report tecnico. Nessun originale con audio non usato viene redistribuito.

Controlli: decodifica completa, formato/durata, 4 campioni visivi al secondo,
intervalli statici, frame neri, audio non silenzioso/non saturato, testo separato
dalla ripresa, nessun riuso di intervalli. Questi controlli non certificano bellezza,
interesse o un voto creativo. La nitidezza è limitata dalla fonte panoramica e
l'aurora ravvicinata è più tenue di quella sull'orizzonte: non si nascondono tali
limiti dietro al successo dei test.

Nessun costo aggiuntivo attivato: fonti senza chiave e strumenti locali open source;
runner GitHub standard nel repository pubblico, nessun runner premium. Nessun
servizio di pubblicazione viene eseguito dal job.

Verifica locale: 126 test superati (un warning esterno Starlette/AnyIO); ispezionati
il primo fotogramma senza logo/testo e i quattro frame del montaggio. La fascia
riservata ai cartigli è intenzionale, non un riempimento con immagini duplicate.
