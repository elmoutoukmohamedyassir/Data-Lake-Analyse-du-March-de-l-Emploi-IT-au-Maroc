"""
pipeline/utils.py
=================
Fonctions utilitaires partagées par l'ensemble du pipeline.
"""

import re
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  Normalisation des villes
# ─────────────────────────────────────────────────────────────────────────────

MAPPING_VILLES = [
    # Casablanca  (toujours en premier — cas le plus courant)
    (r"casablanca|grand\s+casablanca|casa\b",     "Casablanca"),
    # Rabat
    (r"rabat",                                     "Rabat"),
    # Tanger
    (r"tanger",                                    "Tanger"),
    # Marrakech
    (r"marrakech|marrakesh",                       "Marrakech"),
    # Fès
    (r"f[eè]s|fez",                               "Fès"),
    # Agadir
    (r"agadir",                                    "Agadir"),
    # Oujda
    (r"oujda",                                     "Oujda"),
    # Kenitra
    (r"k[eé]nitra",                               "Kenitra"),
    # Meknès
    (r"mekn[eè]s",                                "Meknès"),
    # Tétouan
    (r"t[eé]touan",                               "Tétouan"),
]

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


def normaliser_ville(valeur: str):
    """
    Normalise une valeur de ville brute vers la forme standard.

    Retourne : (ville_std: str, region_admin: str)

    Exemples :
      "casa"        → ("Casablanca", "Casablanca-Settat")
      "CASABLANCA"  → ("Casablanca", "Casablanca-Settat")
      "Tanger-Med"  → ("Tanger",     "Tanger-Tétouan-Al Hoceïma")
      "xyz"         → ("Inconnue",   "Inconnue")
    """
    if not valeur:
        return "Inconnue", "Inconnue"
    v = str(valeur).lower().strip()
    for pattern, ville_std in MAPPING_VILLES:
        if re.search(pattern, v, re.IGNORECASE):
            return ville_std, REGIONS.get(ville_std, "Inconnue")
    # Valeur non reconnue : on la capitalise et on la conserve
    return str(valeur).strip().title(), "Inconnue"


# ─────────────────────────────────────────────────────────────────────────────
#  Normalisation du type de contrat
# ─────────────────────────────────────────────────────────────────────────────

def normaliser_contrat(valeur: str) -> str:
    """
    Normalise le type de contrat vers CDI / CDD / Freelance / Stage / Alternance.

    Exemples :
      "cdi"                        → "CDI"
      "Contrat à durée indéterminée" → "CDI"
      "Mission freelance"          → "Freelance"
    """
    if not valeur:
        return "Non précisé"
    v = str(valeur).lower().strip()
    if any(x in v for x in ["cdi", "permanent", "indéterminée", "full-time cdi"]):
        return "CDI"
    if any(x in v for x in ["cdd", "déterminée", "temporary"]):
        return "CDD"
    if any(x in v for x in ["freelance", "indépendant", "mission", "consultant"]):
        return "Freelance"
    if any(x in v for x in ["stage", "intern", "pfe"]):
        return "Stage"
    if any(x in v for x in ["alternance", "apprentissage"]):
        return "Alternance"
    return "Non précisé"


# ─────────────────────────────────────────────────────────────────────────────
#  Validation des dates
# ─────────────────────────────────────────────────────────────────────────────

def valider_dates(date_pub: str, date_exp: str) -> dict:
    """
    Valide la cohérence publication / expiration.

    Règle : date_expiration doit être strictement > date_publication.
    Les dates incohérentes sont flaggées mais conservées (zone Bronze = immuable,
    correction uniquement en Silver).

    Retourne un dict avec les clés :
      date_publication_std, date_expiration_std,
      annee, mois, date_coherente (bool)
    """
    dp = None
    de = None

    try:
        dp = datetime.strptime(str(date_pub)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    try:
        de = datetime.strptime(str(date_exp)[:10], "%Y-%m-%d") if date_exp else None
    except (ValueError, TypeError):
        pass

    coherente = True
    if dp and de and de <= dp:
        coherente = False   # problème intentionnel dans les données brutes

    return {
        "date_publication_std": dp.strftime("%Y-%m-%d") if dp else None,
        "date_expiration_std":  de.strftime("%Y-%m-%d") if de else None,
        "annee":                str(dp.year)            if dp else None,
        "mois":                 str(dp.month).zfill(2)  if dp else None,
        "date_coherente":       coherente,
    }