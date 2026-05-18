import json
import random
import csv
import os
from datetime import datetime, timedelta

random.seed(42)

# ─── Données de référence ────────────────────────────────────────────────────

SOURCES = ["rekrute", "marocannonce", "linkedin"]
SOURCE_WEIGHTS = [0.50, 0.25, 0.25]

VILLES_VARIANTS = {
    "Casablanca": ["Casablanca", "casablanca", "CASABLANCA", "casa", "Casa", "Casablanca-Anfa"],
    "Rabat":      ["Rabat", "rabat", "RABAT", "Rabat-Salé", "Rabat Salé"],
    "Tanger":     ["Tanger", "tanger", "TANGER", "Tanger-Med", "Tanger Med"],
    "Marrakech":  ["Marrakech", "marrakech", "MARRAKECH", "Marrakesh"],
    "Fès":        ["Fès", "Fes", "fès", "FES", "Fez"],
    "Agadir":     ["Agadir", "agadir", "AGADIR"],
    "Oujda":      ["Oujda", "oujda"],
    "Kenitra":    ["Kenitra", "kenitra", "Kénitra"],
    "Meknès":     ["Meknès", "Meknes", "meknès"],
    "Tétouan":    ["Tétouan", "Tetouan", "tétouan"],
}
VILLE_WEIGHTS = [0.42, 0.20, 0.10, 0.07, 0.05, 0.04, 0.03, 0.03, 0.03, 0.03]

REGIONS = {
    "Casablanca": "Casablanca-Settat",
    "Rabat":      "Rabat-Salé-Kénitra",
    "Tanger":     "Tanger-Tétouan-Al Hoceïma",
    "Marrakech":  "Marrakech-Safi",
    "Fès":        "Fès-Meknès",
    "Agadir":     "Souss-Massa",
    "Oujda":      "Oriental",
    "Kenitra":    "Rabat-Salé-Kénitra",
    "Meknès":     "Fès-Meknès",
    "Tétouan":    "Tanger-Tétouan-Al Hoceïma",
}

