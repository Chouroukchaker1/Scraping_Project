import http.server
import socketserver
import threading
import json
import time
import requests
import pandas as pd
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
from textwrap import dedent
from pymongo import MongoClient
from typing import List, Optional, Dict
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
MONGO_URI = "mongodb://localhost:27017/ines"
DB_NAME = "worldbank_db-ines"
COLLECTION_NAME = "tenders_ines"
PENDING_COLLECTION_NAME = "pending_tenders_ines"

API_BASE_URL = "https://be.appeloffres.net/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"

EMAIL = "ines.mtiri@tunipages.tn"
PASSWORD = "InesMTIRI567@!"
DEFAULT_SOURCE_ID = 1464
DEFAULT_AVIS_ID = 8

COUNTRIES_MAP = {
    "angola": 9, "botswana": 32, "burundi": 38, "comoros": 51, "congo, dem. rep.": 177, "eritrea": 66,
    "eswatini": 67, "ethiopia": 68, "kenya": 106, "lesotho": 113, "madagascar": 123, "malawi": 125,
    "mauritius": 133, "mozambique": 142, "namibia": 144, "rwanda": 176, "seychelles": 190, "somalia": 195,
    "south africa": 4, "south sudan": 199, "tanzania": 214, "uganda": 156, "zambia": 229, "zimbabwe": 230,
    "benin": 26, "burkina faso": 37, "cameroon": 41, "cape verde": 43, "central african republic": 179,
    "chad": 45, "congo, rep.": 228, "côte d'ivoire": 58, "equatorial guinea": 83, "gabon": 72,
    "gambia, the": 73, "ghana": 74, "guinea": 82, "guinea-bissau": 84, "liberia": 117, "mali": 127,
    "mauritania": 134, "niger": 148, "nigeria": 149, "sao tome and principe": 187, "senegal": 188,
    "sierra leone": 191, "togo": 215
}

TRANSLATION_DICT = {
    'consultor para atualiza': 'Consultant pour la mise à jour', 'manual de opera': 'Manuel d\'opérations',
    'projecto': 'Projet', 'consultancy': 'Consultance', 'construction': 'Construction',
    'supply': 'Fourniture', 'services': 'Services', 'development': 'Développement',
    'project': 'Projet', 'implementation': 'Mise en œuvre', 'facilitation': 'Facilitation',
}

