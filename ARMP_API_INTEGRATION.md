# ✅ ARMP - Intégration API AppelOffres

## 🎯 Objectif

Configurer le scraper ARMP (Madagascar) pour qu'il:
1. ✅ Utilise 2 collections MongoDB (pending + validated)
2. ✅ Vérifie les doublons avant d'ajouter en pending
3. ✅ Envoie vers l'API AppelOffres lors de la validation
4. ✅ Utilise `source_id = 410` (ARMP Madagascar)

## 🔧 Modifications effectuées

### Fichier: `backend/scripts/armp_flask.py`

#### 1. Configuration API AppelOffres (lignes 40-54)

**Ajouté**:
```python
# API AppelOffres Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"

# ARMP utilise le compte de Mariem Bousalem
EMAIL = os.getenv("API_EMAIL", "mariem.bousalem@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "L96BhA6ODugl")

# ARMP source_id = 410
DEFAULT_SOURCE_ID_ARMP = 410
DEFAULT_AVIS_ID = int(os.getenv("DEFAULT_AVIS_ID", "1"))
PAYS_MADAGASCAR = 123  # Madagascar country_id
```

#### 2. Initialisation session API (lignes 112-137)

**Ajouté**:
```python
self.session_appeloffres = requests.Session()  # Session séparée pour API
self.access_token = None
self.promoters_cache = {}  # Cache des promoteurs {nom: id}
```

#### 3. Fonction `get_api_token()` (lignes 560-585)

Authentification auprès de l'API AppelOffres:
```python
def get_api_token(self):
    """Obtenir le token d'authentification de l'API AppelOffres"""
    if self.access_token:
        return True

    try:
        login_data = {"email": EMAIL, "password": API_PASSWORD}
        response = self.session_appeloffres.post(
            LOGIN_ENDPOINT,
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("accessToken")
            if self.access_token:
                logger.info(f"✅ Token API obtenu avec succès pour {EMAIL}")
                return True
    ...
```

#### 4. Fonction `find_or_create_promoter()` (lignes 587-638)

Recherche ou création d'un promoteur dans l'API:
```python
def find_or_create_promoter(self, promoter_name: str):
    """Trouve ou crée un promoteur dans l'API"""
    # Vérifier le cache
    if promoter_name in self.promoters_cache:
        return self.promoters_cache[promoter_name]

    # Rechercher le promoteur
    search_response = self.session_appeloffres.get(
        f"{PROMOTER_ENDPOINT}?name={promoter_name}",
        headers=search_headers,
        timeout=10
    )

    # Si trouvé, retourner l'ID
    if promoters and len(promoters) > 0:
        promoter_id = promoters[0].get('id')
        self.promoters_cache[promoter_name] = promoter_id
        return promoter_id

    # Sinon, créer le promoteur
    create_response = self.session_appeloffres.post(...)
    ...
```

#### 5. Fonction `send_to_appeloffres()` (lignes 640-703)

Envoi de l'offre validée vers l'API:
```python
def send_to_appeloffres(self, offre: OffreARMP):
    """Envoie une offre validée vers l'API AppelOffres"""
    # Authentification
    if not self.get_api_token():
        return False

    # Récupérer le promoteur
    promoter_id = self.find_or_create_promoter(offre.promoteur)

    # Préparer les données
    tender_data = {
        "sourceId": DEFAULT_SOURCE_ID_ARMP,  # 410
        "avisId": DEFAULT_AVIS_ID,
        "reference": offre.reference,
        "description": offre.description,
        "publicationDate": offre.date_debut,
        "expirationDate": offre.date_limite,
        "promoterId": promoter_id,
        "type": "public",
        "nature": "public",
        "addresses": [{"countryId": PAYS_MADAGASCAR}],  # 123
        "batches": [{"activitiesIds": [], "title": offre.description[:100], "deposit": "0"}],
        ...
    }

    # Envoyer vers l'API
    response = self.session_appeloffres.post(TENDER_ENDPOINT, ...)
    return response.status_code in [200, 201]
```

#### 6. Fonction `validate_offre()` modifiée (lignes 722-766)

**Avant**:
```python
def validate_offre(self, reference: str):
    # Récupérer l'offre pending
    pending_doc = self.pending_tenders_collection.find_one(...)

    # Insérer dans validated
    self.tenders_collection.insert_one(pending_doc)

    # Supprimer de pending
    self.pending_tenders_collection.delete_one(...)
```

