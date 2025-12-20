"""
Flask App pour visualiser et lancer le scraping des Marchés Publics Bénin
Intègre le scraper Selenium existant. Templates HTML intégrés dans le fichier Python.
Améliorations:
- Extraction améliorée pour 'Autorité Contractante' avec regex flexible pour 'contractant(e)' et capture jusqu'à la prochaine section majuscule ou date/ref.
- Correction du SettingWithCopyWarning dans Pandas en utilisant .loc.
- Intégration MongoDB pour stockage des données extraites (remplace JSON).
- Suppression de la surcharge de 'Date_publication' par la date d'extraction : utilisation de la date extraite du site.
- Amélioration de l'extraction de la Description pour gérer les titres multi-lignes ou longs.
- Frontend inchangé, focus sur la correction du scraping et MongoDB.
- Correction spécifique pour 'Autorité Contractante' : utilise le contexte après label et capture jusqu'à fin de section.
- Nom de la base de données corrigé en "marches_publics_benin_scraping".
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
import os
import json
from datetime import datetime
import pandas as pd
import pymongo

# Configuration MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "marches_publics_benin_scraping")  # Nom corrigé pour éviter incohérences
COLLECTION_NAME = "appels_offres_scraping"

# Connexion MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Import du scraper (copié ici pour complétude)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re

class MarchesPublicsBeninScraper:
    def __init__(self, headless=False):
        self.base_url = "https://www.marches-publics.bj"
        self.appels_url = f"{self.base_url}/appels-doffres"
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Configure le driver Selenium"""
        chrome_options = Options()
 
        if self.headless:
            chrome_options.add_argument('--headless')
 
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--lang=fr-FR')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
 
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            print("✓ Driver Chrome initialisé avec succès")
        except Exception as e:
            print(f"✗ Erreur lors de l'initialisation du driver: {e}")
            raise
 
    def wait_for_page_load(self, timeout=20):
        """Attend que la page soit complètement chargée"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(3)  # Attente supplémentaire pour Angular/JavaScript
            return True
        except TimeoutException:
            print("⚠ Timeout lors du chargement de la page")
            return False
 
    def scroll_to_element(self, element):
        """Scroll vers un élément spécifique"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
        except:
            pass
 
    def extract_date_from_header(self, card):
        """Extrait la date limite et le délai depuis l'en-tête vert de la carte"""
        try:
            # En-tête avec fond vert contenant DATE LIMITE DE DÉPÔT et DÉLAI
            header_selectors = ["mat-card-header", ".mat-card-header", "[class*='header']", ".green-gradient"]
            header = None
            for selector in header_selectors:
                try:
                    header = card.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
 
            if not header:
                return "", ""
 
            header_text = header.text
 
            date_limite = ""
            delai = ""
 
            # Extrait la date limite (format: JJ-MM-AAAA à HHhMM)
            date_pattern = r'(\d{2}-\d{2}-\d{4}\s+à\s+\d{2}[hH]\d{2})'
            dates = re.findall(date_pattern, header_text)
            if dates:
                date_limite = dates[0]
 
            # Extrait le délai (format: XX jours)
            delai_pattern = r'(\d+\s+jours?)'
            delais = re.findall(delai_pattern, header_text, re.IGNORECASE)
            if delais:
                delai = delais[0]
 
            return date_limite, delai
        except:
            return "", ""
 
    def extract_from_mat_card_content(self, card):
        """Extrait les informations depuis le contenu de la carte - Amélioré pour Autorité Contractante et Description"""
        data = {}
 
        try:
            # Trouve le contenu principal de la carte
            content_selectors = ["mat-card-content", ".mat-card-content", ".content"]
            content = None
            for selector in content_selectors:
                try:
                    content = card.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
 
            if not content:
                # Fallback: utilise le texte de toute la carte
                content_text = card.text
            else:
                content_text = content.text
 
            lines = [line.strip() for line in content_text.split('\n') if line.strip()]
 
            # Description: Capture la première ligne descriptive longue (titre principal), ou concatène si multi-ligne
            description_lines = []
            in_description = False
            for line in lines:
                if len(line) > 30 and not any(re.search(kw, line, re.I) for kw in
                    ['DATE', 'DÉLAI', 'REF', 'AUTORITÉ', 'LIEU', 'PUBLICATION', 'ACQUISITION']):
                    if not in_description:
                        in_description = True
                    description_lines.append(line)
                else:
                    if in_description and description_lines:
                        break
                    in_description = False
 
            if description_lines:
                data['Description'] = ' '.join(description_lines).strip()
 
            # Parcourt les lignes pour extraire les informations
            i = 0
            while i < len(lines):
                line = lines[i]
 
                # Autorité contractante - Recherche plus robuste (peut être sur plusieurs lignes), regex flexible pour 'contractant(e)'
                if re.search(r'(?i)autorité\s+contractant(e)?', line):
                    autorite = line
                    i += 1
                    while i < len(lines) and len(lines[i]) > 5 and not re.search(r'(?i)(date|ref|lieu|description|publication|ouverture)', lines[i]):
                        autorite += " " + lines[i]
                        i += 1
                    data['Autorite_contractante'] = re.sub(r'(?i)autorité\s+contractant(e)?[:\s]*', '', autorite).strip()
                    continue
 
                # Date de publication (extraite du site, pas surchargée)
                if re.search(r'(?i)date\s+de\s+publication', line):
                    i += 1
                    if i < len(lines):
                        data['Date_publication'] = lines[i]
                        continue
 
                # Date d'ouverture des offres
                if re.search(r'(?i)date\s+d\'?ouverture\s+des\s+offres', line):
                    i += 1
                    if i < len(lines):
                        data['Date_ouverture_offres'] = lines[i]
                        continue
 
                # Référence
                if re.search(r'(?i)ref', line):
                    i += 1
                    if i < len(lines):
                        data['Ref'] = lines[i]
                        continue
 
                # Lieu d'acquisition
                if re.search(r'(?i)lieu\s+d\'?acquisition', line):
                    i += 1
                    if i < len(lines):
                        data['Lieu_acquisition'] = lines[i]
                        continue
 
                i += 1
 
            # Fallback pour Autorité Contractante si pas trouvé dans la boucle - Amélioré avec regex sur tout le texte, capture jusqu'à prochaine section
            if 'Autorite_contractante' not in data:
                # Regex flexible pour 'contractant(e)', capture jusqu'à prochaine ligne majuscule ou date/ref (non-greedy)
                autorite_pattern = r'(?i)(?:autorité\s+contractant(e)?|AUTORITÉ\s+CONTRACTANT(E)?)[:\s]*(.+?)(?=\n[A-Z]{3,}|\n\d{2}-\d{2}-\d{4}|\nREF|\nLIEU|\nDESCRIPTION|\n$date|\Z)'
                match = re.search(autorite_pattern, content_text, re.DOTALL | re.IGNORECASE)
                if match:
                    data['Autorite_contractante'] = match.group(3).strip()
                else:
                    # Dernier fallback: cherche dans la description ou lieu si contient mots-clés
                    if any(kw in content_text for kw in ['Ministère', 'Agence', 'Direction', 'Commune', 'Mairie', 'Centre', 'Hospitalier']):
                        # Extrait la ligne contenant ces mots après description
                        desc_pattern = r'(?i)(ministère|agence|direction|autorité|mairie|commune|centre\s+hospitalier)\s+([^\n]{10,})'
                        desc_match = re.search(desc_pattern, content_text)
                        if desc_match:
                            data['Autorite_contractante'] = desc_match.group(0).strip()
 
            # Fallback pour Description si pas capturée
            if 'Description' not in data or not data['Description']:
                # Cherche la première ligne longue après les en-têtes
                desc_pattern = r'(?i)(travaux|acquisition|équipements|construction|fourniture)[^\n]{20,}(?=\n[A-Z]{4,}|\nDate|\nRef)'
                desc_match = re.search(desc_pattern, content_text, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    data['Description'] = desc_match.group(0).strip()
 
        except Exception as e:
            print(f" ⚠ Erreur extraction contenu: {e}")
 
        return data
 
    def extract_pdf_link(self, card):
        """Extrait le lien PDF depuis le bouton TÉLÉCHARGER - Amélioré"""
        try:
            # Cherche tous les liens dans la carte
            links = card.find_elements(By.TAG_NAME, "a")
 
            for link in links:
                href = link.get_attribute('href')
                if href and '.pdf' in href.lower():
                    if href.startswith('/'):
                        return self.base_url + href
                    elif href.startswith('http'):
                        return href
                    else:
                        return self.base_url + '/' + href
 
                # Vérifie le texte du lien
                link_text = link.text.strip().upper()
                if 'TÉLÉCHARGER' in link_text or 'DOWNLOAD' in link_text:
                    href = link.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            return self.base_url + href
                        return href
 
            # Cherche les boutons avec onclick
            buttons = card.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                onclick = button.get_attribute('onclick')
                if onclick and '.pdf' in onclick:
                    pdf_match = re.search(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick)
                    if pdf_match:
                        pdf_url = pdf_match.group(1)
                        if pdf_url.startswith('/'):
                            return self.base_url + pdf_url
                        return pdf_url
 
            # Alternative: Cherche des data-attributes
            data_attrs = card.find_elements(By.CSS_SELECTOR, "[data-pdf], [data-url*='.pdf']")
            for elem in data_attrs:
                attr_val = elem.get_attribute('data-pdf') or elem.get_attribute('data-url')
                if attr_val and '.pdf' in attr_val:
                    if attr_val.startswith('/'):
                        return self.base_url + attr_val
                    return attr_val
 
            return "Lien non trouvé"
 
        except Exception as e:
            print(f" ⚠ Erreur extraction PDF: {e}")
            return "Erreur extraction"
 
    def extract_appels_from_current_page(self):
        """Extrait les appels d'offres de la page actuelle - VERSION OPTIMISÉE"""
        appels = []
 
        try:
            # Attend que les cartes soient chargées
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "mat-card"))
            )
 
            # Attente supplémentaire pour le rendu complet
            time.sleep(2)
 
            # Trouve tous les blocs mat-card
            cards = self.driver.find_elements(By.TAG_NAME, "mat-card")
            print(f" → {len(cards)} cartes trouvées")
 
            for idx, card in enumerate(cards, 1):
                try:
                    print(f"\n 📋 Extraction carte {idx}...")
 
                    # Scroll vers la carte
                    self.scroll_to_element(card)
 
                    # Initialise les données
                    appel_data = {}
 
                    # ÉTAPE 1: Extrait date limite et délai depuis l'en-tête
                    date_limite, delai = self.extract_date_from_header(card)
                    if date_limite:
                        appel_data['Date_limite_depot'] = date_limite
                        print(f" ✓ Date limite: {date_limite}")
                    if delai:
                        appel_data['Delai'] = delai
                        print(f" ✓ Délai: {delai}")
 
                    # ÉTAPE 2: Extrait les autres infos depuis le contenu
                    content_data = self.extract_from_mat_card_content(card)
                    appel_data.update(content_data)
 
                    # Affiche les données extraites (incluant Autorité Contractante et Description)
                    for key, value in content_data.items():
                        if value:
                            print(f" ✓ {key}: {value[:60]}..." if len(str(value)) > 60 else f" ✓ {key}: {value}")
 
                    # ÉTAPE 3: Extrait le lien PDF
                    pdf_link = self.extract_pdf_link(card)
                    appel_data['Lien_PDF'] = pdf_link
                    print(f" ✓ Lien PDF: {pdf_link}")
 
                    # Vérifie si on a des données valides
                    filled_fields = sum(1 for v in appel_data.values() if v and v not in ["", "Non trouvé", "Erreur extraction"])
 
                    if filled_fields >= 3:
                        appels.append(appel_data)
                        print(f" ✅ Carte {idx} extraite avec succès ({filled_fields} champs)")
                    else:
                        print(f" ⚠ Carte {idx} ignorée (seulement {filled_fields} champs valides)")
 
                except Exception as e:
                    print(f" ✗ Erreur carte {idx}: {e}")
                    continue
 
        except TimeoutException:
            print(" ✗ Timeout: les cartes ne se sont pas chargées")
        except Exception as e:
            print(f" ✗ Erreur lors de l'extraction: {e}")
 
        return appels
 
    def scrape_all_pages(self, max_pages=5):
        """Scrape plusieurs pages"""
        all_appels = []
 
        try:
            self.setup_driver()
 
            print(f"\nDébut du scraping de {self.appels_url}")
            self.driver.get(self.appels_url)
 
            if not self.wait_for_page_load():
                print("✗ La page n'a pas pu se charger correctement")
                return all_appels
 
            print("✓ Page chargée avec succès\n")
 
            for page in range(1, max_pages + 1):
                print(f"\n{'='*70}")
                print(f"📄 PAGE {page}")
                print(f"{'='*70}")
 
                # Scroll progressif pour charger tout le contenu
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
 
                # Extrait les données
                appels = self.extract_appels_from_current_page()
 
                if appels:
                    all_appels.extend(appels)
                    print(f"\n ✅ {len(appels)} appels extraits de la page {page}")
                    print(f" 📊 Total cumulé: {len(all_appels)} appels")
                else:
                    print(f"\n ⚠ Aucun appel extrait de la page {page}")
                    if page > 1:
                        print(" → Arrêt du scraping (plus de données)")
                        break
 
                # Essaie de passer à la page suivante
                if page < max_pages:
                    try:
                        print("\n → Recherche du bouton 'Suivant'...")
 
                        # Différentes méthodes pour trouver le bouton suivant
                        next_selectors = [
                            "//button[contains(@aria-label, 'Next')]",
                            "//button[contains(., 'Suivant')]",
                            "//button[contains(@class, 'mat-paginator-navigation-next')]",
                            "//mat-paginator//button[last()]"
                        ]
 
                        next_button = None
                        for selector in next_selectors:
                            try:
                                next_button = self.driver.find_element(By.XPATH, selector)
                                if next_button.is_enabled() and next_button.is_displayed():
                                    break
                            except:
                                continue
 
                        if next_button and next_button.is_enabled():
                            print(" ✓ Bouton 'Suivant' trouvé, navigation...")
                            next_button.click()
                            time.sleep(4)
                            self.wait_for_page_load()
                        else:
                            print(" → Dernière page atteinte (bouton désactivé)")
                            break
 
                    except Exception as e:
                        print(f" → Pas de page suivante ({e})")
                        break
 
        except Exception as e:
            print(f"\n✗ Erreur générale: {e}")
            import traceback
            traceback.print_exc()
 
        finally:
            if self.driver:
                self.driver.quit()
                print("\n✓ Navigateur fermé")
 
        return all_appels

