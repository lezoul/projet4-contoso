# Projet 4 · Analyse des ventes, retours et promotions (Contoso)

Pourquoi un distributeur d'électronique perd-il de l'argent dans ses magasins alors qu'il reste bénéficiaire ? Ce projet suit les ventes, les charges, les promotions et les retours de 56 boutiques sur trois exercices (2019 à 2021), du chargement des données brutes jusqu'aux recommandations chiffrées.

Projet de cours en équipe, mené en Scrum : *Projet analyse de données*, Science des données appliquées, Collège La Cité (Ottawa), automne 2026.

## Problématique

Optimiser la performance commerciale en répondant à cinq questions de recherche :

| | Question |
|---|---|
| Q1 | Quels facteurs déterminent la performance des ventes (boutique, produit, promotion) ? |
| Q2 | Quel est l'effet des promotions sur les ventes, et à quel coût ? |
| Q3 | Quels sont les patterns de retour de produits ? |
| Q4 | Existe-t-il une corrélation entre les remises et le taux de retour ? |
| Q5 | Quels niveaux de remise maximisent la marge ? |

L'étude porte sur le dernier exercice, 2021, qui est la situation à régler. 2019 sert de référence et 2020 d'exercice de bascule.

## Principaux résultats

**L'entreprise reste bénéficiaire, ce sont les magasins qui basculent.** Le chiffre d'affaires net passe de 945,4 M$ en 2019 à 688,2 M$ en 2021 (−27,2 %), à taux de marge inchangé (56 %). Le résultat d'exploitation des magasins passe de 121,6 M$ à −10,8 M$ : 48 magasins sur 48 étaient bénéficiaires en 2019, 4 sur 53 en 2021.

**Ce ne sont pas les clients qui ont cessé d'acheter, c'est l'assortiment qui a vieilli.**
- L'entreprise lance de moins en moins de produits : 552 en 2019, 429 en 2020, 272 en 2021, et aucun au second semestre 2021.
- La part des nouveautés dans les ventes des magasins tombe de 39 % à 10 %, et leur recul porte 69 % de la chute des magasins.
- En 2021, 59 % des couples magasin et produit n'enregistrent aucune vente.
- Les grands comptes professionnels de la boutique en ligne partent quand les nouveautés s'épuisent.

**Les charges ne suivent pas les ventes.** Les frais généraux augmentent de 17 % pendant que les ventes baissent. Ils passent de 16,4 % à 36,8 % du chiffre d'affaires des magasins.

**Promotions, remises et retours ne sont pas les problèmes prioritaires.**
- Q2 : aucun gain de ventes démontré pour les promotions, alors que leur coût est certain (13,9 M$ de remises en 2021).
- Q3 : aucun pattern de retour. Une ligne sur sept a un retour, presque toujours d'une seule unité.
- Q4 : la remise ajoute environ 3 points de retours en ligne et chez le revendeur, et rien en magasin. L'enjeu est de 0,31 M$ au plus.
- Q5 : en magasin, la remise est un coût sans contrepartie et le meilleur niveau est l'absence de remise. Ailleurs, un niveau plus bas que 20 % est à confirmer par un essai.

**Leviers chiffrés sur 2021, en gain de résultat par an**

| Levier | Gain estimé |
|---|---|
| Revenir au rythme de lancement de 2019 | 46,1 M$ (gain brut, coût de lancement non inclus) |
| Annuler les hausses de frais généraux | 9,2 M$ |
| Publicité des magasins −10 %, avec un test piloté | 6,2 M$ |
| Arrêter les remises en magasin | 5,4 M$ |
| Remettre les nouveautés en rayon | 3,8 M$ |
| Réduire les retours de moitié | 2,6 M$ au plus |

Ce sont des pistes de réflexion pour le métier, pas des décisions : chaque levier repose sur des hypothèses explicitées dans le rapport.

## Données

Les données viennent de la base publique **Contoso Retail DW** de Microsoft, restaurée dans SQL Server Express. Les dates de la base (2007 à 2009) sont décalées de 12 ans pour correspondre à l'énoncé (2019 à 2021).

