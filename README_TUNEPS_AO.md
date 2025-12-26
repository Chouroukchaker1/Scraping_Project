# 🇹🇳 Guide TUNEPS Appels d'Offres - Docker

## ✅ Installation et Démarrage

### 1. Démarrer avec Docker Compose
```bash
docker-compose up -d
```

Cela démarre automatiquement :
- **MongoDB** sur port `27018`
- **Backend Node.js** sur port `5000`
- **Frontend React** sur port `8080`
- **Tous les scrapers Python** (TUNEPS AO sur port 5005)

### 2. Vérifier que tout fonctionne
```bash
# Vérifier les conteneurs
docker ps

# Tester l'API TUNEPS AO
curl http://localhost:8080/api/tuneps_ao/api/test
```

## 🚀 Utilisation

### Via l'interface web (Recommandé)
1. Ouvrez votre navigateur : **http://localhost:8080/tuneps_appel-offres**
2. Entrez la **date de début** et la **date de fin** (format: YYYY-MM-DD)
   - Exemple: `2025-12-24` à `2025-12-24`
3. Cochez **"Mode extraction complète"** si vous voulez :
   - Les lots détaillés
   - Les cautionnements
   - Les PDFs des cahiers des charges
   - ⚠️ Plus lent mais plus complet
4. Cliquez sur **"Lancer le Scraping"**
5. Les données apparaissent dans **"Offres en Attente"** après le scraping
6. Validez les offres pour les envoyer vers l'API AppelOffres

### Via API directement
```bash
# Lancer un scraping rapide pour aujourd'hui
curl -X POST http://localhost:8080/api/tuneps_ao/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start":"2025-12-24","end":"2025-12-24","extraction_complete":false}'

# Vérifier le statut
curl http://localhost:8080/api/tuneps_ao/api/status

# Récupérer les offres en attente
curl http://localhost:8080/api/tuneps_ao/api/pending?limit=100

# Récupérer les offres validées
curl http://localhost:8080/api/tuneps_ao/api/tenders
```

## 📁 Architecture

```
Frontend (port 8080)
    ↓ nginx proxy /api
Backend Node.js (port 5000)
    ↓ proxy /api/tuneps_ao
Flask TUNEPS AO (port 5005)
    ↓
MongoDB (port 27018)
```

**Collections MongoDB** :
- `pending_tenders_marmouch_bd` : Offres en attente de validation
- `tenders_marmouch` : Offres validées

## 🔧 Configuration

### Variables d'environnement (backend/.env)
```bash
MONGO_URI=mongodb://mongodb:27017/marmoucha
DB_NAME=marmouchbd

# API AppelOffres
API_BASE_URL=https://be.appeloffres.net/api
EMAIL=maryam.marmouch@tunipages.tn
API_PASSWORD=Marmouch2345!@
DEFAULT_SOURCE_ID=817
DEFAULT_PROMOTER_ID=223472
DEFAULT_AVIS_ID=2
DEFAULT_PAYS_ID=219
DEFAULT_CURRENCY_ID=111
```

## 🔍 Logs et Debugging

```bash
# Voir les logs du backend
docker logs backend_tenders -f

# Voir les logs du frontend
docker logs frontend_tenders -f

# Voir les logs MongoDB
docker logs mongodb_tenders -f

# Filtrer les logs TUNEPS AO
docker logs backend_tenders 2>&1 | grep "TUNEPS AO"
```

## 🛑 Arrêt et redémarrage

```bash
# Arrêter tous les services
docker-compose down

# Redémarrer avec rebuild (après modification du code)
docker-compose up --build -d

# Redémarrer seulement le frontend
docker-compose up --build -d frontend

# Redémarrer seulement le backend
docker-compose up --build -d backend
```

## 📊 Fonctionnalités TUNEPS AO

### Extraction automatique
- ✅ Référence complète (N° référence + N° offre)
- ✅ Description de l'offre
- ✅ Acheteur public (promoteur)
- ✅ Dates (publication, début soumission, expiration, ouverture offres)
- ✅ **Lots** avec titre et cautionnement
- ✅ Région de Tunisie (auto-détection)
- ✅ Cautionnement provisoire
- ✅ Durée de validité de l'offre
- ✅ Documents joints
- ✅ Cahier des charges (URL)

### Modes de scraping
1. **Mode rapide** (par défaut) :
   - Extraction des données essentielles
   - Pas de téléchargement PDF
   - Plus rapide (quelques minutes)

2. **Mode complet** :
   - Extraction complète avec lots détaillés
   - Téléchargement des PDFs
   - Upload des images vers S3
   - Plus lent (peut prendre 10-30 minutes)

### Filtrage intelligent
- ✅ Détection automatique des dates anciennes (> 90 jours)
- ✅ Arrêt automatique après 3 pages vides
- ✅ Déduplication automatique
- ✅ Filtrage par plage de dates

## 🔐 Sécurité

- CORS configuré pour accepter les requêtes de localhost
- Timeouts configurés pour 30 minutes (scrapers longs)
- Gestion automatique des erreurs et retry
- Health checks sur tous les services

## 📞 Support

Pour tout problème :
1. Vérifiez les logs : `docker logs backend_tenders -f`
2. Vérifiez que MongoDB est démarré : `docker ps`
3. Testez l'API : `curl http://localhost:8080/api/tuneps_ao/api/test`
4. Si problème persiste, reconstruisez : `docker-compose up --build -d`

## 🎯 URLs importantes

- **Frontend** : http://localhost:8080
- **Page TUNEPS AO** : http://localhost:8080/tuneps_appel-offres
- **API Backend** : http://localhost:5000
- **API TUNEPS AO directe** : http://localhost:5005/api
- **MongoDB** : mongodb://localhost:27018/marmoucha
