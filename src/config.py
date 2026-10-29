"""
Configuration commune du projet 4 : analyse des données de vente et retours.

Tous les chemins du projet sont définis ici. Les notebooks et scripts les importent
au lieu de les écrire en dur :

    from src import config
    config.SALES            # data/raw/contoso/Sales
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Racine du projet : le dossier qui contient src/ (donc « Projet ADD »)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------
DATA = ROOT / "data"

RAW = DATA / "raw"                      # 1. BRUT : jamais modifié
#
#   data/raw/
#   ├── professeur/     les 6 fichiers fournis par le professeur (jamais modifiés, jamais régénérés)
#   ├── contexte/       jours fériés et sévérité COVID-19 (Contexte.py)
#   └── contoso/        tout ce qui est extrait de la base Contoso par Extraction.py
#       ├── Dim/        tables de dimension
#       ├── Sales/      ventes (FactSales) par trimestre, clés canal et devise,
#       │               et ventes en ligne détaillées (FactOnlineSales) par année
#       ├── Plan/       charges (FactStrategyPlan) et objectifs de vente (FactSalesQuota)
#       └── Stock/      stock hebdomadaire (FactInventory)
#
# Chaque dossier de contoso couvre toutes les années extraites : il n'y a pas de dossier par année.
PROFESSEUR = RAW / "professeur"
CONTOSO = RAW / "contoso"
DIM = CONTOSO / "Dim"
SALES_CONTOSO = CONTOSO / "Sales"
PLAN = CONTOSO / "Plan"
STOCK = CONTOSO / "Stock"
ANCIEN = RAW / "_ancien"                # anciens dossiers, rangés là par Extraction.py lors du passage à cette structure

# Deux sources de ventes, toutes deux au même format (mêmes 14 colonnes, mêmes noms de fichiers) :
#   SALES_PROF    : fichiers fournis par le professeur. C'est la table FactSales de nos 56 boutiques,
#                   LIMITÉE à 5 catégories de produits sur 8 et aux trimestres 1 à 3 de 2020 et 2021
#                   (144 874 lignes, environ 37 % du chiffre d'affaires de ces deux années).
#   SALES_COMPLET : toutes les lignes de FactSales pour ces mêmes boutiques, sur toutes les années
#                   extraites (8 catégories, tous les trimestres). Écrit par Extraction.py.
SALES_PROF = PROFESSEUR
SALES_COMPLET = SALES_CONTOSO

# Source utilisée par tous les notebooks : "complet" ou "professeur".
# On travaille sur les ventes complètes : elles seules correspondent aux charges du plan
# stratégique (FactStrategyPlan) et donnent des totaux exacts.
# Pour revenir au périmètre du professeur, mettre "professeur" et relancer les notebooks.
SOURCE_VENTES = "complet"
SALES = SALES_COMPLET if SOURCE_VENTES == "complet" else SALES_PROF
CONTEXTE = RAW / "contexte"             # jours fériés, périodes COVID-19

INTERIM = DATA / "interim"              # 2. TRANSFORMÉ : pas encore nettoyé
DIM_REALIGNEES = INTERIM / "dimensions_realignees"

CLEAN = DATA / "clean"                  # 3. VALIDÉ : prêt pour l'analyse
CLEAN_DIMENSIONS = CLEAN / "dimensions"
AGREGATS = CLEAN / "agregats"

OUTPUTS = DATA / "outputs"              # 4. RÉSULTATS : lus par Power BI et Excel
PREDICTIONS = OUTPUTS / "predictions"
SCENARIOS = OUTPUTS / "scenarios"
OPTIMISATION = OUTPUTS / "optimisation"

# ---------------------------------------------------------------------------
# Livrables
# ---------------------------------------------------------------------------
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
LIVRABLES = REPORTS / "livrables"
L1_L2 = LIVRABLES / "L1_L2_phases_backlog"
L3 = LIVRABLES / "L3_diagnostic_nettoyage"
L4 = LIVRABLES / "L4_analyse"
L5 = LIVRABLES / "L5_rapport_final"
PRESENTATIONS = REPORTS / "presentations"
DASHBOARDS = ROOT / "dashboards"

# ---------------------------------------------------------------------------
# Paramètres métier
# ---------------------------------------------------------------------------
# Les données fournies correspondent à FactSales de Contoso (2008-2009),
# décalées de 12 ans (2020-2021). Toutes les dates Contoso sont réalignées de +12 ans.
DECALAGE_ANNEES = 12

# Période attendue d'après l'énoncé : ventes trimestrielles 2020 et 2021
ANNEES_ATTENDUES = [2020, 2021]
# Année de référence : la base Contoso contient une année de plus (2007, donc 2019 après décalage).
# Elle n'est pas dans le périmètre de l'énoncé : elle sert de point de comparaison, pour dire
# d'où vient la situation de 2020 et 2021.
ANNEE_REFERENCE = 2019
# Années étudiées : la référence, puis le périmètre de l'énoncé. Ce sont les années extraites de la
# base par Extraction.py et chargées par tous les notebooks.
ANNEES_ETUDE = [ANNEE_REFERENCE] + ANNEES_ATTENDUES
ANNEES_EXTRAITES = ANNEES_ETUDE
# Dernier exercice : c'est sur lui que sont chiffrés la situation de l'entreprise et les leviers
EXERCICE = max(ANNEES_ETUDE)
TRIMESTRES_ATTENDUS = [1, 2, 3, 4]

# Fichiers de ventes : « Sales 2020 T1.csv », « Sales 2021 T3.csv »…
MOTIF_FICHIERS_VENTES = "Sales *.csv"

# Colonnes des fichiers de ventes (dans l'ordre fourni par le professeur)
COL_DATE = "IdDate"
COL_VENTE = "IdVente"
COL_BOUTIQUE = "IdBoutique"
COL_PRODUIT = "IdProduit"
COL_PROMOTION = "IdPromotion"

COLONNES_MONTANTS = [                   # texte « $1,062.60 » à convertir en nombre
    "Montant du retour",
    "Montant des ventes",
    "Coût total",
    "Coût unitaire",
    "Prix unitaire",
    "Montant de la remise",
]
COLONNES_QUANTITES = [
    "Quantité de retour",
    "Quantité de vente",
    "Quantité de remise",
]

# Tables de dimension retenues (sélection justifiée par l'analyse des clés étrangères)
TABLES_DIMENSION = [
    "DimStore", "DimGeography",
    "DimProduct", "DimProductSubcategory", "DimProductCategory",
    "DimPromotion", "DimDate", "DimChannel", "DimCurrency",
]

# Correspondance entre les clés de nos ventes et celles de Contoso
CORRESPONDANCE_CLES = {
    COL_BOUTIQUE: ("DimStore", "StoreKey"),
    COL_PRODUIT: ("DimProduct", "ProductKey"),
    COL_PROMOTION: ("DimPromotion", "PromotionKey"),
}

# Tables qui décrivent le plan stratégique (comptes, scénarios, lien entre boutique et entité)
TABLES_PLAN = ["DimAccount", "DimScenario", "DimEntity"]
# Tables examinées pour le diagnostic : clients (rattachés aux seules ventes en ligne détaillées)
# et employés (aucune clé vers une boutique)
TABLES_COMPLEMENT = ["DimCustomer", "DimEmployee"]

# Fichiers écrits par Extraction.py
FICHIER_CLES_CANAL_DEVISE = "FactSales_cles_canal_devise.csv"   # canal et devise de chaque vente (IdVente = SalesKey)
MOTIF_FICHIERS_EN_LIGNE = "FactOnlineSales *.parquet"           # ventes en ligne détaillées, un fichier par année
FICHIER_PLAN = "FactStrategyPlan.csv"                           # charges par boutique, mois, scénario, compte, catégorie
FICHIER_OBJECTIFS = "FactSalesQuota.parquet"                    # objectifs de vente par boutique, produit et mois
FICHIER_STOCK = "FactInventory.parquet"                         # stock hebdomadaire par boutique et produit

# ---------------------------------------------------------------------------
# Paramètres du modèle en flocon (02_flocon) et des données de contexte (Contexte.py)
# ---------------------------------------------------------------------------
# Calendrier de l'étude : du premier au dernier jour des années étudiées
DATE_DEBUT = f"{min(ANNEES_ETUDE)}-01-01"
DATE_FIN = f"{max(ANNEES_ETUDE)}-12-31"

# Colonnes de dates des dimensions Contoso à réaligner de +DECALAGE_ANNEES
# (les colonnes techniques LoadDate et UpdateDate ne sont pas des dates métier)
DATES_A_REALIGNER = {
    "DimStore": ["OpenDate", "CloseDate", "LastRemodelDate"],
    "DimProduct": ["AvailableForSaleDate", "StopSaleDate"],
    "DimPromotion": ["StartDate", "EndDate"],
}

# Pays des boutiques présentes dans nos ventes (DimGeography.RegionCountryName)
#   nom dans Contoso -> (code ISO à 2 lettres, code ISO à 3 lettres)
# Le code à 2 lettres sert à la bibliothèque "holidays" (jours fériés),
# le code à 3 lettres au jeu de données OxCGRT (sévérité des mesures COVID-19).
PAYS_ISO = {
    "Denmark": ("DK", "DNK"),
    "France": ("FR", "FRA"),
    "Germany": ("DE", "DEU"),
    "Greece": ("GR", "GRC"),
    "Ireland": ("IE", "IRL"),
    "Italy": ("IT", "ITA"),
    "Malta": ("MT", "MLT"),
    "Poland": ("PL", "POL"),
    "Portugal": ("PT", "PRT"),
    "Romania": ("RO", "ROU"),
    "Russia": ("RU", "RUS"),
    "Slovenia": ("SI", "SVN"),
    "Spain": ("ES", "ESP"),
    "Sweden": ("SE", "SWE"),
    "Switzerland": ("CH", "CHE"),
    "United Kingdom": ("GB", "GBR"),
    "the Netherlands": ("NL", "NLD"),
}

# Fichiers de contexte (data/raw/contexte), produits par Contexte.py
FICHIER_JOURS_FERIES = "jours_feries.csv"
FICHIER_SEVERITE_COVID = "severite_covid.csv"
# Fichier source OxCGRT téléchargé à la main et déposé dans data/raw/contexte
MOTIF_OXCGRT = "OxCGRT*.csv"

# ---------------------------------------------------------------------------
# Connexion SQL Server (utilisée par Extraction.py)
# ---------------------------------------------------------------------------
SQL_DRIVER = "ODBC Driver 17 for SQL Server"
SQL_SERVER = r"YACINE-LAPTOP\SQLEXPRESS"
SQL_DATABASE = "ContosoRetailDW"


def creer_dossiers():
    """Crée tous les dossiers du projet s'ils n'existent pas encore."""
    for dossier in [PROFESSEUR, DIM, SALES_CONTOSO, PLAN, STOCK, CONTEXTE, DIM_REALIGNEES, CLEAN_DIMENSIONS, AGREGATS,
                    PREDICTIONS, SCENARIOS, OPTIMISATION, FIGURES, L1_L2, L3, L4, L5,
                    PRESENTATIONS]:
        dossier.mkdir(parents=True, exist_ok=True)
