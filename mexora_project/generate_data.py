"""
generate_data.py
================
Génère les 3 fichiers de données brutes du projet :
  - data/raw/offres_emploi_it_maroc.json       (5 000 offres IT avec problèmes intentionnels)
  - data/raw/referentiel_competences_it.json   (référentiel 300+ compétences)
  - data/raw/entreprises_it_maroc.csv          (40 entreprises IT marocaines)

Usage : python generate_data.py
"""

import json
import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
#  Données de référence
# ─────────────────────────────────────────────────────────────────────────────

SOURCES          = ["rekrute", "marocannonce", "linkedin"]
SOURCE_WEIGHTS   = [0.50, 0.25, 0.25]

# Variantes intentionnellement incohérentes par ville (problème voulu)
VILLES_VARIANTES = {
    "Casablanca": ["Casablanca", "casablanca", "CASABLANCA", "casa", "Casa",
                   "Casablanca-Anfa", "Grand Casablanca"],
    "Rabat":      ["Rabat", "rabat", "RABAT", "Rabat-Salé", "Rabat Salé"],
    "Tanger":     ["Tanger", "tanger", "TANGER", "Tanger-Med", "Tanger Med"],
    "Marrakech":  ["Marrakech", "marrakech", "MARRAKECH", "Marrakesh"],
    "Fès":        ["Fès", "Fes", "fès", "FES", "Fez"],
    "Agadir":     ["Agadir", "agadir", "AGADIR"],
    "Oujda":      ["Oujda", "oujda", "OUJDA"],
    "Kenitra":    ["Kenitra", "kenitra", "Kénitra"],
    "Meknès":     ["Meknès", "Meknes", "meknès", "MEKNES"],
    "Tétouan":    ["Tétouan", "Tetouan", "tétouan", "TETOUAN"],
}
VILLE_WEIGHTS = [0.42, 0.20, 0.10, 0.07, 0.05, 0.04, 0.03, 0.03, 0.03, 0.03]

# Variantes incohérentes des contrats (problème voulu)
CONTRATS_VARIANTES = {
    "CDI":       ["CDI", "cdi", "Contrat à durée indéterminée", "Permanent",
                  "Full-time CDI", "CDI - Temps plein"],
    "CDD":       ["CDD", "cdd", "Contrat à durée déterminée", "Temporary", "CDD 6 mois"],
    "Freelance": ["Freelance", "freelance", "Indépendant", "Mission freelance",
                  "Consultant indépendant"],
    "Stage":     ["Stage", "stage", "Internship", "Stage PFE", "Stage de fin d'études"],
    "Alternance":["Alternance", "alternance", "Contrat d'apprentissage"],
}
CONTRAT_WEIGHTS = [0.55, 0.15, 0.15, 0.10, 0.05]

TELETRAVAIL   = ["Présentiel", "Hybride", "Télétravail complet", "Remote", "Non précisé"]
TT_WEIGHTS    = [0.35, 0.35, 0.10, 0.05, 0.15]

NIVEAUX_ETUDES = ["Bac+2", "Bac+3", "Bac+5", "Bac+5 Ingénieur", "Bac+3/5", "Non précisé"]

LANGUES_OPTIONS = [
    ["Français"],
    ["Français", "Anglais"],
    ["Arabe", "Français"],
    ["Français", "Anglais", "Arabe"],
    ["Anglais"],
]

