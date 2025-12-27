# 🌍 Guide Complet - ReliefWeb Scraper

## ✅ Améliorations Apportées

### 1. **Pagination Complète** (RÉSOLU ✅)
- **Avant**: Scraping de la page 1 seulement (20 offres max)
- **Maintenant**: Scraping de toutes les pages disponibles (jusqu'à 200 offres)
- **Méthode**: Pages avec format `?page=0`, `?page=1`, etc.
- **Impact**: +900% d'offres récupérées potentiellement

### 2. **Extraction HTML Corrigée** (RÉSOLU ✅)
- **Problème**: 0 offres extraites malgré 200 articles trouvés
- **Cause**: Sélecteurs HTML incorrects pour la structure ReliefWeb
- **Solution**:
  - Extraction du titre depuis `<h3 class="rw-river-article__title">`
  - Détection du lien via pattern `/job/XXXXXXX`
  - Extraction de l'organisation et du pays depuis les bonnes classes CSS

### 3. **Indicateurs Visuels dans le Frontend** (NOUVEAU ✅)

#### **Pendant le scraping:**
- ⏳ Message bleu: "Scraping en cours... Veuillez patienter"
- 🔄 Icône tournante animée
- Bouton grisé et désactivé

#### **En cas de succès:**
- ✅ Message vert avec le nombre d'offres ajoutées
- Exemple: "✅ Succès! 50 nouvelles offres ajoutées sur 50 trouvées"
- ℹ️ Si 0 nouvelles offres: "Aucune nouvelle offre (déjà en base)"

#### **En cas d'erreur:**
- ❌ Message rouge avec détails de l'erreur
- Exemple: "❌ Erreur: Impossible de se connecter au serveur"

### 4. **Console de Debug** (NOUVEAU ✅)
Logs détaillés dans la console navigateur (F12):
- 📝 Form submitted
- ✅ Validation OK
- 🚀 handleScrape appelé
- 📤 Envoi requête POST
- ✅ Réponse reçue

## 🌐 À Propos de ReliefWeb

**ReliefWeb** est une plateforme humanitaire internationale gérée par l'ONU (OCHA) qui publie:
- Offres d'emploi humanitaires
- Opportunités dans les ONG internationales
- Postes dans les zones de crise et développement
- Missions internationales

**Type de contenu**: Jobs humanitaires (pas des appels d'offres)

## 🚀 Comment Utiliser

### Via l'Interface Web (RECOMMANDÉ)

1. **Accéder à la page**
   ```
   http://localhost:8080/relief
   ```

2. **Se connecter si nécessaire**
   - Login/mot de passe

3. **Remplir le formulaire**
   - **Date début**: `2025-12-01` (format YYYY-MM-DD)
   - **Date fin**: `2025-12-31`
   - **Limite**: `100` (optionnel, défaut: 100, max recommandé: 200)

4. **Cliquer sur "Lancer le Scraping"**

5. **Observer les indicateurs**
   - ⏳ Message bleu: scraping en cours (2-30 secondes)
   - ✅ Message vert: succès + nombre d'offres
   - ❌ Message rouge: erreur

### Via API Directe

```bash
# Lancer le scraping
curl -X POST http://localhost:8080/api/relief/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "limit": 100
  }'

# Voir les offres en attente
curl http://localhost:8080/api/relief/api/pending?limit=100

# Voir les offres validées
curl http://localhost:8080/api/relief/api/validated?limit=100

# Valider une offre
curl -X POST http://localhost:8080/api/relief/api/validate/4192721

# Supprimer toutes les offres en attente
curl -X POST http://localhost:8080/api/relief/api/delete_all
```

## 🔍 Comprendre les Résultats

### Cas 1: "X nouvelles offres ajoutées"
✅ **C'est un succès!**
- Des nouvelles offres ont été trouvées et ajoutées
- Elles apparaissent dans "Offres en Attente"
- Exemple: "50 nouvelles offres ajoutées sur 50 trouvées"

### Cas 2: "Aucune nouvelle offre (déjà en base)"
ℹ️ **C'est normal!**
- Le scraping a fonctionné
- Des offres ont été trouvées sur ReliefWeb
- Mais elles sont déjà dans votre base de données
- Le système évite les doublons via l'ID unique

### Note sur les dates
⚠️ **IMPORTANT**: ReliefWeb ne filtre PAS par date de publication!
- Les dates dans le formulaire sont **ignorées** par ReliefWeb
- Le site affiche toujours les offres les plus récentes en premier
- Le scraping récupère les 200 offres les plus récentes disponibles
- Filtrage futur possible via l'API officielle (nécessite approbation)

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
   - Cherchez: POST `/api/relief/api/scrape`
   - Statut: 200 = OK, 500 = erreur serveur, 404 = route introuvable

### Messages d'erreur courants:

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Impossible de se connecter au serveur" | Backend arrêté | `docker-compose up -d backend` |
| "404 Not Found" | Route incorrecte | Vérifier proxy nginx |
| "0 offres extraites" | Structure HTML changée | Vérifier sélecteurs dans relief.py |
| "Aucune nouvelle offre" | Déjà en base | Normal, déduplication active |

## 📈 Statistiques

**Volume de données ReliefWeb:**
- Total disponible: **~200 offres** (site web actif)
- Répartition: ~10 pages de 20 offres
- Mise à jour: quotidienne (nouvelles offres)
- Couverture: Monde entier (zones humanitaires)

**État de votre base:**
```bash
# Vérifier
curl http://localhost:8080/api/relief/api/pending?limit=1
curl http://localhost:8080/api/relief/api/validated?limit=1
```

## 🎯 Workflow Recommandé

1. **Scraping quotidien**
   - Limite: 100 offres
   - Résultat: nouvelles offres ajoutées

2. **Validation des offres**
   - Parcourir "Offres en Attente"
   - Cliquer ✅ pour valider
   - Envoi automatique vers AppelOffres (source_id=1716)

3. **Gestion des offres**
   - Recherche par pays, organisation, description
   - Export possible (si implémenté)

## 🔐 Configuration

**API AppelOffres:**
- Email: `oumayma.dahmani@tunipages.tn`
- Source ID: `1716` (ReliefWeb)
- Avis ID: `2` (Appel d'offres)
- Type: International

**Collections MongoDB:**
- `pending_tenders_relief` - Offres en attente
- `tenders_relief` - Offres validées

**Structure HTML ReliefWeb:**
```html
<article class="rw-river-article--job">
  <header>
    <p class="rw-entity-country-slug">
      <a>Syria</a>
    </p>
    <h3 class="rw-river-article__title">
      <a href="https://reliefweb.int/job/4192721/...">
        Logistics & Procurement Officer
      </a>
    </h3>
  </header>
  <footer>
    <a class="rw-entity-source__link">Olive Branch</a>
  </footer>
</article>
```

## 🔧 Détails Techniques

### Pagination
- URL pattern: `https://reliefweb.int/jobs?page={N}` (N = 0, 1, 2, ...)
- Pages scrapées: Jusqu'à 10 pages (200 offres max)
- Arrêt automatique: Quand page vide détectée

### Extraction des données
- **Titre**: `<h3 class="rw-river-article__title">`
- **Lien**: Pattern `/job/XXXXXXX` dans les URLs
- **ID**: Extrait du lien (ex: 4192721)
- **Organisation**: `class="rw-entity-source__link"`
- **Pays**: `<p class="rw-entity-country-slug">`

### Limitations
- ⚠️ Scraping HTML (API officielle nécessite approbation)
- ⚠️ Pas de filtrage par date (non supporté par la page web)
- ⚠️ Limite pratique: 200 offres par scraping

## 📞 Support

**Problèmes fréquents résolus:**
- ✅ Pagination manquante → Corrigé (jusqu'à 10 pages)
- ✅ Extraction 0 offres → Corrigé (sélecteurs HTML)
- ✅ Pas d'indicateur visuel → Ajouté (messages clairs)
- ✅ Déduplication → Active (évite doublons)

**Fichiers de test:**
- `test_relief_structure.py` - Vérifier structure HTML du site
- `backend/scripts/relief.py` - Code principal du scraper

## 🎉 Tout Fonctionne Maintenant!

- ✅ Pagination complète (jusqu'à 200 offres)
- ✅ Extraction correcte des données
- ✅ Indicateurs visuels clairs
- ✅ Messages de succès/erreur
- ✅ Console de debug
- ✅ Déduplication automatique
- ✅ Validation et envoi vers AppelOffres API

**Date de mise à jour:** 26 décembre 2025
**Version:** 2.0 (avec pagination et feedback visuel)

## 🌟 Différences avec MediaCongo

| Aspect | MediaCongo | ReliefWeb |
|--------|------------|-----------|
| **Type** | Appels d'offres RDC | Jobs humanitaires internationaux |
| **Pagination** | `page-{N}.html` | `?page={N}` |
| **Filtrage date** | ✅ Supporté | ❌ Non supporté (HTML) |
| **Volume** | 117 offres | ~200 offres |
| **Source ID** | 337 | 1716 |
| **Compte API** | oumayma.dahmani | oumayma.dahmani |
| **Mise à jour** | Quotidienne | Quotidienne |
| **Couverture** | RDC uniquement | Monde entier |

---

**Pour toute question ou problème, référez-vous aux logs Docker:**
```bash
docker logs backend_tenders --tail 100 | grep RELIEF
```