PROFILS = {
    "Data Engineer": {
        "titres": [
            "Data Engineer", "Ingénieur Data", "Data Eng.", "Ingénieur Big Data",
            "Data Pipeline Engineer", "Ingénieur ETL", "ETL Developer",
            "Data Engineer Senior", "Data Engineer Junior", "Dev Data",
        ],
        "competences": ["Python", "Spark", "Kafka", "Airflow", "SQL", "dbt", "Hadoop",
                        "AWS", "GCP", "Azure", "Docker", "Git", "Linux"],
        "salaire_range": (12000, 35000),
        "freq": 0.12,
    },
    "Data Analyst": {
        "titres": [
            "Data Analyst", "Analyste Data", "Analyste BI", "Business Intelligence Analyst",
            "Développeur BI", "Ingénieur BI", "Reporting Analyst", "Analyste données",
            "BI Analyst", "Data Analytics Engineer",
        ],
        "competences": ["SQL", "Power BI", "Python", "Excel", "Tableau", "Metabase",
                        "Looker", "R", "DAX", "Git"],
        "salaire_range": (8000, 22000),
        "freq": 0.10,
    },
    "Data Scientist": {
        "titres": [
            "Data Scientist", "Machine Learning Engineer", "ML Engineer",
            "Ingénieur Machine Learning", "Data Science Engineer", "IA Engineer",
            "Deep Learning Engineer", "NLP Engineer",
        ],
        "competences": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "SQL",
                        "R", "Spark", "AWS", "Docker", "Git", "Keras"],
        "salaire_range": (15000, 45000),
        "freq": 0.06,
    },
    "Développeur Full Stack": {
        "titres": [
            "Développeur Full Stack", "Full Stack Developer", "Fullstack Developer",
            "Développeur Full-Stack React/Node.js", "Full Stack Engineer",
        ],
        "competences": ["React", "Node.js", "JavaScript", "Python", "SQL",
                        "Docker", "Git", "Angular", "Spring", "AWS"],
        "salaire_range": (8000, 25000),
        "freq": 0.15,
    },
    "Développeur Backend": {
        "titres": [
            "Développeur Backend", "Backend Developer", "Développeur Back-End",
            "Ingénieur Développement Backend", "Backend Engineer",
        ],
        "competences": ["Java", "Python", "Node.js", "Spring", "Django",
                        "SQL", "Docker", "Git", "AWS"],
        "salaire_range": (7000, 22000),
        "freq": 0.12,
    },
    "Développeur Frontend": {
        "titres": [
            "Développeur Frontend", "Frontend Developer", "Développeur Front-End",
            "Développeur React", "Développeur Angular",
        ],
        "competences": ["React", "Angular", "JavaScript", "CSS", "HTML",
                        "TypeScript", "Git", "Vue.js"],
        "salaire_range": (6000, 18000),
        "freq": 0.10,
    },
    "DevOps / SRE": {
        "titres": [
            "DevOps Engineer", "Ingénieur DevOps", "SRE", "Site Reliability Engineer",
            "DevOps / Cloud Engineer",
        ],
        "competences": ["Docker", "Kubernetes", "Jenkins", "Terraform", "AWS",
                        "Azure", "GCP", "Linux", "Python", "Git", "Ansible"],
        "salaire_range": (12000, 35000),
        "freq": 0.08,
    },
    "Cloud Engineer": {
        "titres": [
            "Cloud Engineer", "Ingénieur Cloud", "AWS Engineer", "Azure Engineer",
            "Cloud Architect",
        ],
        "competences": ["AWS", "Azure", "GCP", "Terraform", "Docker",
                        "Kubernetes", "Linux", "Python"],
        "salaire_range": (14000, 40000),
        "freq": 0.05,
    },
    "Cybersécurité": {
        "titres": [
            "Ingénieur Cybersécurité", "Cybersecurity Engineer", "Pentester",
            "SOC Analyst", "Analyste Sécurité", "Security Engineer",
        ],
        "competences": ["Python", "Linux", "Kali", "Wireshark", "SIEM",
                        "Firewall", "ISO27001", "OWASP"],
        "salaire_range": (12000, 38000),
        "freq": 0.06,
    },
    "Chef de Projet IT": {
        "titres": [
            "Chef de Projet IT", "Project Manager IT", "Scrum Master",
            "Chef de Projet Informatique", "IT Project Manager",
        ],
        "competences": ["Agile", "Scrum", "Jira", "MS Project", "Prince2",
                        "PMP", "Communication", "SQL"],
        "salaire_range": (10000, 28000),
        "freq": 0.08,
    },
    "Développeur Mobile": {
        "titres": [
            "Développeur Mobile", "Mobile Developer", "iOS Developer",
            "Android Developer", "React Native Developer",
        ],
        "competences": ["React Native", "Flutter", "Swift", "Kotlin",
                        "Android", "iOS", "JavaScript", "Git"],
        "salaire_range": (8000, 22000),
        "freq": 0.05,
    },
    "Architecte IT": {
        "titres": [
            "Architecte Solutions", "Architecte Logiciel", "Software Architect",
            "Architecte Technique", "Architecte Cloud",
        ],
        "competences": ["Java", "Python", "AWS", "Azure", "Docker",
                        "Microservices", "API REST", "UML"],
        "salaire_range": (20000, 55000),
        "freq": 0.03,
    },
}

ENTREPRISES = [
    ("OCP Group", "Casablanca", "Grande Entreprise", "Industrie"),
    ("Maroc Telecom", "Rabat", "Grande Entreprise", "Telecom"),
    ("Attijariwafa Bank", "Casablanca", "Grande Entreprise", "Banque"),
    ("BMCE Bank", "Casablanca", "Grande Entreprise", "Banque"),
    ("CIH Bank", "Casablanca", "Grande Entreprise", "Banque"),
    ("Banque Populaire", "Casablanca", "Grande Entreprise", "Banque"),
    ("Inwi", "Casablanca", "Grande Entreprise", "Telecom"),
    ("Orange Maroc", "Casablanca", "Grande Entreprise", "Telecom"),
    ("Capgemini Maroc", "Casablanca", "ETI", "SSII"),
    ("CGI Maroc", "Casablanca", "ETI", "SSII"),
    ("IBM Maroc", "Casablanca", "ETI", "SSII"),
    ("HPS", "Casablanca", "ETI", "Produit"),
    ("Viasur IT", "Casablanca", "PME", "SSII"),
    ("WafaCash", "Casablanca", "ETI", "Fintech"),
    ("Société Générale Maroc", "Casablanca", "Grande Entreprise", "Banque"),
    ("TechMaroc SARL", "Casablanca", "PME", "SSII"),
    ("Intelcia", "Casablanca", "ETI", "Conseil"),
    ("Lydec", "Casablanca", "Grande Entreprise", "Energie"),
    ("ONCF", "Rabat", "Grande Entreprise", "Transport"),
    ("Ministère des Finances", "Rabat", "Grande Entreprise", "Public"),
    ("CNSS", "Rabat", "Grande Entreprise", "Public"),
    ("DataTech Rabat", "Rabat", "PME", "SSII"),
    ("Webhelp Maroc", "Rabat", "ETI", "Conseil"),
    ("Teleperformance Maroc", "Rabat", "ETI", "SSII"),
    ("Tanger Free Zone Corp", "Tanger", "ETI", "Industrie"),
    ("TechTanger Solutions", "Tanger", "PME", "SSII"),
    ("MedTech Tanger", "Tanger", "Startup", "Produit"),
    ("Renault Tanger", "Tanger", "Grande Entreprise", "Industrie"),
    ("Delphi Technologies Tanger", "Tanger", "Grande Entreprise", "Industrie"),
    ("NorthData Tanger", "Tanger", "Startup", "SSII"),
    ("Mexora", "Tanger", "PME", "Produit"),
    ("Jumia Maroc", "Casablanca", "Startup", "E-commerce"),
    ("Hmizate", "Casablanca", "Startup", "E-commerce"),
    ("InviteMaroc", "Casablanca", "Startup", "Produit"),
    ("Avito Maroc", "Casablanca", "ETI", "Produit"),
    ("Yabiladi", "Casablanca", "PME", "Media"),
    ("Lagoon Digital", "Marrakech", "PME", "SSII"),
    ("Marrakech Data", "Marrakech", "Startup", "SSII"),
    ("AxaDev Fès", "Fès", "PME", "SSII"),
    ("Fès Digital Hub", "Fès", "Startup", "SSII"),
]

