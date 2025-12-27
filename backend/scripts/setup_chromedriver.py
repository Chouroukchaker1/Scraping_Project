#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour installer et configurer ChromeDriver automatiquement
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def setup_chromedriver():
    """Télécharge et configure ChromeDriver"""
    print("🔧 Installation de ChromeDriver...")

    try:
        # Télécharge ChromeDriver via webdriver-manager
        driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver installé à: {driver_path}")

        # Crée une variable d'environnement
        os.environ['CHROMEDRIVER_PATH'] = driver_path

        # Test rapide
        print("🧪 Test de ChromeDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            service=Service(driver_path),
            options=options
        )
        driver.get("https://www.google.com")
        print(f"✅ Test réussi! Titre de la page: {driver.title}")
        driver.quit()

        # Sauvegarde le chemin dans un fichier
        config_file = os.path.join(os.path.dirname(__file__), '.chromedriver_path')
        with open(config_file, 'w') as f:
            f.write(driver_path)
        print(f"✅ Chemin sauvegardé dans: {config_file}")

        return driver_path

    except Exception as e:
        print(f"❌ Erreur lors de l'installation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    path = setup_chromedriver()
    print(f"\n🎉 ChromeDriver configuré avec succès!")
    print(f"📍 Chemin: {path}")
    print(f"\nPour l'utiliser dans tuneps.py, ajoutez:")
    print(f"  chromedriver_path = '{path}'")
