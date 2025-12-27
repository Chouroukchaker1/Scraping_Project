#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to check ReliefWeb HTML structure"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import re

def test_reliefweb_structure():
    url = "https://reliefweb.int/jobs?page=0"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        print("="*80)
        print("TESTING RELIEFWEB HTML STRUCTURE")
        print("="*80)

        # Test different selectors
        print("\n1. Looking for <article> with 'job' or 'listing' in class:")
        articles = soup.find_all('article', class_=re.compile(r'.*job.*|.*listing.*'))
        print(f"   Found: {len(articles)} articles")

        if articles:
            print("\n   First article classes:")
            print(f"   {articles[0].get('class')}")
            print("\n   First article HTML (first 500 chars):")
            print(f"   {str(articles[0])[:500]}")

            # Try to extract from first article
            article = articles[0]

            print("\n2. Looking for title (h3):")
            h3 = article.find('h3')
            print(f"   Found h3: {h3 is not None}")
            if h3:
                print(f"   h3 text: {h3.get_text(strip=True)}")

            print("\n3. Looking for title (h2):")
            h2 = article.find('h2')
            print(f"   Found h2: {h2 is not None}")
            if h2:
                print(f"   h2 text: {h2.get_text(strip=True)}")

            print("\n4. Looking for any <a> tags:")
            links = article.find_all('a', href=True)
            print(f"   Found {len(links)} links")
            if links:
                for i, link in enumerate(links[:3], 1):
                    print(f"   Link {i}: {link.get('href')}")
                    print(f"   Link {i} text: {link.get_text(strip=True)[:50]}")

            print("\n5. Looking for title in <a> tag:")
            title_link = article.find('a', class_=re.compile(r'.*title.*'))
            print(f"   Found title link: {title_link is not None}")
            if title_link:
                print(f"   Text: {title_link.get_text(strip=True)}")

        # Try alternative selector
        print("\n\n6. Alternative: <div> with 'job' or 'card' in class:")
        divs = soup.find_all('div', class_=re.compile(r'.*job.*|.*card.*'))
        print(f"   Found: {len(divs)} divs")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reliefweb_structure()
