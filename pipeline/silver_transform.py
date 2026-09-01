"""
pipeline/silver_transform.py
=============================
Étape Silver (nettoyage) : Bronze → Silver.

Transformations appliquées :
  1. Normalisation des villes          (10 formes → standard)
  2. Normalisation des titres de poste → 12 profils IT standard
  3. Normalisation des salaires        (MAD / EUR / K-notation → float MAD)
  4. Normalisation de l'expérience     (texte → int min/max années)
  5. Normalisation des contrats        (variantes → CDI/CDD/Freelance/Stage/Alternance)
  6. Validation et correction des dates

Format de sortie : Parquet (Snappy) dans silver/offres_clean/offres_clean.parquet
"""

import re
import json
from pathlib import Path

import pandas as pd

from pipeline.utils import normaliser_ville, normaliser_contrat, valider_dates


# ─────────────────────────────────────────────────────────────────────────────
#  Chargement depuis Bronze
# ─────────────────────────────────────────────────────────────────────────────

def charger_depuis_bronze(data_lake_root: str) -> pd.DataFrame:
    """
    Charge et consolide toutes les offres depuis la zone Bronze.
    Parcourt récursivement tous les fichiers offres_raw.json.

    Retourne : DataFrame pandas (5 000 lignes, colonnes brutes)
    """
    all_offres = []
    bronze_path = Path(data_lake_root) / "bronze"

    for json_file in sorted(bronze_path.rglob("offres_raw.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_offres.extend(data.get("offres", []))

    df = pd.DataFrame(all_offres)
    print(f"[SILVER] {len(df)} offres chargées depuis Bronze")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  1. Normalisation des titres de poste → profils
# ─────────────────────────────────────────────────────────────────────────────

def nettoyer_titres_postes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise les intitulés de poste en familles de profils IT.

    Règle métier : un titre est normalisé vers le profil le plus proche.
    Les titres non reconnus reçoivent le flag 'Autre IT'.

    Exemples :
      "Data Eng."           → "Data Engineer"
      "Ingénieur Big Data"  → "Data Engineer"
      "Dev Data"            → "Data Engineer"
      "Développeur BI"      → "Data Analyst"
      "ML Engineer"         → "Data Scientist"
    """
    mapping_profils = {
        # Data Engineering
        r"data\s*eng(ineer|ineer\w*|\.)?|ingénieur\s+data|dev\s+data\b|ingenieur\s+data":
            "Data Engineer",
        r"etl\s*(dev|developer|engineer)|pipeline\s*(dev|engineer)|ingénieur\s+etl":
            "Data Engineer",
        r"big\s*data\s*(eng|engineer|dev)":
            "Data Engineer",

        # Data Analysis / BI
        r"data\s*anal(yst|yste|ytics)|analyste?\s*data|bi\s*anal":
            "Data Analyst",
        r"business\s*intel(ligence)?|ingénieur\s*bi|développeur\s*bi|dev(eloppeur)?\s*bi":
            "Data Analyst",
        r"reporting\s*(anal|spec|officer)":
            "Data Analyst",

        # Data Science
        r"data\s*sci(entist|ence)|machine\s*learn|ml\s*(eng|engineer)|ia\s*(eng|engineer)":
            "Data Scientist",
        r"deep\s*learn|nlp\s*(eng|engineer)|computer\s*vision":
            "Data Scientist",

        # Full Stack
        r"full[\s\-]*stack|fullstack":
            "Développeur Full Stack",

        # Backend
        r"back[\s\-]*end\b|backend":
            "Développeur Backend",

        # Frontend
        r"front[\s\-]*end\b|frontend":
            "Développeur Frontend",

        # Mobile
        r"développeur\s+mobile|mobile\s+developer|ios\s+dev|android\s+dev":
            "Développeur Mobile",

        # DevOps / SRE
        r"devops|sre\b|site\s*reliab":
            "DevOps / SRE",

        # Cloud
        r"cloud\s*(arch|eng|admin|engineer)|aws\s+eng|gcp\s+eng|azure\s+eng":
            "Cloud Engineer",

        # Cybersécurité
        r"cyber|sécurité\s+info|securite\s+info|pentester|soc\s+anal":
            "Cybersécurité",

        # Chef de Projet
        r"chef\s+de\s+proj(et)?|project\s+man(ager)?|scrum\s*master":
            "Chef de Projet IT",

        # Architecte
        r"architect(e)?\s+(log|tech|data|cloud|sol|solutions?)":
            "Architecte IT",

        # Admin Systèmes
        r"sys(admin|tème|teme)|réseau|network\s+eng|admin\s+sys":
            "Admin Systèmes & Réseaux",
    }

    nb_avant = len(df)
    df = df.copy()
    df["profil_normalise"] = "Autre IT"
    df["_titre_lower"]     = df["titre_poste"].fillna("").str.lower().str.strip()

    for pattern, profil in mapping_profils.items():
        masque = df["_titre_lower"].str.contains(pattern, regex=True, na=False)
        df.loc[masque, "profil_normalise"] = profil

    df.drop(columns=["_titre_lower"], inplace=True)

    non_classes = (df["profil_normalise"] == "Autre IT").sum()
    print(f"[SILVER] Titres normalisés : {non_classes} offres classées 'Autre IT' "
          f"sur {nb_avant} ({non_classes / nb_avant * 100:.1f}%)")
    print(f"[SILVER] Répartition profils :")
    for profil, cnt in (
        df["profil_normalise"]
        .value_counts()
        .head(8)
        .items()
    ):
        print(f"         • {profil:<35s}: {cnt:5d}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  2. Normalisation des salaires
# ─────────────────────────────────────────────────────────────────────────────

TAUX_EUR_MAD = 10.8   # taux fixe 2024


def normaliser_salaires(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait et normalise les salaires en MAD mensuel brut.

    Règles :
      - Fourchettes → extraire min et max, calculer médiane
      - "K" → multiplier par 1 000
      - EUR → convertir en MAD (taux fixe 1 EUR = 10.8 MAD pour 2024)
      - "Selon profil", "Confidentiel", null → salaire_connu = False
      - Cohérence : salaires IT Maroc entre 3 000 et 100 000 MAD

    Nouvelles colonnes : salaire_min_mad, salaire_max_mad,
                         salaire_median_mad, salaire_connu
    """

    def parser_salaire(valeur):
        """Retourne (sal_min, sal_max, salaire_connu)."""
        if pd.isna(valeur) or str(valeur).lower() in [
            "null", "confidentiel", "selon profil",
            "selon experience", "non précisé", "à négocier", "",
        ]:
            return None, None, False

        s = str(valeur).lower().replace(" ", "").replace("\u202f", "").replace(",", ".")

        # Détecter EUR
        est_eur = "eur" in s or "€" in s
        s = (
            s.replace("eur", "")
             .replace("€",   "")
             .replace("mad", "")
             .replace("dh",  "")
        )

        # Notation K → valeur numérique (ex: "15k" → "15000")
        s = re.sub(
            r"(\d+(?:\.\d+)?)k",
            lambda m: str(int(float(m.group(1)) * 1000)),
            s,
        )

        # Extraction des montants numériques
        nombres = re.findall(r"\d+(?:\.\d+)?", s)
        if not nombres:
            return None, None, False

        montants = [float(n) for n in nombres[:2]]

        # Conversion EUR → MAD
        if est_eur:
            montants = [m * TAUX_EUR_MAD for m in montants]

        if len(montants) >= 2:
            sal_min = min(montants)
            sal_max = max(montants)
        else:
            sal_min = sal_max = montants[0]

        # Vérification cohérence
        if sal_min < 3_000 or sal_max > 100_000:
            return None, None, False

        return sal_min, sal_max, True

    # Application ligne par ligne
    resultats = df["salaire_brut"].apply(
        lambda x: pd.Series(
            parser_salaire(x),
            index=["salaire_min_mad", "salaire_max_mad", "salaire_connu"],
        )
    )
    df = pd.concat([df, resultats], axis=1)
    df["salaire_median_mad"] = (df["salaire_min_mad"] + df["salaire_max_mad"]) / 2

    pct = df["salaire_connu"].mean() * 100
    print(f"[SILVER] Salaires : {pct:.1f}% des offres ont un salaire renseigné et valide "
          f"({int(df['salaire_connu'].sum())} / {len(df)})")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  3. Normalisation de l'expérience
# ─────────────────────────────────────────────────────────────────────────────

def normaliser_experience(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforme l'expérience en valeurs numériques (années min/max requises).

    Exemples :
      "3-5 ans"          → experience_min_ans=3,  experience_max_ans=5
      "3 à 5 ans"        → experience_min_ans=3,  experience_max_ans=5
      "min 3 ans"        → experience_min_ans=3,  experience_max_ans=None
      "Débutant accepté" → experience_min_ans=0,  experience_max_ans=2
      "Junior"           → experience_min_ans=0,  experience_max_ans=2
      "Senior (7+ ans)"  → experience_min_ans=7,  experience_max_ans=None
      null               → experience_min_ans=None, experience_max_ans=None
    """

    def parser_experience(valeur):
        if pd.isna(valeur):
            return None, None

        s = str(valeur).lower().strip()

        # Débutant / Junior
        if any(m in s for m in ["débutant", "debutant", "junior", "stage",
                                  "sans expérience", "0-1"]):
            return 0, 2

        # Senior confirmé / Expert
        if any(m in s for m in ["senior confirmé", "expert", "8+"]):
            return 8, None

        # Senior générique
        if any(m in s for m in ["senior", "confirmé", "lead", "5+"]):
            return 5, None

        # Fourchette : "3-5 ans", "3 à 5 ans", "3/5 ans"
        fourchette = re.search(r"(\d+)\s*[-àa/]\s*(\d+)", s)
        if fourchette:
            return int(fourchette.group(1)), int(fourchette.group(2))

        # Minimum seul : "min 3 ans", "3+ ans", "3 ans"
        min_seul = re.search(r"(\d+)\s*(?:\+|ans?|years?)", s)
        if min_seul:
            return int(min_seul.group(1)), None

        return None, None

    resultats = df["experience_requise"].apply(
        lambda x: pd.Series(
            parser_experience(x),
            index=["experience_min_ans", "experience_max_ans"],
        )
    )
    df = pd.concat([df, resultats], axis=1)

    parsees = df["experience_min_ans"].notna().sum()
    print(f"[SILVER] Expérience : {parsees}/{len(df)} valeurs parsées "
          f"({parsees / len(df) * 100:.1f}%)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  4 & 5. Normalisation villes + contrats + dates  (via utils)
# ─────────────────────────────────────────────────────────────────────────────

def normaliser_villes_contrats_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique les normalisations de villes, contrats et dates.
    Utilise les fonctions partagées de pipeline/utils.py.
    """
    df = df.copy()

    # Villes
    villes_std = df["ville"].apply(normaliser_ville)
    df["ville_std"]    = villes_std.apply(lambda x: x[0])
    df["region_admin"] = villes_std.apply(lambda x: x[1])

    inconnues = (df["ville_std"] == "Inconnue").sum()
    print(f"[SILVER] Villes : {len(df) - inconnues}/{len(df)} reconnues "
          f"({(len(df) - inconnues) / len(df) * 100:.1f}%)")

    # Contrats
    df["type_contrat_std"] = df["type_contrat"].apply(normaliser_contrat)

    # Dates
    dates_info = df.apply(
        lambda row: pd.Series(
            valider_dates(row.get("date_publication"), row.get("date_expiration"))
        ),
        axis=1,
    )
    df = pd.concat([df, dates_info], axis=1)

    incoherentes = (~df["date_coherente"]).sum()
    print(f"[SILVER] Dates : {incoherentes} dates incohérentes détectées "
          f"(date_expiration ≤ date_publication) → flaggées")

    return df


# ─────────────────────────────────────────────────────────────────────────────
#  Sauvegarde Silver au format Parquet
# ─────────────────────────────────────────────────────────────────────────────

def sauvegarder_silver_offres(df: pd.DataFrame, data_lake_root: str) -> str:
    """
    Sauvegarde les offres nettoyées au format Parquet (Snappy).

    Chemin de sortie : silver/offres_clean/offres_clean.parquet
    """
    silver_path = Path(data_lake_root) / "silver" / "offres_clean"
    silver_path.mkdir(parents=True, exist_ok=True)

    chemin = silver_path / "offres_clean.parquet"

    # Conversion des colonnes liste en string (Parquet ne supporte pas list nativement)
    df_out = df.copy()
    if "langue_requise" in df_out.columns:
        df_out["langue_requise"] = df_out["langue_requise"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x or "")
        )

    df_out.to_parquet(chemin, index=False, compression="snappy")
    taille_ko = chemin.stat().st_size // 1024
    print(f"[SILVER] offres_clean.parquet sauvegardé → {chemin} ({taille_ko} Ko)")
    return str(chemin)


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline Silver complet
# ─────────────────────────────────────────────────────────────────────────────

def transformer_silver(data_lake_root: str) -> pd.DataFrame:
    """
    Pipeline complet Bronze → Silver.
    Enchaîne toutes les transformations et retourne le DataFrame nettoyé.
    """
    print(f"\n{'='*60}")
    print("[SILVER] Début transformation Bronze → Silver")
    print(f"{'='*60}")

    df = charger_depuis_bronze(data_lake_root)
    nb_initial = len(df)

    df = nettoyer_titres_postes(df)
    df = normaliser_salaires(df)
    df = normaliser_experience(df)
    df = normaliser_villes_contrats_dates(df)

    print(f"\n[SILVER] Bilan : {nb_initial} offres en entrée → {len(df)} en sortie")
    return df


if __name__ == "__main__":
    df_clean = transformer_silver("data_lake_mexora_rh")
    sauvegarder_silver_offres(df_clean, "data_lake_mexora_rh")
    print("[SILVER] Transformation terminée.\n")