# Un Reel: prima il filmato, poi l'argomento

Ricerca effettuata il 16 ottobre 2026 tramite il catalogo WordPress pubblico
NASA (`/wp-json/wp/v2/media?media_type=video`). NASA Image and Video Library,
SVS ed ESA risultano bloccati dalla rete di questo ambiente. Non abbiamo
presunto permessi ESA né aggirato restrizioni: il catalogo NASA accessibile
fornisce direttamente metadati e MP4 originali sul dominio `www.nasa.gov`.

Sono stati scaricati **cinque filmati distinti**, analizzati con ffprobe e
ispezionati tramite fotogrammi. Non sono cinque varianti dello stesso video.
Metadati originali e risultati ffprobe sono conservati in `docs/footage-evidence/`;
URL diretti, hash SHA-256, crediti e valutazione individuale sono nel manifest
`autopilot/footage_sources.json`, incluso nell'artifact come `five-candidates.json`.

| Candidato e scheda ufficiale | Risoluzione / durata | Diritti e decisione |
|---|---|---|
| [Aurora borealis over the US and Canada — 849432](https://www.nasa.gov/wp-json/wp/v2/media/849432) | 3840×2160 / 12,467 s | **Scelto**. Ripresa ISS pubblicata da NASA, senza attribuzione terza nei metadati. Uso informativo alle condizioni NASA; credito NASA / ISS. Nessun autore individuale inventato. Audio sorgente scartato. |
| [Matthew Dominick — 752957](https://www.nasa.gov/wp-json/wp/v2/media/752957) | 1920×1080 / 55,3 s | Credito Matthew Dominick. Escluso: filmato incorporato in schermata X, con testo e interfaccia di terzi. Non viene attribuita una licenza NASA a ogni elemento del contenitore. |
| [Timelapse of Earth and Auroras at Night — 232648](https://www.nasa.gov/wp-json/wp/v2/media/232648) | 1200×800 / 14,68 s | Ripresa ISS pubblicata da NASA, senza avviso di diritti terzi nei metadati; uso informativo con attribuzione secondo policy NASA. Escluso per risoluzione insufficiente nel ritaglio verticale. |
| [Experiment Re-Creating a Carbon Dioxide Plume — 730261](https://www.nasa.gov/wp-json/wp/v2/media/730261) | 1080×1080 / 18,944 s | Credito NASA/JPL-Caltech. Escluso: condizioni specifiche JPL non verificabili dall'ambiente, oltre a testo incorporato e minore impatto visivo. Nessun permesso presunto. |
| [Orion Camera View of Spacecraft Adapter Jettison Panel Separation — 980951](https://www.nasa.gov/wp-json/wp/v2/media/980951) | 3840×2160 / 29,997 s | Credito NASA esplicito. Policy NASA per uso fattuale informativo senza endorsement. Escluso per aree sovraesposte e bordi neri. |

## URL diretti dei cinque MP4

1. https://www.nasa.gov/wp-content/uploads/2025/04/iss072e503021-aurora-borealis-4k.mp4
2. https://www.nasa.gov/wp-content/uploads/2024/11/matthew-dominick-x-timelapse-post.mp4
3. https://www.nasa.gov/wp-content/uploads/2023/02/iss068-e-66732-67098-20230302-night.mp4
4. https://www.nasa.gov/wp-content/uploads/2024/09/e3-pia26404-experiment-recreating-a-carbon-dioxide-plume.mp4
5. https://www.nasa.gov/wp-content/uploads/2026/04/art002m1200912222b-saj-jettison-2-2.mp4

## Condizioni del materiale utilizzato

https://www.nasa.gov/nasa-brand-center/images-and-media/

Passaggio verificato: “NASA content used in a factual manner that does not imply
endorsement may be used without needing explicit permission.” La policy richiede
attribuzione e distingue materiali protetti di terzi, loghi, persone e promozione
commerciale. La pagina non concede una licenza universale a tutto ciò che NASA
ospita. Il file selezionato è una ripresa ISS identificata dal catalogo NASA;
non compaiono persone, marchi aggiunti o avvisi di terzi nei metadati esaminati.
Il campo credito individuale è vuoto: si attribuisce NASA / ISS, non un astronauta
ipotetico. Non si suggerisce approvazione NASA. Questo controllo documentale non
è un parere legale né estende il permesso a pubblicità o usi promozionali futuri.

Il video originale contiene una traccia audio, **completamente esclusa** dal mix.
Il Reel usa soltanto una composizione originale locale con oscillatori, senza
campioni esterni. Il file `audio-license.txt` dedica questa composizione a CC0;
la dedica non si applica al filmato NASA. Nessun TTS, servizio generativo o API pagata.

## Scienza e narrazione

Fonte: https://www.nasa.gov/image-article/red-green-aurora-australis/

I passaggi salvati in `evidence.json` sostengono collisioni fra elettroni e atomi,
emissione di luce al ritorno allo stato non eccitato e origine del verde
nell'ossigeno. La fonte descrive la fisica generale, **non** la specifica ripresa
ISS selezionata. Nessuna inferenza su data esatta, quota, tempesta particolare o
velocità del fenomeno. Le luci puntiformi delle città sono distinte dall'aurora
nella caption. Il catalogo non dichiara la cadenza di acquisizione del file scelto:
non lo presentiamo come moto in tempo reale.

Sei brevi segmenti di testo, leggibili senza audio, accompagnano la ripresa per
24 secondi. Il testo spiega ciò che si vede; non sostituisce le immagini.

## Montaggio e limiti di qualità

Solo il file 849432 fornisce l'immagine, dall'inizio alla fine: **nessun pianeta
Python, immagine generativa, simulazione, sfondo sintetico o slide**.
Sei tagli con inquadrature verticali diverse, ritaglio 1216×2160 ridotto a
1080×1920, senza ingrandimenti oltre la risoluzione sorgente. Movimento reale
più un piccolo spostamento del ritaglio. Il filmato originale di circa 12,5 secondi
è rimontato in ordine editoriale (la chiusura riprende due secondi già visti,
con ritaglio diverso), riprodotto a metà velocità e portato a 24 fps
con media fra fotogrammi adiacenti. Non sono 24 secondi di osservazioni nuove.
Gamma 1,6, contrasto 1,03 e saturazione 1,06 rendono leggibile l'aurora notturna:
non si creano strutture, ma non è un'esportazione fotometricamente calibrata.

Limiti da giudicare guardando il file: ripresa notturna rumorosa, possibili scie
lievi dovute alla media fra fotogrammi, parti della ISS nella composizione originale,
una sola scena osservativa e nessuna voce narrante. Non si promette qualità da
produzione cinematografica con più camere. Le sei inquadrature derivano dalla
stessa ripresa, non da sei missioni o eventi diversi.

## Verifica e uso

```bash
python -m pip install -r requirements.txt -c requirements.lock
python -m autopilot.footage_demo --output data/authentic-footage
python -m pytest -q
```

Servono FFmpeg/ffprobe e DejaVu Sans, già previsti dal progetto. Nessuna nuova
libreria, credenziale o configurazione di servizio. Lo script fallisce se cambiano
fonte, policy, hash del filmato o formato; **nessun fallback grafico**.
La CI esegue lo stesso comando su Ubuntu standard, senza segreti Instagram.

Il report controlla formato, durata, decodifica integrale, audio e movimento del
soggetto (senza titoli) campionato a 4 fps. Ogni testo è misurato prima del rendering.
Questi controlli non sono una valutazione estetica umana e possono non rilevare
un difetto visivo più breve di 250 ms. I fotogrammi della preview sono estratti
dall'MP4 effettivamente codificato.

Artifact `authentic-footage-reel`: `reel.mp4`, `index.html`, preview, fotogrammi,
caption, SRT, prove NASA, cinque candidati, musica e controlli. Conservazione 7 giorni.
Nessun canone o API a pagamento. Repository pubblico, runner GitHub standard;
quote e condizioni GitHub continuano ad applicarsi. Nessuna spesa attivata.
Questo comando dimostrativo non importa né chiama il publisher: integrazione
Instagram, cron, token e registro restano invariati. Nessuna pubblicazione reale.
