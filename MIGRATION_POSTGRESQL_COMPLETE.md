# Migration MongoDB → PostgreSQL - Guide Complet

## ✅ État de la Migration

### Scripts DÉJÀ migrés vers PostgreSQL:
1. ✅ **tuneps.py** - Complètement fonctionnel avec PostgreSQL
2. ✅ **tuneps_ao.py** - Migré vers PostgreSQL
3. ✅ **benin.py** - Utilise PostgreSQL
4. ✅ **mediacongo.py** - Utilise PostgreSQL
5. ✅ **relief.py** - Utilise PostgreSQL

### Scripts ENCORE sur MongoDB (à migrer):
6. ❌ **pnud.py** - Utilise encore MongoDB
7. ❌ **banque.py** - Utilise encore MongoDB
8. ❌ **banque_flask.py** - Utilise encore MongoDB
9. ❌ **haicop.py** - Utilise encore MongoDB
10. ❌ **armp_flask.py** - Utilise encore MongoDB
11. ❌ **expertise.py** - Utilise encore MongoDB
12. ❌ **france.py** - Utilise encore MongoDB
13. ❌ **france_marches_scraper.py** - Utilise encore MongoDB

---

## 🗄️ Base de Données PostgreSQL

### Connexion

```bash
Host: localhost (ou postgres depuis Docker)
Port: 5432
Database: tenders_db
User: tender_user
Password: tender_password_2024
```

### Tables créées

Toutes les tables suivantes sont prêtes dans PostgreSQL:

- `tenders_tuneps` - Appels d'offres Tunisie (TUNEPS)
- `tenders_tuneps_ao` - Appels d'offres Tunisie (/portail/offres)
- `tenders_benin` - Marchés publics Bénin
- `tenders_mediacongo` - Offres MediaCongo (RDC)
- `tenders_relief` - Offres Relief (humanitaire)
- `tenders_pnud` - Offres PNUD (UNDP)
- `tenders_banque` - Banque Mondiale
- `tenders_boamp` - BOAMP France
- `tenders_haicop` - Tunisie (Haicop)
- `tenders_armp` - Madagascar (ARMP)
- `tenders_expertise` - Expertise France

---

## 🚀 Démarrage de l'Application

### 1. Arrêter tous les containers

```bash
docker-compose down
```

### 2. Supprimer les volumes MongoDB (OPTIONNEL - seulement si vous voulez repartir à zéro)

```bash
docker volume rm extractionautomatic_mongodb_data
docker volume rm extractionautomatic_mongodb_config
```

### 3. Démarrer PostgreSQL seul (pour vérifier)

```bash
docker-compose up -d postgres
```

Attendre 10 secondes, puis vérifier les tables:

```bash
docker exec postgres_tenders psql -U tender_user -d tenders_db -c "\dt"
```

Vous devriez voir 11 tables.

### 4. Démarrer TOUTE l'application

```bash
docker-compose up -d
```

### 5. Vérifier les logs

```bash
# Backend
docker logs backend_tenders -f

# Frontend
docker logs frontend_tenders -f

# PostgreSQL
docker logs postgres_tenders -f
```

---

## 🔧 Accès aux Services

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:5000
- **PostgreSQL**: localhost:5432

### Scrapers disponibles:

- **TUNEPS**: http://localhost:5001
- **TUNEPS AO**: http://localhost:5005
- **BOAMP**: http://localhost:5003
- **PNUD**: http://localhost:5006
- **ARMP**: http://localhost:5007
- **BANQUE**: http://localhost:5010
- **HAICOP**: http://localhost:5011
- **BENIN**: http://localhost:5012
- **EXPERTISE**: http:// localhost:5013
- **RELIEF**: http://localhost:5015
- **MEDIACONGO**: http://localhost:5016

---

## 📝 Comment Migrer les Scripts Restants

Pour migrer les scripts qui utilisent encore MongoDB (pnud.py, banque.py, etc.), suivez ce pattern:

### 1. Remplacer les imports

**AVANT:**
```python
from pymongo import MongoClient
from pymongo.errors import PyMongoError
```

**APRÈS:**
```python
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
```

### 2. Remplacer la configuration

**AVANT:**
```python
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/...")
DB_NAME = "..."
COLLECTION_NAME = "..."
```

**APRÈS:**
```python
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_pnud"  # Adapter selon le scraper
```

### 3. Ajouter les fonctions helper PostgreSQL

```python
def get_db_connection():
    """Créer une connexion PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def get_all_tenders(status=None):
    """Récupère toutes les offres depuis PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if status:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY created_at DESC")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def insert_tender(tender_dict):
    """Insère une offre en PostgreSQL"""
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = f"""
            INSERT INTO {TABLE_NAME} (reference, description, description_fr, publication_date,
                                      expiration_date, promoter, source_id, avis_id, external_url,
                                      montant, nature, country, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reference) DO NOTHING
            RETURNING id
        """
        values = (
            tender_dict.get('reference'),
            tender_dict.get('description'),
            tender_dict.get('description_fr'),
            tender_dict.get('publicationDate') or tender_dict.get('publication_date'),
            tender_dict.get('expirationDate') or tender_dict.get('expiration_date'),
            tender_dict.get('promoter'),
            tender_dict.get('sourceId') or tender_dict.get('source_id'),
            tender_dict.get('avisId') or tender_dict.get('avis_id'),
            tender_dict.get('external_url'),
            tender_dict.get('montant'),
            tender_dict.get('nature', 'public'),
            tender_dict.get('country') or tender_dict.get('pays'),
            tender_dict.get('status', 'pending')
        )
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()

def delete_tender(reference):
    """Supprime une offre"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    finally:
        cursor.close()
        conn.close()
```

