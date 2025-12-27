# 🇧🇯 Guide Complet - Scraper Marchés Publics Bénin

## ✅ Améliorations Apportées

### 1. **Correction de l'API Endpoint** (RÉSOLU ✅)
- **Avant**: Frontend appelait `/scrape-tunisie` sur `http://localhost:5012`
- **Maintenant**: Frontend appelle `/api/scrape` via proxy nginx `/api/benin/api`
- **Résultat**: Communication frontend-backend fonctionnelle

### 2. **Indicateurs Visuels dans le Frontend** (NOUVEAU ✅)

#### **Pendant le scraping:**
- ⏳ Message bleu: "Scraping en cours... Veuillez patienter (plusieurs minutes pour Selenium)"
- 🔄 Icône tournante animée
- Bouton grisé et désactivé

#### **En cas de succès:**
- ✅ Message avec le nombre d'offres extraites
- Exemple: "✅ Succès! 15 offres extraites"
- Rafraîchissement automatique des données

#### **En cas d'erreur:**
- ❌ Message rouge avec détails de l'erreur
- Logs console pour debugging (F12)

### 3. **Console de Debug** (NOUVEAU ✅)
Logs détaillés dans la console navigateur (F12):
- 🚀 handleScrape appelé
- 📤 Envoi requête POST
- 📦 Payload avec nombre de pages
- ✅ Réponse reçue

## 🌐 À Propos du Scraper Bénin

**Marchés Publics Bénin** est la plateforme officielle des appels d'offres du Bénin:
- URL: https://www.marches-publics.bj
- Type: Appels d'offres publics béninois
- Méthode: **Selenium** (scraping avec navigateur headless)
- Framework: Chrome WebDriver + BeautifulSoup

**Particularité**: Utilise Selenium car le site est en Angular avec du contenu dynamique JavaScript.

## 🚀 Comment Utiliser

### Via l'Interface Web (RECOMMANDÉ)

1. **Accéder à la page**
   ```
   http://localhost:8080/benin
   ```

