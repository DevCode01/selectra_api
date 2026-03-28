from scraper import scrape_provider

data = scrape_provider("edf")
if data:
    print("Provider:", data.provider)
    print("Total entries:", len(data.tariffs))
    for t in data.tariffs[:5]:
        print(" ", t.offer_name, "|", t.option, "| kVA:", t.kva, "| Abo:", t.abonnement_eur_par_an, "| kWh:", t.kwh_prix)
else:
    print("FAILED")