def translate_to_french(text: str) -> str:
    if not text:
        return text
    translated = text
    for eng, fr in TRANSLATION_DICT.items():
        translated = re.sub(re.escape(eng), fr, translated, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', translated).strip()

class TenderModel:
    def __init__(self):
        self.title = ""
        self.description = ""
        self.publicationDate = ""
        self.startBiddingDate = None
        self.expirationDate = ""
        self.openingBidsDate = None
        self.reference = ""
        self.specificationsPrice = ""
        self.offerValidityPeriode = None
        self.costEstimateMin = None
        self.costEstimateMax = None
        self.avisId = DEFAULT_AVIS_ID
        self.sourceId = DEFAULT_SOURCE_ID
        self.promoterId = None
        self.type = "international"
        self.nature = "public"
        self.isEnabled = False
        self.images = []
        self.specificationsReceivingAddress = ""
        self.fundingSourceType = "international"
        self.fundingSource = "Banque Mondiale"
        self.currencyId = None
        self.isMultiCurrency = False
        self.batches = []
        self.addresses = []
        self.createdAt = ""
        self.updatedAt = ""
        self.extractionDate = ""
        self.deletedAt = None
        self.status = "pending"
        self.full_content = ""
        self.pays = ""
        self.source = "Banque Mondiale"
        self.promoter = "Banque Mondiale"
        self.pieces_jointes = []
        self.cahier_charge = ""
        self.mots_cles_detectes = []
        self.avis = "Avis d'attribution"
        self.procedure = "N/A"
        self.type_marche = "Public"
        self.url_source = ""
        self.validationDate = None
        self.projet = ""
        self.intitule_projet = ""
        self.reference_offre_emprunteur = ""
        self.notice_id = ""

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

class WorldBankFinalExtractor:
    def __init__(self):
        self.api_url = "https://search.worldbank.org/api/v2/procnotices"
        self.base_project_url = "https://projects.banquemondiale.org/fr/projects-operations/procurement-detail/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
            'Referer': 'https://search.worldbank.org/procnotices',
            'Origin': 'https://search.worldbank.org',
        }
        self.start_date = None
        self.end_date = None
        self.seen_ids = set()
        self.all_contracts = []
        self.extraction_status = "Prêt"
        self.progress = 0
        self.current_step = ""
        self.results = []
        self.session = requests.Session()

    def set_date_range(self, start_date_str, end_date_str):
        self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        print(f"📅 Plage: {self.start_date.strftime('%d/%m/%Y')} au {self.end_date.strftime('%d/%m/%Y')}")

    def update_status(self, status, progress=None, step=""):
        self.extraction_status = status
        if progress is not None:
            self.progress = progress
        if step:
            self.current_step = step
        print(f"[{progress}%] {step}: {status}")

    def execute_complete_extraction(self):
        if self.start_date is None or self.end_date is None:
            self.update_status("Erreur: Dates non définies", 0, "Init")
            return None
        self.update_status("Extraction COMPLÈTE", 0, "Init")
        self.complete_extraction_all_contracts()
        return self.save_complete_results()

    def complete_extraction_all_contracts(self):
        self.update_status("Extraction TOUS les contrats", 10, "Extraction")
        self.update_status("Phase 1: Pagination", 15, "Phase 1")
        self.deep_pagination_unlimited()
        self.update_status("Phase 2: Pays", 40, "Phase 2")
        self.all_countries_parallel()
        self.update_status("Phase 3: Régions", 60, "Phase 3")
        self.all_regions_complete()
        self.update_status("Phase 4: Mots-clés", 75, "Phase 4")
        self.extended_keyword_search()
        self.update_status("Phase 5: Dates", 85, "Phase 5")
        self.all_date_variants()
        self.update_status("Phase 6: Vérification", 95, "Phase 6")
        self.final_complete_check()

    def deep_pagination_unlimited(self):
        year = self.start_date.year
        offset = 0
        rows = 200
        while True:
            progress = 15 + min(offset / 10000 * 20, 20)
            self.update_status(f"Offset {offset}", progress, "Phase 1")
            data = self.fetch_with_params({
                'os': offset, 'rows': rows, 'srt': 'publishdate', 'order': 'desc',
                'notice_type_exact': 'Contract Award', 'qterm': str(year),
            })
            if not data:
                break
            records = data.get('procnotices', [])
            if not records:
                break
            for record in records:
                if self.is_target_contract(record):
                    contract = self.enrich_contract_final(record)
                    self.add_contract(contract)
            oldest = self.get_oldest_date(records)
            if oldest and self.is_date_before_start(oldest):
                if offset > 2000:
                    break
            offset += rows
            if offset >= 20000:
                break

    def all_countries_parallel(self):
        countries = [
            'Angola', 'Botswana', 'Burundi', 'Comoros', 'Eritrea', 'Ethiopia', 'Kenya', 'Lesotho',
            'Madagascar', 'Malawi', 'Mauritius', 'Mozambique', 'Namibia', 'Rwanda', 'Seychelles',
            'Somalia', 'South Africa', 'South Sudan', 'Sudan', 'Eswatini', 'Tanzania', 'Uganda',
            'Zambia', 'Zimbabwe', 'Benin', 'Burkina Faso', 'Cameroon', 'Cape Verde',
            'Central African Republic', 'Chad', 'Congo', 'Democratic Republic of Congo',
            'Côte d\'Ivoire', 'Gabon', 'Gambia', 'Ghana', 'Guinea', 'Liberia', 'Mali',
            'Mauritania', 'Niger', 'Nigeria', 'Senegal', 'Sierra Leone', 'Togo',
        ]
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self.search_country_deep, c): c for c in countries}
            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass

    def search_country_deep(self, country):
        for offset in [0, 100, 200]:
            data = self.fetch_with_params({
                'os': offset, 'rows': 100,
                'qterm': f'{self.start_date.year} "{country}"',
                'notice_type_exact': 'Contract Award',
            })
            if data:
                for record in data.get('procnotices', []):
                    if self.is_target_contract(record):
                        self.add_contract(self.enrich_contract_final(record))

    def all_regions_complete(self):
        regions = ['Eastern and Southern Africa', 'Western and Central Africa', 'Africa',
                  'Sub-Saharan Africa', 'West Africa', 'East Africa', 'Southern Africa']
        for region in regions:
            for offset in [0, 100, 200]:
                data = self.fetch_with_params({
                    'os': offset, 'rows': 100,
                    'qterm': f'{self.start_date.year} "{region}"',
                    'notice_type_exact': 'Contract Award',
                })
                if data:
                    for record in data.get('procnotices', []):
                        if self.is_target_contract(record):
                            self.add_contract(self.enrich_contract_final(record))

    def extended_keyword_search(self):
        keywords = ['procurement', 'contract', 'tender', 'construction', 'supply', 'consultancy']
        for kw in keywords:
            for offset in [0, 100]:
                data = self.fetch_with_params({
                    'os': offset, 'rows': 100,
                    'qterm': f'{self.start_date.year} {kw}',
                    'notice_type_exact': 'Contract Award',
                })
                if data:
                    for record in data.get('procnotices', []):
                        if self.is_target_contract(record):
                            self.add_contract(self.enrich_contract_final(record))

    def all_date_variants(self):
        current = self.start_date
        variants = []
        while current <= self.end_date:
            variants.extend([current.strftime('%d-%b-%Y'), current.strftime('%Y-%m-%d')])
            current += timedelta(days=1)
        for var in variants[:20]:
            data = self.fetch_with_params({
                'os': 0, 'rows': 100, 'qterm': f'"{var}"',
                'notice_type_exact': 'Contract Award',
            })
            if data:
                for record in data.get('procnotices', []):
                    if self.is_target_contract(record):
                        self.add_contract(self.enrich_contract_final(record))

    def final_complete_check(self):
        checks = [
            {'qterm': f'{self.start_date.strftime("%Y-%m-%d")} Africa', 'rows': 200},
            {'qterm': f'Contract Award {self.start_date.strftime("%B")}', 'rows': 100},
        ]
        for check in checks:
            data = self.fetch_with_params({'os': 0, **check})
            if data:
                for record in data.get('procnotices', []):
                    if self.is_target_contract(record):
                        self.add_contract(self.enrich_contract_final(record))

    def fetch_with_params(self, custom_params):
        try:
            params = {'format': 'json', 'apilang': 'en', 'srce': 'both', **custom_params}
            response = self.session.get(self.api_url, params=params, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def is_target_contract(self, record):
        date_str = record.get('noticedate', '')
        if not self.is_in_target_period(date_str):
            return False
        country = record.get('project_ctry_name', '') or record.get('country', '')
        return self.is_target_region(country)

    def is_in_target_period(self, date_str):
        if not date_str or not self.start_date or not self.end_date:
            return False
        try:
            for fmt in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return self.start_date <= dt <= self.end_date
                except:
                    continue
        except:
            pass
        return False

    def is_target_region(self, country):
        if not country:
            return False
        text = str(country).lower()
        if ('eastern' in text and 'southern' in text) or ('western' in text and 'central' in text):
            return True
        return any(p in text for p in [
            'angola', 'botswana', 'burundi', 'comoros', 'eritrea', 'ethiopia', 'kenya',
            'lesotho', 'madagascar', 'malawi', 'mauritius', 'mozambique', 'namibia',
            'rwanda', 'seychelles', 'somalia', 'south africa', 'tanzania', 'uganda',
            'zambia', 'zimbabwe', 'benin', 'burkina', 'cameroon', 'chad', 'congo',
            'gabon', 'gambia', 'ghana', 'guinea', 'liberia', 'mali', 'niger', 'nigeria', 'senegal', 'togo'
        ])

    def get_region(self, country):
        if not country:
            return 'Unknown'
        cl = str(country).lower()
        if 'eastern' in cl and 'southern' in cl:
            return 'Eastern and Southern Africa'
        elif 'western' in cl and 'central' in cl:
            return 'Western and Central Africa'
        east_south = ['angola', 'botswana', 'burundi', 'comoros', 'eritrea', 'ethiopia',
                      'kenya', 'lesotho', 'madagascar', 'malawi', 'mauritius', 'mozambique',
                      'namibia', 'rwanda', 'seychelles', 'somalia', 'south africa', 'tanzania', 'uganda', 'zambia', 'zimbabwe']
        return 'Eastern and Southern Africa' if any(c in cl for c in east_south) else 'Western and Central Africa'

    def extract_promoter_selenium(self, project_url):
        """
        EXTRACTION AVEC SELENIUM pour page Angular
        Attend que le contenu JavaScript soit chargé
        """
        if not project_url or project_url == 'URL_NON_DISPO':
            return 'Non disponible'
        
        driver = None
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            
            driver = webdriver.Chrome(options=options)
            driver.get(project_url)
            
            # Attendre que la page Angular charge
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)  # Temps supplémentaire pour Angular
            
            # Méthode 1: Chercher par XPATH précis
            try:
                # XPath: trouver label "Intitulé du Projet" puis le <p> suivant
                xpath_query = "//label[contains(text(), 'Intitulé du Projet')]/following-sibling::p[@class='document-info']"
                element = driver.find_element(By.XPATH, xpath_query)
                promoter = element.text.strip()
                if len(promoter) > 10:
                    print(f"✅ PROMOTEUR SELENIUM (XPath): {promoter[:80]}")
                    driver.quit()
                    return promoter[:200]
            except:
                pass
            
            # Méthode 2: Chercher dans tout le HTML après chargement
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Chercher <p class="document-info">
            doc_info_elements = soup.find_all('p', class_='document-info')
            for elem in doc_info_elements:
                # Vérifier si c'est après un label "Intitulé du Projet"
                prev_label = elem.find_previous('label')
                if prev_label and 'intitulé' in prev_label.get_text().lower():
                    promoter = elem.get_text(strip=True)
                    if len(promoter) > 10:
                        print(f"✅ PROMOTEUR SELENIUM (class): {promoter[:80]}")
                        driver.quit()
                        return promoter[:200]
            
            # Méthode 3: Pattern regex dans le texte complet
            page_text = soup.get_text()
            patterns = [
                r'Intitulé\s+du\s+Projet\s*[:.\s]*([^\n\r]{15,200})',
                r'Project\s+Title\s*[:.\s]*([^\n\r]{15,200})',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    clean = re.sub(r'\s+', ' ', match.strip())
                    if len(clean) > 15 and 'intitulé' not in clean.lower():
                        print(f"✅ PROMOTEUR SELENIUM (pattern): {clean[:80]}")
                        driver.quit()
                        return clean[:200]
            
            # Fallback: titre
            title = driver.title
            clean_title = re.sub(r' - Banque.*| - World.*|Procurement.*|Détails.*', '', title).strip()
            if len(clean_title) > 10:
                print(f"⚠️ PROMOTEUR (fallback titre): {clean_title[:80]}")
                driver.quit()
                return clean_title[:200]
            
            driver.quit()
            return 'Intitulé non trouvé'
        except Exception as e:
            if driver:
                driver.quit()
            print(f"❌ Erreur Selenium: {e}")
            return f'Erreur: {str(e)}'

    def enrich_contract_final(self, record):
        country = record.get('project_ctry_name', '') or record.get('country', '')
        notice_number = self.extract_notice_number(record)
        full_url = self.build_complete_url(notice_number)
        
        # EXTRACTION AVEC SELENIUM
        promoter_exact = self.extract_promoter_selenium(full_url)
        
        promoter_fr = translate_to_french(promoter_exact)
        description = translate_to_french(record.get('bid_description') or record.get('project_name') or 'N/A')
        
        return {
            'description': description, 'country': country, 'date': record.get('noticedate', 'N/A'),
            'reference': record.get('bid_reference_no', 'N/A'), 'notice_number': notice_number,
            'project_id': record.get('project_id', 'N/A'),
            'project_name': translate_to_french(record.get('project_name', 'N/A')),
            'url': full_url, 'region': self.get_region(country),
            'notice_type': record.get('notice_type', 'N/A'),
            'language': record.get('notice_lang_name', 'N/A'),
            'date_limite': self.calculate_date_limite(record.get('noticedate', '')),
            'intitule_projet_complet': promoter_fr,
            'promoter_name': promoter_fr,
        }

    def extract_notice_number(self, record):
        url = record.get('url', '')
        if url and 'procurement-detail/' in url:
            match = re.search(r'procurement-detail/([^/?]+)', url)
            if match:
                return match.group(1)
        for field in [record.get('notice_no', ''), record.get('bid_reference_no', ''),
                     record.get('project_id', ''), record.get('id', '')]:
            if field and len(field) > 5:
                clean = str(field).strip()
                if re.match(r'^[A-Z]{2}\d+', clean) or re.match(r'^\d+$', clean):
                    return clean
        return f"NOTICE_{record.get('id', '')}" if record.get('id') else 'NON_DISPO'

    def build_complete_url(self, notice_number):
        if not notice_number or notice_number == 'NON_DISPO':
            return 'URL_NON_DISPO'
        clean = str(notice_number).strip()
        return clean if clean.startswith('http') else f"{self.base_project_url}{clean}"

    def calculate_date_limite(self, pub_date):
        if not pub_date:
            return 'N/A'
        try:
            for fmt in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    pd = datetime.strptime(pub_date, fmt)
                    return (pd + timedelta(days=30)).strftime('%d/%m/%Y')
                except:
                    continue
        except:
            pass
        return 'N/A'

    def add_contract(self, contract):
        cid = f"{contract.get('project_id')}|{contract.get('reference')}|{contract.get('date')}"
        if cid not in self.seen_ids:
            self.seen_ids.add(cid)
            self.all_contracts.append(contract)
            return True
        return False

    def get_oldest_date(self, records):
        dates = [r.get('noticedate', '') for r in records if r.get('noticedate')]
        return min(dates) if dates else None

    def is_date_before_start(self, date_str):
        if not date_str:
            return False
        try:
            for fmt in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str, fmt) < self.start_date
                except:
                    continue
        except:
            pass
        return False

    def save_complete_results(self):
        self.update_status("Sauvegarde", 98, "Finalisation")
        if not self.all_contracts:
            self.update_status("Aucune donnée", 100, "Terminé")
            return None
        
        self.all_contracts.sort(key=lambda x: (x['country'], x['description']))
        data = []
        for idx, contract in enumerate(self.all_contracts, 1):
            data.append({
                'ID': idx, 'Description': contract['description'][:500],
                'Pays/Région': contract['country'], 'Date de publication': contract['date'],
                'Date limite': contract['date_limite'], 'Région': contract['region'],
                'Référence contrat': contract['reference'], 'Numéro d\'avis': contract['notice_number'],
                'ID Projet': contract['project_id'], 'Intitulé du Projet': contract['project_name'],
                'Intitulé Complet du Projet': contract['intitule_projet_complet'],
                'Promoteur': contract['promoter_name'], 'Type d\'avis': contract['notice_type'],
                'Langue': contract['language'], 'URL complète': contract['url'],
                'Source': 'Extraction SELENIUM', 'status': 'pending'
            })
        
        start_str = self.start_date.strftime("%d_%m_%Y")
        end_str = self.end_date.strftime("%d_%m_%Y")
        filename = f'CONTRATS_{start_str}_AU_{end_str}_SELENIUM.xlsx'
        
        try:
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"✅ Fichier: {filename}")
            print(f"✅ Contrats: {len(data)}")
            
            client = MongoClient(MONGO_URI)
            db = client[DB_NAME]
            pending = db[PENDING_COLLECTION_NAME]
            coll = db[f'contracts_{start_str}_to_{end_str.replace("/","_")}']
            
            for item in data:
                coll.replace_one({'Référence contrat': item['Référence contrat']}, item, upsert=True)
            for item in data:
                tender = self.map_to_tender_model(item)
                tender['extraction_status'] = 'pending'
                pending.replace_one({'reference': tender['reference']}, tender, upsert=True)
            
            client.close()
            self.results = data
            self.update_status(f"✅ {len(data)} contrats extraits!", 100, "Terminé")
            return df
        except Exception as e:
            self.update_status(f"Erreur: {e}", 100, "Erreur")
            return None

    def map_to_tender_model(self, contract_data: Dict) -> Dict:
        cl = contract_data.get('Pays/Région', '').lower().strip()
        cid = int(COUNTRIES_MAP.get(cl, 1))
        
        pub = contract_data.get('Date de publication', '')
        exp = contract_data.get('Date limite', '')
        
        try:
            pub_dt = datetime.strptime(pub, '%d/%m/%Y') if '/' in pub else datetime.strptime(pub, '%d-%b-%Y')
            pub_iso = pub_dt.isoformat()
            start_iso = (pub_dt + timedelta(days=1)).isoformat()
            open_iso = pub_dt.isoformat()
        except:
            pub_iso = pub
            start_iso = None
            open_iso = None
        
        try:
            exp_dt = datetime.strptime(exp, '%d/%m/%Y') if '/' in exp else datetime.strptime(exp, '%d-%b-%Y')
            exp_iso = exp_dt.isoformat()
        except:
            exp_iso = exp
        
        t = TenderModel()
        t.title = translate_to_french(contract_data.get('Intitulé Complet du Projet', '') or contract_data.get('Description', '')[:100])
        t.description = translate_to_french(contract_data.get('Description', ''))
        t.full_content = t.description
        t.publicationDate = pub_iso
        t.startBiddingDate = start_iso
        t.expirationDate = exp_iso
        t.openingBidsDate = open_iso
        t.reference = contract_data.get('Référence contrat', '')
        t.specificationsReceivingAddress = contract_data.get('URL complète', '')
        t.promoter = translate_to_french(contract_data.get('Promoteur', 'Banque Mondiale'))
        t.batches = [{"activitiesIds": [], "title": t.description, "deposit": 0}]
        t.addresses = [{"countryId": cid}]
        t.pays = cid
        t.cahier_charge = contract_data.get('URL complète', '')
        t.url_source = contract_data.get('URL complète', '')
        t.validationDate = datetime.now().isoformat()
        t.projet = translate_to_french(contract_data.get('Intitulé du Projet', ''))
        t.intitule_projet = translate_to_french(contract_data.get('Intitulé Complet du Projet', ''))
        t.reference_offre_emprunteur = contract_data.get('Référence contrat', '')
        t.notice_id = contract_data.get('Numéro d\'avis', '')
        
        return t.to_dict()

    def run_complete_extraction(self):
        self.update_status("Extraction SELENIUM", 0, "Démarrage")
        start = time.time()
        df = self.execute_complete_extraction()
        end = time.time()
        print(f"⏱️ Temps: {end - start:.2f}s")
        return {
            'success': df is not None,
            'contracts_count': len(self.all_contracts),
            'execution_time': end - start,
            'results': self.results
        }

