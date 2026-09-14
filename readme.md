# Mexora RH Intelligence — Data Lake Emploi IT Maroc

> **Mini-projet 2 | Analyse du marché de l'emploi IT marocain**
> Pipeline Bronze → Silver → Gold, orchestré par Airflow, avec contrôle qualité, tests et containerisation — sur 5 000 offres d'emploi (2023–2024)

---

## Vue d'ensemble

Ce projet construit un **Data Lake en trois zones** (Bronze / Silver / Gold) alimenté par des offres d'emploi IT marocaines issues de Rekrute, MarocAnnonce et LinkedIn. L'objectif final est de produire une analyse stratégique du marché pour guider la politique de recrutement de Mexora, une marketplace en forte croissance basée à Tanger.

**Ce que fait le pipeline, en résumé :**
- Ingère ~5 000 offres brutes et les partitionne par source et par mois (Bronze)
- Nettoie les données : villes, salaires, titres de postes, expérience, contrats (Silver)
- Extrait les compétences IT depuis le texte libre via matching regex (Silver NLP)
- **Valide la qualité des données Silver avec Great Expectations avant d'autoriser le passage en Gold**
- Calcule des agrégats analytiques : top compétences, salaires, tendances (Gold)
- Produit 5 analyses DuckDB avec visualisations et recommandations RH
- **S'orchestre automatiquement avec Airflow** (dépendances entre tâches, retries, planification quotidienne)
- **Tourne en conteneurs Docker**, avec Postgres comme backend Airflow
- Est couvert par une **suite de tests pytest** sur les couches Bronze/Silver

---

## Structure du projet

```
mexora_project/
├── pipeline/
│   ├── bronze_ingestion.py      # Chargement brut → zone Bronze (immuable)
│   ├── silver_transform.py      # Nettoyage et standardisation → Silver
│   ├── silver_nlp.py            # Extraction de compétences depuis texte libre
│   ├── gold_aggregation.py      # Calcul des agrégats → Gold (DuckDB)
│   └── utils.py                 # Fonctions partagées (normalisation villes, etc.)
├── data_quality/
│   └── validate_silver.py       # Contrôle qualité Silver (Great Expectations) — porte avant Gold
├── dags/
│   └── mexora_pipeline_dag.py   # DAG Airflow : bronze >> silver >> data_quality >> gold
├── tests/
│   ├── test_bronze_ingestion.py
│   ├── test_silver_transform.py
│   └── test_utils.py
├── analysis/
│   ├── analyse_marche_it_maroc.ipynb  # Notebook — 5 questions analytiques + interprétations
│   ├── analyse_marche.py        # 5 questions analytiques DuckDB (version script)
│   └── dashboard.py             # Génération du dashboard (4 visualisations)
├── data/
│   └── raw/
│       ├── offres_emploi_it_maroc.json       # Dataset principal (5 000 offres)
│       ├── referentiel_competences_it.json   # Référentiel 300 compétences IT
│       └── entreprises_it_maroc.csv          # Entreprises IT marocaines
├── data_lake_mexora_rh/
│   ├── bronze/                  # Données brutes partitionnées (immuables)
│   │   ├── rekrute/YYYY_MM/offres_raw.json
│   │   ├── marocannonce/YYYY_MM/offres_raw.json
│   │   └── linkedin/YYYY_MM/offres_raw.json
│   ├── silver/
│   │   ├── offres_clean/offres_clean.parquet
│   │   └── competences_extraites/competences.parquet
│   └── gold/
│       ├── top_competences.parquet
│       ├── salaires_par_profil.parquet
│       ├── offres_par_ville.parquet
│       ├── entreprises_recruteurs.parquet
│       └── tendances_mensuelles.parquet
├── generate_data.py             # Génération du jeu de données synthétiques
├── main.py                      # Orchestrateur CLI (bronze / silver / gold / all)
├── rapport_pipeline.md          # Rapport détaillé des transformations
├── Dockerfile                   # Image du pipeline
├── docker-compose.yml           # Stack complète : Postgres + Airflow webserver/scheduler
├── pytest.ini                   # Config des tests
└── requirements.txt              # Dépendances Python
```

