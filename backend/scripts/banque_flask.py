# Installation nécessaire
# pip install flask flask-cors pymongo selenium beautifulsoup4 pandas requests

import sys
import os
import json
import time
import requests
import pandas as pd
import re
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from pymongo import MongoClient
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import base64

# Configuration UTF-8 pour Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============================== CONFIGURATION ==============================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/ines")
DB_NAME = "worldbank_db-ines"
COLLECTION_NAME = "tenders_ines"
PENDING_COLLECTION_NAME = "pending_tenders_ines"

API_BASE_URL = "https://be.appeloffres.net/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"

EMAIL = "mariem.bousalem@tunipages.tn"
PASSWORD = "L96BhA6ODugl"
DEFAULT_SOURCE_ID = 1464
DEFAULT_AVIS_ID = 8

# Configuration Screenshots
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'screenshots_banque')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Token API global
api_token = None
token_expiration = None

COUNTRIES_MAP = {
    "angola": 9, "botswana": 32, "burundi": 38, "comoros": 51, "congo, dem. rep.": 177,
    "eritrea": 66, "eswatini": 67, "ethiopia": 68, "kenya": 106, "lesotho": 113,
    "madagascar": 123, "malawi": 125, "mauritius": 133, "mozambique": 142,
    "namibia": 144, "rwanda": 176, "seychelles": 190, "somalia": 195,
    "south africa": 4, "south sudan": 199, "tanzania": 214, "uganda": 156,
    "zambia": 229, "zimbabwe": 230, "benin": 26, "burkina faso": 37,
    "cameroon": 41, "cape verde": 43, "central african republic": 179,
    "chad": 45, "congo, rep.": 228, "côte d'ivoire": 58, "equatorial guinea": 83,
    "gabon": 72, "gambia, the": 73, "ghana": 74, "guinea": 82, "guinea-bissau": 84,
    "liberia": 117, "mali": 127, "mauritania": 134, "niger": 148, "nigeria": 149,
    "sao tome and principe": 187, "senegal": 188, "sierra leone": 191, "togo": 215
}

# ============================== TRADUCTION ==============================
TRANSLATION_DICT = {
    'consultancy': 'Consultance', 'construction': 'Construction', 'supply': 'Fourniture',
    'services': 'Services', 'project': 'Projet', 'implementation': 'Mise en œuvre',
    'procurement': 'Acquisition', 'goods': 'Biens', 'works': 'Travaux',
    'consulting': 'Conseil', 'consultant': 'Consultant', 'consultants': 'Consultants',
    'advertisement': 'Annonce', 'invitation': 'Invitation', 'bidding': 'Appel d\'offres',
    'tender': 'Soumission', 'contract': 'Contrat', 'development': 'Développement',
    'management': 'Gestion', 'technical': 'Technique', 'financial': 'Financier',
    'economic': 'Économique', 'social': 'Social', 'environmental': 'Environnemental',
    'assessment': 'Évaluation', 'study': 'Étude', 'design': 'Conception',
    'engineering': 'Ingénierie', 'supervision': 'Supervision', 'training': 'Formation',
    'capacity': 'Capacité', 'building': 'Renforcement', 'support': 'Soutien',
    'assistance': 'Assistance', 'advisory': 'Conseil', 'feasibility': 'Faisabilité',
    'monitoring': 'Suivi', 'evaluation': 'Évaluation', 'audit': 'Audit',
    'information': 'Information', 'communication': 'Communication', 'technology': 'Technologie',
    'system': 'Système', 'equipment': 'Équipement', 'materials': 'Matériaux',
    'vehicles': 'Véhicules', 'machinery': 'Machinerie', 'instrument': 'Instrument',
    'laboratory': 'Laboratoire', 'medical': 'Médical', 'health': 'Santé',
    'education': 'Éducation', 'agriculture': 'Agriculture', 'irrigation': 'Irrigation',
    'water': 'Eau', 'sanitation': 'Assainissement', 'energy': 'Énergie',
    'power': 'Électricité', 'transport': 'Transport', 'road': 'Route',
    'bridge': 'Pont', 'building': 'Bâtiment', 'housing': 'Logement',
    'urban': 'Urbain', 'rural': 'Rural', 'infrastructure': 'Infrastructure',
    'facility': 'Installation', 'plant': 'Usine', 'rehabilitation': 'Réhabilitation',
    'renovation': 'Rénovation', 'maintenance': 'Maintenance', 'operation': 'Exploitation',
    'service': 'Service', 'provider': 'Fournisseur', 'firm': 'Firme',
    'company': 'Entreprise', 'corporation': 'Société', 'international': 'International',
    'national': 'National', 'local': 'Local', 'regional': 'Régional',
    'global': 'Mondial', 'world': 'Monde', 'bank': 'Banque', 'fund': 'Fonds',
    'agency': 'Agence', 'ministry': 'Ministère', 'department': 'Département',
    'authority': 'Autorité', 'institution': 'Institution', 'organization': 'Organisation',
    'program': 'Programme', 'component': 'Composante', 'activity': 'Activité',
    'initiative': 'Initiative', 'procurement notice': 'Avis de passation de marchés',
    'contract award': 'Attribution de contrat', 'expression of interest': 'Appel à manifestation d\'intérêt',
    'request for proposal': 'Demande de propositions', 'request for quotation': 'Demande de devis',
    'invitation for bids': 'Invitation à soumissionner'
}

