# Contrôle de facturation : détection d'écarts de prix (Python)

Script Python qui automatise le contrôle de factures par rapport à une grille tarifaire contractuelle : nettoyage, rapprochement, détection d'écarts, propositions d'avoirs et rapport Excel.

> Les données sont entièrement synthétiques, générées par `generer_donnees.py`, avec des erreurs volontaires. Aucune donnée réelle.

> Projet réalisé avec l'aide d'un assistant IA (génération des données synthétiques et accompagnement pas à pas). L'analyse a été écrite et vérifiée par moi.

## Problème
Des factures clients contiennent des erreurs : références saisies de plusieurs façons, doublons, prix différents de la grille, trajets absents de la grille.

## Méthode
1. **Nettoyage des références** avec une regex (`FAC-AAAA-NNNNNN`).
2. **Suppression des doublons** sur la référence nettoyée.
3. **Rapprochement** de chaque facture avec la grille (Pandas `merge`, clé : client, trajet, service).
4. **Calcul des écarts** avec NumPy (`np.select`), avec une tolérance de 1 EUR pour ignorer les arrondis.
5. **Propositions d'avoirs** pour les surfacturations.
6. **Rapport Excel** : résumé, anomalies, avoirs proposés, factures hors grille.

## Résultats (sur le jeu de données fourni)
- 812 lignes reçues, 12 doublons supprimés, 800 factures analysées
- 56 anomalies de prix : 33 surfacturations (3 921,41 EUR) et 23 sous-facturations (2 363,90 EUR)
- 8 factures hors grille à traiter manuellement
- 33 avoirs proposés
- Le sous-traitant Trans Nord concentre le plus d'anomalies (23 sur 56)

## Utilisation
```bash
pip install pandas numpy openpyxl
python generer_donnees.py        # crée factures.csv et grille_tarifaire.csv
python controle_facturation.py   # crée le rapport Excel
```

## Fichiers
- `controle_facturation.py` : le contrôle (nettoyage, rapprochement, écarts, avoirs, rapport)
- `generer_donnees.py` : génération des données synthétiques
- `factures.csv`, `grille_tarifaire.csv` : données d'entrée
- `rapport_controle_facturation.xlsx` : exemple de rapport produit

## Limites et suite
- Une seule règle de contrôle (prix unitaire contre grille). Pas de remises ni de dates de validité des tarifs.
- Le total net par client ou par sous-traitant mélange surfacturations et sous-facturations : elles se compensent et peuvent masquer des erreurs. Il faudrait aussi les suivre séparément.
- Suite possible : contrôle des coûts sous-traitants (STT) contre un tarif convenu, tests unitaires.
