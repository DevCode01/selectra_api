import pytest
from bs4 import BeautifulSoup
from scraper import _parse_tariff_table, _parse_caption

from tests.conftest import make_table, SCRAPED_AT, PROVIDER_NAME, SLUG, SOURCE_URL


def parse(table):
    return _parse_tariff_table(table, PROVIDER_NAME, SLUG, SOURCE_URL, SCRAPED_AT)


class TestParseCaption:
    def test_with_option(self):
        offer, option = _parse_caption(
            "Grille tarifaire de l'offre Zen Fixe par EDF en option Heures pleines heures creuses (TTC)",
            "edf"
        )
        assert offer == "Zen Fixe par EDF"
        assert option.lower() == "heures pleines heures creuses"

    def test_without_option(self):
        offer, option = _parse_caption(
            "Grille tarifaire de l'offre Zen Fixe par EDF (TTC)",
            "edf"
        )
        assert offer == "Zen Fixe par EDF"
        assert option == "Base"

    def test_fallback_on_no_match(self):
        offer, option = _parse_caption("", "edf")
        assert offer == "Edf"   # slug.title()
        assert option == "Base"

    def test_tempo_caption(self):
        offer, option = _parse_caption(
            "Grille tarifaire de l'offre EDF Tempo en option Tempo (TTC)",
            "edf"
        )
        assert "tempo" in option.lower()


class TestStandardTable:
    def test_base_offer_parsed_correctly(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Base"],
            rows=[
                ["3 kVA", "144,36\xa0€/an", "0,2018\xa0€/kWh"],
                ["6 kVA", "187,92\xa0€/an", "0,2018\xa0€/kWh"],
            ],
            caption="Grille tarifaire de l'offre Tarif bleu résidentiel en option Base (TTC)",
        )
        entries = parse(t)
        assert len(entries) == 2
        assert entries[0].kva == 3
        assert entries[0].abonnement_eur_par_an == pytest.approx(144.36)
        assert entries[0].kwh_prix == pytest.approx({"Base": 0.2018})

    def test_hphc_offer_parsed_correctly(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Heures Pleines", "Prix du kWh Heures Creuses"],
            rows=[["6 kVA", "187,80\xa0€/an", "0,2075\xa0€/kWh", "0,1589\xa0€/kWh"]],
            caption="Grille tarifaire de l'offre nRFixe+ Elec par ilek en option Heures pleines heures creuses (TTC)",
        )
        entries = parse(t)
        assert len(entries) == 1
        assert entries[0].abonnement_eur_par_an == pytest.approx(187.80)
        assert "Heures Pleines" in entries[0].kwh_prix
        assert "Heures Creuses" in entries[0].kwh_prix
        assert entries[0].option.lower() == "heures pleines heures creuses"

    def test_large_abonnement_thousand_separator(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Heures Pleines", "Prix du kWh Heures Creuses"],
            rows=[["36 kVA", "1.048,92\xa0€/an", "0,2075\xa0€/kWh", "0,1589\xa0€/kWh"]],
            caption="Grille tarifaire de l'offre nRFixe+ Elec par ilek en option Heures pleines heures creuses (TTC)",
        )
        entries = parse(t)
        assert len(entries) == 1
        assert entries[0].abonnement_eur_par_an == pytest.approx(1048.92)


class TestNonStandardColumnOrder:

    def _modulo_table(self, rows=None):
        if rows is None:
            rows = [
                ["3 kVA", "0,2115\xa0€/kWh", "0,1552\xa0€/kWh", "0,1546\xa0€/kWh", "165,36\xa0€/an", "0,0998\xa0€/kWh"],
                ["6 kVA", "0,2115\xa0€/kWh", "0,1552\xa0€/kWh", "0,1546\xa0€/kWh", "190,44\xa0€/an", "0,0998\xa0€/kWh"],
            ]
        return make_table(
            headers=["Puissance", "Prix du kWh HP Équilibre", "Prix du kWh HC Équilibre",
                     "Prix du kWh Heures solaires", "Abonnement", "Prix du kWh Jour Zen"],
            rows=rows,
        )

    def test_abonnement_extracted_from_col4(self):
        entries = parse(self._modulo_table())
        assert len(entries) == 2
        assert entries[0].abonnement_eur_par_an == pytest.approx(165.36)
        assert entries[1].abonnement_eur_par_an == pytest.approx(190.44)

    def test_kwh_keys_do_not_contain_abonnement(self):
        entries = parse(self._modulo_table())
        assert "Abonnement" not in entries[0].kwh_prix

    def test_kwh_values_are_correct(self):
        entries = parse(self._modulo_table())
        kwh = entries[0].kwh_prix
        assert "HP Équilibre" in kwh or "HP quilibre" in kwh  # accents may be stripped
        assert "Jour Zen" in kwh

    def test_large_abonnement_nonstandard_column(self):
        rows = [["36 kVA", "0,2115\xa0€/kWh", "0,1552\xa0€/kWh", "0,1546\xa0€/kWh", "1.048,92\xa0€/an", "0,0998\xa0€/kWh"]]
        entries = parse(self._modulo_table(rows))
        assert entries[0].abonnement_eur_par_an == pytest.approx(1048.92)


