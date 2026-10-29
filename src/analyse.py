"""
Fonctions communes aux notebooks d'analyse (dossier notebooks/2_analyses).

Elles sont regroupées ici pour que les notebooks 06 (Q1), 07 (Q2) et 08 (Q3 et Q4) calculent
les mêmes indicateurs de la même façon, sans recopier le code :

    from src import analyse
    from src.analyse import resumer, afficher, eta2

Contenu
    LIBELLES_TYPES, ORDRE_TYPES, NOMS_MOIS  libellés français et ordres d'affichage
    resumer(df, cles)                       indicateurs de ventes par groupe
    FORMATS, afficher(table)                affichage homogène des tableaux
    eta2(valeurs, groupes)                  part de la variation expliquée par un facteur
    exporter_tableaux(tableaux, chemin)     un classeur Excel, un onglet par tableau
    mann_whitney(a, b)                      test de Mann-Whitney avec sa taille d'effet
    khi2(evenement, facteur)                test du khi-deux avec le V de Cramér
    noter_test, tableau_tests               registre des tests d'hypothèse et correction de Bonferroni
"""
import pandas as pd

# ---------------------------------------------------------------------------
# Libellés et ordres d'affichage
# ---------------------------------------------------------------------------
# Type de boutique : valeur de dim_boutique -> libellé français
LIBELLES_TYPES = {"Online": "En ligne", "Reseller": "Revendeur", "Store": "Magasins"}
ORDRE_TYPES = ["En ligne", "Revendeur", "Magasins"]
NOMS_MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


# ---------------------------------------------------------------------------
# Indicateurs de ventes par groupe
# ---------------------------------------------------------------------------
def resumer(df, cles):
    """Indicateurs de performance des ventes par groupe.

    df   : table des ventes avec les variables de 05_variables
    cles : colonne ou liste de colonnes de regroupement
    Renvoie une ligne par groupe : lignes, unités, chiffre d'affaires net, marge nette des retours,
    puis les ratios, tous recalculés à partir des SOMMES du groupe (jamais une moyenne de taux).
    """
    g = df.groupby(cles, observed=True)
    r = g.agg(nb_lignes=("id_vente", "size"),
              quantite=("quantite_vente", "sum"),
              ca_net=("ca_net", "sum"),
              marge_nette=("marge_nette", "sum"))
    r["part_du_ca"] = r.ca_net / r.ca_net.sum()
    r["part_de_la_marge"] = r.marge_nette / r.marge_nette.sum()
    r["taux_de_marge"] = r.marge_nette / r.ca_net
    r["ca_par_ligne"] = r.ca_net / r.nb_lignes
    r["prix_moyen_par_unite"] = r.ca_net / r.quantite
    return r


# ---------------------------------------------------------------------------
# Affichage homogène des tableaux
# ---------------------------------------------------------------------------
# Format d'affichage de chaque colonne produite par resumer()
FORMATS = {"nb_lignes": "{:,.0f}", "quantite": "{:,.0f}", "ca_net": "{:,.0f}", "marge_nette": "{:,.0f}",
           "part_du_ca": "{:.1%}", "part_de_la_marge": "{:.1%}", "taux_de_marge": "{:.1%}",
           "ca_par_ligne": "{:,.0f}", "prix_moyen_par_unite": "{:,.2f}"}


def afficher(table, formats_en_plus=None):
    """Affiche un tableau avec les formats communs, complétés au besoin.

    formats_en_plus : dictionnaire colonne -> format, pour les colonnes propres à un notebook.
    """
    from IPython.display import display          # importé ici : le module reste utilisable hors notebook
    formats = {**FORMATS, **(formats_en_plus or {})}
    display(table.style.format({c: f for c, f in formats.items() if c in table.columns}))


# ---------------------------------------------------------------------------
# Poids d'un facteur
# ---------------------------------------------------------------------------
def eta2(valeurs, groupes):
    """Part de la variation de `valeurs` expliquée par l'appartenance aux `groupes`.

    C'est le rapport de corrélation η² de l'analyse de variance :
        η² = variation entre les groupes ÷ variation totale
    0 : les groupes ont tous la même moyenne. 1 : le groupe suffit à connaître la valeur.
    """
    moyenne = valeurs.mean()
    g = valeurs.groupby(groupes, observed=True)
    entre_groupes = (g.size() * (g.mean() - moyenne) ** 2).sum()
    totale = ((valeurs - moyenne) ** 2).sum()
    return float(entre_groupes / totale)


