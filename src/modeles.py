"""
Fonctions communes aux notebooks prédictifs et prescriptifs (dossiers notebooks/3_modeles et 4_prescriptif).

Le notebook 10 (prévision des ventes) construit sa table de modélisation et ses prévisions avec ces
fonctions. Le simulateur du notebook 14 les réutilise : il doit calculer les variables exactement de
la même façon, sinon le modèle enregistré recevrait des données qu'il ne connaît pas.

    from src import modeles
    table = modeles.construire_table(commun, dim_boutique, dim_produit, contexte, ventes)

Contenu
    FAMILLES                                   variables candidates, rangées par famille
    variables_catalogue(dates_lancement, mois) lancements récents et âge moyen du catalogue, mois par mois
    construire_table(...)                      une ligne par boutique et par mois, variables et cible
    ajouter_historique(table)                  ventes des mois précédents (décalées, donc connues à l'avance)
    wape(reel, prevision)                      erreur totale rapportée au chiffre d'affaires total
    mesurer(reel, prevision)                   MAE, WAPE, R² et biais
    predire_recursif(modele, ...)              prévision mois après mois sur un horizon de plusieurs mois

Règle commune : chaque variable d'un mois doit être connue au début de ce mois. Les ventes du mois
lui-même ne servent jamais de variable : seulement celles des mois précédents.
"""
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Variables candidates, par famille
# ---------------------------------------------------------------------------
FAMILLES = {
    "Calendrier": ["mois_sin", "mois_cos", "jours", "jours_week_end", "jours_feries"],
    "Contexte COVID": ["severite_covid"],
    "Boutique": ["type_boutique", "surface", "effectif"],
    "Historique": ["log_ca_m1", "log_ca_moy3"],
    "Assortiment": ["lancements_3m", "lancements_12m", "age_catalogue"],
    "Commercial": ["taux_promotion", "publicite"],
}
VARIABLES_CATEGORIELLES = ["type_boutique"]


# ---------------------------------------------------------------------------
# Variables du catalogue (communes à toutes les boutiques)
# ---------------------------------------------------------------------------
def variables_catalogue(dates_lancement, mois):
    """Lancements récents et âge moyen du catalogue, pour chaque mois de `mois`.

    dates_lancement : dates de mise en vente des produits (une par produit)
    mois            : premiers jours des mois à décrire

    Le mois m compte les produits mis en vente pendant le mois m et les mois précédents : la date de
    mise en vente fait partie du plan de lancement, elle est donc connue au début du mois.
    age_catalogue est l'âge moyen, en mois, des produits mis en vente depuis moins de 36 mois.
    """
    lancements = pd.Series(pd.to_datetime(dates_lancement)).dropna()
    debut = min(lancements.min(), pd.Timestamp(min(mois))).to_period("M").to_timestamp()
    tous = pd.date_range(debut, pd.Timestamp(max(mois)), freq="MS")
    par_mois = lancements.dt.to_period("M").dt.to_timestamp().value_counts().reindex(tous, fill_value=0)
    cat = pd.DataFrame({"lancements_mois": par_mois})
    cat["lancements_3m"] = cat.lancements_mois.rolling(3, min_periods=1).sum()
    cat["lancements_12m"] = cat.lancements_mois.rolling(12, min_periods=1).sum()
    valeurs = lancements.values

    def age_moyen(m):
        age = (np.datetime64(m) - valeurs).astype("timedelta64[D]").astype(float) / 30.44
        age = age[(age >= 0) & (age < 36)]
        return age.mean() if len(age) else np.nan

    cat["age_catalogue"] = [age_moyen(m) for m in cat.index]
    return cat.loc[pd.DatetimeIndex(mois), ["lancements_3m", "lancements_12m", "age_catalogue"]]


# ---------------------------------------------------------------------------
# Table de modélisation : une ligne par boutique et par mois
# ---------------------------------------------------------------------------
def construire_table(commun, dim_boutique, dim_produit, contexte, ventes):
    """Assemble les variables candidates et la cible, une ligne par boutique et par mois.

    commun       : table ventes et charges par boutique et par mois (05b)
    dim_boutique : surface et effectif
    dim_produit  : dates de mise en vente
    contexte     : jours fériés et sévérité COVID par pays et par jour (02)
    ventes       : lignes de vente, pour le taux de promotion annoncé du mois
    """
    table = commun[["date", "annee", "mois", "id_boutique", "nom_boutique", "type_boutique", "pays",
                    "ca_net", "publicite"]].copy()
    table = table.merge(dim_boutique[["id_boutique", "surface", "effectif"]], on="id_boutique", how="left")

    # Calendrier : saison (mois sur un cercle, pour que décembre soit voisin de janvier), jours, fins de semaine
    table["mois_sin"] = np.sin(2 * np.pi * table.mois / 12)
    table["mois_cos"] = np.cos(2 * np.pi * table.mois / 12)
    table["jours"] = table.date.dt.days_in_month
    table["jours_week_end"] = table.date.map(_jours_week_end)

    # Contexte : jours fériés du pays et sévérité moyenne des mesures COVID du mois
    ctx = contexte.assign(mois_debut=contexte.date.dt.to_period("M").dt.to_timestamp())
    ctx = ctx.groupby(["pays", "mois_debut"]).agg(jours_feries=("est_ferie", "sum"),
                                                  severite_covid=("severite_covid", "mean")).reset_index()
    table = table.merge(ctx, left_on=["pays", "date"], right_on=["pays", "mois_debut"], how="left").drop(columns="mois_debut")

    # Commercial : taux annoncé de la promotion du mois dans la boutique (calendrier fixé à l'avance)
    v = ventes.assign(mois_debut=ventes.date.dt.to_period("M").dt.to_timestamp())
    promo = v.groupby(["id_boutique", "mois_debut"]).taux_remise_annonce.max().rename("taux_promotion")
    table = table.merge(promo, left_on=["id_boutique", "date"], right_index=True, how="left")
    table["taux_promotion"] = table.taux_promotion.fillna(0)

    # Assortiment : lancements récents et âge du catalogue, identiques pour toutes les boutiques un mois donné
    cat = variables_catalogue(dim_produit.date_mise_en_vente, sorted(table.date.unique()))
    table = table.merge(cat, left_on="date", right_index=True, how="left")

    table["log_ca"] = np.log(table.ca_net)
    return ajouter_historique(table)


