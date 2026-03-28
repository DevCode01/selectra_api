from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TariffEntry(BaseModel):

    provider: str
    offer_name: str
    option: str
    kva: int
    abonnement_eur_par_an: Optional[float] = None
    kwh_prix: dict  # e.g. {"Base": 0.1774} or {"HP": 0.1888, "HC": 0.1496}
    source_url: str
    scraped_at: datetime


class ProviderTariffs(BaseModel):

    provider: str
    slug: str
    source_url: str
    scraped_at: datetime
    tariffs: List[TariffEntry]


class ScrapeSummary(BaseModel):

    total_providers: int
    total_tariff_entries: int
    scraped_at: datetime
    providers: List[str]

