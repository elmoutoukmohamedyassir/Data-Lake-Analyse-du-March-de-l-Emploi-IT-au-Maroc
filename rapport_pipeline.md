# Rapport Pipeline — Mexora RH Intelligence



## 1. Bronze — Ingestion brute

### Règle appliquée
Chargement des données brutes **sans aucune modification**. Partitionnement par `source` (rekrute / marocannonce / linkedin) et par `mois de publication` (`YYYY_MM`).

**Principe fondamental** : la zone Bronze est **immuable**. Une fois ingérées, les données ne sont jamais modifiées. En cas d'erreur dans la transformation Silver, on peut toujours rejouer depuis Bronze.

### Statistiques

| Métrique            | Valeur  |
|---------------------|---------|
| Offres en entrée    | 5 000   |
| Partitions créées   | 69      |
| Fichiers JSON écrits| 70 (69 partitions + 1 rapport) |
| Taille totale       | ~5 200 Ko |

### Répartition par source

| Source        | Offres | %     |
|---------------|--------|-------|
| rekrute       | 2 467  | 49,3% |
| linkedin      | 1 299  | 26,0% |
| marocannonce  | 1 234  | 24,7% |

### Cas limites
- **Date manquante** → partition `date_inconnue/`
- **Source inconnue** → partition `inconnu/`
- Métadonnées d'ingestion ajoutées : horodatage ISO 8601, version de schéma (`1.0`), nombre d'offres

---

## 2. Silver — Nettoyage et standardisation

### 2.1 Normalisation des villes

**Règle** : mapping regex `IGNORECASE` vers 10 villes standards.

| Valeur brute        | Valeur normalisée | Region admin               |
|---------------------|-------------------|----------------------------|
| `casa`, `CASABLANCA`, `Casablanca-Anfa` | `Casablanca` | Casablanca-Settat |
| `Fez`, `fès`, `FES` | `Fès`             | Fès-Meknès                 |
| `Tanger-Med`        | `Tanger`          | Tanger-Tétouan-Al Hoceïma  |
| `Rabat Salé`        | `Rabat`           | Rabat-Salé-Kénitra         |
| Valeur non reconnue | conservée (`.title()`) | `Inconnue`            |

**Résultat** : ~99,5% des villes reconnues. Champ `region_admin` ajouté.

### 2.2 Normalisation des titres de poste → profils

**Règle** : 14 patterns regex ordonnés par spécificité.  
Titres non reconnus → `"Autre IT"`.

| Profil normalisé        | Variantes couvertes                                              |
|-------------------------|------------------------------------------------------------------|
| Data Engineer           | "Data Eng.", "Ingénieur Big Data", "ETL Developer", "Dev Data"  |
| Data Analyst            | "Analyste BI", "Business Intelligence", "Développeur BI"        |
| Data Scientist          | "ML Engineer", "IA Engineer", "Machine Learning"                |
| DevOps / SRE            | "Ingénieur DevOps", "Site Reliability Engineer"                 |
| Développeur Full Stack  | "Full Stack Developer", "Fullstack", "Full-Stack"               |

**Répartition obtenue** :

| Profil                  | Offres | %     |
|-------------------------|--------|-------|
| Développeur Full Stack  | 766    | 15,3% |
| Développeur Backend     | 630    | 12,6% |
| Data Engineer           | 483    | 9,7%  |
| Data Analyst            | 426    | 8,5%  |
| Chef de Projet IT       | 403    | 8,1%  |
| DevOps / SRE            | 380    | 7,6%  |
| Autre IT                | 552    | 11,0% |

### 2.3 Normalisation des salaires

**Règles** :
1. `"Selon profil"`, `"Confidentiel"`, `null` → `salaire_connu = False`
2. Notation K : `"15K-20K"` → `15000-20000`
3. EUR → MAD : taux fixe `1 EUR = 10.8 MAD` (2024)
4. Fourchette → `salaire_min_mad`, `salaire_max_mad`, `salaire_median_mad`
5. Rejet si `< 3 000 MAD` ou `> 100 000 MAD` (incohérence)

| Format d'entrée       | Exemple           | Résultat                       |
|-----------------------|-------------------|--------------------------------|
| Normal                | `15000-20000 MAD` | min=15000, max=20000           |
| K-notation            | `15K-20K MAD`     | min=15000, max=20000           |
| K sans unité          | `15K-20K`         | min=15000, max=20000           |
| EUR                   | `1500-2000 EUR`   | min=16200, max=21600           |
| Confidentiel          | `"Confidentiel"`  | salaire_connu=False            |
| Selon profil          | `"Selon profil"`  | salaire_connu=False            |
| NULL                  | `null`            | salaire_connu=False            |

