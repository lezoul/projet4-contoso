"""
Application Streamlit du simulateur de scénarios (prescriptif, projet 4).

L'application ne fait aucun calcul elle-même : elle lit les données préparées, transforme
chaque curseur en une valeur de `reglages(...)` et appelle le moteur `src/simulateur.py`,
le même que le notebook 14.

Prérequis : avoir exécuté les notebooks 00 à 05c (données) et le notebook 14
(base 2022 enregistrée dans data/outputs/scenarios/base_canal_2022.parquet).
Le notebook 10 est facultatif : il ajoute la base « Random Forest ».

Lancement, depuis la racine du projet :
    streamlit run dashboards/app_simulateur.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:                    # streamlit lance le fichier depuis dashboards/ : on ajoute la racine
    sys.path.insert(0, str(ROOT))

import altair as alt
import pandas as pd
import streamlit as st

from src import config, simulateur
from src.simulateur import reglages

EXERCICE = config.EXERCICE                       # 2021 : dernier exercice connu
ANNEE = EXERCICE + 1                             # 2022 : année simulée
ORDRE_CANAUX = ["En ligne", "Revendeur", "Magasins"]

# Scénarios du notebook 14 : ils pré-remplissent les curseurs
SCENARIOS = {
    "Au fil de l'eau": {},
    "Prudent": dict(frais_maitrisables="gel", remises_magasin="sans le 20 %"),
    "Charges": dict(frais_maitrisables="niveau 2019", baisse_publicite_magasins=0.10, remises_magasin="supprimées"),
    "Assortiment": dict(lancements=552, nouveautes_en_magasin=1.0),
    "Complet": dict(lancements=552, nouveautes_en_magasin=1.0, frais_maitrisables="niveau 2019",
                    baisse_publicite_magasins=0.10, remises_magasin="supprimées"),
}
CHOIX_FRAIS = ["fil de l'eau", "gel", "niveau 2020", "niveau 2019", "baisse en %"]
CHOIX_REMISES = ["maintenues", "sans le 20 %", "supprimées"]


# ---------------------------------------------------------------------------
# Mise en forme
# ---------------------------------------------------------------------------
def m_dollars(valeur, decimales=1, signe=False):
    """Montant en millions de dollars, virgule française : 12,3 M$."""
    texte = f"{valeur / 1e6:{'+' if signe else ''},.{decimales}f}".replace(",", " ").replace(".", ",")
    return f"{texte} M$"


def md(texte):
    """Texte affiché en Markdown : le $ y ouvre une formule mathématique, on l'échappe."""
    return texte.replace("$", "\\$")


def pct(valeur, decimales=1, signe=False):
    texte = f"{valeur * 100:{'+' if signe else ''}.{decimales}f}".replace(".", ",")
    return f"{texte} %"


# ---------------------------------------------------------------------------
# Données : lues une seule fois, puis gardées en cache
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Préparation des données de l'exercice…")
def charger():
    chemins = {
        "commun": config.AGREGATS / "ventes_charges_boutique_mois.parquet",
        "charges": config.CLEAN / "fait_charges.parquet",
        "ventes": config.CLEAN / "fait_ventes_variables.parquet",
        "dim_produit": config.CLEAN_DIMENSIONS / "dim_produit.parquet",
        "dim_boutique": config.CLEAN_DIMENSIONS / "dim_boutique.parquet",
        "base": config.SCENARIOS / f"base_canal_{ANNEE}.parquet",
    }
    manquants = [str(c.relative_to(config.ROOT)) for c in chemins.values() if not c.exists()]
    if manquants:
        return None, manquants
    ventes = pd.read_parquet(chemins["ventes"], columns=["annee", "id_boutique", "id_produit", "type_boutique", "ca_net",
                                                         "taux_remise_annonce", "montant_remise", "marge_perdue_retours"])
    donnees = simulateur.preparer(pd.read_parquet(chemins["commun"]), pd.read_parquet(chemins["charges"]), ventes,
                                  pd.read_parquet(chemins["dim_produit"]), pd.read_parquet(chemins["dim_boutique"]), EXERCICE)

    # Bases possibles : le CA de chaque boutique en 2022 si rien ne change
    base_2021 = simulateur.base_reconduite(donnees)
    bases = {"Lissage saisonnier (notebook 14)": simulateur.base_par_canal(donnees, pd.read_parquet(chemins["base"]).sum()),
             f"{EXERCICE} reconduit": base_2021}
    chemin_rf = config.PREDICTIONS / "previsions_ventes.parquet"
    if chemin_rf.exists():
        rf = pd.read_parquet(chemin_rf)
        rf = rf[rf.jeu.str.startswith("Prévision")]
        bases["Random Forest (notebook 10)"] = (rf.groupby("id_boutique").prevision.sum()
                                                .reindex(donnees["boutiques"].id_boutique).fillna(base_2021).rename("ca_base"))
    return {"donnees": donnees, "bases": bases}, []


