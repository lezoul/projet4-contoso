"""
Exploration_promotions.py : comprendre le mécanisme des remises grâce au détail des ventes en ligne.

Dans FactSales (table agrégée), une ligne rattachée à une promotion n'a qu'une partie de ses
unités remisées, et on ne sait pas lesquelles ni pourquoi. FactOnlineSales décrit chaque unité
vendue en ligne, avec sa commande et son client : on y cherche la règle.

  P1. Une unité remisée l'est-elle au taux annoncé en entier ?
  P2. Quelle part des unités d'une promotion est remisée ?
  P3. Dans une commande, combien de lignes sont remisées ?
  P4. La remise dépend-elle de la position de la ligne dans la commande ?
  P5. La remise dépend-elle du produit ?
  P6. La remise dépend-elle du client ?
  P7. Que sont les lignes de quantité 0 ?
  B.  Le plan stratégique se rapproche-t-il de FactSales mois par mois ? (point resté ouvert)
  R.  Répartition des ventes en ligne dans le temps (requête longue, placée en dernier)

Lecture seule : ce script ne modifie rien dans la base.
Chaque résultat est affiché et écrit tout de suite dans exploration_promotions.txt.

Lancement, depuis le dossier Projet ADD :  python Exploration_promotions.py
"""
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

from src import config

# ---------------------------------------------------------------------------
# 1. Paramètres de l'exploration
# ---------------------------------------------------------------------------
BOUTIQUE_EN_LIGNE = 306                     # Contoso Europe Online Store (la seule de nos 56 boutiques)
MOIS = ["2008-03-01", "2008-12-01"]         # un mois de promotion de printemps, un mois de promotion des Fêtes
MAX_LIGNES = 400_000                        # sécurité : on ne charge jamais plus que cela par mois
BOUTIQUE_TEST_PLAN = 201                    # Contoso London Store, pour le rapprochement avec le plan

# ---------------------------------------------------------------------------
# 2. Connexion, fichier de résultats et fonctions d'affichage
# ---------------------------------------------------------------------------
conn_str = (
    f"DRIVER={{{config.SQL_DRIVER}}};"
    f"SERVER={config.SQL_SERVER};"
    f"DATABASE={config.SQL_DATABASE};"
    "Trusted_Connection=yes;"
)
engine = create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str))

pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")

fichier = config.ROOT / "exploration_promotions.txt"
fichier.write_text("", encoding="utf-8")


def bloc(titre, contenu, index=False):
    """Affiche un résultat et l'ajoute tout de suite au fichier."""
    texte = "\n" + "=" * 110 + f"\n{titre}\n" + "=" * 110 + "\n"
    texte += contenu if isinstance(contenu, str) else contenu.to_string(index=index)
    print(texte, flush=True)
    with open(fichier, "a", encoding="utf-8") as f:
        f.write(texte + "\n")


def requete(titre, sql):
    """Exécute une requête et enregistre le résultat ; une erreur n'arrête pas les suivantes."""
    try:
        resultat = pd.read_sql(sql, engine)
        bloc(titre, resultat)
        return resultat
    except Exception as erreur:
        bloc(titre, f"ÉCHEC : {str(erreur)[:400]}")
        return None


