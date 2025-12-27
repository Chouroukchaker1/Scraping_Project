# 🌍 Plateforme d'Extraction Automatique d'Appels d'Offres

Plateforme web complète pour l'extraction, la gestion et la validation automatique d'appels d'offres provenant de 7 sources internationales différentes.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Node](https://img.shields.io/badge/node-18.x-green.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-18.3-61DAFB.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture](#-architecture)
- [Fonctionnalités](#-fonctionnalités)
- [Technologies](#-technologies)
- [Sources de données](#-sources-de-données)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation avec Docker](#-utilisation-avec-docker)
- [Utilisation sans Docker](#-utilisation-sans-docker)
- [API Documentation](#-api-documentation)
- [Structure du projet](#-structure-du-projet)
- [Contribution](#-contribution)
- [License](#-license)

## 🎯 Vue d'ensemble

Cette plateforme centralise l'extraction automatique d'appels d'offres depuis plusieurs organismes internationaux et nationaux. Elle offre :

- ✅ **Extraction automatique** depuis 7 sources différentes
- ✅ **Interface web moderne** avec authentification
- ✅ **Validation manuelle** des offres extraites
- ✅ **Export Excel** des données
- ✅ **API REST** complète
- ✅ **Multi-utilisateurs** avec gestion des rôles
- ✅ **Containerisation Docker** pour déploiement facile

## 🏗️ Architecture

Le projet suit une architecture **microservices** avec :

```
┌─────────────────┐
│   React SPA     │  (Port 80)
│   (Frontend)    │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Nginx  │
    └────┬────┘
         │
┌────────▼────────────┐
│   Node.js/Express   │  (Port 5000)
│   (API Gateway)     │
└─────────┬───────────┘
          │
    ┌─────┴──────┬──────────┬──────────┬──────────┬──────────┬──────────┐
    │            │          │          │          │          │          │
┌───▼───┐   ┌───▼───┐  ┌──▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐
│BOAMP  │   │TUNEPS │  │ PNUD │  │ ARMP  │  │HAICOP │  │BANQUE │  │ Flask │
│Flask  │   │ AO    │  │Flask │  │Flask  │  │Flask  │  │Flask  │  │ ...   │
│:5003  │   │ :5005 │  │:5006 │  │:5007  │  │:5011  │  │:5010  │  │       │
└───┬───┘   └───┬───┘  └──┬───┘  └───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘
    │           │         │          │          │          │          │
    └───────────┴─────────┴──────────┴──────────┴──────────┴──────────┘
                                      │
                              ┌───────▼────────┐
                              │   MongoDB      │
                              │   Database     │
                              │   (tunip)      │
                              └────────────────┘
```

### Composants principaux

1. **Frontend React** (Port 80) - Interface utilisateur moderne
2. **API Gateway Node.js** (Port 5000) - Routage et authentification
3. **Scrapers Python Flask** (Ports 5003-5011) - Extraction des données
4. **MongoDB** (Port 27017) - Base de données NoSQL

## ✨ Fonctionnalités

### 🔐 Authentification et Autorisation
- Inscription/Connexion avec JWT
- Gestion des rôles (USER, ADMIN, SUPER_ADMIN)
- Routes protégées
- Session persistante

### 📊 Tableau de bord
- Vue d'ensemble de toutes les sources
- Statistiques en temps réel
- Accès rapide aux différents scrapers

### 🤖 Scrapers automatisés
- Extraction programmée ou manuelle
- Validation en deux étapes (pending → validated)
- Détection des doublons
- Export Excel automatique

### 📈 Gestion des offres
- Liste des offres en attente
- Validation manuelle
- Modification des données
- Suppression
- Filtrage et recherche
- Pagination

### 📥 Export de données
- Export Excel par source
- Export global
- Données structurées

## 🛠️ Technologies

### Frontend
- **React** 18.3 - Framework UI
- **React Router** 7.9 - Routage
- **Axios** 1.12 - Client HTTP
- **Material-UI** 7.3 - Composants UI
- **Lucide React** - Icônes
- **JWT Decode** - Gestion tokens

### Backend
- **Node.js** 18.x - Runtime JavaScript
- **Express** 4.22 - Framework web
- **MongoDB** 7.0 - Base de données
- **Mongoose** 8.20 - ODM MongoDB
- **JWT** 9.0 - Authentification
- **Bcrypt** 3.0 - Hashage passwords

### Scrapers Python
- **Flask** 3.0 - Framework web
- **Flask-CORS** 4.0 - CORS
- **Requests** 2.32 - Client HTTP
- **BeautifulSoup** 4.12 - Parsing HTML
- **Selenium** 4.25 - Automation navigateur
- **Pandas** 2.2 - Manipulation données
- **PyMongo** 4.8 - Driver MongoDB
- **Playwright** - Scraping avancé
- **pdf2image** - Extraction PDF
- **Pillow** - Traitement images
- **APScheduler** - Tâches planifiées

### DevOps
- **Docker** - Containerisation
- **Docker Compose** - Orchestration
- **Nginx** - Reverse proxy
- **Git** - Contrôle de version

## 🌐 Sources de données

| Source | Pays/Organisation | Port | Description |
|--------|------------------|------|-------------|
| **PNUD** | Nations Unies | 5006 | Programme des Nations Unies pour le Développement |
| **TUNEPS** | Tunisie | 5005 | Plateforme tunisienne des marchés publics |
| **HAICOP** | Tunisie | 5011 | Haute Instance de la Commande Publique |
| **ARMP** | Madagascar | 5007 | Autorité de Régulation des Marchés Publics |
| **BOAMP** | France | 5003 | Bulletin Officiel des Annonces des Marchés Publics |
| **Banque Mondiale** | International | 5010 | Banque mondiale - Projets et marchés |

## 🚀 Installation

### Prérequis

- **Docker** et **Docker Compose** (recommandé)

OU

- **Node.js** 18.x ou supérieur
- **Python** 3.11 ou supérieur
- **MongoDB** 7.0 ou supérieur
- **Git**

### 1. Cloner le repository

```bash
git clone https://github.com/votre-username/extraction-automatique.git
cd extraction-automatique
```

### 2. Configuration des variables d'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer le fichier .env avec vos configurations
nano .env
```

**Important:** Modifiez au minimum ces variables :
- `JWT_SECRET` - Clé secrète pour JWT (utilisez une valeur aléatoire sécurisée)
- `API_EMAIL` et `API_PASSWORD` - Vos identifiants pour l'API externe
- `MONGO_URI` - URI de connexion MongoDB (si différent)

## 🐳 Utilisation avec Docker

### Démarrage rapide

```bash
# Construire et démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes (données)
docker-compose down -v
```

### Accès à l'application

- **Frontend:** http://localhost
- **API Backend:** http://localhost:5000
- **MongoDB:** localhost:27017

### Commandes utiles

```bash
# Reconstruire les images
docker-compose build

# Reconstruire un service spécifique
docker-compose build backend

# Redémarrer un service
docker-compose restart backend

# Voir l'état des services
docker-compose ps

# Exécuter une commande dans un container
docker-compose exec backend sh
docker-compose exec mongodb mongosh tunip

# Voir les logs d'un service spécifique
docker-compose logs -f backend
```

## 💻 Utilisation sans Docker

### Installation Backend

```bash
cd backend

# Installer les dépendances Node.js
npm install

# Installer les dépendances Python
pip install -r requirements.txt

# Installer Poppler (pour PDF - Windows)
# Télécharger depuis: https://github.com/oschwartz10612/poppler-windows/releases/
# Extraire et ajouter le dossier bin au PATH

# Démarrer le serveur
npm start
```

### Installation Frontend

```bash
cd auth-frontend

# Installer les dépendances
npm install

# Développement
npm start

# Production
npm run build
```

### Installation MongoDB

```bash
# Ubuntu/Debian
sudo apt-get install mongodb

# Windows
# Télécharger depuis: https://www.mongodb.com/try/download/community

# macOS
brew install mongodb-community

# Démarrer MongoDB
mongod --dbpath /path/to/data
```

## ⚙️ Configuration

### Variables d'environnement (.env)

```env
# Serveur
PORT=5000
NODE_ENV=production

# Base de données
MONGO_URI=mongodb://localhost:27017/tunip
DB_NAME=tunip

# JWT
JWT_SECRET=your_super_secret_jwt_key_change_me

# API externe
API_BASE_URL=https://be.appeloffres.net/api
API_EMAIL=your_email@example.com
API_PASSWORD=your_password

# IDs par défaut
DEFAULT_SOURCE_ID=1674
DEFAULT_SOURCE_ID_PNUD=1656
DEFAULT_PROMOTER_ID=223472
DEFAULT_AVIS_ID=1
DEFAULT_PAYS_ID=70
DEFAULT_CURRENCY_ID=111

# Collections MongoDB
BOAMP_COLLECTION_NAME=boampvalidates
BOAMP_PENDING_COLLECTION_NAME=boampoffres
PNUD_COLLECTION_NAME=tenders_pnud
PNUD_PENDING_COLLECTION_NAME=pending_tenders_pnud

# Frontend
REACT_APP_API_BASE=http://localhost:5000/api
```

### Ports utilisés

| Service | Port | Description |
|---------|------|-------------|
| Frontend (dev) | 3000 | Serveur de développement React |
| Frontend (prod) | 80 | Nginx |
| Backend API | 5000 | Node.js/Express |
| BOAMP | 5003 | Scraper Flask |
| TUNEPS AO | 5005 | Scraper Flask |
| PNUD | 5006 | Scraper Flask |
| ARMP | 5007 | Scraper Flask |
| Banque Mondiale | 5010 | Scraper Flask |
| HAICOP | 5011 | Scraper Flask |
| MongoDB | 27017 | Base de données |

## 📚 API Documentation

### Authentification

#### Inscription
```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securePassword123"
}
```

#### Connexion
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securePassword123"
}

Response:
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "...",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "USER"
  }
}
```

### Scrapers (exemple PNUD)

#### Lancer un scraping
```http
POST /api/pnud/api/scrape
Authorization: Bearer <token>
Content-Type: application/json

{
  "start_date": "2025-01-01",
  "end_date": "2025-12-31"
}
```

#### Obtenir les offres en attente
```http
GET /api/pnud/api/pending?page=1&limit=50
Authorization: Bearer <token>
```

#### Obtenir les offres validées
```http
GET /api/pnud/api/tenders
Authorization: Bearer <token>
```

#### Valider une offre
```http
POST /api/pnud/api/validate/<reference>
Authorization: Bearer <token>
```

#### Supprimer une offre
```http
DELETE /api/pnud/api/delete/<reference>
Authorization: Bearer <token>
```

### Health Check

```http
GET /health

Response:
{
  "node": "healthy",
  "timestamp": "2025-12-18T12:00:00.000Z",
  "scrapers": {
    "pnud": "running",
    "haicop": "running",
    ...
  }
}
```

## 📁 Structure du projet

```
extraction-automatique/
│
├── backend/                        # API Node.js + Scrapers Python
│   ├── server.js                   # Point d'entrée principal
│   ├── package.json                # Dépendances Node.js
│   ├── requirements.txt            # Dépendances Python
│   ├── Dockerfile                  # Image Docker backend
│   ├── .dockerignore
│   │
│   ├── config.js                   # Configuration globale
│   │
│   ├── models/                     # Modèles Mongoose
│   │   └── User.js
│   │
│   ├── routes/                     # Routes Express
│   │   ├── auth.js                 # Authentification
│   │   ├── users.js                # Gestion utilisateurs
│   │   ├── tuneps.js               # Routes TUNEPS
│   │   └── routesboamp.js          # Routes BOAMP
│   │
│   ├── middleware/                 # Middlewares Express
│   │   └── auth.js                 # Middleware JWT
│   │
│   ├── controllers/                # Contrôleurs
│   │   ├── authController.js
│   │   └── scraperController.js
│   │
│   └── scripts/                    # Scrapers Python Flask
│       ├── pnud.py                 # PNUD (Port 5006)
│       ├── haicop.py               # HAICOP (Port 5011)
│       ├── tuneps_ao.py            # TUNEPS AO (Port 5005)
│       ├── armp_flask.py           # ARMP (Port 5007)
│       ├── banque_flask.py         # Banque Mondiale (Port 5010)
│       └── scraper.py              # BOAMP (Port 5003)
│
├── auth-frontend/                  # Application React
│   ├── public/
│   │   └── index.html
│   │
│   ├── src/
│   │   ├── App.js                  # Routeur principal
│   │   ├── index.js                # Point d'entrée
│   │   ├── axiosConfig.js          # Configuration Axios
│   │   │
│   │   ├── components/             # Composants réutilisables
│   │   │   ├── Navbar.js
│   │   │   ├── PrivateRoute.js
│   │   │   └── Pagination.js
│   │   │
│   │   ├── pages/                  # Pages de l'application
│   │   │   ├── Login.js            # Page de connexion
│   │   │   ├── Register.js         # Page d'inscription
│   │   │   ├── Dashboard.js        # Tableau de bord
│   │   │   ├── tuneps.js           # Visualisateur TUNEPS
│   │   │   ├── pnud.js             # Visualisateur PNUD
│   │   │   ├── haicop.js           # Visualisateur HAICOP
│   │   │   ├── banque.js           # Visualisateur Banque
│   │   │   ├── boamp.js            # Visualisateur BOAMP
│   │   │   ├── armp.js             # Visualisateur ARMP
│   │   │   ├── appel_offres.js     # Appels d'offres TUNEPS
│   │   │   └── mutlisites.js       # Navigation multi-sites
│   │   │
│   │   └── context/                # Context API React
│   │       └── AuthContext.js      # Contexte authentification
│   │
│   ├── package.json                # Dépendances React
│   ├── Dockerfile                  # Image Docker frontend
│   ├── nginx.conf                  # Configuration Nginx
│   └── .dockerignore
│
├── docker-compose.yml              # Orchestration Docker
├── .env                            # Variables d'environnement (à créer)
├── .env.example                    # Exemple de configuration
├── .gitignore
└── README.md                       # Cette documentation
```

## 👥 Gestion des utilisateurs

### Rôles disponibles

- **USER** - Accès lecture seule, peut consulter les offres
- **ADMIN** - Peut valider/supprimer des offres, créer des utilisateurs
- **SUPER_ADMIN** - Accès complet, gestion des utilisateurs et paramètres

### Créer un utilisateur ADMIN

```bash
# Via l'API (nécessite un compte SUPER_ADMIN)
curl -X POST http://localhost:5000/api/users/create \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin User",
    "email": "admin@example.com",
    "password": "securePassword",
    "role": "ADMIN"
  }'
```

## 🔧 Dépannage

### Problème: Les scrapers ne démarrent pas

**Solution:**
```bash
# Vérifier les logs
docker-compose logs backend

# Redémarrer le backend
docker-compose restart backend
```

### Problème: MongoDB connection refused

**Solution:**
```bash
# Vérifier que MongoDB est lancé
docker-compose ps

# Vérifier les logs MongoDB
docker-compose logs mongodb

# Redémarrer MongoDB
docker-compose restart mongodb
```

### Problème: Frontend ne se connecte pas au backend

**Solution:**
- Vérifier que `REACT_APP_API_BASE` dans `.env` pointe vers le bon backend
- En développement: `http://localhost:5000/api`
- En production Docker: `/api` (Nginx proxy)

### Problème: Erreur "Port already in use"

**Solution:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

## 📊 Monitoring et Logs

### Logs Docker

```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs -f backend
docker-compose logs -f mongodb

# 100 dernières lignes
docker-compose logs --tail=100 backend
```

### Logs fichiers (sans Docker)

```bash
# Backend
tail -f backend/logs/*.log

# Scrapers Python
tail -f backend/*.log
```

## 🔒 Sécurité

### Bonnes pratiques

1. **Changez le JWT_SECRET** dans `.env`
2. **Utilisez HTTPS** en production
3. **Mettez à jour** régulièrement les dépendances
4. **Limitez** les rôles ADMIN
5. **Sauvegardez** régulièrement MongoDB
6. **N'exposez pas** les ports des scrapers en production
7. **Utilisez** des mots de passe forts

### Sauvegarder MongoDB

```bash
# Backup
docker-compose exec mongodb mongodump --db tunip --out /data/backup

# Restore
docker-compose exec mongodb mongorestore --db tunip /data/backup/tunip
```

## 🚀 Déploiement en production

### 1. Préparer l'environnement

```bash
# Créer le fichier .env de production
cp .env.example .env
nano .env  # Configurer les valeurs de production
```

### 2. Build et démarrage

```bash
# Pull les dernières modifications
git pull origin main

# Build et démarrer
docker-compose -f docker-compose.yml up -d --build

# Vérifier le statut
docker-compose ps
```

### 3. Configuration HTTPS (optionnel)

```bash
# Installer Certbot
sudo apt-get install certbot

# Obtenir un certificat SSL
sudo certbot certonly --standalone -d votre-domaine.com

# Mettre à jour nginx.conf avec les certificats
```

### 4. Configuration du pare-feu

```bash
# Autoriser HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Bloquer les ports des scrapers (sécurité)
sudo ufw deny 5003:5011/tcp
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📝 Changelog

### Version 1.0.0 (2025-12-18)
- ✨ Release initiale
- ✅ 7 scrapers fonctionnels
- ✅ Interface React complète
- ✅ Authentification JWT
- ✅ Containerisation Docker
- ✅ Documentation complète

## 📄 License

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👨‍💻 Auteurs

- **Votre Nom** - *Développement initial*

## 🙏 Remerciements

- PNUD pour leur API publique
- TUNEPS pour la plateforme
- ARMP Madagascar
- HAICOP Tunisie
- Banque Mondiale
- BOAMP France

## 📞 Support

Pour toute question ou problème :
- 📧 Email: support@example.com
- 💬 Issues GitHub: [Issues](https://github.com/votre-username/extraction-automatique/issues)

---

**Note:** Ce projet est développé à des fins éducatives et de recherche. Veuillez respecter les conditions d'utilisation des sites web sources lors du scraping.
