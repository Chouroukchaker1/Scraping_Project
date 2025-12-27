# 🇨🇩 Guide Complet - MediaCongo Scraper

## ✅ Améliorations Apportées

### 1. **Pagination Complète** (RÉSOLU ✅)
- **Avant**: Scraping de la page 1 seulement (30 offres)
- **Maintenant**: Scraping de toutes les pages (117 offres au total)
- **Impact**: +290% d'offres récupérées

### 2. **Indicateurs Visuels dans le Frontend** (NOUVEAU ✅)

#### **Pendant le scraping:**
- ⏳ Message bleu: "Scraping en cours... Veuillez patienter"
- 🔄 Icône tournante animée
- Bouton grisé et désactivé

#### **En cas de succès:**
- ✅ Message vert avec le nombre d'offres ajoutées
- Exemple: "✅ Succès! 101 nouvelles offres ajoutées sur 117 trouvées"
- ℹ️ Si 0 nouvelles offres: "Aucune nouvelle offre (déjà en base)"

#### **En cas d'erreur:**
- ❌ Message rouge avec détails de l'erreur
- Exemple: "❌ Erreur: Impossible de se connecter au serveur"

### 3. **Console de Debug** (NOUVEAU ✅)
Logs détaillés dans la console navigateur (F12):
- 📝 Form submitted
- ✅ Validation OK
- 🚀 handleScrape appelé
- 📤 Envoi requête POST
- ✅ Réponse reçue

## 📊 Dates Disponibles sur MediaCongo

**État actuel du site (26 déc 2025):**
```
Page 1: 24 décembre 2025 (30 offres) - FHI 360, Equity BCDC
Page 2: 20-22 décembre 2025 (30 offres)
Page 3: 16 décembre 2025 (30 offres)
Page 4: 11 décembre 2025 (27 offres)
Total: 117 offres d'emploi RDC
```

**⚠️ IMPORTANT**: Il n'y a AUCUNE offre publiée les 25-26 décembre!

## 🚀 Comment Utiliser

### Via l'Interface Web (RECOMMANDÉ)

1. **Accéder à la page**
   ```
   http://localhost:8080/mediacongo
   ```

2. **Se connecter si nécessaire**
   - Login/mot de passe

3. **Remplir le formulaire**
   - **Date début**: `2025-12-01` (format YYYY-MM-DD)
   - **Date fin**: `2025-12-31`
   - **Limite**: `200` (optionnel, défaut: 100)

4. **Cliquer sur "Lancer le Scraping"**

5. **Observer les indicateurs**
   - ⏳ Message bleu: scraping en cours (2-30 secondes)
   - ✅ Message vert: succès + nombre d'offres
   - ❌ Message rouge: erreur

### Via API Directe

```bash
# Lancer le scraping
curl -X POST http://localhost:8080/api/mediacongo/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "limit": 200
  }'

# Voir les offres en attente
curl http://localhost:8080/api/mediacongo/api/pending?limit=100

# Voir les offres validées
curl http://localhost:8080/api/mediacongo/api/validated?limit=100

# Valider une offre
curl -X POST http://localhost:8080/api/mediacongo/api/validate/OEM42731

# Supprimer toutes les offres en attente
curl -X POST http://localhost:8080/api/mediacongo/api/delete_all
```

## 🔍 Comprendre les Résultats

### Cas 1: "X nouvelles offres ajoutées"
✅ **C'est un succès!**
- Des nouvelles offres ont été trouvées et ajoutées
- Elles apparaissent dans "Offres en Attente"

### Cas 2: "Aucune nouvelle offre (déjà en base)"
ℹ️ **C'est normal!**
- Le scraping a fonctionné
- Des offres ont été trouvées sur le site
- Mais elles sont déjà dans votre base de données
- Le système évite les doublons

### Cas 3: "0 offres trouvées"
⚠️ **Vérifiez les dates!**
- Aucune offre n'existe pour cette période sur MediaCongo
- Exemple: dates 25-26 déc → aucune offre à ces dates
- Solution: élargir la plage de dates

## 🐛 Debugging

### Si le bouton ne réagit pas:

1. **Vider le cache navigateur**
   ```
   Ctrl + Shift + R (Windows)
   Cmd + Shift + R (Mac)
   ```

2. **Ouvrir la console (F12)**
   - Onglet "Console"
   - Cherchez les messages 📝 🚀 📤
   - Y a-t-il des erreurs rouges?

3. **Vérifier l'onglet Network**
   - F12 → Network
   - Cliquer "Lancer le Scraping"
   - Cherchez: POST `/api/mediacongo/api/scrape`
   - Statut: 200 = OK, 500 = erreur serveur, 404 = route introuvable

### Messages d'erreur courants:

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Impossible de se connecter au serveur" | Backend arrêté | `docker-compose up -d backend` |
| "404 Not Found" | Route incorrecte | Vérifier proxy nginx |
| "0 offres trouvées" | Dates hors plage | Utiliser dates 11-24 déc |
| "Aucune nouvelle offre" | Déjà en base | Normal, déduplication active |

## 📈 Statistiques

**Volume de données MediaCongo:**
- Total disponible: **117 offres**
- Répartition: 4 pages
- Dates: 11-24 décembre 2025
- Mise à jour: quotidienne (nouvelles offres)

**État de votre base:**
```bash
# Vérifier
curl http://localhost:8080/api/mediacongo/api/pending?limit=1
curl http://localhost:8080/api/mediacongo/api/validated?limit=1
```

## 🎯 Workflow Recommandé

1. **Scraping quotidien**
   - Date début: il y a 7 jours
   - Date fin: aujourd'hui
   - Résultat: nouvelles offres ajoutées

2. **Validation des offres**
   - Parcourir "Offres en Attente"
   - Cliquer ✅ pour valider
   - Envoi automatique vers AppelOffres (source_id=337)

3. **Export Excel** (si implémenté)
   - Bouton export dans l'interface
   - Téléchargement fichier .xlsx

## 🔐 Configuration

**API AppelOffres:**
- Email: `oumayma.dahmani@tunipages.tn`
- Source ID: `337` (MediaCongo RDC)
- Avis ID: `2` (Appel d'offres)

**Collections MongoDB:**
- `pending_tenders_mediacongo` - Offres en attente
- `tenders_mediacongo` - Offres validées

## 📞 Support

**Problèmes fréquents résolus:**
- ✅ Pagination manquante → Corrigé (4 pages)
- ✅ Pas d'indicateur visuel → Ajouté (messages clairs)
- ✅ Filtrage par date → Fonctionne correctement
- ✅ Déduplication → Active (évite doublons)

**Fichiers de test:**
- `test_mediacongo_frontend.html` - Test HTML simple
- `backend/test_mediacongo_dates.py` - Vérifier dates du site
- `backend/test_all_pages.py` - Tester toutes les pages

## 🎉 Tout Fonctionne Maintenant!

- ✅ Pagination complète (117 offres)
- ✅ Indicateurs visuels clairs
- ✅ Messages de succès/erreur
- ✅ Console de debug
- ✅ Filtrage par date
- ✅ Déduplication automatique

**Date de mise à jour:** 26 décembre 2025
**Version:** 2.0 (avec pagination et feedback visuel)