# Profils IT avec leurs titres variés et compétences associées
PROFILS = {
    "Data Engineer": {
        "titres": [
            "Data Engineer", "Ingénieur Data", "Data Eng.", "Ingénieur Big Data",
            "Data Pipeline Engineer", "Ingénieur ETL", "ETL Developer",
            "Data Engineer Senior", "Data Engineer Junior", "Dev Data",
            "Développeur Data", "Big Data Engineer",
        ],
        "competences": [
            "Python", "Spark", "Kafka", "Airflow", "SQL", "dbt", "Hadoop",
            "AWS", "GCP", "Azure", "Docker", "Git", "Linux", "Scala",
        ],
        "salaire_range": (12000, 35000),
        "freq": 0.12,
    },
    "Data Analyst": {
        "titres": [
            "Data Analyst", "Analyste Data", "Analyste BI",
            "Business Intelligence Analyst", "Développeur BI", "Ingénieur BI",
            "Reporting Analyst", "Analyste données", "BI Analyst",
            "Data Analytics Engineer",
        ],
        "competences": [
            "SQL", "Power BI", "Python", "Excel", "Tableau", "Metabase",
            "Looker", "R", "DAX", "Git",
        ],
        "salaire_range": (8000, 22000),
        "freq": 0.10,
    },
    "Data Scientist": {
        "titres": [
            "Data Scientist", "Machine Learning Engineer", "ML Engineer",
            "Ingénieur Machine Learning", "Data Science Engineer", "IA Engineer",
            "Deep Learning Engineer", "NLP Engineer",
        ],
        "competences": [
            "Python", "TensorFlow", "PyTorch", "Scikit-learn", "SQL",
            "R", "Spark", "AWS", "Docker", "Git", "Keras",
        ],
        "salaire_range": (15000, 45000),
        "freq": 0.06,
    },
    "Développeur Full Stack": {
        "titres": [
            "Développeur Full Stack", "Full Stack Developer", "Fullstack Developer",
            "Développeur Full-Stack React/Node.js", "Full Stack Engineer",
        ],
        "competences": [
            "React", "Node.js", "JavaScript", "Python", "SQL",
            "Docker", "Git", "Angular", "Spring", "AWS",
        ],
        "salaire_range": (8000, 25000),
        "freq": 0.15,
    },
    "Développeur Backend": {
        "titres": [
            "Développeur Backend", "Backend Developer", "Développeur Back-End",
            "Ingénieur Développement Backend", "Backend Engineer",
        ],
        "competences": [
            "Java", "Python", "Node.js", "Spring", "Django",
            "SQL", "Docker", "Git", "AWS",
        ],
        "salaire_range": (7000, 22000),
        "freq": 0.12,
    },
    "Développeur Frontend": {
        "titres": [
            "Développeur Frontend", "Frontend Developer", "Développeur Front-End",
            "Développeur React", "Développeur Angular",
        ],
        "competences": [
            "React", "Angular", "JavaScript", "CSS", "HTML",
            "TypeScript", "Git",
        ],
        "salaire_range": (6000, 18000),
        "freq": 0.10,
    },
    "DevOps / SRE": {
        "titres": [
            "DevOps Engineer", "Ingénieur DevOps", "SRE",
            "Site Reliability Engineer", "DevOps / Cloud Engineer",
        ],
        "competences": [
            "Docker", "Kubernetes", "Jenkins", "Terraform", "AWS",
            "Azure", "Linux", "Python", "Git", "Ansible",
        ],
        "salaire_range": (12000, 35000),
        "freq": 0.08,
    },
    "Cloud Engineer": {
        "titres": [
            "Cloud Engineer", "Ingénieur Cloud", "AWS Engineer",
            "Azure Engineer", "Cloud Architect",
        ],
        "competences": [
            "AWS", "Azure", "GCP", "Terraform", "Docker", "Kubernetes", "Linux", "Python",
        ],
        "salaire_range": (14000, 40000),
        "freq": 0.05,
    },
    "Cybersécurité": {
        "titres": [
            "Ingénieur Cybersécurité", "Cybersecurity Engineer", "Pentester",
            "SOC Analyst", "Analyste Sécurité", "Security Engineer",
        ],
        "competences": [
            "Python", "Linux", "Kali", "Wireshark", "SIEM", "Firewall", "OWASP",
        ],
        "salaire_range": (12000, 38000),
        "freq": 0.06,
    },
    "Chef de Projet IT": {
        "titres": [
            "Chef de Projet IT", "Project Manager IT", "Scrum Master",
            "Chef de Projet Informatique", "IT Project Manager",
        ],
        "competences": [
            "Agile", "Scrum", "Jira", "MS Project", "Prince2", "PMP", "SQL",
        ],
        "salaire_range": (10000, 28000),
        "freq": 0.08,
    },
    "Développeur Mobile": {
        "titres": [
            "Développeur Mobile", "Mobile Developer", "iOS Developer",
            "Android Developer", "React Native Developer",
        ],
        "competences": [
            "React Native", "Flutter", "Swift", "Kotlin", "Android", "iOS", "JavaScript", "Git",
        ],
        "salaire_range": (8000, 22000),
        "freq": 0.05,
    },
    "Architecte IT": {
        "titres": [
            "Architecte Solutions", "Architecte Logiciel", "Software Architect",
            "Architecte Technique", "Architecte Cloud",
        ],
        "competences": [
            "Java", "Python", "AWS", "Azure", "Docker", "Microservices", "API REST", "UML",
        ],
        "salaire_range": (20000, 55000),
        "freq": 0.03,
    },
}

