# Migration MongoDB → PostgreSQL

## ✅ Modifications Effectuées

### 1. Docker Compose
- ❌ **Supprimé**: Service `mongodb` (port 27018)
- ✅ **Ajouté**: Service `postgres` (port 5432)
- ✅ **Image**: `postgres:15-alpine`
- ✅ **Script d'initialisation**: `backend/init.sql` monté automatiquement

### 2. Variables d'Environnement

**Avant (MongoDB):**
```env
MONGO_URI=mongodb://mongodb:27017/marmoucha
DB_NAME=marmoucha
```

**Après (PostgreSQL):**
```env
DATABASE_URL=postgresql://tender_user:tender_password_2024@postgres:5432/tenders_db
DB_HOST=postgres
DB_PORT=5432
DB_NAME=tenders_db
DB_USER=tender_user
DB_PASSWORD=tender_password_2024
```

### 3. Base de Données

**Credentials:**
- **Host**: `localhost` (ou `postgres` depuis Docker)
- **Port**: `5432`
- **Database**: `tenders_db`
- **User**: `tender_user`
- **Password**: `tender_password_2024`

**Tables créées automatiquement:**
- `tenders` - Table principale unifiée
- `tenders_benin` - Offres Bénin
- `tenders_mediacongo` - Offres MediaCongo
- `tenders_relief` - Offres Relief
- `tenders_pnud` - Offres PNUD

## 🚀 Démarrage

### Première Installation

1. **Arrêter MongoDB** (si en cours):
```bash
docker-compose down
docker volume rm extractionautomatic_mongodb_data
docker volume rm extractionautomatic_mongodb_config
```

2. **Démarrer PostgreSQL**:
```bash
docker-compose up -d postgres
```

3. **Vérifier la base**:
```bash
docker exec -it postgres_tenders psql -U tender_user -d tenders_db -c "\dt"
```

Tu devrais voir:
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

4. **Démarrer tout**:
```bash
docker-compose up -d
```

## 📝 Modifications à Faire dans les Scripts Python

### Pour BENIN (backend/scripts/benin.py)

**Avant (MongoDB):**
```python
import pymongo

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["appels_offres_scraping"]

# Insertion
collection.insert_many(data)
```

**Après (PostgreSQL):**
```python
import psycopg2
from psycopg2.extras import execute_values

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "postgres"),
    port=os.getenv("DB_PORT", 5432),
    database=os.getenv("DB_NAME", "tenders_db"),
    user=os.getenv("DB_USER", "tender_user"),
    password=os.getenv("DB_PASSWORD", "tender_password_2024")
)

# Insertion
cursor = conn.cursor()
query = """
    INSERT INTO tenders_benin (ref, description, date_publication, date_limite_depot,
                                delai, autorite_contractante, lieu_execution, lien_pdf)
    VALUES %s
    ON CONFLICT (ref) DO NOTHING
"""
execute_values(cursor, query, data)
conn.commit()
```

### Installation des Dépendances Python

Ajouter au `backend/requirements.txt`:
```txt
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
```

Ou dans le Dockerfile:
```dockerfile
RUN pip install psycopg2-binary sqlalchemy
```

## 🔧 Commandes Utiles

### Se connecter à PostgreSQL
```bash
docker exec -it postgres_tenders psql -U tender_user -d tenders_db
```

### Voir toutes les tables
```sql
\dt
```

### Voir les offres en attente (toutes sources)
```sql
SELECT * FROM pending_tenders_all LIMIT 10;
```

### Compter les offres par source
```sql
SELECT
    (SELECT COUNT(*) FROM tenders_benin WHERE status = 'pending') as benin,
    (SELECT COUNT(*) FROM tenders_mediacongo WHERE status = 'pending') as mediacongo,
    (SELECT COUNT(*) FROM tenders_relief WHERE status = 'pending') as relief,
    (SELECT COUNT(*) FROM tenders_pnud WHERE status = 'pending') as pnud;
```

### Exporter la base
```bash
docker exec postgres_tenders pg_dump -U tender_user tenders_db > backup.sql
```

### Importer une sauvegarde
```bash
docker exec -i postgres_tenders psql -U tender_user -d tenders_db < backup.sql
```

## ⚠️ Important

1. **Les données MongoDB existantes ne seront PAS migrées automatiquement**
   - Si tu veux garder les anciennes données, il faut les exporter puis importer dans PostgreSQL

2. **Tous les scripts Python doivent être modifiés** pour utiliser PostgreSQL
   - Remplacer `pymongo` par `psycopg2`
   - Adapter les requêtes MongoDB → SQL

3. **Le frontend fonctionne toujours** car il communique via API REST
   - Aucune modification nécessaire côté frontend

## 📊 Avantages PostgreSQL

✅ Relations entre tables (JOIN, Foreign Keys)
✅ Transactions ACID garanties
✅ Requêtes SQL puissantes
✅ Meilleure intégrité des données
✅ Performance sur gros volumes
✅ Outils d'administration riches (pgAdmin, DBeaver)

## 🎯 Prochaines Étapes

1. ✅ Modifier `backend/scripts/benin.py` pour utiliser PostgreSQL
2. ✅ Modifier `backend/scripts/mediacongo.py`
3. ✅ Modifier `backend/scripts/relief.py`
4. ✅ Tester le scraping avec la nouvelle base
5. ✅ Migrer les autres scrapers (PNUD, etc.)