**Après**:
```python
def validate_offre(self, reference: str):
    """Valide une offre ET l'envoie vers l'API AppelOffres"""
    # Récupérer l'offre pending
    pending_doc = self.pending_tenders_collection.find_one(...)

    # Créer l'objet OffreARMP
    offre = OffreARMP(**pending_doc)

    # ✅ ENVOYER VERS L'API APPELOFFRES
    api_success = self.send_to_appeloffres(offre)

    if not api_success:
        return {"success": False, "message": "Échec de l'envoi vers l'API AppelOffres"}

    # Si l'envoi API réussit, sauvegarder dans validated
    self.tenders_collection.insert_one(pending_doc)

    # Supprimer de pending
    self.pending_tenders_collection.delete_one(...)

    logger.info(f"✅ Offre {reference} validée et envoyée à AppelOffres avec succès")
    return {"success": True, "message": "Offre validée et envoyée avec succès"}
```

## 🔍 Vérifications des doublons

Le code vérifie déjà les doublons (lignes 516-525):

```python
# Vérifier si existe déjà dans validated
if reference in self.existing_offres_set:
    logger.info(f"⏭️ {reference} déjà validé, skip")
    continue

# Vérifier si déjà en pending
existing_pending = self.pending_tenders_collection.find_one({"reference": reference})
if existing_pending:
    logger.info(f"⏭️ {reference} déjà en pending, skip")
    continue
```

## 📊 Flux de données

```
┌─────────────────┐
│  Site ARMP      │
│  (Madagascar)   │
└────────┬────────┘
         │
         │ Scraping
         ▼
┌─────────────────────────┐
│  pending_tenders_armp   │ ◄─── ✅ Vérification doublons
│  (MongoDB)              │
└────────┬────────────────┘
         │
         │ Validation (UI)
         ▼
┌─────────────────────────┐
│  send_to_appeloffres()  │
│  - Login API            │
│  - Créer promoteur      │
│  - Envoyer tender       │
└────────┬────────────────┘
         │
         │ Si succès
         ▼
┌─────────────────────────┐       ┌──────────────────────┐
│  tenders_armp           │       │  API AppelOffres     │
│  (MongoDB - validated)  │       │  Source ID: 410      │
└─────────────────────────┘       └──────────────────────┘
```

## 🚀 Utilisation

### Via l'interface web

1. Allez sur: `http://localhost:8080/armp`
2. Lancez un scraping (bouton "Lancer le scraping")
3. Les offres apparaissent dans **"Offres en attente"** (pending)
4. Cliquez sur le bouton ✅ **Valider** pour une offre
5. L'offre est envoyée vers AppelOffres avec `source_id=410`
6. Si succès, l'offre passe dans **"Offres validées"**

### Via API

**Lancer le scraping**:
```bash
curl -X POST http://localhost:8080/api/armp/api/scrape
```

**Voir les offres en attente**:
```bash
curl http://localhost:8080/api/armp/api/pending?page=1&limit=10
```

**Valider une offre**:
```bash
curl -X POST http://localhost:8080/api/armp/api/validate/REF-12345
```

Réponse en cas de succès:
```json
{
  "success": true,
  "message": "Offre validée et envoyée avec succès"
}
```

**Voir les offres validées**:
```bash
curl http://localhost:8080/api/armp/api/validated
```

## 🔐 Configuration

### Identifiants API

- **Email**: `mariem.bousalem@tunipages.tn`
- **Password**: `L96BhA6ODugl`
- **Source ID**: `410` (ARMP Madagascar)
- **Avis ID**: `1` (Appel d'offres)
- **Pays ID**: `123` (Madagascar)

### Variables d'environnement

```bash
API_BASE_URL=https://be.appeloffres.net/api
API_EMAIL=mariem.bousalem@tunipages.tn
API_PASSWORD=L96BhA6ODugl
DEFAULT_AVIS_ID=1
```

## 📝 Collections MongoDB

| Collection | Description | Contenu |
|------------|-------------|---------|
| `pending_tenders_armp` | Offres en attente | Offres scrapées non validées |
| `tenders_armp` | Offres validées | Offres envoyées à AppelOffres |

## ✅ Tests

### 1. Tester l'authentification API
```bash
curl -X POST https://be.appeloffres.net/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"mariem.bousalem@tunipages.tn","password":"L96BhA6ODugl"}'
```

### 2. Vérifier le statut ARMP
```bash
curl http://localhost:8080/api/armp/api/status
```

Réponse attendue:
```json
{
  "message": "Aucun scraping en cours",
  "pending_count": 147,
  "processing": false
}
```

### 3. Récupérer les sources avec ID=410
```bash
curl -X GET "https://be.appeloffres.net/api/sources/410" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🎉 Conclusion

Le scraper ARMP est maintenant complètement intégré avec l'API AppelOffres:

- ✅ **2 collections** (pending + validated)
- ✅ **Vérification doublons** avant ajout en pending
- ✅ **Envoi automatique** vers AppelOffres lors de la validation
- ✅ **Source ID 410** pour ARMP Madagascar
- ✅ **Compte Mariem Bousalem** pour l'authentification

Les offres validées depuis l'interface web sont automatiquement envoyées vers l'API AppelOffres avec le bon source_id !

Date de mise à jour: 24 décembre 2025
