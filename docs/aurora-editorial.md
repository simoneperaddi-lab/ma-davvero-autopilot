# Aurora: montaggio editoriale da osservazioni autentiche

Esecuzione: `python -m autopilot.aurora_editorial --output data/aurora-editorial`.
Nessuna chiave, nessun modulo Instagram importato. Il job di verifica in Actions produce
`aurora-editorial-reel` con MP4, anteprima, caption, fonti, prove e report. Non modifica
la programmazione o l'abilitazione della pubblicazione.

## Scelte verificabili

20 secondi, 1080×1920, H.264 a 24 fps, AAC stereo. Apertura selezionata fra aurora 4K e campo largo ISS;
cambio immediato all’altra osservazione; osservazione solare SDO; ritorno alle particelle/luce
nell'atmosfera; quota dell'emissione verde; chiusura «La Terra risponde».
Tagli netti motivati dal racconto. Nessuna dissolvenza decorativa, grafica scientifica
inventata, ripetizione temporale, rallentamento o sfondo duplicato/sfocato.

Tre osservazioni distinte, **non tre riprese diverse della stessa aurora**:

| NASA ID | Materiale | Uso e limiti |
|---|---|---|
| 849432 | Aurora borealis over the US and Canada, 3840×2160 | Ritaglio nativo 1216×2160 ridotto a verticale; gamma 1.35, contrasto 1.03, saturazione 1.02. |
| 232648 | ISS, 2 marzo 2023, 1200×800 | Campo largo completo, ridotto a 1080×720 dentro il quadro verticale. Nessun ingrandimento artificiale. |
| 819232 | NASA SDO, maggio 2024, 1024×1024 | Disco solare a risoluzione nativa, etichettato UV/falsi colori. Osservazione strumentale reale, non simulazione né luce visibile. |

URL diretti, hash, attribuzioni e schede originali sono in
`autopilot/aurora_sources.json` e `docs/footage-evidence/`. Il rendering scarica di
nuovo policy NASA, testi scientifici e schede: modifiche alle descrizioni, ai crediti,
alle affermazioni verificate o ai file bloccano la produzione per nuova verifica.
NASA consente l'uso fattuale informativo senza endorsement; non estendiamo questa
regola a contenuti terzi. Non sono stati individuati crediti terzi nelle tre schede.
L'audio dei filmati non viene usato né distribuito. Il sottofondo è una composizione
locale di oscillatori, senza campioni, rilasciata CC0. Non si rilascia sotto CC0 il video NASA.

Le tre varianti del post di Matthew Dominick (752962, 752957, 752953) sono escluse:
contengono interfaccia social, poco dettaglio utile e diritti ulteriori non verificati.
La vista diurna ISS 364031 è stata ispezionata ma non aggiunge informazione sull'aurora.
Non è stata presunta alcuna autorizzazione ESA.

## Regole riutilizzabili e limiti dell'autonomia

`autopilot/editorial.py` è indipendente dall'aurora e dal publisher: richiede almeno
tre gruppi di osservazione distinti, controlla hash duplicati, intervalli sovrapposti,
durata e autorizzazioni revisionate. Ritagli e download diversi dello stesso evento
non aumentano la varietà. Materiale insufficiente fa scartare il progetto, senza
riempire la durata. La provenienza dei gruppi è curata, non dedotta magicamente dai pixel.

L'apertura viene scelta fra finestre pertinenti già revisionate, misurando contrasto,
colore e attività; il piano viene poi nuovamente validato contro le ripetizioni.
Gli hook dipendono dal tema e vengono da formulazioni revisionate. Un tema senza hook
supportato viene scartato, non completato con un generatore di affermazioni inventate.
Queste regole sono usate dal comando di produzione, ma **non sostituiscono il renderer
quotidiano dell'autopilota**: la pubblicazione e tutte le modalità esistenti restano
intatte. L'estensione automatica a temi nuovi richiederebbe altri pool verificati.

## Verifica e limiti editoriali

Il report misura decodifica completa, durata, risoluzione, codec, audio presente/non
silenzioso/non saturato, fotogrammi neri e intervalli statici campionati a 4 fps.
I limiti del testo sono verificati prima del rendering: x 80–920, y 170–1570;
le interfacce Instagram possono comunque variare. Il layout non ingrandisce le fonti.
Il controllo di movimento non certifica ritmo, bellezza o interesse. Non assegniamo
un voto estetico automatico e non dichiariamo raggiunto 8/10.

Le fonti sono osservazioni diverse: **il brillamento SDO non è identificato come causa
delle aurore mostrate**. «Sembra bruciare» e «La Terra risponde» sono immagini narrative;
il testo chiarisce subito che non è fuoco. Il verde a 100–250 km è una proprietà
generale documentata dell'emissione dell'ossigeno, non una misura tratta da questi frame.
Le luci puntiformi al suolo sono città. I file mantengono la propria velocità: il
campo largo è un time-lapse; la cadenza originale della ripresa 4K non è dichiarata.

Il campo largo e il Sole non riempiono l'intera altezza: compromesso esplicito per
non tagliare l'orizzonte o degradare il dettaglio. Nessuna voce narrante; il racconto
è affidato a testi brevi e musica originale essenziale. Serve la valutazione editoriale
del MP4 per giudicare se il risultato è pubblicabile.

## Costi

Nessuna API a pagamento, abbonamento o hosting. Fonti pubbliche senza chiavi e
FFmpeg sui runner Ubuntu standard. Per repository pubblici i runner standard GitHub
sono gratuiti secondo le condizioni correnti; per repository privati valgono i minuti
e lo storage inclusi nel piano, con possibili costi se superati. Artifact conservato
7 giorni. Non viene attivato alcun acquisto o runner premium. Il job ha timeout di
10 minuti; il report registra il tempo effettivo, non promette risorse illimitate.

## Risultato controllato prima della PR

Rendering locale completo: 20 s, 1080×1920, H.264/24 fps e AAC stereo. Decodifica
integrale senza errori; 80 frame campionati, nessun intervallo statico rilevato alla
soglia usata, picco audio 0.162 e RMS 0.0346. I sette fotogrammi estratti sono stati
ispezionati: testi leggibili e nei margini; apertura ampia verde/rossa; contrasto netto
con disco solare; aurora ravvicinata più tenue e presenza visibile di luci cittadine.
Restano spazio vuoto nei campi non verticali, una sequenza ravvicinata di 6 secondi e
musica sintetica essenziale. Nessuna certificazione del voto editoriale richiesto.

Suite locale: 126 test superati, un warning di deprecazione esterno Starlette/AnyIO.
Actionlint e controllo whitespace superati. Un test preesistente del rate limit
poteva attraversare il confine del minuto: ora i due test relativi fissano l'orologio
locale del componente, senza modificare il comportamento della sicurezza in produzione.
