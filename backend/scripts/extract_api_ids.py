"""
Script pour extraire les sources et avis disponibles depuis l'API appeloffres.net
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration API
API_BASE_URL = "https://be.appeloffres.net/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
SOURCES_ENDPOINT = f"{API_BASE_URL}/source"
AVIS_ENDPOINT = f"{API_BASE_URL}/avis"

# Credentials BOAMP (qui fonctionnent pour l'API)
EMAIL = "oumayma.dahmani@tunipages.tn"
PASSWORD = "Ah0F553KKu0A"

def login():
    """Login et récupérer le token"""
    print(f"[LOGIN] Login avec {EMAIL}...")

    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    if response.status_code in [200, 201]:
        data = response.json()
        token = data.get("accessToken")
        print(f"[OK] Login reussi - Token obtenu")
        return token
    else:
        print(f"[ERREUR] Login echoue: {response.status_code} - {response.text}")
        return None

def get_sources(token):
    """Récupérer la liste des sources"""
    print(f"\n[SOURCES] Recuperation des sources...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "page": 1,
        "itemsPerPage": 200
    }

    response = requests.get(SOURCES_ENDPOINT, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        # L'API peut retourner un objet avec une clé 'data' ou 'items'
        if isinstance(data, dict):
            sources = data.get('data') or data.get('items') or data.get('results') or []
        else:
            sources = data

        print(f"[OK] {len(sources)} sources trouvees\n")

        print("=" * 80)
        print("LISTE DES SOURCES:")
        print("=" * 80)

        for source in sources:
            if isinstance(source, dict):
                print(f"ID: {source.get('id', 'N/A'):<6} | Nom: {source.get('name', 'N/A')}")
                if 'tunisia' in str(source.get('name', '')).lower() or 'tunisie' in str(source.get('name', '')).lower() or 'observatoire' in str(source.get('name', '')).lower() or 'haicop' in str(source.get('name', '')).lower():
                    print(f"        >>> POTENTIEL MATCH TUNISIE/HAICOP <<<")

        print("=" * 80)

        # Sauvegarder dans un fichier JSON
        with open('sources_api.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n[SAVE] Sources sauvegardees dans sources_api.json")

        return sources
    else:
        print(f"[ERREUR] Erreur recuperation sources: {response.status_code} - {response.text}")
        return []

def get_avis(token):
    """Récupérer la liste des types d'avis"""
    print(f"\n[AVIS] Recuperation des types d'avis...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "page": 1,
        "itemsPerPage": 200
    }

    response = requests.get(AVIS_ENDPOINT, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        # L'API peut retourner un objet avec une clé 'data' ou 'items'
        if isinstance(data, dict):
            avis = data.get('data') or data.get('items') or data.get('results') or []
        else:
            avis = data

        print(f"[OK] {len(avis)} types d'avis trouves\n")

        print("=" * 80)
        print("LISTE DES TYPES D'AVIS:")
        print("=" * 80)

        for av in avis:
            if isinstance(av, dict):
                print(f"ID: {av.get('id', 'N/A'):<6} | Nom: {av.get('name', 'N/A')}")
                # Afficher plus d'info si disponible
                if 'description' in av:
                    print(f"        Description: {av.get('description')}")

        print("=" * 80)

        # Sauvegarder dans un fichier JSON
        with open('avis_api.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n[SAVE] Types d'avis sauvegardes dans avis_api.json")

        return avis
    else:
        print(f"[ERREUR] Erreur recuperation avis: {response.status_code} - {response.text}")
        return []

def main():
    print("=" * 80)
    print("EXTRACTION DES SOURCES ET AVIS DEPUIS L'API APPELOFFRES.NET")
    print("=" * 80)

    # Login
    token = login()
    if not token:
        print("\n[ERREUR] Impossible de continuer sans token")
        return

    # Récupérer les sources
    sources = get_sources(token)

    # Récupérer les avis
    avis = get_avis(token)

    print("\n" + "=" * 80)
    print("[OK] EXTRACTION TERMINEE")
    print("=" * 80)
    print("\nFichiers crees:")
    print("  - sources_api.json")
    print("  - avis_api.json")
    print("\nCherchez 'Observatoire National des Marches Publics' ou 'HAICOP' dans sources_api.json")

if __name__ == "__main__":
    main()