**Résultat** : **~59,7%** des offres ont un salaire valide (2 985 / 5 000).

### 2.4 Normalisation de l'expérience

**Règles** :

| Valeur brute            | experience_min_ans | experience_max_ans |
|-------------------------|--------------------|--------------------|
| `"Débutant accepté"`    | 0                  | 2                  |
| `"Junior"`              | 0                  | 2                  |
| `"3-5 ans"` / `"3 à 5 ans"` | 3              | 5                  |
| `"min 3 ans"` / `"3+ ans"` | 3               | None               |
| `"Senior confirmé"`     | 8                  | None               |
| `null`                  | None               | None               |

**Résultat** : ~93% des valeurs parsées avec succès.

### 2.5 Normalisation des contrats

| Valeur brute                          | Valeur standard |
|---------------------------------------|-----------------|
| `"CDI"`, `"cdi"`, `"Permanent"`, `"Contrat à durée indéterminée"` | `CDI` |
| `"CDD"`, `"cdd"`, `"Temporary"`       | `CDD`           |
| `"Freelance"`, `"Mission freelance"`  | `Freelance`     |
| `"Stage"`, `"Stage PFE"`, `"Internship"` | `Stage`      |
| `"Alternance"`                        | `Alternance`    |

### 2.6 Validation des dates

**Règle** : `date_expiration` doit être strictement `> date_publication`.

- **Dates incohérentes détectées** : ~522 (10,4%) — problème intentionnel
- **Traitement** : flag `date_coherente = False`, valeurs conservées pour audit

### Bilan Silver

| Champ               | Avant         | Après                    |
|---------------------|---------------|--------------------------|
| `ville`             | 10+ variantes | 10 villes standards      |
| `titre_poste`       | texte libre   | 13 profils normalisés    |
| `salaire_brut`      | 7 formats     | 3 colonnes numériques MAD |
| `experience_requise`| texte libre   | 2 colonnes int/None      |
| `type_contrat`      | 15+ variantes | 5 valeurs standards      |
| Nouvelles colonnes  | —             | 13 colonnes ajoutées     |

---

## 3. Silver NLP — Extraction des compétences

### Stratégie
Matching **word-boundary regex** sur le texte concaténé de `competences_brut` + `description`.  
Pattern : `\b{alias}\b` — aliases triés par longueur décroissante.

### Référentiel

| Famille        | Compétences | Aliases |
|----------------|-------------|---------|
| langages       | 10          | 42      |
| frameworks_web | 8           | 22      |
| data_engineering | 8         | 22      |
| cloud          | 3           | 16      |
| bi_analytics   | 5           | 14      |
| devops_infra   | 7           | 27      |
| ml_ai          | 5           | 14      |
| methodologies  | 3           | 10      |
| **Total**      | **49**      | **167** |

### Résultats

| Métrique                    | Valeur         |
|-----------------------------|----------------|
| Offres analysées            | 5 000          |
| Offres avec ≥ 1 compétence  | 4 983 (99,7%)  |
| Offres sans compétence      | 17 (0,3%)      |
| Lignes (offre × compétence) | ~26 000        |
| Compétence #1               | `git` (~57%)   |

### Cas limites traités
- **Alias ambigus** : `"r"` (langage R) → le tri longueur décroissante et le word-boundary limitent les faux positifs dans le contexte IT
- **Texte null** : `None` → remplacé par `""` avant concaténation
- **Doublon intra-offre** : une compétence détectée plusieurs fois → une seule ligne (via `set`)

---

## 4. Gold — Tables analytiques (DuckDB)

| Table                      | Lignes | Description                              |
|----------------------------|--------|------------------------------------------|
| `top_competences`          | ~188   | Compétences par profil + rang            |
| `salaires_par_profil`      | ~234   | Médiane, Q1, Q3 par profil/ville/contrat |
| `offres_par_ville`         | ~1 735 | Volume offres × ville × profil × mois   |
| `entreprises_recruteurs`   | 100    | Top 100 recruteurs                       |
| `tendances_mensuelles`     | ~299   | Évolution + LAG mois précédent           |

---

## 5. Bilan global du pipeline

| Étape           | Input         | Output                    | Durée  |
|-----------------|---------------|---------------------------|--------|
| Bronze          | 5 000 offres  | 69 partitions JSON        | ~0.3s  |
| Silver transform| 5 000 offres  | offres_clean.parquet      | ~1.2s  |
| Silver NLP      | 5 000 offres  | competences.parquet       | ~8s    |
| Gold (DuckDB)   | 2 Parquet     | 5 tables Parquet          | ~0.5s  |
| **Total**       | 1 JSON brut   | 77 fichiers, ~20 Mo       | ~10s   |