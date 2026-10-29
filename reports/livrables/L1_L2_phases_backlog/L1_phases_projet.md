# Projet Agile : Analyse des données de vente et retours (Projet 4)

## Équipe
| Rôle | Membre |
|---|---|
| Product Owner | Yacine Lezoul |
| Scrum Master | Achraf Chihab |
| Développeur | Jean Robert Joseph |
| Développeur | Barnabe Landry Evouna |
| Développeur | Douyeri Lamoussa Sanogo |
| Développeur | Mouncif Bouchachi |

Dans la suite du document, les membres sont désignés par leur prénom usuel : Yacine, Achraf, Jean Robert, Barnabé, Lamoussa et Mouncif.

## Vision produit
Optimiser la performance commerciale en identifiant les drivers de vente, les facteurs de retour et l'impact réel des promotions, mesurés en **marge brute en valeur** (et non en taux), afin de proposer des recommandations opérationnelles chiffrées.

Le projet couvre les quatre niveaux d'analyse : **descriptive** (que s'est-il passé ?), **diagnostique** (pourquoi ?), **prédictive** (que va-t-il se passer ?) et **prescriptive** (que faut-il faire ?). Le volet prescriptif simule des scénarios de promotion et détermine la politique de remise qui maximise la marge en valeur nette des retours.

Le jeu de données fourni ne contient que la table des transactions (2020-2021), sans aucune table de dimension. Le Sprint 0 a donc inclus une phase de **collecte et recherche de données**, décrite ci-dessous.

## Collecte des données : démarche et résultats

### 1. Identification de la source
La structure des fichiers fournis (IdVente, IdBoutique, IdProduit, IdPromotion, montants de vente, de retour et de remise) est identique à la table **FactSales** de la base publique **Contoso Retail DW** de Microsoft, à deux colonnes près (canal et devise).

### 2. Collecte
- Téléchargement de la base (ContosoBIdemoBAK, Microsoft Download Center)
- Restauration du fichier `.bak` dans **SQL Server Express** avec SSMS
- Connexion depuis Python (pyodbc, SQLAlchemy) et extraction de chaque table dans son propre CSV ; les colonnes géographiques (type `geography`) sont converties en texte

### 3. Vérification
- Les IdVente d'un échantillon de nos fichiers ont été retrouvés dans FactSales avec **les mêmes boutiques, produits, quantités, remises et montants** : **IdVente = SalesKey**
- Les dates sont **décalées de 12 ans** : 2008-2009 dans Contoso correspondent à 2020-2021 dans nos données
- Exemple : la promotion 10 est la « European Holiday Promotion » (remise saisonnière de 20 %), active du 1er octobre 2019 au 31 janvier 2020 une fois les dates réalignées
- Règles métier observées : Montant des ventes = Prix unitaire × Quantité − Remise ; une vente peut porter une promotion sans remise, et la remise ne s'applique qu'à une partie des unités

### 4. Arborescence des clés étrangères
Les relations déclarées dans la base (`sys.foreign_keys`) donnent le chemin de jointure complet à partir des ventes, y compris les doubles jointures :

```
FactSales ─┬─ StoreKey     → DimStore   → DimGeography
           ├─ ProductKey   → DimProduct → DimProductSubcategory → DimProductCategory
           ├─ PromotionKey → DimPromotion
           ├─ DateKey      → DimDate
           ├─ channelKey   → DimChannel
           └─ CurrencyKey  → DimCurrency
```

### 5. Sélection des tables : 8 retenues sur 17
Une table n'est utile que si elle se relie à nos ventes (directement ou par double jointure) **et** aide à répondre à une question de recherche.

| Table | Décision | Lien avec nos ventes | Questions servies |
|---|---|---|---|
| DimStore | Retenue | IdBoutique | Q1 (type, surface, effectif, ouverture), Q3 |
| DimGeography | Retenue | Double jointure via DimStore | Q1 (analyse géographique) |
| DimProduct | Retenue | IdProduit | Q1, Q3, Q5 (marque, classe, prix catalogue) |
| DimProductSubcategory | Retenue | Double jointure via DimProduct | Q1, Q3, Q5 |
| DimProductCategory | Retenue | Triple jointure via DimProduct | Q1, Q3, Q5 |
| DimPromotion | Retenue | IdPromotion | Q2, Q4, Q5 (type, % de remise, dates) |
| DimChannel | Retenue | Canal récupéré depuis FactSales (IdVente = SalesKey) | Q1 : 3 canaux présents dans nos ventes (48 %, 30 % et 21 % des lignes) |
| DimCurrency | Écartée | Devise récupérée depuis FactSales | Une seule devise dans nos ventes : aucune information utile |
| DimDate | Référence | Dates 2007-2009 | Remplacée par notre propre calendrier 2020-2021 (fériés, COVID-19) |
| DimCustomer | Écartée | Aucun lien avec FactSales (liée aux ventes en ligne) | |
| DimAccount, DimEntity, DimScenario | Écartées | Comptabilité et budget (FactStrategyPlan) | |
| DimEmployee, DimMachine, DimOutage, DimSalesTerritory | Écartées | Aucun lien avec FactSales | |

