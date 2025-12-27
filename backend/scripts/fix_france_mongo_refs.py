#!/usr/bin/env python3
"""Script pour remplacer toutes les références MongoDB dans france.py"""
import re

filepath = "france.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacements
replacements = [
    # MongoDB client/db/collection declarations
    (r'mongo_client\s*=\s*MongoClient\(.*?\)', '# PostgreSQL used'),
    (r'db\s*=\s*mongo_client\[.*?\]', ''),
    (r'collection\s*=\s*db\[.*?\]', ''),
    (r'pending_collection\s*=\s*db\[.*?\]', ''),
    (r'tenders_collection\s*=\s*db\[.*?\]', ''),
    (r'pending_tenders_collection\s*=\s*db\[.*?\]', ''),

    # count_documents
    (r'\.count_documents\(\{\}\)', 'count_tenders()'),
    (r'\.count_documents\(\{"status": "pending"\}\)', 'count_tenders(status="pending")'),
    (r'\.count_documents\(\{"status": "active"\}\)', 'count_tenders(status="active")'),

    # find
    (r'\.find\(\{\}\)\.sort\([^)]+\)\.skip\([^)]+\)\.limit\([^)]+\)', 'get_all_tenders()'),
    (r'\.find\(\{"status": "pending"\}\)', 'get_all_tenders(status="pending")'),
    (r'\.find\(\{"status": "active"\}\)', 'get_all_tenders(status="active")'),
    (r'\.find\(\{\}\)', 'get_all_tenders()'),

    # find_one
    (r'\.find_one\(\{"reference": ([^}]+)\}\)', r'get_tender_by_reference(\1)'),

    # insert_one
    (r'\.insert_one\(([^)]+)\)', r'insert_tender(\1)'),

    # delete_one
    (r'\.delete_one\(\{"reference": ([^}]+)\}\)', r'delete_tender(\1)'),

    # delete_many
    (r'\.delete_many\(\{\}\)', 'delete_all_pending()'),

    # update_one
    (r'\.update_one\([^)]+\)', 'update_tender(reference, update_data)'),

    # PyMongoError
    (r'PyMongoError', 'Exception'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Sauvegarder
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("France.py migration complete")
