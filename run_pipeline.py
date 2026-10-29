"""
Exécution de toute la chaîne du projet 4, notebook par notebook, dans l'ordre.

Chaque notebook est exécuté par Papermill dans son propre dossier (les notebooks retrouvent
la racine du projet tout seuls). La copie exécutée, avec ses résultats, est rangée dans
notebooks/executes/ ; le notebook d'origine n'est pas modifié. La chaîne s'arrête au premier
notebook en erreur.

Prérequis : l'extraction des données (python -m src.extraction et python -m src.contexte)
a déjà été faite, et l'environnement .venv est activé.

    python run_pipeline.py                   # toute la chaîne
    python run_pipeline.py --depuis 10       # à partir du notebook 10
    python run_pipeline.py --seulement 14    # un seul notebook
    python run_pipeline.py --liste           # affiche l'ordre sans rien exécuter
"""
import argparse
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent
NOTEBOOKS = RACINE / "notebooks"
EXECUTES = NOTEBOOKS / "executes"

# Ordre d'exécution : chaque notebook lit ce qu'écrivent les précédents.
# 06b passe avant 06, qui réutilise ses mesures de l'assortiment.
ORDRE = [
    ("00", "1_preparation/00_inventaire.ipynb"),
    ("01", "1_preparation/01_etl.ipynb"),
    ("02", "1_preparation/02_flocon.ipynb"),
    ("03", "1_preparation/03_diagnostic.ipynb"),
    ("04", "1_preparation/04_nettoyage.ipynb"),
    ("05", "1_preparation/05_variables.ipynb"),
    ("05b", "1_preparation/05b_charges.ipynb"),
    ("05c", "1_preparation/05c_stock_objectifs.ipynb"),
    ("06b", "2_analyses/06b_q1_chute_des_ventes.ipynb"),
    ("06", "2_analyses/06_q1_facteurs_rentabilite.ipynb"),
    ("07", "2_analyses/07_q2_promotions.ipynb"),
    ("08", "2_analyses/08_q3_q4_retours.ipynb"),
    ("09", "2_analyses/09_q5_remises.ipynb"),
    ("10", "3_modeles/10_prevision_ventes.ipynb"),
    ("14", "4_prescriptif/14_simulateur.ipynb"),
]


def selection(depuis=None, seulement=None):
    codes = [code for code, _ in ORDRE]
    for demande in (depuis, seulement):
        if demande is not None and demande not in codes:
            sys.exit(f"Notebook « {demande} » inconnu. Codes possibles : {', '.join(codes)}")
    if seulement:
        return [e for e in ORDRE if e[0] == seulement]
    if depuis:
        return ORDRE[codes.index(depuis):]
    return ORDRE


def executer(etapes):
    import papermill as pm          # importé ici : --liste fonctionne même sans Papermill

    EXECUTES.mkdir(parents=True, exist_ok=True)
    debut_total = time.time()
    for rang, (code, chemin) in enumerate(etapes, start=1):
        source = NOTEBOOKS / chemin
        if not source.exists():
            sys.exit(f"Introuvable : {source.relative_to(RACINE)}")
        sortie = EXECUTES / source.name
        print(f"[{rang}/{len(etapes)}] {code} · {chemin} …", flush=True)
        debut = time.time()
        try:
            pm.execute_notebook(str(source), str(sortie), cwd=str(source.parent),
                                kernel_name="python3", progress_bar=False)
        except Exception as erreur:            # PapermillExecutionError : la cellule fautive est dans la copie
            print(f"\nÉchec dans {code} après {time.time() - debut:.0f} s.")
            print(f"Ouvrir {sortie.relative_to(RACINE)} pour voir la cellule en erreur.")
            print(f"Reprendre ensuite avec : python run_pipeline.py --depuis {code}")
            print(f"\n{type(erreur).__name__} : {erreur}"[:2000])
            sys.exit(1)
        print(f"        terminé en {time.time() - debut:.0f} s", flush=True)
    print(f"\nChaîne terminée : {len(etapes)} notebook{'s' if len(etapes) > 1 else ''} en {(time.time() - debut_total) / 60:.1f} min.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exécute les notebooks du projet 4 dans l'ordre.")
    groupe = parser.add_mutually_exclusive_group()
    groupe.add_argument("--depuis", help="code du premier notebook à exécuter (ex. 10)")
    groupe.add_argument("--seulement", help="code du seul notebook à exécuter (ex. 14)")
    parser.add_argument("--liste", action="store_true", help="affiche l'ordre sans rien exécuter")
    args = parser.parse_args()

    etapes = selection(args.depuis, args.seulement)
    if args.liste:
        for code, chemin in etapes:
            print(f"{code:>4}  notebooks/{chemin}")
    else:
        executer(etapes)
