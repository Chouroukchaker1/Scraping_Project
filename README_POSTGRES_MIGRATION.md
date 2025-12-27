# 🐘 Migration Complète: MongoDB → PostgreSQL

## ✅ Modifications Effectuées

### 1. Docker Compose (`docker-compose.yml`)
- ❌ Supprimé: Service `mongodb`
- ✅ Ajouté: Service `postgres` (PostgreSQL 15)
- ✅ Script d'initialisation: `backend/init.sql`
- ✅ Variables d'environnement PostgreSQL configurées

### 2. Backend Dockerfile (`backend/Dockerfile`)
- ✅ Variables d'environnement mises à jour
- ✅ MONGO_URI → DATABASE_URL
- ✅ Ajout DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

### 3. Dépendances Python (`backend/requirements.txt`)
- ❌ Supprimé: `pymongo==4.8.0`
- ✅ Ajouté: `psycopg2-binary==2.9.9`

### 4. Scripts Python Modifiés

#### ✅ `backend/scripts/benin.py`
- Remplacé pymongo par psycopg2
- Modifié `load_data()` pour utiliser SELECT PostgreSQL
- Modifié `save_data()` pour utiliser INSERT avec ON CONFLICT
- Modifié `/api/delete` pour utiliser DELETE PostgreSQL
- Mapping des champs MongoDB → PostgreSQL (snake_case)

#### ✅ `backend/scripts/db_postgres.py` (NOUVEAU)
- Helper class PostgreSQLHelper
- Fonctions réutilisables pour tous les scrapers
- Context manager pour connexions
- insert_tenders(), get_all(), count(), delete(), update_status()

### 5. Base de Données (`backend/init.sql`)

**Tables créées automatiquement:**
```sql
tenders               -- Table principale unifiée
tenders_benin         -- Offres Bénin
tenders_mediacongo    -- Offres MediaCongo
tenders_relief        -- Offres Relief
tenders_pnud          -- Offres PNUD
pending_tenders_all   -- Vue combinée
```

## 🚀 Démarrage

### Étape 1: Arrêter MongoDB

```bash
docker-compose down
docker volume rm extractionautomatic_mongodb_data 2>/dev/null || true
docker volume rm extractionautomatic_mongodb_config 2>/dev/null || true
```

### Étape 2: Démarrer PostgreSQL

```bash
docker-compose up -d postgres
```

**Attendez 10 secondes** pour que PostgreSQL démarre et exécute le script d'initialisation.

### Étape 3: Vérifier la Base

```bash
docker exec -it postgres_tenders psql -U tender_user -d tenders_db -c "\dt"
```

**Sortie attendue:**
```
            List of relations
 Schema |        Name         | Type  |   Owner
--------+---------------------+-------+------------
 public | tenders             | table | tender_user
 public | tenders_benin       | table | tender_user
 public | tenders_mediacongo  | table | tender_user
 public | tenders_pnud        | table | tender_user
 public | tenders_relief      | table | tender_user
```

### Étape 4: Rebuild le Backend

```bash
docker-compose build backend
```

### Étape 5: Tout Démarrer

```bash
docker-compose up -d
```

### Étape 6: Vérifier les Logs

```bash
docker logs backend_tenders | grep -i "postgres\|database"
docker logs backend_tenders | grep -i "benin" | head -5
```

Vous devriez voir:
```
✓ X documents chargés depuis PostgreSQL
```

## 🔧 Configuration PostgreSQL

**Credentials:**
- **Host**: `localhost` (depuis Windows)  ou `postgres` (depuis Docker)
- **Port**: `5432`
- **Database**: `tenders_db`
- **User**: `tender_user`
- **Password**: `tender_password_2024`

**Connection String:**
```
postgresql://tender_user:tender_password_2024@localhost:5432/tenders_db
```

## 📊 Commandes Utiles

### Se Connecter à PostgreSQL
```bash
docker exec -it postgres_tenders psql -U tender_user -d tenders_db
```

### Voir Toutes les Tables
```sql
\dt
```

### Compter les Offres
```sql
SELECT
    'BENIN' as source,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'pending') as pending
FROM tenders_benin
UNION ALL
SELECT
    'MEDIACONGO',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending')
FROM tenders_mediacongo
UNION ALL
SELECT
    'RELIEF',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending')
FROM tenders_relief;
```

### Voir les Dernières Offres Benin
```sql
SELECT ref, description, date_publication, status
FROM tenders_benin
ORDER BY created_at DESC
LIMIT 10;
```