2. **Remplir le formulaire**
   - **Date Filtre**: Laisser vide ou "ALL" (le filtrage par date n'est pas encore implémenté)
   - **Nombre Max de Pages**: `3` (défaut recommandé, max 10)

   ⚠️ **IMPORTANT**: Le scraping Selenium est **très lourd**:
   - Chaque page prend ~20-30 secondes
   - 3 pages = 1-2 minutes minimum
   - 10 pages = 5-10 minutes
   - Utilise beaucoup de mémoire

3. **Cliquer sur "Lancer le Scraping BÉNIN"**

4. **Observer les indicateurs**
   - ⏳ Message bleu: scraping en cours (patience!)
   - 🖥️ Console (F12): Logs `[BENIN]` montrent la progression
   - ✅ Alert succès: nombre d'offres extraites (après 5-10 min)
   - ❌ Message rouge: erreur éventuelle

5. **⚠️ NE PAS RAFRAÎCHIR LA PAGE pendant le scraping!**
   - Si tu rafraîchis, l'indicateur bleu disparaît
   - **MAIS** le scraping continue dans le backend
   - Attends 5-10 minutes puis clique "Rafraîchir" en haut de page
   - Les nouvelles offres apparaîtront

### Comportement Important: Scraping en Arrière-Plan

**Scenario 1: Attendre sans rafraîchir (RECOMMANDÉ)**
```
1. Clique "Lancer le Scraping BÉNIN"
2. NE FERME PAS / NE RAFRAÎCHIS PAS la page
3. Tu vois l'indicateur bleu ⏳
4. Attends 5-10 minutes (lis un café ☕)
5. Alert de succès apparaît: "✅ Succès! X offres extraites"
6. Les offres apparaissent automatiquement
```

**Scenario 2: Rafraîchir ou fermer la page**
```
1. Clique "Lancer le Scraping BÉNIN"
2. Tu vois l'indicateur bleu ⏳
3. Tu rafraîchis la page → L'indicateur disparaît
4. MAIS Selenium continue de tourner dans le backend!
5. Après 5-10 minutes, reviens sur la page
6. Clique le bouton "Rafraîchir" 🔄 en haut
7. Les nouvelles offres apparaissent dans "Offres en Attente"
```

**Comment savoir si le scraping est terminé?**
```bash
# Vérifie le nombre d'offres en attente
curl http://localhost:5012/api/health

# Si "pending" augmente, le scraping a fonctionné!
```

6. **Voir les résultats**
   - Section "Offres en Attente BÉNIN"
   - 38+ offres déjà disponibles
   - Utilise la recherche pour filtrer

### Via API Directe

```bash
# Lancer le scraping (3 pages)
curl -X POST http://localhost:8080/api/benin/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 3}'

# Health check
curl http://localhost:8080/api/benin/api/health

# Voir les offres en attente
curl http://localhost:8080/api/benin/api/pending-all

# Valider une offre (pas encore implémenté avec AppelOffres API)
curl -X POST http://localhost:8080/api/benin/api/validate/S_SN_105830

# Supprimer une offre
curl -X DELETE "http://localhost:8080/api/benin/api/delete/S_SN_105830"
```

## 🔍 Structure des Données Extraites

Chaque offre contient:

| Champ | Description | Exemple |
|-------|-------------|---------|
| **Ref** | Référence unique | `S_SN_105830` |
| **Description** | Titre/objet du marché | `Recrutement d'une structure de gardiennage...` |
| **Autorite_contractante** | Autorité contractante | `Mairie de Gogounou` |
| **Date_publication** | Date de publication | `09-12-2025` |
| **Date_limite_depot** | Date limite de dépôt | `22-01-2026 à 10H00` |
| **Date_ouverture_offres** | Date d'ouverture | `22-01-2026 à 10H30` |
| **Delai** | Délai en jours | `32 jours` |
| **Lieu_acquisition** | Lieu de retrait du dossier | `Secrétariat de la PRMP...` |
| **Lien_PDF** | Lien vers le PDF | `https://bi.marches-publics.bj/...` |

## 🔧 Configuration Technique

### Backend (benin.py)
- **Port**: 5012
- **Framework**: Flask + Selenium
- **Database**: MongoDB
  - Database: `marches_publics_benin_scraping`
  - Collection: `appels_offres_scraping`
- **Scraping Method**: Selenium WebDriver (Chrome headless)
- **Pagination**: Boutons "Suivant" dans l'interface web

### Selenium Configuration
```python
chrome_options.add_argument('--headless')  # Mode invisible
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
```

### Extraction Process
1. Navigate vers `https://www.marches-publics.bj/appels-doffres`
2. Attend le chargement complet (Angular)
3. Trouve les cartes `<mat-card>`
4. Pour chaque carte:
   - Extrait date limite depuis l'en-tête vert
   - Extrait délai, référence, description
   - Extrait autorité contractante
   - Extrait dates de publication et ouverture
   - Extrait lieu d'acquisition
   - Extrait lien PDF
5. Clique "Suivant" pour page suivante
6. Répète jusqu'à max_pages ou dernière page

## ⚠️ Limitations et Particularités

### Limitations Actuelles
1. **Pas d'intégration AppelOffres API**
   - Les offres vont uniquement dans MongoDB
   - Pas encore de validation vers AppelOffres
   - Nécessite adaptation du format (source_id, promoter_id, etc.)

2. **Filtrage par date non implémenté**
   - Le paramètre `date_filtre` est ignoré
   - Extrait toujours les offres les plus récentes
   - Possible d'ajouter filtrage post-extraction

3. **Performance Selenium**
   - Très lent (20-30 sec/page)
   - Consomme beaucoup de mémoire
   - Chrome doit être installé dans le container Docker

4. **Extraction imparfaite**
   - Autorité contractante parfois vide
   - Description peut être incomplète
   - Structure HTML Angular complexe

### Avantages
✅ Extrait du contenu JavaScript dynamique
✅ Gère la pagination automatique
✅ Extrait les PDFs
✅ Déduplication par référence
✅ 38+ offres déjà disponibles

## 📊 Statistiques

**État actuel:**
- **38 offres** en attente dans MongoDB
- **0 offres** validées (pas d'intégration API)
- Données de **décembre 2025 - janvier 2026**
- Couverture: Tout le Bénin

**Exemples de marchés:**
- Recrutement de structures de gardiennage
- Fourniture de matériel informatique
- Travaux de construction
- Services de maintenance
- Ouverture de couloirs de pâturage

## 🐛 Debugging

### Si le scraping échoue:

1. **Vérifier que Chrome est installé dans le container**
   ```bash
   docker exec backend_tenders which chromium
   # Doit retourner: /usr/bin/chromium
   ```

2. **Vérifier les logs Selenium**
   ```bash
   docker logs backend_tenders | grep BENIN
   docker logs backend_tenders | grep Selenium
   ```

3. **Tester manuellement**
   ```bash
   docker exec -it backend_tenders python
   >>> from scripts.benin import MarchesPublicsBeninScraper
   >>> scraper = MarchesPublicsBeninScraper(headless=True)
   >>> scraper.setup_driver()
   >>> scraper.driver.get("https://www.marches-publics.bj/appels-doffres")
   ```

### Messages d'erreur courants:

| Erreur | Cause | Solution |
|--------|-------|----------|
| "ChromeDriver not found" | Chrome non installé | Vérifier Dockerfile (chromium installé) |
| "Timeout lors du chargement" | Site lent/indisponible | Augmenter timeout (ligne 74) |
| "Aucun mat-card trouvé" | Structure HTML changée | Vérifier sélecteurs |
| "MongoDB connection failed" | MongoDB arrêté | `docker-compose up -d mongodb` |

## 🔄 Workflow Recommandé

1. **Scraping (1-2 fois par semaine)**
   - Limite: 3-5 pages max
   - Temps: 2-5 minutes
   - Résultat: 10-30 nouvelles offres

2. **Consultation des offres**
   - Voir "Offres en Attente BÉNIN"
   - Filtrer par recherche
   - Pagination (10/25/50/100 par page)

3. **Validation future (à implémenter)**
   - Mapper vers format AppelOffres
   - Créer promoters automatiquement
   - Envoyer vers API avec source_id spécifique

## 🛠️ Pour Développeurs

### Ajouter l'intégration AppelOffres API

Pour envoyer les offres vers AppelOffres, il faudra:

1. **Ajouter la configuration API**
   ```python
   API_BASE_URL = "https://be.appeloffres.net/api"
   EMAIL = "compte@email.com"
   PASSWORD = "motdepasse"
   DEFAULT_SOURCE_ID_BENIN = 1234  # À définir
   ```

2. **Créer la fonction de mapping**
   ```python
   def map_benin_to_appeloffres(offre):
       return {
           "title": offre["Description"][:200],
           "reference": offre["Ref"],
           "publicationDate": parse_benin_date(offre["Date_publication"]),
           "expirationDate": parse_benin_date(offre["Date_limite_depot"]),
           "sourceId": DEFAULT_SOURCE_ID_BENIN,
           "promoterId": get_or_create_promoter(offre["Autorite_contractante"]),
           # ... autres champs
       }
   ```

3. **Ajouter l'endpoint de validation**
   ```python
   @app.route('/api/validate/<reference>', methods=['POST'])
   def validate_offre(reference):
       # Charger l'offre depuis MongoDB
       # Mapper vers format AppelOffres
       # Login API
       # POST vers /tender
       # Marquer comme validée
   ```

## 📞 Support

**Problèmes résolus:**
- ✅ API endpoint mismatch → Corrigé (proxy nginx)
- ✅ Pas d'indicateur visuel → Ajouté (messages clairs)
- ✅ Console debugging → Ajouté (logs détaillés)

**Limitations connues:**
- ⚠️ Pas d'intégration AppelOffres API (en attente)
- ⚠️ Filtrage date non implémenté
- ⚠️ Selenium lent (nature du scraping)

**Fichiers clés:**
- Backend: `backend/scripts/benin.py`
- Frontend: `auth-frontend/src/pages/benin.js`
- CSS: `auth-frontend/src/pages/Benin.css`

## 🎉 Résumé

**Ce qui fonctionne:**
- ✅ Scraping Selenium avec pagination
- ✅ Extraction de 38+ offres
- ✅ Stockage MongoDB
- ✅ Interface frontend moderne
- ✅ Indicateurs visuels (loading/success/error)
- ✅ Console debugging
- ✅ Recherche et pagination frontend
- ✅ Liens PDF cliquables

**Ce qui reste à faire:**
- ⏳ Intégration AppelOffres API
- ⏳ Filtrage par date
- ⏳ Optimisation performance Selenium
- ⏳ Amélioration extraction (autorité contractante)

---

**Date de mise à jour:** 26 décembre 2025
**Version:** 2.0 (avec indicateurs visuels et debug console)

## 🌟 Différences avec autres scrapers

| Aspect | MediaCongo | ReliefWeb | **Bénin** |
|--------|------------|-----------|-----------|
| **Méthode** | HTML (requests) | HTML (requests) | **Selenium (browser)** |
| **Vitesse** | Rapide (secondes) | Rapide (secondes) | **Lent (minutes)** |
| **Pagination** | URL pattern | `?page=N` | **Bouton "Suivant"** |
| **API Integration** | ✅ Oui | ✅ Oui | **❌ Non (encore)** |
| **Source ID** | 337 | 1716 | **À définir** |
| **Type données** | Appels d'offres RDC | Jobs humanitaires | **Marchés publics Bénin** |
| **Framework** | BeautifulSoup | BeautifulSoup | **Selenium + BS4** |
| **Complexité** | Simple | Simple | **Complexe (Angular)** |

---

**Pour toute question, consultez les logs:**
```bash
docker logs backend_tenders --tail 100 | grep -i benin
```
