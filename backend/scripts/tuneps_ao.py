# ================================================
# TUNEPS Scraper - OFFRES[](https://www.tuneps.tn/portail/offres)
# Extraction lots → title + cautionnement → deposit
# ================================================
import os
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
import requests
import pandas as pd
from dateutil.parser import parse
from dateutil import tz
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import tenacity
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import unicodedata
import warnings
import traceback
from dataclasses import dataclass, field, asdict, fields
from typing import Optional, List, Dict, Tuple
import base64
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pdf2image import convert_from_path
from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import time
import random
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
warnings.filterwarnings('ignore')
load_dotenv()
# ===== CONFIGURATION =====
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/marmouch")
DB_NAME = "marmouchbd"
COLLECTION_NAME = "tenders_marmouch"
PENDING_COLLECTION_NAME = "pending_tenders_marmouch_bd"
# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
TENDER_UPDATE_ENDPOINT = f"{API_BASE_URL}/tenders"
TENDERS_ENDPOINT = f"{API_BASE_URL}/tenders"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
EMAIL = os.getenv("API_EMAIL", "mariem.bousalem@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "L96BhA6ODugl")
DEFAULT_SOURCE_ID = os.getenv("DEFAULT_SOURCE_ID", "817")
DEFAULT_PROMOTER_ID = os.getenv("DEFAULT_PROMOTER_ID", "223472")
DEFAULT_AVIS_ID = os.getenv("DEFAULT_AVIS_ID", "2")
DEFAULT_PAYS_ID = os.getenv("DEFAULT_PAYS_ID", "219")
DEFAULT_CURRENCY_ID = os.getenv("DEFAULT_CURRENCY_ID", "111")
# S3 Configuration
S3_BUCKET = "tender-s3"
S3_REGION = "de"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_ENDPOINT_URL = "https://s3.de.10.cloud.ovh.net"
# Paths
POPPLER_PATH = r"C:\poppler\Library\bin"
PDF_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\pdf_tuneps_extraction"
TUNEPS_CAPTURES_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\tunepscaptures"
IMAGES_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\images_tuneps"
OUTPUT_DIR = "output"
TEMPLATES_DIR = "output"
REACT_BUILD_DIR = "react-frontend/build"
EXCEL_DIR = "excel"
for directory in [PDF_DIR, TUNEPS_CAPTURES_DIR, IMAGES_DIR, OUTPUT_DIR, TEMPLATES_DIR, REACT_BUILD_DIR, EXCEL_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_offres.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
# MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
tenders_collection = db[COLLECTION_NAME]
pending_tenders_collection = db[PENDING_COLLECTION_NAME]
try:
    db.command('ping')
    logger.info("MongoDB connecté avec succès")
except PyMongoError as e:
    logger.error(f"Erreur MongoDB: {e}")
    raise
# Régions Tunisie
REGION_IDS = {
    "Ariana": 1, "Béja": 2, "Ben Arous": 4, "Bizerte": 5, "Gabès": 6,
    "Gafsa": 7, "Jendouba": 8, "Kairouan": 9, "Kasserine": 10, "Kébili": 11,
    "Manouba": 13, "Le Kef": 15, "Mahdia": 17, "Medenine": 16, "Monastir": 18,
    "Nabeul": 19, "Sfax": 20, "Sidi Bouzid": 22, "Siliana": 23, "Sousse": 24,
    "Tataouine": 25, "Tozeur": 26, "Tunis": 27, "Zaghouan": 28
}
@dataclass
class OffreBase:
    createdAt: str = ""
    updatedAt: str = ""
    extractionDate: str = ""
    deletedAt: Optional[str] = None
    status: str = "pending"
    description: str = ""
    full_content: str = ""
    expirationDate: str = ""
    publicationDate: str = ""
    startBiddingDate: Optional[str] = None
    type: str = "national"
    reference: str = ""
    specificationsReceivingAddress: str = ""
    offerValidityPeriod: str = ""
    nature: str = "public"
    fundingSource: Optional[str] = None
    fundingSourceType: str = "national"
    isMultiCurrency: bool = False
    sourceId: Optional[str] = None
    promoterId: Optional[str] = None
    currencyId: str = "111"
    createdById: Optional[str] = None
    updatedById: Optional[str] = None
    pays: str = "Tunisie"
    source: str = "TUNEPS"
    promoter: str = ""
    pieces_jointes: List[str] = field(default_factory=list)
    cahier_charge: str = ""
    cahier_charge_pdf: str = ""
    cahier_charge_pdf_filename: str = ""
    cahier_charge_pdf_base64: str = ""
    cahier_charge_url: str = ""
    image_path: str = ""
    image_filename: str = ""
    image_base64: str = ""
    s3_image_url: str = ""
    lots: List[Dict] = field(default_factory=list)
    mots_cles_detectes: List[str] = field(default_factory=list)
    avis: str = "appel d'offre"
    procedure: str = "N/A"
    type_marche: str = "Public"
    url_source: str = ""
    validationDate: Optional[str] = None
    region_id: Optional[int] = None
    ouverture_offres: str = ""
    offer_validity_duration: str = ""
    cautionnement_provisoire: str = "0"
    def __post_init__(self):
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()
        if not self.updatedAt:
            self.updatedAt = datetime.now().isoformat()
        if not self.extractionDate:
            self.extractionDate = datetime.now().isoformat()
    def to_dict(self):
        return asdict(self)
@dataclass
class OffreTuneps(OffreBase):
    pass
class TUNEPSScraper:
    def __init__(self, use_selenium=True, skip_s3=True):
        self.session = requests.Session()
        self.use_selenium = use_selenium
        self.driver = None
        self.access_token = None
        self.session_appeloffres = requests.Session()
        self.promoter_cache = {}
        self.offres_cache = []
        self.pending_set = set()
        self.validated_refs = set()
        self.logger = logging.getLogger(__name__)
        self.pdf_dir = PDF_DIR
        self.captures_dir = TUNEPS_CAPTURES_DIR
        self.images_dir = IMAGES_DIR
        self.output_dir = OUTPUT_DIR
        self.excel_dir = EXCEL_DIR
        self.skip_s3 = skip_s3
        self.poppler_path = POPPLER_PATH
        self.is_processing = False
        self.processing_start_time = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }
        self.session.headers.update(self.headers)
        self.appeloffres_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.default_source_id = DEFAULT_SOURCE_ID
        self.default_promoter_id = DEFAULT_PROMOTER_ID
        # URL vers /offres
        self.BASE_URL = "https://www.tuneps.tn/portail/offres"
     
        self.TIMEOUT = 30
        self.WAIT_TIME = 1
        self.DELAY_BETWEEN_CONSULTATIONS = (1.0, 2.0)
        self.DELAY_BETWEEN_PAGES = (1, 2) # Réduit pour plus de vitesse
        self.MAX_EMPTY_PAGES = 3 # Stop after 3 empty pages
        self.MAX_RETRIES = 2
        self.DATE_CUTOFF_DAYS = 90
        # S3 Client
        self.s3_client = None
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    endpoint_url=S3_ENDPOINT_URL
                )
                self.logger.info("Client S3 initialisé")
            except Exception as s3_e:
                self.logger.error(f"Erreur init S3: {s3_e}")
        self.load_pending_offers()
        self.load_validated_refs()
        self._load_pending_set()
        self._test_poppler()
    def _test_poppler(self):
        """Test Poppler"""
        try:
            test_pdf = None
            for file in os.listdir(self.pdf_dir):
                if file.endswith('.pdf'):
                    test_pdf = os.path.join(self.pdf_dir, file)
                    break
            if test_pdf and os.path.exists(test_pdf):
                images = convert_from_path(test_pdf, first_page=1, last_page=1, dpi=300, poppler_path=self.poppler_path)
                if images:
                    self.logger.info("Poppler test OK")
        except Exception as e:
            self.logger.error(f"Poppler non fonctionnel: {e}")
    def load_validated_refs(self):
        try:
            validated_docs = list(tenders_collection.find({"status": "active"}).sort("createdAt", -1))
            self.validated_refs = {doc.get("reference", "") for doc in validated_docs if doc.get("reference")}
            self.logger.info(f"{len(self.validated_refs)} références validées chargées")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement validées: {e}")
    def _load_pending_set(self):
        try:
            pending_docs = list(pending_tenders_collection.find({"status": "pending"}).sort("createdAt", -1))
            self.pending_set = set()
            for doc in pending_docs:
                ref = doc.get("reference", "")
                desc_hash = hash(doc.get("description", ""))
                self.pending_set.add((ref, desc_hash))
            self.logger.info(f"{len(self.pending_set)} pending chargés")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement pending set: {e}")
    def load_pending_offers(self):
        try:
            pending_docs = list(pending_tenders_collection.find({"status": "pending"}).sort("createdAt", -1))
            self.offres_cache = []
            for doc in pending_docs:
                clean_doc = {k: v for k, v in doc.items() if k in {f.name for f in fields(OffreTuneps)}}
                offre = OffreTuneps(**clean_doc)
                self.offres_cache.append(offre)
            self.logger.info(f"{len(self.offres_cache)} offres pending chargées")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement pending: {e}")
    def _init_driver(self):
        if self.driver:
            try:
                self.driver.execute_script("return 'alive';")
                return
            except:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.driver = None
        if not self.driver:
            try:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,3000")
                options.add_argument("--user-agent=" + self.headers["User-Agent"])
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
             
                # Use system ChromeDriver from environment variable or default path
                chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
                self.driver.set_page_load_timeout(self.TIMEOUT)
                self.driver.set_script_timeout(self.TIMEOUT)
                self.logger.info("Driver Selenium initialisé")
            except WebDriverException as e:
                self.logger.error(f"Échec init driver: {e}")
                self.use_selenium = False
                self.driver = None
    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    def nettoyer_texte(self, texte: str) -> str:
        if not texte:
            return ""
        texte = unicodedata.normalize('NFKD', str(texte))
        texte = ''.join(c for c in texte if not unicodedata.combining(c))
        texte = re.sub(r'{{.*?}}', '', texte)
        texte = re.sub(r'\s+', ' ', texte)
        texte = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', texte)
        return texte.strip()
    def clean_date_str(self, date_str: str) -> str:
        if not date_str:
            return ""
        date_str = re.sub(r'[\u200E\u200F\u202A-\u202E]', '', date_str)
        date_str = re.sub(r'[^\d/\-\s:]+', '', date_str)
        return date_str.strip()
    def parse_date(self, date_str):
        if not date_str or date_str == "N/A":
            return None
        try:
            date_str = self.clean_date_str(date_str)
            date_str = re.sub(r'h', ':', date_str)
            date_str = re.sub(r'\s+', ' ', date_str).strip()
         
            try:
                dt = datetime.strptime(date_str, '%d/%m/%Y %H:%M')
            except ValueError:
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                except ValueError:
                    dt = parse(date_str, fuzzy=True, tzinfos={None: tz.gettz('Africa/Tunis')})
         
            dt = dt.replace(tzinfo=tz.gettz('Africa/Tunis'))
            return dt.isoformat()
        except Exception as e:
            self.logger.warning(f"Erreur parsing date '{date_str}': {e}")
            return None
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def login_appeloffres(self) -> bool:
        if self.access_token:
            return True
        try:
            response = self.session_appeloffres.post(
                LOGIN_ENDPOINT,
                json={"email": EMAIL, "password": API_PASSWORD},
                headers=self.appeloffres_headers,
                timeout=30
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.access_token = data.get("accessToken")
                self.appeloffres_headers["Authorization"] = f"Bearer {self.access_token}"
                self.logger.info("Connexion API réussie")
                return True
            self.logger.error(f"Erreur connexion: {response.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur connexion: {e}")
            return False
    def get_or_create_promoter(self, promoter_name: str) -> str:
        if not promoter_name or promoter_name.strip() == "":
            promoter_name = "Promoteur TUNEPS Inconnu"
     
        clean_name = self.nettoyer_texte(promoter_name)
        if clean_name in self.promoter_cache:
            return self.promoter_cache[clean_name]
        if not self.login_appeloffres():
            return self.default_promoter_id
        payload = {
            "name": promoter_name,
            "description": f"Acheteur public TUNEPS: {promoter_name}",
            "reference": re.sub(r'\W+', '_', promoter_name.upper())[:20],
            "isEnabled": True,
            "companyName": promoter_name,
            "address": {"street": "Adresse inconnue", "city": "Tunis", "country": "Tunisie", "postalCode": "1000"}
        }
        try:
            response = self.session_appeloffres.post(PROMOTER_ENDPOINT, json=payload, headers=self.appeloffres_headers, timeout=30)
            if response.status_code in [200, 201]:
                promoter_id = str(response.json().get("id"))
                self.promoter_cache[clean_name] = promoter_id
                self.logger.info(f"Promoteur créé: {promoter_id}")
                return promoter_id
            else:
                return self.default_promoter_id
        except Exception as e:
            self.logger.error(f"Erreur promoteur: {e}")
            return self.default_promoter_id
    def extract_table_safe(self, driver, table_identifier):
        """
        Extraire un tableau de manière sécurisée depuis la page de détail.
        Pour les lots: extraire l'objet/titre → title ET cautionnement → deposit
        """
        try:
            table_xpaths = [
                f"//table[.//th[contains(text(), '{table_identifier}')]]",
                f"//table[.//td[contains(text(), '{table_identifier}')]]",
                f"//mat-table[.//mat-header-cell[contains(text(), '{table_identifier}')]]",
                f"//table[.//th[contains(translate(text(), 'LOT', 'lot'), 'lot')]]",
                f"//table[.//td[contains(translate(text(), 'LOT', 'lot'), 'lot')]]"
            ]
         
            table = None
            for xpath in table_xpaths:
                try:
                    table = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    break
                except:
                    continue
            if not table:
                return ""
            # Extraire headers
            headers = []
            try:
                header_elements = table.find_elements(By.CSS_SELECTOR, "th, mat-header-cell")
                headers = [h.text.strip() for h in header_elements if h.text.strip()]
            except:
                pass
            if not headers:
                return ""
            # Extraire data rows
            data = []
            try:
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr, mat-row")
                for row in rows:
                    try:
                        cells = row.find_elements(By.CSS_SELECTOR, "td, mat-cell, .mat-cell")
                        row_data = [cell.text.strip() for cell in cells]
                     
                        if any(row_data):
                            lot_dict = {}
                            for i, header in enumerate(headers):
                                if i < len(row_data):
                                    header_lower = header.lower()
                                 
                                    # Mapping intelligent des colonnes
                                    if 'objet' in header_lower or 'title' in header_lower or 'désignation' in header_lower or 'description' in header_lower:
                                        lot_dict['title'] = row_data[i]
                                        lot_dict['objet'] = row_data[i]
                                        lot_dict['description'] = row_data[i]
                                    elif 'caution' in header_lower or 'deposit' in header_lower or 'garantie' in header_lower:
                                        lot_dict['deposit'] = row_data[i]
                                        lot_dict['Cautionnement provisoire'] = row_data[i]
                                    elif 'montant' in header_lower or 'prix' in header_lower or 'estimation' in header_lower:
                                        lot_dict['montant_estime'] = row_data[i]
                                    elif 'lot' in header_lower or 'n°' in header_lower or 'numéro' in header_lower:
                                        lot_dict['numero_lot'] = row_data[i]
                                    else:
                                        lot_dict[header] = row_data[i]
                         
                            if lot_dict.get('title') or lot_dict.get('objet') or lot_dict.get('description'):
                                data.append(lot_dict)
                                self.logger.info(f"✅ Lot extrait: title='{lot_dict.get('title', 'N/A')}', deposit='{lot_dict.get('deposit', '0')}'")
                    except Exception as row_err:
                        self.logger.error(f"Erreur ligne lot: {row_err}")
                        continue
            except Exception as rows_err:
                self.logger.error(f"Erreur extraction rows: {rows_err}")
            return json.dumps(data, ensure_ascii=False) if data else ""
        except Exception as e:
            self.logger.error(f"Erreur extract_table_safe: {e}")
            return ""
    def get_value_safe(self, driver, label, timeout=10):
        """Extraire une valeur de manière sécurisée depuis la page de détail"""
        try:
            strategies = [
                f"//*[normalize-space(text())='{label}']/following-sibling::*[1]",
                f"//*[contains(normalize-space(text()), '{label}')]/following-sibling::*[1]",
                f"//div[contains(text(), '{label}')]/following-sibling::div[1]",
                f"//span[contains(text(), '{label}')]/following-sibling::span[1]",
                f"//label[contains(text(), '{label}')]/following-sibling::*[1]",
                f"//td[contains(text(), '{label}')]/following-sibling::td[1]",
                f"//th[contains(text(), '{label}')]/following-sibling::td[1]"
            ]
         
            for xpath in strategies:
                try:
                    element = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    value = element.text.strip()
                    if value and value not in ["N/A", "", "None"]:
                        value = re.sub(r'\s+', ' ', value).strip()
                        self.logger.info(f"Valeur extraite pour '{label}': {value}")
                        return value
                except:
                    continue
         
            # Fallback JS
            try:
                page_text = driver.execute_script("return document.body.innerText;")
                pattern = f"{label}\\s*:?\\s*([^\\n\\r]+?)(?:\\n|$)"
                match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    self.logger.info(f"Valeur JS pour '{label}': {value}")
                    return value
            except:
                pass
         
            self.logger.warning(f"Aucune valeur trouvée pour '{label}'")
            return ""
        except Exception as e:
            self.logger.error(f"Erreur get_value_safe pour '{label}': {e}")
            return ""
    def extraire_contenu_detaille(self, url: str, data: dict, reference: str) -> dict:
        """Extraire le contenu détaillé d'une offre avec lots et cautionnements"""
        contenu = {
            'description_complete': self.nettoyer_texte(data.get('Objet Offre', '')),
            'expiration_date': data.get('Dernier Délai', 'N/A'),
            'publication_date_full': 'N/A',
            'start_bidding_date_full': 'N/A',
            'expiration_date_full': 'N/A',
            'ouverture_offres': 'N/A',
            'offer_validity_duration': 'N/A',
            'cautionnement_provisoire': '0',
            'pieces_jointes': [],
            'lots': [],
            'texte_integral': '',
            'pdf_path': '',
            'pdf_filename': '',
            'image_path': '',
            'image_filename': '',
            'procedure': 'N/A',
            'type_marche': 'Public',
            'cahier_charge_url': '',
            's3_image_url': ''
        }
        try:
            self._init_driver()
            if not self.driver:
                raise WebDriverException("Driver non disponible")
            for attempt in range(self.MAX_RETRIES):
                try:
                    self.driver.get(url)
                    time.sleep(1) # Réduit pour vitesse
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//*[contains(text(), 'N° référence') or contains(text(), 'Objet')]")
                        )
                    )
                    time.sleep(0.5) # Réduit
                    # Extraction N° référence
                    n_ref = self.get_value_safe(self.driver, "N° référence", timeout=10)
                    num_offre = data.get("N° Offre", "")
                 
                    if n_ref and re.search(r'\d+/\d{2,4}', n_ref.strip()):
                        full_reference = f"{n_ref} - {num_offre}" if num_offre else n_ref
                    else:
                        full_reference = num_offre
                 
                    data["Reference"] = full_reference
                    self.logger.info(f"Référence complète: {full_reference}")
                    # Extraction dates
                    contenu['publication_date_full'] = self.get_value_safe(self.driver, "Date et heure publication", timeout=10)
                    contenu['start_bidding_date_full'] = self.get_value_safe(self.driver, "Date et heure du commencement d'envoi des offres", timeout=10)
                    contenu['expiration_date_full'] = self.get_value_safe(self.driver, "Dernier délai réception offres", timeout=10)
                    contenu['ouverture_offres'] = self.get_value_safe(self.driver, "Date et heure d'ouverture des offres", timeout=10)
                    contenu['offer_validity_duration'] = self.get_value_safe(self.driver, "Durée de validité de l'offre", timeout=10)
                    # Cautionnement global
                    global_caution = self.get_value_safe(self.driver, "Cautionnement provisoire", timeout=5)
                    if global_caution:
                        contenu['cautionnement_provisoire'] = global_caution
                    else:
                        contenu['cautionnement_provisoire'] = '0'
                    # Extraction LOTS
                    self.logger.info("🔍 Extraction des lots...")
                    lots_json = self.extract_table_safe(self.driver, "Lot")
                    if lots_json:
                        lots = json.loads(lots_json)
                        contenu['lots'] = lots
                        self.logger.info(f"✅ {len(lots)} lot(s) extrait(s)")
                     
                        if not global_caution and lots:
                            first_lot_caution = lots[0].get("deposit", "0") or lots[0].get("Cautionnement provisoire", "0")
                            contenu['cautionnement_provisoire'] = first_lot_caution
                            self.logger.info(f"Cautionnement du 1er lot: {first_lot_caution}")
                    else:
                        self.logger.warning("Aucun lot trouvé")
                    # Documents
                    docs_json = self.extract_table_safe(self.driver, "Document")
                    if docs_json:
                        contenu['pieces_jointes'] = json.loads(docs_json)
                    # Texte intégral
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    main_content = soup.select_one('main, article, div.offer-details')
                    texte_integral = main_content.get_text(separator=' ', strip=True) if main_content else soup.get_text(separator=' ', strip=True)
                    contenu['texte_integral'] = texte_integral
                    # PDF
                    pdf_links = soup.find_all('a', href=re.compile(r'.pdf$', re.I))
                    if pdf_links:
                        pdf_url = urljoin(url, pdf_links[0]['href'])
                        contenu['cahier_charge_url'] = pdf_url
                        if not self.skip_s3:
                            pdf_path, pdf_filename = self.telecharger_pdf_tuneps(pdf_url, full_reference)
                            if pdf_path:
                                contenu['pdf_path'] = pdf_path
                                contenu['pdf_filename'] = pdf_filename
                    break
                except Exception as e:
                    self.logger.error(f"Erreur extraction détail (tentative {attempt+1}): {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(1)
                        continue
        except Exception as e:
            self.logger.error(f"ERREUR EXTRACTION CONTENU: {e}")
        self.logger.info(f"📋 Résumé pour {data.get('Reference', reference)}: {len(contenu.get('lots', []))} lot(s), caution={contenu['cautionnement_provisoire']}")
        return contenu
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def telecharger_pdf_tuneps(self, pdf_url: str, reference: str) -> Tuple[str, str]:
        try:
            if not pdf_url or not reference:
                return "", ""
         
            filename = f"{reference}.pdf"
            pdf_path = os.path.join(self.pdf_dir, filename)
         
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                if file_size > 100:
                    self.logger.info(f"PDF déjà présent: {pdf_path}")
                    return pdf_path, filename
                else:
                    os.remove(pdf_path)
            if self.skip_s3:
                return "", ""
            response = self.session.get(pdf_url, timeout=30, stream=True)
            if response.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
             
                if os.path.exists(pdf_path):
                    file_size = os.path.getsize(pdf_path)
                    if file_size > 100:
                        self.logger.info(f"PDF téléchargé: {pdf_path} ({file_size} octets)")
                        return pdf_path, filename
                    else:
                        os.remove(pdf_path)
         
            return "", ""
        except Exception as e:
            self.logger.error(f"Erreur téléchargement PDF: {e}")
            return "", ""
    def save_to_pending(self, offre):
        try:
            desc_hash = hash(offre.description)
            if offre.reference in self.validated_refs:
                self.logger.warning(f"Doublon détecté: {offre.reference} déjà validé")
                return False
            if (offre.reference, desc_hash) in self.pending_set:
                self.logger.warning(f"Doublon détecté: {offre.reference} déjà pending")
                return False
            tender_dict = offre.to_dict()
            tender_dict["status"] = "pending"
            result = pending_tenders_collection.insert_one(tender_dict)
         
            if result.inserted_id:
                self.pending_set.add((offre.reference, desc_hash))
                self.logger.info(f"✅ Offre sauvegardée en pending: {offre.reference}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur save pending: {e}")
            return False
    def map_offre_to_tender_payload(self, offre) -> dict:
        """Mapper l'offre vers le payload API avec batches[].title + batches[].deposit"""
        publication_ts = self.parse_date(offre.publicationDate)
        start_bidding_ts = self.parse_date(offre.startBiddingDate)
        if start_bidding_ts is None:
            start_bidding_ts = publication_ts
     
        expiration_ts = self.parse_date(offre.expirationDate)
        opening_ts = self.parse_date(offre.ouverture_offres)
        if expiration_ts is None:
            if publication_ts:
                pub_dt = datetime.fromisoformat(publication_ts.replace('Z', '+00:00'))
                exp_dt = (pub_dt + timedelta(days=30)).replace(hour=12, minute=0, second=0, microsecond=0)
                expiration_ts = exp_dt.isoformat()
            else:
                exp_dt = (datetime.now(timezone.utc) + timedelta(days=30)).replace(hour=12, minute=0, second=0, microsecond=0)
                expiration_ts = exp_dt.isoformat()
        # Construction des batches
        batches = []
     
        def clean_deposit(dep_str):
            if not dep_str:
                return "0"
            cleaned = re.sub(r'[^\d\s,.]', '', str(dep_str)).strip()
            return cleaned or "0"
        if offre.lots:
            for i, lot in enumerate(offre.lots, 1):
                lot_title = (
                    lot.get("title") or
                    lot.get("objet") or
                    lot.get("description") or
                    f"Lot {i}"
                )
             
                lot_deposit = (
                    lot.get("deposit") or
                    lot.get("Cautionnement provisoire") or
                    offre.cautionnement_provisoire or
                    "0"
                )
                deposit = clean_deposit(lot_deposit)
             
                batches.append({
                    "activitiesIds": [],
                    "title": lot_title,
                    "deposit": deposit
                })
             
                self.logger.info(f"✅ Batch {i}: title='{lot_title[:50]}...', deposit='{deposit}'")
     
        # Fallback: batch unique
        if not batches:
            raw_description = str(offre.description).strip()
            if not raw_description:
                raw_description = f"Appel d'offres TUNEPS - Référence: {offre.reference}"
         
            global_deposit = clean_deposit(offre.cautionnement_provisoire)
         
            batches = [{
                "activitiesIds": [],
                "title": raw_description,
                "deposit": global_deposit
            }]
         
            self.logger.info(f"Batch unique: title='{raw_description[:50]}...', deposit='{global_deposit}'")
        promoter_id = self.get_or_create_promoter(offre.promoter)
     
        source_id = int(self.default_source_id)
        currency_id = int(DEFAULT_CURRENCY_ID)
        avis_id = int(DEFAULT_AVIS_ID)
        region_id = offre.region_id
        raw_description = str(offre.description).strip()
        if not raw_description:
            raw_description = f"Appel d'offres TUNEPS - Référence: {offre.reference}"
        title_parts = [raw_description]
        if offre.lots and len(offre.lots) > 1:
            lots_titles = [lot.get("title", lot.get("objet", lot.get("description", ""))) for lot in offre.lots if lot.get("title") or lot.get("objet") or lot.get("description")]
            if lots_titles:
                title_parts.append(f"Lots: {', '.join(lots_titles[:3])}")
     
        title = " - ".join(title_parts)
        description = raw_description
        addresses = [{"countryId": DEFAULT_PAYS_ID}]
        if region_id:
            addresses[0]["regionId"] = str(region_id)
        offer_validity_periode = None
        if offre.offer_validity_duration and offre.offer_validity_duration != 'N/A':
            offer_validity_periode = offre.offer_validity_duration
        images = []
        if offre.s3_image_url:
            images = [{"url": offre.s3_image_url, "description": "Capture TUNEPS"}]
        else:
            images = [{"url": "https://placeholder.com/tuneps-image.jpg", "description": "Image placeholder"}]
        payload = {
            "title": title,
            "description": description,
            "publicationDate": publication_ts,
            "startBiddingDate": start_bidding_ts,
            "expirationDate": expiration_ts,
            "openingBidsDate": opening_ts,
            "reference": offre.reference,
            "specificationsPrice": 0,
            "offerValidityPeriode": offer_validity_periode,
            "avisId": avis_id,
            "sourceId": source_id,
            "promoterId": int(promoter_id),
            "type": offre.type,
            "nature": offre.nature,
            "isEnabled": True,
            "specificationsReceivingAddress": offre.url_source or "URL non disponible",
            "fundingSourceType": "national",
            "fundingSource": None if offre.fundingSource is None else offre.fundingSource,
            "currencyId": currency_id,
            "isMultiCurrency": offre.isMultiCurrency,
            "batches": batches,
            "addresses": addresses,
            "images": images
        }
        filtered_payload = {k: v for k, v in payload.items() if v is not None and v != ""}
     
        self.logger.info(f"📤 Payload API pour {offre.reference}: {len(batches)} lot(s)")
     
        return filtered_payload
    @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_exponential(multiplier=2, min=4, max=20))
    def post_tender_to_database(self, offre) -> dict:
        existing = tenders_collection.find_one({"reference": offre.reference})
        if existing:
            self.logger.info(f"Offre {offre.reference} existe déjà")
            return {"success": False, "message": "Offre déjà validée", "offre_ref": offre.reference}
        tender_dict = offre.to_dict()
        tender_dict["status"] = "active"
        tender_dict["validationDate"] = datetime.now().isoformat()
        try:
            result = tenders_collection.insert_one(tender_dict)
            if result.inserted_id:
                pending_deleted = pending_tenders_collection.delete_one({"reference": offre.reference})
                if pending_deleted.deleted_count > 0:
                    to_remove = [(r, h) for r, h in self.pending_set if r == offre.reference]
                    for tup in to_remove:
                        self.pending_set.discard(tup)
             
                self.validated_refs.add(offre.reference)
             
                api_success = False
                api_id = None
                api_message = ""
             
                try:
                    if not self.login_appeloffres():
                        api_message = "Échec connexion API"
                    else:
                        payload = self.map_offre_to_tender_payload(offre)
                        response = self.session_appeloffres.post(
                            TENDER_ENDPOINT,
                            json=payload,
                            headers=self.appeloffres_headers,
                            timeout=30
                        )
                     
                        if response.status_code in [200, 201]:
                            api_data = response.json()
                            api_id = api_data.get("id")
                            api_success = True
                            api_message = f"Envoi API réussi - ID: {api_id}"
                            self.logger.info(f"✅ ENVOI API RÉUSSI: {offre.reference} - ID: {api_id}")
                         
                            tenders_collection.update_one(
                                {"_id": result.inserted_id},
                                {"$set": {"api_id": api_id}}
                            )
                        else:
                            api_message = f"Échec API: {response.status_code} - {response.text}"
                            self.logger.error(f"❌ ENVOI API ÉCHOUÉ: {api_message}")
                except Exception as api_e:
                    api_message = f"Erreur API: {str(api_e)}"
                    self.logger.error(f"❌ ERREUR API: {api_e}")
                message = "Insertion réussie en DB"
                if api_success:
                    message += f" et envoi API (ID: {api_id})"
                else:
                    message += f" mais échec API: {api_message}"
                return {
                    "success": True,
                    "message": message,
                    "offre_ref": offre.reference,
                    "mongo_id": str(result.inserted_id),
                    "api_id": api_id,
                    "api_success": api_success
                }
            else:
                raise PyMongoError("Insertion échouée")
        except PyMongoError as e:
            self.logger.error(f"Erreur MongoDB: {e}")
            return {"success": False, "message": f"Erreur MongoDB: {str(e)}", "offre_ref": offre.reference}
    # ⭐ FONCTION AMÉLIORÉE: Extraction robuste de l'ID
    def extract_all_rows_data(self):
        """Extraire toutes les lignes du tableau des offres avec extraction robuste de l'ID"""
        consultations = []
        driver = self.driver
     
        try:
            time.sleep(0.5) # Réduit pour vitesse
         
            # Forcer l'affichage de colonnes cachées
            script = """
            var style = document.createElement('style');
            style.innerHTML = '.mat-column-spShopMasterId, .mat-column-id, .mat-column-offerId { display: table-cell !important; visibility: visible !important; }';
            document.head.appendChild(style);
            """
            driver.execute_script(script)
            time.sleep(0.5)
         
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, mat-row")
         
            if not rows:
                return consultations
            self.logger.info(f"\n{len(rows)} lignes détectées")
            for idx, row in enumerate(rows):
                try:
                    # ⭐ STRATÉGIE 1: Extraire l'ID depuis href
                    id1 = ""
                    try:
                        links = row.find_elements(By.CSS_SELECTOR, "a[href*='/offres/details/'], a[href*='/details/']")
                        if links:
                            href = links[0].get_attribute('href')
                            match = re.search(r'/details/(\d{6})/(\d+)', href)
                            if match:
                                id1 = match.group(1)
                                self.logger.info(f"✅ ID extrait depuis href: {id1}")
                    except:
                        pass
                 
                    # ⭐ STRATÉGIE 2: Attributs data-*
                    if not id1:
                        try:
                            data_attrs = driver.execute_script("""
                                var row = arguments[0];
                                var attrs = {};
                                for (var i = 0; i < row.attributes.length; i++) {
                                    var attr = row.attributes[i];
                                    if (attr.name.startsWith('data-')) {
                                        attrs[attr.name] = attr.value;
                                    }
                                }
                                return attrs;
                            """, row)
                         
                            for key, value in data_attrs.items():
                                if value and str(value).isdigit() and len(str(value)) == 6:
                                    id1 = str(value)
                                    self.logger.info(f"✅ ID extrait depuis {key}: {id1}")
                                    break
                        except:
                            pass
                 
                    # ⭐ STRATÉGIE 3: Cellules visibles
                    all_cells = row.find_elements(By.CSS_SELECTOR, "td, mat-cell, .mat-cell")
                    all_texts = [cell.text.strip() for cell in all_cells]
                 
                    js_texts = driver.execute_script("""
                        var row = arguments[0];
                        var cells = row.querySelectorAll('td, mat-cell, .mat-cell');
                        var values = [];
                        cells.forEach(function(cell) {
                            values.push(cell.innerText || cell.textContent || '');
                        });
                        return values;
                    """, row)
                 
                    # ⭐ STRATÉGIE 4: Colonnes cachées
                    if not id1:
                        try:
                            selectors = [
                                ".mat-column-spShopMasterId",
                                ".mat-column-id",
                                ".mat-column-offerId",
                                ".mat-column-consultationId",
                                "td[data-column='id']",
                                "mat-cell[data-column='id']"
                            ]
                         
                            for selector in selectors:
                                try:
                                    id1_cell = row.find_element(By.CSS_SELECTOR, selector)
                                    id1 = id1_cell.text.strip() or driver.execute_script(
                                        "return arguments[0].innerText || arguments[0].textContent || '';",
                                        id1_cell
                                    ).strip()
                                    if id1 and id1.isdigit() and len(id1) == 6:
                                        self.logger.info(f"✅ ID extrait depuis {selector}: {id1}")
                                        break
                                except:
                                    continue
                        except:
                            pass
                 
                    # ⭐ STRATÉGIE 5: Textes cellules
                    if not id1:
                        for text in all_texts + js_texts:
                            if text and text.isdigit() and len(text) == 6:
                                id1 = text
                                self.logger.info(f"✅ ID extrait depuis texte: {id1}")
                                break
                 
                    # ⭐ STRATÉGIE 6: N° Offre
                    num_offre = all_texts[0] if len(all_texts) > 0 else ""
                    if not id1 and num_offre:
                        match = re.search(r'(\d{6})$', num_offre)
                        if match:
                            id1 = match.group(1)
                            self.logger.info(f"✅ ID extrait depuis N° Offre: {id1}")
                 
                    # Warnings si échec
                    if not id1:
                        self.logger.warning(f"⚠️ Ligne {idx+1}: Impossible d'extraire l'ID")
                        self.logger.warning(f" Cellules: {all_texts[:5]}")
                 
                    basic_data = {
                        "N° Offre": num_offre,
                        "Acheteur public": all_texts[1] if len(all_texts) > 1 else "",
                        "Date Publication": all_texts[2] if len(all_texts) > 2 else "",
                        "Objet Offre": all_texts[3] if len(all_texts) > 3 else "",
                        "Dernier Délai": all_texts[4] if len(all_texts) > 4 else "",
                        "_id1": id1
                    }
                 
                    consultations.append(basic_data)
                 
                except Exception as e:
                    self.logger.error(f"Erreur ligne {idx+1}: {str(e)[:80]}")
                    continue
            return consultations
        except Exception as e:
            self.logger.error(f"Erreur extraction: {str(e)[:80]}")
            return consultations
    def click_next_page(self):
        driver = self.driver
        try:
            next_selectors = [
                ".mat-paginator-navigation-next",
                "button[aria-label*='suivant']",
                "button[aria-label*='next']"
            ]
         
            next_button = None
            for selector in next_selectors:
                try:
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if next_button.get_attribute("disabled"):
                        return False
                    break
                except:
                    continue
            if not next_button:
                return False
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(0.5) # Réduit
            driver.execute_script("arguments[0].click();", next_button)
         
            WebDriverWait(driver, self.TIMEOUT).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr, mat-row"))
            )
            time.sleep(self.WAIT_TIME)
            return True
        except:
            return False
    def should_stop_scraping(self, rows_data, page_num):
        """Condition d'arrêt basée sur dates anciennes (comme tuneps.py)"""
        if not rows_data:
            return False

        cutoff_date = datetime.now().date() - timedelta(days=self.DATE_CUTOFF_DAYS)
        all_old = True

        for r in rows_data:
            pub_date_str = r.get("Date Publication", "")
            exp_date_str = r.get("Dernier Délai", "")

            pub_date = None
            date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %m %Y"]

            for fmt in date_formats:
                try:
                    pub_date = datetime.strptime(pub_date_str.strip().split()[0], fmt).date()
                    break
                except ValueError:
                    continue

            if pub_date and pub_date >= cutoff_date:
                all_old = False
                break

            exp_date = None
            for fmt in date_formats:
                try:
                    exp_date = datetime.strptime(exp_date_str.strip().split()[0], fmt).date()
                    break
                except ValueError:
                    continue

            if exp_date and exp_date >= cutoff_date:
                all_old = False
                break

        if all_old:
            self.logger.info(f"Arrêt scraping à page {page_num}: Toutes dates (pub/exp) > {self.DATE_CUTOFF_DAYS} jours anciennes ({cutoff_date})")
            return True

        return False

    def is_between_dates(self, date_str, start_date_str, end_date_str):
        try:
            if not date_str or date_str in ["N/A", ""]:
                return False

            date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %m %Y"]
            pub_date = None
            for fmt in date_formats:
                try:
                    pub_date = datetime.strptime(date_str.strip().split()[0], fmt).date()
                    break
                except ValueError:
                    continue
            if not pub_date:
                return False
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
            if start_date and end_date:
                return start_date <= pub_date <= end_date
            elif start_date:
                return pub_date >= start_date
            elif end_date:
                return pub_date <= end_date
            else:
                return True
        except Exception as e:
            self.logger.warning(f"Erreur filtrage date '{date_str}': {e}")
            return False
    def process_single_detail(self, data):
        """Traiter une offre individuelle"""
        reference = data.get("Reference", data.get("N° Offre", ""))
        url = data.get("URL_Detail", "")
        i = data.get("index", 0)
     
        self.logger.info(f"🔍 Thread: Traitement offre {i}: {data.get('N° Offre', 'N/A')}")
     
        if not url:
            self.logger.warning(f"⚠️ Pas d'URL pour offre {i}: {reference}")
            return None
        extraction_complete = getattr(self, 'extraction_complete_mode', True)
        contenu = self.extraire_contenu_detaille(url, data, reference) if extraction_complete else {}
        region_id = None
        clean_promoter = self.nettoyer_texte(data.get("Acheteur public", ""))
        clean_promoter_words = set(clean_promoter.split())
     
        for region, rid in REGION_IDS.items():
            clean_region = self.nettoyer_texte(region)
            clean_region_words = set(clean_region.split())
            if clean_region in clean_promoter or any(word in clean_promoter_words for word in clean_region_words):
                region_id = rid
                break
        raw_desc = self.nettoyer_texte(data.get("Objet Offre", ""))
        if not raw_desc.strip():
            raw_desc = f"Appel d'offres TUNEPS - Référence: {reference}"
        start_bidding_full = contenu.get('start_bidding_date_full', contenu.get('publication_date_full', 'N/A')) if extraction_complete else data.get("Date Publication", "N/A")
        offre = OffreTuneps(
            reference=reference,
            description=raw_desc,
            full_content=contenu.get('texte_integral', '') if extraction_complete else raw_desc,
            promoter=self.nettoyer_texte(data.get("Acheteur public", "")),
            publicationDate=contenu.get('publication_date_full', data.get("Date Publication", "N/A")) if extraction_complete else data.get("Date Publication", "N/A"),
            startBiddingDate=start_bidding_full,
            expirationDate=contenu.get('expiration_date_full', data.get("Dernier Délai", "N/A")) if extraction_complete else data.get("Dernier Délai", "N/A"),
            ouverture_offres=contenu.get('ouverture_offres', "N/A") if extraction_complete else "N/A",
            offer_validity_duration=contenu.get('offer_validity_duration', 'N/A') if extraction_complete else 'N/A',
            cautionnement_provisoire=contenu.get('cautionnement_provisoire', '0') if extraction_complete else '0',
            pieces_jointes=contenu.get('pieces_jointes', []) if extraction_complete else [],
            cahier_charge=contenu.get('pdf_path', '') if extraction_complete else '',
            cahier_charge_pdf=contenu.get('pdf_path', '') if extraction_complete else '',
            cahier_charge_pdf_filename=contenu.get('pdf_filename', '') if extraction_complete else '',
            cahier_charge_url=contenu.get('cahier_charge_url', '') if extraction_complete else '',
            image_path=contenu.get('image_path', '') if extraction_complete else '',
            image_filename=contenu.get('image_filename', '') if extraction_complete else '',
            s3_image_url=contenu.get('s3_image_url', '') if extraction_complete else '',
            lots=contenu.get('lots', []) if extraction_complete else [],
            mots_cles_detectes=[],
            sourceId=self.default_source_id,
            promoterId=None,
            fundingSource=None,
            procedure=contenu.get('procedure', 'N/A') if extraction_complete else 'N/A',
            type_marche=contenu.get('type_marche', 'Public') if extraction_complete else 'Public',
            url_source=url,
            region_id=region_id
        )
        if self.save_to_pending(offre):
            self.offres_cache.append(offre)
            self.logger.info(f"✅ Offre {reference} ajoutée (pending)")
            return offre
        else:
            self.logger.warning(f"Offre {reference} skippée (doublon)")
            return None
    _scrape_lock = threading.Lock()
    def scraper_offres_tuneps(self, start_date: str = None, end_date: str = None, extraction_complete: bool = False) -> List:
        """Scraper les appels d'offres depuis /portail/offres"""
        if self.is_processing:
            self.logger.warning("Scraping déjà en cours")
            return []
        self.is_processing = True
        self.processing_start_time = time.time()
        self.extraction_complete_mode = extraction_complete
     
        self.logger.info(f"🚀 Début scraping TUNEPS OFFRES ({datetime.now().strftime('%d/%m/%Y %H:%M')})")
        self.logger.info(f"📅 Dates: {start_date} à {end_date}")
        self.logger.info(f"🔧 Mode complete: {extraction_complete}")
        with self._scrape_lock:
            self._init_driver()
            if not self.use_selenium or not self.driver:
                self.logger.error("Selenium unavailable")
                self.is_processing = False
                return []
            all_consultations = []
            all_refs = set()
            empty_pages = 0
            try:
                max_retries_get = 3
                for retry_get in range(max_retries_get):
                    try:
                        self.driver.get(self.BASE_URL)
                        time.sleep(self.WAIT_TIME)
                        self.logger.info(f"✅ Page offres chargée (tentative {retry_get+1})")
                        break
                    except TimeoutException as te:
                        self.logger.warning(f"Timeout BASE_URL (tentative {retry_get+1}): {te}")
                        if retry_get < max_retries_get - 1:
                            self._init_driver()
                            time.sleep(5)
                        else:
                            raise te
                page = 1
                while True:  # No max pages limit, stop based on dates/empty pages
                    self.logger.info(f"\n📄 Traitement page {page}...")
                 
                    try:
                        WebDriverWait(self.driver, self.TIMEOUT).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr, mat-row"))
                        )
                    except TimeoutException:
                        self.logger.warning("Timeout chargement page")
                        break
                    rows_data = self.extract_all_rows_data()
                    self.logger.info(f"📊 {len(rows_data)} lignes extraites sur page {page}")

                    # Filtrer par plage de dates
                    rows_data = [r for r in rows_data if self.is_between_dates(r.get("Date Publication", ""), start_date, end_date)]

                    if not rows_data:
                        empty_pages += 1
                        self.logger.info(f"Aucune offre dans la plage ({empty_pages}/3)")
                        if empty_pages >= 3:
                            self.logger.info("Arrêt automatique : aucune donnée dans la plage trouvée.")
                            break
                    else:
                        empty_pages = 0

                    # Vérifier si on doit arrêter basé sur les dates anciennes (comme tuneps.py)
                    if self.should_stop_scraping(rows_data, page):
                        break
                    for r in rows_data:
                        id1 = r.get("_id1", "")
                        num_offre = r.get("N° Offre", "")
                     
                        if id1 and num_offre:
                            r["URL_Detail"] = f"https://www.tuneps.tn/portail/offres/details/{id1}/{num_offre}"
                        else:
                            r["URL_Detail"] = ""
                            self.logger.warning(f"ID ou N° offre manquant: {r}")
                        r["Reference"] = num_offre
                        r["Source"] = "tuneps"
                        r["Pays"] = "tunisie"
                        key = r["N° Offre"]
                        if key not in all_refs:
                            all_consultations.append(r)
                            all_refs.add(key)
                    self.logger.info(f"{len(rows_data)} offres dans la plage sur page {page}")
                    if not self.click_next_page():
                        self.logger.info("Fin de pagination")
                        break
                    page += 1
                    time.sleep(random.uniform(*self.DELAY_BETWEEN_PAGES))
                self.logger.info(f"\n✅ Extraction liste terminée: {len(all_consultations)} offres")
                if not all_consultations:
                    self.logger.info("Aucune offre trouvée")
                    self.is_processing = False
                    return []
                offres = []
                self.logger.info(f"🚀 Lancement {len(all_consultations)} threads (max_workers=5)")
             
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for i, data in enumerate(all_consultations, 1):
                        data["index"] = i
                        future = executor.submit(self.process_single_detail, data)
                        futures.append(future)
                    for future in futures:
                        result_offre = future.result()
                        if result_offre:
                            offres.append(result_offre)
                if offres:
                    excel_filename = f"tuneps_offres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    excel_path = os.path.join(self.excel_dir, excel_filename)
                    df = pd.DataFrame([o.to_dict() for o in offres])
                    df.to_excel(excel_path, index=False, engine='openpyxl')
                    self.logger.info(f"📊 Export Excel: {excel_path} ({len(offres)} lignes)")
                self.logger.info(f"🎉 Scraping terminé: {len(offres)} offres")
                return offres
            finally:
                processing_duration = time.time() - self.processing_start_time if self.processing_start_time else 0
                self.is_processing = False
                self.processing_start_time = None
                self.logger.info(f"⏱️ Durée totale: {processing_duration:.2f}s")
             
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.driver = None
    def get_offres_cache(self, page: int = 1, limit: int = 10):
        if self.is_processing:
            duration = time.time() - self.processing_start_time if self.processing_start_time else 0
            return {
                "processing": True,
                "message": f"Scraping en cours ({duration:.2f}s)...",
                "total": 0,
                "page": page,
                "limit": limit,
                "totalPages": 0,
                "offres": []
            }
        total = len(self.offres_cache)
        start = (page - 1) * limit
        end = start + limit
        paginated_offres = self.offres_cache[start:end]
        return {
            "offres": [
                {
                    "reference": offre.reference,
                    "description": offre.description,
                    "promoter": offre.promoter,
                    "publicationDate": offre.publicationDate,
                    "startBiddingDate": offre.startBiddingDate,
                    "expirationDate": offre.expirationDate,
                    "extractionDate": offre.extractionDate,
                    "ouverture_offres": offre.ouverture_offres,
                    "offer_validity_duration": offre.offer_validity_duration,
                    "cautionnement_provisoire": offre.cautionnement_provisoire,
                    "cahier_charge_pdf": offre.cahier_charge_pdf,
                    "cahier_charge_pdf_filename": offre.cahier_charge_pdf_filename,
                    "cahier_charge_url": offre.cahier_charge_url,
                    "image_filename": offre.image_filename,
                    "s3_image_url": offre.s3_image_url,
                    "lots": offre.lots,
                    "procedure": offre.procedure,
                    "type_marche": offre.type_marche,
                    "url_source": offre.url_source,
                    "status": offre.status,
                    "mots_cles_detectes": offre.mots_cles_detectes,
                    "region_id": offre.region_id
                } for offre in paginated_offres
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit
        }
    def update_offre_in_cache(self, reference: str, updated_data: dict) -> bool:
        for i, offre in enumerate(self.offres_cache):
            if offre.reference == reference:
                for key, value in updated_data.items():
                    if hasattr(offre, key):
                        setattr(offre, key, value)
                pending_tenders_collection.replace_one({"reference": reference}, offre.to_dict())
                self.logger.info(f"Offre {reference} mise à jour")
                return True
        return False
    def delete_pending_offre(self, reference: str) -> bool:
        try:
            result = pending_tenders_collection.delete_one({"reference": reference, "status": "pending"})
            if result.deleted_count > 0:
                self.offres_cache = [o for o in self.offres_cache if o.reference != reference]
                to_remove = [(r, h) for r, h in self.pending_set if r == reference]
                for tup in to_remove:
                    self.pending_set.discard(tup)
                self.logger.info(f"Offre supprimée: {reference}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur delete pending: {e}")
            return False
    def delete_validated_offre(self, reference: str) -> bool:
        try:
            result = tenders_collection.delete_one({"reference": reference, "status": "active"})
            if result.deleted_count > 0:
                self.validated_refs.discard(reference)
                self.logger.info(f"Offre validée supprimée: {reference}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur delete validated: {e}")
            return False
    def get_tenders_from_db(self, limit=100):
        try:
            tenders = list(tenders_collection.find({"status": "active"}).limit(limit).sort("createdAt", -1))
            for tender in tenders:
                tender["_id"] = str(tender["_id"])
                tender["extractionDate"] = tender.get("extractionDate", "")
                tender["validationDate"] = tender.get("validationDate", "")
            return tenders
        except PyMongoError as e:
            self.logger.error(f"Erreur récupération DB: {e}")
            return []
# ===== FLASK APP =====
app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path='/static', template_folder=REACT_BUILD_DIR)
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["*"], supports_credentials=True)
scraper = TUNEPSScraper(use_selenium=True, skip_s3=True)
def run_automatic_scrape():
    try:
        tunisia_tz = pytz.timezone('Africa/Tunis')
        logger.info("🤖 Extraction automatique TUNEPS OFFRES (mode rapide)")
        scraper.scraper_offres_tuneps(extraction_complete=False)
        logger.info(f"✅ Extraction automatique terminée ({datetime.now(tunisia_tz).strftime('%H:%M:%S')})")
    except Exception as e:
        logger.error(f"❌ Scheduler failed: {e}")
