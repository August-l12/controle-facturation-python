import pandas  as pd
import numpy as np
import re

TOLERANCE_EUR = 1.0   # écart unitaire en dessous duquel on considère que ce sont des arrondis

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


#lire le fichier csv factures.csv:
factures= pd.read_csv("factures.csv")

#lire le fichier csv grille_tarifaire.csv:
grille_tarifaire = pd.read_csv("grille_tarifaire.csv")

def nettoyer_ref(valeur) -> str:
    """Normalise une référence de facture au format FAC-AAAA-NNNNNN (regex : on garde les chiffres)."""
    chiffres = re.sub(r"[^0-9]", "", str(valeur))
    return f"FAC-{chiffres[:4]}-{chiffres[4:]}"

def nettoyer(factures):
    """Normalise les références de factures puis supprime les doublons."""
    factures = factures.copy()
    factures["ref"] = factures["facture_id"].map(nettoyer_ref)
    bonne_forme_apres = factures["ref"].str.fullmatch(r"FAC-\d{4}-\d{6}")
    assert bonne_forme_apres.all(), "Des références ne sont pas au bon format après nettoyage"

    nb_doublons = factures.duplicated(subset="ref").sum()
    print(f"Nombre de doublons dans les références de factures: {nb_doublons}")
    print(factures[factures.duplicated("ref", keep=False)].sort_values("ref").head(6))
    propres = factures.drop_duplicates(subset="ref", keep="first").drop(columns="facture_id")
    print(propres.shape)
    return propres, nb_doublons

#note: Les doublons n’étaient visibles qu’après avoir normalisé les références.

propres, nb_doublons = nettoyer(factures)

#ici on va faire un merge entre les factures et la grille tarifaire pour voir quelles factures sont hors grille:
rapproche= pd.merge(propres, grille_tarifaire, on=["client", "trajet", "service"], how="left", indicator=True)
print(rapproche["_merge"].value_counts())

#on isole les factures sans prix:
hors_grille= rapproche[rapproche["_merge"]=="left_only"].drop(columns=["_merge", "prix_grille"])
print(hors_grille[["ref", "client", "trajet"]])

#d'abord on garde les factures qui ont un prix: 
avec_prix= rapproche[rapproche["_merge"]=="both"].copy()
print(avec_prix.shape)

assert len(avec_prix) + len(hors_grille) == len(propres), "Le rapprochement perd ou duplique des factures"

#calculer les écarts et repérer les anomalies:
avec_prix["ecart_unitaire"] = (avec_prix["prix_unitaire"] - avec_prix["prix_grille"]).round(2)
avec_prix["ecart_total"] = (avec_prix["ecart_unitaire"] * avec_prix["quantite"]).round(2)
print(avec_prix[["ref", "prix_unitaire", "prix_grille", "ecart_unitaire", "ecart_total"]].head(10))

#on classe chaque ligne selon l'écart unitaire par rapport au prix de grille
avec_prix["type_anomalie"] = np.select(
    [avec_prix["ecart_unitaire"] > TOLERANCE_EUR, avec_prix["ecart_unitaire"] < -TOLERANCE_EUR],
    ["surfacturation", "sous-facturation"],
    default="conforme",
)
print(avec_prix["type_anomalie"].value_counts())

#on isole les anomalies: 
anomalies= avec_prix[avec_prix["type_anomalie"]!= "conforme"]
print(len(anomalies))

#on chiffre les montants: 
total_surfacture= anomalies.loc[anomalies["type_anomalie"]=="surfacturation", "ecart_total"].sum()
print(total_surfacture)

total_sousfacture=anomalies.loc[anomalies["type_anomalie"]=="sous-facturation", "ecart_total"].sum()
print(total_sousfacture)

#on calcule les avoirs:
avoirs= anomalies[anomalies["type_anomalie"]== "surfacturation"]
avoirs= avoirs[["ref", "client", "trajet", "ecart_total"]]
avoirs = avoirs.rename(columns={"ecart_total": "montant_avoirs_propose"})
print(len(avoirs))
print(avoirs.head())

#on calcule les anomalies par groupe: 
print(anomalies["client"].value_counts())
print(anomalies["stt"].value_counts())

#on additionne les montants par groupe:
print(anomalies.groupby("stt")["ecart_total"].sum())

#on additionne les montants par client:
print(anomalies.groupby("client")["ecart_total"].sum())

#rapport excel: 

#on construit resume: 
resume= pd.DataFrame({
    "Indicateur": ["Lignes de factures reçues", "Doublons supprimés", "Factures analysées",
                   "Factures hors grille (à traiter à la main)", f"Anomalies de prix (écart > {TOLERANCE_EUR} EUR)",
                   "Montant surfacturé (EUR)", "Montant sous-facturé (EUR)", "Avoirs proposés (nombre)"],
    "Valeur": pd.Series([len(factures), nb_doublons, len(propres), len(hors_grille), len(anomalies),
               round(total_surfacture, 2), round(total_sousfacture, 2), len(avoirs)], dtype=object),
})
with pd.ExcelWriter("rapport_controle_facturation.xlsx") as writer:
    resume.to_excel(writer, sheet_name="Resume", index=False)
    anomalies.to_excel(writer, sheet_name="Anomalies", index=False)
    avoirs.to_excel(writer, sheet_name="Avoirs proposes", index=False)
    hors_grille.to_excel(writer, sheet_name="Hors grille", index=False)

