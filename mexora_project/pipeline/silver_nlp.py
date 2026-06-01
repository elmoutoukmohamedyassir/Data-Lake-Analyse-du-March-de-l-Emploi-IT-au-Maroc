"""
pipeline/silver_nlp.py
=======================
Étape Silver (NLP) : extraction des compétences IT depuis texte libre.

C'est la transformation la plus importante et la plus originale du projet.
Elle transforme du texte non structuré en données structurées exploitables.

Stratégie :
  1. Charger le référentiel de compétences (alias → nom normalisé, famille)
  2. Pour chaque offre, concaténer 'competences_brut' + 'description'
  3. Matching regex word-boundary sur chaque alias (trié longueur décroissante
     pour éviter les faux positifs : "node.js" avant "node")
  4. Chaque offre produit N lignes (une par compétence détectée)

Format de sortie : Parquet (Snappy) dans silver/competences_extraites/competences.parquet
"""

import re
import json
from pathlib import Path

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
#  Chargement du référentiel
# ─────────────────────────────────────────────────────────────────────────────

def charger_referentiel(referentiel_path: str) -> tuple:
    """
    Charge le référentiel de compétences et construit :
      - dict_competences : alias (str) → {"competence": str, "famille": str}
      - aliases_tries    : liste triée par longueur décroissante

    Le tri décroissant est crucial pour éviter les faux positifs :
      "scikit-learn" doit être détecté avant "scikit"
      "node.js"      doit être détecté avant "node"
      "apache spark" doit être détecté avant "spark"
    """
    with open(referentiel_path, "r", encoding="utf-8") as f:
        referentiel = json.load(f)

    dict_competences = {}
    for famille, competences in referentiel["familles"].items():
        for nom_normalise, aliases in competences.items():
            for alias in aliases:
                dict_competences[alias.lower()] = {
                    "competence": nom_normalise,
                    "famille":    famille,
                }

    # Tri par longueur décroissante → priorité aux alias longs
    aliases_tries = sorted(dict_competences.keys(), key=len, reverse=True)

    nb_familles   = len(referentiel["familles"])
    nb_competences = len({v["competence"] for v in dict_competences.values()})
    print(f"[NLP] Référentiel chargé : {len(dict_competences)} aliases, "
          f"{nb_competences} compétences, {nb_familles} familles")

    return dict_competences, aliases_tries


# ─────────────────────────────────────────────────────────────────────────────
#  Extraction pour une offre
# ─────────────────────────────────────────────────────────────────────────────

def _extraire_competences_offre(
    offre: pd.Series,
    dict_competences: dict,
    aliases_tries: list,
) -> list:
    """
    Extrait les compétences d'une offre depuis deux sources de texte :
      1. 'competences_brut' : liste semi-structurée (séparateurs incohérents)
      2. 'description'      : texte libre — plus riche mais plus bruité

    Retourne une liste de dicts (une entrée par compétence détectée).
    Si aucune compétence n'est trouvée, retourne une ligne 'non_détecté'.
    """
    # Concaténation des deux sources
    texte = " ".join(
        filter(
            None,
            [
                str(offre.get("competences_brut") or ""),
                str(offre.get("description")      or ""),
            ],
        )
    ).lower()

    competences_trouvees = set()
    resultats = []

    for alias in aliases_tries:
        # Word boundary : évite "spark" dans "sparkasse", "java" dans "javascript"
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, texte):
            info = dict_competences[alias]
            cle  = info["competence"]
            if cle not in competences_trouvees:
                competences_trouvees.add(cle)
                resultats.append(
                    {
                        "id_offre":    offre["id_offre"],
                        "profil":      offre.get("profil_normalise"),
                        "ville":       offre.get("ville_std"),
                        "competence":  info["competence"],
                        "famille":     info["famille"],
                        "date_pub":    offre.get("date_publication"),
                        "annee":       str(offre.get("date_publication", ""))[:4],
                        "mois":        str(offre.get("date_publication", ""))[5:7],
                        "type_contrat":offre.get("type_contrat_std"),
                        "salaire_connu":offre.get("salaire_connu", False),
                    }
                )

    # Offre sans aucune compétence détectée → ligne de traçage
    if not competences_trouvees:
        resultats.append(
            {
                "id_offre":    offre["id_offre"],
                "profil":      offre.get("profil_normalise"),
                "ville":       offre.get("ville_std"),
                "competence":  "non_détecté",
                "famille":     "inconnu",
                "date_pub":    offre.get("date_publication"),
                "annee":       str(offre.get("date_publication", ""))[:4],
                "mois":        str(offre.get("date_publication", ""))[5:7],
                "type_contrat":offre.get("type_contrat_std"),
                "salaire_connu":offre.get("salaire_connu", False),
            }
        )

    return resultats