---

## Prérequis

- **Python 3.11+**
- Les dépendances listées dans `requirements.txt`

```bash
pip install -r requirements.txt
```

Dépendances principales :

| Package             | Usage                                          |
|----------------------|-------------------------------------------------|
| pandas               | Manipulation des DataFrames                    |
| pyarrow              | Lecture/écriture Parquet                       |
| duckdb               | Requêtes SQL analytiques sur Parquet           |
| matplotlib / seaborn | Visualisations                                 |
| plotly               | Visualisations interactives (option)           |
| jupyter              | Notebook d'analyse                             |
| pytest               | Tests unitaires                                |
| great-expectations   | Validation qualité de la couche Silver         |
| apache-airflow       | Orchestration du pipeline (DAG)                |
| psycopg2-binary      | Connecteur Postgres pour le backend Airflow    |

---

## Reproduire le pipeline complet

### Option A — En local (sans Airflow)

**Étape 0 — Générer les données**

Les données brutes ne sont pas committées dans le repo (taille). Pour les générer :

```bash
cd mexora_project
python generate_data.py
```

Cela crée `data/raw/offres_emploi_it_maroc.json` avec 5 000 offres réalistes, incluant intentionnellement les problèmes de qualité décrits dans l'énoncé (villes mal orthographiées, salaires en formats mixtes, titres non standardisés, etc.).

**Étape 1 — Lancer le pipeline complet**

```bash
python main.py            # pipeline complet : bronze → silver → data_quality → gold
python main.py bronze     # ingestion Bronze seulement
python main.py silver     # Silver (nettoyage + NLP) seulement
python main.py gold       # Gold seulement
```

Le contrôle qualité (`data_quality/validate_silver.py`) s'exécute automatiquement entre Silver et Gold : si une règle critique échoue (doublons d'`id_offre`, salaire hors fourchette, profil inconnu...), le pipeline s'arrête et Gold n'est pas lancé.

Durée approximative : **10–15 secondes** pour 5 000 offres.

**Étape 2 — Lancer les analyses DuckDB**

```bash
python analysis/analyse_marche.py
```

**Étape 3 — Générer le dashboard**

```bash
python analysis/dashboard.py
```

Génère les 4 visualisations dans le répertoire `outputs/dashboard/`.

**Étape 4 — Lancer les tests**

```bash
pytest
```

### Option B — Avec Airflow (via Docker)

Le DAG `mexora_rh_pipeline` orchestre les mêmes étapes en tâches séparées avec dépendances explicites et retries automatiques :

```bash
docker compose up -d
```

- Airflow webserver disponible sur `http://localhost:8080` (utilisateur `admin` / mot de passe `admin`)
- Le DAG `mexora_rh_pipeline` est planifié quotidiennement (`@daily`) : `bronze_ingestion >> silver_transform >> data_quality_check >> gold_aggregation`
- Si `data_quality_check` échoue, `gold_aggregation` ne se déclenche pas — la porte de qualité est appliquée aussi en orchestration

---

## Détail des transformations Silver

### Normalisation des villes
Mapping regex `IGNORECASE` : `"casa"`, `"CASABLANCA"`, `"Casablanca-Anfa"` → `"Casablanca"`. Champ `region_admin` ajouté. Taux de reconnaissance : ~99,5%.

### Normalisation des titres de postes
14 patterns regex ordonnés par spécificité. `"Dev Data"`, `"Ingénieur Big Data"`, `"Data Eng."` → `"Data Engineer"`. Titres non reconnus → `"Autre IT"`.

### Normalisation des salaires
- Notation K : `"15K-20K"` → `15000-20000`
- Conversion EUR → MAD au taux fixe `1 EUR = 10.8 MAD` (2024)
- Rejet des valeurs hors fourchette `[3 000, 100 000]` MAD
- `"Confidentiel"`, `null` → `salaire_connu = False`
- Résultat : ~59,7% des offres ont un salaire valide