CONTRATS_VARIANTS = {
    "CDI": ["CDI", "cdi", "Contrat à durée indéterminée", "Permanent", "Full-time CDI"],
    "CDD": ["CDD", "cdd", "Contrat à durée déterminée", "Temporary"],
    "Freelance": ["Freelance", "freelance", "Indépendant", "Mission freelance", "Consultant"],
    "Stage": ["Stage", "stage", "Internship", "Stage PFE", "Stage de fin d'études"],
    "Alternance": ["Alternance", "alternance", "Contrat d'apprentissage"],
}
CONTRAT_WEIGHTS = [0.55, 0.15, 0.15, 0.10, 0.05]

EXPERIENCE_VARIANTS = [
    ("0-1 ans", "Débutant accepté", "Sans expérience", "0-1 an", "Junior"),
    ("1-3 ans", "1 à 3 ans", "min 1 an", "1-3 years", "min 2 ans"),
    ("3-5 ans", "3 à 5 ans", "min 3 ans", "3-5 years", "3/5 ans"),
    ("5-8 ans", "5 à 8 ans", "min 5 ans", "Senior (5+ ans)", "5-7 ans"),
    ("8+ ans", "Senior confirmé (8+ ans)", "Expert 10 ans+", None, None),
]
EXP_WEIGHTS = [0.20, 0.30, 0.30, 0.15, 0.05]

SALAIRE_VARIANTS = {
    "normal": lambda mn, mx: f"{mn}-{mx} MAD",
    "k_notation": lambda mn, mx: f"{mn//1000}K-{mx//1000}K MAD",
    "k_no_unit": lambda mn, mx: f"{mn//1000}K-{mx//1000}K",
    "eur": lambda mn, mx: f"{int(mn/10.8)}-{int(mx/10.8)} EUR",
    "confidentiel": lambda mn, mx: "Confidentiel",
    "selon_profil": lambda mn, mx: "Selon profil",
    "null_val": lambda mn, mx: None,
}

TELETRAVAIL = ["Présentiel", "Hybride", "Télétravail complet", "Remote", "Non précisé"]
TT_WEIGHTS = [0.35, 0.35, 0.10, 0.05, 0.15]

NIVEAUX_ETUDES = ["Bac+2", "Bac+3", "Bac+5", "Bac+5 Ingénieur", "Bac+3/5", "Non précisé"]

LANGUES = [
    ["Français"],
    ["Français", "Anglais"],
    ["Arabe", "Français"],
    ["Français", "Anglais", "Arabe"],
    ["Anglais"],
]