### 6. Inventaire et homogénéisation des ventes (notebook 00_inventaire)
Les 6 fichiers de ventes ont été chargés, homogénéisés et contrôlés sans modifier les données brutes :

| Contrôle | Résultat |
|---|---|
| Fichiers | 6 fichiers, chacun conforme au trimestre annoncé par son nom |
| Trimestres absents | 2020 T4 et 2021 T4 (octobre à décembre des deux années) |
| Ventes | 144 874 lignes, du 1er janvier 2020 au 30 septembre 2021 |
| Homogénéisation des formats | Encodage UTF-8 et 14 colonnes identiques dans les 6 fichiers ; dates au format mois/jour/année ; montants texte (« $1,062.60 ») convertis en nombres ; aucun échec de conversion |
| Doublons | Aucun IdVente en double |
| Correspondance des clés | 100 % pour les boutiques (56), les produits (1 310), les promotions (12) et les ventes (IdVente = SalesKey) |
| Décalage de 12 ans | 98,66 % des ventes en promotion tombent dans la période de leur promotion avec un décalage de 12 ans, contre 0 à 1,6 % pour les autres décalages |
| Canal et devise | 3 canaux, 1 seule devise |

Résultats détaillés : `reports/livrables/L1_L2_phases_backlog/dictionnaire_donnees.xlsx` et `reports/figures/00_ca_mensuel.png`.

### 7. Données de contexte (à collecter)
Jours fériés 2020-2021 et périodes de confinement COVID-19 pour les pays des boutiques.

## Calendrier général
Projet sur **7 sprints** (1 à 2 semaines), démarrage **lundi 21 septembre 2026**. Les sprints sont calés sur les dates de remise communiquées par le professeur : chaque remise tombe un lundi, le sprint se termine donc le dimanche précédent.

| Sprint | Thème | Dates | Sprint Review / Rétro | Livrable remis |
|---|---|---|---|---|
| 0 | Cadrage, collecte et recherche de données | 21 sept.-4 oct. 2026 | ven. 2 oct. | L1 et L2 + présentation UA1 (lun. 5 oct.) |
| 1 | ETL, consolidation et modèle en flocon | 5-18 oct. 2026* | ven. 16 oct. | |
| 2 | Diagnostic de qualité et nettoyage | 19 oct.-1 nov. 2026 | ven. 30 oct. | |
| 3 | Transformation et rapport de diagnostic | 2-8 nov. 2026 | ven. 6 nov. | L3 (lun. 9 nov.) |
| 4 | Analyse Q1 à Q4, modèle prédictif des retours, tableau de bord Excel | 9-22 nov. 2026 | ven. 20 nov. | |
| 5 | Q5, modèles prédictifs, simulation et optimisation des remises, Power BI, rapport et présentation | 23 nov.-6 déc. 2026 | ven. 4 déc. | L4 (lun. 7 déc.) |
| 6 | Analyse de sensibilité, plan promotionnel et rapport final | 7-13 déc. 2026 | ven. 11 déc. | L5 (lun. 14 déc.) |

*Le 12 octobre 2026 est l'Action de grâce (jour férié) : le Sprint Planning du sprint 1 a lieu le lundi 5 octobre, pas d'impact sur la date de fin.

## Livrables et pondération
| Livrable | Contenu | Date de remise | Poids |
|---|---|---|---|
| L1 | Identification des phases du projet | 5 oct. 2026 | 20 % (avec L2) |
| L2 | Création de tâches granulaires (ce backlog) | 5 oct. 2026 | |
| L3 | Diagnostic, nettoyage et transformation des données | 9 nov. 2026 | 25 % |
| L4 | Analyse exploratoire, rapport et présentation des conclusions | 7 déc. 2026 | 35 % |
| L5 | Rapport final avec recommandations opérationnelles | 14 déc. 2026 | 20 % |

## Rythme des cérémonies Scrum
- **Lundi (début de sprint)** : Sprint Planning (45-60 min) : sélection des user stories, découpage en tâches, estimation, répartition
- **Mardi à jeudi** : Daily standup (15 min) : fait / à faire / blocages
- **Sprints de 2 semaines** : point de mi-sprint le lundi de la 2e semaine (20 min) pour réajuster la charge
- **Vendredi (fin de sprint)** :
  - Sprint Review (30-45 min) : démonstration des résultats au Product Owner
  - Rétrospective (30 min) : ce qui a bien marché / ce qui peut être amélioré / actions pour le sprint suivant
- **Week-end avant remise** : marge de sécurité pour la relecture et la mise en forme du livrable

