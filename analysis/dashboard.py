"""
dashboard.py
━━━━━━━━━━━━
Étape 4 — Dashboard : 4 visualisations requises
1. Carte du Maroc — volume d'offres IT par ville (bubble map simulée)
2. Top 15 compétences — barres horizontales par famille
3. Boxplot salaires — distribution par profil
4. Évolution mensuelle — Data Engineer / Analyst / Scientist
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec
from pathlib import Path
from collections import defaultdict
import statistics

# ─── Configuration visuelle ───────────────────────────────────────────────────

COLORS = {
    'langages':         '#2196F3',
    'devops_infra':     '#FF9800',
    'frameworks_web':   '#9C27B0',
    'cloud':            '#00BCD4',
    'bi_analytics':     '#4CAF50',
    'data_engineering': '#F44336',
    'ml_ai':            '#E91E63',
    'methodologies':    '#795548',
    'inconnu':          '#9E9E9E',
}

PROFIL_COLORS = {
    'Data Engineer':          '#1565C0',
    'Data Analyst':           '#2E7D32',
    'Data Scientist':         '#6A1B9A',
    'Développeur Full Stack': '#E65100',
    'Développeur Backend':    '#4E342E',
    'Développeur Frontend':   '#00695C',
    'DevOps / SRE':           '#AD1457',
    'Cloud Engineer':         '#0277BD',
    'Cybersécurité':          '#558B2F',
    'Chef de Projet IT':      '#F57F17',
    'Développeur Mobile':     '#37474F',
    'Architecte IT':          '#4527A0',
    'Autre IT':               '#9E9E9E',
}

GOLD_PATH = Path('/home/claude/mexora_rh_lake/data_lake/gold')
OUTPUT_DIR = Path('/home/claude/mexora_rh_lake/analysis')

def charger(nom):
    with open(GOLD_PATH / f'{nom}.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def median_safe(vals):
    v = [x for x in vals if x is not None]
    return statistics.median(v) if v else None

def percentile(values, p):
    v = sorted(x for x in values if x is not None)
    if not v: return None
    idx = (len(v) - 1) * p / 100
    lo, hi = int(idx), min(int(idx)+1, len(v)-1)
    return v[lo] + (v[hi]-v[lo]) * (idx-lo)


# ─── Viz 1 : Carte bubble du Maroc ───────────────────────────────────────────

def viz1_carte_maroc(ax):
    offres_ville = charger('offres_par_ville')
    total_ville = defaultdict(int)
    for r in offres_ville:
        total_ville[r['ville']] += r['nb_offres']

    # Coordonnées approximatives des villes
    coords = {
        'Casablanca': (-7.59, 33.57),
        'Rabat':      (-6.84, 34.02),
        'Tanger':     (-5.81, 35.78),
        'Marrakech':  (-8.01, 31.63),
        'Fès':        (-5.00, 34.04),
        'Agadir':     (-9.57, 30.42),
        'Oujda':      (-1.91, 34.69),
        'Kenitra':    (-6.57, 34.26),
        'Meknès':     (-5.56, 33.90),
        'Tétouan':    (-5.37, 35.57),
    }

    # Fond carte simplifié — contour du Maroc
    maroc_shape = [
        (-5.9, 35.9), (-2.2, 35.1), (-1.7, 34.8), (-1.2, 34.1),
        (-2.5, 32.8), (-3.0, 31.5), (-4.0, 30.2), (-5.5, 29.7),
        (-8.7, 28.7), (-11.5, 28.0), (-13.2, 27.6), (-13.2, 27.0),
        (-12.6, 23.7), (-8.7, 21.3), (-5.5, 22.0), (-4.8, 24.0),
        (-4.0, 26.0), (-3.7, 28.0), (-2.5, 29.0), (-1.1, 30.5),
        (-1.0, 31.5), (-2.0, 33.0), (-3.0, 34.0), (-4.5, 35.0),
        (-5.9, 35.9),
    ]
    xs_m, ys_m = zip(*maroc_shape)
    ax.fill(xs_m, ys_m, color='#E8F4F8', alpha=0.7, linewidth=0)
    ax.plot(xs_m, ys_m, color='#B0BEC5', linewidth=1)

    max_offres = max(total_ville.values()) if total_ville else 1
    for ville, (lon, lat) in coords.items():
        n = total_ville.get(ville, 0)
        if n == 0:
            continue
        size = (n / max_offres) * 2000 + 100
        color = '#FF5722' if ville == 'Tanger' else '#2196F3'
        alpha = 0.8 if ville == 'Tanger' else 0.6
        ax.scatter(lon, lat, s=size, c=color, alpha=alpha, zorder=5)
        offset_x = 0.2
        offset_y = 0.25 if ville not in ['Rabat', 'Kenitra'] else -0.35
        ax.annotate(f'{ville}\n{n:,}', (lon + offset_x, lat + offset_y),
                    fontsize=7.5, ha='center', fontweight='bold',
                    color='#1A237E')

    ax.set_xlim(-14.5, 0)
    ax.set_ylim(21, 37)
    ax.set_aspect('equal')
    ax.set_facecolor('#DEEAF6')
    ax.set_title("Volume d'offres IT par ville\n(2023–2024)", fontsize=12, fontweight='bold', pad=10)

    # Légende taille
    for n_leg, label in [(500, '500'), (1000, '1 000'), (2000, '2 000+')]:
        s = (n_leg / max_offres) * 2000 + 100
        ax.scatter([], [], s=s, c='#2196F3', alpha=0.6, label=label)
    ax.legend(title='Nb offres', title_fontsize=8, fontsize=8,
              loc='lower left', framealpha=0.9)

    # Marqueur Mexora
    lon_t, lat_t = coords['Tanger']
    ax.annotate('★ Mexora', (lon_t - 0.3, lat_t - 0.45), fontsize=8,
                color='#B71C1C', fontweight='bold', ha='center')
    ax.set_xlabel("Longitude", fontsize=8)
    ax.set_ylabel("Latitude", fontsize=8)
    ax.tick_params(labelsize=7)


# ─── Viz 2 : Top 15 compétences ──────────────────────────────────────────────

def viz2_top_competences(ax):
    top_comp = charger('top_competences')
    tous = [r for r in top_comp if r['profil'] == 'tous']
    tous_sorted = sorted(tous, key=lambda x: x['nb_offres_mentionnent'], reverse=True)[:15]

    competences = [r['competence'] for r in tous_sorted]
    values = [r['nb_offres_mentionnent'] for r in tous_sorted]
    familles = [r['famille'] for r in tous_sorted]
    colors = [COLORS.get(f, '#9E9E9E') for f in familles]

    bars = ax.barh(competences, values, color=colors, edgecolor='white', linewidth=0.5)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
                f'{val:,}', va='center', fontsize=8.5, color='#333')

    ax.set_xlabel("Nombre d'offres mentionnant la compétence", fontsize=9)
    ax.set_title("Top 15 compétences IT — Maroc (2023–2024)", fontsize=12, fontweight='bold', pad=10)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.15)
    ax.tick_params(labelsize=9)
    ax.set_facecolor('#FAFAFA')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Légende familles
    familles_uniques = list(dict.fromkeys(familles))
    patches = [mpatches.Patch(color=COLORS.get(f, '#9E9E9E'), label=f.replace('_', ' ').title())
               for f in familles_uniques]
    ax.legend(handles=patches, title='Famille', title_fontsize=8, fontsize=7.5,
              loc='lower right', framealpha=0.9)


# ─── Viz 3 : Boxplot salaires par profil ─────────────────────────────────────

def viz3_boxplot_salaires(ax):
    salaires_raw = charger('salaires_par_profil')
    silver_path = Path('/home/claude/mexora_rh_lake/data_lake/silver/offres_clean/offres_clean.json')
    with open(silver_path) as f:
        offres = json.load(f)

    # Grouper les salaires individuels par profil
    profil_salaires = defaultdict(list)
    for o in offres:
        if o.get('salaire_connu') and o.get('salaire_median_mad'):
            profil_salaires[o['profil_normalise']].append(o['salaire_median_mad'])

    # Sélectionner profils data + dev les plus importants
    profils_selec = ['Data Scientist', 'Cloud Engineer', 'Data Engineer', 'DevOps / SRE',
                     'Chef de Projet IT', 'Data Analyst', 'Développeur Full Stack',
                     'Développeur Backend', 'Développeur Frontend']

    data_box = []
    labels = []
    colors_box = []

    for profil in profils_selec:
        sals = [s for s in profil_salaires.get(profil, []) if 3000 <= s <= 80000]
        if len(sals) >= 10:
            data_box.append(sals)
            labels.append(profil.replace('Développeur ', 'Dev. ').replace('Chef de Projet IT', 'Chef Proj. IT'))
            colors_box.append(PROFIL_COLORS.get(profil, '#9E9E9E'))

    bp = ax.boxplot(data_box, vert=False, patch_artist=True,
                    whiskerprops=dict(color='#666'),
                    capprops=dict(color='#666'),
                    medianprops=dict(color='white', linewidth=2.5),
                    flierprops=dict(marker='o', markersize=3, alpha=0.4))

    for patch, color in zip(bp['boxes'], colors_box):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Salaire mensuel brut (MAD)", fontsize=9)
    ax.set_title("Distribution des salaires par profil IT\n(médiane, Q1–Q3, min–max)", fontsize=12, fontweight='bold', pad=10)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{int(x):,} MAD'))
    ax.tick_params(axis='x', labelsize=8)
    ax.set_facecolor('#FAFAFA')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Ligne médiane nationale Data Engineer
    median_de = median_safe(profil_salaires.get('Data Engineer', []))
    if median_de:
        ax.axvline(median_de, color='#F44336', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(median_de + 200, len(data_box) + 0.3, f'Méd. Data Eng.\n{int(median_de):,} MAD',
                fontsize=7, color='#F44336')


# ─── Viz 4 : Évolution mensuelle ─────────────────────────────────────────────

def viz4_evolution_mensuelle(ax):
    tendances = charger('tendances_mensuelles')

    profils_data = ['Data Engineer', 'Data Analyst', 'Data Scientist']
    colors_ev = {'Data Engineer': '#1565C0', 'Data Analyst': '#2E7D32', 'Data Scientist': '#6A1B9A'}

    # Agréger par année-mois-profil
    agg = defaultdict(lambda: defaultdict(int))
    for r in tendances:
        if r['profil'] in profils_data and r['annee'] and r['mois']:
            key = f"{r['annee']}-{r['mois']}"
            agg[key][r['profil']] += r['nb_offres']

    # Trier les mois
    mois_tries = sorted(agg.keys())
    # Filtrer 2023-01 à 2024-11
    mois_tries = [m for m in mois_tries if '2023' <= m <= '2024-11']

    for profil in profils_data:
        vals = [agg[m].get(profil, 0) for m in mois_tries]
        ax.plot(range(len(mois_tries)), vals, marker='o', markersize=4,
                linewidth=2, color=colors_ev[profil], label=profil, alpha=0.9)

        # Remplissage sous la courbe
        ax.fill_between(range(len(mois_tries)), vals, alpha=0.08, color=colors_ev[profil])

    # Axe x — afficher 1 label sur 3
    step = max(1, len(mois_tries) // 10)
    xticks = range(0, len(mois_tries), step)
    xlabels = [mois_tries[i][:7] if i < len(mois_tries) else '' for i in xticks]
    ax.set_xticks(list(xticks))
    ax.set_xticklabels(xlabels, rotation=45, ha='right', fontsize=8)

    # Séparateur 2023 / 2024
    limite_2024 = next((i for i, m in enumerate(mois_tries) if m.startswith('2024')), None)
    if limite_2024:
        ax.axvline(limite_2024 - 0.5, color='#B0BEC5', linestyle='--', linewidth=1)
        ax.text(limite_2024 - 0.4, ax.get_ylim()[1] * 0.95, '2024 →',
                fontsize=8, color='#78909C')

    ax.set_xlabel("Mois", fontsize=9)
    ax.set_ylabel("Nombre d'offres publiées", fontsize=9)
    ax.set_title("Évolution mensuelle des offres Data\n(Jan 2023 – Nov 2024)", fontsize=12, fontweight='bold', pad=10)
    ax.legend(fontsize=9, framealpha=0.9)
    ax.set_facecolor('#FAFAFA')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', labelsize=8)
    ax.grid(axis='y', alpha=0.3)


# ─── Assemblage dashboard ─────────────────────────────────────────────────────

def creer_dashboard():
    fig = plt.figure(figsize=(20, 16))
    fig.patch.set_facecolor('#F5F7FA')

    # Titre principal
    fig.suptitle(
        "MEXORA RH INTELLIGENCE — Dashboard Marché IT Marocain 2023–2024",
        fontsize=16, fontweight='bold', y=0.98, color='#1A237E'
    )
    fig.text(0.5, 0.955, "Source : 5 000 offres d'emploi IT (Rekrute, MarocAnnonce, LinkedIn) | Mexora Data Lake",
             ha='center', fontsize=9, color='#546E7A')

    gs = GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.35,
                  left=0.06, right=0.97, top=0.94, bottom=0.06)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    print("[Dashboard] Génération Viz 1 — Carte du Maroc...")
    viz1_carte_maroc(ax1)

    print("[Dashboard] Génération Viz 2 — Top 15 compétences...")
    viz2_top_competences(ax2)

    print("[Dashboard] Génération Viz 3 — Boxplot salaires...")
    viz3_boxplot_salaires(ax3)

    print("[Dashboard] Génération Viz 4 — Évolution mensuelle...")
    viz4_evolution_mensuelle(ax4)

    # Numérotation des panels
    for i, (ax, letter) in enumerate(zip([ax1, ax2, ax3, ax4], ['A', 'B', 'C', 'D'])):
        ax.text(-0.02, 1.02, letter, transform=ax.transAxes,
                fontsize=14, fontweight='bold', color='#1A237E', va='bottom')

    output_path = OUTPUT_DIR / 'dashboard_mexora_rh.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#F5F7FA')
    plt.close()
    print(f"[Dashboard] Sauvegardé : {output_path}")
    return str(output_path)


if __name__ == '__main__':
    creer_dashboard()
    print("[Dashboard] Terminé.")