ENTREPRISES = [
    ("OCP Group",               "Casablanca", "Grande Entreprise", "Industrie"),
    ("Maroc Telecom",           "Rabat",       "Grande Entreprise", "Telecom"),
    ("Attijariwafa Bank",       "Casablanca", "Grande Entreprise", "Banque"),
    ("BMCE Bank",               "Casablanca", "Grande Entreprise", "Banque"),
    ("CIH Bank",                "Casablanca", "Grande Entreprise", "Banque"),
    ("Banque Populaire",        "Casablanca", "Grande Entreprise", "Banque"),
    ("Inwi",                    "Casablanca", "Grande Entreprise", "Telecom"),
    ("Orange Maroc",            "Casablanca", "Grande Entreprise", "Telecom"),
    ("Capgemini Maroc",         "Casablanca", "ETI",               "SSII"),
    ("CGI Maroc",               "Casablanca", "ETI",               "SSII"),
    ("IBM Maroc",               "Casablanca", "ETI",               "SSII"),
    ("HPS",                     "Casablanca", "ETI",               "Produit"),
    ("Viasur IT",               "Casablanca", "PME",               "SSII"),
    ("WafaCash",                "Casablanca", "ETI",               "Banque"),
    ("Société Générale Maroc",  "Casablanca", "Grande Entreprise", "Banque"),
    ("TechMaroc SARL",          "Casablanca", "PME",               "SSII"),
    ("Intelcia",                "Casablanca", "ETI",               "Conseil"),
    ("Lydec",                   "Casablanca", "Grande Entreprise", "Autre"),
    ("ONCF",                    "Rabat",       "Grande Entreprise", "Autre"),
    ("DataTech Rabat",          "Rabat",       "PME",               "SSII"),
    ("Webhelp Maroc",           "Rabat",       "ETI",               "Conseil"),
    ("Teleperformance Maroc",   "Rabat",       "ETI",               "SSII"),
    ("Tanger Free Zone Corp",   "Tanger",      "ETI",               "Autre"),
    ("TechTanger Solutions",    "Tanger",      "PME",               "SSII"),
    ("MedTech Tanger",          "Tanger",      "Startup",           "Produit"),
    ("Renault Tanger",          "Tanger",      "Grande Entreprise", "Autre"),
    ("Delphi Technologies",     "Tanger",      "Grande Entreprise", "Autre"),
    ("NorthData Tanger",        "Tanger",      "Startup",           "SSII"),
    ("Mexora",                  "Tanger",      "PME",               "Produit"),
    ("Jumia Maroc",             "Casablanca", "Startup",           "Produit"),
    ("Hmizate",                 "Casablanca", "Startup",           "Produit"),
    ("Avito Maroc",             "Casablanca", "ETI",               "Produit"),
    ("Lagoon Digital",          "Marrakech",  "PME",               "SSII"),
    ("Marrakech Data",          "Marrakech",  "Startup",           "SSII"),
    ("AxaDev Fès",              "Fès",         "PME",               "SSII"),
    ("Fès Digital Hub",         "Fès",         "Startup",           "SSII"),
    ("DataAgadir",              "Agadir",      "PME",               "SSII"),
    ("SouthTech",               "Agadir",      "Startup",           "Produit"),
    ("OrientalSoft",            "Oujda",       "PME",               "SSII"),
    ("NordNet Tétouan",         "Tétouan",     "PME",               "SSII"),
]