# Serveur HTTP (rester identique au précédent - juste changer le nom de la classe)
class ExtractionHandler(http.server.SimpleHTTPRequestHandler):
    extractor = WorldBankFinalExtractor()
    extraction_thread = None
    extraction_results = None
    auth_token = None
    promoters_list = None
    promoters_dict = {}

    def login_to_api(self):
        if self.auth_token:
            return True
        try:
            response = requests.post(LOGIN_ENDPOINT, json={'email': EMAIL, 'password': PASSWORD}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result and isinstance(result, dict):
                    self.auth_token = result.get('accessToken') or result.get('access_token') or result.get('token')
                    if self.auth_token:
                        return True
            return False
        except:
            return False

    def load_promoters_list(self):
        if self.promoters_list is not None:
            return True
        if not self.login_to_api():
            return False
        try:
            response = requests.get(PROMOTER_ENDPOINT,
                                   headers={'Authorization': f'Bearer {self.auth_token}'},
                                   params={'page': 1, 'itemsPerPage': 500}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self.promoters_list = result.get('data', []) if result else []
                for p in self.promoters_list:
                    name = p.get('name', '').lower()
                    pid = p.get('id')
                    if name and pid:
                        self.promoters_dict[name] = pid
                if self.promoters_list:
                    df = pd.DataFrame([{'ID': p.get('id'), 'Nom': p.get('name')} for p in self.promoters_list])
                    df.to_excel('PROMOTEURS_LISTE.xlsx', index=False, engine='openpyxl')
                return True
            return False
        except:
            return False

    def find_or_create_promoter(self, name: str):
        if not name or name in ['Non disponible', 'Intitulé non trouvé', 'Erreur']:
            name = 'Banque Mondiale'
        if not self.load_promoters_list():
            return None
        nl = name.lower()
        if nl in self.promoters_dict:
            return self.promoters_dict[nl]
        for en, pid in self.promoters_dict.items():
            if nl in en or en in nl:
                return pid
        return self.create_new_promoter(name)

    def create_new_promoter(self, name: str):
        if not self.login_to_api():
            return None
        try:
            response = requests.post(PROMOTER_ENDPOINT,
                                    json={'companyName': name,
                                          'address': {'street': 'Projet BM', 'city': 'Cap', 'state': 'Rég',
                                                     'postalCode': '00000', 'country': 'Afrique'},
                                          'description': f'Projet: {name}'},
                                    headers={'Authorization': f'Bearer {self.auth_token}'}, timeout=10)
            if response.status_code == 201:
                result = response.json()
                if result:
                    pid = result.get('id')
                    self.promoters_dict[name.lower()] = pid
                    self.promoters_list.append({'id': pid, 'name': name})
                    df = pd.DataFrame([{'ID': p.get('id'), 'Nom': p.get('name')} for p in self.promoters_list])
                    df.to_excel('PROMOTEURS_LISTE.xlsx', index=False, engine='openpyxl')
                    return pid
        except:
            pass
        return None

    def map_to_tender_model(self, cd: Dict) -> Dict:
        return self.extractor.map_to_tender_model(cd)

    def extract_attachments_and_upload(self, url: str) -> List[str]:
        if not url or url == 'URL_NON_DISPO':
            return []
        filenames = []
        folder = 'banquemondiale'
        os.makedirs(folder, exist_ok=True)
        driver = None
        try:
            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=opts)
            driver.get(url)
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            lp = os.path.join(folder, f"sc_{ts}.png")
            driver.save_screenshot(lp)
            if not self.login_to_api():
                return []
            with open(lp, 'rb') as f:
                ur = requests.post(FILES_ENDPOINT,
                                  headers={'Authorization': f'Bearer {self.auth_token}'},
                                  files={'file': (f"sc_{ts}.png", f, 'image/png')}, timeout=10)
            if ur.status_code in [200, 201]:
                s3 = ur.json().get('url', '')
                if s3:
                    parsed = urllib.parse.urlparse(s3)
                    path = parsed.path.replace('/tender-s3', '', 1).lstrip('/')
                    if path.startswith('-prod/'):
                        path = path[5:]
                    path = path.lstrip('/')
                    if path:
                        filenames.append(path)
            os.remove(lp)
            return filenames
        except:
            return []
        finally:
            if driver:
                driver.quit()

    def create_tender(self, td: Dict) -> bool:
        if not self.login_to_api():
            return False
        pn = td.get('promoter', 'Banque Mondiale')
        pid = self.find_or_create_promoter(pn)
        if not pid:
            return False
        td['promoterId'] = int(pid)
        purl = td.get('specificationsReceivingAddress', '')
        s3 = self.extract_attachments_and_upload(purl)
        td['images'] = [i.lstrip('/') for i in s3]
        keys = ["title", "description", "publicationDate", "startBiddingDate", "expirationDate",
                "openingBidsDate", "reference", "specificationsPrice", "offerValidityPeriode",
                "costEstimateMin", "costEstimateMax", "avisId", "sourceId", "promoterId",
                "type", "nature", "isEnabled", "images", "specificationsReceivingAddress",
                "fundingSourceType", "fundingSource", "currencyId", "isMultiCurrency",
                "batches", "addresses"]
        for attempt in range(2):
            try:
                payload = {k: v for k, v in td.items() if k in keys}
                resp = requests.post(TENDER_ENDPOINT, json=payload,
                                    headers={'Authorization': f'Bearer {self.auth_token}'}, timeout=10)
                if resp.status_code in [200, 201]:
                    client = MongoClient(MONGO_URI)
                    db = client[DB_NAME]
                    db[PENDING_COLLECTION_NAME].update_one({'reference': td['reference']},
                                                           {'$set': {'status': 'validated'}})
                    db[COLLECTION_NAME].replace_one({'reference': td['reference']}, td, upsert=True)
                    client.close()
                    return True
                elif resp.status_code == 500 and attempt < 1:
                    if 'addresses' in payload and payload['addresses']:
                        payload['addresses'][0]['countryId'] = 1
                        time.sleep(0.5)
                        continue
                else:
                    return False
            except:
                if attempt < 1:
                    time.sleep(0.5)
                else:
                    return False
        return False

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_html().encode('utf-8'))
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': self.extractor.extraction_status,
                'progress': self.extractor.progress,
                'step': self.extractor.current_step,
                'contracts_count': len(self.extractor.all_contracts)
            }).encode('utf-8'))
        elif self.path == '/results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'results': self.extractor.results,
                                        'total_count': len(self.extractor.results)},
                                       ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/start':
            cl = int(self.headers['Content-Length'])
            pd = self.rfile.read(cl)
            data = json.loads(pd.decode('utf-8'))
            if data.get('startDate') and data.get('endDate'):
                self.extractor.set_date_range(data['startDate'], data['endDate'])
            if self.extraction_thread is None or not self.extraction_thread.is_alive():
                self.extraction_thread = threading.Thread(target=self.run_extraction)
                self.extraction_thread.start()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False}).encode('utf-8'))
        elif self.path == '/validate':
            cl = int(self.headers['Content-Length'])
            pd = self.rfile.read(cl)
            cd = json.loads(pd.decode('utf-8'))
            td = self.map_to_tender_model(cd)
            success = self.create_tender(td)
            self.send_response(200 if success else 400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': success}).encode('utf-8'))
        else:
            self.send_error(404)

    def run_extraction(self):
        self.extraction_results = self.extractor.run_complete_extraction()

    def get_html(self):
        return dedent("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Extracteur SELENIUM - Promoteur EXACT</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI'; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
       min-height: 100vh; padding: 20px; }
.container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 15px;
             box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
.header { background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white;
          padding: 30px; text-align: center; }
.header h1 { font-size: 2.5rem; margin-bottom: 10px; }
.content { padding: 30px; }
.panel { background: #f8f9fa; border-radius: 10px; padding: 25px; margin-bottom: 30px; }
.btn { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; border: none;
       padding: 12px 30px; border-radius: 25px; font-size: 1.1rem; cursor: pointer; font-weight: 600; }
.btn:hover { transform: translateY(-2px); }
.btn:disabled { background: #95a5a6; cursor: not-allowed; }
.btn-validate { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); padding: 8px 16px;
                font-size: 0.9rem; }
.btn-validate.success { background: linear-gradient(135deg, #27ae60 0%, #229954 100%); }
.progress-container { background: #e9ecef; border-radius: 10px; height: 20px; margin: 20px 0; }
.progress-bar { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); height: 100%;
                width: 0%; transition: width 0.3s; }
.status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
.status-item { background: #fff; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th { background: #34495e; color: white; padding: 12px; text-align: left; }
td { padding: 12px; border-bottom: 1px solid #e9ecef; }
tr:hover { background: #f8f9fa; }
input[type="date"] { padding: 8px; border: 1px solid #ddd; border-radius: 5px; width: 200px; margin-right: 10px; }
.notice { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 8px;
          margin-bottom: 20px; color: #155724; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🎯 Extracteur SELENIUM - Promoteur EXACT</h1>
<p>Extraction avec Selenium pour pages Angular + Promoteur depuis HTML chargé</p>
</div>
<div class="content">
<div class="notice">
<strong>🚀 SELENIUM:</strong><br>
✅ Attend que JavaScript/Angular charge la page<br>
✅ Extrait "Intitulé du Projet" depuis `&lt;p class="document-info"&gt;`<br>
✅ Promoteur = Intitulé exact depuis HTML chargé<br>
✅ TOUS les contrats extraits
</div>
<div class="panel">
<h2>📊 Extraction</h2>
<div style="margin: 15px 0;">
<label>Dates :</label>
<div style="display: flex; align-items: center; gap: 10px;">
<input type="date" id="startDateInput" value="2025-12-10">
<span>au</span>
<input type="date" id="endDateInput" value="2025-12-10">
</div>
</div>
<button id="startBtn" class="btn">🚀 Démarrer</button>
</div>
<div class="panel">
<h2>📈 Statut</h2>
<div class="progress-container">
<div id="progressBar" class="progress-bar"></div>
</div>
<div class="status-grid">
<div class="status-item">
<div style="font-weight: 600;">Statut</div>
<div id="statusText" style="font-size: 1.1rem; color: #3498db;">Prêt</div>
</div>
<div class="status-item">
<div style="font-weight: 600;">Progression</div>
<div id="progressText" style="font-size: 1.1rem; color: #3498db;">0%</div>
</div>
<div class="status-item">
<div style="font-weight: 600;">Étape</div>
<div id="stepText" style="font-size: 1.1rem; color: #3498db;">-</div>
</div>
<div class="status-item">
<div style="font-weight: 600;">Contrats</div>
<div id="contractsCount" style="font-size: 1.1rem; color: #3498db;">0</div>
</div>
</div>
</div>
<div class="panel">
<h2>📋 Résultats</h2>
<div id="resultsContainer">
<p>En attente...</p>
<div id="resultsContent" style="display: none;">
<table id="contractsTable">
<thead>
<tr>
<th>ID</th><th>Description</th><th>Pays</th><th>Date</th><th>Promoteur</th><th>URL</th><th>Actions</th>
</tr>
</thead>
<tbody id="contractsBody"></tbody>
</table>
</div>
</div>
</div>
</div>
</div>
<script>
let si;
function start() {
const btn = document.getElementById('startBtn');
btn.disabled = true;
btn.innerHTML = '⏳ En cours...';
si = setInterval(updateStatus, 1000);
fetch('/start', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({
startDate: document.getElementById('startDateInput').value,
endDate: document.getElementById('endDateInput').value
})
});
}
function updateStatus() {
fetch('/status').then(r => r.json()).then(d => {
document.getElementById('statusText').textContent = d.status;
document.getElementById('progressText').textContent = d.progress + '%';
document.getElementById('stepText').textContent = d.step;
document.getElementById('contractsCount').textContent = d.contracts_count;
document.getElementById('progressBar').style.width = d.progress + '%';
if (d.progress === 100) {
clearInterval(si);
document.getElementById('startBtn').disabled = false;
document.getElementById('startBtn').innerHTML = '✅ Terminé';
loadResults();
}
});
}
function loadResults() {
fetch('/results').then(r => r.json()).then(d => {
document.getElementById('resultsContent').style.display = 'block';
const b = document.getElementById('contractsBody');
b.innerHTML = '';
d.results.forEach(c => {
const r = b.insertRow();
r.innerHTML = `
<td>${c.ID}</td>
<td title="${c.Description}">${c.Description.substring(0, 60)}...</td>
<td>${c['Pays/Région']}</td>
<td>${c['Date de publication']}</td>
<td title="${c['Promoteur']}" style="background: #e8f5e9; font-weight: bold;">${c['Promoteur'].substring(0, 40)}...</td>
<td><a href="${c['URL complète']}" target="_blank">🔗</a></td>
<td><button class="btn-validate" onclick="validate(${JSON.stringify(c).replace(/"/g, '&quot;')})">Valider</button></td>
`;
});
});
}
function validate(c) {
event.target.disabled = true;
event.target.innerHTML = '⏳';
fetch('/validate', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify(c)
}).then(r => r.json()).then(d => {
if (d.success) {
event.target.classList.add('success');
event.target.innerHTML = '✅';
}
});
}
document.getElementById('startBtn').addEventListener('click', start);
</script>
</body>
</html>
        """)

    def log_message(self, format, *args):
        pass

def main():
    PORT = 8000
    with socketserver.TCPServer(("", PORT), ExtractionHandler) as httpd:
        print(f"🎯 Serveur SELENIUM démarré!")
        print(f"📊 http://localhost:{PORT}")
        print(f"")
        print(f"🚀 SELENIUM:")
        print(f"   ✅ Charge JavaScript/Angular")
        print(f"   ✅ Extrait promoteur EXACT depuis HTML")
        print(f"   ✅ TOUS les contrats")
        print(f"")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Arrêté")

if __name__ == "__main__":
    main()