DESCRIPTIONS_TEMPLATES = [
    """Nous recherchons un(e) {titre} expérimenté(e) pour rejoindre notre équipe dynamique.
Profil recherché : maîtrise de {comp1}, {comp2} et {comp3} indispensable. Connaissance de {comp4} appréciée.
Le candidat travaillera en méthode Agile avec une équipe de 5 à 10 personnes.
Responsabilités : développement et maintenance de pipelines, collaboration avec les équipes métier,
garantie de la qualité des données et automatisation des processus.
Compétences requises : {comp1}, {comp2}, {comp3}, {comp4}, Git, communication.""",

    """Dans le cadre de notre croissance, {entreprise} recrute un {titre}.
Vous serez en charge de : {comp1} et {comp2} principalement, ainsi que {comp3}.
Nous cherchons quelqu'un avec de solides connaissances en {comp2}, {comp4} et des bases en {comp1}.
Environnement de travail moderne, stack technologique récente, équipe internationale.""",

    """Poste : {titre} | Localisation : {ville}
Missions principales :
- Maîtrise de {comp1} requise
- Expérience avec {comp2} et {comp3}
- Connaissance de {comp4} est un plus
- Travailler avec {comp1}, {comp2} au quotidien
Technologies : {comp1} • {comp2} • {comp3} • {comp4}
Profil : diplômé Bac+5, esprit d'équipe, autonomie.""",

    """{entreprise} est à la recherche d'un talent {titre} pour renforcer son pôle technique.
Stack technique : {comp1}, {comp2}, {comp3}. La maîtrise de {comp4} sera un avantage.
Le candidat idéal a une expérience significative avec {comp1} et {comp2}.
Ambiance startup, challenges techniques, évolution rapide.""",
]

# ─── Générateur principal ─────────────────────────────────────────────────────

def generer_id(source, idx):
    prefix = {"rekrute": "RK", "marocannonce": "MA", "linkedin": "LN"}.get(source, "XX")
    return f"{prefix}-2024-{idx:05d}"

def date_aleatoire(start="2023-01-01", end="2024-11-30"):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    delta = (e - s).days
    return s + timedelta(days=random.randint(0, delta))