DESCRIPTIONS_TEMPLATES = [
    (
        "Nous recherchons un(e) {titre} expérimenté(e) pour rejoindre notre équipe dynamique. "
        "Profil recherché : maîtrise de {c0}, {c1} et {c2} indispensable. "
        "Connaissance de {c3} appréciée. Le candidat travaillera en méthode Agile. "
        "Responsabilités : développement et maintenance, collaboration avec les équipes métier, "
        "automatisation des processus. Compétences requises : {c0}, {c1}, {c2}, {c3}, Git."
    ),
    (
        "Dans le cadre de notre croissance, {entreprise} recrute un {titre}. "
        "Vous serez en charge de : {c0} et {c1} principalement, ainsi que {c2}. "
        "Nous cherchons quelqu'un avec de solides connaissances en {c1}, {c3}. "
        "Environnement de travail moderne, stack technologique récente, équipe internationale."
    ),
    (
        "Poste : {titre} | Localisation : {ville}\n"
        "Missions principales :\n"
        "- Maîtrise de {c0} requise\n"
        "- Expérience avec {c1} et {c2}\n"
        "- Connaissance de {c3} est un plus\n"
        "Technologies : {c0} • {c1} • {c2} • {c3}\n"
        "Profil : diplômé Bac+5, esprit d'équipe, autonomie."
    ),
    (
        "{entreprise} est à la recherche d'un talent {titre} pour renforcer son pôle technique. "
        "Stack technique : {c0}, {c1}, {c2}. La maîtrise de {c3} sera un avantage. "
        "Le candidat idéal a une expérience significative avec {c0} et {c1}. "
        "Ambiance startup, challenges techniques, évolution rapide."
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Fonctions de génération
# ─────────────────────────────────────────────────────────────────────────────

def _date_aleatoire(debut="2023-01-01", fin="2024-11-30"):
    d1 = datetime.strptime(debut, "%Y-%m-%d")
    d2 = datetime.strptime(fin,   "%Y-%m-%d")
    delta = (d2 - d1).days
    return d1 + timedelta(days=random.randint(0, delta))


def _generer_id(source, idx):
    prefix = {"rekrute": "RK", "marocannonce": "MA", "linkedin": "LN"}.get(source, "XX")
    return f"{prefix}-2024-{idx:05d}"


def _generer_salaire(sal_min_range, sal_max_range):
    """Génère un salaire dans plusieurs formats intentionnellement incohérents."""
    mn = (random.randint(sal_min_range, (sal_min_range + sal_max_range) // 2) // 500) * 500
    mx = (random.randint(mn + 1000, sal_max_range) // 500) * 500

    fmt = random.choices(
        ["normal", "k_mad", "k_seul", "eur", "confidentiel", "selon_profil", "null_val"],
        weights=[0.30, 0.15, 0.10, 0.05, 0.15, 0.15, 0.10],
    )[0]

    if fmt == "normal":
        return f"{mn}-{mx} MAD"
    elif fmt == "k_mad":
        return f"{mn // 1000}K-{mx // 1000}K MAD"
    elif fmt == "k_seul":
        return f"{mn // 1000}K-{mx // 1000}K"
    elif fmt == "eur":
        return f"{int(mn / 10.8)}-{int(mx / 10.8)} EUR"
    elif fmt == "confidentiel":
        return "Confidentiel"
    elif fmt == "selon_profil":
        return "Selon profil"
    else:
        return None


def _generer_experience():
    """Génère une expérience dans plusieurs formats intentionnellement incohérents."""
    options = [
        # (valeur brute, poids)
        ("Débutant accepté",    10),
        ("Junior",              10),
        ("0-1 an",               5),
        ("1-3 ans",             15),
        ("1 à 3 ans",            5),
        ("min 1 an",             5),
        ("3-5 ans",             20),
        ("3 à 5 ans",            5),
        ("min 3 ans",            5),
        ("5-8 ans",             10),
        ("Senior (5+ ans)",      5),
        ("Senior confirmé",      3),
        ("8+ ans",               2),
        (None,                   5),
    ]
    vals, poids = zip(*options)
    return random.choices(vals, weights=poids)[0]


def _generer_offre(idx, source, profil_nom, profil_data, entreprise_data):
    nom_ent, ville_ent, taille_ent, secteur_ent = entreprise_data

    # Titre : variante incohérente (problème intentionnel)
    titre = random.choice(profil_data["titres"])

    # Ville : variante incohérente (problème intentionnel)
    ville_key = random.choices(list(VILLES_VARIANTES.keys()), weights=VILLE_WEIGHTS)[0]
    ville_brute = random.choice(VILLES_VARIANTES[ville_key])

    # Compétences
    comps = profil_data["competences"]
    nb_comp = random.randint(3, min(7, len(comps)))
    comp_sel = random.sample(comps, nb_comp)

    # Séparateur incohérent (problème intentionnel)
    sep = random.choice([", ", " / ", " • ", "\n", " | "])
    competences_brut = sep.join(comp_sel)

    # Salaire (problème intentionnel)
    salaire_brut = _generer_salaire(*profil_data["salaire_range"])

    # Contrat : variante incohérente (problème intentionnel)
    contrat_key = random.choices(list(CONTRATS_VARIANTES.keys()), weights=CONTRAT_WEIGHTS)[0]
    type_contrat = random.choice(CONTRATS_VARIANTES[contrat_key])

    # Expérience : format incohérent (problème intentionnel)
    experience_requise = _generer_experience() if random.random() > 0.05 else None

    # Dates
    date_pub = _date_aleatoire()
    # 10 % des offres : date_expiration < date_publication  (problème intentionnel)
    if random.random() < 0.10:
        date_exp = date_pub - timedelta(days=random.randint(1, 30))
    else:
        date_exp = date_pub + timedelta(days=random.randint(15, 45))

    # Description (texte libre)
    c = comp_sel + [comp_sel[0]] * 4   # padding pour éviter IndexError
    desc_tpl = random.choice(DESCRIPTIONS_TEMPLATES)
    description = desc_tpl.format(
        titre=titre,
        entreprise=nom_ent,
        ville=ville_key,
        c0=c[0], c1=c[1], c2=c[2], c3=c[3],
    )

    return {
        "id_offre":          _generer_id(source, idx),
        "source":            source,
        "titre_poste":       titre,
        "description":       description,
        "competences_brut":  competences_brut,
        "entreprise":        nom_ent,
        "ville":             ville_brute,           # ← valeur brute incohérente
        "type_contrat":      type_contrat,           # ← valeur brute incohérente
        "experience_requise":experience_requise,     # ← format incohérent
        "salaire_brut":      salaire_brut,           # ← format incohérent
        "niveau_etudes":     random.choice(NIVEAUX_ETUDES),
        "secteur":           secteur_ent,
        "date_publication":  date_pub.strftime("%Y-%m-%d"),
        "date_expiration":   date_exp.strftime("%Y-%m-%d"),   # ← parfois < date_pub
        "nb_postes":         random.choices([1, 2, 3, 5], weights=[0.70, 0.15, 0.10, 0.05])[0],
        "teletravail":       random.choices(TELETRAVAIL, weights=TT_WEIGHTS)[0],
        "langue_requise":    random.choice(LANGUES_OPTIONS),
    }


def generer_offres(n=5000):
    profil_noms  = list(PROFILS.keys())
    profil_freqs = [PROFILS[p]["freq"] for p in profil_noms]

    offres = []
    for i in range(1, n + 1):
        source     = random.choices(SOURCES, weights=SOURCE_WEIGHTS)[0]
        profil_nom = random.choices(profil_noms, weights=profil_freqs)[0]
        entreprise = random.choice(ENTREPRISES)
        offres.append(_generer_offre(i, source, profil_nom, PROFILS[profil_nom], entreprise))

    return {"offres": offres}


def generer_referentiel():
    return {
        "familles": {
            "langages": {
                "python":      ["python", "python3", "py", "python 3"],
                "javascript":  ["javascript", "js", "node.js", "nodejs", "node",
                                "typescript", "ts"],
                "java":        ["java", "java8", "java11", "java17", "java ee"],
                "sql":         ["sql", "mysql", "postgresql", "postgres", "oracle",
                                "tsql", "pl/sql"],
                "r":           ["r", "rlang", "r-studio", "rstudio"],
                "scala":       ["scala"],
                "go":          ["golang", "go"],
                "php":         ["php", "php7", "php8"],
                "swift":       ["swift"],
                "kotlin":      ["kotlin"],
            },
            "frameworks_web": {
                "react":       ["react", "reactjs", "react.js", "react native"],
                "angular":     ["angular", "angularjs", "angular2"],
                "django":      ["django", "django rest"],
                "spring":      ["spring", "spring boot", "springboot"],
                "vue":         ["vue", "vuejs", "vue.js"],
                "flutter":     ["flutter", "dart"],
                "express":     ["express", "expressjs"],
                "laravel":     ["laravel"],
            },
            "data_engineering": {
                "spark":       ["spark", "apache spark", "pyspark"],
                "kafka":       ["kafka", "apache kafka"],
                "airflow":     ["airflow", "apache airflow"],
                "dbt":         ["dbt", "data build tool"],
                "hadoop":      ["hadoop", "hdfs", "mapreduce"],
                "hive":        ["hive", "hiveql"],
                "flink":       ["flink", "apache flink"],
                "nifi":        ["nifi", "apache nifi"],
            },
            "cloud": {
                "aws":         ["aws", "amazon web services", "ec2", "s3", "lambda",
                                "redshift"],
                "gcp":         ["gcp", "google cloud", "bigquery", "cloud storage"],
                "azure":       ["azure", "microsoft azure", "synapse", "azure devops"],
            },
            "bi_analytics": {
                "power_bi":    ["power bi", "powerbi", "pbi", "dax"],
                "tableau":     ["tableau", "tableau desktop"],
                "metabase":    ["metabase"],
                "looker":      ["looker", "looker studio"],
                "excel":       ["excel", "vba"],
            },
            "devops_infra": {
                "docker":      ["docker", "dockerfile", "docker-compose"],
                "kubernetes":  ["kubernetes", "k8s", "kubectl"],
                "terraform":   ["terraform"],
                "jenkins":     ["jenkins", "ci/cd", "cicd"],
                "ansible":     ["ansible"],
                "linux":       ["linux", "ubuntu", "centos", "bash", "shell"],
                "git":         ["git", "github", "gitlab", "bitbucket"],
            },
            "ml_ai": {
                "tensorflow":  ["tensorflow", "tf"],
                "pytorch":     ["pytorch", "torch"],
                "scikit":      ["scikit-learn", "sklearn", "scikit"],
                "keras":       ["keras"],
                "nlp":         ["nlp", "spacy", "nltk", "transformers", "bert"],
            },
            "methodologies": {
                "agile":       ["agile", "scrum", "kanban", "sprint"],
                "api_rest":    ["api rest", "rest api", "restful", "graphql"],
                "microservices": ["microservices", "microservice", "soa"],
            },
        }
    }


def generer_entreprises_csv():
    rows = []
    for nom, ville, taille, secteur in ENTREPRISES:
        slug = nom.lower().replace(" ", "").replace("'", "")[:15]
        rows.append({
            "nom_entreprise": nom,
            "secteur":        secteur,
            "taille":         taille,
            "ville_siege":    ville,
            "site_web":       f"www.{slug}.ma",
            "type":           secteur,
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
#  Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    print("Génération des 5 000 offres d'emploi IT...")
    dataset = generer_offres(5000)
    with open("data/raw/offres_emploi_it_maroc.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"  -> {len(dataset['offres'])} offres écrites dans data/raw/offres_emploi_it_maroc.json")

    print("Génération du référentiel de compétences...")
    ref = generer_referentiel()
    total_aliases = sum(
        len(aliases)
        for fam in ref["familles"].values()
        for aliases in fam.values()
    )
    with open("data/raw/referentiel_competences_it.json", "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False, indent=2)
    print(f"  -> {total_aliases} aliases dans data/raw/referentiel_competences_it.json")

    print("Génération du fichier entreprises...")
    rows = generer_entreprises_csv()
    champs = ["nom_entreprise", "secteur", "taille", "ville_siege", "site_web", "type"]
    with open("data/raw/entreprises_it_maroc.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  -> {len(rows)} entreprises dans data/raw/entreprises_it_maroc.csv")

    print("\nDonnées brutes générées avec succes !")