### Extraction de compétences (NLP)
Word-boundary regex (`\b{alias}\b`) sur la concaténation de `competences_brut` + `description`. Les aliases sont triés par longueur décroissante pour éviter les faux positifs (`"node"` ne matche pas avant `"node.js"`).

### Contrôle qualité (Great Expectations)
Avant que Gold ne consomme les données Silver, `data_quality/validate_silver.py` vérifie :
- `id_offre` et `titre_poste` non nuls, `id_offre` unique
- Les salaires connus respectent la fourchette `[3 000, 100 000]` MAD
- `profil_normalise` appartient à la liste des 14 profils valides

Si une vérification échoue, le pipeline s'arrête avant Gold — évite de propager des données corrompues en aval.

---

## Résultats clés

| Métrique | Valeur |
|---|---|
| Offres ingérées | 5 000 |
| Partitions Bronze | 69 |
| Taux de salaires valides | 59,7% |
| Offres avec ≥ 1 compétence détectée | 99,7% |
| Tables Gold produites | 5 |
| Compétences dans le référentiel | 49 (167 aliases) |

---

## Architecture Data Lake

```
JSON brut (scraping)
        │
        ▼  [bronze_ingestion.py]
  BRONZE — JSON partitionné (immuable)
  par source (rekrute / linkedin / marocannonce)
  par mois de publication (YYYY_MM)
        │
        ▼  [silver_transform.py + silver_nlp.py]
  SILVER — Parquet (snappy)
  offres_clean.parquet   → offres standardisées
  competences.parquet    → une ligne par offre × compétence
        │
        ▼  [data_quality/validate_silver.py — Great Expectations]
  PORTE QUALITÉ — bloque le passage en Gold si les règles échouent
        │
        ▼  [gold_aggregation.py — DuckDB]
  GOLD — Parquet (tables analytiques)
  top_competences / salaires_par_profil /
  offres_par_ville / entreprises / tendances
        │
        ▼
  Dashboard + Rapport analytique

  Orchestration : Airflow (dags/mexora_pipeline_dag.py) — planification @daily,
  retries automatiques, exécutable en local via `python main.py` ou en conteneurs via Docker Compose.
```

---

## Choix techniques justifiés

**Pourquoi JSON en Bronze ?** Les données brutes de scraping sont semi-structurées et évolutives. JSON préserve fidèlement la structure originale sans imposer de schéma. Zone immuable : si une transformation Silver introduit un bug, on peut toujours rejouer depuis Bronze.

**Pourquoi Parquet en Silver/Gold ?** Format columnar compressé (Snappy) : 5–10× plus compact que CSV, lectures 10–50× plus rapides sur les colonnes d'intérêt. Support natif des types (date, float, int, bool) évitant les conversions répétées. Interopérable avec DuckDB, Spark, pandas, Polars.

**Pourquoi DuckDB pour le Gold ?** Moteur SQL analytique in-process, sans serveur à démarrer. Lit les fichiers Parquet directement depuis le disque avec des performances proches d'un entrepôt de données. Idéal pour des analyses ad hoc sur des volumes <10 Go.

**Pourquoi Great Expectations pour la qualité ?** Permet de déclarer les règles métier (unicité, plages de valeurs, valeurs autorisées) comme du code versionné plutôt que des vérifications ad hoc, et de bloquer explicitement la propagation de données corrompues vers Gold.

**Pourquoi Airflow ?** Rend les dépendances entre étapes explicites (Gold ne se lance jamais avant que Silver et la validation qualité aient réussi), gère les retries automatiquement, et permet une planification récurrente (`@daily`) sans script cron maison.

**Pourquoi Docker Compose ?** Isole l'environnement Airflow (webserver + scheduler + Postgres) du poste de développement, et rend le déploiement reproductible en une seule commande.

---

## Auteurs

Projet réalisé par :
      EL-Moutouk Mohamed Yassir


Mexora RH