| Source | Contenu | Volume |
|---|---|---|
| `FactSales` | Ventes par boutique, produit, jour et promotion | 715 291 lignes, 2 426,1 M$ de chiffre d'affaires brut |
| `FactStrategyPlan` | Charges par boutique et par mois : coût des ventes, frais généraux, publicité, impôts | 533 370 lignes |
| `FactOnlineSales` | Ventes en ligne détaillées, par commande et par client | |
| `FactInventory` | Stock hebdomadaire par boutique et par produit | |
| Dimensions | Boutique, géographie, produit (3 niveaux), promotion, date, canal, devise, compte, scénario | |
| Contexte | Jours fériés par pays (bibliothèque `holidays`), sévérité des mesures COVID-19 (OxCGRT, Université d'Oxford) | |

Le périmètre couvre 56 boutiques dans 17 pays, 2 516 produits et 1 096 jours. Les fichiers fournis au départ ne couvraient que 5 catégories sur 8 et les trimestres 1 à 3 (37 % du chiffre d'affaires) : le projet repart des ventes complètes, avec l'accord du professeur.

Le dossier `data/` n'est pas versionné : il se reconstruit avec les scripts d'extraction (voir *Installation*).

## Démarche

| Phase | Notebook | Ce qu'il fait |
|---|---|---|
| Préparation | `00_inventaire` | Inventaire des sources, périmètre et justification du passage aux ventes complètes |
| | `01_etl` | Chargement, harmonisation des types et des dates, réalignement des dimensions |
| | `02_flocon` | Modèle en flocon : tables de faits et de dimension, contexte par pays et par jour |
| | `03_diagnostic` | 56 contrôles de qualité : valeurs manquantes, doublons, types, cohérence métier |
| | `04_nettoyage` | 8 règles de nettoyage, 0 ligne supprimée, 0 montant modifié, 29 contrôles de validation |
| | `05_variables` | Variables dérivées : marge en valeur, ventes nettes, taux de remise effectif, agrégats |
| | `05b_charges` | Deuxième table de faits : charges, compte de résultat par boutique et par mois |
| | `05c_stock_objectifs` | Stock et mesures de l'offre (assortiment, rotation, nouveautés) |
| Analyse | `06b_q1_chute_des_ventes` | Q1 : pourquoi les ventes ont chuté (assortiment, rotation, grands comptes en ligne) |
| | `06_q1_facteurs_rentabilite` | Q1 : facteurs de performance, rentabilité après charges, leviers chiffrés |
| | `07_q2_promotions` | Q2 : effet et coût des promotions (avant et après, magasin témoin, corrélations) |
| | `08_q3_q4_retours` | Q3 et Q4 : patterns de retour, lien avec les remises (régression logistique) |
| | `09_q5_remises` | Q5 : niveaux de remise et marge, par canal et par segment |
| Prédiction | `10` à `12` | À venir : prévision des ventes, départ des grands comptes en ligne, typologie des magasins |
| Prescription | `13` et `14` | À venir : priorités de renouvellement de l'assortiment, simulateur de scénarios |

Les conclusions s'appuient sur des tests d'hypothèse (Mann-Whitney, Kruskal-Wallis, régressions) plutôt que sur de simples comparaisons de moyennes. Chaque notebook commente ses constats d'un point de vue métier.

## Arborescence

```
projet4-contoso/
├── Notebooks/
│   ├── 1_preparation/          00 à 05c : inventaire, ETL, modèle en flocon, diagnostic, nettoyage, variables
│   ├── 2_analyses/             06 à 09 : une ou deux questions de recherche par notebook
│   ├── 3_modeles/              notebooks prédictifs de l'UA3 (à venir)
│   ├── 4_prescriptif/          notebooks prescriptifs de l'UA3 (à venir)
│   └── executes/               copies exécutées produites par run_pipeline.py (non versionnées)
├── src/
│   ├── config.py               tous les chemins et paramètres du projet, importés par les notebooks
│   ├── extraction.py           extraction unique des données Contoso depuis SQL Server vers data/raw
│   ├── contexte.py             jours fériés et sévérité COVID-19 par pays et par jour
│   ├── etl.py                  chargement et harmonisation des tables
│   ├── analyse.py              fonctions statistiques partagées par les notebooks d'analyse
│   └── viz.py                  charte graphique commune (couleurs, police, formats)
├── data/                       non versionné
│   ├── raw/                    brut, jamais modifié : professeur/, contexte/, contoso/ (Dim, Sales, Plan, Stock)
│   ├── interim/                transformé, pas encore nettoyé
│   ├── clean/                  nettoyé et validé : tables de faits, dimensions, agrégats
│   └── outputs/                résultats des modèles (prévisions, scénarios, optimisation)
├── reports/
│   ├── figures/                graphiques exportés par les notebooks
│   ├── livrables/              L1 et L2 (phases, backlog), L3 et L4 (rapport et présentation de l'UA2), L5
│   └── presentations/          présentation de l'UA1
├── dashboards/
│   └── app_simulateur.py       application Streamlit : simulateur de scénarios 2022
├── run_pipeline.py             exécution de tous les notebooks dans l'ordre (à venir)
├── requirements.txt
└── README.md
```

## Installation

Prérequis : Windows, Python 3.12, SQL Server Express et le pilote *ODBC Driver 17 for SQL Server*.

```powershell
git clone https://github.com/lezoul/projet4-contoso.git
cd projet4-contoso
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
nbstripout --install            # retire les sorties des notebooks à chaque commit
```

**Reconstruire les données**

1. Télécharger la sauvegarde *ContosoBIdemoBAK* sur le Microsoft Download Center et la restaurer dans SQL Server Express avec SSMS.
2. Vérifier le serveur et le pilote dans `src/config.py` (`SQL_SERVER`, `SQL_DRIVER`).
3. Déposer les fichiers de ventes fournis par le professeur dans `data/raw/professeur/`.
4. Lancer l'extraction depuis la racine du projet (une dizaine de minutes, lecture seule sur la base) :

   ```powershell
   python -m src.extraction
   ```

5. Pour les données de contexte, télécharger le fichier national *compact* d'OxCGRT ([covid-policy-dataset](https://github.com/OxCGRT/covid-policy-dataset/tree/main/data)), le déposer dans `data/raw/contexte/`, puis lancer :

   ```powershell
   python -m src.contexte
   ```

## Exécution

Les notebooks s'exécutent dans l'ordre de leur numéro : `00`, `01`, `02`, `03`, `04`, `05`, `05b`, `05c`, puis `06b`, `06`, `07`, `08`, `09`. Chacun lit le dossier de l'étape précédente et écrit dans le suivant : `raw → interim → clean → outputs`.

**Application Streamlit (simulateur de scénarios)**

Après le notebook 14, qui enregistre la base 2022 dans `data/outputs/scenarios/`, lancer depuis la racine du projet :

```powershell
streamlit run dashboards/app_simulateur.py
```

L'application s'ouvre dans le navigateur. Elle n'a aucun calcul propre : chaque curseur alimente `reglages(...)` et le moteur `src/simulateur.py`, le même que le notebook 14.

## Conventions

- Tous les chemins viennent de `src/config.py`, jamais écrits en dur dans les notebooks.
- Les données brutes (`data/raw`) ne sont jamais modifiées.
- Une fonction utilisée dans au moins deux notebooks passe dans `src/`.
- Les notebooks sont versionnés sans leurs sorties.

## Outils

Python (pandas, NumPy, SciPy, statsmodels, scikit-learn), SQL Server et SQLAlchemy, Jupyter, Matplotlib, seaborn et Plotly, Git et GitHub, Jira pour le suivi Scrum. Streamlit pour l'application de l'UA3.

## Équipe

| Rôle | Membre |
|---|---|
| Product Owner | Yacine Lezoul |
| Scrum Master | Achraf Chihab |
| Développeur | Barnabe Landry Evouna |
| Développeur | Mouncif Bouchachi |

Professeur : Tinninnan Soro.
