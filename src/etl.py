"""
etl.py : fonctions de lecture, de conversion et de consolidation des données (version 1).

Ces fonctions sont utilisées par plusieurs notebooks. Elles sont écrites une seule fois ici,
au lieu d'être copiées d'un notebook à l'autre : si on corrige un défaut, tous les notebooks
en profitent.

    00_inventaire  : lire_csv, typer_ventes, lire_dimension          (observer, sans rien écrire)
    01_etl         : charger_ventes, renommer_colonnes,
                     ajouter_calendrier, joindre_canal_devise,
                     charger_stock, charger_objectifs,
                     charger_ventes_en_ligne, enregistrer_interim    (raw -> interim)
    02_flocon      : lire_dimension, enregistrer_interim             (raw + interim -> interim)

Utilisation dans un notebook :

    from src import config, etl
    ventes, controle = etl.charger_ventes()
"""
import re

import pandas as pd

from src import config


# ===========================================================================
# 1. LECTURE DES FICHIERS
# ===========================================================================

# Encodages essayés, du plus strict au plus permissif :
#   utf-8-sig -> UTF-8, en ignorant le BOM éventuel (marqueur invisible
#                ajouté par Excel au début du fichier)
#   cp1252    -> encodage Windows d'Europe de l'Ouest (accents français)
#   latin-1   -> accepte n'importe quel octet, donc n'échoue jamais :
#                c'est le dernier recours
ENCODAGES = ("utf-8-sig", "cp1252", "latin-1")


def lister_fichiers_ventes(dossier=None):
    """Renvoie la liste triée des fichiers de ventes (Sales *.csv) d'un dossier.

    dossier : dossier à lire. Par défaut config.SALES, c'est-à-dire la source choisie dans
              config.SOURCE_VENTES (ventes complètes ou fichiers du professeur).
              On peut passer config.SALES_PROF ou config.SALES_COMPLET pour lire l'une
              ou l'autre explicitement (utile pour les comparer).

    glob() cherche tous les fichiers dont le nom correspond au motif défini dans config.
    sorted() garantit le même ordre à chaque exécution.
    """
    dossier = config.SALES if dossier is None else dossier
    return sorted(dossier.glob(config.MOTIF_FICHIERS_VENTES))


def periode_du_nom(nom):
    """Extrait (année, trimestre) du nom d'un fichier : 'Sales 2020 T3' -> (2020, 3).

    Renvoie (None, None) si le nom ne respecte pas le format attendu.
    """
    #   (\d{4})  -> 4 chiffres, groupe 1 : l'année
    #   \s*      -> zéro ou plusieurs espaces
    #   T        -> la lettre T
    #   (\d)     -> 1 chiffre, groupe 2 : le trimestre
    m = re.search(r"(\d{4})\s*T(\d)", nom)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def lire_csv(chemin):
    """Lit un CSV en texte brut, en essayant les encodages courants.

    Renvoie un couple (DataFrame, encodage utilisé).
    """
    for enc in ENCODAGES:
        try:
            # dtype=str : toutes les colonnes sont lues comme du texte.
            # pandas ne devine aucun type, donc rien n'est transformé à la lecture
            # (pas de zéros de tête perdus, pas de dates mal interprétées).
            # La conversion des types se fait ensuite, de façon contrôlée (typer_ventes).
            df = pd.read_csv(chemin, dtype=str, encoding=enc)
        except UnicodeDecodeError:
            # Cet encodage ne convient pas : on passe au suivant
            continue

        # Nettoyer les noms de colonnes : retirer les espaces en début et en fin
        # (ex. " Montant " -> "Montant"), sinon deux colonnes identiques
        # seraient considérées comme différentes
        df.columns = df.columns.str.strip()
        return df, enc

    # Atteint seulement si tous les encodages ont échoué
    # (en pratique jamais, puisque latin-1 accepte tout : simple filet de sécurité)
    raise ValueError(f"Encodage non reconnu : {chemin.name}")


def lire_dimension(table):
    """Lit une table de dimension (data/raw/contoso/Dim/<table>.csv).

    Contrairement aux ventes, les types sont devinés par pandas : ces fichiers ont été
    écrits par Extraction.py, leur format est donc connu et propre.
    Renvoie un couple (DataFrame, encodage utilisé).
    """
    chemin = config.DIM / f"{table}.csv"
    for enc in ENCODAGES:
        try:
            # low_memory=False : pandas lit tout le fichier avant de décider du type
            # de chaque colonne (évite les colonnes au type mixte)
            return pd.read_csv(chemin, encoding=enc, low_memory=False), enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Encodage non reconnu : {chemin.name}")


# ===========================================================================
# 2. CONVERSION DES TYPES (texte -> nombre, texte -> date)
# ===========================================================================

