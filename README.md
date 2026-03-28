# French Electricity Tariff API

REST API that scrapes electricity offers and tariffs from French energy providers via [Selectra.info](https://selectra.info).

## Data collected

For each provider and offer:
- **Provider name**
- **Offer name** (e.g. Zen Fixe, Tempo, etc.)
- **Pricing option** (Base, Peak/Off-Peak Hours, EJP…)
- **Subscribed power** in kVA (3, 6, 9, 12, 15, 18, 24, 30, 36 kVA…)
- **Subscription fee** in €/year
- **Price per kWh** by period type (Base, HP, HC, etc.)

## Supported providers

enercoop, happ-e, edf, geg, plenitude, wekiwi, elmy, alterna, ekwateur, urban-solar-energy, alpiq, totalenergies, vattenfall, primeo, gaz-de-bordeaux, mint-energie, engie, dyneff, octopus-energy, la-bellenergie, ohm-energie, ilek

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

The API starts, scrapes all providers automatically, then refreshes data every 24 hours.

## Interactive documentation

Open [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/providers` | List of provider slugs |
| `GET` | `/summary` | Summary of the last scrape |
| `GET` | `/tariffs` | All offers / all providers |
| `GET` | `/tariffs?kva=6` | Filter by subscribed power |
| `GET` | `/tariffs?provider=edf` | Filter by provider |
| `GET` | `/tariffs/{slug}` | Offers for a specific provider |
| `GET` | `/tariffs/{slug}?kva=6` | Offers for a provider at a given kVA |
| `GET` | `/tariffs/{slug}/offers` | Offer names for a provider |
| `POST` | `/refresh` | Trigger an immediate re-scrape of all providers |
| `POST` | `/refresh/{slug}` | Trigger a re-scrape for a single provider |

## Sample response

### `GET /tariffs/edf?kva=6`

```json
{
  "provider": "EDF",
  "slug": "edf",
  "source_url": "https://selectra.info/energie/fournisseurs/edf/tarifs",
  "scraped_at": "2026-03-28T10:00:00Z",
  "tariffs": [
    {
      "provider": "EDF",
      "offer_name": "Zen Fixe par EDF",
      "option": "Base",
      "kva": 6,
      "abonnement_eur_par_an": 177.36,
      "kwh_prix": { "Base": 0.1774 },
      "source_url": "https://selectra.info/energie/fournisseurs/edf/tarifs",
      "scraped_at": "2026-03-28T10:00:00Z"
    },
    {
      "provider": "EDF",
      "offer_name": "Zen Fixe par EDF",
      "option": "Heures pleines heures creuses",
      "kva": 6,
      "abonnement_eur_par_an": 180.60,
      "kwh_prix": { "Heures Pleines": 0.1888, "Heures Creuses": 0.1496 },
      "source_url": "https://selectra.info/energie/fournisseurs/edf/tarifs",
      "scraped_at": "2026-03-28T10:00:00Z"
    }
  ]
}
```

## Project structure

```
API_elec/
├── main.py          # FastAPI application
├── scraper.py       # Scraping logic
├── models.py        # Pydantic models
├── requirements.txt # Python dependencies
└── README.md
```