### 4. Remplacer les appels MongoDB

**AVANT:**
```python
# Find
tenders_collection.find({"status": "pending"})

# Insert
tenders_collection.insert_one(data)

# Delete
tenders_collection.delete_one({"reference": ref})

# Update
tenders_collection.update_one({"reference": ref}, {"$set": {"status": "active"}})
```

**APRÈS:**
```python
# Find
get_all_tenders(status="pending")

# Insert
insert_tender(data)

# Delete
delete_tender(ref)

# Update (delete + insert)
delete_tender(ref)
insert_tender(updated_data)
```

---

## 🔍 Commandes Utiles PostgreSQL

### Se connecter à la base

```bash
docker exec -it postgres_tenders psql -U tender_user -d tenders_db
```

### Voir toutes les tables

```sql
\dt
```

### Compter les offres par source

```sql
SELECT
    'TUNEPS' as source,
    (SELECT COUNT(*) FROM tenders_tuneps WHERE status = 'pending') as pending,
    (SELECT COUNT(*) FROM tenders_tuneps WHERE status = 'active') as active
UNION ALL
SELECT
    'TUNEPS_AO',
    (SELECT COUNT(*) FROM tenders_tuneps_ao WHERE status = 'pending'),
    (SELECT COUNT(*) FROM tenders_tuneps_ao WHERE status = 'active')
UNION ALL
SELECT
    'BENIN',
    (SELECT COUNT(*) FROM tenders_benin WHERE status = 'pending'),
    (SELECT COUNT(*) FROM tenders_benin WHERE status = 'active')
UNION ALL
SELECT
    'MEDIACONGO',
    (SELECT COUNT(*) FROM tenders_mediacongo WHERE status = 'pending'),
    (SELECT COUNT(*) FROM tenders_mediacongo WHERE status = 'active')
UNION ALL
SELECT
    'RELIEF',
    (SELECT COUNT(*) FROM tenders_relief WHERE status = 'pending'),
    (SELECT COUNT(*) FROM tenders_relief WHERE status = 'active')
UNION ALL
SELECT
    'PNUD',
    (SELECT COUNT(*) FROM tenders_pnud WHERE status = 'pending'),
    (SELECT COUNT(*) FROM tenders_pnud WHERE status = 'active')
UNION ALL
SELECT
    'BANQUE',
    (SELECT COUNT(*) FROM tenders_banque WHERE status = 'pending'),
    (SELECT COUNT(*) FROM tenders_banque WHERE status = 'active');
```

### Voir les offres récentes

```sql
SELECT reference, description, publication_date, status
FROM tenders_tuneps
ORDER BY created_at DESC
LIMIT 10;
```

### Exporter la base

```bash
docker exec postgres_tenders pg_dump -U tender_user tenders_db > backup_$(date +%Y%m%d).sql
```

### Importer une sauvegarde

```bash
docker exec -i postgres_tenders psql -U tender_user -d tenders_db < backup.sql
```

---

## ⚠️ Notes Importantes

1. **MongoDB n'est PLUS utilisé** - Le service mongodb a été supprimé du docker-compose.yml

2. **Données MongoDB existantes** - Si vous aviez des données dans MongoDB, elles ne sont PAS migrées automatiquement. Vous devez:
   - Soit exporter les données de MongoDB
   - Soit re-scraper toutes les sources

3. **Scrapers non migrés** - Les scrapers qui utilisent encore MongoDB (pnud.py, banque.py, etc.) vont planter au démarrage. Il faut:
   - Soit les migrer vers PostgreSQL (voir section "Comment Migrer")
   - Soit désactiver temporairement leurs ports dans docker-compose.yml

4. **Frontend inchangé** - Le frontend React n'a AUCUN changement à faire, il communique via API REST

5. **psycopg2-binary** - Déjà ajouté dans requirements.txt

---

## 📊 Avantages PostgreSQL vs MongoDB

✅ **Relations entre tables** - JOIN, Foreign Keys
✅ **Transactions ACID** garanties
✅ **Requêtes SQL puissantes** - Agrégations, fenêtres, CTEs
✅ **Meilleure intégrité des données** - Contraintes, validations
✅ **Performance sur gros volumes** - Indexation efficace
✅ **Outils d'administration riches** - pgAdmin, DBeaver, TablePlus
✅ **Backup/Restore robuste** - pg_dump, PITR
✅ **Monitoring avancé** - pg_stat_*, logs détaillés

---

## 🎯 Prochaines Étapes

1. ✅ PostgreSQL démarré et testé
2. ⏳ Migrer les 8 scripts restants (pnud, banque, haicop, armp, expertise, france)
3. ⏳ Tester chaque scraper individuellement
4. ⏳ Vérifier l'intégration avec l'API AppelOffres.net
5. ⏳ Importer les données historiques si nécessaire
6. ⏳ Configurer les sauvegardes automatiques
7. ⏳ Monitorer les performances

---

## 📞 Support

Si vous rencontrez des erreurs:

1. **Vérifier les logs PostgreSQL:**
   ```bash
   docker logs postgres_tenders -f
   ```

2. **Vérifier que les tables existent:**
   ```bash
   docker exec postgres_tenders psql -U tender_user -d tenders_db -c "\dt"
   ```

3. **Tester la connexion PostgreSQL:**
   ```bash
   docker exec postgres_tenders psql -U tender_user -d tenders_db -c "SELECT version();"
   ```

4. **Recréer les tables si nécessaire:**
   ```bash
   docker exec -i postgres_tenders psql -U tender_user -d tenders_db < backend/init.sql
   ```

---

**Date de migration**: 27 décembre 2025
**Version PostgreSQL**: 15.15
**Status**: ✅ PostgreSQL opérationnel, 5/13 scripts migrés
