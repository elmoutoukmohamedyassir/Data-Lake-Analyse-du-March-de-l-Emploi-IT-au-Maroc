"""
tests/test_silver_transform.py
================================
Tests unitaires pour pipeline/silver_transform.py — nettoyage Bronze → Silver.
Chaque fonction est testée isolément avec un petit DataFrame construit à la main,
sans dépendre du data lake réel.
"""

import pandas as pd
import pytest

from pipeline.silver_transform import (
    nettoyer_titres_postes,
    normaliser_salaires,
    normaliser_experience,
)


# ── nettoyer_titres_postes ───────────────────────────────────────────────────

class TestNettoyerTitresPostes:

    def test_data_engineer_variantes(self):
        df = pd.DataFrame({"titre_poste": ["Data Eng.", "Ingénieur Big Data", "Dev Data"]})
        result = nettoyer_titres_postes(df)
        assert (result["profil_normalise"] == "Data Engineer").all()

    def test_data_analyst(self):
        df = pd.DataFrame({"titre_poste": ["Développeur BI"]})
        result = nettoyer_titres_postes(df)
        assert result["profil_normalise"].iloc[0] == "Data Analyst"

    def test_titre_non_reconnu(self):
        df = pd.DataFrame({"titre_poste": ["Boulanger"]})
        result = nettoyer_titres_postes(df)
        assert result["profil_normalise"].iloc[0] == "Autre IT"

    def test_titre_null(self):
        df = pd.DataFrame({"titre_poste": [None]})
        result = nettoyer_titres_postes(df)
        assert result["profil_normalise"].iloc[0] == "Autre IT"

    def test_colonne_temporaire_supprimee(self):
        # _titre_lower est une colonne de travail : elle ne doit pas fuiter en sortie
        df = pd.DataFrame({"titre_poste": ["Data Engineer"]})
        result = nettoyer_titres_postes(df)
        assert "_titre_lower" not in result.columns


# ── normaliser_salaires ──────────────────────────────────────────────────────

class TestNormaliserSalaires:

    def test_fourchette_simple(self):
        df = pd.DataFrame({"salaire_brut": ["8000-12000 MAD"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == True
        assert result["salaire_min_mad"].iloc[0] == 8000
        assert result["salaire_max_mad"].iloc[0] == 12000
        assert result["salaire_median_mad"].iloc[0] == 10000

    def test_notation_k(self):
        df = pd.DataFrame({"salaire_brut": ["15k MAD"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == True
        assert result["salaire_min_mad"].iloc[0] == 15000

    def test_conversion_eur(self):
        df = pd.DataFrame({"salaire_brut": ["1000 EUR"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == True
        # 1000 EUR * 10.8 = 10800 MAD
        assert result["salaire_min_mad"].iloc[0] == 10800

    def test_valeur_confidentielle(self):
        df = pd.DataFrame({"salaire_brut": ["Confidentiel"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == False
        assert pd.isna(result["salaire_min_mad"].iloc[0])

    def test_valeur_null(self):
        df = pd.DataFrame({"salaire_brut": [None]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == False

    def test_hors_bornes_trop_bas(self):
        # règle métier : salaire IT Maroc doit être entre 3 000 et 100 000 MAD
        df = pd.DataFrame({"salaire_brut": ["500 MAD"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == False

    def test_hors_bornes_trop_haut(self):
        df = pd.DataFrame({"salaire_brut": ["500000 MAD"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == False

    def test_limite_basse_acceptee(self):
        # cas limite : exactement 3000 doit être accepté (règle : >= 3000)
        df = pd.DataFrame({"salaire_brut": ["3000 MAD"]})
        result = normaliser_salaires(df)
        assert result["salaire_connu"].iloc[0] == True

    def test_valeur_unique_sans_fourchette(self):
        df = pd.DataFrame({"salaire_brut": ["10000 MAD"]})
        result = normaliser_salaires(df)
        assert result["salaire_min_mad"].iloc[0] == 10000
        assert result["salaire_max_mad"].iloc[0] == 10000


# ── normaliser_experience ────────────────────────────────────────────────────

class TestNormaliserExperience:

    def test_fourchette(self):
        df = pd.DataFrame({"experience_requise": ["3-5 ans"]})
        result = normaliser_experience(df)
        assert result["experience_min_ans"].iloc[0] == 3
        assert result["experience_max_ans"].iloc[0] == 5

    def test_debutant(self):
        df = pd.DataFrame({"experience_requise": ["Débutant accepté"]})
        result = normaliser_experience(df)
        assert result["experience_min_ans"].iloc[0] == 0
        assert result["experience_max_ans"].iloc[0] == 2

    def test_junior(self):
        df = pd.DataFrame({"experience_requise": ["Junior"]})
        result = normaliser_experience(df)
        assert result["experience_min_ans"].iloc[0] == 0

    def test_senior_avec_plus(self):
        df = pd.DataFrame({"experience_requise": ["Senior (7+ ans)"]})
        result = normaliser_experience(df)
        assert result["experience_min_ans"].iloc[0] == 5
        assert pd.isna(result["experience_max_ans"].iloc[0])

    def test_minimum_seul(self):
        df = pd.DataFrame({"experience_requise": ["min 3 ans"]})
        result = normaliser_experience(df)
        assert result["experience_min_ans"].iloc[0] == 3
        assert pd.isna(result["experience_max_ans"].iloc[0])

    def test_valeur_null(self):
        df = pd.DataFrame({"experience_requise": [None]})
        result = normaliser_experience(df)
        assert pd.isna(result["experience_min_ans"].iloc[0])
