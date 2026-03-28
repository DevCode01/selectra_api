# API Tarifs Électricité France

API REST qui scrape les offres et tarifs des fournisseurs d'électricité en France depuis [Selectra.info](https://selectra.info).

## Données récupérées

Pour chaque fournisseur et chaque offre :
- **Nom du fournisseur**
- **Nom de l'offre** (ex : Zen Fixe, Tempo, etc.)
- **Option tarifaire** (Base, Heures Pleines / Heures Creuses, EJP…)
- **Puissance souscrite** en kVA (3, 6, 9, 12, 15, 18, 24, 30, 36 kVA…)
- **Tarif d'abonnement** en €/an
- **Prix du kWh** par type (Base, HP, HC, etc.)

## Fournisseurs couverts

enercoop, happ-e, edf, geg, plenitude, wekiwi, elmy, alterna, ekwateur, urban-solar-energy, alpiq, totalenergies, vattenfall, primeo, gaz-de-bordeaux, mint-energie, engie, dyneff, octopus-energy, la-bellenergie, ohm-energie, ilek

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

L'API démarre, scrape tous les fournisseurs automatiquement, puis rafraîchit les données toutes les 24 h.

## Documentation interactive

Ouvrez [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/providers` | Liste des slugs fournisseurs |
| `GET` | `/summary` | Résumé du dernier scrape |
| `GET` | `/tariffs` | Toutes les offres / tous les fournisseurs |
| `GET` | `/tariffs?kva=6` | Filtrer par puissance |
| `GET` | `/tariffs?provider=edf` | Filtrer par fournisseur |
| `GET` | `/tariffs/{slug}` | Offres d'un fournisseur |
| `GET` | `/tariffs/{slug}?kva=6` | Offres d'un fournisseur pour un kVA |
| `GET` | `/tariffs/{slug}/offers` | Noms des offres d'un fournisseur |
| `POST` | `/refresh` | Re-scrape immédiat de tous les fournisseurs |
| `POST` | `/refresh/{slug}` | Re-scrape d'un fournisseur |

## Exemples de réponse

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

## Structure du projet

```
API_elec/
├── main.py          # Application FastAPI
├── scraper.py       # Logique de scraping
├── models.py        # Modèles Pydantic
├── requirements.txt # Dépendances Python
└── README.md
```