def convertir_montant(serie):
    """'$1,062.60 ' -> 1062.60 ; '($5.00)' -> -5.00 ; texte vide -> NaN"""
    # Passer au type texte de pandas et retirer les espaces en début et en fin
    s = serie.astype("string").str.strip()

    # Notation comptable : un montant entre parenthèses est négatif.
    # On mémorise quelles lignes sont concernées AVANT de retirer les parenthèses.
    negatif = s.str.startswith("(") & s.str.endswith(")")

    # Retirer tout ce qui n'est pas le nombre lui-même :
    #   \$ -> symbole dollar     ,  -> séparateur de milliers
    #   \s -> espaces            () -> parenthèses
    # Puis traiter comme valeur manquante le texte vide et le tiret seul
    # (un "-" est souvent utilisé pour dire "pas de montant").
    s = s.str.replace(r"[\$,\s()]", "", regex=True).replace({"": pd.NA, "-": pd.NA})

    # Texte -> nombre. errors="coerce" : ce qui n'est pas convertible devient NaN
    # au lieu de provoquer une erreur.
    valeurs = pd.to_numeric(s, errors="coerce")

    # where(condition, autre) garde la valeur là où la condition est vraie,
    # et met "autre" ailleurs. Donc : on garde la valeur si elle n'est PAS
    # négative (~negatif), sinon on prend son opposé (-valeurs).
    return valeurs.where(~negatif, -valeurs)


