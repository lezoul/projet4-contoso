# Projet 4 : Analyse des données de vente et retours

Collège La Cité · Science des données appliquées · Automne 2026

**Problématique** : optimisation de la performance commerciale, par l'analyse des drivers de vente, des retours et de l'impact des promotions, mesurés en marge brute en valeur.

## Équipe

| Rôle | Membre |
|---|---|
| Product Owner | Yacine Lezoul |
| Scrum Master | Achraf Chihab |
| Développeur | Barnabe Landry Evouna |
| Développeur | Mouncif Bouchachi |

## Données

- **Ventes** : fichiers trimestriels fournis (`data/raw/contoso/Sales/Sales AAAA Tn.csv`). Ils correspondent à la table `FactSales` de la base publique **Contoso Retail DW** de Microsoft (2008-2009), avec des dates décalées de 12 ans (2020-2021).
- **Dimensions** : 9 tables extraites de Contoso Retail DW par `Connexion.py` (`data/raw/contoso/Dim/`).

Le dossier `data/` n'est pas versionné sur GitHub. Il est partagé par OneDrive ou Teams.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
nbstripout --install            # retire les sorties des notebooks avant chaque commit
```

## Obtenir les données

1. Télécharger la base Contoso Retail DW (ContosoBIdemoBAK, Microsoft Download Center) et la restaurer dans SQL Server Express avec SSMS.
2. Vérifier les paramètres de connexion dans `src/config.py` (serveur, pilote ODBC).
3. Lancer `python Connexion.py` : les tables de dimension sont écrites dans `data/raw/contoso/Dim/`.
4. Copier les fichiers de ventes fournis dans `data/raw/contoso/Sales/`.

## Structure du projet

| Dossier | Contenu |
|---|---|
| `data/raw` | Données brutes, jamais modifiées |
| `data/interim` | Données transformées (après ETL), pas encore nettoyées |
| `data/clean` | Données nettoyées et validées, agrégats |
| `data/outputs` | Résultats des modèles (prévisions, scénarios, optimisation) |
| `notebooks/` | Un notebook par étape, rangés par phase (`1_preparation` à `4_prescriptif`) |
| `src/` | Fonctions partagées et configuration (`config.py`) |
| `tests/` | Vérifications automatiques (pytest) |
| `dashboards/` | Tableaux de bord Excel et Power BI |
| `reports/` | Figures, livrables L1 à L5, présentations |

L'arborescence détaillée est décrite dans `reports/livrables/L1_L2_phases_backlog/L1_phases_projet.docx`.

## Exécution

Les notebooks s'exécutent dans l'ordre de leur numéro. Chacun lit le dossier de l'étape précédente et écrit dans le suivant : `raw → interim → clean → outputs`.

```bash
jupyter notebook notebooks/1_preparation/00_inventaire.ipynb   # un notebook
python run_pipeline.py                                          # tout le pipeline (à partir du sprint 1)
pytest                                                          # vérifications automatiques
```

## Conventions

- Tous les chemins viennent de `src/config.py`, jamais écrits en dur dans les notebooks.
- Un notebook par responsable, pour éviter les conflits Git.
- Une fonction utilisée dans au moins deux notebooks passe dans `src/`.
- Les données brutes (`data/raw`) ne sont jamais modifiées.
