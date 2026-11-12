"""
Paquet de données de l'application Streamlit, pour la déployer en ligne.

En ligne, l'application n'a pas accès au dossier data/ (non versionné, plusieurs centaines de Mo).
Ce module enregistre dans dashboards/donnees/ le strict nécessaire, déjà calculé :
  - boutiques.parquet   : une ligne par boutique (sortie de simulateur.preparer, exercice 2021)
  - hausses.parquet     : hausses de charges 2020 → 2021, par compte et par canal
  - parametres.json     : les mesures de l'exercice (lancements, CA d'une nouveauté…)
  - bases.parquet       : les bases de CA 2022 par boutique (lissage saisonnier, Random Forest si disponible)
Ce sont des agrégats par boutique : aucune ligne de vente ni aucun client.

À relancer après le notebook 14, depuis la racine du projet :
    python -m src.paquet_app
"""
import json
from pathlib import Path

import pandas as pd

from src import config, simulateur

DOSSIER = config.ROOT / "dashboards" / "donnees"


def preparer_complet():
    """Prépare les données de l'exercice à partir des tables complètes de data/clean."""
    ventes = pd.read_parquet(config.CLEAN / "fait_ventes_variables.parquet",
                             columns=["annee", "id_boutique", "id_produit", "type_boutique", "ca_net",
                                      "taux_remise_annonce", "montant_remise", "marge_perdue_retours"])
    return simulateur.preparer(pd.read_parquet(config.AGREGATS / "ventes_charges_boutique_mois.parquet"),
                               pd.read_parquet(config.CLEAN / "fait_charges.parquet"), ventes,
                               pd.read_parquet(config.CLEAN_DIMENSIONS / "dim_produit.parquet"),
                               pd.read_parquet(config.CLEAN_DIMENSIONS / "dim_boutique.parquet"),
                               config.EXERCICE)


def bases_completes(donnees):
    """Bases de CA de l'année simulée, une colonne par base, une ligne par boutique."""
    annee = donnees["exercice"] + 1
    bases = {"Lissage saisonnier (notebook 14)": simulateur.base_par_canal(
        donnees, pd.read_parquet(config.SCENARIOS / f"base_canal_{annee}.parquet").sum())}
    chemin_rf = config.PREDICTIONS / "previsions_ventes.parquet"
    if chemin_rf.exists():
        rf = pd.read_parquet(chemin_rf)
        rf = rf[rf.jeu.str.startswith("Prévision")]
        bases["Random Forest (notebook 10)"] = (rf.groupby("id_boutique").prevision.sum()
                                                .reindex(donnees["boutiques"].id_boutique)
                                                .fillna(simulateur.base_reconduite(donnees)))
    return pd.DataFrame({nom: b.values for nom, b in bases.items()}, index=donnees["boutiques"].id_boutique.values)


def exporter(dossier=DOSSIER):
    donnees = preparer_complet()
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    donnees["boutiques"].to_parquet(dossier / "boutiques.parquet", index=False)
    pd.DataFrame(donnees["hausses"]).to_parquet(dossier / "hausses.parquet")
    bases_completes(donnees).rename_axis("id_boutique").to_parquet(dossier / "bases.parquet")
    parametres = {"exercice": int(donnees["exercice"]), "lances": int(donnees["lances"]),
                  "ca_par_nouveaute": float(donnees["ca_par_nouveaute"]),
                  "uplift_nouveautes_magasin": float(donnees["uplift_nouveautes_magasin"]),
                  "rapports": {k: float(v) for k, v in donnees["rapports"].items()}}
    (dossier / "parametres.json").write_text(json.dumps(parametres, ensure_ascii=False, indent=2), encoding="utf-8")
    taille = sum(f.stat().st_size for f in dossier.iterdir()) / 1024
    print(f"Paquet écrit dans {dossier.relative_to(config.ROOT)} ({taille:.0f} Ko)")


def charger(dossier=DOSSIER):
    """Relit le paquet : renvoie les données au format de simulateur.preparer, et les bases."""
    dossier = Path(dossier)
    p = json.loads((dossier / "parametres.json").read_text(encoding="utf-8"))
    hausses = pd.read_parquet(dossier / "hausses.parquet")
    donnees = {"exercice": p["exercice"], "boutiques": pd.read_parquet(dossier / "boutiques.parquet"),
               "hausses": {compte: hausses[compte] for compte in hausses.columns}, "lances": p["lances"],
               "ca_par_nouveaute": p["ca_par_nouveaute"], "uplift_nouveautes_magasin": p["uplift_nouveautes_magasin"],
               "rapports": p["rapports"]}
    tableau = pd.read_parquet(dossier / "bases.parquet")
    bases = {nom: tableau[nom].reindex(donnees["boutiques"].id_boutique.values).rename("ca_base") for nom in tableau.columns}
    return donnees, bases


def present(dossier=DOSSIER):
    return all((Path(dossier) / f).exists() for f in ["boutiques.parquet", "hausses.parquet", "bases.parquet", "parametres.json"])


if __name__ == "__main__":
    exporter()