# Formats de date essayés, dans l'ordre de préférence :
#   %m/%d/%Y %H:%M     -> 03/25/2020 14:30   (mois/jour, style américain)
#   %d/%m/%Y %H:%M     -> 25/03/2020 14:30   (jour/mois)
#   %Y-%m-%d %H:%M:%S  -> 2020-03-25 14:30:00 (ISO avec heure)
#   %Y-%m-%d           -> 2020-03-25          (ISO sans heure)
FORMATS_DATE = ("%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def convertir_date(serie):
    """Essaie mois/jour puis jour/mois et garde le format qui convertit le plus de valeurs.

    Renvoie un couple (série de dates, format retenu).
    """
    # On convertit la colonne entière avec chaque format candidat.
    # Résultat : un dictionnaire  format -> série convertie
    # (les valeurs qui ne correspondent pas au format deviennent NaT, grâce à "coerce").
    essais = {fmt: pd.to_datetime(serie, format=fmt, errors="coerce") for fmt in FORMATS_DATE}

    # Choisir le format qui a réussi à convertir le plus de valeurs :
    # notna().sum() compte les dates valides obtenues avec chaque format.
    # En cas d'égalité, max() garde le premier de la liste (mois/jour).
    meilleur = max(essais, key=lambda k: essais[k].notna().sum())

    return essais[meilleur], meilleur


def typer_ventes(df):
    """Convertit un fichier de ventes brut (tout en texte) vers les bons types.

    Renvoie un triplet :
      - v       : copie du DataFrame avec la date en datetime, les montants, quantités
                  et identifiants en nombres
      - fmt     : format de date retenu pour ce fichier
      - echecs  : dictionnaire colonne -> nombre de valeurs présentes dans le brut
                  mais non convertibles (colonnes sans échec absentes du dictionnaire)
    """
    # Travailler sur une copie : le brut (df) reste intact, ce qui permet
    # de comparer avant/après
    v = df.copy()

    # Date : on récupère la colonne convertie et le format retenu pour ce fichier
    v[config.COL_DATE], fmt = convertir_date(df[config.COL_DATE])

    # Montants : nettoyage complet ($, virgules, parenthèses)
    for col in config.COLONNES_MONTANTS:
        v[col] = convertir_montant(df[col])

    # Quantités et identifiants : simple conversion après retrait des espaces
    identifiants = [config.COL_VENTE, config.COL_BOUTIQUE, config.COL_PRODUIT, config.COL_PROMOTION]
    for col in config.COLONNES_QUANTITES + identifiants:
        v[col] = pd.to_numeric(df[col].str.strip(), errors="coerce")

    # Contrôle : valeurs présentes dans le brut mais non convertibles.
    # Pour chaque colonne, on compte les lignes où le brut avait une valeur
    # (df[col].notna()) et où le résultat est vide (v[col].isna()).
    # Ce sont les valeurs "perdues" par la conversion. On ne garde que les colonnes
    # ayant au moins un échec (if n).
    echecs = {col: int((df[col].notna() & v[col].isna()).sum()) for col in df.columns}
    echecs = {col: n for col, n in echecs.items() if n}

    return v, fmt, echecs


# ===========================================================================
# 3. CONSOLIDATION DES VENTES (utilisée par 01_etl)
# ===========================================================================

def charger_ventes(dossier=None):
    """Lit, type et empile tous les fichiers de ventes en une seule table.

    dossier : dossier à lire (voir lister_fichiers_ventes). Par défaut, la source choisie
              dans config.SOURCE_VENTES.

    Renvoie un couple :
      - ventes   : toutes les ventes, avec une colonne "fichier" indiquant leur origine
      - controle : une ligne par fichier (encodage, lignes, format de date, échecs)
    """
    morceaux = []   # un DataFrame typé par fichier
    controle = []   # une fiche de contrôle par fichier

    fichiers = lister_fichiers_ventes(dossier)
    if not fichiers:
        # Message clair plutôt qu'une erreur obscure de pandas sur une liste vide
        raise FileNotFoundError(
            f"Aucun fichier de ventes dans {config.SALES if dossier is None else dossier}. "
            "Pour les ventes complètes, lancer d'abord Extraction.py ; "
            "sinon mettre SOURCE_VENTES = \"professeur\" dans src/config.py."
        )

    for f in fichiers:
        brut, enc = lire_csv(f)
        v, fmt, echecs = typer_ventes(brut)

        # Garder la trace du fichier d'origine de chaque ligne (traçabilité)
        v.insert(0, "fichier", f.name)
        morceaux.append(v)

        controle.append({
            "fichier": f.name,
            "encodage": enc,
            "lignes": len(v),
            "format_date": fmt,
            "valeurs_non_converties": sum(echecs.values()),
        })

    # Empiler les fichiers les uns sous les autres.
    # ignore_index=True : on renumérote les lignes de 0 à n-1.
    ventes = pd.concat(morceaux, ignore_index=True)
    return ventes, pd.DataFrame(controle)


# Noms de colonnes après ETL : minuscules, sans accent ni espace (snake_case).
# Ils sont plus simples à écrire dans le code (ventes.montant_ventes) et évitent
# les problèmes d'accents dans Power BI, SQL et les fichiers Parquet.
RENOMMAGE_VENTES = {
    "IdDate": "date",
    "IdVente": "id_vente",
    "IdBoutique": "id_boutique",
    "IdProduit": "id_produit",
    "IdPromotion": "id_promotion",
    "Montant du retour": "montant_retour",
    "Quantité de retour": "quantite_retour",
    "Montant des ventes": "montant_ventes",
    "Quantité de vente": "quantite_vente",
    "Coût total": "cout_total",
    "Coût unitaire": "cout_unitaire",
    "Prix unitaire": "prix_unitaire",
    "Montant de la remise": "montant_remise",
    "Quantité de remise": "quantite_remise",
}


def renommer_colonnes(ventes):
    """Renomme les colonnes des ventes selon RENOMMAGE_VENTES (les autres sont conservées)."""
    return ventes.rename(columns=RENOMMAGE_VENTES)


def ajouter_calendrier(ventes, col_date="date"):
    """Ajoute les colonnes annee, trimestre et mois, déduites de la date.

    Ces colonnes servent aux regroupements simples. Le calendrier complet
    (jours fériés, périodes COVID-19) est construit dans 02_flocon.
    """
    v = ventes.copy()
    v["annee"] = v[col_date].dt.year
    v["trimestre"] = v[col_date].dt.quarter
    v["mois"] = v[col_date].dt.month
    return v


def joindre_canal_devise(ventes, col_vente="id_vente"):
    """Ajoute le canal de vente et la devise à chaque vente (IdVente = FactSales.SalesKey).

    Renvoie un couple (ventes enrichies, nombre de ventes sans correspondance).
    """
    # Le fichier des clés est écrit par Extraction.py dans data/raw/contoso/Sales, à côté des ventes.
    # On le lit à cet endroit précis : une ancienne copie ailleurs dans data/raw ne peut pas être prise par erreur.
    fichier_cles = config.SALES_CONTOSO / config.FICHIER_CLES_CANAL_DEVISE
    if not fichier_cles.exists():
        raise FileNotFoundError(
            f"{fichier_cles} introuvable : lancer Extraction.py"
        )

    cles = pd.read_csv(fichier_cles).rename(columns={
        "SalesKey": col_vente, "channelKey": "id_canal", "CurrencyKey": "id_devise"})

    # Jointure à gauche : on garde toutes nos ventes, même sans correspondance.
    # validate="many_to_one" : pandas vérifie qu'une clé n'apparaît qu'une fois
    # dans le fichier des clés, sinon la jointure dupliquerait des ventes.
    v = ventes.merge(cles, on=col_vente, how="left", validate="many_to_one")

    sans_correspondance = int(v["id_canal"].isna().sum())
    return v, sans_correspondance


# ===========================================================================
# 4. AUTRES TABLES DE FAITS (utilisées par 01_etl)
# ===========================================================================
# Ces trois tables sont écrites par Extraction.py au format Parquet, donc déjà typées : il n'y a
# aucune conversion à faire, seulement des noms à harmoniser avec ceux des ventes (snake_case).
# La colonne DateContoso (date d'origine, avant le décalage de +12 ans) n'est pas reprise :
# elle reste dans le fichier brut.

RENOMMAGE_STOCK = {
    "Date": "date",
    "IdBoutique": "id_boutique",
    "IdProduit": "id_produit",
    "QuantiteEnStock": "quantite_en_stock",
    "QuantiteEnCommande": "quantite_en_commande",
    "StockDeSecurite": "stock_de_securite",
    "CoutUnitaire": "cout_unitaire",
    "JoursEnStock": "jours_en_stock",
    "JoursEnStockMin": "jours_en_stock_min",
    "JoursEnStockMax": "jours_en_stock_max",
    "Anciennete": "anciennete",
}

RENOMMAGE_OBJECTIFS = {
    "Date": "date",
    "IdBoutique": "id_boutique",
    "IdProduit": "id_produit",
    "ChannelKey": "id_canal",
    "ScenarioKey": "id_scenario",
    "QuantiteObjectif": "quantite_objectif",
    "VentesObjectif": "ventes_objectif",
    "MargeObjectif": "marge_objectif",
}

RENOMMAGE_EN_LIGNE = {
    "IdVenteEnLigne": "id_vente_en_ligne",
    "Date": "date",
    "IdBoutique": "id_boutique",
    "IdProduit": "id_produit",
    "IdPromotion": "id_promotion",
    "IdClient": "id_client",
    "NumeroCommande": "numero_commande",
    "LigneCommande": "ligne_commande",
    "QuantiteVente": "quantite_vente",
    "PrixUnitaire": "prix_unitaire",
    "CoutUnitaire": "cout_unitaire",
    "MontantVentes": "montant_ventes",
    "CoutTotal": "cout_total",
    "QuantiteRemise": "quantite_remise",
    "MontantRemise": "montant_remise",
    "QuantiteRetour": "quantite_retour",
    "MontantRetour": "montant_retour",
}


def _lire_parquet(chemin, renommage):
    """Lit un fichier Parquet écrit par Extraction.py et ne garde que les colonnes renommées, dans l'ordre du dictionnaire."""
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} introuvable : lancer Extraction.py")
    df = pd.read_parquet(chemin)
    absentes = [c for c in renommage if c not in df.columns]
    if absentes:
        raise KeyError(f"Colonnes attendues absentes de {chemin.name} : {absentes}")
    return df[list(renommage)].rename(columns=renommage)


