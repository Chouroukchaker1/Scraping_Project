#!/usr/bin/env python3
"""Migration rapide des scripts restants vers PostgreSQL"""
import os
import re

SCRIPTS_DIR = "scripts"

SCRIPTS_TO_MIGRATE = {
    "banque.py": "tenders_banque",
    "banque_flask.py": "tenders_banque",
    "haicop.py": "tenders_haicop",
    "armp_flask.py": "tenders_armp",
    "expertise.py": "tenders_expertise",
    "france.py": "tenders_boamp",
    "france_marches_scraper.py": "tenders_boamp"
}

POSTGRES_IMPORTS = """import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
"""

def get_postgres_config(table_name):
    return f"""
# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "{table_name}"
"""

def migrate_script(filename, table_name):
    filepath = os.path.join(SCRIPTS_DIR, filename)

    if not os.path.exists(filepath):
        print(f"Fichier non trouve: {filepath}")
        return False

    # Backup
    backup_path = filepath + ".mongodb_backup"
    if not os.path.exists(backup_path):
        with open(filepath, 'r', encoding='utf-8') as f:
            with open(backup_path, 'w', encoding='utf-8') as fb:
                fb.write(f.read())
        print(f"Backup: {backup_path}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Supprimer imports MongoDB
    content = re.sub(r'from pymongo import.*?\n', '', content)
    content = re.sub(r'from pymongo\.errors import.*?\n', '', content)
    content = re.sub(r'from bson import.*?\n', '', content)
    content = re.sub(r'import pymongo.*?\n', '', content)

    # 2. Ajouter imports PostgreSQL si pas déjà présents
    if 'import psycopg2' not in content:
        # Trouver la première ligne après les imports
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_pos = i + 1
        lines.insert(insert_pos, POSTGRES_IMPORTS)
        content = '\n'.join(lines)

    # 3. Remplacer config MongoDB
    content = re.sub(
        r'MONGO_URI\s*=.*?\n',
        '',
        content
    )
    content = re.sub(
        r'DB_NAME\s*=\s*["\'].*?["\']\s*\n',
        '',
        content
    )
    content = re.sub(
        r'COLLECTION_NAME\s*=.*?\n',
        '',
        content
    )
    content = re.sub(
        r'PENDING_COLLECTION_NAME\s*=.*?\n',
        get_postgres_config(table_name),
        content
    )

    # 4. Remplacer initialisations MongoDB
    content = re.sub(
        r'mongo_client\s*=\s*MongoClient\(.*?\)',
        '# PostgreSQL used instead',
        content
    )
    content = re.sub(
        r'db\s*=\s*mongo_client\[.*?\]',
        '',
        content
    )
    content = re.sub(
        r'.*?collection\s*=\s*db\[.*?\]',
        '',
        content
    )

    # 5. Remplacer PyMongoError
    content = re.sub(r'PyMongoError', 'Exception', content)
    content = re.sub(r'ConnectionFailure', 'Exception', content)

    # 6. Sauvegarder
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Migre: {filename} -> {table_name}")
    return True

def main():
    print("Migration rapide vers PostgreSQL")
    print("=" * 60)

    migrated = 0
    for filename, table_name in SCRIPTS_TO_MIGRATE.items():
        if migrate_script(filename, table_name):
            migrated += 1

    print("=" * 60)
    print(f"Scripts migres: {migrated}/{len(SCRIPTS_TO_MIGRATE)}")
    print("\nATTENTION: Migration partielle!")
    print("Les appels collection.find(), insert_one(), etc. doivent etre")
    print("remplaces manuellement par les fonctions PostgreSQL.")

if __name__ == "__main__":
    main()