## Definition of Done (générale)
- Code versionné (Git) et documenté, revu par un autre membre
- Résultats reproductibles (le pipeline s'exécute de bout en bout à partir des fichiers bruts)
- Hypothèses et limites documentées
- Résultat validé par le PO en Sprint Review
- Livrable présentable (graphique, tableau, tableau de bord ou synthèse écrite)

## Outils
- Gestion du backlog : Jira / GitHub Projects (backlog détaillé de 166 tâches dans le fichier Excel joint)
- Code, ETL, analyse et modélisation : Python (pandas, numpy, matplotlib, seaborn, plotly, scipy, statsmodels, scikit-learn, shap, pytest), notebooks Jupyter
- Orchestration et versionnement : papermill, Git / GitHub, nbstripout
- Extraction des données : SQL Server Express, SSMS, pyodbc, SQLAlchemy
- Optimisation : Python (scipy.optimize, PuLP) et Solveur Excel
- Tableaux de bord et simulation : Excel (Power Query, tableaux croisés dynamiques, segments, Gestionnaire de scénarios) et Power BI (modèle en flocon, DAX, paramètre what-if)
- Présentations : PowerPoint
- Rapports : Word

## Architecture du projet et pipeline d'exécution
Principe : les **données** (`data/`, lourdes, non versionnées), le **code** (`notebooks/`, `src/`, `tests/`, versionnés sur GitHub) et les **livrables** (`dashboards/`, `reports/`) sont séparés. Les données passent par quatre états : brut, transformé, validé, résultats.

```
Projet ADD/
│
├── README.md                          # présentation du projet, installation, exécution
├── requirements.txt                   # bibliothèques Python et leurs versions
├── .gitignore                         # ce que GitHub ignore : data/, notebooks/executes/
├── Connexion.py                       # extraction SQL Server → data/raw/contoso
├── run_pipeline.py                    # lance tous les notebooks dans l'ordre
│
├── data/                              # LES DONNÉES
│   ├── raw/                           # 1. BRUT : jamais modifié
│   │   ├── contoso/
│   │   │   ├── Dim/                   # tables de dimension extraites de Contoso
│   │   │   └── Sales/                 # ventes fournies + clés canal et devise
│   │   └── contexte/                  # jours fériés, périodes COVID-19
│   │
│   ├── interim/                       # 2. TRANSFORMÉ : pas encore nettoyé
│   │   ├── ventes_consolidees.parquet # toutes les ventes, montants en nombres
│   │   ├── dimensions_realignees/     # dates des dimensions décalées de +12 ans
│   │   ├── dim_date.parquet           # notre calendrier 2020-2021
│   │   └── ventes_jointes.parquet     # ventes + toutes les dimensions
│   │
│   ├── clean/                         # 3. VALIDÉ : prêt pour l'analyse
│   │   ├── fait_ventes.parquet        # ventes avec anomalies traitées
│   │   ├── dimensions/                # dimensions vérifiées
│   │   ├── journal_nettoyage.csv      # ce qui a été corrigé, et pourquoi
│   │   ├── rapport_validation.csv     # résultat des contrôles de qualité
│   │   └── agregats/                  # totaux par semaine, boutique, produit, promotion
│   │
│   └── outputs/                       # 4. RÉSULTATS : lus par Power BI et Excel
│       ├── predictions/               # prévision des ventes, risque de retour
│       ├── scenarios/                 # résultats des simulations
│       └── optimisation/              # remise optimale, plan promotionnel
│
├── notebooks/                         # LE CODE, étape par étape
│   ├── 1_preparation/
│   │   ├── 00_inventaire.ipynb        # vérifier les fichiers et les clés
│   │   ├── 01_etl.ipynb               # raw → interim : regrouper, convertir
│   │   ├── 02_flocon.ipynb            # réaligner les dates, joindre les dimensions
│   │   ├── 03_diagnostic.ipynb        # repérer les anomalies
│   │   ├── 04_nettoyage.ipynb         # interim → clean : corriger, valider
│   │   └── 05_variables.ipynb         # marge, taux de retour, taux de remise
│   ├── 2_analyses/
│   │   ├── 06_q1_performance.ipynb    # facteurs de performance des ventes
│   │   ├── 07_q2_promotions.ipynb     # effet des promotions
│   │   ├── 08_q3_q4_retours.ipynb     # retours et lien avec les remises
│   │   └── 09_q5_remises.ipynb        # marge selon le niveau de remise
│   ├── 3_modeles/
│   │   ├── 10_risque_retour.ipynb     # prédire les ventes retournées
│   │   ├── 11_reponse_promo.ipynb     # prédire l'effet d'une remise
│   │   └── 12_prevision.ipynb         # prévoir les ventes hebdomadaires
│   ├── 4_prescriptif/
│   │   ├── 13_simulation.ipynb        # comparer des scénarios de remise
│   │   ├── 14_optimisation.ipynb      # trouver la remise optimale
│   │   └── 15_plan_promo.ipynb        # tester la solidité, bâtir le plan
│   └── executes/                      # copies exécutées (preuve que tout tourne)
│
├── src/                               # FONCTIONS RÉUTILISÉES par les notebooks
│   ├── config.py                      # chemins des dossiers, décalage de 12 ans
│   ├── etl.py                         # charger, convertir, joindre
│   ├── qualite.py                     # contrôles et règles de nettoyage
│   ├── features.py                    # calcul des indicateurs
│   ├── modeles.py                     # entraîner et évaluer les modèles
│   ├── prescriptif.py                 # simuler et optimiser
│   └── viz.py                         # charte graphique : couleurs, police, format des montants
│
├── tests/                             # VÉRIFICATIONS AUTOMATIQUES
│   ├── test_etl.py                    # montants bien convertis, aucune vente perdue
│   ├── test_qualite.py                # ventes = prix × quantité − remise
│   ├── test_features.py               # taux entre 0 et 1, marge correcte
│   └── test_prescriptif.py            # remise, budget et retours dans les limites
│
├── dashboards/                        # TABLEAUX DE BORD
│   ├── excel/
│   │   ├── tableau_de_bord.xlsx       # indicateurs, graphiques, segments
│   │   └── optimisation_solveur.xlsx  # optimisation refaite avec le Solveur
│   └── powerbi/
│       └── projet4.pbix               # lit data/clean et data/outputs
│
└── reports/                           # LIVRABLES
    ├── figures/                       # graphiques exportés des notebooks
    ├── livrables/
    │   ├── L1_L2_phases_backlog/
    │   ├── L3_diagnostic_nettoyage/
    │   ├── L4_analyse/
    │   └── L5_rapport_final/
    └── presentations/
        ├── UA1_cadrage.pptx
        └── finale_conclusions.pptx
```

### Notebooks : contenu, flux des données et responsables
| Notebook | Contenu | Lit dans | Écrit dans | Sprint | Responsable |
|---|---|---|---|---|---|
| Connexion.py | Extraction des tables Contoso | SQL Server | raw/contoso | 0 | Yacine |
| 00_inventaire | Vérifier les fichiers et la correspondance des clés sur toutes les lignes | raw | reports/figures | 0 | Jean Robert |
| 01_etl | Regrouper les ventes, convertir les montants | raw | interim | 1 | Jean Robert |
| 02_flocon | Réaligner les dates (+12 ans), construire le calendrier, joindre les dimensions | raw, interim | interim | 1 | Mouncif |
| 03_diagnostic | Repérer les anomalies (manquants, incohérences, valeurs aberrantes) | interim | reports/figures | 2 | Barnabé |
| 04_nettoyage | Appliquer les règles, écrire le journal, valider | interim | clean | 2 | Mouncif |
| 05_variables | Marge en valeur, taux de retour, taux de remise, agrégats | clean | clean/agregats | 3 | Lamoussa |
| 06_q1_performance | Q1 : facteurs de performance des ventes | clean | reports/figures | 4 | Jean Robert et Barnabé |
| 07_q2_promotions | Q2 : effet des promotions | clean | reports/figures | 4 | Lamoussa |
| 08_q3_q4_retours | Q3 et Q4 : retours et lien avec les remises | clean | reports/figures | 4 | Mouncif |
| 09_q5_remises | Q5 : marge selon le niveau de remise | clean | reports/figures | 5 | Barnabé |
| 10_risque_retour | Prédire les ventes retournées | clean | outputs/predictions | 4 | Jean Robert |
| 11_reponse_promo | Prédire l'effet d'une remise | clean | outputs/predictions | 5 | Barnabé |
| 12_prevision | Prévoir les ventes hebdomadaires | clean/agregats | outputs/predictions | 5 | Lamoussa |
| 13_simulation | Comparer des scénarios de remise | clean, outputs/predictions | outputs/scenarios | 5 | Jean Robert |
| 14_optimisation | Trouver la remise optimale sous contraintes | outputs/predictions | outputs/optimisation | 5 | Jean Robert |
| 15_plan_promo | Tester la solidité, bâtir le plan promotionnel | outputs | outputs/optimisation | 6 | Jean Robert et Lamoussa |
| Excel, Power BI | Tableaux de bord et page what-if | clean, outputs | dashboards | 4-5 | Barnabé (Excel), Mouncif (Power BI) |

### Exécution
`python run_pipeline.py` lance tous les notebooks avec papermill dans l'ordre des dépendances. Les étapes indépendantes s'exécutent en parallèle, et une copie exécutée de chaque notebook est archivée dans `notebooks/executes/`.

| Étape | Notebooks | Mode |
|---|---|---|
| 1. Préparation | 00 → 01 → 02 → 03 → 04 → 05 | Séquentiel (chaque étape dépend de la précédente) |
| 2. Analyses | 06, 07, 08, 09 | En parallèle |
| 3. Modèles | 10, 11, 12 | En parallèle |
| 4. Prescriptif | 13 → 14 → 15 | Séquentiel |

### Tests automatiques (pytest)
Les tests sont lancés avant toute écriture dans `clean` ou `outputs` : une étape n'écrit ses résultats que si ses contrôles passent.

| Fichier | Vérifications |
|---|---|
| test_etl.py | « $1,062.60 » converti en 1062.60 ; aucune vente perdue à la jointure ; dates décalées de 12 ans |
| test_qualite.py | Montant des ventes = Prix × Quantité − Remise ; retours ≤ ventes ; quantité remisée ≤ quantité vendue |
| test_features.py | Taux de retour et de remise entre 0 et 1 ; marge = ventes − coût |
| test_prescriptif.py | Remise optimale entre 0 et 30 % ; budget de remise respecté ; taux de retour ≤ seuil ; le scénario actuel reproduit la situation observée |

### Conventions
- Les données de `raw` ne sont jamais modifiées : chaque étape lit le dossier précédent et écrit dans le suivant (raw → interim → clean → outputs), ce qui permet de relancer une étape sans refaire les précédentes.
- Tous les chemins viennent de `src/config.py`, jamais écrits en dur dans les notebooks.
- Un notebook par responsable pour éviter les conflits Git ; le code réutilisable va dans `src/` plutôt que d'être copié entre notebooks.
- Les sorties des notebooks sont retirées avant chaque commit (nbstripout) ; `data/` est partagé par OneDrive ou Teams, pas par GitHub.

---

## Épopées
| ID | Épopée | Objectif |
|---|---|---|
| E0 | Gestion de projet Scrum | Organiser l'équipe, planifier et suivre les sprints |
| E1 | Collecte et recherche de données | Inventorier les données, identifier les manques, collecter les dimensions et le contexte |
| E2 | Intégration et modélisation (ETL) | Consolider les trimestres, construire un modèle en flocon |
| E3 | Qualité et nettoyage | Diagnostiquer et corriger les anomalies |
| E4 | Transformation et variables dérivées | Créer les indicateurs de marge, de retour et de remise |
| E5 | Analyse exploratoire (Q1 à Q5) | Répondre aux questions de recherche |
| E6 | Modélisation prédictive | Prévoir les ventes, le risque de retour et la réponse aux promotions |
| E7 | Tableaux de bord | Explorer d'autres modes de visualisation (Excel, Power BI) |
| E8 | Documentation et livrables | Rapports, présentations et remises |
| E9 | Analyse prescriptive | Simuler des scénarios de promotion et déterminer la politique de remise optimale |

## Backlog produit (priorisé)
| # | User story | Épopée | Sprint | Priorité | Points |
|---|---|---|---|---|---|
| US01 | Cadre Scrum et espace de travail commun (board, dépôt Git, DoD) | E0 | 0 | Must | 3 |
| US02 | Inventaire et homogénéisation des données fournies (6 trimestres, dictionnaire initial) | E1 | 0 | Must | 3 |
| US03 | Identification des données manquantes et de leur impact, demande au professeur | E1 | 0 | Must | 2 |
| US04 | Collecte et vérification des tables de dimension (Contoso Retail DW), arborescence des clés, sélection des tables | E1 | 0 | Must | 8 |
| US05 | Collecte des données de contexte (jours fériés, périodes COVID-19) | E1 | 0 | Should | 3 |
| US06 | Phases et jalons du projet (Livrable 1) | E0 | 0 | Must | 2 |
| US07 | Backlog de tâches granulaires, estimées et priorisées (Livrable 2) | E0 | 0 | Must | 5 |
| US08 | Présentation PowerPoint du cadrage (UA1) | E8 | 0 | Must | 3 |
| US09 | Table de faits unique consolidant les 6 trimestres | E2 | 1 | Must | 5 |
| US10 | Modèle en flocon (faits ventes + boutique → géographie, produit → sous-catégorie → catégorie, promotion, date, canal) | E2 | 1 | Must | 8 |
| US11 | Pipeline reproductible exécutable en une commande (run_pipeline.py) | E2 | 1 | Must | 5 |
| US12 | Diagnostic complet de la qualité des données | E3 | 2 | Must | 8 |
| US13 | Nettoyage selon des règles documentées et testées | E3 | 2 | Must | 5 |
| US14 | Variables dérivées : marge en valeur, taux de retour, taux de remise | E4 | 3 | Must | 5 |
| US15 | Jeux agrégés prêts pour l'analyse et les tableaux de bord | E4 | 3 | Must | 3 |
| US16 | Rapport de diagnostic, nettoyage et transformation (Livrable 3) | E8 | 3 | Must | 5 |
| US17 | Q1 : facteurs déterminants de la performance des ventes | E5 | 4 | Must | 8 |
| US18 | Q2 : effet des promotions sur le volume et la marge en valeur | E5 | 4 | Must | 8 |
| US19 | Q3 : patterns de retour de produits | E5 | 4 | Must | 5 |
| US20 | Tableau de bord Excel interactif | E7 | 4 | Should | 5 |
| US21 | Q4 : corrélation entre remises et taux de retour | E5 | 4 | Must | 5 |
| US22 | Q5 : niveaux de remise qui maximisent la marge en valeur | E5 | 5 | Must | 5 |
| US23 | Modèle de prévision des ventes | E6 | 5 | Must | 8 |
| US24 | Tableau de bord Power BI multi-pages | E7 | 5 | Must | 8 |
| US25 | Rapport d'analyse et présentation des conclusions (Livrable 4) | E8 | 5 | Must | 8 |
| US26 | Rapport final avec recommandations opérationnelles (Livrable 5) | E8 | 6 | Must | 5 |
| US28 | Modèle prédictif du risque de retour et de ses facteurs (Q3, Q4) | E6 | 4 | Must | 5 |
| US29 | Modèle de réponse aux promotions : volume et marge attendus selon la remise (Q2, Q5) | E6 | 5 | Must | 8 |
| US30 | Simulation de scénarios de promotion (what-if) | E9 | 5 | Must | 5 |
| US31 | Optimisation du taux de remise par catégorie sous contraintes (Q5) | E9 | 5 | Must | 8 |
| US32 | Analyse de sensibilité et plan promotionnel recommandé | E9 | 6 | Must | 5 |
| US33 | Structure du dépôt, notebooks numérotés et conventions communes | E2 | 0 | Must | 3 |
| US27 | Cérémonies Scrum à chaque sprint | E0 | Tous | Must | 3 |

**Total : 33 user stories, 175 points, 166 tâches, environ 280 heures d'équipe.**

---

## Sprint 0 : Cadrage, collecte et recherche de données (21 sept.-4 oct.)
**Objectif** : cadrer le projet, combler le manque de données de dimension et remettre les livrables 1 et 2. *(Cadrage)*

- **Yacine (PO)** : rédige la vision produit, reformule les questions de recherche, envoie la demande au professeur sur les tables de dimension, définit les phases et jalons (L1), priorise le backlog
- **Achraf (SM)** : met en place le board Scrum (Jira / GitHub Projects), construit le diagramme de Gantt, saisit le backlog, anime le kick-off et rédige la Definition of Done
- **Jean Robert** : crée le dépôt Git, l'arborescence, les squelettes des 16 notebooks et l'environnement (requirements.txt, nbstripout), charge les 6 fichiers trimestriels et relève volumétrie, types et période couverte
- **Barnabé** : inventorie les données manquantes (boutique, produit, promotion, client, retours, stocks, charges) et évalue leur impact sur Q1 à Q5, rédige le dictionnaire de données initial
- **Lamoussa** : mesure le taux de correspondance des clés sur toutes les lignes des fichiers de ventes, évalue FactInventory (stocks) pour la démarque
- **Mouncif** : collecte les jours fériés et les périodes de confinement COVID-19 par pays, vérifie la cohérence des dates, documente les sources et conditions d'utilisation
- **Toute l'équipe** : présentation PowerPoint UA1 (contexte, données et manques, démarche de collecte, arborescence des clés et sélection des tables, phases, backlog et sprints), une partie par membre, répétition chronométrée

**État d'avancement (28 sept.)** : base Contoso restaurée et extraite (`Connexion.py`), source vérifiée (FactSales, décalage de 12 ans confirmé sur toutes les ventes), arborescence des clés établie, 8 tables retenues, environnement de travail en place (`.venv`, `requirements.txt`, `config.py`, `.gitignore`, README), charte graphique commune (`viz.py`), inventaire et homogénéisation des 6 fichiers de ventes terminés (00_inventaire), dictionnaire de données produit. Reste : données de contexte (reportées au sprint 1), Gantt, board Scrum, présentation UA1.

## Sprint 1 : ETL, consolidation et modèle en flocon (5-18 oct.)
**Objectif** : disposer d'une base unique, fiable et exploitable par Python, Excel et Power BI. *(Préparation)*

- **Jean Robert** : script de chargement, harmonisation des colonnes, types et formats de date, concaténation des trimestres, factorisation du code partagé dans `src/`, script `run_pipeline.py` (papermill) testé sur un poste vierge
- **Barnabé** : contrôle des doublons d'IdVente entre trimestres, réconciliation des lignes et des totaux avant et après consolidation
- **Lamoussa** : construction de la dimension date (jour, semaine, mois, trimestre, jour férié, période COVID), aplatissement des hiérarchies produit et géographie
- **Mouncif** : conception du schéma en flocon, réalignement des dates des dimensions (+12 ans), jointure des dimensions et du canal, traitement des clés sans correspondance (membre « Inconnu »), export Parquet et CSV dans data/interim
- **Yacine (PO)** : valide le modèle de données et le seuil de correspondance des clés acceptable

## Sprint 2 : Diagnostic de qualité et nettoyage (19 oct.-1 nov.)
**Objectif** : identifier toutes les anomalies et les traiter selon des règles validées. *(Analyse descriptive)*

- **Jean Robert** : taux de valeurs manquantes, valeurs nulles ou négatives, valeurs aberrantes (IQR, z-score) et leur visualisation
- **Barnabé** : contrôles arithmétiques (Montant des ventes = Prix unitaire × Quantité − Remise, Coût total = Coût unitaire × Quantité), comparaison avec les prix et coûts de DimProduct
- **Lamoussa** : contrôles de cohérence (retours ≤ ventes, quantité de remise ≤ quantité vendue, promotion sans remise, ventes hors dates de promotion ou de fonctionnement des boutiques), synthèse chiffrée des anomalies
- **Mouncif** : application des règles de nettoyage dans le pipeline (data/interim → data/clean), journal avant/après, tests de qualité automatisés (pytest)
- **Yacine (PO)** : arbitre les règles de traitement (supprimer, corriger, imputer, signaler)

## Sprint 3 : Transformation et rapport de diagnostic (2-8 nov.)
**Objectif** : produire les variables d'analyse et remettre le livrable 3. *(Préparation)*

- **Jean Robert** : marge brute en valeur, ventes nettes des retours, marge après retours (hypothèse documentée)
- **Barnabé** : taux de retour, taux de remise effectif, tranches de remise, indicateur promotion et attributs de DimPromotion
- **Lamoussa** : agrégats par boutique, produit, promotion et période, séries hebdomadaires pour la prévision, indicateurs standardisés (par transaction, par jour de promotion, par m²)
- **Mouncif** : visuels de qualité des données, mise à jour du dictionnaire avec les variables dérivées
- **Toute l'équipe** : rédaction du rapport L3 (sources et modèle de données, diagnostic, règles de nettoyage, transformations, limites et hypothèses), relecture croisée coordonnée par Yacine

## Sprint 4 : Analyse Q1 à Q4, modèle prédictif des retours et tableau de bord Excel (9-22 nov.)
**Objectif** : répondre aux quatre premières questions de recherche et expliquer le risque de retour. *(Analyse exploratoire, diagnostique et prédictive)*

- **Jean Robert** : Q1 côté boutiques (CA et marge en valeur par boutique, type et pays, productivité par m² et par employé) ; modèle prédictif du risque de retour (régression logistique, gradient boosting, AUC, facteurs expliqués avec SHAP)
- **Barnabé** : Q1 côté produits et temps (catégorie, sous-catégorie, marque, Pareto 80/20, saisonnalité et effet COVID-19, ANOVA des facteurs) ; tableau de bord Excel (Power Query, tableaux croisés dynamiques, segments et chronologie)
- **Lamoussa** : Q2 : volume, panier et marge en valeur, promo vs hors promo, par type de promotion, effet avant/pendant/après (uplift), tests statistiques
- **Mouncif** : Q3 (taux de retour standardisés par produit, catégorie, boutique et période, cas anormaux, relation prix et retours) et Q4 (corrélation remise et retour, contrôle des facteurs de confusion par régression)
- **Yacine (PO)** : valide les synthèses Q1 à Q4 et teste le tableau de bord Excel

## Sprint 5 : Prédiction, simulation et optimisation des promotions (23 nov.-6 déc.)
**Objectif** : passer de « que s'est-il passé » à « que faut-il faire » sur les promotions, et présenter les conclusions et recommandations (L4). *(Analyse prédictive et prescriptive)*

- **Barnabé** : Q5 descriptive (marge en valeur par tranche de remise, élasticité du volume, seuils où la marge baisse ou les retours augmentent) ; modèle de réponse aux promotions (volume et marge attendus selon la remise, la catégorie, la boutique et la période, uplift incrémental par type de promotion)
- **Lamoussa** : modèle de prévision des ventes hebdomadaires (référence naïve, SARIMA, gradient boosting avec variables calendrier et promotion), évaluation MAE / MAPE ; reproduction de l'optimisation avec le Solveur Excel et le Gestionnaire de scénarios
- **Jean Robert** : simulation what-if de 6 scénarios ou plus (taux de remise de 0 à 30 %, catégories ciblées, périodes) à partir des modèles de retour et de réponse ; optimisation en Python : maximiser la marge nette des retours sous contraintes (budget de remise, volume minimal, taux de retour maximal) et comparer à la politique actuelle
- **Mouncif** : tableau de bord Power BI alimenté par data/clean et data/outputs (relations, mesures DAX, pages vue d'ensemble, boutiques avec carte, produits, promotions, retours) et page what-if avec paramètre de taux de remise, validation des mesures contre Python
- **Yacine (PO)** : assemble le rapport d'analyse (chaque membre rédige sa section) et sélectionne les visualisations clés
- **Achraf (SM)** : coordonne la présentation PowerPoint des conclusions et la démonstration des tableaux de bord, organise la répétition chronométrée

## Sprint 6 : Plan promotionnel recommandé et rapport final (7-13 déc.)
**Objectif** : fiabiliser les recommandations, les transformer en plan d'action chiffré et remettre le rapport final (L5). *(Analyse prescriptive)*

- **Yacine (PO)** : formule et priorise les recommandations opérationnelles (impact, faisabilité)
- **Jean Robert** : analyse de sensibilité de la politique optimale (élasticité ±20 %, part de retours invendables de 0 à 100 %, budget de remise) ; intègre la rétroaction reçue lors de la présentation
- **Barnabé** : calendrier promotionnel recommandé (catégories, périodes, taux de remise) ; limites et pistes d'amélioration (données à collecter : motifs de retour, stocks, charges, clients)
- **Lamoussa** : prévision des ventes du trimestre suivant avec le plan recommandé vs le plan actuel ; compile les annexes (dictionnaire, code, captures des tableaux de bord)
- **Mouncif** : chiffrage des gains attendus et des risques du plan ; exécution complète de `run_pipeline.py` et archivage des notebooks exécutés ; relecture finale et mise en page
- **Achraf (SM)** : revue finale et rétrospective du projet

---

## Correspondance avec les types d'analyses
| Sprint | Type d'analyse |
|---|---|
| 0 | Cadrage et collecte |
| 1-3 | Préparation et descriptive |
| 4 | Exploratoire, diagnostique (Q1 à Q4) et prédictive (risque de retour) |
| 5 | Prédictive (ventes, réponse aux promotions) et prescriptive (simulation, optimisation) |
| 6 | Prescriptive (sensibilité, plan promotionnel) |

## Couverture des questions de recherche
| Question | Descriptive / diagnostique | Prédictive | Prescriptive |
|---|---|---|---|
| Q1 : facteurs de performance | CA et marge par boutique, produit, période, Pareto, ANOVA (US17) | Importance des variables du modèle de prévision (US23) | Boutiques et catégories à prioriser (US26) |
| Q2 : effet des promotions | Promo vs hors promo, uplift observé (US18) | Modèle de réponse aux promotions (US29) | Scénarios what-if (US30) |
| Q3 : patterns de retour | Taux de retour standardisés, cas anormaux (US19) | Modèle du risque de retour (US28) | Seuils de remise et produits à surveiller (US31, US32) |
| Q4 : remises et retours | Corrélation contrôlée (US21) | Effet de la remise dans le modèle de retour (US28) | Contrainte de taux de retour maximal dans l'optimisation (US31) |
| Q5 : stratégie de prix | Marge par tranche de remise, élasticité (US22) | Volume et marge attendus par remise (US29) | Remise optimale par catégorie et plan promotionnel (US31, US32) |

## Hypothèses et limites
- Les données fournies correspondent à FactSales de Contoso Retail DW (vérifié sur échantillon, IdVente = SalesKey). L'utilisation des tables de dimension Contoso reste soumise à la validation du professeur ; à défaut, les tâches liées à la géographie, aux catégories et aux types de promotion seront remplacées par des dimensions dérivées des transactions.
- Les dates de Contoso sont décalées de 12 ans par rapport à nos données : toutes les dates des dimensions sont réalignées (+12 ans).
- La rentabilité est analysée en **marge brute en valeur** : les charges d'exploitation ne sont pas disponibles, la rentabilité nette et le seuil de rentabilité sont hors périmètre.
- La démarque (retours invendables, vol) n'est pas mesurable avec les données disponibles. La part de retours invendables est traitée comme un **paramètre** dans la simulation et l'optimisation, et son effet est testé dans l'analyse de sensibilité.
- Les modèles prédictifs et prescriptifs reposent sur des relations observées en 2020-2021 : l'élasticité estimée est descriptive et non causale, ce qui justifie l'analyse de sensibilité avant toute recommandation.
- Les fichiers fournis ne contiennent que 6 trimestres : octobre à décembre 2020 et 2021 sont absents. La saisonnalité des Fêtes ne peut pas être observée, et la prévision portera sur les trimestres 1 à 3. Point signalé au professeur.
- Les données couvrent un échantillon de 56 boutiques : les conclusions portent sur ce périmètre et non sur l'ensemble de l'entreprise.
- 2020 et 2021 sont marquées par la COVID-19 : les tendances temporelles seront interprétées en tenant compte des périodes de confinement.
- La présentation UA1 est supposée coïncider avec la remise du 5 octobre.
