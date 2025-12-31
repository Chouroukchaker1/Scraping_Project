"""
Script pour extraire les pays disponibles depuis l'API appeloffres.net
"""
import requests
import json

# Configuration API
API_BASE_URL = "https://be.appeloffres.net/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
COUNTRIES_ENDPOINT = f"{API_BASE_URL}/country"

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

def get_countries(token):
    """Récupérer la liste des pays"""
    print(f"\n[COUNTRIES] Recuperation des pays...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    all_countries = []
    page = 1

    while True:
        params = {
            "page": page,
            "itemsPerPage": 200  # Maximum autorisé par l'API
        }

        response = requests.get(COUNTRIES_ENDPOINT, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()

            # L'API peut retourner un objet avec une clé 'data' ou 'items'
            if isinstance(data, dict):
                countries = data.get('data') or data.get('items') or data.get('results') or []
                total_pages = data.get('lastPage', 1)
            else:
                countries = data
                total_pages = 1

            all_countries.extend(countries)
            print(f"[OK] Page {page}/{total_pages}: {len(countries)} pays")

            if page >= total_pages:
                break

            page += 1
        else:
            print(f"[ERREUR] Erreur page {page}: {response.status_code} - {response.text}")
            break

    countries = all_countries
    print(f"\n[OK] Total: {len(countries)} pays trouves\n")

    print("=" * 80)
    print("LISTE DES PAYS:")
    print("=" * 80)

    for country in countries:
        if isinstance(country, dict):
            print(f"ID: {country.get('id', 'N/A'):<6} | Nom: {country.get('name', 'N/A')}")

    print("=" * 80)

    # Sauvegarder dans un fichier JSON
    with open('countries_api.json', 'w', encoding='utf-8') as f:
        json.dump(countries, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVE] Pays sauvegardes dans countries_api.json")

    # Créer un mapping nom -> ID pour faciliter la recherche
    country_mapping = {}
    for country in countries:
        if isinstance(country, dict):
            country_mapping[country.get('name', '').lower()] = country.get('id')

    with open('country_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(country_mapping, f, indent=2, ensure_ascii=False)
    print(f"[SAVE] Mapping pays sauvegarde dans country_mapping.json")

    return countries

def main():
    print("=" * 80)
    print("EXTRACTION DES PAYS DEPUIS L'API APPELOFFRES.NET")
    print("=" * 80)

    # Login
    token = login()
    if not token:
        print("\n[ERREUR] Impossible de continuer sans token")
        return

    # Récupérer les pays
    countries = get_countries(token)

    print("\n" + "=" * 80)
    print("[OK] EXTRACTION TERMINEE")
    print("=" * 80)
    print("\nFichiers crees:")
    print("  - countries_api.json (liste complete)")
    print("  - country_mapping.json (mapping nom -> ID)")

if __name__ == "__main__":
    main()
