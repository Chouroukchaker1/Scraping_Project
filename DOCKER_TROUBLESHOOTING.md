# 🐳 Guide de Dépannage Docker

## Problèmes courants et solutions

### 1. Port déjà utilisé (MongoDB 27017)

**Erreur:**
```
Bind for 0.0.0.0:27017 failed: port is already allocated
```

**Solution:**
Le port MongoDB a été changé de 27017 à 27018 dans `docker-compose.yml`

### 2. Erreur de build Docker

**Erreur:**
```
failed to prepare extraction snapshot
```

**Solution:**
```bash
# Nettoyer Docker
docker system prune -f

# Rebuild sans cache
docker-compose build --no-cache

# Démarrer
docker-compose up -d
```

### 3. Containers ne démarrent pas

**Vérifier l'état:**
```bash
docker-compose ps
```

**Voir les logs:**
```bash
docker-compose logs -f
```

**Redémarrer un service:**
```bash
docker-compose restart backend
docker-compose restart frontend
docker-compose restart mongodb
```

### 4. Frontend ne se charge pas

**Vérifier si le container tourne:**
```bash
docker ps | grep frontend
```

**Voir les logs:**
```bash
docker-compose logs frontend
```

**Rebuild frontend:**
```bash
docker-compose up -d --build frontend
```

### 5. Backend ne répond pas

**Vérifier:**
```bash
docker-compose logs backend
```

**Tester l'API:**
```bash
curl http://localhost:5000/health
```

### 6. MongoDB connection error

**Vérifier MongoDB:**
```bash
docker-compose logs mongodb
```

**Se connecter à MongoDB:**
```bash
docker-compose exec mongodb mongosh tunip
```

## 🔧 Commandes utiles

### Démarrage/Arrêt

```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v

# Redémarrer tout
docker-compose restart
```

### Logs et debug

```bash
# Voir tous les logs
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb

# Dernières 100 lignes
docker-compose logs --tail=100 backend
```

### Build et rebuild

```bash
# Build initial
docker-compose build

# Build sans cache (si problèmes)
docker-compose build --no-cache

# Build et start
docker-compose up -d --build

# Rebuild un service spécifique
docker-compose build backend
docker-compose up -d backend
```

### Nettoyage Docker

```bash
# Nettoyer cache build
docker builder prune -f

# Nettoyer tout le système
docker system prune -f

# Supprimer images non utilisées
docker image prune -a -f

# Supprimer volumes non utilisés
docker volume prune -f
```

### Inspection

```bash
# Liste des containers
docker ps -a

# Liste des images
docker images

# Liste des volumes
docker volume ls

# Liste des réseaux
docker network ls

# Inspecter un container
docker inspect backend_tenders

# Ressources utilisées
docker stats
```

### Accès aux containers

```bash
# Shell dans le backend
docker-compose exec backend sh

# Shell dans MongoDB
docker-compose exec mongodb mongosh tunip

# Shell dans le frontend (Nginx)
docker-compose exec frontend sh
```

## 📊 Vérification santé

### Tester tous les services

```bash
# Frontend
curl http://localhost:8080

# Backend
curl http://localhost:5000/health

# MongoDB (depuis le container backend)
docker-compose exec backend sh -c "curl mongodb:27017"
```

### Vérifier les ports

```bash
# Windows
netstat -ano | findstr :8080
netstat -ano | findstr :5000
netstat -ano | findstr :27018

# Linux/Mac
lsof -i :8080
lsof -i :5000
lsof -i :27018
```

## 🚀 Procédure de démarrage propre

```bash
# 1. Arrêter tout
docker-compose down -v

# 2. Nettoyer Docker
docker system prune -f

# 3. Vérifier le fichier .env
cat .env

# 4. Build complet
docker-compose build --no-cache

# 5. Démarrer
docker-compose up -d

# 6. Attendre 30 secondes
sleep 30

# 7. Vérifier l'état
docker-compose ps

# 8. Voir les logs
docker-compose logs -f

# 9. Tester l'application
# Ouvrir http://localhost:8080
```

## ⚠️ Problèmes spécifiques

### "Cannot connect to Docker daemon"

**Solution:**
- Démarrer Docker Desktop
- Vérifier que Docker est en cours d'exécution

### "Permission denied"

**Linux/Mac:**
```bash
sudo docker-compose up -d
```

Ou ajouter votre utilisateur au groupe docker:
```bash
sudo usermod -aG docker $USER
# Puis redémarrer la session
```

### "Out of disk space"

**Solution:**
```bash
# Nettoyer tout
docker system prune -a -f --volumes
```

### "Network error"

**Solution:**
```bash
# Supprimer le réseau
docker network rm extractionautomatic_tenders_network

# Relancer
docker-compose up -d
```

## 📝 Checklist avant de démarrer

- [ ] Docker Desktop est installé et démarré
- [ ] Fichier `.env` existe et contient `JWT_SECRET`
- [ ] Ports 8080, 5000, 27018 sont libres
- [ ] Au moins 10 GB d'espace disque disponible
- [ ] Connexion internet active (première fois)

## 🆘 En cas de problème persistant

1. **Nettoyer complètement:**
```bash
docker-compose down -v
docker system prune -a -f --volumes
```

2. **Supprimer les images:**
```bash
docker rmi extractionautomatic-backend extractionautomatic-frontend
```

3. **Rebuild from scratch:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

4. **Vérifier les logs détaillés:**
```bash
docker-compose logs --tail=1000
```

## 📞 URLs de test

- **Frontend:** http://localhost:8080
- **Backend API:** http://localhost:5000
- **Backend Health:** http://localhost:5000/health
- **MongoDB:** localhost:27018 (depuis host)
- **MongoDB:** mongodb:27017 (depuis containers)

## 🎯 Configuration actuelle

```yaml
Frontend: Port 8080 → 80 (Nginx)
Backend: Port 5000
MongoDB: Port 27018 → 27017

Volumes:
- mongodb_data (persistant)
- mongodb_config (persistant)
- Backend logs, excel, screenshots (bind mounts)
```

---

**Note:** Ce guide suppose que vous avez modifié `docker-compose.yml` pour utiliser le port 8080 (frontend) et 27018 (MongoDB).