def jouer(donnees, base, reglages_):
    """Simulation + chiffres clés."""
    r = simulateur.simuler(donnees, base, reglages_)
    mag = r[r.type == "Magasins"].resultat_exploitation_simule
    return r, {"ca": r.ca_net_simule.sum(), "resultat": simulateur.resultat_entreprise(r),
               "magasins": mag.sum(), "deficitaires": int((mag < 0).sum()), "nb_magasins": len(mag)}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Simulateur Contoso", page_icon="📊", layout="wide")
st.title(f"Simulateur de scénarios {ANNEE}")
st.caption(f"Contoso · compte de résultat recalculé boutique par boutique à partir de l'exercice {EXERCICE}. "
           "Chaque levier reprend un mécanisme mesuré dans les notebooks d'analyse (06, 06b, 07, 08, 09).")

paquet, manquants = charger()
if paquet is None:
    st.error("Fichiers introuvables. Exécuter d'abord les notebooks 00 à 05c, puis le notebook 14 :")
    st.code("\n".join(manquants))
    st.stop()
donnees, BASES = paquet["donnees"], paquet["bases"]

# --- Barre latérale : base, scénario de départ, hypothèses et leviers
with st.sidebar:
    st.header("1. Point de départ")
    nom_base = st.selectbox("Base de chiffre d'affaires", list(BASES), help="Le CA de chaque boutique si rien ne change.")
    erreur_base = st.slider("Décalage de la base", -20, 20, 0, step=1, format="%d %%",
                            help="Pour tester une prévision trop haute ou trop basse.") / 100
    hausse = st.radio("Charges fixes", ["prolongée", "gelée"], horizontal=True,
                      help=f"« prolongée » : les hausses {EXERCICE - 1} → {EXERCICE} continuent.")

    st.header("2. Décisions")
    preset = st.selectbox("Pré-remplir avec un scénario", list(SCENARIOS), index=0)
    d = reglages(**SCENARIOS[preset])
    k = lambda nom: f"{nom}|{preset}"            # une clé par scénario : changer de scénario remet les curseurs

    with st.expander("Assortiment", expanded=True):
        lancements = st.slider("Nouveautés lancées dans l'année", 0, 800,
                               donnees["lances"] if d["lancements"] is None else d["lancements"], step=8, key=k("lanc"),
                               help=f"{donnees['lances']} en {EXERCICE}, 552 en 2019.")
        nouveautes_mag = st.slider("Écart des nouveautés en magasin comblé", 0, 100, int(d["nouveautes_en_magasin"] * 100),
                                   step=5, format="%d %%", key=k("nouv")) / 100
    with st.expander("Charges", expanded=True):
        choix = d["frais_maitrisables"] if isinstance(d["frais_maitrisables"], str) else "baisse en %"
        frais = st.selectbox("Personnel, administration, informatique (magasins)", CHOIX_FRAIS,
                             index=CHOIX_FRAIS.index(choix), key=k("frais"))
        if frais == "baisse en %":
            frais = st.slider("Baisse par rapport au fil de l'eau", 0, 30, 10, format="%d %%", key=k("frais_pct")) / 100
        regroupement = st.slider("Regroupement par pays : économie sur administration et informatique", 0, 40,
                                 int(d["regroupement_pays"] * 100), step=5, format="%d %%", key=k("pays")) / 100
    with st.expander("Publicité des magasins"):
        pub = st.slider("Baisse du budget", 0, 50, int(d["baisse_publicite_magasins"] * 100), step=5,
                        format="%d %%", key=k("pub")) / 100
        reaction = st.slider("Réaction des ventes des magasins (hypothèse)", -10.0, 0.0, 0.0, step=0.5,
                             format="%.1f %%", key=k("reac")) / 100
    with st.expander("Remises et retours"):
        remises = st.selectbox("Remises en magasin", CHOIX_REMISES, index=CHOIX_REMISES.index(d["remises_magasin"]), key=k("rem"))
        plafond = st.checkbox("Plafonner la remise à 10 % en ligne et chez le revendeur",
                              d["plafond_remise_10_hors_magasin"], key=k("plaf"))
        retours = st.slider("Retours évités", 0, 100, int(d["baisse_retours"] * 100), step=5, format="%d %%", key=k("ret")) / 100

    st.header("3. Hypothèses incertaines")
    efficacite = st.slider("CA d'une nouveauté en plus, rapporté à " + str(EXERCICE), 50, 150, 100, step=5, format="%d %%",
                           help=f"100 % = {m_dollars(donnees['ca_par_nouveaute'], 3)} par nouveauté.") / 100
    cout = st.number_input("Coût de lancement d'une nouveauté ($)", 0, 400_000, 0, step=10_000,
                           help="Absent des données : le seuil de rentabilité est affiché plus bas.")