def charger_stock():
    """Stock hebdomadaire (FactInventory) : une ligne par boutique, produit et semaine."""
    return _lire_parquet(config.STOCK / config.FICHIER_STOCK, RENOMMAGE_STOCK)


def charger_objectifs():
    """Objectifs de vente (FactSalesQuota) : une ligne par boutique, produit, mois et scénario."""
    return _lire_parquet(config.PLAN / config.FICHIER_OBJECTIFS, RENOMMAGE_OBJECTIFS)


def charger_ventes_en_ligne():
    """Ventes en ligne détaillées (FactOnlineSales) : une ligne par ligne de commande d'un client.

    Renvoie un couple (table, contrôle) comme charger_ventes : le contrôle donne le nombre de lignes de chaque fichier.
    """
    fichiers = sorted(config.SALES_CONTOSO.glob(config.MOTIF_FICHIERS_EN_LIGNE))
    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier {config.MOTIF_FICHIERS_EN_LIGNE} dans {config.SALES_CONTOSO} : lancer Extraction.py")
    morceaux, controle = [], []
    for f in fichiers:
        morceau = _lire_parquet(f, RENOMMAGE_EN_LIGNE)
        morceaux.append(morceau)
        controle.append({"fichier": f.name, "lignes": len(morceau)})
    return pd.concat(morceaux, ignore_index=True), pd.DataFrame(controle)


def enregistrer_interim(df, nom, sous_dossier=None):
    """Enregistre une table dans data/interim/<nom>.parquet et renvoie le chemin.

    sous_dossier : nom d'un sous-dossier de data/interim (ex. "dimensions_realignees").

    Le format Parquet conserve les types (dates, entiers, décimaux), contrairement au CSV
    où tout redevient du texte. Il est aussi plus compact et plus rapide à relire.
    """
    dossier = config.INTERIM / sous_dossier if sous_dossier else config.INTERIM
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{nom}.parquet"
    df.to_parquet(chemin, index=False)
    return chemin
