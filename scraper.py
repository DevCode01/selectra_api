"""
scraper.py – scrape electricity tariffs from Selectra pages.

For each provider URL the scraper:
  1. Fetches the HTML page.
  2. Finds all <table class="table table--small"> elements which contain tariff grids.
  3. Parses caption → offer name + option.
  4. Parses each <tr> → kVA, abonnement (€/an), kWh price(s).
  5. Returns a list of TariffEntry objects.
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict

import requests
from bs4 import BeautifulSoup

from models import TariffEntry, ProviderTariffs

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider URL mapping  slug → (display_name, url)
# ---------------------------------------------------------------------------
PROVIDERS: Dict[str, str] = {
    "enercoop":           "https://selectra.info/energie/fournisseurs/enercoop/tarifs",
    "happ-e":             "https://selectra.info/energie/fournisseurs/happ-e/tarifs",
    "edf":                "https://selectra.info/energie/fournisseurs/edf/tarifs",
    "geg":                "https://selectra.info/energie/fournisseurs/geg/tarifs",
    "plenitude":          "https://selectra.info/energie/fournisseurs/plenitude/tarifs",
    "wekiwi":             "https://selectra.info/energie/fournisseurs/wekiwi/tarifs",
    "elmy":               "https://selectra.info/energie/fournisseurs/elmy/tarifs",
    "alterna":            "https://selectra.info/energie/fournisseurs/alterna/tarifs",
    "ekwateur":           "https://selectra.info/energie/fournisseurs/ekwateur/tarifs",
    "urban-solar-energy": "https://selectra.info/energie/fournisseurs/urban-solar-energy/tarifs",
    "alpiq":              "https://selectra.info/energie/fournisseurs/alpiq/tarifs",
    "totalenergies":      "https://selectra.info/energie/fournisseurs/totalenergies/tarifs",
    "vattenfall":         "https://selectra.info/energie/fournisseurs/vattenfall/tarifs",
    "primeo":             "https://selectra.info/energie/fournisseurs/primeo/tarifs",
    "gaz-de-bordeaux":    "https://selectra.info/energie/fournisseurs/gaz-de-bordeaux/tarifs",
    "mint-energie":       "https://selectra.info/energie/fournisseurs/mint-energie/tarifs",
    "engie":              "https://selectra.info/energie/fournisseurs/engie/tarifs",
    "dyneff":             "https://selectra.info/energie/fournisseurs/dyneff/tarifs",
    "octopus-energy":     "https://selectra.info/energie/fournisseurs/octopus-energy/tarifs",
    "la-bellenergie":     "https://selectra.info/energie/fournisseurs/la-bellenergie/tarifs",
    "ohm-energie":        "https://selectra.info/energie/fournisseurs/ohm-energie/tarifs",
    "ilek":               "https://selectra.info/energie/fournisseurs/ilek/tarifs",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RE_KVA = re.compile(r"(\d+)\s*kVA", re.IGNORECASE)
_RE_EUR_AN = re.compile(r"([\d,\.]+)\s*[€\u20ac]\/an")
_RE_KWH = re.compile(r"([\d,\.]+)\s*[€\u20ac]\/kWh")

# Caption patterns:
# "Grille tarifaire de l'offre <NAME> en option <OPTION> (TTC)"
# "Grille tarifaire de <NAME> en option <OPTION> (TTC)"
# "Grille tarifaire de l'offre <NAME> (TTC)"
_RE_CAPTION = re.compile(
    r"(?:Grille tarifaire de l[''']offre|Grille tarifaire de)\s+"
    r"(?P<offer>.+?)"
    r"(?:\s+en option\s+(?P<option>.+?))?"
    r"\s*(?:\(TTC\))?\s*$",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    """Remove non-breaking spaces and extra whitespace."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _parse_float(value: str) -> Optional[float]:
    """Convert '0,1774' or '177,36' to float."""
    value = _clean(value).replace(",", ".").replace(" ", "")
    try:
        return float(value)
    except ValueError:
        return None


