"""
data_quality/validate_silver.py
=================================
Validation de la qualité des données de la couche Silver avec Great Expectations.

Principe : avant de laisser la couche Gold (agrégations/rapports) consommer
les données Silver, on vérifie qu'elles respectent un contrat de qualité
minimal. Si une vérification critique échoue, le pipeline s'arrête plutôt
que de propager des données corrompues en aval.

Usage :
    python -m data_quality.validate_silver
"""

import sys
from pathlib import Path

import pandas as pd


def valider_offres_silver(data_lake_root: str = "data_lake_mexora_rh") -> bool:
    chemin = Path(data_lake_root) / "silver" / "offres_clean" / "offres_clean.parquet"
    if not chemin.exists():
        print(f"[DQ] Fichier introuvable : {chemin} (lancer d'abord le pipeline Silver)")
        return False

    df = pd.read_parquet(chemin)

    # API "legacy" de Great Expectations (great_expectations.dataset) :
    # la plus simple pour valider un DataFrame pandas sans mise en place
    # d'un DataContext complet — suffisant pour un contrôle qualité de pipeline.
    from great_expectations.dataset import PandasDataset
    ge_df = PandasDataset(df)

    resultats = []

    # 1. Colonnes obligatoires ne doivent jamais être nulles
    resultats.append(ge_df.expect_column_values_to_not_be_null("id_offre"))
    resultats.append(ge_df.expect_column_values_to_not_be_null("titre_poste"))

    # 2. id_offre doit être unique (pas de doublons après Bronze→Silver)
    resultats.append(ge_df.expect_column_values_to_be_unique("id_offre"))

    # 3. Les salaires connus doivent respecter la règle métier (3000-100000 MAD)
    df_sal_connu = df[df["salaire_connu"] == True]
    ge_sal = PandasDataset(df_sal_connu)
    resultats.append(
        ge_sal.expect_column_values_to_be_between(
            "salaire_min_mad", min_value=3000, max_value=100000
        )
    )

    # 4. profil_normalise doit être dans la liste des profils connus
    profils_valides = [
        "Data Engineer", "Data Analyst", "Data Scientist",
        "Développeur Full Stack", "Développeur Backend", "Développeur Frontend",
        "Développeur Mobile", "DevOps / SRE", "Cloud Engineer", "Cybersécurité",
        "Chef de Projet IT", "Architecte IT", "Admin Systèmes & Réseaux", "Autre IT",
    ]
    resultats.append(ge_df.expect_column_values_to_be_in_set("profil_normalise", profils_valides))

    # 5. Le volume total ne doit pas s'effondrer anormalement (garde-fou)
    resultats.append(ge_df.expect_table_row_count_to_be_between(min_value=100))

    # ── Rapport ──────────────────────────────────────────────────────────
    nb_ok = sum(1 for r in resultats if r["success"])
    nb_total = len(resultats)
    print(f"\n{'='*60}")
    print(f"[DQ] Résultat validation Silver : {nb_ok}/{nb_total} règles passées")
    print(f"{'='*60}")

    for r in resultats:
        statut = "✓ OK" if r["success"] else "✗ ÉCHEC"
        expectation = r["expectation_config"]["expectation_type"]
        print(f"  {statut}  {expectation}")

    tout_ok = nb_ok == nb_total
    if not tout_ok:
        print("\n[DQ] ⚠️  Des règles de qualité ont échoué. Vérifier avant de lancer Gold.")
    return tout_ok


if __name__ == "__main__":
    ok = valider_offres_silver()
    sys.exit(0 if ok else 1)