def ajouter_historique(table):
    """Ventes des mois précédents, en logarithme : mois précédent, moyenne des 3 mois précédents, même mois N-1.

    log_ca_m12 ne sert qu'à la référence naïve « même mois l'an dernier » : il n'existe pas pour 2019.
    """
    table = table.sort_values(["id_boutique", "date"]).reset_index(drop=True)
    groupe = table.groupby("id_boutique").log_ca
    table["log_ca_m1"] = groupe.shift(1)
    table["log_ca_moy3"] = groupe.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    table["log_ca_m12"] = groupe.shift(12)
    # Un mois manquant (boutique pas encore ouverte) casse la suite : on ne décale que des mois consécutifs
    ecart = table.groupby("id_boutique").date.diff().dt.days
    table.loc[ecart.isna() | (ecart > 31), ["log_ca_m1", "log_ca_moy3"]] = np.nan
    table["variation"] = table.log_ca - table.log_ca_m1          # cible : variation par rapport au mois précédent
    return table


def _jours_week_end(mois):
    jours = pd.date_range(mois, mois + pd.offsets.MonthEnd(0))
    return int((jours.dayofweek >= 5).sum())


# ---------------------------------------------------------------------------
# Mesures d'erreur
# ---------------------------------------------------------------------------
def wape(reel, prevision):
    """Erreur absolue totale rapportée aux ventes totales : 0,10 = on se trompe de 10 % des ventes."""
    reel, prevision = np.asarray(reel, float), np.asarray(prevision, float)
    return np.abs(reel - prevision).sum() / np.abs(reel).sum()


def mesurer(reel, prevision):
    """MAE en dollars, WAPE, R² et biais (écart du total prévu au total réel)."""
    reel, prevision = np.asarray(reel, float), np.asarray(prevision, float)
    residus = reel - prevision
    return {
        "MAE": np.abs(residus).mean(),
        "WAPE": wape(reel, prevision),
        "R²": 1 - (residus ** 2).sum() / ((reel - reel.mean()) ** 2).sum(),
        "Biais": prevision.sum() / reel.sum() - 1,
    }


# ---------------------------------------------------------------------------
# Prévision sur plusieurs mois
# ---------------------------------------------------------------------------
def predire_recursif(modele, variables, depart, futur, cible="variation"):
    """Prévoit mois après mois, en réutilisant chaque prévision comme historique du mois suivant.

    modele    : modèle entraîné (pipeline scikit-learn)
    variables : colonnes attendues par le modèle
    depart    : historique réel (colonnes id_boutique, date, log_ca) jusqu'au dernier mois connu
    futur     : une ligne par boutique et par mois à prévoir, avec toutes les variables sauf l'historique
    cible     : "variation" (variation du log par rapport au mois précédent) ou "niveau" (log du chiffre d'affaires)

    Renvoie `futur` complété de log_ca_prevu et ca_prevu.
    """
    historique = {b: list(g.sort_values("date").log_ca.values[-3:]) for b, g in depart.groupby("id_boutique")}
    resultats = []
    for mois, lignes in futur.sort_values("date").groupby("date", sort=True):
        lignes = lignes[lignes.id_boutique.isin(historique)].copy()
        lignes["log_ca_m1"] = [historique[b][-1] for b in lignes.id_boutique]
        lignes["log_ca_moy3"] = [np.mean(historique[b][-3:]) for b in lignes.id_boutique]
        sortie = modele.predict(lignes[variables])
        lignes["log_ca_prevu"] = lignes.log_ca_m1 + sortie if cible == "variation" else sortie
        for b, valeur in zip(lignes.id_boutique, lignes.log_ca_prevu):
            historique[b].append(valeur)
        resultats.append(lignes)
    futur = pd.concat(resultats, ignore_index=True)
    futur["ca_prevu"] = np.exp(futur.log_ca_prevu)
    return futur
