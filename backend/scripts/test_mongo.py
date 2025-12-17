"""
Script de test pour vérifier la connexion MongoDB
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tunip")
DB_NAME = os.getenv("DB_NAME", "tunip")

print("="*80)
print("TEST DE CONNEXION MONGODB")
print("="*80)
print(f"URI: {MONGO_URI}")
print(f"Database: {DB_NAME}")
print()

try:
    print("Tentative de connexion...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    print("Test de ping...")
    client.admin.command('ping')

    print("✅ CONNEXION RÉUSSIE!")
    print()

    # Lister les bases de données
    print("Bases de données disponibles:")
    for db_name in client.list_database_names():
        print(f"  - {db_name}")
    print()

    # Vérifier la base de données cible
    db = client[DB_NAME]
    print(f"Collections dans '{DB_NAME}':")
    for coll_name in db.list_collection_names():
        count = db[coll_name].count_documents({})
        print(f"  - {coll_name}: {count} documents")
    print()

    # Test d'écriture
    print("Test d'écriture dans la collection 'test'...")
    test_coll = db['test']
    result = test_coll.insert_one({"test": "ok", "message": "Test de connexion"})
    print(f"✅ Document inséré avec ID: {result.inserted_id}")

    # Supprimer le document de test
    test_coll.delete_one({"_id": result.inserted_id})
    print("✅ Document de test supprimé")
    print()

    print("="*80)
    print("✅ TOUS LES TESTS SONT PASSÉS - MongoDB fonctionne correctement!")
    print("="*80)

except Exception as e:
    print("="*80)
    print("❌ ERREUR DE CONNEXION MONGODB")
    print("="*80)
    print(f"Erreur: {e}")
    print()
    print("SOLUTIONS POSSIBLES:")
    print("1. Vérifier que MongoDB est démarré:")
    print("   - Windows: Vérifier le service 'MongoDB' dans services.msc")
    print("   - Ou démarrer manuellement: mongod")
    print()
    print("2. Vérifier l'URI dans le fichier .env")
    print(f"   URI actuelle: {MONGO_URI}")
    print()
    print("3. Vérifier que le port 27017 est accessible")
    print("="*80)