scheduler = BackgroundScheduler()
scheduler.add_job(
    run_automatic_scrape,
    'cron',
    hour=7,
    minute=30,
    timezone='Africa/Tunis',
    misfire_grace_time=3600,
    coalesce=True,
    max_instances=1
)
scheduler.start()
logger.info("⏰ Scheduler: Extraction quotidienne à 7h30 (Tunisie)")
# ===== ROUTES API =====
@app.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({
        "message": "Backend TUNEPS OFFRES OK",
        "base_url": scraper.BASE_URL,
        "pending_count": len(scraper.offres_cache),
        "processing": scraper.is_processing
    })
@app.route('/api/scrape', methods=['POST', 'OPTIONS'])
def scrape():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        logger.info("📡 OPTIONS preflight received")
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    logger.info("📡 /api/scrape appelée (POST)")
    try:
        # Get JSON data from request
        logger.info(f"📡 Request content-type: {request.content_type}")
        logger.info(f"📡 Request data (raw): {request.data}")
        data = request.get_json(force=True, silent=True) or {}
        logger.info(f"📡 Data received: {data}")

        # Support both 'start'/'end' and 'start_date'/'end_date'
        start_date = data.get('start') or data.get('start_date')
        end_date = data.get('end') or data.get('end_date')

        # Convertir les chaînes vides en None
        if start_date == "":
            start_date = None
        if end_date == "":
            end_date = None

        complete_mode = data.get('extraction_complete', False)
        logger.info(f"📡 Scraping TUNEPS AO: {start_date} à {end_date} - Complete: {complete_mode}")

        thread = threading.Thread(target=scraper.scraper_offres_tuneps, args=(start_date, end_date, complete_mode))
        thread.daemon = True
        thread.start()

        response = jsonify({
            "success": True,
            "message": f"Scraping TUNEPS AO lancé ({'complet' if complete_mode else 'rapide'})"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        logger.error(f"❌ Erreur /api/scrape: {e}")
        logger.exception(e)
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
@app.route('/api/status', methods=['GET'])
def status():
    if scraper.is_processing:
        duration = time.time() - scraper.processing_start_time if scraper.processing_start_time else 0
        return jsonify({
            "processing": True,
            "duration_seconds": round(duration, 2),
            "message": "Scraping en cours..."
        })
    else:
        return jsonify({
            "processing": False,
            "pending_count": len(scraper.offres_cache),
            "message": "Aucun scraping en cours"
        })
@app.route('/api/validate/<path:reference>', methods=['POST'])
def validate_offre(reference):
    logger.info(f"✅ Validation: {reference}")
 
    existing_active = tenders_collection.find_one({"reference": reference, "status": "active"})
    if existing_active:
        return jsonify({"success": False, "message": "Offre déjà validée", "offre_ref": reference})
    for offre in scraper.offres_cache[:]:
        if offre.reference == reference:
            result = scraper.post_tender_to_database(offre)
            if result['success']:
                scraper.offres_cache.remove(offre)
            return jsonify(result)
    pending_doc = pending_tenders_collection.find_one({"reference": reference, "status": "pending"})
    if pending_doc:
        offre = OffreTuneps(**pending_doc)
        result = scraper.post_tender_to_database(offre)
        if result['success']:
            scraper.offres_cache = [o for o in scraper.offres_cache if o.reference != reference]
            pending_tenders_collection.delete_one({"reference": reference})
        return jsonify(result)
    return jsonify({"success": False, "message": "Offre non trouvée", "offre_ref": reference})
@app.route('/api/update/<path:reference>', methods=['POST'])
def update_offre(reference):
    data = request.json
    if scraper.update_offre_in_cache(reference, data):
        return jsonify({"success": True, "message": "Offre mise à jour", "offre_ref": reference})
    return jsonify({"success": False, "message": "Offre non trouvée", "offre_ref": reference})
@app.route('/api/delete/<path:reference>', methods=['DELETE'])
def delete_offre(reference):
    if scraper.delete_pending_offre(reference):
        return jsonify({"success": True, "message": "Offre supprimée", "offre_ref": reference})
    return jsonify({"success": False, "message": "Offre non trouvée", "offre_ref": reference})
@app.route('/api/tenders/delete/<path:reference>', methods=['DELETE'])
def delete_validated_offre(reference):
    if scraper.delete_validated_offre(reference):
        return jsonify({"success": True, "message": "Offre validée supprimée", "offre_ref": reference})
    return jsonify({"success": False, "message": "Offre non trouvée", "offre_ref": reference})
@app.route('/api/tenders', methods=['GET'])
def get_tenders():
    tenders = scraper.get_tenders_from_db()
    return jsonify({"success": True, "tenders": tenders})
@app.route('/api/pending', methods=['GET'])
def get_pending():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        paginated = scraper.get_offres_cache(page=page, limit=limit)
        return jsonify({"success": True, "pending": paginated})
    except Exception as e:
        logger.error(f"Erreur /api/pending: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@app.route('/api/download_pdf/<filename>')
def download_pdf(filename):
    pdf_path = os.path.join(PDF_DIR, filename)
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True)
    return jsonify({"success": False, "message": "PDF non trouvé"}), 404
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(REACT_BUILD_DIR, path)):
        return send_file(os.path.join(REACT_BUILD_DIR, path))
 
    index_path = os.path.join(REACT_BUILD_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
 
    return Response("<h1>TUNEPS OFFRES Scraper - Frontend manquant</h1>", mimetype='text/html')
if __name__ == "__main__":
    # Fix Windows console encoding for emojis
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    print("="*80)
    print("🚀 SCRAPER TUNEPS - APPELS D'OFFRES (/portail/offres)")
    print("="*80)
    print(f"📍 URL cible: {scraper.BASE_URL}")
    print(f"📂 MongoDB: {MONGO_URI}")
    print(f"🔧 API: {API_BASE_URL}")
    print(f"💰 Currency ID: {DEFAULT_CURRENCY_ID} (TND)")
    print(f"📰 Source ID: {DEFAULT_SOURCE_ID} (TUNEPS)")
    print(f"📋 Avis ID: {DEFAULT_AVIS_ID}")
    print(f"🌍 Pays ID: {DEFAULT_PAYS_ID} (Tunisie)")
    print("="*80)
    print("✅ FONCTIONNALITÉS CLÉS:")
    print(" - Extraction LOTS → batches[].title (titre du lot)")
    print(" - Extraction CAUTIONNEMENT → batches[].deposit (caution du lot)")
    print(" - Extraction ID robuste (6 stratégies)")
    print(" - Fallback cautionnement global si absent par lot")
    print(" - Scraping sans limite de pages, arrêt basé sur dates")
    print(" - Traitement parallèle (5 threads)")
    print(" - Mode rapide par défaut (extraction_complete=False)")
    print("="*80)
    app.run(debug=False, port=5005, host='0.0.0.0')