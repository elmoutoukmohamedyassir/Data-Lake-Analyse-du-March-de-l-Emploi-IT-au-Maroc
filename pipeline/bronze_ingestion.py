"""
pipeline/bronze_ingestion.py
============================
Étape Bronze : ingestion brute des offres d'emploi.

Principe fondamental : la zone Bronze est IMMUABLE.
On ne modifie JAMAIS les données une fois chargées en Bronze.
C'est l'archive fidèle de ce qui a été reçu — en cas d'erreur de
transformation Silver, on peut toujours rejouer depuis Bronze.

Partitionnement : bronze/{source}/{YYYY_MM}/offres_raw.json
  - par source : rekrute / marocannonce / linkedin
  - par mois   : permet de rejouer un mois sans toucher les autres
"""

import json
import os
from datetime import datetime
from pathlib import Path


def ingerer_bronze(filepath_source: str, data_lake_root: str) -> dict:
    """
    Charge les données brutes dans la zone Bronze sans aucune modification.
    Partitionne par source et par mois de publication.

    Paramètres
    ----------
    filepath_source : chemin vers offres_emploi_it_maroc.json
    data_lake_root  : chemin racine du Data Lake (ex: "data_lake_mexora_rh")

    Retourne
    --------
    dict de statistiques : total, par_source, par_mois, nb_fichiers
    """
    print(f"\n{'='*60}")
    print(f"[BRONZE] Début ingestion : {filepath_source}")
    print(f"{'='*60}")

    with open(filepath_source, "r", encoding="utf-8") as f:
        data = json.load(f)

    offres = data.get("offres", [])
    stats = {
        "total":       len(offres),
        "par_source":  {},
        "par_mois":    {},
        "nb_fichiers": 0,
        "date_ingestion": datetime.now().isoformat(),
    }

    # ── Partitionnement par source et par mois ────────────────────────────
    partitions = {}
    for offre in offres:
        source   = offre.get("source", "inconnu").lower().replace(" ", "_")
        date_pub = offre.get("date_publication", "")

        try:
            mois_partition = datetime.strptime(date_pub[:7], "%Y-%m").strftime("%Y_%m")
        except (ValueError, TypeError):
            mois_partition = "date_inconnue"

        cle = f"{source}/{mois_partition}"
        if cle not in partitions:
            partitions[cle] = []
        partitions[cle].append(offre)

    # ── Écriture dans Bronze (données BRUTES, non modifiées) ─────────────
    for partition, offres_partition in partitions.items():
        chemin_dir = os.path.join(data_lake_root, "bronze", partition)
        os.makedirs(chemin_dir, exist_ok=True)

        chemin_fichier = os.path.join(chemin_dir, "offres_raw.json")
        with open(chemin_fichier, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "source_fichier":  filepath_source,
                        "date_ingestion":  datetime.now().isoformat(),
                        "partition":       partition,
                        "nb_offres":       len(offres_partition),
                        "schema_version":  "1.0",
                    },
                    "offres": offres_partition,   # ← AUCUNE modification
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        stats["nb_fichiers"] += 1
        source_nom = partition.split("/")[0]
        mois_nom   = partition.split("/")[1]
        stats["par_source"][source_nom] = (
            stats["par_source"].get(source_nom, 0) + len(offres_partition)
        )
        stats["par_mois"][mois_nom] = (
            stats["par_mois"].get(mois_nom, 0) + len(offres_partition)
        )

    # ── Rapport d'ingestion ───────────────────────────────────────────────
    print(f"[BRONZE] {stats['total']} offres ingérées dans {stats['nb_fichiers']} partitions")
    print(f"[BRONZE] Répartition par source :")
    for src, cnt in sorted(stats["par_source"].items()):
        pct = cnt / stats["total"] * 100
        print(f"         • {src:<20s} : {cnt:5d} offres ({pct:.1f}%)")
    print(f"[BRONZE] Période couverte : {len(stats['par_mois'])} mois")

    # Sauvegarde du rapport dans bronze/
    rapport_path = os.path.join(data_lake_root, "bronze", "_ingestion_report.json")
    with open(rapport_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


def lister_partitions_bronze(data_lake_root: str) -> list:
    """Liste toutes les partitions disponibles en zone Bronze."""
    bronze_path = Path(data_lake_root) / "bronze"
    return sorted(str(p) for p in bronze_path.rglob("offres_raw.json"))


if __name__ == "__main__":
    stats = ingerer_bronze(
        filepath_source="data/raw/offres_emploi_it_maroc.json",
        data_lake_root="data_lake_mexora_rh",
    )
    partitions = lister_partitions_bronze("data_lake_mexora_rh")
    print(f"\n[BRONZE] {len(partitions)} fichiers de partition créés.")
    print("[BRONZE] Ingestion terminée avec succès.\n")