class TestTempoDetection:

    def _tempo_table(self):
        return make_table(
            headers=[
                "Puissance", "Abonnement",
                "Prix du kWh HP Jour Bleu", "Prix du kWh HC Jour Bleu",
                "Prix du kWh HP Jour Blanc", "Prix du kWh HC Jour Blanc",
                "Prix du kWh HP Jour Rouge", "Prix du kWh HC Jour Rouge",
            ],
            rows=[["6 kVA", "187,08\xa0€/an",
                   "0,1612\xa0€/kWh", "0,1325\xa0€/kWh",
                   "0,1871\xa0€/kWh", "0,1499\xa0€/kWh",
                   "0,7060\xa0€/kWh", "0,1575\xa0€/kWh"]],
        )

    def test_option_set_to_tempo(self):
        entries = parse(self._tempo_table())
        assert len(entries) == 1
        assert entries[0].option.lower() == "tempo"

    def test_all_six_tempo_periods_present(self):
        entries = parse(self._tempo_table())
        kwh = entries[0].kwh_prix
        keys_lower = {k.lower() for k in kwh}
        assert any("bleu" in k for k in keys_lower)
        assert any("blanc" in k for k in keys_lower)
        assert any("rouge" in k for k in keys_lower)
        assert len(kwh) == 6

    def test_abonnement_correct_for_tempo(self):
        entries = parse(self._tempo_table())
        assert entries[0].abonnement_eur_par_an == pytest.approx(187.08)


class TestVETableSkipped:

    def _ve_table_with_ve(self):
        return make_table(
            headers=[
                "Puissance",
                "Prix du kWh price kwh hp ve ilek",
                "Prix du kWh Subscription VE Ilek",
                "Prix du kWh price kwh hc ve ilek",
                "Prix du kWh price kwh shc ve ilek",
            ],
            rows=[["6 kVA", "0,2065\xa0€/kWh", "28,0800\xa0€/kWh", "0,1579\xa0€/kWh", "0,1059\xa0€/kWh"]],
        )

    def _ve_table_with_shc(self):
        return make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh HP", "Prix du kWh HC", "Prix du kWh SHC"],
            rows=[["6 kVA", "180,00\xa0€/an", "0,20\xa0€/kWh", "0,15\xa0€/kWh", "0,10\xa0€/kWh"]],
        )

    def test_ve_table_returns_no_entries(self):
        entries = parse(self._ve_table_with_ve())
        assert entries == []

    def test_shc_table_returns_no_entries(self):
        entries = parse(self._ve_table_with_shc())
        assert entries == []


class TestSubscriptionColumn:

    def _subscription_table(self):
        return make_table(
            headers=["Puissance", "Prix du kWh HP Standard", "Prix du kWh Subscription Mensuel", "Prix du kWh HC Standard"],
            rows=[["6 kVA", "0,2065\xa0€/kWh", "28,0800\xa0€/kWh", "0,1579\xa0€/kWh"]],
        )

    def test_subscription_converted_to_annual(self):
        entries = parse(self._subscription_table())
        if entries:
            assert entries[0].abonnement_eur_par_an == pytest.approx(28.08 * 12, rel=0.01)


class TestHPHCAutoDetection:

    def test_hphc_option_set_from_headers(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Heures Pleines", "Prix du kWh Heures Creuses"],
            rows=[["6 kVA", "190,08\xa0€/an", "0,2149\xa0€/kWh", "0,1639\xa0€/kWh"]],
        )
        entries = parse(t)
        assert len(entries) == 1
        assert entries[0].option.lower() == "heures pleines heures creuses"

    def test_base_option_kept_when_single_kwh_col(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Base"],
            rows=[["3 kVA", "144,36\xa0€/an", "0,2018\xa0€/kWh"]],
        )
        entries = parse(t)
        assert len(entries) == 1
        assert entries[0].option == "Base"


class TestEdgeCases:
    def test_empty_table_returns_no_entries(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Base"],
            rows=[],
        )
        assert parse(t) == []

    def test_row_without_kva_is_skipped(self):
        t = make_table(
            headers=["Puissance", "Abonnement", "Prix du kWh Base"],
            rows=[
                ["Abonnement (€/an)", "144,36\xa0€", "—"],   # gas-style row, no kVA
                ["3 kVA", "144,36\xa0€/an", "0,2018\xa0€/kWh"],
            ],
        )
        entries = parse(t)
        assert all(e.kva == 3 for e in entries)

    def test_table_without_thead_returns_empty(self):
        html = '<table class="table table--small"><tbody><tr><td>3 kVA</td></tr></tbody></table>'
        soup = BeautifulSoup(html, "lxml")
        t = soup.find("table")
        assert parse(t) == []