# Flask App
app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Pour les flashes

# Variable globale pour stocker les données (chargée depuis MongoDB)
current_data = []

def load_data():
    """Charge les données depuis MongoDB"""
    global current_data
    current_data = list(collection.find())
    print(f"✓ {len(current_data)} documents chargés depuis MongoDB")

def save_data(data):
    """Sauvegarde les données dans MongoDB (insert_many pour accumulation, déduplication possible via Ref si besoin)"""
    global current_data
    if data:
        # Optionnel: Déduplication basique par Ref avant insertion
        existing_refs = {doc.get('Ref') for doc in current_data if doc.get('Ref')}
        new_data = [item for item in data if item.get('Ref') not in existing_refs]
 
        if new_data:
            collection.insert_many(new_data)
            print(f"✓ {len(new_data)} nouveaux documents insérés dans MongoDB")
            load_data()  # Recharge pour mise à jour
        else:
            print("✓ Aucune nouvelle donnée à insérer (déjà existantes)")

# Templates HTML intégrés - Améliorés avec pagination, recherche et tri
INDEX_TEMPLATE = """\
<!DOCTYPE html>\
<html lang="fr">\
<head>\
    <meta charset="UTF-8">\
    <meta name="viewport" content="width=device-width, initial-scale=1.0">\
    <title>Scraper Marchés Publics Bénin</title>\
    <style>\
        body { font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }\
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }\
        h1 { color: #007bff; text-align: center; }\
        form { margin: 20px 0; display: flex; flex-direction: column; gap: 10px; }\
        input[type="number"] { width: 100px; padding: 8px; }\
        button { padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; font-size: 16px; }\
        button:hover { background: #0056b3; }\
        .flash { padding: 12px; margin: 10px 0; border-radius: 4px; }\
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }\
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }\
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }\
        .stats { text-align: center; margin: 20px 0; font-size: 18px; color: #6c757d; }\
    </style>\
</head>\
<body>\
    <div class="container">\
        <h1>Extracteur d'Appels d'Offres - Marchés Publics Bénin</h1>\
        {% with messages = get_flashed_messages(with_categories=true) %}\
            {% if messages %}\
                {% for category, message in messages %}\
                    <div class="flash {{ category }}">{{ message }}</div>\
                {% endfor %}\
            {% endif %}\
        {% endwith %}\
        <p class="stats">Données actuelles: {{ data_len }} appels disponibles (depuis MongoDB).</p>\
        <form method="POST">\
            <label for="max_pages">Nombre de pages à scraper (défaut: 3, max: 10):</label>\
            <div style="display: flex; gap: 10px; align-items: center;">\
                <input type="number" id="max_pages" name="max_pages" value="3" min="1" max="10">\
                <button type="submit">Lancer le Scraping</button>\
            </div>\
        </form>\
        {% if data_len > 0 %}\
            <a href="{{ url_for('data') }}"><button>Voir les Données</button></a>\
        {% endif %}\
    </div>\
</body>\
</html>\
"""

