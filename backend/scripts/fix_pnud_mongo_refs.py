#!/usr/bin/env python3
"""
Script pour remplacer toutes les références MongoDB dans pnud.py
"""
import re

filepath = "pnud.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Supprimer les checks mongo_connected
content = re.sub(r'if not scraper\.mongo_connected:\s+return.*?\n.*?\n', '', content, flags=re.MULTILINE)
content = re.sub(r'if not self\.mongo_connected:\s+return\n', '', content, flags=re.MULTILINE)
content = re.sub(r'if self\.mongo_connected and self\.mongo_client:\s+self\.mongo_client\.close\(\)\n', '', content, flags=re.MULTILINE)

# 2. Remplacer les appels collection
replacements = [
    # count_documents
    (r'scraper\.pending_tenders_collection\.count_documents\(\{\}\)', 'count_tenders(status="pending")'),
    (r'scraper\.tenders_collection\.count_documents\(\{\}\)', 'count_tenders(status="active")'),
    (r'self\.pending_tenders_collection\.count_documents\(\{\}\)', 'count_tenders(status="pending")'),
    (r'self\.tenders_collection\.count_documents\(\{\}\)', 'count_tenders(status="active")'),

    # find
    (r'scraper\.pending_tenders_collection\.find\(\{\}\)\.sort\("fetchedAt", -1\)\.skip\(skip\)\.limit\(limit\)',
     'get_all_tenders(status="pending")[skip:skip+limit]'),
    (r'scraper\.pending_tenders_collection\.find\(\{\}\)', 'get_all_tenders(status="pending")'),
    (r'scraper\.tenders_collection\.find\(\{\}\)\.sort\("fetchedAt", -1\)\.limit\(50\)',
     'get_all_tenders(status="active")[:50]'),
    (r'self\.tenders_collection\.find\(\{\}\)', 'get_all_tenders(status="active")'),

    # find_one
    (r'scraper\.pending_tenders_collection\.find_one\(\{"reference": reference\}\)',
     'get_tender_by_reference(reference)'),

    # insert_one
    (r'self\.tenders_collection\.insert_one\(asdict\(offre\)\)',
     'insert_tender({**asdict(offre), "status": "active"})'),

    # delete_one
    (r'self\.pending_tenders_collection\.delete_one\(\{"reference": offre\.reference\}\)',
     'delete_tender(offre.reference)'),
    (r'scraper\.pending_tenders_collection\.delete_one\(\{"reference": reference\}\)',
     'delete_tender(reference)'),

    # delete_many
    (r'scraper\.pending_tenders_collection\.delete_many\(\{\}\)',
     'delete_all_pending()'),

    # update_one
    (r'scraper\.pending_tenders_collection\.update_one\([^)]+\)',
     'update_tender(reference, update_data)'),

    # Status checks
    (r'scraper\.mongo_connected', 'True'),
    (r'self\.mongo_connected', 'True'),
    (r'"mongodb_connected": scraper\.mongo_connected', '"postgresql_connected": True'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# 3. Sauvegarder
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fichier pnud.py mis à jour")
