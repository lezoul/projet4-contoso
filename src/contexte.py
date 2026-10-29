"""
contexte.py : collecte des données de contexte, par pays et par jour.

Produit dans data/raw/contexte/ :
  - jours_feries.csv    : jours fériés des pays de nos boutiques, pour toutes les années étudiées
                          (config.ANNEES_ETUDE : 2019 à 2021), générés par la bibliothèque Python "holidays"
  - severite_covid.csv  : indice de sévérité des mesures COVID-19 (0 à 100), par pays et par jour
                          (extrait du jeu de données OxCGRT de l'Université d'Oxford).
                          L'indice n'existe qu'à partir du 1er janvier 2020 : le fichier ne contient donc
                          aucune ligne pour 2019. Ce vide est traité dans 02_flocon (aucune mesure avant 2020).

Avant de lancer ce script :
  1. pip install holidays
  2. Télécharger le fichier national "compact" d'OxCGRT (CSV) depuis
     https://github.com/OxCGRT/covid-policy-dataset/tree/main/data
     et le déposer tel quel dans data/raw/contexte/ (son nom doit commencer par "OxCGRT").
     Sans ce fichier, le script produit quand même les jours fériés.

Lancement, depuis le dossier Projet ADD :  python -m src.contexte
"""
import pandas as pd

from src import config, etl

config.creer_dossiers()
annees = config.ANNEES_ETUDE

# ---------------------------------------------------------------------------
# 1. Pays des boutiques réellement présentes dans nos ventes
# ---------------------------------------------------------------------------
boutiques, _ = etl.lire_dimension("DimStore")
geographie, _ = etl.lire_dimension("DimGeography")
ventes, _ = etl.charger_ventes()

# Boutiques utilisées par nos ventes, rattachées à leur géographie
utilisees = boutiques[boutiques.StoreKey.isin(ventes[config.COL_BOUTIQUE])]
utilisees = utilisees.merge(geographie, on="GeographyKey", how="left")

# str.strip() retire les espaces en trop : dans Contoso, "Germany" existe aussi
# sous la forme "Germany " (avec une espace finale), ce qui créerait deux pays différents.
pays_presents = sorted(utilisees.RegionCountryName.str.strip().dropna().unique())

# Tout pays absent de config.PAYS_ISO doit y être ajouté (sinon pas de contexte pour lui)
inconnus = [p for p in pays_presents if p not in config.PAYS_ISO]
if inconnus:
    print("Pays sans code ISO dans config.PAYS_ISO (à ajouter) :", inconnus)
pays_presents = [p for p in pays_presents if p in config.PAYS_ISO]
print(f"{len(pays_presents)} pays :", ", ".join(pays_presents))

# ---------------------------------------------------------------------------
# 2. Jours fériés → data/raw/contexte/jours_feries.csv
# ---------------------------------------------------------------------------
import holidays

# Certains pays (la Suède) comptent chaque dimanche comme un jour férié.
# Un dimanche ordinaire n'est pas un jour férié au sens de notre analyse : on l'écarte.
DIMANCHES = {"Söndag", "Sunday"}

lignes = []
for pays in pays_presents:
    iso2, _iso3 = config.PAYS_ISO[pays]
    # Jours fériés NATIONAUX du pays pour nos années.
    # Les jours fériés régionaux (Länder allemands, cantons suisses...) ne sont pas inclus.
    for jour, nom in sorted(holidays.country_holidays(iso2, years=annees).items()):
        # Quand deux fêtes tombent le même jour, leurs noms sont séparés par "; ".
        # On retire la mention "dimanche" et on garde le reste.
        noms = [n for n in nom.split("; ") if n not in DIMANCHES]
        if noms:
            lignes.append({"pays": pays, "code_iso2": iso2, "date": jour, "nom_ferie": "; ".join(noms)})

feries = pd.DataFrame(lignes)
chemin_feries = config.CONTEXTE / config.FICHIER_JOURS_FERIES
feries.to_csv(chemin_feries, index=False, encoding="utf-8-sig")
print(f"\nJours fériés : {len(feries)} lignes -> {chemin_feries}")
print(feries.groupby("pays").size().to_string())

# ---------------------------------------------------------------------------
# 3. Sévérité des mesures COVID-19 → data/raw/contexte/severite_covid.csv
# ---------------------------------------------------------------------------
sources = sorted(config.CONTEXTE.glob(config.MOTIF_OXCGRT))
if not sources:
    print("\nFichier OxCGRT absent de", config.CONTEXTE)
    print("Téléchargez le fichier national compact (CSV) puis relancez ce script.")
else:
    source = sources[0]
    brut = pd.read_csv(source, low_memory=False)

    # Ne garder que le niveau national (le fichier peut aussi contenir des régions)
    if "Jurisdiction" in brut.columns:
        brut = brut[brut.Jurisdiction == "NAT_TOTAL"]

    # Colonne de l'indice de sévérité : son nom exact varie selon la version du fichier
    # (StringencyIndex_Average, StringencyIndex...). On prend la première qui commence ainsi,
    # en préférant la moyenne si elle existe.
    candidates = [c for c in brut.columns if c.startswith("StringencyIndex")]
    col_indice = next((c for c in candidates if c.endswith("_Average")), candidates[0])

    # Correspondance code ISO à 3 lettres -> nom du pays dans Contoso
    iso3_vers_pays = {config.PAYS_ISO[p][1]: p for p in pays_presents}

    covid = brut[brut.CountryCode.isin(iso3_vers_pays)].copy()
    covid["pays"] = covid.CountryCode.map(iso3_vers_pays)
    # Les dates sont écrites 20200325 (année, mois, jour collés)
    covid["date"] = pd.to_datetime(covid.Date.astype(str), format="%Y%m%d")
    covid = covid[(covid.date >= config.DATE_DEBUT) & (covid.date <= config.DATE_FIN)]
    covid = covid.rename(columns={col_indice: "severite_covid"})[["pays", "date", "severite_covid"]]
    covid = covid.sort_values(["pays", "date"])

    chemin_covid = config.CONTEXTE / config.FICHIER_SEVERITE_COVID
    covid.to_csv(chemin_covid, index=False, encoding="utf-8-sig")
    print(f"\nSévérité COVID-19 ({col_indice}, source {source.name}) : {len(covid)} lignes -> {chemin_covid}")
    manquants = sorted(set(pays_presents) - set(covid.pays))
    if manquants:
        print("Pays sans données COVID-19 :", manquants)
