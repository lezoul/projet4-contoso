"""
extraction.py : extraction unique de toutes les données Contoso du projet, depuis SQL Server.

Remplace Connexion.py, Extraction_charges.py et Extraction_2019_stock.py.

Périmètre : nos 56 boutiques (celles des fichiers du professeur) et toutes les années de
config.ANNEES_EXTRAITES (2019 à 2021, soit 2007 à 2009 dans la base : les dates sont décalées de +12 ans).

Produit, dans data/raw/contoso :
  Dim/    les tables de dimension (ventes, plan stratégique, clients et employés)
  Sales/  Sales AAAA Tn.csv                  ventes (FactSales), un fichier par trimestre, au format du professeur
          FactSales_cles_canal_devise.csv    canal et devise de chaque vente
          FactOnlineSales AAAA.parquet       ventes en ligne détaillées (client, commande), un fichier par année
  Plan/   FactStrategyPlan.csv               charges par boutique, mois, scénario, compte et catégorie
          FactSalesQuota.parquet             objectifs de vente par boutique, produit et mois
  Stock/  FactInventory.parquet              stock hebdomadaire par boutique et produit

Ce que le script efface : uniquement ses propres fichiers dans Sales/, Plan/ et Stock/, pour ne jamais
mélanger deux extractions. Il ne touche jamais à data/raw/professeur ni à data/raw/contexte.

Premier lancement après l'ancienne organisation : les anciens dossiers (Sales_complet, Sales_2019,
Plan_2019, Objectifs, Ventes_en_ligne...) sont DÉPLACÉS dans data/raw/_ancien, pas supprimés.
Une fois les notebooks relancés et vérifiés, supprimer data/raw/_ancien à la main.

Lancement, depuis le dossier Projet ADD :  python -m src.extraction
Durée : une dizaine de minutes. Lecture seule sur la base.
"""
import shutil
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

from src import config, etl

DECALAGE = pd.DateOffset(years=config.DECALAGE_ANNEES)
ANNEES_CONTOSO = [annee - config.DECALAGE_ANNEES for annee in config.ANNEES_EXTRAITES]      # 2007, 2008, 2009


def titre(texte):
    print(f"\n=== {texte} ===")


def nombre(valeur, decimales=0):
    """12345678.9 -> '12 345 679' (séparateur de milliers : espace)."""
    return f"{valeur:,.{decimales}f}".replace(",", " ")


def bornes(annee_contoso):
    """Bornes d'une année pour SQL Server, écrites AAAAMMJJ sans tiret : c'est le seul format lu de la
    même façon quelle que soit la langue de la session (en français, '2008-03-01' est lu comme le 3 janvier)."""
    return f"'{annee_contoso}0101'", f"'{annee_contoso + 1}0101'"


def decaler(serie):
    """Date Contoso -> date du projet (+12 ans)."""
    return pd.to_datetime(serie) + DECALAGE


