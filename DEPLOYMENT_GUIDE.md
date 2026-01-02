# 📦 Guide de Déploiement Complet - Système d'Extraction d'Appels d'Offres

## 🎯 Ce Guide Contient TOUT pour l'Hébergement

Votre hébergeur n'a qu'à suivre ces étapes. Tous les scripts et configurations sont prêts!

---

## 📋 Prérequis sur le Serveur

- Docker + Docker Compose installés
- Ports disponibles: 5432 (PostgreSQL), 5000-5018 (APIs), 8080-8081 (Frontend + pgAdmin)
- 4GB RAM minimum
- 20GB espace disque

---

## 🚀 Déploiement en 3 Étapes

### Étape 1: Cloner le Projet

```bash
git clone https://gitlab.com/tunipages-nac/extractionauto.git
cd extractionauto
git checkout development
```

### Étape 2: Lancer Docker Compose

```bash
docker-compose up -d
```

**C'EST TOUT!** 🎉

Le fichier `backend/init.sql` va automatiquement:
- ✅ Créer toutes les 14 tables PostgreSQL
- ✅ Créer tous les index pour la performance
- ✅ Créer les triggers pour updated_at automatique
- ✅ Créer une vue globale `pending_tenders_all`

### Étape 3: Vérifier que tout fonctionne

```bash
# Vérifier les conteneurs
docker ps

# Vérifier les logs
docker-compose logs -f
```

---

## 🗄️ Structure de la Base de Données PostgreSQL

### Connexion PostgreSQL

```
Host: localhost (ou IP du serveur)
Port: 5432
Database: tenders_db
User: tender_user
Password: tender_password_2024
```

### Tables Créées Automatiquement (14 tables)

#### 1. **tenders_benin** - Appels d'offres Bénin
```sql
Colonnes principales:
- ref (VARCHAR) - Référence unique
- description (TEXT)
- date_publication (VARCHAR)
- date_limite_depot (VARCHAR)
- autorite_contractante (TEXT)
- lien_pdf (TEXT)
- status (VARCHAR) - 'pending' ou 'validated'
```

#### 2. **tenders_mediacongo** - RDC MediaCongo
```sql
Colonnes principales:
- reference (VARCHAR) - Référence unique
- description (TEXT)
- publication_date (TIMESTAMP)
- expiration_date (TIMESTAMP)
- promoter (TEXT)
- source_id (INTEGER) - 337
- external_url (TEXT)
- status (VARCHAR)
```

#### 3. **tenders_relief** - ReliefWeb
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- expiration_date (TIMESTAMP)
- promoter (TEXT)
- source_id (INTEGER) - 1716
- country (VARCHAR)
- status (VARCHAR)
```

#### 4. **tenders_tuneps** - TUNEPS Tunisie
```sql
Colonnes principales:
- reference (VARCHAR)
- title (TEXT)
- description (TEXT)
- publication_date (TIMESTAMP)
- expiration_date (TIMESTAMP)
- promoter (TEXT)
- source_id (INTEGER) - 817
- batches (JSONB) - Lots en JSON
- status (VARCHAR)
```

#### 5. **tenders_tuneps_ao** - TUNEPS Appels d'Offres
```sql
Structure identique à tenders_tuneps
```

#### 6. **tenders_armp** - Madagascar ARMP
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- expiration_date (TIMESTAMP)
- promoter (TEXT)
- country (VARCHAR) - 'Madagascar'
- status (VARCHAR)
```

#### 7. **tenders_pnud** - UNDP/PNUD
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- promoter (TEXT)
- country (VARCHAR)
- status (VARCHAR)
```

#### 8. **tenders_banque** - Banque Mondiale
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- promoter (TEXT)
- source_id (INTEGER) - 1464
- borrower (VARCHAR)
- status (VARCHAR)
```

#### 9. **tenders_boamp** - BOAMP France
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- promoter (TEXT)
- business_sector (VARCHAR)
- country (VARCHAR) - 'France'
- status (VARCHAR)
```

#### 10. **tenders_haicop** - HAICOP Tunisie
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- promoter (TEXT)
- source_id (INTEGER) - 279
- status (VARCHAR)
```

#### 11. **tenders_expertise** - Expertise France
```sql
Colonnes principales:
- reference (VARCHAR)
- description (TEXT)
- publication_date (TIMESTAMP)
- promoter (TEXT)
- country (VARCHAR)
- status (VARCHAR)
```

