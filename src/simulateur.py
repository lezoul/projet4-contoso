"""
Moteur du simulateur de scénarios (notebook 14 et application Streamlit).

Le simulateur calcule le compte de résultat d'une année, boutique par boutique, à partir de :
  - une **base** : le chiffre d'affaires net prévu de chaque boutique si rien ne change ;
  - des **réglages** : les décisions de gestion (leviers) et les hypothèses incertaines.

Chaque levier reprend le mécanisme chiffré dans les notebooks d'analyse, sans en inventer de nouveau :

    Levier                                   Mécanisme                                              Source
    Rythme de lancement                      nouveautés × CA d'une nouveauté de l'exercice          06, 06b
    Nouveautés en magasin                    magasins ÷ en ligne ramené à celui des produits anciens 06
    Frais généraux maîtrisables              personnel, administration, informatique               06
    Regroupement par pays                    part de l'administration et de l'informatique          06
    Publicité des magasins                   baisse en %, réaction supposée des ventes             06
    Remises en magasin                       la remise supprimée reste dans le chiffre d'affaires   07, 09
    Plafond de remise en ligne et revendeur  les lignes à 20 % ramenées à 10 %                      09
    Retours                                  marge perdue évitée                                    08

Règle de calcul commune : un dollar de chiffre d'affaires en plus apporte sa marge (au taux de la boutique)
et déclenche les « autres charges » (seule charge qui suit les ventes). Une remise supprimée ou un retour
évité ajoute du chiffre d'affaires sans coût des ventes : il apporte donc toute sa valeur moins les autres charges.

    from src import simulateur
    donnees = simulateur.preparer(commun, charges, ventes, dim_produit, dim_boutique, exercice=2021)
    base = simulateur.base_reconduite(donnees)
    resultat = simulateur.simuler(donnees, base, simulateur.REGLAGES_FIL_DE_L_EAU)
"""
from copy import deepcopy

import numpy as np
import pandas as pd

COMPTES_MAITRISABLES = ["Personnel", "Administration", "Informatique"]      # décidés chaque exercice
COMPTES_SUBIS = ["Loyers et immobilier", "Énergie et communication"]        # baux et prix de l'énergie
COMPTE_VARIABLE = "Autres charges"                                           # seule charge qui suit les ventes
LIBELLES_TYPES = {"Online": "En ligne", "Reseller": "Revendeur", "Store": "Magasins"}

# ---------------------------------------------------------------------------
# Réglages
# ---------------------------------------------------------------------------
REGLAGES_FIL_DE_L_EAU = {
    # Hypothèses de base
    "erreur_base": 0.0,                   # la base est décalée de ce pourcentage (test de robustesse)
    "hausse_charges": "prolongée",        # "prolongée" (hausses du dernier exercice reconduites) ou "gelée"
    # Leviers
    "lancements": None,                   # nombre de nouveautés de l'année ; None = rythme du dernier exercice
    "nouveautes_en_magasin": 0.0,         # part de l'écart comblé (0 à 1)
    "frais_maitrisables": "fil de l'eau", # "fil de l'eau", "gel", "niveau 2020", "niveau 2019" ou une baisse en % (ex. 0.10)
    "regroupement_pays": 0.0,             # part de l'administration et de l'informatique économisée (0 à 0.4)
    "baisse_publicite_magasins": 0.0,     # baisse du budget publicitaire des magasins (0 à 1)
    "reaction_ventes_publicite": 0.0,     # variation des ventes des magasins qui en résulte (ex. -0.02)
    "remises_magasin": "maintenues",      # "maintenues", "sans le 20 %" ou "supprimées"
    "plafond_remise_10_hors_magasin": False,
    "baisse_retours": 0.0,                # part des retours évitée (0 à 1)
    # Hypothèses incertaines des leviers
    "efficacite_nouveaute": 1.0,          # CA d'une nouveauté supplémentaire, rapporté à celui du dernier exercice
    "cout_par_lancement": 0.0,            # coût de conception et de lancement d'une nouveauté (absent des données)
}


