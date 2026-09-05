# 🏢 Application de Gestion Immobilière pour SCI (Streamlit + Turso)

Application web moderne, intuitive et complète pour gérer administrativement, locativement et fiscalement votre Société Civile Immobilière (SCI), propulsée par **Streamlit** et une base de données **Turso** (libSQL / SQLite sur le cloud).

---

## 🌟 Fonctionnalités

1. **📊 Tableau de Bord & Indicateurs Clés** :
   - Chiffre d'affaires annuel perçu, encaissements du mois, loyers impayés ou en retard.
   - Taux d'occupation en temps réel.
   - Solde net de trésorerie (Recettes - Dépenses).
   - Graphiques mensuels dynamiques (Plotly).

2. **🏢 Gestion du Patrimoine & Amortissements IS** :
   - Fiches détaillées de chaque appartement, parking, local (adresse, surface, pièces, étage, quote-part copropriété, prix d'achat, loyers cibles).
   - **Calculateur d'Amortissement Comptable IS** : séparation du terrain (non amortissable, ~15-20%), calcul de la base amortissable du bâti (frais d'acquisition inclus) et du mobilier, annuités déductibles annuelles.
   - Suivi d'état : *Loué*, *Vacant*, *En travaux*.

3. **👥 Gestion des Locataires & Baux** :
   - Fiches locataires complètes (coordonnées, garant, dépôt de garantie).
   - Attribution et mise à jour automatique du statut des lots.
   - Procédure de départ avec clôture de bail et remise en vacance immédiate.

4. **💳 Loyers, Encaissements & Quittances de Loyer** :
   - Génération en 1 clic des échéances de loyers pour tous les locataires actifs.
   - Validation rapide des règlements (virement, chèque, prélèvement).
   - Génération et aperçu instantané de **quittances de loyer conformes à la loi de 1989**, avec bouton d'impression / téléchargement en PDF.

5. **🏛️ Charges Globales de la SCI** :
   - Ventilation des charges de structure : Assurance PNO, honoraires comptables, frais bancaires, taxe foncière, échéances de prêt (intérêts / capital).
   - Déductibilité fiscale au compte de résultat IS.

6. **🏠 Charges des Lots & Régularisation Annuelle** :
   - Suivi des charges spécifiques aux logements (appels de fonds syndic, eau, TEOM).
   - Distinction entre charges récupérables sur le locataire et non récupérables (propriétaire).
   - **Module de régularisation automatique** : calcul du solde différentiel entre les provisions perçues et les dépenses réelles récupérables.

7. **🤝 Comptes Courants d'Associés (CCA)** :
   - Suivi des apports personnels (apport bancaire, travaux avancés par les associés).
   - Suivi des remboursements effectués par la SCI vers les comptes personnels.
   - Calcul en temps réel du **solde récupérable en franchise totale d'impôt**.

8. **📑 Liasse Fiscale & Compte de Résultat IS (Cerfa 2065 / 2033)** :
   - Produits d'exploitation (loyers nets perçus).
   - Charges déductibles (assurances, entretien, comptabilité, charges d'immeuble).
   - **Dotations aux Amortissements (DAA)** déductibles (bâti + meubles).
   - Charges financières (intérêts d'emprunt).
   - **Calcul automatique de l'IS** : 15% jusqu'à 42 500 € de bénéfice, 25% au-delà.
   - Résultat net comptable de l'exercice.
   - Export CSV conforme pour l'expert-comptable.

8. **⚙️ Paramètres & Connexion Turso** :
   - Informations administratives de la SCI (SIREN, gérant, adresse, IBAN).
   - Diagnostic de connexion et switch transparent entre Turso Cloud et le mode local SQLite.

---

## 🚀 Démarrage Rapide

### 1. Installation des dépendances

```bash
pip install -r requirements.txt
```

### 2. Configuration de Turso (Optionnelle)

Si vous disposez d'une base de données sur [Turso](https://turso.tech) :
1. Créez un fichier `.streamlit/secrets.toml` (vous pouvez copier le modèle `.streamlit/secrets.toml.example`) :
```toml
TURSO_DATABASE_URL = "libsql://votre-base-nom.turso.io"
TURSO_AUTH_TOKEN = "votre_token_secret_turso"
```
*(Remarque : Si aucun token n'est renseigné, l'application démarre automatiquement en mode local SQLite sécurisé dans `data/sci_local.db`)*.

### 3. Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvrira directement dans votre navigateur web à l'adresse `http://localhost:8501`.

---

## ☁️ Déploiement sur Streamlit Community Cloud

1. Déposez ce projet sur votre dépôt GitHub.
2. Rendez-vous sur [share.streamlit.io](https://share.streamlit.io) et connectez votre dépôt.
3. Fichier principal : `app.py`.
4. Dans **Advanced Settings > Secrets**, collez vos variables Turso :
```toml
TURSO_DATABASE_URL = "libsql://votre-base-nom.turso.io"
TURSO_AUTH_TOKEN = "votre_token_secret_turso"
```
5. Cliquez sur **Deploy** ! Votre application est en ligne, accessible 24/7 sur mobile et ordinateur.
