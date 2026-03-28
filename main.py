import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from models import TariffEntry, ProviderTariffs, ScrapeSummary
from scraper import scrape_all_providers, scrape_provider, PROVIDERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_cache: Dict[str, ProviderTariffs] = {}
_last_refresh: Optional[datetime] = None


def _do_refresh_all() -> None:
    global _cache, _last_refresh
    logger.info("Starting full scrape of all providers…")
    results = scrape_all_providers()
    _cache.update(results)
    _last_refresh = datetime.now(timezone.utc)
    total = sum(len(p.tariffs) for p in _cache.values())
    logger.info("Scrape complete: %d providers, %d total tariff entries", len(_cache), total)


def _do_refresh_one(slug: str) -> Optional[ProviderTariffs]:
    global _cache, _last_refresh
    logger.info("Scraping provider: %s", slug)
    data = scrape_provider(slug)
    if data:
        _cache[slug] = data
        _last_refresh = datetime.now(timezone.utc)
    return data


app = FastAPI(
    title="API Tarifs Électricité France",
    description=(
        "API REST exposant les offres et tarifs des fournisseurs d'électricité "
        "en France, scraped depuis Selectra.info."
    ),
    version="1.0.0",
    contact={"name": "API_elec"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()
scheduler.add_job(_do_refresh_all, "interval", hours=24, id="auto_refresh")


@app.on_event("startup")
def startup_event():
    _do_refresh_all()
    scheduler.start()
    logger.info("Scheduler started – auto-refresh every 24 h.")


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown(wait=False)




@app.get("/", tags=["Info"])
def root() -> Dict[str, Any]:
    return {
        "status": "ok",
        "description": "API Tarifs Électricité France",
        "providers_cached": len(_cache),
        "last_refresh": _last_refresh.isoformat() if _last_refresh else None,
        "docs": "/docs",
    }


@app.get("/providers", tags=["Providers"], response_model=List[str])
def list_providers():
    return list(PROVIDERS.keys())


@app.get("/summary", tags=["Info"], response_model=ScrapeSummary)
def summary():
    if not _cache:
        raise HTTPException(status_code=503, detail="No data available yet. Try again shortly.")
    total = sum(len(p.tariffs) for p in _cache.values())
    return ScrapeSummary(
        total_providers=len(_cache),
        total_tariff_entries=total,
        scraped_at=_last_refresh or datetime.now(timezone.utc),
        providers=list(_cache.keys()),
    )


@app.get("/tariffs", tags=["Tariffs"])
def get_all_tariffs(
    kva: Optional[int] = Query(None, description="Filtrer par puissance souscrite (kVA)"),
    provider: Optional[str] = Query(None, description="Filtrer par slug de fournisseur"),
) -> List[Dict[str, Any]]:
    if not _cache:
        raise HTTPException(status_code=503, detail="No data available yet. Try again shortly.")

    entries: List[TariffEntry] = []
    for slug, pdata in _cache.items():
        if provider and slug != provider:
            continue
        entries.extend(pdata.tariffs)

    if kva is not None:
        entries = [e for e in entries if e.kva == kva]

    return [e.model_dump() for e in entries]


@app.get("/tariffs/{slug}", tags=["Tariffs"], response_model=ProviderTariffs)
def get_provider_tariffs(
    slug: str,
    kva: Optional[int] = Query(None, description="Filtrer par puissance souscrite (kVA)"),
    option: Optional[str] = Query(None, description="Filtrer par option tarifaire (ex: Base, HP, HC)"),
):
    if slug not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{slug}' not found.")
    if slug not in _cache:
        raise HTTPException(status_code=503, detail="Data not yet available. Try again shortly.")

    pdata = _cache[slug]
    tariffs = pdata.tariffs

    if kva is not None:
        tariffs = [t for t in tariffs if t.kva == kva]
    if option is not None:
        tariffs = [t for t in tariffs if option.lower() in t.option.lower()]

    return ProviderTariffs(
        provider=pdata.provider,
        slug=pdata.slug,
        source_url=pdata.source_url,
        scraped_at=pdata.scraped_at,
        tariffs=tariffs,
    )


@app.get("/tariffs/{slug}/offers", tags=["Tariffs"])
def get_provider_offers(slug: str) -> List[Dict[str, Any]]:
    if slug not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{slug}' not found.")
    if slug not in _cache:
        raise HTTPException(status_code=503, detail="Data not yet available. Try again shortly.")

    seen = {}
    for t in _cache[slug].tariffs:
        key = (t.offer_name, t.option)
        if key not in seen:
            seen[key] = {
                "offer_name": t.offer_name,
                "option": t.option,
                "kwh_types": list(t.kwh_prix.keys()),
            }
    return list(seen.values())


@app.post("/refresh", tags=["Admin"])
def refresh_all():
    _do_refresh_all()
    return {"status": "ok", "providers_refreshed": len(_cache), "scraped_at": _last_refresh}


@app.post("/refresh/{slug}", tags=["Admin"])
def refresh_one(slug: str):
    if slug not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{slug}' not found.")
    data = _do_refresh_one(slug)
    if not data:
        raise HTTPException(status_code=502, detail=f"Failed to scrape provider '{slug}'.")
    return {
        "status": "ok",
        "provider": slug,
        "tariff_entries": len(data.tariffs),
        "scraped_at": data.scraped_at,
    }