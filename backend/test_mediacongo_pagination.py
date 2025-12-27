#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to check pagination on MediaCongo website"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup

def check_pagination():
    url = "https://www.mediacongo.net/emplois.html"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"Erreur: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # Chercher les éléments de pagination
        print("="*80)
        print("RECHERCHE DE PAGINATION SUR MEDIACONGO")
        print("="*80)

        # 1. Chercher des liens de pagination (page 1, 2, 3, etc.)
        pagination_links = soup.find_all('a', href=True)
        page_links = [a for a in pagination_links if 'page' in a.get('href', '').lower() or
                      any(char.isdigit() for char in a.get_text()) and len(a.get_text().strip()) <= 3]

        if page_links:
            print(f"\n✓ PAGINATION TROUVEE! {len(page_links)} liens de pagination detectes:")
            for link in page_links[:10]:
                print(f"  - {link.get_text().strip()}: {link.get('href')}")
        else:
            print("\n✗ Aucun lien de pagination classique trouve")

        # 2. Chercher des boutons "suivant", "précédent", "next", "previous"
        nav_keywords = ['next', 'prev', 'suivant', 'precedent', 'page']
        nav_elements = []
        for keyword in nav_keywords:
            nav_elements.extend(soup.find_all(text=lambda t: t and keyword.lower() in t.lower()))

        if nav_elements:
            print(f"\n✓ Elements de navigation trouves: {len(nav_elements)}")
            for elem in nav_elements[:5]:
                print(f"  - {elem.strip()[:50]}")

        # 3. Chercher des divs/sections de pagination
        pagination_divs = soup.find_all(['div', 'nav', 'ul'], class_=lambda c: c and 'paginat' in c.lower() if c else False)
        if pagination_divs:
            print(f"\n✓ Divs de pagination trouves: {len(pagination_divs)}")
            for div in pagination_divs:
                print(f"  - Class: {div.get('class')}")

        # 4. Compter le nombre total d'offres dans la table
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            print(f"\n✓ Table trouvee: {len(rows)} lignes (offres)")

        # 5. Chercher des informations sur le nombre total d'offres
        total_info = soup.find_all(text=lambda t: t and ('total' in t.lower() or 'résultats' in t.lower()))
        if total_info:
            print(f"\n✓ Informations sur le total:")
            for info in total_info[:3]:
                print(f"  - {info.strip()[:80]}")

        # 6. Afficher tous les liens pour analyse
        print(f"\n\nTOUS LES LIENS SUR LA PAGE:")
        print("-"*80)
        all_links = soup.find_all('a', href=True)
        emploi_links = [a for a in all_links if 'emploi' in a.get('href', '').lower()]
        print(f"Liens contenant 'emploi': {len(emploi_links)}")
        for link in emploi_links[:10]:
            print(f"  - {link.get('href')}")

        print(f"\n\n{'='*80}")
        print(f"RESUME:")
        print(f"- Offres visibles sur cette page: {len(rows) if table else 0}")
        print(f"- Liens de pagination: {len(page_links)}")
        print(f"- Elements de navigation: {len(nav_elements)}")
        print("="*80)

    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_pagination()