DATA_TEMPLATE = """\
<!DOCTYPE html>\
<html lang="fr">\
<head>\
    <meta charset="UTF-8">\
    <meta name="viewport" content="width=device-width, initial-scale=1.0">\
    <title>Données Extraites</title>\
    <style>\
        body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }\
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }\
        h1 { color: #007bff; text-align: center; }\
        .controls { margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }\
        input[type="text"] { padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 200px; }\
        select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }\
        .back { margin: 20px 0; text-align: center; }\
        button { padding: 8px 16px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }\
        button:hover { background: #0056b3; }\
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }\
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }\
        th { background-color: #f2f2f2; cursor: pointer; user-select: none; }\
        th:hover { background-color: #e9ecef; }\
        tr:nth-child(even) { background-color: #f9f9f9; }\
        tr:hover { background-color: #e9ecef; }\
        a { color: #007bff; text-decoration: none; }\
        a:hover { text-decoration: underline; }\
        .pagination { text-align: center; margin: 20px 0; }\
        .pagination a, .pagination span { padding: 8px 12px; margin: 0 4px; border: 1px solid #ddd; border-radius: 4px; text-decoration: none; color: #007bff; }\
        .pagination a:hover { background: #007bff; color: white; }\
        .pagination .current { background: #007bff; color: white; }\
        .no-data { text-align: center; color: #6c757d; font-style: italic; }\
        @media (max-width: 768px) { .controls { flex-direction: column; align-items: stretch; } table { font-size: 14px; } th, td { padding: 8px; } }\
    </style>\
    <script>\
        function searchData() {\
            const query = document.getElementById('search').value;\
            window.location.href = '?search=' + encodeURIComponent(query) + '&page=1';\
        }\
        function sortTable(column) {\
            const direction = document.getElementById('sort_dir').value === 'asc' ? 'desc' : 'asc';\
            document.getElementById('sort_dir').value = direction;\
            window.location.href = '?sort=' + column + '&dir=' + direction + '&page=1';\
        }\
    </script>\
</head>\
<body>\
    <div class="container">\
        <h1>Appels d'Offres Extraits (Total: {{ total }})</h1>\
        <div class="controls">\
            <input type="text" id="search" placeholder="Rechercher..." value="{{ search_query }}" onkeypress="if(event.key==='Enter') searchData();">\
            <button onclick="searchData()">Rechercher</button>\
            <label>Tri par: </label>\
            <select onchange="sortTable(this.value)">\
                {% for col in columns %}\
                <option value="{{ col }}" {% if col == sort_col %}selected{% endif %}>{{ col }}</option>\
                {% endfor %}\
            </select>\
            <input type="hidden" id="sort_dir" value="{{ sort_dir }}">\
        </div>\
        <div class="back">\
            <a href="{{ url_for('index') }}"><button>Retour à l'Accueil</button></a>\
        </div>\
        {% if tables %}\
            {% for table in tables %}\
                {{ table|safe }}\
            {% endfor %}\
            <div class="pagination">\
                {% if prev_page %}\
                <a href="?page={{ prev_page }}&search={{ search_query }}&sort={{ sort_col }}&dir={{ sort_dir }}">Précédent</a>\
                {% endif %}\
                <span class="current">Page {{ current_page }} sur {{ total_pages }}</span>\
                {% if next_page %}\
                <a href="?page={{ next_page }}&search={{ search_query }}&sort={{ sort_col }}&dir={{ sort_dir }}">Suivant</a>\
                {% endif %}\
            </div>\
        {% else %}\
            <p class="no-data">Aucune donnée trouvée pour ce filtre.</p>\
        {% endif %}\
    </div>\
</body>\
</html>\
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        max_pages = int(request.form.get('max_pages', 3))
        try:
            print("Lancement du scraping...")
            scraper = MarchesPublicsBeninScraper(headless=False)  # Visible pour debug, changez à True en prod
            appels_offres = scraper.scrape_all_pages(max_pages=max_pages)
            if appels_offres:
                # NE PAS surcharger 'Date_publication' : garder la valeur extraite du site
                save_data(appels_offres)
                flash(f'Success! {len(appels_offres)} appels extraits et stockés en MongoDB.', 'success')
                return redirect(url_for('data'))
            else:
                flash('Erreur: Aucune donnée extraite.', 'error')
        except Exception as e:
            flash(f'Erreur lors du scraping: {str(e)}', 'error')
    load_data()
    return render_template_string(INDEX_TEMPLATE, data_len=len(current_data))

@app.route('/data')
def data():
    load_data()
    if not current_data:
        flash('Aucune donnée disponible. Lancez le scraping d\'abord.', 'info')
        return redirect(url_for('index'))
 
    # Paramètres de pagination et filtrage
    page = int(request.args.get('page', 1))
    per_page = 10
    search_query = request.args.get('search', '').lower()
    sort_col = request.args.get('sort', 'Date_limite_depot')
    sort_dir = request.args.get('dir', 'desc')
 
    # Convertir en DataFrame
    df = pd.DataFrame(current_data)
 
    # Colonnes d'affichage
    display_columns = ['Date_limite_depot', 'Delai', 'Ref', 'Description', 'Date_publication',
                       'Date_ouverture_offres', 'Autorite_contractante', 'Lieu_acquisition', 'Lien_PDF']
    existing_columns = [col for col in display_columns if col in df.columns]
    df_display = df[existing_columns].copy()
 
    # Recherche basique
    if search_query:
        mask = df_display.astype(str).apply(lambda row: row.str.contains(search_query, na=False).any(), axis=1)
        df_display = df_display[mask]
 
    # Tri
    if sort_col in df_display.columns:
        ascending = sort_dir == 'asc'
        df_display = df_display.sort_values(by=sort_col, ascending=ascending)
 
    # Pagination
    total = len(df_display)
    total_pages = (total + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_df = df_display.iloc[start_idx:end_idx]
 
    if paginated_df.empty:
        return render_template_string(DATA_TEMPLATE, tables=[], total=0, columns=existing_columns,
                                      current_page=1, total_pages=1, prev_page=None, next_page=None,
                                      search_query=search_query, sort_col=sort_col, sort_dir=sort_dir)
 
    # Rendre le lien PDF cliquable - Utilise .loc pour éviter le warning
    if 'Lien_PDF' in paginated_df.columns:
        paginated_df.loc[:, 'Lien_PDF'] = paginated_df['Lien_PDF'].apply(
            lambda x: f'<a href="{x}" target="_blank">Télécharger PDF</a>' if x and x != 'Lien non trouvé' else 'N/A'
        )
 
    table_html = paginated_df.to_html(classes='data', table_id='appels_table', escape=False, index=False)
 
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None
 
    return render_template_string(DATA_TEMPLATE, tables=[table_html], total=total, columns=existing_columns,
                                  current_page=page, total_pages=total_pages, prev_page=prev_page, next_page=next_page,
                                  search_query=search_query, sort_col=sort_col, sort_dir=sort_dir)

if __name__ == '__main__':
    load_data()  # Charge initial au démarrage
    app.run(debug=True, host='0.0.0.0', port=5009)