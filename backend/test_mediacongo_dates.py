#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to check dates on MediaCongo website"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
from datetime import datetime

def check_mediacongo_dates():
    url = "https://www.mediacongo.net/emplois.html"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')

        if not table:
            print("❌ No table found")
            return

        rows = table.find_all('tr')[1:]  # Skip header
        print(f"✅ Found {len(rows)} jobs on MediaCongo\n")
        print("="*80)

        for i, row in enumerate(rows[:10], 1):  # Show first 10
            cells = row.find_all('td')
            if len(cells) < 5:
                continue

            # Extract data
            titre_cell = cells[1]
            link = titre_cell.find('a')
            if not link:
                continue

            title_elem = link.find('strong')
            title = title_elem.get_text(strip=True) if title_elem else "N/A"

            id_elem = titre_cell.find('strong', class_='format_id_emploi')
            job_id = id_elem.get_text(strip=True) if id_elem else f"MC-{i}"

            promoter = cells[2].get_text(strip=True)
            location = cells[3].get_text(strip=True)
            date_str = cells[4].get_text(strip=True)

            # Parse date
            pub_date = "Unknown"
            try:
                date_parts = date_str.split('.')
                if len(date_parts) == 3:
                    pub_date_obj = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                    pub_date = pub_date_obj.strftime("%Y-%m-%d")
            except:
                pub_date = f"Parse error: {date_str}"

            print(f"{i}. [{job_id}] {title[:50]}...")
            print(f"   Company: {promoter}")
            print(f"   Location: {location}")
            print(f"   Date: {pub_date} (raw: {date_str})")
            print("-"*80)

        print(f"\n✅ Showing first 10 of {len(rows)} total jobs")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_mediacongo_dates()