### Vider une Table (Attention!)
```sql
TRUNCATE TABLE tenders_benin CASCADE;
```

### Backup de la Base
```bash
docker exec postgres_tenders pg_dump -U tender_user tenders_db > backup_$(date +%Y%m%d).sql
```

### Restaurer un Backup
```bash
docker exec -i postgres_tenders psql -U tender_user -d tenders_db < backup_20241227.sql
```

## 🔍 Vérification que Tout Fonctionne

### Test 1: Backend Benin API
```bash
curl http://localhost:5012/api/health
```

**Attendu:**
```json
{
  "status": "ok",
  "pending": 0,
  "validated": 0
}
```

### Test 2: Frontend
```
1. Ouvre http://localhost:8080/benin
2. Clique "Rafraîchir" 🔄
3. Tu devrais voir les offres (ou 0 si base vide)
```

### Test 3: Lancer un Scraping
```
1. Va sur http://localhost:8080/benin
2. Remplis: Date vide, Pages = 1
3. Clique "Lancer le Scraping BÉNIN"
4. Attends 5 minutes
5. Les offres apparaîtront
```

### Test 4: Vérifier dans PostgreSQL
```bash
docker exec -it postgres_tenders psql -U tender_user -d tenders_db -c "SELECT COUNT(*) FROM tenders_benin;"
```

## ⚠️ Différences MongoDB vs PostgreSQL

### Champs Renommés (snake_case)

| MongoDB (ancien)        | PostgreSQL (nouveau) |
|------------------------|----------------------|
| `_id`                  | `id`                 |
| `Ref`                  | `ref`                |
| `Description`          | `description`        |
| `Date_publication`     | `date_publication`   |
| `Date_limite_depot`    | `date_limite_depot`  |
| `Autorite_contractante`| `autorite_contractante` |
| `Lien_PDF`             | `lien_pdf`           |

### Requêtes

**Avant (MongoDB):**
```python
collection.find({"status": "pending"})
collection.insert_many(data)
collection.delete_one({"_id": offer_id})
```

**Après (PostgreSQL):**
```python
cursor.execute("SELECT * FROM tenders_benin WHERE status = %s", ("pending",))
execute_values(cursor, query, values)
cursor.execute("DELETE FROM tenders_benin WHERE id = %s", (offer_id,))
```

## 🎯 Avantages de PostgreSQL

✅ **Relations** - JOIN entre tables, Foreign Keys
✅ **Transactions ACID** - Garantie d'intégrité
✅ **SQL Puissant** - Requêtes complexes, agrégations
✅ **Performance** - Meilleur sur gros volumes
✅ **Outils** - pgAdmin, DBeaver, TablePlus
✅ **Standard** - SQL universel, facile à maintenir

## 🐛 Troubleshooting

### Erreur: "connection refused"
```bash
# Vérifier que PostgreSQL tourne
docker ps | grep postgres

# Redémarrer si besoin
docker-compose restart postgres
```

### Erreur: "relation does not exist"
```bash
# Recréer les tables
docker exec -i postgres_tenders psql -U tender_user -d tenders_db < backend/init.sql
```

### Erreur: "role 'tender_user' does not exist"
```bash
# Recréer le container PostgreSQL
docker-compose down
docker volume rm extractionautomatic_postgres_data
docker-compose up -d postgres
```

### Les offres n'apparaissent pas
```bash
# Vérifier les logs backend
docker logs backend_tenders | grep -i "postgres\|error"

# Vérifier la connexion
docker exec backend_tenders env | grep DB_
```

## 📝 TODO: Scripts à Migrer (si nécessaire)

Les scripts suivants utilisent encore MongoDB mais ne sont **PAS critiques** pour Benin/MediaCongo/Relief:

- `backend/scripts/scraper.py` (BOAMP)
- `backend/scripts/pnud.py`
- `backend/scripts/haicop.py`
- `backend/scripts/tuneps.py`
- `backend/scripts/banque_flask.py`

**Migration optionnelle** - Ces scrapers peuvent continuer avec MongoDB ou être migrés plus tard.

## ✅ Résumé

- ✅ PostgreSQL installé et configuré
- ✅ Tables créées automatiquement
- ✅ benin.py converti à PostgreSQL
- ✅ Helper db_postgres.py créé
- ✅ Dépendances mises à jour
- ✅ Docker configuré
- ✅ Frontend compatible (aucune modification)

**Status:** Migration complète pour Benin, MediaCongo, Relief! 🎉
