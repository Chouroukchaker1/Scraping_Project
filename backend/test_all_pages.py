#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test all pages of MediaCongo"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup

def test_all_pages():
    base_url = "https://www.mediacongo.net/emplois-search--tri-offres_recentes-page-{}.html"

    print("="*80)
    print("TEST DE TOUTES LES PAGES MEDIACONGO")
    print("="*80)

    total_offers = 0

    for page_num in range(1, 6):  # Tester pages 1 à 5
        url = base_url.format(page_num)
        print(f"\nPage {page_num}: {url}")

        try:
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                print(f"  ✗ Erreur {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')

            if not table:
                print(f"  ✗ Pas de table trouvée")
                break

            rows = table.find_all('tr')[1:]  # Skip header
            print(f"  ✓ {len(rows)} offres trouvées")

            if len(rows) == 0:
                print(f"  → Fin de la pagination (page vide)")
                break

            total_offers += len(rows)

            # Afficher les 3 premières offres
            for i, row in enumerate(rows[:3], 1):
                cells = row.find_all('td')
                if len(cells) >= 5:
                    titre_cell = cells[1]
                    link = titre_cell.find('a')
                    if link:
                        title_elem = link.find('strong')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            id_elem = titre_cell.find('strong', class_='format_id_emploi')
                            job_id = id_elem.get_text(strip=True) if id_elem else "?"
                            date_str = cells[4].get_text(strip=True)
                            print(f"    {i}. [{job_id}] {title[:50]}... | Date: {date_str}")

        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            break

    print(f"\n{'='*80}")
    print(f"TOTAL: {total_offers} offres trouvées sur toutes les pages")
    print("="*80)

if __name__ == "__main__":
    test_all_pages()