def reglages(**modifs):
    """Réglages au fil de l'eau, modifiés par les arguments donnés."""
    r = deepcopy(REGLAGES_FIL_DE_L_EAU)
    inconnus = set(modifs) - set(r)
    if inconnus:
        raise KeyError(f"Réglages inconnus : {sorted(inconnus)}")
    r.update(modifs)
    return r


# ---------------------------------------------------------------------------
# Données du dernier exercice, boutique par boutique
# ---------------------------------------------------------------------------
def preparer(commun, charges, ventes, dim_produit, dim_boutique, exercice):
    """Tout ce dont le simulateur a besoin, mesuré sur l'exercice de référence (le dernier).

    commun      : table ventes et charges par boutique et par mois (05b)
    charges     : table de faits des charges (05b), scénario « Réel »
    ventes      : lignes de vente avec variables (05)
    dim_produit : dates de mise en vente
    dim_boutique: dates d'ouverture (le retour des charges à un niveau passé ne vise que les magasins ouverts à cette date, comme au 06)
    """
    reel = charges[charges.scenario == "Réel"]
    c = commun[commun.annee == exercice]
    b = c.groupby(["id_boutique", "nom_boutique", "type_boutique", "pays"], as_index=False)[
        ["ca_net", "marge_nette", "frais_generaux", "publicite", "resultat_exploitation", "montant_remise", "montant_retour"]].sum()
    b["type"] = b.type_boutique.map(LIBELLES_TYPES)

    # Charges compte par compte, sur l'exercice et le précédent (pour prolonger les hausses)
    comptes = COMPTES_MAITRISABLES + COMPTES_SUBIS + [COMPTE_VARIABLE]
    par_compte = reel[reel.nom_compte.isin(comptes)].pivot_table(index=["id_boutique", "annee"], columns="nom_compte",
                                                                  values="montant", aggfunc="sum").fillna(0)
    for compte in comptes:
        for annee in [exercice - 2, exercice - 1, exercice]:
            serie = par_compte[compte].xs(annee, level="annee") if annee in par_compte.index.get_level_values("annee") else pd.Series(dtype=float)
            b[f"{compte} {annee}"] = b.id_boutique.map(serie).fillna(0)
    # Hausse de chaque compte entre les deux derniers exercices, par type de boutique
    hausses = {}
    for compte in COMPTES_MAITRISABLES + COMPTES_SUBIS:
        avant = b.groupby("type")[f"{compte} {exercice - 1}"].sum()
        apres = b.groupby("type")[f"{compte} {exercice}"].sum()
        hausses[compte] = (apres / avant - 1).fillna(0)

    ouverture = b.id_boutique.map(dim_boutique.set_index("id_boutique").date_ouverture)
    for annee in [exercice - 2, exercice - 1]:
        b[f"ouverte_en_{annee}"] = ouverture < pd.Timestamp(annee, 1, 2)
    b["taux_marge"] = b.marge_nette / b.ca_net
    b["taux_autres_charges"] = b[f"{COMPTE_VARIABLE} {exercice}"] / b.ca_net

    # Remises et retours de l'exercice, ligne par ligne
    v = ventes[ventes.annee == exercice]
    b["remise_20"] = b.id_boutique.map(v[v.taux_remise_annonce == 0.20].groupby("id_boutique").montant_remise.sum()).fillna(0)
    b["marge_perdue_retours"] = b.id_boutique.map(v.groupby("id_boutique").marge_perdue_retours.sum()).fillna(0)

    # Nouveautés de l'exercice : produits mis en vente pendant l'année, et ce qu'ils vendent
    annee_lancement = dim_produit.set_index("id_produit").date_mise_en_vente.dt.year
    nouveaute = v.id_produit.map(annee_lancement) >= exercice
    lances = int(dim_produit[dim_produit.id_produit.isin(ventes.id_produit.unique())].date_mise_en_vente.dt.year.eq(exercice).sum())
    b["ca_nouveautes"] = b.id_boutique.map(v[nouveaute].groupby("id_boutique").ca_net.sum()).fillna(0)
    ca_age = v.assign(nouveaute=nouveaute).pivot_table(index="nouveaute", columns="type_boutique", values="ca_net", aggfunc="sum")
    rapport_nouveautes = ca_age.loc[True, "Store"] / ca_age.loc[True, "Online"]
    rapport_anciens = ca_age.loc[False, "Store"] / ca_age.loc[False, "Online"]

    # Pays qui comptent plusieurs magasins : candidats au regroupement des bureaux
    magasins = b[b.type == "Magasins"]
    pays_multi = magasins.pays.value_counts()
    b["pays_plusieurs_magasins"] = (b.type == "Magasins") & b.pays.map(pays_multi).gt(1)

    return {"exercice": exercice, "boutiques": b, "hausses": hausses, "lances": lances,
            "ca_par_nouveaute": v[nouveaute].ca_net.sum() / lances,
            "uplift_nouveautes_magasin": rapport_anciens / rapport_nouveautes - 1,
            "rapports": {"nouveautés": rapport_nouveautes, "anciens": rapport_anciens}}


