# Tre film da valutare, non una certificazione estetica

`python -m autopilot.showcase` produce tre film da 24 secondi e una pagina
`data/cinema-showcase/index.html`, apribile dopo aver estratto l'artifact.
Ogni cartella contiene MP4, otto fotogrammi estratti dal file codificato,
contact sheet, SRT, caption, fonti, provenienza e report tecnico.
La CI genera l'artifact **cinematic-science-reels**, conservato per 7 giorni.
Nessun job di questa consegna carica contenuti su Instagram.

## Montaggio e materiali

- **Pioggia solare**: osservazioni SDO di pioggia coronale dopo un'eruzione del
  2012, pubblicate nell'articolo NASA del 2019; ultravioletto in falsi colori e
  tempo accelerato. Il GIF originale è 600×338: lo mostriamo nativo, in una
  finestra d'archivio. Le altre scene sono illustrazioni procedurali animate,
  con plasma, particelle in movimento, superficie e dettagli ravvicinati.
- **Anelli di Saturno**: mosaico Cassini del 17 ottobre 2012, 1041×484, colori
  enfatizzati. Non è una fotografia nei colori percepiti dall'occhio. Passaggi
  fra vedute degli anelli, sorvoli illustrativi di frammenti e cambi di piano.
- **Luna rossa**: visualizzazione NASA/Goddard/LRO della Luna piena del dicembre
  2015, 3240×3240. Il dettaglio lunare deriva da questa risorsa. La colorazione
  rossa è una nostra elaborazione illustrativa, non la fotografia di un'eclissi.
  Sequenza del percorso della luce, dispersione del blu, atmosfera e primo piano.

Le immagini originali sono accompagnate dai crediti riportati nella loro pagina.
Le illustrazioni locali sono marcate «ILLUSTRAZIONE ANIMATA · NON IN SCALA»:
non sono simulazioni scientifiche, non ricostruiscono geometrie misurate e non
vanno usate per inferire dimensioni, temperature, tempi o mappe terrestri.
Non si usano APOD, media di terzi non autorizzati, loghi NASA o musiche commerciali.

## Fonti e condizioni d'uso

Il catalogo in `autopilot/documentaries.py` lega ciascun film a passaggi testuali
precisi, URL della fonte, pagina del materiale, credito e hash del file.
Ogni esecuzione recupera le pagine e verifica che passaggi, credito e permesso
editoriale siano ancora presenti. Salva i testi consultati e gli hash delle pagine.
Se una fonte, un credito o il file cambiano, la storia viene saltata.
Non è un fact-check scientifico indipendente: è una selezione editoriale
ristretta, con verifica automatica della corrispondenza alle fonti NASA.

Condizioni consultate il 15 ottobre 2026:
https://www.nasa.gov/nasa-brand-center/images-and-media/

La pagina consente l'uso fattuale informativo senza implicare approvazione NASA;
richiede attribuzione e distingue i materiali di terzi. I materiali scelti sono
accreditati alle missioni/istituzioni indicate nelle rispettive pagine, senza
avviso di copyright di terzi associato. Le altre immagini della stessa pagina
non vengono importate (l'articolo sulla pioggia include anche una foto protetta,
che abbiamo escluso). Non attribuiamo una licenza CC0 ai materiali NASA.
La caption distingue la nostra produzione automatica dalle risorse originali
ed esplicita che NASA non ha revisionato o approvato il risultato.

## Audio e voce italiana

Musica originale locale stereo 48 kHz: oscillatori, armonia lenta, battito morbido,
rumore sintetico filtrato per transizioni; nessun campione esterno. I tagli ogni
3 secondi coincidono con sei battiti a 120 BPM. Fade finale e margine dal clipping.
Sottotitoli impressi nel video e file SRT seguono gli otto segmenti del racconto.
Non essendoci voce, sono sincronizzati alle scene, non a parole pronunciate.

