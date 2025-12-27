"""
Script pour vérifier les données MongoDB pour BOAMP
"""
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Forcer UTF-8
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tunip")
DB_NAME = os.getenv("DB_NAME", "tunip")
COLLECTION_NAME = os.getenv("BOAMP_COLLECTION_NAME", "boampvalidates")
PENDING_COLLECTION_NAME = os.getenv("BOAMP_PENDING_COLLECTION_NAME", "boampoffres")

print("=" * 80)
print("VERIFICATION DONNEES MONGODB BOAMP")
print("=" * 80)
print(f"URI: {MONGO_URI}")
print(f"Database: {DB_NAME}")
print(f"Collection validees: {COLLECTION_NAME}")
print(f"Collection pending: {PENDING_COLLECTION_NAME}")
print()

try:
    print("Connexion a MongoDB...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("CONNEXION OK")
    print()

    db = client[DB_NAME]

    # Compter les documents
    validated_count = db[COLLECTION_NAME].count_documents({})
    pending_count = db[PENDING_COLLECTION_NAME].count_documents({})

    print(f"COLLECTION VALIDEES ({COLLECTION_NAME}): {validated_count} documents")
    print(f"COLLECTION PENDING ({PENDING_COLLECTION_NAME}): {pending_count} documents")
    print()

    # Afficher quelques exemples de pending
    if pending_count > 0:
        print("Exemples d'offres en attente:")
        for doc in db[PENDING_COLLECTION_NAME].find().limit(5):
            print(f"  - {doc.get('reference', 'NO_REF')}: {doc.get('description', 'NO_DESC')[:60]}...")
        print()
    else:
        print("AUCUNE OFFRE EN ATTENTE DANS MONGODB!")
        print("Cela signifie que:")
        print("  1. Soit le scraping n'a jamais ete lance")
        print("  2. Soit les donnees ne sont PAS sauvegardees dans MongoDB")
        print("  3. Soit MongoDB a ete vide/reinitialise")
        print()

    # Afficher quelques exemples de validated
    if validated_count > 0:
        print("Exemples d'offres validees:")
        for doc in db[COLLECTION_NAME].find().limit(5):
            print(f"  - {doc.get('reference', 'NO_REF')}: {doc.get('description', 'NO_DESC')[:60]}...")
        print()

    print("=" * 80)
    print("VERIFICATION TERMINEE")
    print("=" * 80)

except Exception as e:
    print("=" * 80)
    print("ERREUR")
    print("=" * 80)
    print(f"Erreur: {e}")
    print()
    print("VERIFICATIONS:")
    print("1. MongoDB est-il demarre?")
    print("2. Le port 27017 est-il accessible?")
    print("3. La base de donnees existe-t-elle?")
    print("=" * 80)