# ---------------------------------------------------------------------------
# 0. Passage de l'ancienne organisation des dossiers à la nouvelle (ne fait rien si c'est déjà fait)
# ---------------------------------------------------------------------------
def migrer_ancienne_structure():
    """Range les anciens dossiers dans data/raw/_ancien et met les fichiers du professeur à leur place.

    Ancienne organisation reconnue à la présence de data/raw/contoso/Sales_complet.
    Rien n'est supprimé : tout est déplacé, et les fichiers du professeur sont d'abord COPIÉS.
    """
    ancien_complet = config.CONTOSO / "Sales_complet"
    if not ancien_complet.exists():
        return
    titre("0. Nouvelle organisation des dossiers")
    config.ANCIEN.mkdir(parents=True, exist_ok=True)

    # a) Les fichiers du professeur étaient dans contoso/Sales : on les copie dans data/raw/professeur
    ancien_prof = config.CONTOSO / "Sales"
    config.PROFESSEUR.mkdir(parents=True, exist_ok=True)
    if ancien_prof.exists() and not any(config.PROFESSEUR.glob(config.MOTIF_FICHIERS_VENTES)):
        for fichier in sorted(ancien_prof.glob(config.MOTIF_FICHIERS_VENTES)):
            shutil.copy2(fichier, config.PROFESSEUR / fichier.name)
            print(f"  copié    {fichier.name} -> {config.PROFESSEUR.relative_to(config.RAW)}")
    nb_prof = len(list(config.PROFESSEUR.glob(config.MOTIF_FICHIERS_VENTES)))
    if nb_prof == 0:
        raise FileNotFoundError(f"Aucun fichier du professeur trouvé dans {ancien_prof} ni dans {config.PROFESSEUR}")
    print(f"  {nb_prof} fichiers du professeur dans {config.PROFESSEUR.relative_to(config.RAW)}")

    # b) Les anciens dossiers de contoso sont déplacés dans _ancien (Dim reste en place : il est réécrit)
    for nom in ["Sales", "Sales_complet", "Sales_2019", "Plan", "Plan_2019", "Objectifs", "Ventes_en_ligne", "Stock"]:
        dossier = config.CONTOSO / nom
        if dossier.exists():
            cible = config.ANCIEN / nom
            if cible.exists():
                raise FileExistsError(f"{cible} existe déjà : vider ou renommer data/raw/_ancien avant de relancer")
            shutil.move(str(dossier), str(cible))
            print(f"  déplacé  contoso/{nom} -> _ancien/{nom}")


def vider(dossier, motifs):
    """Efface, dans un dossier, les fichiers écrits par une extraction précédente (et rien d'autre)."""
    dossier.mkdir(parents=True, exist_ok=True)
    for motif in motifs:
        for fichier in dossier.glob(motif):
            fichier.unlink()