Valutazione concreta: eseguito **eSpeak NG**, distribuzione WASM npm `espeak-ng`
1.0.2 (GPL-3.0-or-later), voce italiana `it`, 150 parole/minuto, ottenendo un WAV
locale. La CI ripete il campione con eSpeak NG del repository Ubuntu e allega
WAV e copyright del motore. È un sintetizzatore a formanti: non è una voce neurale
naturale. Il campione non è stato sottoposto a una valutazione d'ascolto umana;
non dichiariamo superata una soglia estetica. La voce è quindi **esclusa** dal mix.
Piper/Paola è stato valutato come candidato, ma la model card su Hugging Face
non è accessibile da questo ambiente: nessun modello scaricato senza verificarne
licenza, nessuna qualità dichiarata. Il sistema quotidiano non dipende dal TTS.

## Controlli e limiti

Rendering nativo 1080×1920, 24 fps, H.264/yuv420p, AAC stereo, 24 secondi.
FFmpeg decodifica l'intero file con `-xerror`; ffprobe controlla formato e durata.
Si campiona a 4 fps la regione del soggetto, escludendo titoli e barra di progresso,
per rilevare fotogrammi neri/vuoti e tratti statici oltre 2 secondi. Campionare non
rileva necessariamente difetti più brevi di 250 ms. L'audio viene decodificato
integralmente per controllare picco, RMS, durata e canali. Dimensioni minime delle
risorse e hash impediscono sostituzioni con miniature. Il materiale d'archivio
non viene ingrandito oltre la sua risoluzione. Ogni testo editoriale viene
misurato ad ogni frame e deve restare nella zona sicura definita dal renderer.
Questa zona non garantisce compatibilità con ogni futura interfaccia Instagram.

Questi controlli **non sono una valutazione estetica umana**. Le tavole dei
fotogrammi codificati sono state ispezionate durante lo sviluppo. Difetti residui:

- Sole: archi ancora stilizzati; ripresa autentica piccola e disponibile per un
  solo segmento; la composizione resta più illustrativa che fotorealistica.
- Saturno: frammenti geometrici, densità e scale illustrative; la ripresa Cassini
  non ha sufficiente risoluzione per un ritaglio verticale a pieno schermo.
- Luna: percorso dei raggi schematico, Terra procedurale con continenti inventati;
  colore lunare illustrativo uniforme, non previsione di una specifica eclissi.
- Tutti: otto segmenti da tre secondi e medesima partitura; ritmo regolare e
  riconoscibile, ma meno vario di un montaggio umano. Nessuna voce narrante.

Il motore supera le slide di testo, ma **non dichiariamo raggiunto un livello
fotorealistico cinematografico uniforme**. I tre file permettono di giudicarlo.

## Automazione e compatibilità

`verify`, `preflight` e la selezione produttiva usano ora il catalogo documentario.
Il renderer precedente resta disponibile per le fixture offline e i vecchi fatti
esopianetari già nel registro: non invalidiamo pubblicazioni pendenti o test.
Integrazione Meta, token, ledger, deduplicazione, consenso esplicito e pianificazione
non sono stati cambiati. Non sono stati attivati variabili o segreti di pubblicazione.

Il catalogo contiene **tre storie**: dopo averle utilizzate, si salta la produzione,
non si riciclano né si inventano temi. Non è un ricercatore scientifico universale
né un servizio editoriale quotidiano illimitato. L'interfaccia consente altri
soggetti con proprie fonti, diritti e regia, ma la loro validazione non è automatica.

## Costo reale

Repository verificato **pubblico** tramite API GitHub il 15 ottobre 2026.
La documentazione ufficiale corrente di GitHub conferma gratuità di Actions
per repository pubblici su runner standard; sorgente consultata:
https://github.com/github/docs/blob/main/content/billing/concepts/product-billing/github-actions.md

Qui si usano solo `ubuntu-24.04`, Python, Pillow, NumPy e FFmpeg; nessuna GPU,
API generativa, hosting, abbonamento o trial. Nessuna modifica alla fatturazione.
La generazione dei tre video richiede nell'ambiente locale circa 1,5–2,5 minuti
per film, più installazione, verifiche e upload. La CI ha timeout 20 minuti per
l'intera consegna; il suo tempo effettivo è consultabile nel run dell'artifact.
Gli artifact di revisione durano 7 giorni, quelli quotidiani 1 giorno.
Lo spazio non è infinito e le quote dell'account sono condivise con altri lavori.
Repository privati, runner maggiorati, conservazione crescente o cambiamenti delle
condizioni GitHub possono introdurre costi: non promettiamo gratuità universale
né abbiamo accesso alla fatturazione complessiva dell'account.
