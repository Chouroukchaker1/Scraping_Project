#!/usr/bin/env python3
"""Migration intelligente - Ajoute PostgreSQL sans écraser la logique existante"""
import re

SCRIPTS = {
    "banque.py": "tenders_banque",
    "banque_flask.py": "tenders_banque",
    "haicop.py": "tenders_haicop",
    "armp_flask.py": "tenders_armp",
    "expertise.py": "tenders_expertise",
    "france_marches_scraper.py": "tenders_boamp"
}

POSTGRES_CONFIG = lambda table: f"""
# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "{table}"
"""

# Lire les helpers depuis france.py
with open("france.py", 'r', encoding='utf-8') as f:
    france_content = f.read()

# Extraire les helpers PostgreSQL de france.py
match = re.search(r'# ================================================\n# POSTGRESQL HELPER FUNCTIONS\n# ================================================\n(.*?)# Test connexion PostgreSQL', france_content, re.DOTALL)
if match:
    POSTGRES_HELPERS = match.group(0)
else:
    print("Erreur: impossible d'extraire les helpers de france.py")
    exit(1)

def migrate_file(filename, table_name):
    print(f"Migration de {filename}...")

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remplacer imports MongoDB par PostgreSQL
    content = re.sub(r'from pymongo import.*?\n', '', content)
    content = re.sub(r'from pymongo\.errors import.*?\n', '', content)
    content = re.sub(r'import pymongo\n', '', content)

    # Ajouter imports PostgreSQL si pas déjà présents
    if 'import psycopg2' not in content:
        # Trouver la première ligne après les imports
        lines = content.split('\\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                insert_pos = i + 1

        lines.insert(insert_pos, "import psycopg2\\nfrom psycopg2.extras import execute_values, RealDictCursor")
        content = '\\n'.join(lines)

    # 2. Remplacer config MongoDB
    content = re.sub(r'MONGO_URI\s*=.*?\\n', '', content)
    content = re.sub(r'DB_NAME\s*=\s*["\'].*?["\']\\n', '', content)
    content = re.sub(r'COLLECTION_NAME\s*=.*?\\n', '', content)
    content = re.sub(r'PENDING_COLLECTION_NAME\s*=.*?\\n', POSTGRES_CONFIG(table_name), content)

    # 3. Ajouter les helpers PostgreSQL si pas déjà présents
    if '# POSTGRESQL HELPER FUNCTIONS' not in content:
        # Trouver où insérer (après les configs)
        insert_marker = "# Configuration API"
        if insert_marker in content:
            parts = content.split(insert_marker)
            content = parts[0] + POSTGRES_HELPERS + "\\n" + insert_marker + parts[1]
        else:
            # Sinon insérer après load_dotenv ou après les imports
            if 'load_dotenv()' in content:
                parts = content.split('load_dotenv()')
                content = parts[0] + 'load_dotenv()\\n' + POSTGRES_HELPERS + parts[1]

    # 4. Remplacer les appels MongoDB
    replacements = [
        (r'mongo_client\s*=\s*MongoClient\\(.*?\\)', '# PostgreSQL used'),
        (r'\\.count_documents\\(\\{\\}\\)', 'count_tenders()'),
        (r'\\.count_documents\\(\\{"status": "pending"\\}\\)', 'count_tenders(status="pending")'),
        (r'\\.find\\(\\{\\}\\)', 'get_all_tenders()'),
        (r'\\.find\\(\\{"status": "pending"\\}\\)', 'get_all_tenders(status="pending")'),
        (r'\\.find_one\\(\\{"reference": ([^}]+)\\}\\)', r'get_tender_by_reference(\\1)'),
        (r'\\.insert_one\\(([^)]+)\\)', r'insert_tender(\\1)'),
        (r'\\.delete_one\\(\\{"reference": ([^}]+)\\}\\)', r'delete_tender(\\1)'),
        (r'\\.delete_many\\(\\{\\}\\)', 'delete_all_pending()'),
        (r'PyMongoError', 'Exception'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    # Sauvegarder
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  OK: {filename} -> {table_name}")

for filename, table_name in SCRIPTS.items():
    try:
        migrate_file(filename, table_name)
    except Exception as e:
        print(f"  ERREUR {filename}: {e}")

print("\\nMigration terminee!")