def translate_to_french(text: str) -> str:
    """Traduit les termes clés de l'anglais vers le français"""
    if not text:
        return text
    translated = text
    for eng, fr in TRANSLATION_DICT.items():
        translated = re.sub(r'\b' + re.escape(eng) + r'\b', fr, translated, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', translated).strip()

# ============================== MODÈLE DE DONNÉES ==============================
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
        self.avis = "Avis d'appel d'offres"
        self.procedure = "Appel d'offres international"
        self.type_marche = "Public"
        self.url_source = ""
        self.validationDate = None
        self.projet = ""
        self.intitule_projet = ""
        self.reference_offre_emprunteur = ""
        self.notice_id = ""

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

# ============================== EXTRACTEUR PRINCIPAL ==============================
class WorldBankCompleteExtractor:
    def __init__(self):
        self.api_url = "https://search.worldbank.org/api/v2/procnotices"
        self.base_project_url = "https://projects.banquemondiale.org/fr/projects-operations/procurement-detail/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://search.worldbank.org/',
        }
        self.start_date = None
        self.end_date = None
        self.seen_ids = set()
        self.all_notices = []
        self.extraction_status = "Prêt"
        self.progress = 0
        self.current_step = ""
        self.results = []
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def set_date_range(self, start_date_str, end_date_str):
        """Définit la plage de dates pour l'extraction"""
        self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        print(f"📅 Plage de dates: {self.start_date.strftime('%d/%m/%Y')} au {self.end_date.strftime('%d/%m/%Y')}")

    def update_status(self, status, progress=None, step=""):
        """Met à jour le statut de l'extraction"""
        self.extraction_status = status
        if progress is not None:
            self.progress = progress
        if step:
            self.current_step = step
        print(f"[{progress}%] {step}: {status}")

    # ============================== MÉTHODES D'EXTRACTION ==============================
    
    def parse_date(self, date_str):
        """Parse une date dans différents formats"""
        if not date_str:
            return None
            
        date_str = str(date_str).strip()
        formats = [
            '%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y',
            '%b %d, %Y', '%Y/%m/%d', '%d.%m.%Y', '%m/%d/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None

    def is_in_period(self, date_str):
        """Vérifie si une date est dans la période sélectionnée"""
        if not date_str:
            return False
            
        dt = self.parse_date(date_str)
        if not dt:
            return False
            
        return self.start_date <= dt <= self.end_date

    def fetch_with_params(self, custom_params, retry_count=3):
        """Récupère les données de l'API avec gestion des erreurs"""
        for attempt in range(retry_count):
            try:
                params = {'format': 'json', 'apilang': 'en', 'srce': 'both', **custom_params}
                response = self.session.get(self.api_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 500:
                    print(f"⚠️ Erreur 500 API (tentative {attempt + 1}/{retry_count})")
                    if attempt < retry_count - 1:
                        time.sleep(2 + attempt)
                        # Essayer avec des paramètres différents
                        if 'os' in custom_params:
                            custom_params['os'] = custom_params['os'] + random.randint(100, 500)
                else:
                    print(f"⚠️ Erreur API: {response.status_code} (tentative {attempt + 1}/{retry_count})")
                    
            except Exception as e:
                print(f"⚠️ Exception lors de la requête (tentative {attempt + 1}): {str(e)[:100]}")
            
            time.sleep(1)
        
        return None

    def extract_notice_number(self, record):
        """Extrait le numéro d'avis"""
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
        """Construit l'URL complète"""
        if not notice_number or notice_number == 'NON_DISPO':
            return 'URL_NON_DISPO'
        clean = str(notice_number).strip()
        return clean if clean.startswith('http') else f"{self.base_project_url}{clean}"

    def calculate_date_limite(self, pub_date):
        """Calcule la date limite (30 jours après publication)"""
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

    # ============================== STRATÉGIES D'EXTRACTION ==============================
    
    def extract_by_date_range(self):
        """Extraction spécifique par plage de dates"""
        print("🔍 Recherche par plage de dates...")
        
        all_notices_temp = []
        
        # Essayer différentes stratégies de recherche
        search_strategies = [
            {'qterm': f'noticedate:{self.start_date.strftime("%Y-%m-%d")}'},
            {'qterm': f'noticedate:{self.start_date.strftime("%Y-%m")}'},
            {'qterm': f'noticedate:{self.start_date.strftime("%Y")}'},
            {'qterm': f'noticedate:[{self.start_date.strftime("%Y-%m-%d")} TO {self.end_date.strftime("%Y-%m-%d")}]'},
            {}
        ]
        
        for strategy_idx, strategy in enumerate(search_strategies, 1):
            print(f"  🔄 Stratégie {strategy_idx}/5")
            
            for page in range(5):  # 5 pages par stratégie
                offset = page * 200
                params = {
                    'os': offset,
                    'rows': 200,
                    **strategy
                }
                
                data = self.fetch_with_params(params)
                if not data or not data.get('procnotices'):
                    break
                    
                notices = data['procnotices']
                print(f"    📄 Page {page+1}: {len(notices)} avis")
                
                for record in notices:
                    date_str = record.get('noticedate')
                    if date_str and self.is_in_period(date_str):
                        cid = f"{record.get('project_id')}_{record.get('id')}"
                        if cid not in self.seen_ids:
                            self.seen_ids.add(cid)
                            all_notices_temp.append(record)
                
                time.sleep(0.5)
        
        return all_notices_temp

    def extract_all_notices_with_retry(self, max_pages=50):
        """Extrait TOUS les avis sans limite - VERSION EXHAUSTIVE"""
        print("🚀 Extraction EXHAUSTIVE de TOUS les avis récents...")

        all_notices_temp = []
        max_offset = 2000  # Augmenté pour extraire plus de données
        page_size = 100

        # Parcourir toutes les pages jusqu'à ne plus trouver de données
        for current_offset in range(0, max_offset, page_size):
            print(f"📄 Page avec offset: {current_offset}")

            params = {
                'os': current_offset,
                'rows': page_size,
                'srt': 'publishdate',
                'order': 'desc'
            }

            data = self.fetch_with_params(params, retry_count=2)
            if not data or not data.get('procnotices'):
                print(f"  ⚠️ Pas de données pour offset {current_offset} - fin")
                break

            notices = data['procnotices']
            if not notices:
                print(f"  ⚠️ Aucun avis à offset {current_offset} - fin de pagination")
                break

            print(f"  ✅ {len(notices)} avis récupérés (offset: {current_offset})")

            found_in_period = 0
            for record in notices:
                date_str = record.get('noticedate')
                if date_str and self.is_in_period(date_str):
                    cid = f"{record.get('project_id')}_{record.get('id')}"
                    if cid not in self.seen_ids:
                        self.seen_ids.add(cid)
                        all_notices_temp.append(record)
                        found_in_period += 1

            print(f"      → {found_in_period} avis dans la période")

            # Si pas de données dans la période et qu'on est loin dans la pagination, arrêter
            if found_in_period == 0 and current_offset > 500:
                print(f"  ℹ️ Aucun avis dans la période - arrêt de la pagination")
                break

            time.sleep(0.5)

        return all_notices_temp

    def extract_by_countries(self):
        """Extraction par pays africains"""
        print("🌍 Extraction par pays africains...")
        
        countries = [
            'Angola', 'Benin', 'Botswana', 'Burkina Faso', 'Burundi', 'Cameroon',
            'Cape Verde', 'Central African Republic', 'Chad', 'Comoros', 'Congo',
            'Democratic Republic of Congo', 'Côte d\'Ivoire', 'Djibouti', 'Equatorial Guinea',
            'Eritrea', 'Eswatini', 'Ethiopia', 'Gabon', 'Gambia', 'Ghana', 'Guinea',
            'Guinea-Bissau', 'Kenya', 'Lesotho', 'Liberia', 'Madagascar', 'Malawi',
            'Mali', 'Mauritania', 'Mauritius', 'Mozambique', 'Namibia', 'Niger',
            'Nigeria', 'Rwanda', 'Sao Tome and Principe', 'Senegal', 'Seychelles',
            'Sierra Leone', 'Somalia', 'South Africa', 'South Sudan', 'Sudan',
            'Tanzania', 'Togo', 'Uganda', 'Zambia', 'Zimbabwe'
        ]
        
        all_notices_temp = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for country in countries:
                futures.append(executor.submit(self.search_country, country))
            
            for future in as_completed(futures):
                try:
                    country_notices = future.result()
                    all_notices_temp.extend(country_notices)
                except Exception as e:
                    print(f"⚠️ Erreur pour un pays: {e}")
        
        return all_notices_temp

    def search_country(self, country):
        """Recherche les avis pour un pays spécifique"""
        country_notices = []
        
        for offset in [0, 100, 200]:
            params = {
                'os': offset,
                'rows': 100,
                'qterm': f'"{country}"',
                'srt': 'publishdate',
                'order': 'desc'
            }
            
            data = self.fetch_with_params(params)
            if not data:
                break
                
            notices = data.get('procnotices', [])
            for record in notices:
                date_str = record.get('noticedate')
                if date_str and self.is_in_period(date_str):
                    cid = f"{record.get('project_id')}_{record.get('id')}"
                    if cid not in self.seen_ids:
                        self.seen_ids.add(cid)
                        country_notices.append(record)
            
            time.sleep(0.5)
        
        print(f"  ✅ {country}: {len(country_notices)} avis")
        return country_notices

    def extract_by_notice_types(self):
        """Extraction de TOUS les types d'avis sans filtre"""
        print("📋 Extraction de TOUS les types d'avis (sans filtre)...")

        all_notices_temp = []

        # Extraction sans filtre de type - on récupère TOUT
        print(f"  🔍 Récupération de TOUS les avis (sans filtre de type)")

        # Parcourir plusieurs pages avec différents offsets
        for offset in range(0, 1000, 100):  # De 0 à 900 par pas de 100
            params = {
                'os': offset,
                'rows': 100,
                'srt': 'publishdate',
                'order': 'desc'
            }

            data = self.fetch_with_params(params)
            if not data:
                print(f"  ⚠️ Pas de données pour offset {offset}")
                break

            notices = data.get('procnotices', [])
            if not notices:
                print(f"  ⚠️ Aucun avis trouvé pour offset {offset} - fin de pagination")
                break

            print(f"  ✅ {len(notices)} avis trouvés (offset: {offset})")

            found_in_period = 0
            for record in notices:
                date_str = record.get('noticedate')
                if date_str and self.is_in_period(date_str):
                    cid = f"{record.get('project_id')}_{record.get('id')}"
                    if cid not in self.seen_ids:
                        self.seen_ids.add(cid)
                        all_notices_temp.append(record)
                        found_in_period += 1

            print(f"      → {found_in_period} avis dans la période de dates")

            # Si aucun avis dans la période sur cette page, on peut arrêter
            if found_in_period == 0 and offset > 200:
                print(f"  ℹ️ Aucun avis dans la période sur les dernières pages - arrêt")
                break

            time.sleep(0.5)

        return all_notices_temp

    # ============================== ENRICHISSEMENT ==============================
    
    def enrich_notice(self, record):
        """Enrichit un avis avec toutes les informations"""
        country = record.get('project_ctry_name', '') or record.get('country', 'N/A')
        notice_number = self.extract_notice_number(record)
        full_url = self.build_complete_url(notice_number)
        
        # Extraction du promoteur (simplifié pour Flask - pas de Selenium ici)
        promoter = 'Banque Mondiale'
        project_name = record.get('project_name', '')
        if project_name and project_name != 'N/A':
            promoter = translate_to_french(project_name)
        
        # Déterminer le type d'avis
        notice_type = record.get('notice_type', '')
        avis_type = self.determine_avis_type(notice_type)
        
        # Déterminer la procédure
        procedure = self.determine_procedure(notice_type)
        
        return {
            'ID': len(self.all_notices) + 1,
            'Description': translate_to_french(record.get('bid_description') or record.get('project_name', 'N/A')),
            'Pays': country,
            'Date publication': record.get('noticedate', 'N/A'),
            'Date limite': self.calculate_date_limite(record.get('noticedate', '')),
            'Type avis': notice_type,
            'Type avis FR': avis_type,
            'Procédure': procedure,
            'Référence': record.get('bid_reference_no', 'N/A') or record.get('id', 'N/A'),
            'ID Projet': record.get('project_id', 'N/A'),
            'Intitulé Projet': translate_to_french(record.get('project_name', 'N/A')),
            'Promoteur': promoter,
            'URL': full_url,
            'Langue': record.get('notice_lang_name', 'N/A'),
            'Source de financement': record.get('fundingsource', 'Banque Mondiale'),
            'Notice Number': notice_number,
            'Project Name': record.get('project_name', 'N/A'),
            'Region': self.get_region(country),
            'Status': 'pending',
            'Extraction Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def determine_avis_type(self, notice_type):
        """Détermine le type d'avis en français"""
        mapping = {
            'Contract Award': 'Attribution de contrat',
            'Invitation for Bids': 'Invitation à soumissionner',
            'Request for Proposal': 'Demande de propositions',
            'Expression of Interest': 'Appel à manifestation d\'intérêt',
            'General Procurement Notice': 'Avis général de passation de marchés',
            'Procurement Notice': 'Avis de passation de marchés'
        }
        return mapping.get(notice_type, notice_type)

    def determine_procedure(self, notice_type):
        """Détermine la procédure"""
        if 'Contract Award' in notice_type:
            return 'Attribution'
        elif 'Invitation for Bids' in notice_type:
            return 'Appel d\'offres international'
        elif 'Request for Proposal' in notice_type:
            return 'Demande de propositions'
        elif 'Expression of Interest' in notice_type:
            return 'Manifestation d\'intérêt'
        else:
            return 'Procédure ordinaire'

    def get_region(self, country):
        """Détermine la région"""
        if not country:
            return 'Unknown'
        cl = str(country).lower()
        
        east_south = ['angola', 'botswana', 'burundi', 'comoros', 'eritrea', 'ethiopia',
                     'kenya', 'lesotho', 'madagascar', 'malawi', 'mauritius', 'mozambique',
                     'namibia', 'rwanda', 'seychelles', 'somalia', 'south africa', 
                     'tanzania', 'uganda', 'zambia', 'zimbabwe']
        
        west_central = ['benin', 'burkina faso', 'cameroon', 'cape verde', 'chad', 'congo',
                       'côte d\'ivoire', 'gabon', 'gambia', 'ghana', 'guinea', 'liberia',
                       'mali', 'mauritania', 'niger', 'nigeria', 'senegal', 'sierra leone', 'togo']
        
        if any(c in cl for c in east_south):
            return 'Afrique de l\'Est et Australe'
        elif any(c in cl for c in west_central):
            return 'Afrique de l\'Ouest et Centrale'
        else:
            return 'Autre région'

    # ============================== EXTRACTION COMPLÈTE ==============================
    
    def execute_complete_extraction(self):
        """Exécute l'extraction complète avec toutes les stratégies"""
        if self.start_date is None or self.end_date is None:
            self.update_status("Erreur: Dates non définies", 0, "Initialisation")
            return None
        
        self.update_status("Démarrage de l'extraction", 5, "Initialisation")
        
        # Étape 1: Extraction par plage de dates
        self.update_status("Extraction par plage de dates", 20, "Étape 1")
        notices_etape1 = self.extract_by_date_range()
        print(f"✅ Étape 1: {len(notices_etape1)} avis trouvés")
        
        # Étape 2: Extraction avec retry
        self.update_status("Extraction étendue avec retry", 40, "Étape 2")
        notices_etape2 = self.extract_all_notices_with_retry()
        filtered_etape2 = [n for n in notices_etape2 
                          if self.is_in_period(n.get('noticedate', ''))]
        print(f"✅ Étape 2: {len(filtered_etape2)} avis filtrés")
        
        # Étape 3: Extraction par pays
        self.update_status("Extraction par pays africains", 60, "Étape 3")
        notices_etape3 = self.extract_by_countries()
        print(f"✅ Étape 3: {len(notices_etape3)} avis trouvés")
        
        # Étape 4: Extraction par types d'avis
        self.update_status("Extraction par types d'avis", 80, "Étape 4")
        notices_etape4 = self.extract_by_notice_types()
        print(f"✅ Étape 4: {len(notices_etape4)} avis trouvés")
        
        # Combiner tous les avis
        all_notices_raw = notices_etape1 + filtered_etape2 + notices_etape3 + notices_etape4
        
        # Dédupliquer
        unique_notices = []
        seen = set()
        for notice in all_notices_raw:
            notice_id = notice.get('id') or notice.get('bid_reference_no', '')
            if notice_id and notice_id not in seen:
                seen.add(notice_id)
                unique_notices.append(notice)
        
        # Enrichir les avis
        self.update_status("Enrichissement des avis", 90, "Enrichissement")
        for record in unique_notices:
            enriched = self.enrich_notice(record)
            self.all_notices.append(enriched)
        
        self.update_status(f"{len(self.all_notices)} avis extraits", 95, "Finalisation")
        
        return self.save_to_mongodb()

    def save_to_mongodb(self):
        """Sauvegarde les résultats dans MongoDB"""
        if not self.all_notices:
            self.update_status("Aucune donnée à sauvegarder", 100, "Terminé")
            return None
        
        try:
            # Connecter à MongoDB
            client = MongoClient(MONGO_URI)
            db = client[DB_NAME]
            pending_collection = db[PENDING_COLLECTION_NAME]
            
            # Sauvegarder chaque avis
            saved_count = 0
            for notice in self.all_notices:
                try:
                    # Vérifier si l'avis existe déjà
                    existing = pending_collection.find_one({
                        'Référence': notice['Référence']
                    })
                    
                    if not existing:
                        # Convertir en TenderModel
                        tender = self.map_to_tender_model(notice)
                        
                        # Sauvegarder dans la collection pending
                        pending_collection.insert_one(tender)
                        saved_count += 1
                        
                except Exception as e:
                    print(f"⚠️ Erreur lors de la sauvegarde d'un avis: {e}")
            
            client.close()
            
            # Préparer les résultats pour l'API
            self.results = self.all_notices
            
            self.update_status(f"✅ {saved_count} avis sauvegardés dans MongoDB", 100, "Terminé")
            
            return {
                'success': True,
                'total_extracted': len(self.all_notices),
                'total_saved': saved_count,
                'results': self.results
            }
            
        except Exception as e:
            self.update_status(f"Erreur MongoDB: {e}", 100, "Erreur")
            return {
                'success': False,
                'message': str(e)
            }

    def map_to_tender_model(self, contract_data):
        """Convertit les données d'avis en TenderModel"""
        # Déterminer l'ID du pays
        country = contract_data.get('Pays', '').lower().strip()
        country_id = COUNTRIES_MAP.get(country, 1)
        
        # Dates
        pub_date = contract_data.get('Date publication', '')
        exp_date = contract_data.get('Date limite', '')
        
        # Parser les dates
        try:
            pub_dt = self.parse_date(pub_date)
            pub_iso = pub_dt.isoformat() if pub_dt else pub_date
            start_iso = (pub_dt + timedelta(days=1)).isoformat() if pub_dt else None
            open_iso = pub_dt.isoformat() if pub_dt else None
        except:
            pub_iso = pub_date
            start_iso = None
            open_iso = None
        
        try:
            exp_dt = self.parse_date(exp_date)
            exp_iso = exp_dt.isoformat() if exp_dt else exp_date
        except:
            exp_iso = exp_date
        
        # Créer le modèle
        tender = TenderModel()
        tender.title = translate_to_french(contract_data.get('Intitulé Projet', '')[:100])
        tender.description = translate_to_french(contract_data.get('Description', ''))
        tender.full_content = tender.description
        tender.publicationDate = pub_iso
        tender.startBiddingDate = start_iso
        tender.expirationDate = exp_iso
        tender.openingBidsDate = open_iso
        tender.reference = contract_data.get('Référence', '')
        tender.specificationsReceivingAddress = contract_data.get('URL', '')
        tender.promoter = translate_to_french(contract_data.get('Promoteur', 'Banque Mondiale'))
        tender.batches = [{"activitiesIds": [], "title": tender.description, "deposit": 0}]
        tender.addresses = [{"countryId": country_id}]
        tender.pays = country_id
        tender.cahier_charge = contract_data.get('URL', '')
        tender.url_source = contract_data.get('URL', '')
        tender.validationDate = datetime.now().isoformat()
        tender.projet = translate_to_french(contract_data.get('Intitulé Projet', ''))
        tender.intitule_projet = translate_to_french(contract_data.get('Intitulé Projet', ''))
        tender.reference_offre_emprunteur = contract_data.get('Référence', '')
        tender.notice_id = contract_data.get('Notice Number', '')
        tender.avis = contract_data.get('Type avis FR', 'Avis d\'appel d\'offres')
        tender.procedure = contract_data.get('Procédure', 'Appel d\'offres international')
        tender.extractionDate = datetime.now().isoformat()
        
        return tender.to_dict()

# ============================== APPLICATION FLASK ==============================

# Initialiser l'extracteur
extractor = WorldBankCompleteExtractor()

# Initialiser MongoDB
try:
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[DB_NAME]
    pending_collection = mongo_db[PENDING_COLLECTION_NAME]
    tenders_collection = mongo_db[COLLECTION_NAME]
    print(f"✅ Connecté à MongoDB: {DB_NAME}")
except Exception as e:
    print(f"⚠️ Erreur de connexion MongoDB: {e}")
    pending_collection = None
    tenders_collection = None

# Créer l'application Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Variables globales pour le statut
extraction_status = {
    "status": "Prêt",
    "progress": 0,
    "step": "",
    "total": 0,
    "saved": 0
}

# Variable pour le thread d'extraction
extraction_thread = None

# ============================== ROUTES API ==============================

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Lance l'extraction"""
    global extraction_thread, extraction_status
    
    try:
        data = request.json
        start_date = data.get('startDate', '2025-12-01')
        end_date = data.get('endDate', '2025-12-10')
        
        # Réinitialiser le statut
        extraction_status = {
            "status": "Démarrage",
            "progress": 0,
            "step": "Initialisation",
            "total": 0,
            "saved": 0
        }
        
        # Configurer l'extracteur
        extractor.set_date_range(start_date, end_date)
        
        # Démarrer l'extraction dans un thread séparé
        extraction_thread = ThreadPoolExecutor(max_workers=1)
        extraction_thread.submit(run_extraction)
        
        return jsonify({
            "success": True,
            "message": "Extraction démarrée",
            "dates": {
                "start": start_date,
                "end": end_date
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def run_extraction():
    """Exécute l'extraction dans un thread séparé"""
    global extraction_status
    
    try:
        result = extractor.execute_complete_extraction()
        
        if result and result.get('success'):
            extraction_status.update({
                "status": "Terminé",
                "progress": 100,
                "step": "Extraction complète",
                "total": result.get('total_extracted', 0),
                "saved": result.get('total_saved', 0)
            })
        else:
            extraction_status.update({
                "status": "Erreur",
                "progress": 100,
                "step": "Échec de l'extraction",
                "total": 0,
                "saved": 0
            })
            
    except Exception as e:
        extraction_status.update({
            "status": "Erreur",
            "progress": 100,
            "step": f"Exception: {str(e)[:100]}",
            "total": 0,
            "saved": 0
        })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retourne le statut de l'extraction"""
    return jsonify(extraction_status)

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Récupère les offres en attente"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        skip = (page - 1) * limit
        
        if pending_collection is None:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500

        # Récupérer les offres pending
        pending_docs = list(pending_collection.find(
            {"status": "pending"}
        ).sort("extractionDate", -1).skip(skip).limit(limit))
        
        total = pending_collection.count_documents({"status": "pending"})
        
        # Convertir ObjectId en string
        for doc in pending_docs:
            doc['_id'] = str(doc['_id'])
        
        return jsonify({
            "success": True,
            "pending": pending_docs,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/validate/<path:reference>', methods=['POST'])
def validate_tender(reference):
    """Valide et envoie une offre à l'API avec capture screenshot"""
    try:
        if pending_collection is None:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500

        # Récupérer l'offre depuis pending
        tender_doc = pending_collection.find_one({"reference": reference})
        if not tender_doc:
            return jsonify({"success": False, "message": "Offre non trouvée"}), 404

        # Se connecter à l'API
        auth_token = login_to_api()
        if not auth_token:
            return jsonify({"success": False, "message": "Échec d'authentification API"}), 401

        # Trouver ou créer le promoteur
        promoter_id = find_or_create_promoter(auth_token, tender_doc.get('promoter', 'Banque Mondiale'))
        if not promoter_id:
            return jsonify({"success": False, "message": "Échec création promoteur"}), 500

        # ✅ Capturer une screenshot de la page source
        images = []
        url_source = tender_doc.get('url_source') or tender_doc.get('cahier_charge') or tender_doc.get('specificationsReceivingAddress')

        if url_source and url_source not in ['URL_NON_DISPO', '', 'N/A']:
            print(f"📸 Tentative de capture screenshot pour {reference}")
            print(f"   URL source: {url_source}")

            try:
                screenshot_path = capture_screenshot_banque(url_source, reference)
                if screenshot_path:
                    s3_url = upload_screenshot_to_s3(screenshot_path, reference)
                    if s3_url:
                        images.append(s3_url)
                        print(f"✅ Image ajoutée au payload: {s3_url}")
                    else:
                        print(f"⚠️ Upload S3 échoué pour {reference}")
                else:
                    print(f"⚠️ Capture screenshot échouée pour {reference}")
            except Exception as e:
                print(f"⚠️ Erreur capture/upload screenshot: {e}")
        else:
            print(f"⚠️ Pas d'URL source valide pour capture: {url_source}")

        # Préparer le payload avec images
        payload = prepare_tender_payload(tender_doc, promoter_id)
        payload['images'] = images  # ✅ Ajouter les images capturées

        print(f"📤 Envoi offre {reference} avec {len(images)} image(s)")

        # Envoyer à l'API
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.post(TENDER_ENDPOINT, json=payload, headers=headers, timeout=30)

        if response.status_code in [200, 201]:
            # Mettre à jour le statut
            tender_doc['status'] = 'validated'
            tender_doc['validationDate'] = datetime.now().isoformat()
            tender_doc['images'] = images

            # Sauvegarder dans la collection principale
            if tenders_collection is not None:
                tenders_collection.insert_one(tender_doc)

            # Supprimer de pending
            pending_collection.delete_one({"reference": reference})

            return jsonify({
                "success": True,
                "message": f"Offre validée et envoyée avec succès ({len(images)} image(s))"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Erreur API: {response.status_code}",
                "details": response.text[:500]
            }), 500

    except Exception as e:
        print(f"❌ Erreur validation: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

def is_token_valid():
    """Vérifie si le token est valide et non expiré"""
    global api_token, token_expiration
    if not api_token:
        return False
    if token_expiration and datetime.now() > token_expiration:
        return False
    return True

def login_to_api():
    """Se connecte à l'API externe et stocke le token globalement"""
    global api_token, token_expiration
    try:
        print(f"🔐 Tentative de connexion API avec {EMAIL}...")
        response = requests.post(
            LOGIN_ENDPOINT,
            json={"email": EMAIL, "password": PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            # Essayer différentes clés possibles pour le token
            api_token = data.get('access_token') or data.get('accessToken') or data.get('token')
            if api_token:
                # Token valide pour 24h
                token_expiration = datetime.now() + timedelta(hours=24)
                print(f"✅ Connexion API réussie - Token obtenu")
                return api_token
        print(f"❌ Échec connexion API: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"❌ Erreur login API: {e}")
    return None

def capture_screenshot_banque(url, reference):
    """Capture une screenshot de la page de détails Banque Mondiale"""
    screenshot_path = None
    driver = None

    try:
        print(f"📸 Capture screenshot pour {reference}...")
        print(f"   URL: {url}")

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")

        # Chemin Chrome dans Docker
        chrome_path = "/usr/bin/chromium"
        driver_path = "/usr/bin/chromedriver"

        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        driver.set_page_load_timeout(60)
        driver.get(url)

        # Attendre que la page charge (le contenu Angular)
        time.sleep(5)

        # Essayer d'attendre le contenu principal
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            time.sleep(3)
        except TimeoutException:
            print(f"⚠️ Timeout chargement page, capture quand même")

        # Faire défiler pour capturer tout le contenu
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Prendre la screenshot
        screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{reference}.png")
        driver.save_screenshot(screenshot_path)

        if os.path.exists(screenshot_path):
            file_size = os.path.getsize(screenshot_path)
            print(f"✅ Screenshot capturée: {screenshot_path} ({file_size} bytes)")
            return screenshot_path
        else:
            print(f"❌ Screenshot non créée")
            return None

    except Exception as e:
        print(f"❌ Erreur capture screenshot: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def upload_screenshot_to_s3(file_path, reference):
    """Upload une screenshot vers S3 via l'API appeloffres.net"""
    global api_token

    # Vérifier et se connecter si nécessaire
    if not is_token_valid():
        print("⚠️ Token invalide, tentative de connexion...")
        if not login_to_api():
            print("❌ Impossible d'uploader sans token - LOGIN ÉCHOUÉ")
            return None

    try:
        headers = {
            'Authorization': f'Bearer {api_token}',
            'User-Agent': 'BanqueMondialeScraper/1.0'
        }

        if not os.path.exists(file_path):
            print(f"❌ Fichier introuvable: {file_path}")
            return None

        file_size = os.path.getsize(file_path)
        print(f"📤 Upload vers S3: {os.path.basename(file_path)} ({file_size} bytes)")

        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'image/png')}
            data = {'description': f'Screenshot Banque Mondiale {reference}'}

            response = requests.post(FILES_ENDPOINT, headers=headers, files=files, data=data, timeout=60)

            if response.status_code in [200, 201]:
                api_data = response.json()
                print(f"✅ Réponse API upload: {response.status_code}")

                s3_url = api_data.get('url') or api_data.get('s3Url') or api_data.get('data', {}).get('url')

                if s3_url:
                    print(f"✅ Upload S3 réussi: {s3_url}")

                    # Extraire le chemin relatif
                    relative_match = re.search(r'/tender-s3-prod/(.+?\.(?:png|pdf|jpg))\??', s3_url)
                    if relative_match:
                        relative_path = relative_match.group(1)
                        print(f"📎 Chemin relatif extrait: {relative_path}")
                        return relative_path
                    else:
                        return s3_url
                else:
                    print(f"❌ URL S3 non trouvée dans la réponse: {api_data}")
                    return None
            else:
                print(f"❌ ERREUR UPLOAD S3: {response.status_code} - {response.text[:200]}")
                return None
    except Exception as e:
        print(f"❌ Exception upload S3: {e}")
        return None
    finally:
        # Nettoyer le fichier temporaire
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Fichier temporaire supprimé: {file_path}")
        except:
            pass

def find_or_create_promoter(auth_token, promoter_name):
    """Trouve ou crée un promoteur dans l'API"""
    try:
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        # Chercher le promoteur existant
        response = requests.get(
            f"{PROMOTER_ENDPOINT}?page=1&itemsPerPage=100",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            promoters = data.get('data', [])
            for promoter in promoters:
                if promoter.get('companyName', '').lower() == promoter_name.lower():
                    return promoter.get('id')
        
        # Créer un nouveau promoteur
        payload = {
            "companyName": promoter_name,
            "address": {
                "street": "World Bank Project",
                "city": "Washington",
                "state": "DC",
                "postalCode": "20433",
                "country": "USA"
            },
            "description": f"Projet Banque Mondiale: {promoter_name}"
        }
        
        response = requests.post(
            PROMOTER_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            return data.get('id')
            
    except:
        pass
    
    return 223472  # ID par défaut

def prepare_tender_payload(tender_doc, promoter_id):
    """Prépare le payload pour l'API"""
    payload = {
        "title": tender_doc.get('title', 'N/A'),
        "description": tender_doc.get('description', 'N/A'),
        "publicationDate": tender_doc.get('publicationDate', datetime.now().isoformat()),
        "expirationDate": tender_doc.get('expirationDate', datetime.now().isoformat()),
        "reference": tender_doc.get('reference', ''),
        "specificationsReceivingAddress": tender_doc.get('specificationsReceivingAddress', ''),
        "avisId": DEFAULT_AVIS_ID,
        "sourceId": DEFAULT_SOURCE_ID,
        "promoterId": promoter_id,
        "type": tender_doc.get('type', 'international'),
        "nature": tender_doc.get('nature', 'public'),
        "isEnabled": True,
        "fundingSourceType": "international",
        "fundingSource": "Banque Mondiale",
        "currencyId": 1,  # EUR par défaut
        "isMultiCurrency": False,
        "batches": tender_doc.get('batches', []),
        "addresses": tender_doc.get('addresses', []),
        "images": tender_doc.get('images', [])  # Ajouter le champ images (array vide par défaut)
    }

    # Dates optionnelles
    if tender_doc.get('startBiddingDate'):
        payload['startBiddingDate'] = tender_doc['startBiddingDate']
    if tender_doc.get('openingBidsDate'):
        payload['openingBidsDate'] = tender_doc['openingBidsDate']

    return payload

@app.route('/api/validated', methods=['GET'])
def get_validated():
    """Récupère les offres validées"""
    try:
        if tenders_collection is None:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500

        validated_docs = list(tenders_collection.find(
            {"status": "validated"}
        ).sort("validationDate", -1).limit(100))
        
        for doc in validated_docs:
            doc['_id'] = str(doc['_id'])
        
        return jsonify({
            "success": True,
            "validated": validated_docs,
            "total": len(validated_docs)
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<path:reference>', methods=['DELETE'])
def delete_tender(reference):
    """Supprime une offre pending"""
    try:
        if pending_collection is None:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500
        
        result = pending_collection.delete_one({"reference": reference})
        
        if result.deleted_count > 0:
            return jsonify({
                "success": True,
                "message": f"Offre {reference} supprimée"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Offre non trouvée"
            }), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/clear_pending', methods=['DELETE'])
def clear_pending():
    """Supprime toutes les offres pending"""
    try:
        if pending_collection is None:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500
        
        result = pending_collection.delete_many({})
        
        # Réinitialiser les IDs vus
        extractor.seen_ids = set()
        
        return jsonify({
            "success": True,
            "message": f"{result.deleted_count} offres supprimées",
            "deleted_count": result.deleted_count
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check de l'application"""
    pending_count = pending_collection.count_documents({}) if pending_collection is not None else 0
    validated_count = tenders_collection.count_documents({}) if tenders_collection is not None else 0

    return jsonify({
        "status": "healthy",
        "service": "Banque Mondiale Extractor API",
        "version": "2.0",
        "database": {
            "connected": pending_collection is not None,
            "pending_count": pending_count,
            "validated_count": validated_count
        },
        "extractor_status": extraction_status
    })

@app.route('/api/export', methods=['GET'])
def export_data():
    """Exporte les données en Excel"""
    try:
        if pending_collection is None:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500
        
        # Récupérer toutes les données pending
        pending_docs = list(pending_collection.find({}))
        
        if not pending_docs:
            return jsonify({"success": False, "message": "Aucune donnée à exporter"}), 404
        
        # Créer un DataFrame
        data = []
        for doc in pending_docs:
            data.append({
                'Référence': doc.get('reference', ''),
                'Titre': doc.get('title', ''),
                'Description': doc.get('description', ''),
                'Pays': doc.get('pays', ''),
                'Promoteur': doc.get('promoter', ''),
                'Date Publication': doc.get('publicationDate', ''),
                'Date Limite': doc.get('expirationDate', ''),
                'URL Source': doc.get('url_source', ''),
                'Statut': doc.get('status', 'pending'),
                'Date Extraction': doc.get('extractionDate', '')
            })
        
        df = pd.DataFrame(data)
        
        # Sauvegarder en Excel
        filename = f'banque_mondiale_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        filepath = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        df.to_excel(filepath, index=False)
        
        return jsonify({
            "success": True,
            "message": "Export terminé",
            "filename": filename,
            "filepath": filepath,
            "count": len(data)
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    """Page d'accueil avec interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Extracteur Banque Mondiale - INES</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            .content {
                padding: 30px;
                display: grid;
                grid-template-columns: 1fr 2fr;
                gap: 30px;
            }
            .panel {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
            }
            .btn {
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 1.1rem;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
                margin: 5px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .btn:disabled {
                background: #95a5a6;
                cursor: not-allowed;
            }
            .btn-danger {
                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            }
            .btn-success {
                background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            }
            .progress-container {
                background: #e9ecef;
                border-radius: 10px;
                height: 20px;
                margin: 20px 0;
                overflow: hidden;
            }
            .progress-bar {
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                height: 100%;
                width: 0%;
                transition: width 0.3s;
                border-radius: 10px;
            }
            .status-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }
            .status-item {
                background: #fff;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                background: #34495e;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #e9ecef;
                vertical-align: top;
            }
            tr:hover {
                background: #f8f9fa;
            }
            input[type="date"] {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 200px;
                margin: 5px;
            }
            .notice {
                background: #d4edda;
                border: 1px solid #c3e6cb;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                color: #155724;
            }
            .actions {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌍 Extracteur Banque Mondiale - INES</h1>
                <p>Extraction multi-stratégies avec sauvegarde MongoDB + API</p>
            </div>
            
            <div class="content">
                <div>
                    <div class="panel">
                        <h2>📊 Paramètres d'extraction</h2>
                        <div style="margin: 15px 0;">
                            <label><strong>Plage de dates :</strong></label><br>
                            <input type="date" id="startDate" value="2025-12-01">
                            <input type="date" id="endDate" value="2025-12-10">
                        </div>
                        <button id="startBtn" class="btn">🚀 Démarrer l'extraction</button>
                        <button id="exportBtn" class="btn btn-success">📥 Exporter Excel</button>
                        <button id="clearBtn" class="btn btn-danger">🗑️ Vider Pending</button>
                    </div>
                    
                    <div class="panel">
                        <h2>📈 Statut</h2>
                        <div class="progress-container">
                            <div id="progressBar" class="progress-bar"></div>
                        </div>
                        <div class="status-grid">
                            <div class="status-item">
                                <div style="font-weight: 600;">Statut</div>
                                <div id="statusText">Prêt</div>
                            </div>
                            <div class="status-item">
                                <div style="font-weight: 600;">Progression</div>
                                <div id="progressText">0%</div>
                            </div>
                            <div class="status-item">
                                <div style="font-weight: 600;">Étape</div>
                                <div id="stepText">-</div>
                            </div>
                            <div class="status-item">
                                <div style="font-weight: 600;">Avis trouvés</div>
                                <div id="totalText">0</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="panel">
                        <h2>⚡ Actions rapides</h2>
                        <div class="actions">
                            <button onclick="refreshPending()" class="btn">🔄 Rafraîchir</button>
                            <button onclick="getValidated()" class="btn btn-success">✅ Voir validés</button>
                            <button onclick="checkHealth()" class="btn">🏥 Health Check</button>
                        </div>
                    </div>
                </div>
                
                <div>
                    <div class="panel">
                        <h2>📋 Offres en attente</h2>
                        <div id="pendingContainer">
                            <p>Chargement...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let currentPage = 1;
            const limit = 20;
            
            // Fonction pour démarrer l'extraction
            document.getElementById('startBtn').addEventListener('click', function() {
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;
                
                const btn = this;
                btn.disabled = true;
                btn.innerHTML = '⏳ Extraction en cours...';
                
                fetch('/api/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ startDate, endDate })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        startStatusPolling();
                    } else {
                        alert('Erreur: ' + data.message);
                        btn.disabled = false;
                        btn.innerHTML = '🚀 Démarrer l\'extraction';
                    }
                });
            });
            
            // Fonction pour suivre le statut
            function startStatusPolling() {
                const interval = setInterval(() => {
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('statusText').textContent = data.status;
                            document.getElementById('progressText').textContent = data.progress + '%';
                            document.getElementById('stepText').textContent = data.step;
                            document.getElementById('totalText').textContent = data.total;
                            document.getElementById('progressBar').style.width = data.progress + '%';
                            
                            if (data.progress === 100) {
                                clearInterval(interval);
                                document.getElementById('startBtn').disabled = false;
                                document.getElementById('startBtn').innerHTML = '🚀 Démarrer l\'extraction';
                                refreshPending();
                            }
                        });
                }, 1000);
            }
            
            // Fonction pour rafraîchir les offres pending
            function refreshPending() {
                fetch(`/api/pending?page=${currentPage}&limit=${limit}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            displayPending(data.pending);
                        }
                    });
            }
            
            // Fonction pour afficher les offres pending
            function displayPending(pendingList) {
                const container = document.getElementById('pendingContainer');
                if (pendingList.length === 0) {
                    container.innerHTML = '<p>Aucune offre en attente</p>';
                    return;
                }
                
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th>Référence</th>
                                <th>Titre</th>
                                <th>Pays</th>
                                <th>Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                pendingList.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.reference || ''}</td>
                            <td title="${item.title || ''}">${(item.title || '').substring(0, 40)}...</td>
                            <td>${item.pays || ''}</td>
                            <td>${(item.publicationDate || '').substring(0, 10)}</td>
                            <td>
                                <button onclick="validateTender('${item.reference}')" class="btn btn-success" style="padding: 5px 10px; font-size: 0.9rem;">
                                    Valider
                                </button>
                                <button onclick="deleteTender('${item.reference}')" class="btn btn-danger" style="padding: 5px 10px; font-size: 0.9rem;">
                                    Supprimer
                                </button>
                            </td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                container.innerHTML = html;
            }
            
            // Fonction pour valider une offre
            function validateTender(reference) {
                if (!confirm(`Valider l'offre ${reference} ?`)) return;
                
                fetch(`/api/validate/${reference}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        if (data.success) {
                            refreshPending();
                        }
                    });
            }
            
            // Fonction pour supprimer une offre
            function deleteTender(reference) {
                if (!confirm(`Supprimer l'offre ${reference} ?`)) return;
                
                fetch(`/api/delete/${reference}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        refreshPending();
                    });
            }
            
            // Fonction pour exporter en Excel
            document.getElementById('exportBtn').addEventListener('click', function() {
                fetch('/api/export')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(`Export terminé: ${data.count} offres exportées`);
                        } else {
                            alert('Erreur: ' + data.message);
                        }
                    });
            });
            
            // Fonction pour vider les pending
            document.getElementById('clearBtn').addEventListener('click', function() {
                if (!confirm('Vider TOUTES les offres en attente ?')) return;
                
                fetch('/api/clear_pending', { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        refreshPending();
                    });
            });
            
            // Fonction pour voir les offres validées
            function getValidated() {
                fetch('/api/validated')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(`${data.total} offres validées`);
                        }
                    });
            }
            
            // Fonction pour health check
            function checkHealth() {
                fetch('/api/health')
                    .then(response => response.json())
                    .then(data => {
                        alert(`Statut: ${data.status}\nPending: ${data.database.pending_count}\nValidé: ${data.database.validated_count}`);
                    });
            }
            
            // Charger initialement les pending
            refreshPending();
        </script>
    </body>
    </html>
    '''

# ============================== DÉMARRAGE ==============================

if __name__ == "__main__":
    print("=" * 80)
    print("🌍 EXTRACTEUR BANQUE MONDIALE - VERSION FLASK COMPLÈTE")
    print("=" * 80)
    print("Configuration:")
    print(f"  MongoDB: {MONGO_URI}")
    print(f"  Base de données: {DB_NAME}")
    print(f"  Collection pending: {PENDING_COLLECTION_NAME}")
    print(f"  Collection validés: {COLLECTION_NAME}")
    print("=" * 80)
    print("Fonctionnalités:")
    print("✅ 4 stratégies d'extraction combinées")
    print("✅ Traduction automatique en français")
    print("✅ Sauvegarde MongoDB (pending + validés)")
    print("✅ Interface web complète")
    print("✅ Validation vers API externe")
    print("✅ Export Excel")
    print("=" * 80)
    print("Serveur démarré sur: http://localhost:5010")
    print("=" * 80)
    
    # Démarrer le serveur Flask
    app.run(debug=True, port=5010, host='0.0.0.0')