#### 12. **tenders_ppda** - PPDA Malawi
```sql
Colonnes principales:
- reference (VARCHAR)
- title (TEXT)
- description (TEXT)
- promoter (TEXT)
- publication_date (DATE)
- expiration_date (DATE)
- document_url (TEXT)
- country (VARCHAR) - 'Malawi'
- status (VARCHAR)
```

#### 13. **jobs_niger** - Emplois Niger
```sql
Colonnes principales:
- reference (VARCHAR)
- title (TEXT)
- description (TEXT)
- promoter (TEXT)
- publication_date (DATE)
- expiration_date (DATE)
- location (VARCHAR)
- url (TEXT)
- country (VARCHAR) - 'Niger'
- status (VARCHAR)
```

#### 14. **jobs_somalia** - Emplois Somalie
```sql
Colonnes principales:
- reference (VARCHAR)
- title (TEXT)
- description (TEXT)
- promoter (TEXT)
- publication_date (DATE)
- location (VARCHAR)
- url (TEXT)
- country (VARCHAR) - 'Somalia'
- status (VARCHAR)
```

---

## 🔗 URLs d'Accès

Après déploiement, les URLs suivantes seront disponibles:

### Frontend (Interface Utilisateur)
- **URL principale**: http://VOTRE_IP:8080
- Login par défaut configuré dans le frontend

### APIs Backend (Scrapers)
- **API Node.js principale**: http://VOTRE_IP:5000
- **BOAMP**: http://VOTRE_IP:5003/api
- **TUNEPS**: http://VOTRE_IP:5001/api
- **TUNEPS AO**: http://VOTRE_IP:5005/api
- **PNUD**: http://VOTRE_IP:5006/api
- **ARMP**: http://VOTRE_IP:5007/api
- **Banque Mondiale**: http://VOTRE_IP:5010/api
- **HAICOP**: http://VOTRE_IP:5011/api
- **BENIN**: http://VOTRE_IP:5012/api
- **Expertise France**: http://VOTRE_IP:5013/api
- **GIZ**: http://VOTRE_IP:5014/api
- **Relief**: http://VOTRE_IP:5015/api
- **MediaCongo**: http://VOTRE_IP:5016/api
- **PPDA Malawi**: http://VOTRE_IP:5017/api
- **Niger Emploi**: http://VOTRE_IP:5018/api
- **Somalia Jobs**: http://VOTRE_IP:5019/api

### Base de Données
- **PostgreSQL**: VOTRE_IP:5432
- **pgAdmin** (interface web): http://VOTRE_IP:8081
  - Email: admin@admin.com
  - Password: admin

---

## 🔧 Configuration Environnement

Le fichier `docker-compose.yml` contient toute la configuration nécessaire:

### Variables d'Environnement PostgreSQL
```yaml
POSTGRES_USER: tender_user
POSTGRES_PASSWORD: tender_password_2024
POSTGRES_DB: tenders_db
```

### Variables d'Environnement Backend
```yaml
DB_HOST: postgres
DB_PORT: 5432
DB_NAME: tenders_db
DB_USER: tender_user
DB_PASSWORD: tender_password_2024

# API appeloffres.net
API_BASE_URL: https://be.appeloffres.net/api
API_EMAIL: mariem.bousalem@tunipages.tn
API_PASSWORD: L96BhA6ODugl

# IDs par défaut
DEFAULT_SOURCE_ID: 817
DEFAULT_PROMOTER_ID: 223472
DEFAULT_AVIS_ID: 2
DEFAULT_PAYS_ID: 219
DEFAULT_CURRENCY_ID: 111
```

---

## 📊 Fonctionnalités du Système

