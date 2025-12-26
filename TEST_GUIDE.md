# 🧪 Guide de Test - TUNEPS Appels d'Offres

## ✅ Étapes de test

### 1. Vérifier que Docker fonctionne
```bash
docker ps
```

Vous devez voir 3 conteneurs en cours d'exécution:
- `backend_tenders` (healthy)
- `frontend_tenders`
- `mongodb_tenders` (healthy)

### 2. Ouvrir l'interface web
Allez sur: **http://localhost:8080/tuneps_appel-offres**

### 3. Lancer un test de scraping

#### Option A: Test rapide (quelques minutes)
1. **Date de début**: `2025-12-24`
2. **Date de fin**: `2025-12-24`
3. **Mode extraction complète**: ❌ NON coché
4. Cliquez sur **"Lancer le Scraping"**

#### Option B: Test complet (10-30 minutes)
1. **Date de début**: `2025-12-20`
2. **Date de fin**: `2025-12-24`
3. **Mode extraction complète**: ✅ COCHÉ
4. Cliquez sur **"Lancer le Scraping"**

### 4. Surveiller le scraping

L'interface se met à jour automatiquement toutes les 10 secondes.

**Indicateurs de progression**:
- ⏱️ Message "Scraping en cours depuis X secondes..."
- 🔄 Icône tournante

**Voir les logs en direct** (optionnel):
```bash
docker logs backend_tenders -f | grep "TUNEPS AO"
```

### 5. Vérifier les résultats

Après quelques minutes, les offres apparaissent dans **"Offres en Attente"**

Pour chaque offre, vous verrez:
- ✅ Référence complète
- ✅ Description
- ✅ Acheteur public
- ✅ Dates (publication, limite)
- ✅ Nombre de lots et cautionnement

### 6. Valider une offre

1. Cliquez sur le bouton vert ✓ (CheckCircle)
2. Confirmez la validation
3. L'offre disparaît de "Offres en Attente"
4. L'offre apparaît dans "Offres Validées"
5. L'offre est automatiquement envoyée vers l'API AppelOffres

### 7. Tests API (optionnel)

#### Test de connexion
```bash
curl http://localhost:8080/api/tuneps_ao/api/test
```

Réponse attendue:
```json
{
  "base_url": "https://www.tuneps.tn/portail/offres",
  "message": "Backend TUNEPS OFFRES OK",
  "pending_count": 4,
  "processing": false
}
```

#### Lancer scraping via API
```bash
curl -X POST http://localhost:8080/api/tuneps_ao/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start":"2025-12-24","end":"2025-12-24","extraction_complete":false}'
```

Réponse attendue:
```json
{
  "success": true,
  "message": "Scraping TUNEPS AO lancé (rapide)"
}
```

#### Vérifier le statut
```bash
curl http://localhost:8080/api/tuneps_ao/api/status
```

Pendant le scraping:
```json
{
  "processing": true,
  "duration_seconds": 45.2,
  "message": "Scraping en cours..."
}
```

Après le scraping:
```json
{
  "processing": false,
  "pending_count": 18,
  "message": "Aucun scraping en cours"
}
```

#### Récupérer les offres
```bash
# Offres en attente
curl http://localhost:8080/api/tuneps_ao/api/pending?limit=100

# Offres validées
curl http://localhost:8080/api/tuneps_ao/api/tenders
```

## 🔍 Résolution de problèmes

### Erreur 502 Bad Gateway
```bash
# Redémarrer le backend
docker-compose restart backend

# Vérifier les logs
docker logs backend_tenders --tail 50
```

### Scraping ne démarre pas
```bash
# Vérifier que Flask TUNEPS AO fonctionne
docker exec backend_tenders curl http://localhost:5005/api/test

# Redémarrer complètement
docker-compose down
docker-compose up -d
```

### Pas de données après scraping
```bash
# Vérifier MongoDB
docker exec -it mongodb_tenders mongosh marmoucha

# Dans mongosh:
db.pending_tenders_marmouch_bd.countDocuments()
db.tenders_marmouch.countDocuments()
```

### Logs détaillés
```bash
# Tous les logs du backend
docker logs backend_tenders -f

# Seulement TUNEPS AO
docker logs backend_tenders -f 2>&1 | grep "TUNEPS AO"

# Logs du frontend nginx
docker logs frontend_tenders -f
```

## 📊 Résultats attendus

### Mode rapide (sans extraction complète)
- ⏱️ Durée: 2-5 minutes
- 📦 Données extraites:
  - Référence
  - Description
  - Acheteur public
  - Dates essentielles
  - URL source

### Mode complet (avec extraction complète)
- ⏱️ Durée: 10-30 minutes (selon nombre d'offres)
- 📦 Données extraites:
  - Tout du mode rapide +
  - Lots détaillés avec titres
  - Cautionnements par lot
  - Durée de validité
  - Date d'ouverture des offres
  - Pièces jointes
  - URL cahier des charges

## ✅ Checklist de validation

- [ ] L'interface charge correctement sur port 8080
- [ ] Le formulaire de scraping est visible
- [ ] Le scraping se lance sans erreur 502
- [ ] Le message "Scraping en cours" apparaît
- [ ] Les offres apparaissent dans "Offres en Attente"
- [ ] On peut valider une offre
- [ ] L'offre validée apparaît dans "Offres Validées"
- [ ] Les lots et cautionnements sont visibles (si mode complet)
- [ ] La pagination fonctionne (si > 50 offres)
- [ ] La recherche fonctionne

## 🎯 Prochaines étapes

Une fois les tests réussis:
1. ✅ Configurer le scraping automatique quotidien (déjà à 7h30)
2. ✅ Personnaliser les filtres de recherche
3. ✅ Exporter vers Excel (déjà disponible dans `/app/excel/`)
4. ✅ Connecter à l'API production AppelOffres

Bon test ! 🚀
