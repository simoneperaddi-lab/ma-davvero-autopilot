# Reel orbitale — verifica visiva

Correzione mirata del renderer dell'autopilota: lo studio editoriale, le API Instagram, i controlli scientifici e il workflow di pubblicazione restano invariati. Nessuna nuova dipendenza o API a pagamento.

Il Reel dura **20 secondi**, 1080×1920, H.264, 24 fps, con AAC 48 kHz opzionale. La scena viene disegnata frame per frame con Pillow e codificata in streaming con FFmpeg; non è uno slideshow con zoom. La grafica viene rasterizzata a 540×960 e ingrandita con Lanczos per l'export 1080×1920. Il limite è deliberato per mantenere bassi i tempi CPU; titoli grandi e un controllo dei frame codificati preservano la leggibilità su smartphone.

| Secondi | Cosa si vede |
|---|---|
| 0–2,5 | Stella in primo piano, pianeta già in moto e dato numerico immediato |
| 2,5–5 | Vista del sistema con etichette stella/pianeta |
| 5–7,5 | Scia orbitale e avanzamento del giro: un'orbita = un anno |
| 7,5–10 | Periodo orbitale espresso in ore terrestri |
| 10–12,5 | Confronto grafico proporzionale tra il periodo misurato e 24 ore |
| 12,5–15 | Camera che segue il pianeta in primo piano; orbita distinta dalla rotazione |
| 15–17,5 | Richiamo alla misura NASA e alla sua incertezza |
| 17,5–20 | Chiusura MA DAVVERO? con rimando alle fonti |

Otto inquadrature, cambi ogni 2,5 secondi, animazione continua anche tra i cambi. Lo sfondo ha stelle procedurali, la stella ha un alone originale, il pianeta una sfera ombreggiata e una scia direzionale. Grafica lime/teal e marchio MA DAVVERO? costanti. Testi principali brevi; misure, URL della fonte, riferimento bibliografico e SHA-256 rimangono in caption/evidence.json. `render.json` registra anche il testo effettivo delle otto inquadrature.

**Il disegno non è una simulazione astrofisica:** colore, dimensioni, inclinazione e velocità sono illustrativi. «SCHEMA • NON IN SCALA» e «Colori illustrativi • tempo accelerato» restano visibili in ogni inquadratura. Non viene inventato il periodo di rotazione, né viene rappresentata una superficie osservata. Il confronto con 24 ore usa invece il rapporto numerico reale del periodo orbitale.

Colonna sonora originale a **120 BPM**, con sintetizzatori sinusoidali, basso, kick e percussioni generate localmente; niente campioni esterni. Ogni cambio di scena cade su un beat (cinque beat per inquadratura). Accenti grafici seguono lo stesso clock. Non indicano variazioni fisiche della stella. Licenza CC0 allegata; nessuna musica commerciale, voce sintetica remota o servizio premium.

## Prova effettuata

`python -m autopilot --mode verify --output data/orbital-preview` ha recuperato due volte il record NASA di **55 Cnc e**, periodo **0,7365474 giorni**, circa **17,7 ore terrestri**, e prodotto il video con fonti reali. Nessun container Instagram o pubblicazione.

Controllo visivo dei frame codificati: apertura, etichette, avanzamento orbitale, misura, barre comparative, primo piano e fonte. Il renderer salva otto JPEG estratti dal MP4 e `contact-sheet.jpg`; questi mostrano il risultato effettivo dopo la compressione. Si possono riesaminare nell'artifact GitHub **nasa-orbital-reel**, insieme a `reel.mp4`, caption, SRT, evidenze, metadati e licenza. La CI conserva questo artifact per **7 giorni**. Una futura esecuzione verify può selezionare un altro soggetto se il catalogo cambia.

Test aggiunti: stella e pianeta presenti al primo frame, movimento durante il primo secondo e dentro le inquadrature, variazioni grafiche tra le viste, barra proporzionale alla misura, identificativi lunghi, etichetta dello schema, rifiuto di misure invalide, headroom e accenti musicali, export senza audio, frame estratti e tracciabilità. La suite precedente verifica anche formato/durata/codec del nuovo Reel con audio e deduplicazione della pipeline.

La pubblicazione non viene abilitata da questa modifica. L'unica richiesta esterna della prova visiva è la lettura pubblica del catalogo NASA.
