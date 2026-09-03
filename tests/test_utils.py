"""
tests/test_utils.py
====================
Tests unitaires pour pipeline/utils.py — fonctions de normalisation
partagées (villes, contrats, dates).
"""

import pytest
from pipeline.utils import normaliser_ville, normaliser_contrat, valider_dates


# ── normaliser_ville ────────────────────────────────────────────────────────

class TestNormaliserVille:

    def test_forme_standard(self):
        assert normaliser_ville("Casablanca") == ("Casablanca", "Casablanca-Settat")

    def test_abreviation(self):
        assert normaliser_ville("casa") == ("Casablanca", "Casablanca-Settat")

    def test_insensible_a_la_casse(self):
        assert normaliser_ville("CASABLANCA") == ("Casablanca", "Casablanca-Settat")

    def test_variante_compose(self):
        # "Tanger-Med" doit être reconnu comme Tanger
        ville, region = normaliser_ville("Tanger-Med")
        assert ville == "Tanger"
        assert region == "Tanger-Tétouan-Al Hoceïma"

    def test_ville_inconnue(self):
        ville, region = normaliser_ville("Atlantis")
        assert ville == "Atlantis"       # conservée telle quelle (title-case)
        assert region == "Inconnue"

    def test_valeur_vide(self):
        assert normaliser_ville("") == ("Inconnue", "Inconnue")

    def test_valeur_none(self):
        assert normaliser_ville(None) == ("Inconnue", "Inconnue")

    def test_accents_fes(self):
        ville, region = normaliser_ville("FEZ")
        assert ville == "Fès"


# ── normaliser_contrat ──────────────────────────────────────────────────────

class TestNormaliserContrat:

    def test_cdi_direct(self):
        assert normaliser_contrat("cdi") == "CDI"

    def test_cdi_texte_long(self):
        assert normaliser_contrat("Contrat à durée indéterminée") == "CDI"

    def test_cdd(self):
        assert normaliser_contrat("CDD 6 mois") == "CDD"

    def test_freelance(self):
        assert normaliser_contrat("Mission freelance") == "Freelance"

    def test_stage(self):
        assert normaliser_contrat("Stage PFE") == "Stage"

    def test_alternance(self):
        assert normaliser_contrat("Contrat d'alternance") == "Alternance"

    def test_valeur_non_reconnue(self):
        assert normaliser_contrat("xyz inconnu") == "Non précisé"

    def test_valeur_vide(self):
        assert normaliser_contrat("") == "Non précisé"

    def test_valeur_none(self):
        assert normaliser_contrat(None) == "Non précisé"


# ── valider_dates ────────────────────────────────────────────────────────────

class TestValiderDates:

    def test_dates_coherentes(self):
        res = valider_dates("2024-01-01", "2024-02-01")
        assert res["date_coherente"] is True
        assert res["annee"] == "2024"
        assert res["mois"] == "01"

    def test_dates_incoherentes_expiration_avant_publication(self):
        res = valider_dates("2024-02-01", "2024-01-01")
        assert res["date_coherente"] is False

    def test_dates_egales_incoherentes(self):
        # règle stricte : expiration doit être > publication
        res = valider_dates("2024-01-01", "2024-01-01")
        assert res["date_coherente"] is False

    def test_expiration_manquante(self):
        res = valider_dates("2024-01-01", None)
        assert res["date_coherente"] is True  # pas de comparaison possible
        assert res["date_expiration_std"] is None

    def test_publication_invalide(self):
        res = valider_dates("date-invalide", "2024-01-01")
        assert res["date_publication_std"] is None
        assert res["date_coherente"] is True