def _extract_provider_name(soup: BeautifulSoup, slug: str) -> str:
    """Extract the provider display name from the page H1 or title."""
    h1 = soup.find("h1")
    if h1:
        text = _clean(h1.get_text())
        # "chez EDF" → "EDF"
        match = re.search(r"chez\s+(.+?)(?:\s+en\s|\s*\?|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return slug.replace("-", " ").title()


def _parse_caption(caption_text: str, slug: str) -> tuple[str, str]:
    """
    Returns (offer_name, option).
    Falls back to (slug, "Base") if the pattern doesn't match.
    """
    caption_text = _clean(caption_text)
    m = _RE_CAPTION.match(caption_text)
    if m:
        offer = _clean(m.group("offer"))
        option = _clean(m.group("option")) if m.group("option") else "Base"
        return offer, option
    return slug.replace("-", " ").title(), "Base"


def _parse_tariff_table(
    table,
    provider_name: str,
    slug: str,
    source_url: str,
    scraped_at: datetime,
) -> List[TariffEntry]:
    """Parse a single tariff table and return a list of TariffEntry objects."""
    entries: List[TariffEntry] = []

    caption_el = table.find("caption")
    if not caption_el:
        return entries
    caption_text = _clean(caption_el.get_text())

    offer_name, option = _parse_caption(caption_text, slug)

    # Determine column mapping from header row
    thead = table.find("thead")
    if not thead:
        return entries
    header_cells = thead.find_all("th")
    # Column 0: kVA, Column 1: Abonnement, Columns 2+: kWh types
    kwh_column_names: List[str] = []
    for i, th in enumerate(header_cells):
        if i < 2:
            continue
        label = _clean(th.get_text())
        # Remove "Prix du kWh" prefix and keep the type
        label = re.sub(r"Prix du kWh\s*", "", label, flags=re.IGNORECASE).strip()
        if not label:
            label = "Base"
        kwh_column_names.append(label)

    tbody = table.find("tbody")
    if not tbody:
        return entries

    for row in tbody.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 3:
            continue

        # kVA
        kva_text = _clean(cells[0].get_text())
        kva_match = _RE_KVA.search(kva_text)
        if not kva_match:
            # Try extracting first number
            num_match = re.search(r"\d+", kva_text)
            if not num_match:
                continue
            kva = int(num_match.group())
        else:
            kva = int(kva_match.group(1))

        # Abonnement
        abo_text = _clean(cells[1].get_text())
        abo_match = _RE_EUR_AN.search(abo_text)
        abonnement = _parse_float(abo_match.group(1)) if abo_match else None

        # kWh prices
        kwh_prix: Dict[str, float] = {}
        for idx, col_name in enumerate(kwh_column_names):
            col_idx = 2 + idx
            if col_idx >= len(cells):
                break
            cell_text = _clean(cells[col_idx].get_text())
            kwh_match = _RE_KWH.search(cell_text)
            if kwh_match:
                val = _parse_float(kwh_match.group(1))
                if val is not None:
                    kwh_prix[col_name if col_name else "Base"] = val

        if not kwh_prix:
            continue

        entries.append(
            TariffEntry(
                provider=provider_name,
                offer_name=offer_name,
                option=option,
                kva=kva,
                abonnement_eur_par_an=abonnement,
                kwh_prix=kwh_prix,
                source_url=source_url,
                scraped_at=scraped_at,
            )
        )

    return entries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrape_provider(slug: str) -> Optional[ProviderTariffs]:
    """Scrape tariffs for a single provider. Returns None on error."""
    url = PROVIDERS.get(slug)
    if not url:
        logger.warning("Unknown provider slug: %s", slug)
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None

    scraped_at = datetime.now(timezone.utc)
    soup = BeautifulSoup(resp.text, "lxml")
    provider_name = _extract_provider_name(soup, slug)

    tariff_tables = soup.find_all("table", class_=lambda c: c and "table--small" in c)

    all_entries: List[TariffEntry] = []
    for table in tariff_tables:
        entries = _parse_tariff_table(table, provider_name, slug, url, scraped_at)
        all_entries.extend(entries)

    logger.info(
        "Scraped %s: %d tariff entries from %d tables",
        slug,
        len(all_entries),
        len(tariff_tables),
    )

    return ProviderTariffs(
        provider=provider_name,
        slug=slug,
        source_url=url,
        scraped_at=scraped_at,
        tariffs=all_entries,
    )


def scrape_all_providers() -> Dict[str, ProviderTariffs]:
    """Scrape all providers and return a dict keyed by slug."""
    results: Dict[str, ProviderTariffs] = {}
    for slug in PROVIDERS:
        data = scrape_provider(slug)
        if data:
            results[slug] = data
    return results