def analyser_mois(debut):
    """Charge un mois de ventes en ligne de notre boutique et teste les hypothèses P1 à P7."""
    # Dates écrites AAAAMMJJ, sans tiret : seul format que SQL Server lit de la même façon
    # quelle que soit la langue de la session ('2008-03-01' est lu 3 janvier en français).
    fin = (pd.Timestamp(debut) + pd.DateOffset(months=1)).strftime("%Y%m%d")
    debut_sql = pd.Timestamp(debut).strftime("%Y%m%d")
    nom = pd.Timestamp(debut).strftime("%Y-%m")

    # Un seul chargement par mois, puis toutes les analyses se font en mémoire avec pandas
    lignes = pd.read_sql(f"""
        SELECT TOP {MAX_LIGNES}
               o.OnlineSalesKey, o.DateKey, o.ProductKey, o.PromotionKey, o.CustomerKey,
               o.SalesOrderNumber, o.SalesOrderLineNumber,
               o.SalesQuantity, o.ReturnQuantity, o.DiscountQuantity,
               CAST(o.UnitPrice AS float) AS UnitPrice,
               CAST(o.DiscountAmount AS float) AS DiscountAmount,
               CAST(o.SalesAmount AS float) AS SalesAmount,
               p.PromotionName, CAST(p.DiscountPercent AS float) AS DiscountPercent
        FROM FactOnlineSales o
        JOIN DimPromotion p ON p.PromotionKey = o.PromotionKey
        WHERE o.StoreKey = {BOUTIQUE_EN_LIGNE}
          AND o.DateKey >= '{debut_sql}' AND o.DateKey < '{fin}'""", engine)

    bloc(f"[{nom}] Volume chargé",
         f"{len(lignes)} lignes, {lignes.SalesOrderNumber.nunique()} commandes, "
         f"{lignes.CustomerKey.nunique()} clients"
         + (" (plafond atteint : mois tronqué)" if len(lignes) >= MAX_LIGNES else ""))
    if lignes.empty:
        return

    lignes["remisee"] = lignes.DiscountQuantity > 0
    # Taux réellement appliqué à une unité remisée = remise / (prix × unités remisées)
    lignes["taux_unitaire"] = lignes.DiscountAmount / (lignes.UnitPrice * lignes.DiscountQuantity.where(lignes.remisee))

    # P1 et P2 : par promotion
    p12 = lignes.groupby(["PromotionKey", "PromotionName", "DiscountPercent"]).agg(
        lignes=("OnlineSalesKey", "size"),
        unites=("SalesQuantity", "sum"),
        unites_remisees=("DiscountQuantity", "sum"),
        taux_unitaire_min=("taux_unitaire", "min"),
        taux_unitaire_max=("taux_unitaire", "max"),
        remise=("DiscountAmount", "sum"),
        montant_avant_remise=("UnitPrice", lambda s: float((s * lignes.loc[s.index, "SalesQuantity"]).sum())),
    ).reset_index()
    p12["part_unites_remisees"] = p12.unites_remisees / p12.unites
    p12["taux_effectif"] = p12.remise / p12.montant_avant_remise
    bloc(f"[{nom}] P1 et P2. Par promotion : taux appliqué à une unité remisée (min et max), "
         "part des unités remisées, taux effectif", p12.drop(columns=["remise", "montant_avant_remise"]))

    # Les analyses suivantes ne portent que sur les lignes rattachées à une vraie promotion
    promo = lignes[lignes.DiscountPercent > 0]
    if promo.empty:
        bloc(f"[{nom}] P3 à P6", "Aucune ligne rattachée à une promotion ce mois-ci.")
        return

    # P3 : par commande, nombre de lignes et nombre de lignes remisées
    commandes = promo.groupby("SalesOrderNumber").agg(lignes=("remisee", "size"), remisees=("remisee", "sum"))
    p3 = commandes.groupby("remisees").agg(commandes=("lignes", "size"), lignes_moyennes=("lignes", "mean")).reset_index()
    p3["part_des_commandes"] = p3.commandes / p3.commandes.sum()
    bloc(f"[{nom}] P3. Nombre de lignes remisées par commande (lignes en promotion seulement)", p3)

    # P4 : selon la position de la ligne dans la commande
    p4 = promo.groupby("SalesOrderLineNumber").agg(lignes=("remisee", "size"), part_remisee=("remisee", "mean")).reset_index()
    bloc(f"[{nom}] P4. Part de lignes remisées selon la position dans la commande", p4.head(20))

    # P5 et P6 : un produit (ou un client) est-il toujours, jamais, ou parfois remisé ?
    for cle, etiquette in [("ProductKey", "P5. Produits"), ("CustomerKey", "P6. Clients")]:
        part = promo.groupby(cle).remisee.agg(lignes="size", part="mean")
        part = part[part.lignes >= 5]                      # on ignore ceux qui ont trop peu de lignes
        classes = pd.cut(part.part, [-0.001, 0.0, 0.2, 0.4, 0.6, 0.8, 0.999, 1.0],
                         labels=["jamais", "0-20 %", "20-40 %", "40-60 %", "60-80 %", "80-99 %", "toujours"])
        repartition = classes.value_counts().sort_index().rename("nombre").reset_index()
        repartition.columns = ["part de lignes remisées", "nombre"]
        bloc(f"[{nom}] {etiquette} (au moins 5 lignes en promotion) selon leur part de lignes remisées", repartition)

    # P7 : les lignes de quantité 0
    p7 = lignes.groupby(["SalesQuantity", "ReturnQuantity", "DiscountQuantity"]).agg(
        lignes=("OnlineSalesKey", "size"), ventes=("SalesAmount", "sum")).reset_index()
    bloc(f"[{nom}] P7. Combinaisons quantité vendue / retournée / remisée", p7)


# ---------------------------------------------------------------------------
# 3. Analyse des promotions, mois par mois
# ---------------------------------------------------------------------------
for mois in MOIS:
    try:
        analyser_mois(mois)
    except Exception as erreur:
        bloc(f"[{mois[:7]}] ÉCHEC de l'analyse", str(erreur)[:500])

