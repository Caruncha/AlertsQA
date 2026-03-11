# 🚦 GTFS-RT Alerts Quality Assurance Dashboard

Outil de validation et d'analyse synthétique pour les flux GTFS-Realtime Alerts. Conçu pour les équipes de développement et de QA afin de valider la conformité des données et la cohérence avec le GTFS statique.

## ✨ Fonctionnalités

- **Acquisition API** : Supporte JSON et Protobuf (Standard, STM, Exo/Azure).
- **Synthèse Qualité** : KPIs automatiques sur les causes, effets et entités les plus impactées.
- **Tableau de Bord Global** : Liste triable et filtrable de toutes les alertes actives.
- **Deep Dive & Inspection** : Analyse détaillée des textes (traductions fr/en), des périodes et des impacts.
- **Validation GTFS Statique** : Détection automatique des IDs de lignes (Route) ou d'arrêts (Stop) inexistants.
- **Conformité Norme** : Vérification des champs obligatoires (header_text).

## 🚀 Installation & Déploiement

### Option 1 : Docker (Recommandé)

1. Clonez le dépôt.
2. Créez votre fichier `.env` à partir du modèle : `cp .env.example .env` (et remplissez vos clés).
3. Lancez le projet :
   ```bash
   docker-compose up -d --build
   ```
4. Accédez au dashboard sur `http://localhost:8501`.

### Option 2 : Installation Locale (Python)

1. Créez un environnement virtuel : `python -m venv venv`.
2. Activez-le et installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancez l'application :
   ```bash
   streamlit run dashboard.py
   ```

## 🗺️ Validation Croisée

Pour activer la validation avec le GTFS statique :
1. Déposez votre fichier `gtfs.zip` (ou les fichiers `.txt` extraits) dans le dossier `gtfs_static/`.
2. Le dashboard détectera automatiquement les données au prochain rafraîchissement.

## 🛠️ Configuration (.env)

| Variable | Description |
|----------|-------------|
| `ALERTS_API_URL` | URL du endpoint GTFS-RT Alerts |
| `ALERTS_AUTH_MODE` | Mode d'auth (Custom Header, API Key, Basic Auth) |
| `ALERTS_CUSTOM_HEADER_NAME` | Nom du header (ex: `Ocp-Apim-Subscription-Key`) |
| `ALERTS_CUSTOM_HEADER_VALUE`| Valeur de votre clé API |

---
*Développé pour l'analyse et la validation de données de transport.*
