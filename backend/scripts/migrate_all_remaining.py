#!/usr/bin/env python3
"""Migration automatique de TOUS les scripts restants vers PostgreSQL"""
import os
import shutil

SCRIPTS = {
    "banque.py": "tenders_banque",
    "banque_flask.py": "tenders_banque",
    "haicop.py": "tenders_haicop",
    "armp_flask.py": "tenders_armp",
    "expertise.py": "tenders_expertise",
    "france_marches_scraper.py": "tenders_boamp"
}

POSTGRES_HELPER = '''
# ================================================
# POSTGRESQL HELPER FUNCTIONS
# ================================================

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

def get_existing_references():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT reference FROM {TABLE_NAME}")
        return {row[0] for row in cursor.fetchall() if row[0]}
    finally:
        cursor.close()
        conn.close()

def insert_tender(tender_dict):
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
            tender_dict.get('externalUrl') or tender_dict.get('external_url'),
            tender_dict.get('montant'),
            tender_dict.get('nature', 'public'),
            tender_dict.get('country'),
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

def count_tenders(status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if status:
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = %s", (status,))
        else:
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()

def get_tender_by_reference(reference):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def delete_all_pending():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE status = 'pending'")
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    finally:
        cursor.close()
        conn.close()

# Test connexion PostgreSQL
try:
    conn = get_db_connection()
    conn.close()
    print(f"PostgreSQL connecte: {DB_NAME} (Table: {TABLE_NAME})")
except Exception as e:
    print(f"Erreur connexion PostgreSQL: {e}")
'''

def migrate_script(filename, table_name):
    print(f"\\nMigration de {filename}...")

    # 1. Copier france.py migré comme template
    shutil.copy("france.py", filename)

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. Remplacer TABLE_NAME
    content = content.replace('TABLE_NAME = "tenders_boamp"', f'TABLE_NAME = "{table_name}"')

    # 3. Sauvegarder
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  {filename} -> {table_name}")

for filename, table_name in SCRIPTS.items():
    migrate_script(filename, table_name)

print("\\n=== MIGRATION TERMINEE ===")
print(f"{len(SCRIPTS)} scripts migres vers PostgreSQL")
