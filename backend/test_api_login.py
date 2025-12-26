#!/usr/bin/env python3
"""
Test de connexion à l'API AppelOffres avec les nouveaux identifiants
"""

import requests
import json
from scripts.tuneps_ao import EMAIL, API_PASSWORD, LOGIN_ENDPOINT, API_BASE_URL

def test_login():
    """Tester la connexion à l'API AppelOffres"""

    print("=" * 80)
    print("TEST DE CONNEXION API APPELOFFRES")
    print("=" * 80)
    print(f"\n📧 Email: {EMAIL}")
    print(f"🔑 Password: {API_PASSWORD[:5]}***")
    print(f"🌐 API Base URL: {API_BASE_URL}")
    print(f"🔗 Login Endpoint: {LOGIN_ENDPOINT}")
    print("\n" + "-" * 80)

    try:
        # Préparer les données de connexion
        login_data = {
            "email": EMAIL,
            "password": API_PASSWORD
        }

        print(f"\n📤 Envoi de la requête de login...")

        # Envoyer la requête
        response = requests.post(
            LOGIN_ENDPOINT,
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"📥 Réponse reçue: Status {response.status_code}")

        # Vérifier la réponse
        if response.status_code == 200:
            data = response.json()
            print("\n✅ CONNEXION RÉUSSIE !")
            print("\n📋 Détails de la réponse:")
            print(f"   - Access Token: {data.get('access_token', '')[:50]}...")

            if 'user' in data:
                user = data['user']
                print(f"   - User ID: {user.get('id')}")
                print(f"   - Email: {user.get('email')}")
                print(f"   - Nom: {user.get('first_name', '')} {user.get('last_name', '')}")

            print("\n🎉 Les identifiants sont corrects et fonctionnels !")
            return True

        elif response.status_code == 401:
            print("\n❌ ÉCHEC DE CONNEXION - Identifiants incorrects")
            print(f"   Message: {response.text}")
            return False

        else:
            print(f"\n⚠️  Erreur inattendue: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("\n❌ ERREUR DE CONNEXION")
        print("   Impossible de se connecter à l'API")
        print("   Vérifiez votre connexion internet")
        return False

    except requests.exceptions.Timeout:
        print("\n❌ TIMEOUT")
        print("   La requête a pris trop de temps")
        return False

    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_login()
    print("\n" + "=" * 80)

    if success:
        print("✅ Test réussi - Les identifiants sont valides")
        exit(0)
    else:
        print("❌ Test échoué - Vérifiez les identifiants")
        exit(1)
