"""
tests/test_bronze_ingestion.py
================================
Vérifie que l'ingestion Bronze est incrémentale et idempotente :
  - relancer avec le même fichier ne doit PAS créer de doublons
  - ingérer un nouveau batch doit AJOUTER les nouvelles offres sans
    perdre les précédentes
"""

import json
import tempfile
import shutil
from pathlib import Path

import pytest

from pipeline.bronze_ingestion import ingerer_bronze


def _ecrire_source(path, offres):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"offres": offres}, f)


def _lire_partition(data_lake_root, source, mois):
    chemin = Path(data_lake_root) / "bronze" / source / mois / "offres_raw.json"
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)["offres"]


@pytest.fixture
def tmp_env():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir)


def test_idempotence_meme_fichier_deux_fois(tmp_env):
    """Ingérer deux fois le même fichier ne doit pas dupliquer les offres."""
    source_path = Path(tmp_env) / "source.json"
    offres = [
        {"id_offre": "MA-001", "source": "rekrute", "date_publication": "2024-01-15"},
        {"id_offre": "MA-002", "source": "rekrute", "date_publication": "2024-01-20"},
    ]
    _ecrire_source(source_path, offres)

    ingerer_bronze(str(source_path), tmp_env)
    ingerer_bronze(str(source_path), tmp_env)  # relance identique

    resultat = _lire_partition(tmp_env, "rekrute", "2024_01")
    assert len(resultat) == 2  # toujours 2, pas 4


def test_incremental_nouveau_batch_ajoute_sans_perdre(tmp_env):
    """Un second batch avec de nouvelles offres doit s'ajouter aux anciennes."""
    source1 = Path(tmp_env) / "source1.json"
    source2 = Path(tmp_env) / "source2.json"

    _ecrire_source(source1, [
        {"id_offre": "MA-001", "source": "rekrute", "date_publication": "2024-01-15"},
    ])
    _ecrire_source(source2, [
        {"id_offre": "MA-002", "source": "rekrute", "date_publication": "2024-01-20"},
    ])

    ingerer_bronze(str(source1), tmp_env)
    ingerer_bronze(str(source2), tmp_env)

    resultat = _lire_partition(tmp_env, "rekrute", "2024_01")
    ids = {o["id_offre"] for o in resultat}
    assert ids == {"MA-001", "MA-002"}  # les deux sont présentes


def test_mise_a_jour_offre_existante(tmp_env):
    """Si une offre est ré-ingérée avec le même id mais des données modifiées,
    la nouvelle version doit remplacer l'ancienne (pas de doublon, pas de perte)."""
    source1 = Path(tmp_env) / "source1.json"
    source2 = Path(tmp_env) / "source2.json"

    _ecrire_source(source1, [
        {"id_offre": "MA-001", "source": "rekrute", "date_publication": "2024-01-15",
         "titre_poste": "Data Engineer Junior"},
    ])
    _ecrire_source(source2, [
        {"id_offre": "MA-001", "source": "rekrute", "date_publication": "2024-01-15",
         "titre_poste": "Data Engineer Senior"},  # mise à jour du titre
    ])

    ingerer_bronze(str(source1), tmp_env)
    ingerer_bronze(str(source2), tmp_env)

    resultat = _lire_partition(tmp_env, "rekrute", "2024_01")
    assert len(resultat) == 1
    assert resultat[0]["titre_poste"] == "Data Engineer Senior"