hypotheses = dict(erreur_base=erreur_base, hausse_charges=hausse)
choisis = reglages(**hypotheses, lancements=lancements, nouveautes_en_magasin=nouveautes_mag, frais_maitrisables=frais,
                   regroupement_pays=regroupement, baisse_publicite_magasins=pub, reaction_ventes_publicite=reaction,
                   remises_magasin=remises, plafond_remise_10_hors_magasin=plafond, baisse_retours=retours,
                   efficacite_nouveaute=efficacite, cout_par_lancement=cout)
base = BASES[nom_base]
resultat, chiffres = jouer(donnees, base, choisis)
_, fil = jouer(donnees, base, reglages(**hypotheses))
reel = donnees["boutiques"]

# --- Chiffres clés
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Résultat d'exploitation {ANNEE}", m_dollars(chiffres["resultat"]),
          f"{m_dollars(chiffres['resultat'] - fil['resultat'], signe=True)} vs fil de l'eau")
c2.metric(f"Chiffre d'affaires net {ANNEE}", m_dollars(chiffres["ca"]),
          f"{pct(chiffres['ca'] / reel.ca_net.sum() - 1, signe=True)} vs {EXERCICE}")
c3.metric("Résultat des magasins", m_dollars(chiffres["magasins"]),
          f"{m_dollars(chiffres['magasins'] - fil['magasins'], signe=True)} vs fil de l'eau")
c4.metric("Magasins déficitaires", f"{chiffres['deficitaires']} sur {chiffres['nb_magasins']}",
          f"{chiffres['deficitaires'] - fil['deficitaires']:+d} vs fil de l'eau", delta_color="inverse")
st.caption(md(f"Au fil de l'eau sur cette base : {m_dollars(fil['resultat'])}. "
              f"Réel {EXERCICE} : {m_dollars(reel.resultat_exploitation.sum())}."))

onglet_sim, onglet_scen, onglet_rob, onglet_bout = st.tabs(
    ["D'où vient le gain", "Comparer les scénarios", "Robustesse", "Boutiques"])

