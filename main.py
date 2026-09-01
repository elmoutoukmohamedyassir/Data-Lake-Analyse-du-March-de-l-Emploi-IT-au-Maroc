"""
main.py
=======
Orchestrateur principal du pipeline Data Lake Mexora RH.
Lance les étapes dans l'ordre : Bronze → Silver → Gold.

Usage :
    python main.py              # pipeline complet
    python main.py bronze       # ingestion Bronze seulement
    python main.py silver       # Silver (nettoyage + NLP) seulement
    python main.py gold         # Gold seulement
"""

import sys
import time
from pathlib import Path

# ── Chemins du projet ─────────────────────────────────────────────────────────
DATA_LAKE_ROOT  = "data_lake_mexora_rh"
SOURCE_FILE     = "data/raw/offres_emploi_it_maroc.json"
REFERENTIEL     = "data/raw/referentiel_competences_it.json"

# ── Création de la structure de répertoires (si pas encore faite) ─────────────
for d in [
    f"{DATA_LAKE_ROOT}/bronze",
    f"{DATA_LAKE_ROOT}/silver/offres_clean",
    f"{DATA_LAKE_ROOT}/silver/competences_extraites",
    f"{DATA_LAKE_ROOT}/gold",
    "data/raw",
]:
    Path(d).mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Étapes du pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_bronze():
    from pipeline.bronze_ingestion import ingerer_bronze
    print("\n" + "█" * 60)
    print("█  ÉTAPE 1 — BRONZE : Ingestion brute (données immuables)")
    print("█" * 60)
    t0 = time.time()
    stats = ingerer_bronze(SOURCE_FILE, DATA_LAKE_ROOT)
    print(f"\n✓ Bronze terminé en {time.time() - t0:.1f}s")
    return stats


def run_silver():
    from pipeline.silver_transform import transformer_silver, sauvegarder_silver_offres
    from pipeline.silver_nlp import extraire_competences, sauvegarder_silver_competences

    print("\n" + "█" * 60)
    print("█  ÉTAPE 2a — SILVER TRANSFORM : Nettoyage & standardisation")
    print("█" * 60)
    t0 = time.time()
    df_clean = transformer_silver(DATA_LAKE_ROOT)
    sauvegarder_silver_offres(df_clean, DATA_LAKE_ROOT)
    print(f"\n✓ Silver transform terminé en {time.time() - t0:.1f}s")

    print("\n" + "█" * 60)
    print("█  ÉTAPE 2b — SILVER NLP : Extraction de compétences")
    print("█" * 60)
    t0 = time.time()
    df_comp = extraire_competences(df_clean, REFERENTIEL)
    sauvegarder_silver_competences(df_comp, DATA_LAKE_ROOT)
    print(f"\n✓ Silver NLP terminé en {time.time() - t0:.1f}s")

    return df_clean, df_comp


def run_gold():
    from pipeline.gold_aggregation import construire_gold
    print("\n" + "█" * 60)
    print("█  ÉTAPE 3 — GOLD : Tables analytiques (DuckDB)")
    print("█" * 60)
    t0 = time.time()
    construire_gold(DATA_LAKE_ROOT)
    print(f"\n✓ Gold terminé en {time.time() - t0:.1f}s")


def run_all():
    print("\n" + "═" * 60)
    print("  MEXORA RH INTELLIGENCE — Pipeline Data Lake")
    print("  Bronze / Silver / Gold")
    print("═" * 60)

    t_start = time.time()
    run_bronze()
    run_silver()
    run_gold()
    total = time.time() - t_start

    print("\n" + "═" * 60)
    print(f"  Pipeline complet terminé en {total:.1f}s")
    print("═" * 60)

    # Résumé des fichiers produits
    print("\nFichiers produits :")
    for zone in ["bronze", "silver", "gold"]:
        zone_path = Path(DATA_LAKE_ROOT) / zone
        fichiers  = list(zone_path.rglob("*"))
        fichiers  = [f for f in fichiers if f.is_file()]
        taille_ko = sum(f.stat().st_size for f in fichiers) // 1024
        print(f"  {zone:<8s}: {len(fichiers):3d} fichiers, {taille_ko:7d} Ko")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    etape = sys.argv[1] if len(sys.argv) > 1 else "all"

    if etape == "bronze":
        run_bronze()
    elif etape == "silver":
        run_silver()
    elif etape == "gold":
        run_gold()
    elif etape == "all":
        run_all()
    else:
        print("Usage : python main.py [bronze|silver|gold|all]")
        sys.exit(1)