# ---------------------------------------------------------------------------
# Bases : chiffre d'affaires de l'année simulée, boutique par boutique
# ---------------------------------------------------------------------------
def base_reconduite(donnees):
    """Le chiffre d'affaires du dernier exercice, reconduit à l'identique."""
    b = donnees["boutiques"]
    return pd.Series(b.ca_net.values, index=b.id_boutique, name="ca_base")


def base_par_canal(donnees, ca_canal):
    """Répartit un chiffre d'affaires annuel par canal (dict ou Series : libellé du canal -> montant)
    entre les boutiques, selon leur part du canal sur le dernier exercice."""
    b = donnees["boutiques"]
    part = b.ca_net / b.groupby("type").ca_net.transform("sum")
    return pd.Series((b.type.map(pd.Series(ca_canal)) * part).values, index=b.id_boutique, name="ca_base")


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def simuler(donnees, base, reglages_):
    """Compte de résultat de l'année simulée, une ligne par boutique.

    Renvoie un DataFrame avec le chiffre d'affaires, la marge, les charges, le résultat d'exploitation
    et l'apport de chaque levier au résultat (colonnes « apport : … »).
    """
    r = reglages_
    ex = donnees["exercice"]
    b = donnees["boutiques"].copy()
    b["ca_base"] = base.reindex(b.id_boutique).values * (1 + r["erreur_base"])
    echelle = b.ca_base / b.ca_net                       # remises, retours et nouveautés suivent le volume de la base
    mag = (b.type == "Magasins").values

    # --- 1. Chiffre d'affaires et marge de la base
    ca = b.ca_base.copy()
    marge = ca * b.taux_marge
    apports = {}

    # --- 2. Assortiment : rythme de lancement et nouveautés en magasin
    n = donnees["lances"] if r["lancements"] is None else r["lancements"]
    supplement = (n - donnees["lances"]) * donnees["ca_par_nouveaute"] * r["efficacite_nouveaute"]
    part_nouveautes = b.ca_nouveautes / b.ca_nouveautes.sum()
    ca_lancements = supplement * part_nouveautes
    ca_nouveautes_total = b.ca_nouveautes * echelle + ca_lancements
    ca_rayon = np.where(mag, ca_nouveautes_total * r["nouveautes_en_magasin"] * donnees["uplift_nouveautes_magasin"], 0)
    for nom, delta in [("lancements", ca_lancements), ("nouveautés en magasin", ca_rayon)]:
        ca += delta
        marge += delta * b.taux_marge
        apports[nom] = delta * (b.taux_marge - b.taux_autres_charges)
    cout_lancements = max(n - donnees["lances"], 0) * r["cout_par_lancement"]

    # --- 3. Publicité des magasins et réaction des ventes
    reaction = np.where(mag, ca * r["reaction_ventes_publicite"], 0)
    ca += reaction
    marge += reaction * b.taux_marge
    publicite = b.publicite * np.where(mag, 1 - r["baisse_publicite_magasins"], 1)
    apports["publicité"] = (b.publicite - publicite) + reaction * (b.taux_marge - b.taux_autres_charges)

    # --- 4. Remises et retours : de la valeur rendue au chiffre d'affaires, sans coût des ventes
    remise = b.montant_remise * echelle
    remise_20 = b.remise_20 * echelle
    recupere = np.where(mag, {"maintenues": 0, "sans le 20 %": 1, "supprimées": 0}[r["remises_magasin"]] * remise_20
                        + {"maintenues": 0, "sans le 20 %": 0, "supprimées": 1}[r["remises_magasin"]] * remise, 0)
    plafond = np.where(~mag & r["plafond_remise_10_hors_magasin"], 0.5 * remise_20, 0)
    retours = r["baisse_retours"] * b.marge_perdue_retours * echelle
    ca_retours = r["baisse_retours"] * b.montant_retour * echelle
    for nom, delta_ca, delta_marge in [("remises en magasin", recupere, recupere), ("plafond de remise hors magasin", plafond, plafond),
                                       ("retours", ca_retours, retours)]:
        ca += delta_ca
        marge += delta_marge
        apports[nom] = delta_marge - delta_ca * b.taux_autres_charges

    # --- 5. Charges : comptes maîtrisables, comptes subis, autres charges
    croissance = {c: (1 + donnees["hausses"][c]) if r["hausse_charges"] == "prolongée" else pd.Series(1.0, index=donnees["hausses"][c].index)
                  for c in COMPTES_MAITRISABLES + COMPTES_SUBIS}
    fil = {c: b[f"{c} {ex}"] * b.type.map(croissance[c]) for c in COMPTES_MAITRISABLES + COMPTES_SUBIS}
    # Le levier porte sur les magasins, comme au notebook 06 ; un magasin sans charges l'année visée garde son niveau actuel
    choix = r["frais_maitrisables"]
    maitrisables = {}
    for c in COMPTES_MAITRISABLES:
        if choix == "fil de l'eau":
            cible = fil[c]
        elif choix == "gel":
            cible = b[f"{c} {ex}"]
        elif choix in ("niveau 2020", "niveau 2019"):
            annee = int(choix[-4:])
            # Magasins déjà ouverts au début de la période de référence (ex - 2), comme au notebook 06
            cible = b[f"{c} {annee}"].where(b[f"ouverte_en_{ex - 2}"] & (b[f"{c} {annee}"] > 0), fil[c])
        else:
            cible = fil[c] * (1 - float(choix))
        maitrisables[c] = pd.Series(np.where(mag, np.minimum(cible, fil[c]), fil[c]), index=b.index)
    apports["frais généraux maîtrisables"] = sum(fil[c] - maitrisables[c] for c in COMPTES_MAITRISABLES)
    bureau = maitrisables["Administration"] + maitrisables["Informatique"]
    economie_pays = np.where(b.pays_plusieurs_magasins, r["regroupement_pays"] * bureau, 0)
    apports["regroupement par pays"] = pd.Series(economie_pays, index=b.index)
    frais = sum(maitrisables.values()) - economie_pays + sum(fil[c] for c in COMPTES_SUBIS) + ca * b.taux_autres_charges

    # --- 6. Résultat
    b["ca_net_simule"] = ca
    b["marge_nette_simulee"] = marge
    b["frais_generaux_simules"] = frais
    b["publicite_simulee"] = publicite
    b["resultat_exploitation_simule"] = marge - frais - publicite
    for nom, valeur in apports.items():
        b[f"apport : {nom}"] = np.asarray(valeur, dtype=float)
    b.attrs["cout_lancements"] = cout_lancements
    return b


def resumer(resultat):
    """Totaux par canal et pour l'entreprise : CA, résultat d'exploitation, magasins déficitaires."""
    t = resultat.groupby("type").agg(ca_net=("ca_net_simule", "sum"), resultat=("resultat_exploitation_simule", "sum"),
                                      boutiques=("id_boutique", "size"),
                                      deficitaires=("resultat_exploitation_simule", lambda s: int((s < 0).sum())))
    t.loc["Entreprise"] = t.sum()
    t.loc["Entreprise", "resultat"] -= resultat.attrs.get("cout_lancements", 0.0)
    return t


def resultat_entreprise(resultat):
    """Résultat d'exploitation de l'entreprise, coût des lancements supplémentaires déduit."""
    return float(resultat.resultat_exploitation_simule.sum() - resultat.attrs.get("cout_lancements", 0.0))
