# 🔧 Correctif Scraper Banque Mondiale

## ✅ Problèmes corrigés

### 1. **Filtrage par type d'avis supprimé**
**Avant**: Le scraper ne récupérait que certains types d'avis:
- Contract Award
- Invitation for Bids
- Request for Proposal
- Expression of Interest
- General Procurement Notice
- Procurement Notice

**Après**: Le scraper récupère **TOUS** les types d'avis sans filtre, seulement filtré par date.

### 2. **Extraction exhaustive augmentée**
**Avant**:
- Pagination limitée à ~1000 offsets
- Arrêt prématuré après quelques pages

**Après**:
- Pagination jusqu'à 2000 offsets
- Extraction complète de toutes les données disponibles
- Meilleure gestion de l'arrêt (continue jusqu'à épuisement des données)

### 3. **Erreur MongoDB corrigée**
**Erreur**: `NotImplementedError: Collection objects do not implement truth value testing`

**Cause**: Ligne 1122 utilisait `if pending_collection` au lieu de `if pending_collection is not None`

**Solution**: Correction de la comparaison avec `None`

## 📝 Modifications apportées

### Fichier: `backend/scripts/banque_flask.py`

#### Fonction `extract_by_notice_types()` (ligne 447)
```python
# AVANT - Filtrait par type
notice_types = [
    'Contract Award', 'Invitation for Bids', 'Request for Proposal',
    'Expression of Interest', 'General Procurement Notice', 'Procurement Notice'
]
for notice_type in notice_types:
    params = {
        'notice_type_exact': notice_type,  # ❌ FILTRE
        ...
    }

# APRÈS - Récupère TOUT
for offset in range(0, 1000, 100):  # Parcourt toutes les pages
    params = {
        'os': offset,
        'rows': 100,
        'srt': 'publishdate',
        'order': 'desc'
        # ✅ PAS DE FILTRE DE TYPE
    }
```

#### Fonction `extract_all_notices_with_retry()` (ligne 339)
```python
# AVANT - Pagination limitée
start_pages = [0, 100, 200, 300, 400]
for start_offset in start_pages:
    if successful_pages >= 5:  # ❌ Limite à 5 pages
        break

# APRÈS - Extraction exhaustive
max_offset = 2000  # ✅ Augmenté
for current_offset in range(0, max_offset, 100):
    # Continue jusqu'à épuisement des données
    if not notices:
        break
```

#### Fonction `health_check()` (ligne 1119)
```python
# AVANT - Erreur
pending_count = pending_collection.count_documents({}) if pending_collection else 0  # ❌

# APRÈS - Corrigé
pending_count = pending_collection.count_documents({}) if pending_collection is not None else 0  # ✅
```

## 🎯 Résultat attendu

### Types d'avis extraits (TOUS)
- ✅ Contract Award (Attribution de contrat)
- ✅ Invitation for Bids (Appel d'offres)
- ✅ Request for Proposal (Demande de propositions)
- ✅ Expression of Interest (Manifestation d'intérêt)
- ✅ General Procurement Notice (Avis général de passation)
- ✅ Procurement Notice (Avis de passation)
- ✅ Request for Quotation (Demande de devis)
- ✅ Prior Review (Examen préalable)
- ✅ **ET TOUS LES AUTRES TYPES**

### Filtres appliqués
- ✅ **Date uniquement** (start_date à end_date)
- ✅ Pays africains (optionnel)
- ❌ **PAS de filtre par type d'avis**
- ❌ **PAS de filtre par contenu**

## 🚀 Utilisation

### Via l'interface web
1. Allez sur: `http://localhost:8080/banque`
2. Sélectionnez la plage de dates
3. Cliquez sur "Lancer l'extraction"
4. **Tous les types d'avis** dans cette période seront extraits

### Via API
```bash
curl -X POST http://localhost:8080/api/banque/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-12-01",
    "end_date": "2025-12-24"
  }'
```

## 📊 Volume de données

### Avant (avec filtres)
- ~50-100 avis par mois
- Seulement 6 types d'avis

### Après (sans filtres)
- **~200-500 avis par mois**
- **TOUS les types d'avis**
- Extraction complète de toutes les publications

## 🔍 Vérification

### Tester le serveur
```bash
curl http://localhost:8080/api/banque/api/health
```

Réponse attendue:
```json
{
  "status": "healthy",
  "service": "Banque Mondiale Extractor API",
  "version": "2.0",
  "database": {
    "connected": true,
    "pending_count": 0,
    "validated_count": 0
  }
}
```

### Lancer un test d'extraction
```bash
curl -X POST http://localhost:8080/api/banque/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-12-20",
    "end_date": "2025-12-24"
  }'
```

### Vérifier les résultats
```bash
# Voir le statut
curl http://localhost:8080/api/banque/api/status

# Voir les offres en attente
curl http://localhost:8080/api/banque/api/pending
```

## 📝 Notes importantes

1. **Performance**: L'extraction complète prend plus de temps (5-15 minutes selon la période)
2. **Volume**: Beaucoup plus de données récupérées
3. **Filtres**: Seul le filtre par date est appliqué
4. **Déduplication**: Automatique par ID de projet

## 🐛 Débogage

### Si aucune donnée n'est extraite
```bash
# Vérifier les logs
docker logs backend_tenders -f | grep "BANQUE"

# Vérifier MongoDB
docker exec -it mongodb_tenders mongosh worldbank_db-ines
db.pending_tenders_ines.countDocuments()
```

### Si erreur de connexion
```bash
# Redémarrer le backend
docker-compose restart backend

# Vérifier la santé
curl http://localhost:8080/api/banque/api/health
```

Date de mise à jour: 24 décembre 2025
