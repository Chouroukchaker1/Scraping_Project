#!/usr/bin/env python3
"""
Script de migration automatique MongoDB → PostgreSQL
Migre tous les scrapers Python vers PostgreSQL
"""
import os
import re

# Configuration des mappings par scraper
SCRAPER_CONFIG = {
    "pnud.py": {
        "table": "tenders_pnud",
        "collection_names": ["tenders_pnud", "pending_tenders_pnud"]
    },
    "banque.py": {
        "table": "tenders_banque",
        "collection_names": ["tenders_banque", "pending_tenders_banque"]
    },
    "banque_flask.py": {
        "table": "tenders_banque",
        "collection_names": ["tenders_banque", "pending_tenders_banque"]
    },
    "haicop.py": {
        "table": "tenders_haicop",
        "collection_names": ["tenders_haicop", "pending_tenders_haicop"]
    },
    "armp_flask.py": {
        "table": "tenders_armp",
        "collection_names": ["tenders_armp", "pending_tenders_armp"]
    },
    "expertise.py": {
        "table": "tenders_expertise",
        "collection_names": ["tenders_expertise", "pending_tenders_expertise"]
    },
    "france.py": {
        "table": "tenders_boamp",
        "collection_names": ["boampvalidates", "boampoffres"]
    },
    "france_marches_scraper.py": {
        "table": "tenders_boamp",
        "collection_names": ["boampvalidates", "boampoffres"]
    }
}

POSTGRES_HELPER = '''
# ================================================
# POSTGRESQL HELPER FUNCTIONS
# ================================================

def get_db_connection():
    """Créer une connexion PostgreSQL"""
    import psycopg2
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def get_all_from_table(status=None):
    """Récupère toutes les offres depuis PostgreSQL"""
    import psycopg2.extras
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if status:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY created_at DESC")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_existing_references():
    """Récupère l'ensemble des références existantes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT reference FROM {TABLE_NAME}")
        return {row[0] for row in cursor.fetchall() if row[0]}
    finally:
        cursor.close()
        conn.close()

def insert_into_postgres(data_dict):
    """Insère une offre en PostgreSQL (version générique)"""
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Adapter selon les champs de votre table
        query = f"""
            INSERT INTO {TABLE_NAME} (reference, description, description_fr, publication_date,
                                      expiration_date, promoter, source_id, avis_id, external_url,
                                      montant, nature, country, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reference) DO NOTHING
            RETURNING id
        """
        values = (
            data_dict.get('reference'),
            data_dict.get('description'),
            data_dict.get('description_fr'),
            data_dict.get('publicationDate') or data_dict.get('publication_date'),
            data_dict.get('expirationDate') or data_dict.get('expiration_date'),
            data_dict.get('promoter'),
            data_dict.get('sourceId') or data_dict.get('source_id'),
            data_dict.get('avisId') or data_dict.get('avis_id'),
            data_dict.get('external_url'),
            data_dict.get('montant'),
            data_dict.get('nature', 'public'),
            data_dict.get('country') or data_dict.get('pays'),
            data_dict.get('status', 'pending')
        )
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        return result[0] if result else None
    except Exception as e:
        conn.rollback()
        print(f"Erreur insertion PostgreSQL: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def delete_from_postgres(reference):
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

def update_status_postgres(reference, status):
    """Met à jour le statut d'une offre"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE {TABLE_NAME} SET status = %s WHERE reference = %s",
            (status, reference)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
'''

def migrate_file(filepath, config):
    """Migre un fichier Python vers PostgreSQL"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Remplacer les imports
    content = re.sub(
        r'from pymongo import MongoClient.*?\n',
        '',
        content,
        flags=re.MULTILINE
    )
    content = re.sub(
        r'from pymongo\.errors import.*?\n',
        '',
        content,
        flags=re.MULTILINE
    )
    content = re.sub(
        r'from bson import ObjectId.*?\n',
        '',
        content,
        flags=re.MULTILINE
    )

    # Ajouter psycopg2
    if 'import psycopg2' not in content:
        # Trouver la section d'imports
        import_section_match = re.search(r'(import.*?\n)+', content)
        if import_section_match:
            import_end = import_section_match.end()
            content = content[:import_end] + "import psycopg2\nfrom psycopg2.extras import execute_values, RealDictCursor\n" + content[import_end:]

    # 2. Remplacer configuration MongoDB par PostgreSQL
    mongo_config_pattern = r'MONGO_URI\s*=.*?\n.*?DB_NAME\s*=.*?\n.*?COLLECTION_NAME\s*=.*?\n.*?PENDING_COLLECTION_NAME\s*=.*?\n'

    postgres_config = f'''# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "{config['table']}"
'''

    content = re.sub(mongo_config_pattern, postgres_config, content, flags=re.MULTILINE)

    # 3. Remplacer initialisation MongoDB
    mongo_init_pattern = r'mongo_client\s*=\s*MongoClient\(.*?\).*?\n.*?db\s*=\s*mongo_client\[.*?\].*?\n.*?collection.*?=.*?db\[.*?\].*?\n.*?pending.*?collection.*?=.*?db\[.*?\].*?\n.*?try:.*?db\.command.*?except.*?PyMongoError.*?raise'

    content = re.sub(
        mongo_init_pattern,
        POSTGRES_HELPER,
        content,
        flags=re.DOTALL
    )

    # 4. Remplacer PyMongoError par Exception
    content = re.sub(r'PyMongoError', 'Exception', content)
    content = re.sub(r'ConnectionFailure', 'Exception', content)

    # 5. Sauvegarder si modifié
    if content != original_content:
        backup_path = filepath + '.mongodb_backup'
        if not os.path.exists(backup_path):
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print(f"Backup cree: {backup_path}")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Migre: {filepath}")
        return True
    else:
        print(f"Aucun changement: {filepath}")
        return False

def main():
    scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")

    print("Migration MongoDB -> PostgreSQL")
    print("=" * 60)

    migrated = 0
    for filename, config in SCRAPER_CONFIG.items():
        filepath = os.path.join(scripts_dir, filename)
        if os.path.exists(filepath):
            print(f"\nTraitement: {filename}")
            if migrate_file(filepath, config):
                migrated += 1
        else:
            print(f"Fichier non trouve: {filepath}")

    print("\n" + "=" * 60)
    print(f"Migration terminee: {migrated} fichiers migres")
    print("\nIMPORTANT: Vous devez maintenant:")
    print("1. Adapter les fonctions PostgreSQL dans chaque fichier")
    print("2. Remplacer les appels collection.find() par get_all_from_table()")
    print("3. Remplacer collection.insert_one() par insert_into_postgres()")
    print("4. Tester chaque scraper individuellement")

if __name__ == "__main__":
    main()