### 1. Extraction Automatique
Chaque scraper extrait automatiquement les offres/emplois depuis sa source:
- **Filtrage par date**: Date de publication exacte (aujourd'hui par défaut)
- **Pagination**: Nombre de pages configurable
- **Déduplication**: Vérifie les références existantes

### 2. Validation et Envoi API
Après extraction, les offres peuvent être:
- **Validées**: Changement de status 'pending' → 'validated'
- **Envoyées vers API**: Intégration avec https://be-stg.appeloffres.net/api
  - Création automatique des promoteurs
  - Envoi des tenders/jobs
  - Stockage de l'api_id retourné

### 3. Gestion des Promoteurs
Chaque scraper crée automatiquement les promoteurs:
```javascript
{
  name: "Nom du promoteur",
  companyName: "Nom du promoteur",
  countryId: ID_PAYS,
  address: {
    streetAddress: "Ville",
    city: "Ville",
    countryId: ID_PAYS
  },
  phoneNumber: "+XXX-X-XXXXXX",
  email: "promoteur@domain.com",
  type: "public" ou "private"
}
```

---

## 🗂️ Structure du Projet

```
extractionautomatic/
│
├── backend/
│   ├── scripts/              # Scrapers Python Flask
│   │   ├── benin.py         # Port 5012
│   │   ├── mediacongo.py    # Port 5016
│   │   ├── relief.py        # Port 5015
│   │   ├── PPDA.py          # Port 5017
│   │   ├── niger_api.py     # Port 5018
│   │   ├── somalijobs_api.py # Port 5019
│   │   └── ...
│   ├── server.js            # Proxy Node.js
│   ├── init.sql             # ⭐ Script PostgreSQL initial
│   ├── Dockerfile
│   └── requirements.txt
│
├── auth-frontend/
│   ├── src/
│   │   ├── pages/           # Pages React
│   │   │   ├── mediacongo.js
│   │   │   ├── relief.js
│   │   │   ├── benin.js
│   │   │   ├── ppda.js
│   │   │   ├── niger.js
│   │   │   ├── somalia.js
│   │   │   └── ...
│   │   └── App.js
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml       # ⭐ Configuration Docker complète
├── DEPLOYMENT_GUIDE.md      # ⭐ Ce fichier
└── POSTGRESQL_SCHEMAS.md    # Documentation des schémas
```

---

## 🛠️ Commandes Utiles

### Gestion des Conteneurs

```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Redémarrer un service spécifique
docker restart backend_tenders

# Voir les logs
docker-compose logs -f backend

# Reconstruire sans cache (après changement code)
docker-compose build --no-cache
docker-compose up -d
```

### Accès PostgreSQL

```bash
# Via Docker
docker exec -it postgres_tenders psql -U tender_user -d tenders_db

# Voir toutes les tables
\dt

# Compter les offres par table
SELECT
  'tenders_benin' as table, COUNT(*) as count FROM tenders_benin
UNION ALL
SELECT 'tenders_mediacongo', COUNT(*) FROM tenders_mediacongo
UNION ALL
SELECT 'tenders_relief', COUNT(*) FROM tenders_relief
UNION ALL
SELECT 'jobs_niger', COUNT(*) FROM jobs_niger
UNION ALL
SELECT 'jobs_somalia', COUNT(*) FROM jobs_somalia;

# Voir les offres pending
SELECT * FROM pending_tenders_all LIMIT 10;
```

### Backup Base de Données

```bash
# Backup complet
docker exec postgres_tenders pg_dump -U tender_user tenders_db > backup_$(date +%Y%m%d).sql

# Restaurer un backup
docker exec -i postgres_tenders psql -U tender_user tenders_db < backup_20260102.sql
```

---

## 🔐 Sécurité en Production

**⚠️ IMPORTANT**: Avant le déploiement en production, changez:

1. **Mot de passe PostgreSQL** dans `docker-compose.yml`:
   ```yaml
   POSTGRES_PASSWORD: NOUVEAU_MOT_DE_PASSE_FORT
   DB_PASSWORD: NOUVEAU_MOT_DE_PASSE_FORT
   ```

2. **Mot de passe pgAdmin**:
   ```yaml
   PGADMIN_DEFAULT_PASSWORD: NOUVEAU_MOT_DE_PASSE
   ```

3. **JWT Secret** (si utilisé):
   ```yaml
   JWT_SECRET: VOTRE_SECRET_TRES_FORT
   ```

4. **Firewall**: Limitez l'accès aux ports sensibles
   - PostgreSQL (5432): Seulement réseau interne Docker
   - pgAdmin (8081): Seulement IP admin

---

## 📞 Support

Pour toute question sur le déploiement:
- Vérifiez les logs: `docker-compose logs -f`
- Vérifiez l'état: `docker ps -a`
- GitLab: https://gitlab.com/tunipages-nac/extractionauto

---

## ✅ Checklist de Déploiement

- [ ] Docker et Docker Compose installés
- [ ] Repository cloné et branch development checkouté
- [ ] Ports 5432, 5000-5019, 8080-8081 disponibles
- [ ] `docker-compose up -d` exécuté avec succès
- [ ] Tous les conteneurs running: `docker ps`
- [ ] Frontend accessible: http://IP:8080
- [ ] pgAdmin accessible: http://IP:8081
- [ ] PostgreSQL accessible via pgAdmin
- [ ] Tables créées: 14 tables visibles dans pgAdmin
- [ ] Tests de scraping fonctionnels

---

**🎉 Voilà! Tout est prêt pour l'hébergement!**

L'hébergeur n'a qu'à exécuter `docker-compose up -d` et tout sera configuré automatiquement grâce au fichier `backend/init.sql`.