# --- 1. Apport de chaque levier
with onglet_sim:
    apports = resultat[[c for c in resultat.columns if c.startswith("apport : ")]].sum()
    apports.index = apports.index.str.replace("apport : ", "", regex=False).str.capitalize()
    apports = pd.concat([apports, pd.Series({"Coût des lancements": -resultat.attrs.get("cout_lancements", 0.0)})])
    apports = apports[apports.abs() > 1e3]
    if apports.empty:
        st.info("Aucun levier activé : c'est le scénario au fil de l'eau. Choisir des décisions dans la barre latérale.")
    else:
        t = apports.rename("gain").rename_axis("levier").reset_index().assign(M=lambda x: x.gain / 1e6)
        t["texte"] = t.gain.map(lambda v: m_dollars(v, signe=True))
        barres = alt.Chart(t).mark_bar().encode(
            x=alt.X("M:Q", title="Gain par rapport au fil de l'eau (M$)"),
            y=alt.Y("levier:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
            color=alt.condition("datum.M >= 0", alt.value("#2E7D5B"), alt.value("#C0392B")),
            tooltip=["levier", "texte"])
        st.altair_chart(barres + barres.mark_text(align="left", dx=4).encode(text="texte"), width="stretch")
        st.caption("Chaque barre est l'apport d'un levier au résultat d'exploitation. "
                   "La somme est très proche du gain total : les leviers se recoupent peu.")

    resume = simulateur.resumer(resultat).reindex(ORDRE_CANAUX + ["Entreprise"])
    resume_fil = simulateur.resumer(jouer(donnees, base, reglages(**hypotheses))[0]).reindex(ORDRE_CANAUX + ["Entreprise"])
    tableau = pd.DataFrame({
        "CA net": resume.ca_net.map(m_dollars),
        "Résultat d'exploitation": resume.resultat.map(m_dollars),
        "Gain vs fil de l'eau": (resume.resultat - resume_fil.resultat).map(lambda v: m_dollars(v, signe=True)),
        "Boutiques": resume.boutiques.astype(int),
        "Déficitaires": resume.deficitaires.astype(int),
    })
    st.subheader("Par canal")
    st.dataframe(tableau.rename_axis("Canal"), width="stretch")

    if lancements > donnees["lances"]:
        gain_unitaire = resultat["apport : lancements"].sum() / (lancements - donnees["lances"])
        st.info(md(f"Seuil de rentabilité d'un lancement : une nouveauté en plus rapporte {gain_unitaire:,.0f} $ ".replace(",", " ")
                + "au résultat. Elle reste rentable tant que son coût de lancement est inférieur à ce montant."))

# --- 2. Les scénarios du notebook 14 sur la base choisie
with onglet_scen:
    lignes = []
    for nom, kw in SCENARIOS.items():
        _, c = jouer(donnees, base, reglages(**hypotheses, **kw))
        lignes.append({"Scénario": nom, "Résultat": c["resultat"], "Gain": c["resultat"] - fil["resultat"],
                       "Magasins déficitaires": c["deficitaires"]})
    lignes.append({"Scénario": "Vos réglages", "Résultat": chiffres["resultat"], "Gain": chiffres["resultat"] - fil["resultat"],
                   "Magasins déficitaires": chiffres["deficitaires"]})
    comp = pd.DataFrame(lignes)
    graphe = alt.Chart(comp.assign(M=comp.Résultat / 1e6, texte=comp.Résultat.map(m_dollars))).mark_bar().encode(
        x=alt.X("Scénario:N", sort=None, title=None), y=alt.Y("M:Q", title=f"Résultat d'exploitation {ANNEE} (M$)"),
        color=alt.condition(alt.datum.Scénario == "Vos réglages", alt.value("#E67E22"), alt.value("#2C6E9B")),
        tooltip=["Scénario", "texte"])
    st.altair_chart(graphe + graphe.mark_text(dy=-8).encode(text="texte"), width="stretch")
    st.dataframe(comp.assign(Résultat=comp.Résultat.map(m_dollars), Gain=comp.Gain.map(lambda v: m_dollars(v, signe=True)))
                 .set_index("Scénario"), width="stretch")
    with st.expander("Contenu des scénarios"):
        for nom, kw in SCENARIOS.items():
            st.markdown(f"**{nom}** : " + (", ".join(f"`{a} = {b}`" for a, b in kw.items()) or "aucune décision"))

# --- 3. Robustesse : le même jeu de décisions sur toutes les bases
with onglet_rob:
    st.markdown("Le gain d'une décision dépend-il de la prévision ? On rejoue **vos réglages** sur chaque base, "
                "ainsi que sur la base choisie décalée de ±10 %.")
    variantes = {nom: (b, 0.0) for nom, b in BASES.items()}
    variantes[f"{nom_base} −10 %"] = (base, -0.10)
    variantes[f"{nom_base} +10 %"] = (base, 0.10)
    lignes = []
    for nom, (b, decalage) in variantes.items():
        h = dict(hypotheses, erreur_base=decalage)
        _, avec = jouer(donnees, b, {**choisis, **h})
        _, sans = jouer(donnees, b, reglages(**h))
        lignes.append({"Base": nom, "Fil de l'eau": sans["resultat"], "Vos réglages": avec["resultat"],
                       "Gain": avec["resultat"] - sans["resultat"], "Magasins déficitaires": avec["deficitaires"]})
    rob = pd.DataFrame(lignes).set_index("Base")
    st.dataframe(rob.assign(**{c: rob[c].map(m_dollars) for c in ["Fil de l'eau", "Vos réglages"]},
                            Gain=rob.Gain.map(lambda v: m_dollars(v, signe=True))), width="stretch")
    st.caption(md(f"Gain de vos réglages selon la base : de {m_dollars(rob.Gain.min())} à {m_dollars(rob.Gain.max())}. "
                  "Le point d'arrivée bouge avec la base ; le gain des décisions beaucoup moins."))

# --- 4. Détail par boutique
with onglet_bout:
    canaux = st.multiselect("Canaux", ORDRE_CANAUX, default=["Magasins"])
    detail = resultat[resultat.type.isin(canaux)][["nom_boutique", "type", "pays", "ca_net", "resultat_exploitation",
                                                     "ca_net_simule", "resultat_exploitation_simule"]].rename(columns={
        "nom_boutique": "Boutique", "type": "Canal", "pays": "Pays", "ca_net": f"CA {EXERCICE}",
        "resultat_exploitation": f"Résultat {EXERCICE}", "ca_net_simule": f"CA {ANNEE}",
        "resultat_exploitation_simule": f"Résultat {ANNEE}"}).sort_values(f"Résultat {ANNEE}")
    st.dataframe(detail, width="stretch", hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.0f $") for c in detail.columns[3:]})
    st.download_button("Télécharger le détail (CSV)", resultat.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"simulation_{ANNEE}.csv", mime="text/csv")