# ---------------------------------------------------------------------------
# 4. B. Plan stratégique contre FactSales, mois par mois, pour une boutique
# ---------------------------------------------------------------------------
requete(f"B1. Boutique {BOUTIQUE_TEST_PLAN}, 2008 : ventes réelles du plan contre FactSales, par mois", f"""
    SELECT COALESCE(pl.mois, fs.mois) AS mois, pl.plan_reel, fs.factsales
    FROM (SELECT CONVERT(char(7), p.Datekey, 126) AS mois, SUM(p.Amount) AS plan_reel
          FROM FactStrategyPlan p
          JOIN DimStore s ON s.EntityKey = p.EntityKey
          WHERE s.StoreKey = {BOUTIQUE_TEST_PLAN} AND p.ScenarioKey = 1 AND p.AccountKey = 4
            AND p.Datekey >= '20080101' AND p.Datekey < '20090101'
          GROUP BY CONVERT(char(7), p.Datekey, 126)) pl
    FULL JOIN (SELECT CONVERT(char(7), DateKey, 126) AS mois, SUM(SalesAmount) AS factsales
               FROM FactSales
               WHERE StoreKey = {BOUTIQUE_TEST_PLAN}
                 AND DateKey >= '20080101' AND DateKey < '20090101'
               GROUP BY CONVERT(char(7), DateKey, 126)) fs ON fs.mois = pl.mois
    ORDER BY mois""")

requete(f"B2. Boutique {BOUTIQUE_TEST_PLAN}, mars 2008 : ventes réelles du plan contre FactSales, par catégorie", f"""
    SELECT c.ProductCategoryKey, c.ProductCategoryName, pl.plan_reel, fs.factsales
    FROM DimProductCategory c
    LEFT JOIN (SELECT p.ProductCategoryKey, SUM(p.Amount) AS plan_reel
               FROM FactStrategyPlan p
               JOIN DimStore s ON s.EntityKey = p.EntityKey
               WHERE s.StoreKey = {BOUTIQUE_TEST_PLAN} AND p.ScenarioKey = 1 AND p.AccountKey = 4
                 AND p.Datekey >= '20080301' AND p.Datekey < '20080401'
               GROUP BY p.ProductCategoryKey) pl ON pl.ProductCategoryKey = c.ProductCategoryKey
    LEFT JOIN (SELECT sc.ProductCategoryKey, SUM(f.SalesAmount) AS factsales
               FROM FactSales f
               JOIN DimProduct pr ON pr.ProductKey = f.ProductKey
               JOIN DimProductSubcategory sc ON sc.ProductSubcategoryKey = pr.ProductSubcategoryKey
               WHERE f.StoreKey = {BOUTIQUE_TEST_PLAN}
                 AND f.DateKey >= '20080301' AND f.DateKey < '20080401'
               GROUP BY sc.ProductCategoryKey) fs ON fs.ProductCategoryKey = c.ProductCategoryKey
    ORDER BY c.ProductCategoryKey""")

requete("B3. Boutique 156 (test resté vide la dernière fois) : ce que le plan contient pour elle en 2008", """
    SELECT CONVERT(char(10), p.Datekey, 126) AS date_plan, p.ScenarioKey, p.AccountKey,
           COUNT(*) AS lignes, SUM(p.Amount) AS montant
    FROM FactStrategyPlan p
    JOIN DimStore s ON s.EntityKey = p.EntityKey
    WHERE s.StoreKey = 156 AND p.ScenarioKey = 1 AND p.AccountKey IN (4, 5)
      AND p.Datekey >= '20080101' AND p.Datekey < '20090101'
    GROUP BY CONVERT(char(10), p.Datekey, 126), p.ScenarioKey, p.AccountKey
    ORDER BY date_plan, p.AccountKey""")

# ---------------------------------------------------------------------------
# 5. R. Répartition des ventes en ligne dans le temps (parcours complet : en dernier)
# ---------------------------------------------------------------------------
# Si cette requête est trop longue, on peut l'interrompre (Ctrl+C) : le reste est déjà enregistré.
print("\nDernière requête (R) : parcours complet de FactOnlineSales, patience...", flush=True)
requete(f"R. Boutique {BOUTIQUE_EN_LIGNE} : lignes de FactOnlineSales par mois, 2008-2009", f"""
    SELECT CONVERT(char(7), DateKey, 126) AS mois, COUNT(*) AS lignes, SUM(SalesAmount) AS ventes
    FROM FactOnlineSales
    WHERE StoreKey = {BOUTIQUE_EN_LIGNE} AND DateKey >= '20080101' AND DateKey < '20100101'
    GROUP BY CONVERT(char(7), DateKey, 126) ORDER BY mois""")

print(f"\nRésultats enregistrés dans : {fichier}")
