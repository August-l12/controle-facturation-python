# Génère des données de facturation synthétiques (grille_tarifaire.csv, factures.csv) avec des erreurs volontaires.
import numpy as np, pandas as pd, json, re

rng = np.random.default_rng(42)
clients = ["Client Alpha", "Client Bravo", "Client Charlie", "Client Delta", "Client Echo"]
trajets = {"Paris-Lyon": 280, "Paris-Lille": 190, "Paris-Marseille": 420,
           "Paris-Bordeaux": 350, "Lyon-Marseille": 210, "Lille-Bruxelles": 260}
services = {"Standard": 1.0, "Express": 1.35}
stts = ["Trans Nord", "Express Sud", "Rapid Est"]

# Grille tarifaire contractuelle
grille = pd.DataFrame([
    {"client": c, "trajet": t, "service": s,
     "prix_grille": round(base * f * rng.uniform(0.95, 1.05))}
    for c in clients for t, base in trajets.items() for s, f in services.items()])

# Factures
n = 800
fact = pd.DataFrame({
    "facture_id": [f"FAC-2026-{i:06d}" for i in range(1, n + 1)],
    "date": pd.to_datetime("2026-09-01") + pd.to_timedelta(rng.integers(0, 30, n), unit="D"),
    "client": rng.choice(clients, n),
    "trajet": rng.choice(list(trajets), n),
    "service": rng.choice(list(services), n, p=[0.7, 0.3]),
    "stt": rng.choice(stts, n),
    "quantite": rng.integers(1, 5, n)})
fact = fact.merge(grille, on=["client", "trajet", "service"], how="left")
fact["prix_unitaire"] = fact["prix_grille"].astype(float)

# Petits arrondis normaux (ne sont PAS des anomalies)
idx = rng.choice(n, 40, replace=False)
fact.loc[idx, "prix_unitaire"] += rng.uniform(-0.4, 0.4, 40).round(2)
# Vraies erreurs de prix
idx_err = rng.choice(list(set(range(n)) - set(idx)), 56, replace=False)
fact.loc[idx_err, "prix_unitaire"] = (fact.loc[idx_err, "prix_grille"] *
                                       (1 + rng.choice([-0.2, -0.1, 0.08, 0.15, 0.3], 56))).round(2)
# Trajet absent de la grille
idx_abs = rng.choice(list(set(range(n)) - set(idx) - set(idx_err)), 8, replace=False)
fact.loc[idx_abs, "trajet"] = "Paris-Nantes"
fact.loc[idx_abs, "prix_grille"] = np.nan
fact.loc[idx_abs, "prix_unitaire"] = 300.0
fact = fact.drop(columns="prix_grille")
fact["montant_ht"] = (fact["quantite"] * fact["prix_unitaire"]).round(2)

# Références mal saisies
idx_ref = rng.choice(n, 120, replace=False)
def abime(ref, k):
    num = ref[-6:]
    return [ref.lower(), f"FAC {ref[4:8]} {num}", f"FAC{ref[4:8]}{num}", f" {ref} "][k % 4]
fact["facture_id"] = fact["facture_id"].astype(object)
for k, i in enumerate(idx_ref):
    fact.at[i, "facture_id"] = abime(fact.at[i, "facture_id"], k)

# Doublons (certains visibles tout de suite, d'autres seulement après nettoyage des références)
dup_idx = rng.choice(n, 12, replace=False)
dups = fact.loc[dup_idx].copy()
for k, i in enumerate(dups.index[6:]):
    dups.at[i, "facture_id"] = abime(str(dups.at[i, "facture_id"]).strip().upper().replace(" ", "-")[:15].ljust(15), k + 1)
fact = pd.concat([fact, dups]).sample(frac=1, random_state=1).reset_index(drop=True)

grille.to_csv("grille_tarifaire.csv", index=False)
fact.to_csv("factures.csv", index=False)

# Clé de contrôle (pour vérifier TES résultats à la fin, pas avant)
def _norm(r): return re.sub(r"[^0-9]", "", str(r))[-10:]
_f = fact.copy(); _f["ref"] = _f["facture_id"].map(_norm)
_dupes = int(_f.duplicated(subset=["ref"]).sum())
_u = _f.drop_duplicates(subset=["ref"]).merge(grille, on=["client", "trajet", "service"], how="left")
_u["ecart"] = (_u["prix_unitaire"] - _u["prix_grille"]) * _u["quantite"]
_abs = int(_u["prix_grille"].isna().sum())
_an = _u[(_u["prix_grille"].notna()) & ((_u["prix_unitaire"] - _u["prix_grille"]).abs() > 1.0)]
json.dump({"lignes_brutes": int(len(fact)), "doublons": _dupes, "absents_de_la_grille": _abs,
           "anomalies_de_prix": int(len(_an)),
           "surfacturation_eur": round(float(_an.loc[_an.ecart > 0, "ecart"].sum()), 2),
           "sous_facturation_eur": round(float(_an.loc[_an.ecart < 0, "ecart"].sum()), 2)},
          open("cle_de_controle.json", "w"), indent=1)
print("Fichiers créés :", len(fact), "lignes de factures,", len(grille), "lignes de grille.")