# ---------------------------------------------------------------------------
# Export des tableaux vers Excel
# ---------------------------------------------------------------------------
def exporter_tableaux(tableaux, chemin):
    """Écrit un classeur Excel avec un onglet par tableau.

    tableaux : dictionnaire nom de l'onglet -> tableau
    chemin   : chemin du fichier .xlsx à écrire
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(chemin, engine="openpyxl") as classeur:
        for onglet, table in tableaux.items():
            # Excel prend pour une formule tout texte qui commence par "=" : on retire ce signe des libellés
            if table.index.nlevels == 1:
                table = table.rename(index=lambda v: v.lstrip("= ") if isinstance(v, str) else v)
            table.to_excel(classeur, sheet_name=onglet[:31])     # un nom d'onglet Excel fait au plus 31 caractères
    return chemin


# ---------------------------------------------------------------------------
# Tests d'hypothèse : taille d'effet et registre des tests
# ---------------------------------------------------------------------------
# Avec plusieurs centaines de milliers de lignes, presque tout écart est "statistiquement significatif".
# On note donc toujours, à côté de la valeur p, la TAILLE de l'effet, et on corrige le seuil
# quand on fait plusieurs tests (correction de Bonferroni : seuil ÷ nombre de tests).
def mann_whitney(a, b):
    """Test de Mann-Whitney entre deux groupes, avec sa taille d'effet.

    Renvoie (effet, p). L'effet est la corrélation bisériale de rang, entre −1 et +1 :
        effet = 2 × P(une valeur de a dépasse une valeur de b) − 1
    0 : les deux groupes se valent. +1 : toutes les valeurs de a dépassent celles de b.
    """
    from scipy import stats                      # importé ici : scipy n'est nécessaire que pour les tests
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return float(2 * u / (len(a) * len(b)) - 1), float(p)


def noter_test(registre, question, h0, test, n, effet, p):
    """Ajoute un test au registre (une liste) et affiche son résultat sur une ligne.

    question : ce qu'on cherche à savoir
    h0       : l'hypothèse nulle, en clair
    test     : nom du test utilisé
    n        : nombre d'observations
    effet    : taille de l'effet, déjà mise en forme (texte)
    p        : valeur p brute
    """
    registre.append({"question": question, "hypothèse nulle (H0)": h0, "test": test,
                     "n": n, "taille de l'effet": effet, "p": p})
    # Une valeur p trop petite pour être représentée par l'ordinateur s'affiche 0 : on l'écrit "< 1e-300"
    p_texte = "< 1e-300" if p == 0 else f"= {p:.2g}"
    print(f"[{test}] {question} · n = {n} · effet : {effet} · p {p_texte}")


def tableau_tests(registre, alpha=0.05):
    """Tableau récapitulatif du registre, avec la correction de Bonferroni.

    Un test est retenu si p < alpha ÷ nombre de tests du registre.
    """
    t = pd.DataFrame(registre)
    seuil = alpha / len(t)
    t["seuil corrigé"] = seuil
    t["décision"] = t.p.map(lambda p: "H0 rejetée" if p < seuil else "H0 conservée")
    return t


def khi2(evenement, facteur):
    """Test du khi-deux d'indépendance entre un événement (oui ou non) et un facteur, avec sa taille d'effet.

    Renvoie (v, p). La taille d'effet est le V de Cramér, entre 0 et 1 :
        V = racine( khi² ÷ (n × (min(lignes, colonnes) − 1)) )
    0 : l'événement est aussi fréquent dans tous les groupes. 1 : le groupe suffit à connaître l'événement.
    Repères usuels : 0,1 petit effet, 0,3 effet moyen, 0,5 grand effet.
    """
    from scipy import stats
    table = pd.crosstab(facteur, evenement)
    statistique, p, _, _ = stats.chi2_contingency(table)
    v = (statistique / (table.values.sum() * (min(table.shape) - 1))) ** 0.5
    return float(v), float(p)
