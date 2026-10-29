# Projet 4 · Ajout du 6 octobre 2026 : charges des boutiques

Ce dossier **ajoute** des fichiers au projet. Il ne remplace rien : les notebooks `00` à `05`, `src/` et la table des ventes ne changent pas, et il n'y a rien à relancer de ce côté.

## Contenu

```
Projet4_ajout_charges_2026-10-06/
├── LISEZ_MOI_charges.md                 ce fichier
├── Extraction_charges.py                NOUVEAU : extrait le plan stratégique de Contoso (inutile de le lancer, voir plus bas)
├── notebooks/1_preparation/
│   └── 05b_charges.ipynb                NOUVEAU : ETL, diagnostic et variables des charges, table commune ventes et charges
└── data/raw/contoso/
    ├── Plan/
    │   └── FactStrategyPlan.csv         NOUVEAU : ventes, coût des ventes et charges par boutique et par mois (355 236 lignes)
    └── Dim/
        ├── DimAccount.csv               NOUVEAU : les comptes (personnel, loyers, publicité...)
        ├── DimScenario.csv              NOUVEAU : réel, budget, prévision
        └── DimEntity.csv                NOUVEAU : lien entre une boutique et le plan
```

## Installation

1. Copier le contenu de ce dossier dans le dossier du projet, en gardant l'arborescence.
2. Il n'est pas nécessaire d'avoir la base Contoso ni de lancer `Extraction_charges.py` : le fichier extrait est fourni.
3. Avoir exécuté les notebooks `00` à `05` (mise à jour du 6 octobre), puis exécuter `05b_charges` avec « Run All ».

## Ce qu'il faut obtenir après exécution

| Contrôle | Valeur attendue |
|---|---|
| Lignes du plan | 355 236 |
| Validation de `05b_charges` | 11 contrôles réussis sur 11 |
| Ventes du plan et chiffre d'affaires de nos ventes | égaux au cent près, pour chaque boutique et chaque mois |
| Table commune `ventes_charges_boutique_mois` | 1 314 lignes × 37 colonnes |
| Résultat d'exploitation total (marge nette des retours − frais généraux − publicité) | 326 259 347 $ |

## Ce que le notebook produit

| Fichier | Contenu |
|---|---|
| `data/clean/fait_charges.parquet` | deuxième table de faits : une ligne par boutique, mois, scénario, compte et catégorie |
| `data/clean/dimensions/dim_compte.parquet` | 17 comptes, avec libellé français et famille |
| `data/clean/dimensions/dim_scenario.parquet` | réel, budget, prévision |
| `data/clean/agregats/resultat_boutique_mois.parquet` | compte de résultat du plan par boutique, mois et scénario |
| `data/clean/agregats/ventes_charges_boutique_mois.parquet` | table commune ventes et charges, par boutique et par mois |
| `reports/figures/05b_structure_resultat.png`, `05b_resultat_par_boutique.png` | deux graphiques |

## À retenir

- Le modèle a maintenant **deux tables de faits** (ventes et charges), reliées par leurs dimensions communes : boutique, date, catégorie de produit.
- Pour la rentabilité nette, on utilise **nos marges** (`marge_nette`) et on ne prend dans le plan que les frais généraux, la publicité et les impôts. Le coût des ventes du plan reprend la colonne `cout_total` de la source, que nous n'utilisons pas.
- **Vocabulaire** : `marge_nette` veut dire « nette des retours », avant toute charge. Le résultat après charges est `resultat_exploitation`, et après impôts `resultat_net`.
- **Premier constat** : avant publicité, tous les types de boutiques sont bénéficiaires. La publicité, identique pour chaque boutique, ramène les 54 magasins à l'équilibre (0,4 % du chiffre d'affaires) quand l'en-ligne et le revendeur restent à plus de 35 %.
- Le plan est généré, comme les ventes : le budget et la prévision sont calculés à partir du réel, et la publicité est répartie à parts presque égales entre les boutiques.