def generer_offre(idx, source, profil_nom, profil_data, entreprise_data):
    nom_ent, ville_ent, taille_ent, secteur_ent = entreprise_data

    # Titre — variante intentionnellement incohérente
    titre = random.choice(profil_data["titres"])

    # Ville — variante incohérente
    villes_list = list(VILLES_VARIANTS.keys())
    ville_key = random.choices(villes_list, weights=VILLE_WEIGHTS)[0]
    ville_variante = random.choice(VILLES_VARIANTS[ville_key])

    # Compétences
    comps = profil_data["competences"]
    nb_comp = random.randint(3, min(8, len(comps)))
    comp_selected = random.sample(comps, nb_comp)

    # Compétences brutes — séparateurs variés
    sep = random.choice([", ", " / ", " • ", "\n", " | "])
    competences_brut = sep.join(comp_selected)

    # Salaire
    sal_min, sal_max = profil_data["salaire_range"]
    sal_mn = random.randint(sal_min, (sal_min + sal_max) // 2)
    sal_mx = random.randint(sal_mn + 1000, sal_max)
    # Arrondir à 500
    sal_mn = (sal_mn // 500) * 500
    sal_mx = (sal_mx // 500) * 500

    sal_format = random.choices(
        list(SALAIRE_VARIANTS.keys()),
        weights=[0.30, 0.15, 0.10, 0.05, 0.15, 0.15, 0.10]
    )[0]
    salaire_brut = SALAIRE_VARIANTS[sal_format](sal_mn, sal_mx)

    # Contrat — variante incohérente
    contrat_key = random.choices(list(CONTRATS_VARIANTS.keys()), weights=CONTRAT_WEIGHTS)[0]
    type_contrat = random.choice(CONTRATS_VARIANTS[contrat_key])

    # Expérience — variante incohérente
    exp_tuple = random.choices(EXPERIENCE_VARIANTS, weights=EXP_WEIGHTS)[0]
    exp_vals = [v for v in exp_tuple if v is not None]
    experience_requise = random.choice(exp_vals) if exp_vals else None

    # Dates
    date_pub = date_aleatoire()
    # 10% des offres ont date_expiration < date_publication (problème intentionnel)
    if random.random() < 0.10:
        date_exp = date_pub - timedelta(days=random.randint(1, 30))
    else:
        date_exp = date_pub + timedelta(days=random.randint(15, 45))

    # Description
    c = comp_selected
    desc_template = random.choice(DESCRIPTIONS_TEMPLATES)
    description = desc_template.format(
        titre=titre,
        entreprise=nom_ent,
        ville=ville_key,
        comp1=c[0],
        comp2=c[1] if len(c) > 1 else c[0],
        comp3=c[2] if len(c) > 2 else c[0],
        comp4=c[3] if len(c) > 3 else c[0],
    )

    return {
        "id_offre": generer_id(source, idx),
        "source": source,
        "titre_poste": titre,
        "description": description,
        "competences_brut": competences_brut,
        "entreprise": nom_ent,
        "ville": ville_variante,
        "type_contrat": type_contrat,
        "experience_requise": experience_requise if random.random() > 0.05 else None,
        "salaire_brut": salaire_brut,
        "niveau_etudes": random.choice(NIVEAUX_ETUDES),
        "secteur": secteur_ent,
        "date_publication": date_pub.strftime("%Y-%m-%d"),
        "date_expiration": date_exp.strftime("%Y-%m-%d"),
        "nb_postes": random.choices([1, 2, 3, 5], weights=[0.70, 0.15, 0.10, 0.05])[0],
        "teletravail": random.choices(TELETRAVAIL, weights=TT_WEIGHTS)[0],
        "langue_requise": random.choice(LANGUES),
    }

def generer_dataset(n=5000):
    profil_noms = list(PROFILS.keys())
    profil_freqs = [PROFILS[p]["freq"] for p in profil_noms]

    offres = []
    for i in range(1, n + 1):
        source = random.choices(SOURCES, weights=SOURCE_WEIGHTS)[0]
        profil_nom = random.choices(profil_noms, weights=profil_freqs)[0]
        profil_data = PROFILS[profil_nom]
        entreprise_data = random.choice(ENTREPRISES)

        offre = generer_offre(i, source, profil_nom, profil_data, entreprise_data)
        offres.append(offre)

    return {"offres": offres}

def generer_referentiel():
    return {
        "familles": {
            "langages": {
                "python":      ["python", "python3", "py", "python 3"],
                "javascript":  ["javascript", "js", "node.js", "nodejs", "node", "typescript", "ts"],
                "java":        ["java", "java8", "java11", "java17", "java ee"],
                "sql":         ["sql", "mysql", "postgresql", "postgres", "oracle", "tsql", "pl/sql"],
                "r":           ["r", "rlang", "r-studio", "rstudio"],
                "scala":       ["scala"],
                "go":          ["golang", "go"],
                "php":         ["php", "php7", "php8"],
                "swift":       ["swift", "ios"],
                "kotlin":      ["kotlin", "android"],
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
                "aws":         ["aws", "amazon web services", "ec2", "s3", "lambda", "redshift"],
                "gcp":         ["gcp", "google cloud", "bigquery", "cloud storage"],
                "azure":       ["azure", "microsoft azure", "synapse", "azure devops"],
            },
            "bi_analytics": {
                "power_bi":    ["power bi", "powerbi", "pbi", "dax"],
                "tableau":     ["tableau", "tableau desktop"],
                "metabase":    ["metabase"],
                "looker":      ["looker", "looker studio"],
                "excel":       ["excel", "vba", "pivot"],
            },
            "devops_infra": {
                "docker":      ["docker", "dockerfile", "docker-compose"],
                "kubernetes":  ["kubernetes", "k8s", "kubectl"],
                "terraform":   ["terraform", "iac", "infrastructure as code"],
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
                "cv":          ["computer vision", "opencv", "yolo"],
            },
            "methodologies": {
                "agile":       ["agile", "scrum", "kanban", "sprint"],
                "api":         ["api rest", "rest api", "restful", "graphql", "api"],
                "microservices": ["microservices", "microservice", "soa"],
            },
        }
    }

def generer_entreprises_csv():
    rows = []
    for nom, ville, taille, secteur in ENTREPRISES:
        rows.append({
            "nom_entreprise": nom,
            "secteur": secteur,
            "taille": taille,
            "ville_siege": ville,
            "site_web": f"www.{nom.lower().replace(' ', '').replace('(','').replace(')','')[:15]}.ma",
            "type": secteur,
        })
    return rows

# ─── Exécution ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    BASE = "/home/claude/mexora_rh_lake/data/raw"

    print("Génération des 5000 offres d'emploi...")
    dataset = generer_dataset(5000)
    with open(f"{BASE}/offres_emploi_it_maroc.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"  -> {len(dataset['offres'])} offres générées")

    print("Génération du référentiel de compétences...")
    ref = generer_referentiel()
    with open(f"{BASE}/referentiel_competences_it.json", "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False, indent=2)
    print(f"  -> Référentiel avec {sum(len(v) for fam in ref['familles'].values() for v in fam.values())} aliases")

    print("Génération du fichier entreprises...")
    rows = generer_entreprises_csv()
    with open(f"{BASE}/entreprises_it_maroc.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["nom_entreprise", "secteur", "taille", "ville_siege", "site_web", "type"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  -> {len(rows)} entreprises")

    print("\nDonnées générées avec succès !")
