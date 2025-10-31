
# Nero Vesuviano • Inventory (Mac-ready)

Gestione **prodotti** e **listini** semplice, locale su **Mac** (o qualunque sistema con Python 3.10+).

## Funzioni
- CRUD prodotti (SKU, nome, categoria, fornitore, prezzo, costo, IVA, giacenza, scorta minima, note)
- Listini multipli con prezzi per prodotto
- Ricerca e filtri per categoria
- Import/Export CSV (prodotti + listini)
- Evidenza prodotti sotto scorta

## Requisiti
- Python 3.10 o superiore
- Connessione internet solo la prima volta per installare le dipendenze

## Installazione su Mac
1. Apri **Terminale** e posizionati nella cartella del progetto.
2. Crea e attiva l'ambiente:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Avvia l'app:
   ```bash
   python app.py
   ```
5. Apri il browser su **http://127.0.0.1:5000**

### Avvio rapido (doppio click)
Su Mac puoi creare un file `start.command` (già incluso) e fare doppio click:
- Se richiesto: in Terminale esegui `chmod +x start.command` una sola volta.

## Import/Export
- Prodotti → pulsanti **Import CSV** e **Export CSV** nella pagina Prodotti.
- Listino → **Export CSV** dalla pagina del singolo listino.

## Sicurezza
- Il file `.env` contiene la `SECRET_KEY` (cambiala).
- Database locale SQLite `inventory.db` (nella cartella del progetto).

## Note
- È un'app base ma estensibile (lotti, scadenze, utenti, ruoli, IVA multilivello, stampe listini, ecc.).


## Novità
- **Lotti & Scadenze** per ogni prodotto (con impatto automatico su giacenza)
- **Margini** (€/%) in lista prodotti (se è valorizzato il costo)
- **Export Listino in PDF** (ReportLab)


## Master dati aggiunti
- **Fornitori (anagrafica)** con P.IVA/CF, contatti e indirizzo
- **Categorie** con descrizione
- Prodotti collegati a **Categoria** e **Fornitore** tramite menu a tendina
- Import CSV riconosce automaticamente nomi Categoria/Fornitore e li crea se mancanti


## Canali listino + Report
- **Listini per canale**: Generale / B2B / B2C / Ho.Re.Ca. (filtro e campo dedicato)
- **Report Scadenze**: filtro giorni, categoria, fornitore + export CSV/PDF
