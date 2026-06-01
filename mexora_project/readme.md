# Mexora RH Intelligence — Data Lake Emploi IT Maroc

> **Mini-projet 2 | Analyse du marché de l'emploi IT marocain**  
> Pipeline Bronze → Silver → Gold sur 5 000 offres d'emploi (2023–2024)

---

## Vue d'ensemble

Ce projet construit un **Data Lake en trois zones** (Bronze / Silver / Gold) alimenté par des offres d'emploi IT marocaines issues de Rekrute, MarocAnnonce et LinkedIn. L'objectif final est de produire une analyse stratégique du marché pour guider la politique de recrutement de Mexora, une marketplace en forte croissance basée à Tanger.

**Ce que fait le pipeline, en résumé :**
- Ingère ~5 000 offres brutes et les partitionne par source et par mois (Bronze)
- Nettoie les données : villes, salaires, titres de postes, expérience, contrats (Silver)
- Extrait les compétences IT depuis le texte libre via matching regex (Silver NLP)
- Calcule des agrégats analytiques : top compétences, salaires, tendances (Gold)
- Produit 5 analyses DuckDB avec visualisations et recommandations RH

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
├── analysis/
│   ├── analyse_marche.py        # 5 questions analytiques DuckDB
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
├── main.py                      # Orchestrateur du pipeline complet
├── rapport_pipeline.md          # Rapport détaillé des transformations
└── requirement.txt              # Dépendances Python
```

---

## Prérequis

- **Python 3.11+**
- Les dépendances listées dans `requirement.txt`

```bash
pip install -r requirement.txt
```

Dépendances principales :

| Package     | Usage                                  |
|-------------|----------------------------------------|
| pandas      | Manipulation des DataFrames            |
| pyarrow     | Lecture/écriture Parquet               |
| duckdb      | Requêtes SQL analytiques sur Parquet   |
| matplotlib  | Visualisations                         |
| seaborn     | Visualisations statistiques            |
| plotly      | Visualisations interactives (option)   |
| jupyter     | Notebook d'analyse                     |

---

## Reproduire le pipeline complet

### Étape 0 — Générer les données

Les données brutes ne sont pas committées dans le repo (taille). Pour les générer :

```bash
cd mexora_project
python generate_data.py
```

Cela crée `data/raw/offres_emploi_it_maroc.json` avec 5 000 offres réalistes, incluant intentionnellement les problèmes de qualité décrits dans l'énoncé (villes mal orthographiées, salaires en formats mixtes, titres non standardisés, etc.).

### Étape 1 — Lancer le pipeline complet

```bash
cd mexora_project
python main.py
```

Ce script orchestre les 4 étapes dans l'ordre :

1. **Bronze** : ingestion brute, partitionnement par source/mois
2. **Silver transform** : nettoyage, normalisation, typage
3. **Silver NLP** : extraction des compétences depuis le texte
4. **Gold** : calcul des agrégats via DuckDB

Durée approximative : **10–15 secondes** pour 5 000 offres.

### Étape 2 — Lancer les analyses DuckDB

```bash
python mexora_project/analysis/analyse_marche.py
```

Affiche les résultats des 5 questions analytiques dans le terminal avec les interprétations métier.

### Étape 3 — Générer le dashboard

```bash
python mexora_project/analysis/dashboard.py
```

Génère les 4 visualisations dans le répertoire `outputs/dashboard/`.

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
        ▼  [gold_aggregation.py — DuckDB]
  GOLD — Parquet (tables analytiques)
  top_competences / salaires_par_profil /
  offres_par_ville / entreprises / tendances
        │
        ▼
  Dashboard + Rapport analytique
```

---

## Choix techniques justifiés

**Pourquoi JSON en Bronze ?** Les données brutes de scraping sont semi-structurées et évolutives. JSON préserve fidèlement la structure originale sans imposer de schéma. Zone immuable : si une transformation Silver introduit un bug, on peut toujours rejouer depuis Bronze.

**Pourquoi Parquet en Silver/Gold ?** Format columnar compressé (Snappy) : 5–10× plus compact que CSV, lectures 10–50× plus rapides sur les colonnes d'intérêt. Support natif des types (date, float, int, bool) évitant les conversions répétées. Interopérable avec DuckDB, Spark, pandas, Polars.

**Pourquoi DuckDB pour le Gold ?** Moteur SQL analytique in-process, sans serveur à démarrer. Lit les fichiers Parquet directement depuis le disque avec des performances proches d'un entrepôt de données. Idéal pour des analyses ad hoc sur des volumes <10 Go.

---

## Auteurs

Projet réalisé par :
      EL-Moutouk Mohamed Yassir
      Abarra SaadEddine
 
Mexora RH 