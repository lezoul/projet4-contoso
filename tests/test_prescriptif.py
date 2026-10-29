"""
Tests du simulateur de scénarios (src/simulateur.py).

Ils vérifient que le moteur retrouve les chiffres publiés dans les notebooks 06, 09 et 14.
Une modification malheureuse du moteur les fait échouer.

Les tests qui ont besoin des données sont ignorés tant que les notebooks 00 à 05c n'ont pas
été exécutés (le dossier data/ n'est pas versionné).

    python -m pytest            # depuis la racine du projet
"""
import pandas as pd
import pytest

from src import config, simulateur
from src.simulateur import reglages

CHEMINS = {
    "commun": config.AGREGATS / "ventes_charges_boutique_mois.parquet",
    "charges": config.CLEAN / "fait_charges.parquet",
    "ventes": config.CLEAN / "fait_ventes_variables.parquet",
    "dim_produit": config.CLEAN_DIMENSIONS / "dim_produit.parquet",
    "dim_boutique": config.CLEAN_DIMENSIONS / "dim_boutique.parquet",
}
DONNEES_ABSENTES = not all(c.exists() for c in CHEMINS.values())
besoin_donnees = pytest.mark.skipif(DONNEES_ABSENTES, reason="données absentes : exécuter les notebooks 00 à 05c")
M = 1e6


# ---------------------------------------------------------------------------
# Tests sans données
# ---------------------------------------------------------------------------
def test_reglages_partent_du_fil_de_l_eau():
    r = reglages(lancements=552)
    assert r["lancements"] == 552
    assert r["frais_maitrisables"] == "fil de l'eau"
    assert simulateur.REGLAGES_FIL_DE_L_EAU["lancements"] is None      # l'original n'est pas modifié


def test_reglage_inconnu_refuse():
    with pytest.raises(KeyError):
        reglages(lancement=552)                                          # faute de frappe : doit échouer


# ---------------------------------------------------------------------------
# Tests sur les données de l'exercice 2021
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def donnees():
    ventes = pd.read_parquet(CHEMINS["ventes"], columns=["annee", "id_boutique", "id_produit", "type_boutique", "ca_net",
                                                         "taux_remise_annonce", "montant_remise", "marge_perdue_retours"])
    return simulateur.preparer(pd.read_parquet(CHEMINS["commun"]), pd.read_parquet(CHEMINS["charges"]), ventes,
                               pd.read_parquet(CHEMINS["dim_produit"]), pd.read_parquet(CHEMINS["dim_boutique"]),
                               config.EXERCICE)


@pytest.fixture(scope="module")
def depart(donnees):
    """2021 reconduit, charges gelées : le moteur doit redonner le résultat réel de 2021."""
    base = simulateur.base_reconduite(donnees)
    return base, simulateur.resultat_entreprise(simulateur.simuler(donnees, base, reglages(hausse_charges="gelée")))


@besoin_donnees
def test_mesures_de_l_exercice(donnees):
    assert donnees["lances"] == 272
    assert donnees["ca_par_nouveaute"] == pytest.approx(298_114, rel=1e-3)


@besoin_donnees
def test_moteur_reproduit_2021(donnees, depart):
    _, resultat = depart
    reel = donnees["boutiques"].resultat_exploitation.sum()
    assert resultat == pytest.approx(reel, rel=1e-3)


@besoin_donnees
@pytest.mark.parametrize("kw, publie", [
    (dict(lancements=552), 46.1),
    (dict(frais_maitrisables="niveau 2019"), 9.2),
    (dict(regroupement_pays=0.30), 6.6),
    (dict(baisse_publicite_magasins=0.10), 6.2),
    (dict(remises_magasin="supprimées"), 5.4),
    (dict(plafond_remise_10_hors_magasin=True), 2.9),
    (dict(baisse_retours=0.5), 2.6),
])
def test_leviers_retrouvent_les_notebooks_06_et_09(donnees, depart, kw, publie):
    base, resultat_depart = depart
    r = simulateur.simuler(donnees, base, reglages(hausse_charges="gelée", **kw))
    gain = (simulateur.resultat_entreprise(r) - resultat_depart) / M
    assert gain == pytest.approx(publie, abs=0.06)


@besoin_donnees
def test_base_par_canal_respecte_les_totaux(donnees):
    ca_canal = {"En ligne": 300 * M, "Revendeur": 150 * M, "Magasins": 200 * M}
    base = simulateur.base_par_canal(donnees, ca_canal)
    types = donnees["boutiques"].set_index("id_boutique").type
    totaux = base.groupby(types.reindex(base.index).values).sum()
    for canal, montant in ca_canal.items():
        assert totaux[canal] == pytest.approx(montant)


@besoin_donnees
def test_decalage_de_base(donnees):
    base = simulateur.base_reconduite(donnees)
    plus_10 = simulateur.simuler(donnees, base, reglages(erreur_base=0.10))
    assert plus_10.ca_net_simule.sum() == pytest.approx(base.sum() * 1.10)


@besoin_donnees
def test_cout_de_lancement_deduit(donnees, depart):
    base, _ = depart
    sans = simulateur.resultat_entreprise(simulateur.simuler(donnees, base, reglages(lancements=552)))
    avec = simulateur.resultat_entreprise(simulateur.simuler(donnees, base, reglages(lancements=552, cout_par_lancement=100_000)))
    assert sans - avec == pytest.approx((552 - 272) * 100_000)
