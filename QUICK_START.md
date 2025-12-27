# 🚀 Guide de démarrage rapide

Ce guide vous permet de démarrer le projet en moins de 5 minutes.

## Option 1: Démarrage avec Docker (Recommandé)

### Prérequis
- Docker Desktop installé ([Télécharger](https://www.docker.com/products/docker-desktop))

### Étapes

```bash
# 1. Cloner le projet
git clone <votre-repo>
cd extractionautomatic

# 2. Créer le fichier .env
cp .env.example .env

# 3. (IMPORTANT) Éditer .env et changer JWT_SECRET
notepad .env  # Windows
nano .env     # Linux/Mac

# 4. Démarrer tous les services
docker-compose up -d

# 5. Attendre 30 secondes que tout démarre

# 6. Ouvrir votre navigateur
# http://localhost
```

### Vérification

```bash
# Vérifier que tout fonctionne
docker-compose ps

# Devrait afficher:
# frontend_tenders    Up    80/tcp, 443/tcp
# backend_tenders     Up    5000/tcp, 5003/tcp, 5005/tcp, 5006/tcp, 5007/tcp, 5010/tcp, 5011/tcp
# mongodb_tenders     Up    27017/tcp
```

### Arrêter

```bash
docker-compose down
```

## Option 2: Démarrage sans Docker

### Prérequis
- Node.js 18+ ([Télécharger](https://nodejs.org/))
- Python 3.11+ ([Télécharger](https://www.python.org/))
- MongoDB 7+ ([Télécharger](https://www.mongodb.com/try/download/community))

### Backend

```bash
# 1. Aller dans le dossier backend
cd backend

# 2. Installer Node.js
npm install

# 3. Installer Python
pip install -r requirements.txt

# 4. Créer .env
cp ../.env.example ../.env
notepad ../.env  # Éditer JWT_SECRET

# 5. Démarrer MongoDB (dans un autre terminal)
mongod --dbpath C:\data\db  # Windows
mongod --dbpath /data/db    # Linux/Mac

# 6. Démarrer le backend
npm start
```

### Frontend

```bash
# Dans un nouveau terminal

# 1. Aller dans le dossier frontend
cd auth-frontend

# 2. Installer les dépendances
npm install

# 3. Démarrer
npm start

# 4. Ouvrir http://localhost:3000
```

## Premiers pas

### 1. Créer un compte

- Aller sur http://localhost (ou http://localhost:3000)
- Cliquer sur "S'inscrire"
- Remplir le formulaire
- Se connecter

### 2. Accéder au tableau de bord

- Après connexion, vous verrez le dashboard
- Cliquer sur "Multi-Sites" pour voir toutes les sources disponibles

### 3. Lancer un scraping

Exemple avec PNUD:

1. Cliquer sur "PNUD" dans Multi-Sites
2. Cliquer sur "Lancer le Scraping"
3. Sélectionner les dates
4. Cliquer sur "Lancer"
5. Attendre quelques secondes
6. Les offres apparaissent dans "Offres en attente"
7. Valider les offres souhaitées

### 4. Voir les offres validées

- Onglet "Offres Validées"
- Export Excel possible

## Ports utilisés

| Service | Port | URL |
|---------|------|-----|
| Frontend | 80 | http://localhost |
| Backend API | 5000 | http://localhost:5000 |
| BOAMP | 5003 | - |
| TUNEPS AO | 5005 | - |
| PNUD | 5006 | - |
| ARMP | 5007 | - |
| Banque Mondiale | 5010 | - |
| HAICOP | 5011 | - |
| MongoDB | 27017 | - |

## Problèmes courants

### Port 80 déjà utilisé (Windows)

```bash
# Arrêter IIS ou autre service web
net stop http

# Ou changer le port dans docker-compose.yml
ports:
  - "8080:80"  # Utiliser 8080 au lieu de 80
```

### MongoDB connection error

```bash
# Vérifier que MongoDB est démarré
docker-compose logs mongodb

# Redémarrer MongoDB
docker-compose restart mongodb
```

### Backend ne démarre pas

```bash
# Voir les erreurs
docker-compose logs backend

# Souvent c'est le JWT_SECRET qui manque
nano .env  # Ajouter JWT_SECRET=votre_secret
docker-compose restart backend
```

## Commandes utiles

```bash
# Voir tous les logs
docker-compose logs -f

# Redémarrer tout
docker-compose restart

# Nettoyer et recommencer
docker-compose down -v
docker-compose up -d --build

# Arrêter un service
docker-compose stop backend

# Démarrer un service
docker-compose start backend
```

## Aide

- README complet: [README.md](README.md)
- Issues: Créer une issue sur GitHub
- Email: support@example.com

## Checklist de démarrage

- [ ] Docker Desktop installé et démarré
- [ ] Repository cloné
- [ ] Fichier .env créé depuis .env.example
- [ ] JWT_SECRET modifié dans .env
- [ ] `docker-compose up -d` exécuté
- [ ] Navigateur ouvert sur http://localhost
- [ ] Compte créé
- [ ] Premier scraping testé

**Félicitations! Vous êtes prêt à utiliser la plateforme! 🎉**
