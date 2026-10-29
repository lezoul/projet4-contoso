"""
Charte graphique commune du projet 4.

Tous les graphiques du projet (notebooks, rapports, présentations) utilisent les mêmes
couleurs, la même police, le même format des montants et le même enregistrement.
Les couleurs sont celles de la présentation.

Utilisation dans un notebook :

    from src import viz
    viz.appliquer_style()                      # une fois, en début de notebook
    fig, ax = plt.subplots()
    ax.bar(x, y, color=viz.PRINCIPALE)
    viz.format_dollars(ax, axe="y")            # 1 250 000 -> 1,3 M$
    viz.titre(ax, "Chiffre d'affaires par mois", "2020-2021, en millions de $")
    viz.enregistrer(fig, "06_ca_par_mois")     # -> reports/figures/06_ca_par_mois.png
"""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from src import config

# ---------------------------------------------------------------------------
# Palette (identique à la présentation)
# ---------------------------------------------------------------------------
FONCE = "#17332E"        # titres, éléments de référence
PRINCIPALE = "#2E5E55"   # couleur principale des données
ACCENT = "#E9A23B"       # mise en valeur (une seule série à la fois)
ALERTE = "#B5523B"       # anomalies, valeurs négatives, données absentes
GRIS = "#5E6B68"         # textes secondaires, axes
CLAIR = "#EAF2EF"        # fonds, zones grisées
GRILLE = "#E3EBE8"

# Palette catégorielle (catégories de produits, canaux, types de promotion…)
CATEGORIES = ["#2E5E55", "#E9A23B", "#6C8EAD", "#B5523B", "#8FB996", "#7A6C9D", "#C9A66B", "#5E6B68"]

# Dégradé pour les valeurs ordonnées (cartes de chaleur, tranches de remise)
SEQUENTIELLE = ["#EAF2EF", "#B9D3CA", "#7FAE9F", "#4E8575", "#2E5E55", "#17332E"]

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
def appliquer_style():
    """Applique la charte à matplotlib et seaborn (à appeler une fois par notebook)."""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Calibri", "Arial", "DejaVu Sans"],
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlecolor": FONCE,
        "axes.titlelocation": "left",
        "axes.labelcolor": GRIS,
        "axes.edgecolor": GRIS,
        "axes.prop_cycle": mpl.cycler(color=CATEGORIES),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,          # la grille passe derrière les barres
        "grid.color": GRILLE,
        "grid.linewidth": 0.8,
        "xtick.color": GRIS,
        "ytick.color": GRIS,
        "legend.frameon": False,
        "figure.figsize": (11, 5),
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })
    try:
        import seaborn as sns
        sns.set_palette(CATEGORIES)
    except ImportError:
        pass


def titre(ax, texte, sous_titre=None):
    """Titre aligné à gauche, avec un sous-titre gris facultatif (période, unité, source)."""
    ax.set_title(texte, pad=22 if sous_titre else 10)
    if sous_titre:
        ax.text(0, 1.02, sous_titre, transform=ax.transAxes, fontsize=10, color=GRIS, va="bottom")


# ---------------------------------------------------------------------------
# Formats des nombres
# ---------------------------------------------------------------------------
def _dollars(valeur, _pos=None):
    a = abs(valeur)
    if a >= 1e6:
        return f"{valeur / 1e6:,.1f} M$".replace(",", " ").replace(".", ",")
    if a >= 1e3:
        return f"{valeur / 1e3:,.0f} k$".replace(",", " ")
    return f"{valeur:,.0f} $".replace(",", " ")


def format_dollars(ax, axe="y"):
    """Affiche les montants d'un axe en $, k$ ou M$."""
    (ax.yaxis if axe == "y" else ax.xaxis).set_major_formatter(FuncFormatter(_dollars))


def format_pourcent(ax, axe="y", decimales=0):
    """Affiche un axe en pourcentage (valeurs stockées entre 0 et 1)."""
    f = FuncFormatter(lambda v, _p: f"{100 * v:.{decimales}f} %".replace(".", ","))
    (ax.yaxis if axe == "y" else ax.xaxis).set_major_formatter(f)


# ---------------------------------------------------------------------------
# Enregistrement
# ---------------------------------------------------------------------------
def enregistrer(fig, nom):
    """Enregistre la figure dans reports/figures/<nom>.png (même résolution pour tout le projet)."""
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    chemin = config.FIGURES / f"{nom}.png"
    fig.savefig(chemin)
    return chemin


# ---------------------------------------------------------------------------
# Plotly (graphiques interactifs)
# ---------------------------------------------------------------------------
def gabarit_plotly():
    """Gabarit plotly aux couleurs du projet : fig.update_layout(template=viz.gabarit_plotly())"""
    import plotly.graph_objects as go
    return go.layout.Template(layout=dict(
        font=dict(family="Calibri, Arial", size=13, color=GRIS),
        title=dict(font=dict(color=FONCE, size=18), x=0),
        colorway=CATEGORIES,
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, linecolor=GRIS),
        yaxis=dict(gridcolor=GRILLE, zeroline=False),
    ))
