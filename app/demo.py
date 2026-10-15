"""Editorial examples; source suggestions still require human checking."""

from app.models import Category, Script


def example(category: Category) -> Script:
    if category == Category.space:
        return Script(
            title="Su Venere un giorno supera un anno?", category=category,
            hook="Su Venere una rotazione dura più di un giro intorno al Sole.",
            slides=[
                {"title": "MA DAVVERO?", "text": "Su Venere un giorno può durare più di un anno. Ma quale giorno?"},
                {"title": "Una rotazione lentissima", "text": "Venere impiega circa 243 giorni terrestri a ruotare una volta rispetto alle stelle."},
                {"title": "Un anno più breve", "text": "Per completare un'orbita intorno al Sole bastano circa 225 giorni terrestri."},
                {"title": "La distinzione che conta", "text": "Il giorno solare, da un mezzogiorno al successivo, dura invece circa 117 giorni terrestri: non supera l'anno."},
                {"title": "Salva questa curiosità", "text": "Quando senti parlare di un giorno più lungo dell'anno, chiedi se si intende la rotazione rispetto alle stelle."},
            ],
            caption="Una rotazione di Venere dura circa 243 giorni terrestri, un anno circa 225. Il giorno solare è un'altra misura: circa 117 giorni. #MaDavvero #Spazio #Venere",
            sources=[{"title": "NASA Science — Venus Facts", "url": "https://science.nasa.gov/venus/facts/"}],
            verification_notes="Controllare i valori e distinguere giorno siderale e solare nella fonte NASA prima della pubblicazione.",
        )
    if category == Category.nature:
        return Script(
            title="I polpi hanno davvero tre cuori", category=category,
            hook="Tre cuori, due branchie e un modo sorprendente di trasportare ossigeno.",
            slides=[
                {"title": "MA DAVVERO?", "text": "Un polpo ha tre cuori. E non fanno tutti lo stesso lavoro."},
                {"title": "Due per le branchie", "text": "Due cuori spingono il sangue verso le branchie, dove può raccogliere ossigeno."},
                {"title": "Uno per il corpo", "text": "Il cuore sistemico invia il sangue ossigenato al resto del corpo."},
                {"title": "Perché il sangue è blu?", "text": "Il trasporto dell'ossigeno usa emocianina, una proteina contenente rame. Quando è ossigenata appare blu."},
                {"title": "La biologia sorprende", "text": "Sistemi circolatori diversi risolvono lo stesso problema: portare ossigeno ai tessuti. Salva la curiosità."},
            ],
            caption="Tre cuori con compiti distinti e sangue con emocianina: il polpo è una lezione di biodiversità. #MaDavvero #Polpi #Biologia",
            sources=[{"title": "Smithsonian Ocean — Octopuses, Squids, and Relatives", "url": "https://ocean.si.edu/ocean-life/invertebrates/octopuses-squids-and-relatives"}],
            verification_notes="Verificare nella fonte il sistema circolatorio e la descrizione dell'emocianina; evitare generalizzazioni su tutti i molluschi.",
        )
    return Script(
        title="Il cervello usa energia anche a riposo", category=Category.body,
        hook="Il cervello non aspetta un problema di matematica per consumare energia.",
        slides=[
            {"title": "MA DAVVERO?", "text": "Anche mentre riposi il cervello continua a usare una quota importante dell'energia del corpo."},
            {"title": "Una rete sempre attiva", "text": "Mantenere i segnali elettrici e la comunicazione tra le cellule richiede energia anche senza un compito cosciente."},
            {"title": "Un ordine di grandezza", "text": "Nell'adulto il cervello rappresenta circa il 2% della massa corporea ma usa circa il 20% dell'energia a riposo."},
            {"title": "Non è un contatore fisso", "text": "Sono valori indicativi: età, stato fisiologico e metodo di misura cambiano le stime. Non sono una misura dell'intelligenza."},
            {"title": "Il riposo non è uno spegnimento", "text": "Le funzioni di base continuano. Salva questo promemoria per la prossima curiosità sul cervello."},
        ],
        caption="Il cervello lavora anche a riposo. Le percentuali sono stime per l'adulto e dipendono dal contesto. #MaDavvero #Cervello #Neuroscienze",
        sources=[{"title": "Raichle & Gusnard — Appraising the brain's energy budget", "url": "https://doi.org/10.1073/pnas.172399499"}],
        verification_notes="Consultare il lavoro citato per il contesto delle stime. Non usare questi dati per consigli medici o promesse cognitive.",
    )