def main():
    migrer_ancienne_structure()
    config.creer_dossiers()

    # -----------------------------------------------------------------------
    # 1. Connexion à SQL Server (paramètres dans src/config.py)
    # -----------------------------------------------------------------------
    conn_str = (f"DRIVER={{{config.SQL_DRIVER}}};SERVER={config.SQL_SERVER};"
                f"DATABASE={config.SQL_DATABASE};Trusted_Connection=yes;")
    engine = create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str))

    # -----------------------------------------------------------------------
    # 2. Nos boutiques : celles des fichiers du professeur (le périmètre du projet ne change pas)
    # -----------------------------------------------------------------------
    titre("1. Périmètre")
    ventes_prof, _ = etl.charger_ventes(config.SALES_PROF)
    boutiques = sorted(int(b) for b in ventes_prof[config.COL_BOUTIQUE].unique())
    liste_boutiques = ",".join(str(b) for b in boutiques)
    print(f"  {len(boutiques)} boutiques, d'après les fichiers du professeur")
    print(f"  Années : {config.ANNEES_EXTRAITES} (dans la base : {ANNEES_CONTOSO})")
    debut, _ = bornes(min(ANNEES_CONTOSO))
    _, fin = bornes(max(ANNEES_CONTOSO))

    # -----------------------------------------------------------------------
    # 3. Tables de dimension -> Dim/
    # -----------------------------------------------------------------------
    titre("2. Tables de dimension")
    tables = config.TABLES_DIMENSION + config.TABLES_PLAN + config.TABLES_COMPLEMENT
    liste_sql = ",".join(f"'{t}'" for t in tables)
    colonnes = pd.read_sql(f"""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME IN ({liste_sql})
        ORDER BY TABLE_NAME, ORDINAL_POSITION""", engine)

    def requete(table):
        """SELECT qui convertit les types non lisibles par pyodbc (geography, geometry, hierarchyid)."""
        parties = []
        for _, c in colonnes[colonnes.TABLE_NAME == table].iterrows():
            nom = f"[{c.COLUMN_NAME}]"
            if c.DATA_TYPE in ("geography", "geometry"):
                parties.append(f"{nom}.STAsText() AS {nom}")
            elif c.DATA_TYPE == "hierarchyid":
                parties.append(f"{nom}.ToString() AS {nom}")
            else:
                parties.append(nom)
        return f"SELECT {', '.join(parties)} FROM [{table}]"

    for table in tables:
        try:
            df = pd.read_sql(requete(table), engine)
            df.to_csv(config.DIM / f"{table}.csv", index=False, encoding="utf-8-sig")
            print(f"  OK      {table:25s} {df.shape[0]:>6} lignes  {df.shape[1]:>3} colonnes")
        except Exception as e:
            print(f"  ÉCHEC   {table:25s} {str(e)[:120]}")

    # -----------------------------------------------------------------------
    # 4. Ventes (FactSales) -> Sales/ : un fichier par trimestre, au format des fichiers du professeur
    # -----------------------------------------------------------------------
    titre("3. Ventes (FactSales)")
    vider(config.SALES_CONTOSO, [config.MOTIF_FICHIERS_VENTES, config.FICHIER_CLES_CANAL_DEVISE, config.MOTIF_FICHIERS_EN_LIGNE])
    # Les montants sont convertis en nombres décimaux par la base (CAST) : sinon pandas reçoit des objets
    # Decimal, lents à écrire. Les 14 premières colonnes sont celles des fichiers du professeur, dans le même ordre.
    ventes = pd.read_sql(f"""
        SELECT DateKey                        AS [IdDate],
               SalesKey                       AS [IdVente],
               StoreKey                       AS [IdBoutique],
               ProductKey                     AS [IdProduit],
               PromotionKey                   AS [IdPromotion],
               CAST(ReturnAmount AS float)    AS [Montant du retour],
               ReturnQuantity                 AS [Quantité de retour],
               CAST(SalesAmount AS float)     AS [Montant des ventes],
               SalesQuantity                  AS [Quantité de vente],
               CAST(TotalCost AS float)       AS [Coût total],
               CAST(UnitCost AS float)        AS [Coût unitaire],
               CAST(UnitPrice AS float)       AS [Prix unitaire],
               CAST(DiscountAmount AS float)  AS [Montant de la remise],
               DiscountQuantity               AS [Quantité de remise],
               channelKey, CurrencyKey
        FROM FactSales
        WHERE StoreKey IN ({liste_boutiques}) AND DateKey >= {debut} AND DateKey < {fin}
        ORDER BY DateKey, SalesKey""", engine)
    ventes["IdDate"] = decaler(ventes["IdDate"])
    colonnes_prof = [c for c in ventes.columns if c not in ("channelKey", "CurrencyKey")]

    # a) Canal et devise de chaque vente (IdVente = SalesKey), pour nos boutiques seulement
    (ventes[["IdVente", "channelKey", "CurrencyKey"]].rename(columns={"IdVente": "SalesKey"})
     .to_csv(config.SALES_CONTOSO / config.FICHIER_CLES_CANAL_DEVISE, index=False))
    print(f"  OK      {config.FICHIER_CLES_CANAL_DEVISE}  {nombre(len(ventes))} lignes · devises : {sorted(int(d) for d in ventes.CurrencyKey.unique())}")

    # b) Un fichier par trimestre : « Sales 2019 T1.csv » ... « Sales 2021 T4.csv »
    for (annee, trimestre), morceau in ventes.groupby([ventes.IdDate.dt.year, ventes.IdDate.dt.quarter]):
        morceau = morceau[colonnes_prof].copy()
        morceau["IdDate"] = morceau["IdDate"].dt.strftime("%Y-%m-%d")       # format lu par etl.convertir_date
        chemin = config.SALES_CONTOSO / f"Sales {annee} T{trimestre}.csv"
        morceau.to_csv(chemin, index=False, encoding="utf-8-sig")
        print(f"  OK      {chemin.name:20s} {len(morceau):>7} lignes")

    # c) Contrôles : totaux par année, et fichiers du professeur contenus dans les ventes complètes
    ventes_par_annee = ventes.groupby(ventes.IdDate.dt.year).agg(
        lignes=("IdVente", "size"), boutiques=("IdBoutique", "nunique"), produits=("IdProduit", "nunique"),
        ventes=("Montant des ventes", "sum"), cout=("Coût total", "sum"))
    print(ventes_par_annee.to_string(float_format=lambda v: nombre(v, 2)))
    retrouvees = ventes_prof[config.COL_VENTE].isin(ventes["IdVente"]).mean()
    print(f"  Lignes du professeur retrouvées dans les ventes complètes : {retrouvees:.2%} "
          f"({nombre(len(ventes_prof))} lignes du professeur, {nombre(len(ventes))} extraites)")
    total_ventes = ventes.groupby(ventes.IdDate.dt.year)["Montant des ventes"].sum()
    del ventes

    # -----------------------------------------------------------------------
    # 5. Ventes en ligne détaillées (FactOnlineSales) -> Sales/ : un fichier par année
    # -----------------------------------------------------------------------
    titre("4. Ventes en ligne détaillées (FactOnlineSales)")
    for annee_contoso in ANNEES_CONTOSO:
        d, f = bornes(annee_contoso)
        en_ligne = pd.read_sql(f"""
            SELECT OnlineSalesKey AS IdVenteEnLigne, DateKey AS DateContoso, StoreKey AS IdBoutique,
                   ProductKey AS IdProduit, PromotionKey AS IdPromotion, CustomerKey AS IdClient,
                   SalesOrderNumber AS NumeroCommande, SalesOrderLineNumber AS LigneCommande,
                   SalesQuantity AS QuantiteVente, ReturnQuantity AS QuantiteRetour, DiscountQuantity AS QuantiteRemise,
                   CAST(SalesAmount AS float) AS MontantVentes, CAST(ReturnAmount AS float) AS MontantRetour,
                   CAST(DiscountAmount AS float) AS MontantRemise, CAST(TotalCost AS float) AS CoutTotal,
                   CAST(UnitCost AS float) AS CoutUnitaire, CAST(UnitPrice AS float) AS PrixUnitaire
            FROM FactOnlineSales
            WHERE StoreKey IN ({liste_boutiques}) AND DateKey >= {d} AND DateKey < {f}""", engine)
        annee = annee_contoso + config.DECALAGE_ANNEES
        if en_ligne.empty:
            print(f"  {annee} : aucune ligne pour nos boutiques")
            continue
        en_ligne["DateContoso"] = pd.to_datetime(en_ligne["DateContoso"])
        en_ligne.insert(1, "Date", en_ligne["DateContoso"] + DECALAGE)
        en_ligne = en_ligne.sort_values(["Date", "IdVenteEnLigne"])
        chemin = config.SALES_CONTOSO / f"FactOnlineSales {annee}.parquet"
        en_ligne.to_parquet(chemin, index=False)
        print(f"  OK      {chemin.name:28s} {nombre(len(en_ligne)):>10} lignes · boutiques {sorted(int(b) for b in en_ligne.IdBoutique.unique())} · "
              f"{nombre(en_ligne.IdClient.nunique())} clients · {nombre(en_ligne.NumeroCommande.nunique())} commandes · "
              f"{nombre(en_ligne.MontantVentes.sum())} $")
        del en_ligne

    # -----------------------------------------------------------------------
    # 6. Plan stratégique (FactStrategyPlan) -> Plan/FactStrategyPlan.csv
    # -----------------------------------------------------------------------
    # Le plan n'est pas rangé par boutique mais par ENTITÉ. Le lien se fait par DimStore.EntityKey :
    # chaque boutique a une entité, et c'est cette entité qui porte les montants du plan.
    titre("5. Plan stratégique (FactStrategyPlan)")
    vider(config.PLAN, [config.FICHIER_PLAN, config.FICHIER_OBJECTIFS])
    plan = pd.read_sql(f"""
        SELECT s.StoreKey AS [IdBoutique], p.EntityKey, p.Datekey AS [DateContoso], p.ScenarioKey, p.AccountKey,
               p.ProductCategoryKey, p.CurrencyKey, CAST(p.Amount AS float) AS [Montant]
        FROM FactStrategyPlan p
        JOIN DimStore s ON s.EntityKey = p.EntityKey
        WHERE s.StoreKey IN ({liste_boutiques}) AND p.Datekey >= {debut} AND p.Datekey < {fin}
        ORDER BY s.StoreKey, p.Datekey, p.ScenarioKey, p.AccountKey, p.ProductCategoryKey""", engine)
    plan["DateContoso"] = pd.to_datetime(plan["DateContoso"])
    plan.insert(2, "Date", plan["DateContoso"] + DECALAGE)          # le plan est mensuel : premier jour du mois
    comptes = pd.read_csv(config.DIM / "DimAccount.csv")[["AccountKey", "AccountName"]]
    scenarios = pd.read_csv(config.DIM / "DimScenario.csv")[["ScenarioKey", "ScenarioName"]]
    controle = plan.merge(comptes, on="AccountKey").merge(scenarios, on="ScenarioKey")
    controle = controle[(controle.ScenarioName == "Actual") & controle.AccountName.isin(["Sale Revenue", "Cost of Goods Sold"])]
    controle = controle.groupby([controle.Date.dt.year.rename("annee"), "AccountName"]).Montant.sum().unstack()
    for colonne in ("Date", "DateContoso"):
        plan[colonne] = plan[colonne].dt.strftime("%Y-%m-%d")
    plan.to_csv(config.PLAN / config.FICHIER_PLAN, index=False, encoding="utf-8-sig")
    print(f"  OK      {config.FICHIER_PLAN}  {nombre(len(plan))} lignes · {plan.IdBoutique.nunique()} boutiques · "
          f"{plan.Date.nunique()} mois · {plan.AccountKey.nunique()} comptes · {plan.ScenarioKey.nunique()} scénarios")
    # Contrôle : les ventes du plan (scénario réel) doivent être égales aux ventes de FactSales, au cent près
    controle["ventes de FactSales"] = total_ventes
    controle["écart sur les ventes"] = controle["Sale Revenue"] - controle["ventes de FactSales"]
    print("  Scénario réel, par année :")
    print(controle.to_string(float_format=lambda v: nombre(v, 2)))
    del plan

    # -----------------------------------------------------------------------
    # 7. Objectifs de vente (FactSalesQuota) -> Plan/FactSalesQuota.parquet
    # -----------------------------------------------------------------------
    titre("6. Objectifs de vente (FactSalesQuota)")
    morceaux = []
    for annee_contoso in ANNEES_CONTOSO:
        d, f = bornes(annee_contoso)
        morceaux.append(pd.read_sql(f"""
            SELECT DateKey AS DateContoso, StoreKey AS IdBoutique, ProductKey AS IdProduit, ChannelKey, ScenarioKey,
                   CAST(SalesQuantityQuota AS float) AS QuantiteObjectif,
                   CAST(SalesAmountQuota AS float) AS VentesObjectif,
                   CAST(GrossMarginQuota AS float) AS MargeObjectif
            FROM FactSalesQuota
            WHERE StoreKey IN ({liste_boutiques}) AND DateKey >= {d} AND DateKey < {f}""", engine))
    objectifs = pd.concat(morceaux, ignore_index=True)
    del morceaux
    objectifs["DateContoso"] = pd.to_datetime(objectifs["DateContoso"])
    objectifs.insert(0, "Date", objectifs["DateContoso"] + DECALAGE)        # mensuel : premier jour du mois
    objectifs = objectifs.sort_values(["Date", "IdBoutique", "IdProduit", "ScenarioKey"])
    objectifs.to_parquet(config.PLAN / config.FICHIER_OBJECTIFS, index=False)
    print(f"  OK      {config.FICHIER_OBJECTIFS}  {nombre(len(objectifs))} lignes · {objectifs.IdBoutique.nunique()} boutiques · "
          f"{objectifs.IdProduit.nunique()} produits · {objectifs.Date.nunique()} mois")
    print("  Ventes par scénario et par année (le scénario réel doit être égal aux ventes de FactSales) :")
    print(objectifs.pivot_table(index=objectifs.Date.dt.year.rename("annee"), columns="ScenarioKey", values="VentesObjectif", aggfunc="sum")
          .assign(**{"ventes de FactSales": total_ventes}).to_string(float_format=lambda v: nombre(v, 2)))
    del objectifs

    # -----------------------------------------------------------------------
    # 8. Stock hebdomadaire (FactInventory) -> Stock/FactInventory.parquet
    # -----------------------------------------------------------------------
    titre("7. Stock hebdomadaire (FactInventory)")
    vider(config.STOCK, [config.FICHIER_STOCK])
    morceaux = []
    for annee_contoso in ANNEES_CONTOSO:
        d, f = bornes(annee_contoso)
        morceaux.append(pd.read_sql(f"""
            SELECT DateKey AS DateContoso, StoreKey AS IdBoutique, ProductKey AS IdProduit,
                   OnHandQuantity AS QuantiteEnStock, OnOrderQuantity AS QuantiteEnCommande,
                   SafetyStockQuantity AS StockDeSecurite, CAST(UnitCost AS float) AS CoutUnitaire,
                   DaysInStock AS JoursEnStock, MinDayInStock AS JoursEnStockMin, MaxDayInStock AS JoursEnStockMax,
                   Aging AS Anciennete
            FROM FactInventory
            WHERE StoreKey IN ({liste_boutiques}) AND DateKey >= {d} AND DateKey < {f}""", engine))
    stock = pd.concat(morceaux, ignore_index=True)
    del morceaux
    stock["DateContoso"] = pd.to_datetime(stock["DateContoso"])
    stock.insert(0, "Date", stock["DateContoso"] + DECALAGE)                # un relevé par semaine
    stock = stock.sort_values(["Date", "IdBoutique", "IdProduit"])
    stock.to_parquet(config.STOCK / config.FICHIER_STOCK, index=False)
    print(f"  OK      {config.FICHIER_STOCK}  {nombre(len(stock))} lignes · {stock.IdBoutique.nunique()} boutiques · "
          f"{stock.IdProduit.nunique()} produits · {stock.Date.nunique()} relevés")
    print(stock.groupby(stock.Date.dt.year.rename("annee")).agg(
        lignes=("IdProduit", "size"), releves=("Date", "nunique"), boutiques=("IdBoutique", "nunique"),
        produits=("IdProduit", "nunique")).to_string())
    print(f"  Doublons sur la clé (date, boutique, produit) : {int(stock.duplicated(['Date', 'IdBoutique', 'IdProduit']).sum())}")
    del stock

    # -----------------------------------------------------------------------
    # 9. Récapitulatif des fichiers écrits
    # -----------------------------------------------------------------------
    titre("8. Fichiers de data/raw/contoso")
    for dossier in (config.DIM, config.SALES_CONTOSO, config.PLAN, config.STOCK):
        fichiers = sorted(f for f in dossier.iterdir() if f.is_file())
        print(f"  {dossier.name}/  {len(fichiers)} fichiers, {sum(f.stat().st_size for f in fichiers) / 1e6:.1f} Mo")
        for fichier in fichiers:
            print(f"      {fichier.name:38s} {fichier.stat().st_size / 1e6:>7.1f} Mo")
    if config.ANCIEN.exists():
        print(f"\n  Anciens dossiers conservés dans {config.ANCIEN} : à supprimer à la main une fois les notebooks relancés.")
    print("\nExtraction terminée.")


if __name__ == "__main__":
    main()