# ─────────────────────────────────────────────────────────────────────────────
#  Extraction sur tout le DataFrame Silver
# ─────────────────────────────────────────────────────────────────────────────

def extraire_competences(df: pd.DataFrame, referentiel_path: str) -> pd.DataFrame:
    """
    Lance l'extraction NLP sur toutes les offres Silver.

    Paramètres
    ----------
    df               : DataFrame Silver (offres nettoyées)
    referentiel_path : chemin vers referentiel_competences_it.json

    Retourne
    --------
    DataFrame : une ligne par (offre × compétence détectée)
    Colonnes  : id_offre, profil, ville, competence, famille,
                date_pub, annee, mois, type_contrat, salaire_connu
    """
    print(f"\n{'='*60}")
    print("[NLP] Début extraction de compétences")
    print(f"{'='*60}")

    dict_competences, aliases_tries = charger_referentiel(referentiel_path)

    tous_resultats = []
    nb_sans_comp   = 0

    for _, offre in df.iterrows():
        rows = _extraire_competences_offre(offre, dict_competences, aliases_tries)
        tous_resultats.extend(rows)
        if len(rows) == 1 and rows[0]["competence"] == "non_détecté":
            nb_sans_comp += 1

    df_competences    = pd.DataFrame(tous_resultats)
    nb_offres_avec    = len(df) - nb_sans_comp
    nb_lignes_totales = len(df_competences)

    # ── Rapport d'extraction ─────────────────────────────────────────────
    print(f"\n[NLP] ── Rapport d'extraction ──")
    print(f"  Offres analysées         : {len(df)}")
    print(f"  Offres avec compétences  : {nb_offres_avec} "
          f"({nb_offres_avec / len(df) * 100:.1f}%)")
    print(f"  Offres sans compétence   : {nb_sans_comp} "
          f"({nb_sans_comp / len(df) * 100:.1f}%)")
    print(f"  Lignes totales générées  : {nb_lignes_totales}")

    # Répartition par famille
    if not df_competences.empty:
        print(f"  Répartition par famille :")
        familles = (
            df_competences[df_competences["competence"] != "non_détecté"]
            ["famille"]
            .value_counts()
        )
        for fam, cnt in familles.items():
            print(f"    • {fam:<22s}: {cnt:6d} mentions")

    return df_competences


# ─────────────────────────────────────────────────────────────────────────────
#  Sauvegarde Silver compétences au format Parquet
# ─────────────────────────────────────────────────────────────────────────────

def sauvegarder_silver_competences(df_competences: pd.DataFrame, data_lake_root: str) -> str:
    """
    Sauvegarde les compétences extraites au format Parquet (Snappy).

    Chemin de sortie : silver/competences_extraites/competences.parquet
    """
    silver_path = Path(data_lake_root) / "silver" / "competences_extraites"
    silver_path.mkdir(parents=True, exist_ok=True)

    chemin = silver_path / "competences.parquet"
    df_competences.to_parquet(chemin, index=False, compression="snappy")

    taille_ko = chemin.stat().st_size // 1024
    print(f"\n[NLP] competences.parquet sauvegardé → {chemin} ({taille_ko} Ko, "
          f"{len(df_competences)} lignes)")
    return str(chemin)


# ─────────────────────────────────────────────────────────────────────────────
#  Point d'entrée (exécution directe)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd

    chemin_silver  = "data_lake_mexora_rh/silver/offres_clean/offres_clean.parquet"
    chemin_ref     = "data/raw/referentiel_competences_it.json"
    data_lake_root = "data_lake_mexora_rh"

    df_offres      = pd.read_parquet(chemin_silver)
    df_competences = extraire_competences(df_offres, chemin_ref)
    sauvegarder_silver_competences(df_competences, data_lake_root)
    print("[NLP] Extraction terminée.\n")