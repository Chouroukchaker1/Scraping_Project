# tuneps.py - VERSION COMPLÈTE CORRIGÉE
import os
import sys
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
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException, NoSuchElementException
import tenacity
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
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

warnings.filterwarnings('ignore')
from dotenv import load_dotenv
load_dotenv()

# ================================================
# CONFIGURATION
# ================================================

# Configuration MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/marmoucha")
DB_NAME = "marmoucha"
COLLECTION_NAME = "tenders_marmoucha"
PENDING_COLLECTION_NAME = "pending_tenders_marmoucha"

# Configuration API AppelOffres
API_BASE_URL = "https://be.appeloffres.net/api"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
TENDER_UPDATE_ENDPOINT = f"{API_BASE_URL}/tenders"
TENDERS_ENDPOINT = f"{API_BASE_URL}/tenders"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"

EMAIL = "maryam.marmouch@tunipages.tn"
API_PASSWORD = "Marmouch2345!@"
DEFAULT_SOURCE_ID = "817"
DEFAULT_PROMOTER_ID = "223472"
DEFAULT_AVIS_ID = "2"
DEFAULT_PAYS_ID = "219"
DEFAULT_CURRENCY_ID = "111"

# Configuration S3
S3_BUCKET = "tender-s3"
S3_REGION = "de"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_ENDPOINT_URL = "https://s3.de.10.cloud.ovh.net"

# Configuration des chemins
POPPLER_PATH = r"C:\poppler\Library\bin"
PDF_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\pdf_tuneps_extraction"
TUNEPS_CAPTURES_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\tunepscaptures"
IMAGES_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\images_tuneps"
OUTPUT_DIR = "output"
TEMPLATES_DIR = "output"
REACT_BUILD_DIR = "react-frontend/build"
EXCEL_DIR = "excel"

# Création sécurisée des dossiers
for directory in [PDF_DIR, TUNEPS_CAPTURES_DIR, IMAGES_DIR, OUTPUT_DIR, TEMPLATES_DIR, REACT_BUILD_DIR, EXCEL_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Utiliser stdout pour éviter encoding errors
        logging.FileHandler('scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Connexion MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
tenders_collection = db[COLLECTION_NAME]
pending_tenders_collection = db[PENDING_COLLECTION_NAME]

try:
    db.command('ping')
    logger.info("MongoDB connecte avec succes")
except PyMongoError as e:
    logger.error(f"Erreur MongoDB: {e}")
    raise

# IDs de régions
REGION_IDS = {
    "Ariana": 1, "Beja": 2, "Ben Arous": 4, "Bizerte": 5,
    "Gabes": 6, "Gafsa": 7, "Jendouba": 8, "Kairouan": 9,
    "Kasserine": 10, "Kebili": 11, "Manouba": 13, "Le Kef": 15,
    "Mahdia": 17, "Medenine": 16, "Monastir": 18, "Nabeul": 19,
    "Sfax": 20, "Sidi Bouzid": 22, "Siliana": 23, "Sousse": 24,
    "Tataouine": 25, "Tozeur": 26, "Tunis": 27, "Zaghouan": 28
}

# ================================================
# CLASSES
# ================================================

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
    currencyId: str = "11"
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
        
        # Chemins
        self.pdf_dir = PDF_DIR
        self.captures_dir = TUNEPS_CAPTURES_DIR
        self.images_dir = IMAGES_DIR
        self.output_dir = OUTPUT_DIR
        self.excel_dir = EXCEL_DIR
        self.skip_s3 = skip_s3
        self.poppler_path = POPPLER_PATH
        
        # Flag de processing
        self.is_processing = False
        self.processing_start_time = None
        
        # Configuration TUNEPS
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
        
        # Configuration scraping
        self.BASE_URL = "https://www.tuneps.tn/portail/consultations"
        self.TIMEOUT = 30
        self.WAIT_TIME = 1
        self.DELAY_BETWEEN_CONSULTATIONS = (1.0, 2.0)
        self.DELAY_BETWEEN_PAGES = (2, 4)
        self.MAX_PAGES = None
        self.MAX_RETRIES = 2
        self.DATE_CUTOFF_DAYS = 90
        
        # Init S3 client
        self.s3_client = None
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    endpoint_url=S3_ENDPOINT_URL
                )
                self.logger.info("Client S3 initialise")
            except Exception as s3_e:
                self.logger.error(f"Erreur init S3: {s3_e}")
        
        # Chargement données
        self.load_pending_offers()
        self.load_validated_refs()
        self._load_pending_set()
        
        if self.skip_s3:
            self.logger.info("Mode LOCAL UNIQUEMENT active")
        else:
            self.logger.info("Mode S3 active")
        
        self._test_poppler()
    
    def _test_poppler(self):
        """Test si Poppler est accessible"""
        try:
            test_pdf = None
            for file in os.listdir(self.pdf_dir):
                if file.endswith('.pdf'):
                    test_pdf = os.path.join(self.pdf_dir, file)
                    break
            
            if test_pdf and os.path.exists(test_pdf):
                file_size = os.path.getsize(test_pdf)
                self.logger.info(f"Test Poppler avec PDF: {test_pdf} (taille: {file_size} octets)")
                
                images = convert_from_path(
                    test_pdf,
                    first_page=1,
                    last_page=1,
                    dpi=300,
                    poppler_path=self.poppler_path
                )
                
                if images:
                    test_png = test_pdf.replace('.pdf', '_test.png')
                    images[0].save(test_png, 'PNG', optimize=True)
                    png_size = os.path.getsize(test_png) if os.path.exists(test_png) else 0
                    self.logger.info(f"Poppler test OK - Conversion reussie")
                    
                    if os.path.exists(test_png):
                        os.remove(test_png)
                else:
                    self.logger.error("Poppler test echoue - Aucune image extraite")
            else:
                self.logger.warning("Pas de PDF test trouve - Test Poppler skippe")
        except Exception as e:
            self.logger.error(f"Poppler non fonctionnel: {e}")
    
    def load_validated_refs(self):
        """Charge les références des offres validées"""
        try:
            validated_docs = list(tenders_collection.find({"status": "active"}).sort("createdAt", -1))
            self.validated_refs = {doc.get("reference", "") for doc in validated_docs if doc.get("reference")}
            self.logger.info(f"{len(self.validated_refs)} references validees chargees")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement validees: {e}")
    
    def _load_pending_set(self):
        """Reconstruit le set des pendings depuis DB"""
        try:
            pending_docs = list(pending_tenders_collection.find({"status": "pending"}).sort("createdAt", -1))
            self.pending_set = set()
            for doc in pending_docs:
                ref = doc.get("reference", "")
                desc_hash = hash(doc.get("description", ""))
                self.pending_set.add((ref, desc_hash))
            self.logger.info(f"{len(self.pending_set)} doublons pendings charges")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement pending set: {e}")
    
    def load_pending_offers(self):
        """Charge les offres en attente depuis MongoDB"""
        try:
            pending_docs = list(pending_tenders_collection.find({"status": "pending"}).sort("createdAt", -1))
            self.offres_cache = []
            for doc in pending_docs:
                clean_doc = {k: v for k, v in doc.items() if k in {f.name for f in fields(OffreTuneps)}}
                offre = OffreTuneps(**clean_doc)
                self.offres_cache.append(offre)
            self.logger.info(f"{len(self.offres_cache)} offres pending chargees depuis DB")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement pending: {e}")
    
    def _init_driver(self):
        """Initialise ou réinitialise le driver Selenium"""
        if self.driver:
            try:
                self.driver.execute_script("return 'alive';")
            except (WebDriverException, AttributeError):
                self.logger.info("Driver session invalid - Reinitializing...")
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
                options.add_argument(f"--user-agent={self.headers['User-Agent']}")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--remote-debugging-port=0")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--ignore-ssl-errors")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Use system ChromeDriver from environment variable or default path
                # Try to load from saved path file first
                saved_path_file = os.path.join(os.path.dirname(__file__), '.chromedriver_path')
                default_path = '/usr/bin/chromedriver'
                if os.path.exists(saved_path_file):
                    with open(saved_path_file, 'r') as f:
                        default_path = f.read().strip()
                chromedriver_path = os.getenv('CHROMEDRIVER_PATH', default_path)
                self.driver = webdriver.Chrome(
                    service=Service(chromedriver_path),
                    options=options
                )
                
                self.driver.set_page_load_timeout(self.TIMEOUT)
                self.driver.set_script_timeout(self.TIMEOUT)
                self.logger.info("Selenium driver initialized/reinitialized")
                
            except WebDriverException as e:
                self.logger.error(f"Failed to initialize driver: {e}")
                self.use_selenium = False
                self.driver = None
    
    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Driver Selenium ferme")
            except Exception:
                pass
    
    def generer_pdf_path(self, filename: str) -> str:
        return os.path.join(self.pdf_dir, filename).replace('\\', '/')
    
    def generer_capture_path(self, filename: str) -> str:
        return os.path.join(self.captures_dir, filename).replace('\\', '/')
    
    def generer_image_path(self, filename: str) -> str:
        return os.path.join(self.images_dir, filename).replace('\\', '/')
    
    def pdf_to_base64(self, pdf_path: str) -> str:
        try:
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                self.logger.info(f"Taille PDF pour base64: {file_size} octets")
                if file_size > 100:
                    with open(pdf_path, 'rb') as pdf_file:
                        return base64.b64encode(pdf_file.read()).decode('utf-8')
                else:
                    self.logger.warning(f"PDF trop petit ({file_size} octets) pour base64")
        except Exception as e:
            self.logger.error(f"Erreur conversion PDF en base64: {e}")
        return ""
    
    def image_to_base64(self, image_path: str) -> str:
        try:
            if os.path.exists(image_path):
                file_size = os.path.getsize(image_path)
                self.logger.info(f"Taille image pour base64: {file_size} octets")
                if file_size > 100:
                    with open(image_path, 'rb') as img_file:
                        return base64.b64encode(img_file.read()).decode('utf-8')
                else:
                    self.logger.warning(f"Image trop petite ({file_size} octets) pour base64")
        except Exception as e:
            self.logger.error(f"Erreur conversion image en base64: {e}")
        return ""
    
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def login_appeloffres(self) -> bool:
        if self.access_token:
            return True
        
        try:
            self.logger.info(f"Tentative de connexion a l'API: {LOGIN_ENDPOINT}")
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
                self.logger.info("Connexion API reussie")
                return True
            
            self.logger.error(f"ERREUR CONNEXION: Status {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"ERREUR CONNEXION: {e}")
            return False
    
    def get_or_create_promoter(self, promoter_name: str) -> str:
        if not promoter_name or promoter_name.strip() == "":
            promoter_name = "Promoteur TUNEPS Inconnu"
        
        clean_name = self.nettoyer_texte(promoter_name)
        if clean_name in self.promoter_cache:
            return self.promoter_cache[clean_name]
        
        if not self.login_appeloffres():
            self.logger.error("Echec connexion pour creation promoteur - utilisation ID par defaut")
            return self.default_promoter_id
        
        payload = {
            "name": promoter_name,
            "description": f"Acheteur public TUNEPS: {promoter_name}",
            "reference": re.sub(r'\W+', '_', promoter_name.upper())[:20],
            "isEnabled": True,
            "companyName": promoter_name,
            "address": {
                "street": "Adresse inconnue",
                "city": "Tunis",
                "country": "Tunisie",
                "postalCode": "1000"
            }
        }
        
        try:
            self.logger.info(f"Creation du promoteur: {promoter_name}")
            response = self.session_appeloffres.post(
                PROMOTER_ENDPOINT,
                json=payload,
                headers=self.appeloffres_headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                promoter_data = response.json()
                promoter_id = str(promoter_data.get("id"))
                self.promoter_cache[clean_name] = promoter_id
                self.logger.info(f"Promoteur cree: {promoter_id}")
                return promoter_id
            else:
                self.logger.error(f"Erreur creation promoteur: Status {response.status_code} - {response.text}")
                return self.default_promoter_id
                
        except Exception as e:
            self.logger.error(f"Erreur promoteur: {e}")
            return self.default_promoter_id
    
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
            
            if dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=8, minute=0)
                self.logger.info(f"Heure forcee a 08:00 pour date sans heure: {dt.isoformat()}")
            
            parsed_iso = dt.isoformat()
            self.logger.info(f"Date parsee: '{date_str}' -> {parsed_iso}")
            return parsed_iso
            
        except Exception as e:
            self.logger.warning(f"Erreur parsing date '{date_str}': {e}")
            return None
    
    def map_offre_to_tender_payload(self, offre) -> dict:
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
                now_dt = datetime.now(timezone.utc)
                exp_dt = (now_dt + timedelta(days=30)).replace(hour=12, minute=0, second=0, microsecond=0)
                expiration_ts = exp_dt.isoformat()
            self.logger.warning(f"Date expiration manquante pour {offre.reference} - Calculee: {expiration_ts}")
        
        batches = []
        
        def clean_deposit(dep_str):
            if not dep_str:
                return "0"
            cleaned = re.sub(r'[^\d\s,.]', '', str(dep_str)).strip()
            return cleaned or "0"
        
        if offre.lots:
            for i, lot in enumerate(offre.lots, 1):
                lot_title = (lot.get("title") or lot.get("objet", "") or 
                           lot.get("description", "") or f"Lot {i}")
                
                if lot.get("description"):
                    lot_title = lot.get("description")
                elif lot.get("objet"):
                    lot_title = lot.get("objet")
                elif lot.get("title"):
                    lot_title = lot.get("title")
                else:
                    lot_title = f"Lot {i}"
                
                lot_deposit = (lot.get("Cautionnement provisoire") or 
                             lot.get("deposit", "") or 
                             offre.cautionnement_provisoire or "0")
                deposit = clean_deposit(lot_deposit)
                
                batches.append({
                    "activitiesIds": [],
                    "title": lot_title,
                    "deposit": deposit
                })
                self.logger.info(f"Lot {i}: Title='{lot_title[:50]}...', Deposit='{deposit}'")
        
        if not batches:
            raw_description = str(offre.description).strip()
            if not raw_description:
                raw_description = f"Appel d'offres TUNEPS - Reference: {offre.reference}"
            
            global_deposit = clean_deposit(offre.cautionnement_provisoire)
            batches = [{
                "activitiesIds": [],
                "title": raw_description,
                "deposit": global_deposit
            }]
            self.logger.info(f"Batch unique: Title='{raw_description[:50]}...', Deposit='{global_deposit}'")
        
        promoter_id = self.get_or_create_promoter(offre.promoter)
        source_id = int(self.default_source_id)
        currency_id = int(DEFAULT_CURRENCY_ID)
        avis_id = int(DEFAULT_AVIS_ID)
        region_id = offre.region_id
        
        raw_description = str(offre.description).strip()
        if not raw_description:
            raw_description = f"Appel d'offres TUNEPS - Reference: {offre.reference}"
        
        title_parts = [raw_description]
        if offre.lots and len(offre.lots) > 1:
            lots_titles = [lot.get("title", lot.get("objet", lot.get("description", ""))) 
                          for lot in offre.lots 
                          if lot.get("title") or lot.get("objet") or lot.get("description")]
            if lots_titles:
                title_parts.append(f"Lots: {', '.join(lots_titles[:3])}")
        
        title = " - ".join(title_parts)
        description = raw_description
        
        addresses = [{"countryId": DEFAULT_PAYS_ID}]
        if region_id:
            addresses[0]["regionId"] = str(region_id)
        
        self.logger.info(f"Country ID utilise: {DEFAULT_PAYS_ID} (Tunisie)")
        
        offer_validity_periode = None
        if offre.offer_validity_duration and offre.offer_validity_duration != 'N/A':
            offer_validity_periode = offre.offer_validity_duration
            self.logger.info(f"Duree de validite extraite pour {offre.reference}: {offer_validity_periode}")
        
        images = []
        if offre.s3_image_url:
            relative_path = re.search(r'/tender-s3-prod/(.+?\.(?:png|pdf))', offre.s3_image_url)
            if relative_path:
                image_path = relative_path.group(1)
                images = [{
                    "url": image_path,
                    "description": "Capture d'ecran ou image du cahier des charges TUNEPS"
                }]
                self.logger.info(f"Image relative extraite pour payload: {image_path}")
            else:
                self.logger.warning(f"URL S3 invalide pour extraction chemin: {offre.s3_image_url}")
        
        if not images:
            images = [{
                "url": "placeholder-tuneps.png",
                "description": "Image placeholder pour appel d'offres TUNEPS"
            }]
        
        type_tender = "national" if "national" in offre.description.lower() or "national" in offre.full_content.lower() else "international"
        
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
            "type": type_tender,
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
        
        self.logger.info(f"Payload complet pour {offre.reference}: {json.dumps(filtered_payload, indent=2, ensure_ascii=False)}")
        self.logger.info(f"Preparation envoi API pour {offre.reference}:")
        self.logger.info(f" Source ID: {source_id} (TUNEPS)")
        self.logger.info(f" Currency ID: {currency_id} (TND)")
        self.logger.info(f" Promoteur ID: {promoter_id}")
        self.logger.info(f" Avis ID: {avis_id} (Avis de consultation)")
        
        if region_id:
            self.logger.info(f" Region ID: {region_id} (dans addresses)")
        
        self.logger.info(f" Title/Description: {title[:50]}... (validee non vide)")
        self.logger.info(f" Type: {type_tender} (detecte: national si mot-cle, sinon international)")
        self.logger.info(f" Dates: pub={publication_ts}, start_bid={start_bidding_ts} (>= pub), exp={expiration_ts}, open={opening_ts}")
        
        if offre.s3_image_url:
            self.logger.info(f" Image S3 (relative): {images[0]['url'] if images else 'N/A'}")
        
        return filtered_payload
    
    @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_exponential(multiplier=2, min=4, max=20))
    def post_tender_to_database(self, offre) -> dict:
        existing = tenders_collection.find_one({"reference": offre.reference})
        if existing:
            self.logger.info(f"Offre {offre.reference} existe deja en base validee")
            return {
                "success": False,
                "message": "Offre deja validee en base",
                "offre_ref": offre.reference
            }
        
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
                    self.logger.info(f"Offre {offre.reference} supprimee de pending DB et set")
                
                self.validated_refs.add(offre.reference)
                self.logger.info(f"Reference {offre.reference} ajoutee a validated_refs")
                self.logger.info(f"Insertion reussie en DB: {offre.reference} - ID Mongo: {result.inserted_id}")
                
                api_success = False
                api_id = None
                api_message = ""
                
                try:
                    if not self.login_appeloffres():
                        self.logger.error(f"Echec connexion API pour {offre.reference}")
                        api_message = "Echec connexion API"
                    else:
                        payload = self.map_offre_to_tender_payload(offre)
                        self.logger.info(f"Envoi vers API: {TENDER_ENDPOINT}")
                        
                        response = self.session_appeloffres.post(
                            TENDER_ENDPOINT,
                            json=payload,
                            headers=self.appeloffres_headers,
                            timeout=30
                        )
                        
                        self.logger.info(f"Reponse API brute pour {offre.reference}: Status={response.status_code}, Text={response.text[:500]}...")
                        
                        if response.status_code in [200, 201]:
                            api_data = response.json()
                            api_id = api_data.get("id")
                            api_success = True
                            api_message = f"Envoi API reussi - ID: {api_id}"
                            self.logger.info(f"ENVOI API REUSSI: {offre.reference} - ID API: {api_id}")
                            
                            tenders_collection.update_one(
                                {"_id": result.inserted_id},
                                {"$set": {"api_id": api_id}}
                            )
                        else:
                            api_message = f"Echec envoi API: Status {response.status_code} - {response.text}"
                            self.logger.error(f"ENVOI API ECHOUE pour {offre.reference}: Status {response.status_code} - {response.text}")
                            api_success = False
                            
                except Exception as api_e:
                    api_message = f"Erreur envoi API: {str(api_e)}"
                    self.logger.error(f"ERREUR ENVOI API pour {offre.reference}: {api_e}")
                
                message = f"Insertion reussie en DB"
                if api_success:
                    message += f" et envoi API (ID: {api_id})"
                else:
                    message += f" mais echec API: {api_message}"
                
                return {
                    "success": True,
                    "message": message,
                    "offre_ref": offre.reference,
                    "mongo_id": str(result.inserted_id),
                    "api_id": api_id,
                    "api_success": api_success,
                    "api_message": api_message
                }
            else:
                raise PyMongoError("Insertion echouee sans ID genere")
                
        except PyMongoError as e:
            self.logger.error(f"Erreur MongoDB: {e}")
            return {
                "success": False,
                "message": f"Erreur MongoDB: {str(e)}",
                "offre_ref": offre.reference
            }
        except Exception as e:
            self.logger.error(f"Erreur insertion DB: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de l'insertion: {str(e)}",
                "offre_ref": offre.reference
            }
    
    def save_to_pending(self, offre):
        try:
            desc_hash = hash(offre.description)

            # Vérifier d'abord dans le cache local
            if offre.reference in self.validated_refs:
                self.logger.warning(f"Doublon detecte pour {offre.reference} - Offre deja validee (cache), skip pending")
                return False

            # Vérification DIRECTE dans MongoDB pour être sûr (important si validation depuis Node.js)
            exists_in_validated = tenders_collection.find_one({"reference": offre.reference})
            if exists_in_validated:
                self.logger.warning(f"Doublon detecte pour {offre.reference} - Offre deja validee (DB check), skip pending")
                # Mettre à jour le cache local
                self.validated_refs.add(offre.reference)
                return False

            if (offre.reference, desc_hash) in self.pending_set:
                self.logger.warning(f"Doublon detecte pour {offre.reference} - Offre deja en pending, skip")
                return False
            
            tender_dict = offre.to_dict()
            tender_dict["status"] = "pending"
            
            result = pending_tenders_collection.insert_one(tender_dict)
            
            if result.inserted_id:
                self.pending_set.add((offre.reference, desc_hash))
                
                if offre.image_filename:
                    file_path = self.generer_image_path(offre.image_filename) if offre.image_filename.endswith('.png') else self.generer_pdf_path(offre.image_filename)
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        self.logger.info(f"Offre sauvegardee en pending DB: {offre.reference} - Image: {offre.image_filename} (taille: {size} octets)")
                    else:
                        self.logger.warning(f"Offre sauvegardee en pending DB: {offre.reference} - Image: {offre.image_filename} (fichier non trouve)")
                else:
                    self.logger.info(f"Offre sauvegardee en pending DB: {offre.reference} - Image: Aucune")
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur save pending: {e}")
            return False
    
    def delete_pending_offre(self, reference: str) -> bool:
        try:
            result = pending_tenders_collection.delete_one({"reference": reference, "status": "pending"})
            
            if result.deleted_count > 0:
                self.offres_cache = [o for o in self.offres_cache if o.reference != reference]
                to_remove = [(r, h) for r, h in self.pending_set if r == reference]
                for tup in to_remove:
                    self.pending_set.discard(tup)
                
                self.logger.info(f"Offre supprimee: {reference} (DB, cache et set)")
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
                self.logger.info(f"Offre validee supprimee: {reference} (DB et set)")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur delete validated: {e}")
            return False
    
    def nettoyer_texte(self, texte: str) -> str:
        if not texte:
            return ""
        
        texte = unicodedata.normalize('NFKD', str(texte))
        texte = ''.join(c for c in texte if not unicodedata.combining(c))
        texte = re.sub(r'{{.*?}}', '', texte)
        texte = re.sub(r'\s+', ' ', texte)
        texte = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', texte)
        
        return texte.strip()
    
    def normaliser_date_api(self, date_text: str) -> str:
        date_text = self.clean_date_str(date_text)
        if not date_text or date_text in ["N/A", "None", "null"]:
            return "N/A"
        
        try:
            date_text = re.sub(r'h', ':', date_text)
            date_text = re.sub(r'\s+', ' ', date_text).strip()
            
            try:
                parsed_date = datetime.strptime(date_text, '%d/%m/%Y %H:%M')
            except ValueError:
                try:
                    parsed_date = datetime.strptime(date_text, '%d/%m/%Y')
                except ValueError:
                    parsed_date = parse(date_text, fuzzy=True, tzinfos={None: tz.gettz('Africa/Tunis')})
            
            return f"{parsed_date.strftime('%d/%m/%Y')} a {parsed_date.strftime('%Hh%M')}"
        except:
            return "N/A"
    
    def get_value_safe(self, driver, label, timeout=10):
        try:
            value_extracted = ""
            strategy_used = ""
            
            # Stratégies spécifiques pour dates
            if "expiration" in label.lower() or "dernier delai reception offres" in label.lower() or "date de limite" in label.lower():
                specific_strategies = [
                    f"//*[normalize-space(text())=\"{label}\"]/following-sibling::*[1]",
                    f"//*[contains(normalize-space(text()), 'Date d\\'expiration')]/following-sibling::*[1]",
                    f"//*[contains(normalize-space(text()), 'Dernier delai reception offres')]/following-sibling::*[1]",
                    "//dt[contains(text(), 'expiration')]/following-sibling::dd[1]",
                    "//div[contains(@class, 'field') and contains(., 'expiration')]/following-sibling::div[1]",
                    f"//*[contains(normalize-space(text()), 'Date de limite')]/following-sibling::*[1]",
                ]
                
                strategy_used = "expiration-specific"
                
                for xpath in specific_strategies:
                    try:
                        element = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        value_extracted = element.text.strip()
                        if value_extracted and value_extracted not in ["N/A", "", "None"]:
                            value_extracted = re.sub(r'\s+', ' ', value_extracted).strip()
                            strategy_used = f"expiration-XPath: {xpath[:50]}..."
                            self.logger.info(f"Date d'expiration extraite: '{value_extracted}' ({strategy_used})")
                            break
                    except:
                        continue
                        
            elif "ouverture des offres" in label.lower() or "ouverture" in label.lower():
                specific_strategies_opening = [
                    f"//*[normalize-space(text())=\"{label}\"]/following-sibling::*[1]",
                    f"//*[contains(normalize-space(text()), 'Date et heure d\\'ouverture')]/following-sibling::*[1]",
                    "//dt[contains(text(), 'ouverture des offres')]/following-sibling::dd[1]",
                    "//div[contains(@class, 'field') and contains(., 'ouverture')]/following-sibling::div[1]",
                    "//th[contains(text(), 'ouverture')]/following-sibling::td[1]",
                ]
                
                for xpath in specific_strategies_opening:
                    try:
                        element = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        value_extracted = element.text.strip()
                        if value_extracted and value_extracted not in ["N/A", "", "None"]:
                            value_extracted = re.sub(r'\s+', ' ', value_extracted).strip()
                            strategy_used = f"opening-XPath: {xpath[:50]}..."
                            self.logger.info(f"Date d'ouverture extraite: '{value_extracted}' ({strategy_used})")
                            break
                    except:
                        continue
                        
            elif "n° reference" in label.lower():
                specific_strategies_ref = [
                    f"//*[normalize-space(text())=\"{label}\"]/following-sibling::*[1]",
                    f"//*[contains(normalize-space(text()), 'N° reference')]/following-sibling::*[1]",
                    "//td[contains(text(), 'N° reference')]/following-sibling::td[1]",
                    "//th[contains(text(), 'N° reference')]/following-sibling::td[1]",
                ]
                
                strategy_used = "reference-specific"
                for xpath in specific_strategies_ref:
                    try:
                        element = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        value_extracted = element.text.strip()
                        if value_extracted and value_extracted not in ["N/A", "", "None"] and re.search(r'\d+/\d{2,4}', value_extracted):
                            value_extracted = re.sub(r'\s+', ' ', value_extracted).strip()
                            strategy_used = f"reference-XPath: {xpath[:50]}..."
                            self.logger.info(f"N° reference extraite: '{value_extracted}' ({strategy_used})")
                            break
                    except:
                        continue
            
            # Stratégies générales pour autres labels
            else:
                strategies = [
                    f"//*[normalize-space(text())='{label}']/following-sibling::*[1]",
                    f"//*[contains(normalize-space(text()), '{label}')]/following-sibling::*[1]",
                    f"//div[contains(text(), '{label}')]/following-sibling::div[1]",
                    f"//label[contains(text(), '{label}')]/following-sibling::*[1]"
                ]
                
                for xpath in strategies:
                    try:
                        element = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        value_extracted = element.text.strip()
                        if value_extracted and value_extracted not in ["N/A", "", "None"]:
                            value_extracted = re.sub(r'\s+', ' ', value_extracted).strip()
                            strategy_used = f"general-XPath: {xpath[:50]}..."
                            self.logger.info(f"Valeur extraite pour '{label}': {value_extracted} ({strategy_used})")
                            break
                    except:
                        continue
            
            if value_extracted:
                self.logger.info(f"Extraction finale pour '{label}': '{value_extracted}' via {strategy_used}")
                return value_extracted
            
            self.logger.warning(f"Aucune valeur trouvee pour '{label}' apres toutes les strategies")
            return ""
            
        except Exception as e:
            self.logger.error(f"Erreur get_value_safe pour '{label}': {e}")
            return ""
    
    def extract_table_safe(self, driver, table_identifier):
        try:
            table_xpaths = [
                f"//table[.//th[contains(text(), '{table_identifier}')]]",
                f"//table[.//td[contains(text(), '{table_identifier}')]]",
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
            
            headers = []
            try:
                header_elements = table.find_elements(By.CSS_SELECTOR, "th, mat-header-cell")
                headers = [h.text.strip() for h in header_elements if h.text.strip()]
            except:
                pass
            
            if not headers:
                return ""
            
            data = []
            try:
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr, mat-row")
                for row in rows:
                    try:
                        cells = row.find_elements(By.CSS_SELECTOR, "td, mat-cell")
                        row_data = [cell.text.strip() for cell in cells]
                        if any(row_data):
                            if any('lot' in str.lower(cell) for cell in row_data):
                                lot_dict = {}
                                for i, header in enumerate(headers):
                                    if i < len(row_data):
                                        if 'objet' in header.lower() or 'title' in header.lower():
                                            lot_dict['title'] = row_data[i]
                                            lot_dict['description'] = row_data[i]
                                            lot_dict['objet'] = row_data[i]
                                        else:
                                            lot_dict[header] = row_data[i]
                                
                                if lot_dict.get('title') or lot_dict.get('description') or lot_dict.get('objet'):
                                    data.append(lot_dict)
                            else:
                                while len(row_data) < len(headers):
                                    row_data.append("")
                                data.append(dict(zip(headers[:len(row_data)], row_data)))
                    except:
                        continue
            except:
                pass
            
            return json.dumps(data, ensure_ascii=False) if data else ""
            
        except Exception as e:
            self.logger.error(f"Erreur extraction table: {e}")
            return ""
    
    def _capture_screenshot(self, url: str, reference: str) -> str:
        if not self.driver:
            self.logger.warning(f"Driver non disponible pour capture {reference}")
            return ""
        
        try:
            now = datetime.now()
            timestamp = now.strftime("%H%M%S")
            hash_ref = abs(hash(reference)) % 1000000
            filename = f"{now.strftime('%d/%m/')}{timestamp}-{hash_ref}.png"
            local_path = self.generer_capture_path(filename)
            
            self.driver.get(url)
            time.sleep(2)
            self.driver.save_screenshot(local_path)
            
            file_size = os.path.getsize(local_path)
            self.logger.info(f"Capture sauvegardee localement: {local_path} (taille: {file_size} octets)")
            
            if file_size < 100:
                self.logger.error(f"Capture corrompue (taille: {file_size} octets) - Suppression")
                os.remove(local_path)
                return ""
            
            return local_path
            
        except Exception as cap_e:
            self.logger.error(f"Erreur capture pour {reference}: {cap_e}")
            return ""
    
    def _upload_image_via_api(self, local_image_path: str, reference: str) -> str:
        if not os.path.exists(local_image_path):
            self.logger.warning(f"Fichier image non trouve pour upload: {local_image_path}")
            return ""
        
        file_size = os.path.getsize(local_image_path)
        if file_size <= 100:
            self.logger.warning(f"Fichier image trop petit pour upload ({file_size} octets): {local_image_path}")
            return ""
        
        try:
            if not self.login_appeloffres():
                self.logger.error("Echec auth pour upload image API")
                return ""
            
            self.appeloffres_headers["Authorization"] = f"Bearer {self.access_token}"
            
            with open(local_image_path, 'rb') as f:
                files = {'file': (os.path.basename(local_image_path), f, 'image/png')}
                data = {'description': f'Image pour tender {reference} - TUNEPS'}
                
                response = self.session_appeloffres.post(
                    FILES_ENDPOINT,
                    files=files,
                    data=data,
                    headers={k: v for k, v in self.appeloffres_headers.items() if k != 'Content-Type'},
                    timeout=30
                )
            
            if response.status_code in [200, 201]:
                api_data = response.json()
                s3_url = api_data.get("url") or api_data.get("s3Url")
                self.logger.info(f"Upload API reussi pour {reference}: {s3_url}")
                
                relative_match = re.search(r'/tender-s3-prod/(.+?\.(?:png|pdf)\??)', s3_url)
                if relative_match:
                    relative_path = relative_match.group(1)
                    self.logger.info(f"Chemin relatif extrait: {relative_path}")
                
                return s3_url
            else:
                self.logger.error(f"Echec upload API: Status {response.status_code} - {response.text}")
                return self._upload_to_s3_fallback(local_image_path, reference)
                
        except Exception as upload_e:
            self.logger.error(f"Erreur upload API pour {reference}: {upload_e}")
            return self._upload_to_s3_fallback(local_image_path, reference)
    
    def _upload_to_s3_fallback(self, local_path: str, reference: str) -> str:
        if not self.s3_client:
            return ""
        
        try:
            now = datetime.now()
            timestamp = now.strftime("%H%M%S")
            hash_ref = abs(hash(reference)) % 1000000
            ext = 'png' if local_path.endswith('.png') else 'pdf'
            filename = f"{now.strftime('%d/%m/')}{timestamp}-{hash_ref}.{ext}"
            s3_key = f"tender-s3/{filename}"
            
            self.s3_client.upload_file(local_path, S3_BUCKET, s3_key)
            s3_url = f"https://s3.de.10.cloud.ovh.net/{s3_key}"
            self.logger.info(f"Fallback S3 upload: {s3_url}")
            
            relative_path = f"{s3_key.split('/', 1)[1]}"
            return s3_url
            
        except Exception as fb_e:
            self.logger.error(f"Fallback S3 echoue: {fb_e}")
            return ""
    
    def pdf_to_png(self, pdf_path: str, reference: str) -> Tuple[str, str]:
        png_path = ""
        png_filename = ""
        
        try:
            if not os.path.exists(pdf_path):
                self.logger.warning(f"PDF non trouve pour conversion: {pdf_path} - Fallback au PDF direct")
                return "", ""
            
            pdf_size = os.path.getsize(pdf_path)
            self.logger.info(f"Taille PDF pour conversion PNG: {pdf_size} octets")
            
            if pdf_size <= 100:
                self.logger.error(f"PDF trop petit pour conversion: {pdf_size} octets - Fallback au PDF direct")
                return "", ""
            
            poppler_path = self.poppler_path if os.path.exists(self.poppler_path) else None
            
            if poppler_path:
                self.logger.info(f"Utilisation Poppler force: {poppler_path}")
                images = convert_from_path(
                    pdf_path,
                    first_page=1,
                    last_page=1,
                    dpi=300,
                    poppler_path=poppler_path
                )
                
                if images:
                    png_filename = f"{reference}.png"
                    png_path = self.generer_image_path(png_filename)
                    images[0].save(png_path, 'PNG')
                    
                    if os.path.exists(png_path):
                        png_size = os.path.getsize(png_path)
                        if png_size > 100:
                            self.logger.info(f"PDF converti en PNG: {png_path} (taille: {png_size} octets)")
                            return png_path, png_filename
                        else:
                            self.logger.error(f"PNG corrompu (taille: {png_size} octets): {png_path}")
                            if os.path.exists(png_path):
                                os.remove(png_path)
                    else:
                        self.logger.error(f"PNG non cree: {png_path}")
                else:
                    self.logger.error(f"Aucune image extraite du PDF: {pdf_path}")
                    
        except Exception as e:
            self.logger.error(f"Erreur conversion PDF en PNG: {e} - Fallback au PDF direct")
        
        if os.path.exists(pdf_path):
            pdf_filename = os.path.basename(pdf_path)
            pdf_size = os.path.getsize(pdf_path)
            self.logger.info(f"Fallback PDF direct comme image: {pdf_filename} (taille: {pdf_size} octets)")
            return pdf_path, pdf_filename
        
        return "", ""
    
    def generate_synthetic_image(self, reference: str, data: dict, contenu: dict) -> Tuple[str, str]:
        try:
            synthetic_pdf_path = self.generer_pdf_path(f"{reference}_synthetic.pdf")
            
            if self.generate_pdf_reportlab(reference, data, contenu, synthetic_pdf_path):
                self.logger.info(f"PDF synthetique genere: {synthetic_pdf_path}")
                return self.pdf_to_png(synthetic_pdf_path, reference)
            else:
                self.logger.error(f"Echec generation PDF synthetique pour {reference}")
                return "", ""
                
        except Exception as e:
            self.logger.error(f"Erreur generation image synthetique: {e}")
            return "", ""
    
    def generate_pdf_reportlab(self, reference, data, contenu, pdf_path):
        try:
            pdf_path = pdf_path.replace('\\', '/')
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=1.5*cm,
                bottomMargin=1.5*cm
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=25,
                textColor=HexColor('#1a365d'),
                alignment=TA_CENTER
            )
            
            header_style = ParagraphStyle(
                'Header',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=HexColor('#2d3748')
            )
            
            body_style = ParagraphStyle(
                'Body',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=8,
                textColor=black,
                alignment=TA_JUSTIFY
            )
            
            story.append(Paragraph(f"CAHIER DES CHARGES - {reference}", title_style))
            story.append(Spacer(1, 0.5*cm))
            
            story.append(Paragraph("Informations principales", header_style))
            
            info_data = [
                [Paragraph('REFERENCE', body_style), Paragraph(f"{reference}", body_style)],
                [Paragraph('ACHETEUR PUBLIC', body_style), Paragraph(f"{data.get('Acheteur public', 'N/A')}", body_style)],
                [Paragraph('DATE PUBLICATION', body_style), Paragraph(f"{contenu.get('publication_date_full', 'N/A')}", body_style)],
                [Paragraph('DATE DEBUT SOUMISSIONS', body_style), Paragraph(f"{contenu.get('start_bidding_date_full', 'N/A')}", body_style)],
                [Paragraph('DATE OUVERTURE OFFRES', body_style), Paragraph(f"{contenu.get('ouverture_offres', 'N/A')}", body_style)],
                [Paragraph('DATE LIMITE', body_style), Paragraph(f"{contenu.get('expiration_date_full', 'N/A')}", body_style)]
            ]
            
            info_table = Table(info_data, colWidths=[5*cm, 10*cm])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (0, -1), white),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 10)
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 0.8*cm))
            
            story.append(Paragraph("Description", header_style))
            desc_text = contenu.get('description_complete', '')[:2000]
            story.append(Paragraph(desc_text, body_style))
            story.append(Spacer(1, 0.5*cm))
            
            doc.build(story)
            
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                self.logger.info(f"PDF synthetique genere: {pdf_path} (taille: {file_size} octets)")
                if file_size > 100:
                    return True
                else:
                    self.logger.error(f"PDF synthetique corrompu (taille: {file_size} octets): {pdf_path}")
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    return False
            else:
                self.logger.error(f"PDF synthetique non cree: {pdf_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur PDF synthetique: {e}")
            return False
    
    def extraire_contenu_detaille(self, url: str, data: dict, reference: str) -> dict:
        contenu = {
            'description_complete': self.nettoyer_texte(data.get('Objet Consultation', '')),
            'expiration_date': data.get('Dernier Delai', 'N/A'),
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
                    local_capture_path = self._capture_screenshot(url, reference)
                    if local_capture_path:
                        s3_uploaded_url = self._upload_image_via_api(local_capture_path, reference)
                        if s3_uploaded_url:
                            contenu['s3_image_url'] = s3_uploaded_url
                            contenu['image_path'] = local_capture_path
                            contenu['image_filename'] = os.path.basename(local_capture_path)
                            self.logger.info(f"Capture uploadée S3 pour {reference}: {s3_uploaded_url}")
                        else:
                            self.logger.warning(f"Upload capture echoue pour {reference} - Image locale seulement")
                    else:
                        self.logger.warning(f"Capture echouee pour {reference} - Pas d'image")
                    
                    time.sleep(2)
                    
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//*[contains(text(), 'N° reference') or contains(text(), 'Objet consultation')]")
                        )
                    )
                    
                    time.sleep(1)
                    
                    # Extraction N° référence
                    n_ref = self.get_value_safe(self.driver, "N° reference", timeout=10)
                    num_cons = data.get("N° consultation", "")
                    
                    if n_ref and re.search(r'\d+/\d{2,4}', n_ref.strip()):
                        full_reference = f"{n_ref} - {num_cons}" if num_cons else n_ref
                    else:
                        if not n_ref or not re.search(r'\d+/\d{2,4}', n_ref.strip()):
                            self.logger.warning(f"N° reference non extraite avec get_value_safe pour {reference} - Tentative fallback JS")
                            try:
                                page_text = self.driver.execute_script("return document.body.innerText;")
                                ref_pattern = r"N° reference\s*:?\s*([0-9]{1,3}/[0-9]{2,4})"
                                match_ref = re.search(ref_pattern, page_text, re.IGNORECASE)
                                if match_ref:
                                    n_ref = match_ref.group(1).strip()
                                    self.logger.info(f"N° reference extraite via fallback JS: '{n_ref}'")
                                else:
                                    self.logger.warning("Fallback JS pour N° reference echoue - Utilisation de N° consultation seule")
                                    n_ref = ""
                            except Exception as ref_js_e:
                                self.logger.error(f"Erreur fallback JS pour N° reference: {ref_js_e}")
                        
                        if n_ref and re.search(r'\d+/\d{2,4}', n_ref.strip()):
                            full_reference = f"{n_ref} - {num_cons}" if num_cons else n_ref
                        else:
                            full_reference = num_cons
                    
                    data["Reference"] = full_reference
                    self.logger.info(f"Reference corrigee pour {reference}: {full_reference} (N° reference: '{n_ref}', N° consultation: '{num_cons}')")
                    
                    # Extraction des dates
                    contenu['publication_date_full'] = self.get_value_safe(self.driver, "Date et heure publication", timeout=10)
                    contenu['start_bidding_date_full'] = self.get_value_safe(self.driver, "Date et heure du commencement d'envoi des offres", timeout=10)
                    contenu['expiration_date_full'] = self.get_value_safe(self.driver, "Dernier delai reception offres", timeout=10)
                    
                    # Si expiration vide, tentative fallback JS
                    if not contenu['expiration_date_full'] or contenu['expiration_date_full'] == 'N/A':
                        self.logger.warning(f"Date d'expiration non trouvee avec label standard pour {full_reference} - Tentative fallback JS")
                        try:
                            page_text = self.driver.execute_script("return document.body.innerText;")
                            exp_pattern = r"Dernier delai (?:de )?reception (?:des )?offres\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4}\s*(?:a|a)?\s*[0-9]{1,2}[h:][0-9]{2})"
                            exp_match = re.search(exp_pattern, page_text, re.IGNORECASE)
                            if exp_match:
                                contenu['expiration_date_full'] = exp_match.group(1).strip()
                                self.logger.info(f"Date d'expiration extraite via fallback JS: '{contenu['expiration_date_full']}'")
                        except Exception as fallback_e:
                            self.logger.error(f"Erreur fallback JS pour expiration: {fallback_e}")
                    
                    # Extraction date d'ouverture
                    self.logger.info(f"Extraction de la date d'ouverture pour {full_reference}...")
                    opening_labels = [
                        "Date et heure d'ouverture des offres",
                        "Date et heure d'ouverture",
                        "Date d'ouverture des offres",
                        "Ouverture des offres",
                        "Date ouverture"
                    ]
                    
                    opening_date = None
                    for label_variant in opening_labels:
                        opening_date = self.get_value_safe(self.driver, label_variant, timeout=10)
                        if opening_date and opening_date != "N/A" and opening_date.strip():
                            self.logger.info(f"Date d'ouverture trouvee avec label '{label_variant}': {opening_date}")
                            break
                    
                    contenu['ouverture_offres'] = opening_date if opening_date else 'N/A'
                    
                    self.logger.info(f"Dates extraites pour {full_reference}:")
                    self.logger.info(f" - Publication: {contenu['publication_date_full']}")
                    self.logger.info(f" - Debut soumissions: {contenu['start_bidding_date_full']}")
                    self.logger.info(f" - Expiration: {contenu['expiration_date_full']}")
                    self.logger.info(f" - OUVERTURE PLIS: {contenu['ouverture_offres']}")
                    
                    # Reste de l'extraction
                    contenu['offer_validity_duration'] = self.get_value_safe(self.driver, "Duree de validite de l'offre", timeout=10)
                    
                    global_caution = self.get_value_safe(self.driver, "Cautionnement provisoire", timeout=5)
                    if global_caution:
                        contenu['cautionnement_provisoire'] = global_caution
                    else:
                        contenu['cautionnement_provisoire'] = '0'
                    
                    lots_json = self.extract_table_safe(self.driver, "Lot")
                    if lots_json:
                        lots = json.loads(lots_json)
                        contenu['lots'] = lots
                        
                        if lots and not global_caution:
                            first_lot_caution = lots[0].get("Cautionnement provisoire", "0")
                            contenu['cautionnement_provisoire'] = first_lot_caution
                    
                    docs_json = self.extract_table_safe(self.driver, "Document")
                    if docs_json:
                        contenu['pieces_jointes'] = json.loads(docs_json)
                    
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    main_content = soup.select_one('main, article, div.consultation-details')
                    texte_integral = main_content.get_text(separator=' ', strip=True) if main_content else soup.get_text(separator=' ', strip=True)
                    contenu['texte_integral'] = texte_integral
                    
                    pdf_links = soup.find_all('a', href=re.compile(r'.pdf$', re.I))
                    if pdf_links:
                        pdf_url = urljoin(url, pdf_links[0]['href'])
                        contenu['cahier_charge_url'] = pdf_url
                        
                        if not self.skip_s3:
                            pdf_path, pdf_filename = self.telecharger_pdf_tuneps(pdf_url, full_reference)
                            if pdf_path:
                                contenu['pdf_path'] = pdf_path
                                contenu['pdf_filename'] = pdf_filename
                                
                                image_path, image_filename = self.pdf_to_png(pdf_path, full_reference)
                                if image_path:
                                    contenu['image_path'] = image_path
                                    contenu['image_filename'] = image_filename
                                    self.logger.info(f"PDF converti en PNG pour {full_reference}: {image_filename}")
                                else:
                                    contenu['image_path'] = pdf_path
                                    contenu['image_filename'] = pdf_filename
                    
                    # Gestion images robuste
                    if not contenu.get('image_filename') and not contenu.get('s3_image_url'):
                        local_paths = [
                            self.generer_image_path(f"{full_reference}.png"),
                            self.generer_image_path(f"{full_reference}_synthetic.png"),
                            self.generer_pdf_path(f"{full_reference}.pdf"),
                            self.generer_pdf_path(f"{full_reference}_synthetic.pdf")
                        ]
                        
                        local_found = False
                        for path in local_paths:
                            if os.path.exists(path):
                                file_size = os.path.getsize(path)
                                if file_size > 100:
                                    self.logger.info(f"Fichier LOCAL trouve pour {full_reference}: {path} (taille: {file_size} octets)")
                                    
                                    if path.endswith('.pdf'):
                                        img_p, img_f = self.pdf_to_png(path, full_reference)
                                        if img_p:
                                            contenu['image_path'] = img_p
                                            contenu['image_filename'] = img_f
                                        else:
                                            contenu['image_path'] = path
                                            contenu['image_filename'] = os.path.basename(path)
                                    else:
                                        contenu['image_path'] = path
                                        contenu['image_filename'] = os.path.basename(path)
                                    
                                    local_found = True
                                    s3_uploaded_url = self._upload_image_via_api(path, full_reference)
                                    if s3_uploaded_url:
                                        contenu['s3_image_url'] = s3_uploaded_url
                                    break
                        
                        if not local_found:
                            self.logger.info(f"Pas de fichier local - Generation synthetique pour {full_reference}")
                            synth_image_path, synth_image_filename = self.generate_synthetic_image(full_reference, data, contenu)
                            if synth_image_path and synth_image_filename:
                                contenu['image_path'] = synth_image_path
                                contenu['image_filename'] = synth_image_filename
                                self.logger.info(f"Image synthetique generee pour {full_reference}: {synth_image_filename}")
                                
                                s3_uploaded_url = self._upload_image_via_api(synth_image_path, full_reference)
                                if s3_uploaded_url:
                                    contenu['s3_image_url'] = s3_uploaded_url
                    
                    break  # Sortir de la boucle de retry si succès
                    
                except Exception as e:
                    self.logger.error(f"Erreur extraction detail (tentative {attempt+1}): {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(1)
                        continue
                    
        except Exception as e:
            self.logger.error(f"ERREUR EXTRACTION CONTENU: {e}")
            
            # Fallback ultime: Générer image synthétique
            self.logger.info(f"Fallback ultime synthetique pour {reference}")
            synth_image_path, synth_image_filename = self.generate_synthetic_image(reference, data, contenu)
            if synth_image_path and synth_image_filename:
                contenu['image_path'] = synth_image_path
                contenu['image_filename'] = synth_image_filename
                img_size = os.path.getsize(synth_image_path) if os.path.exists(synth_image_path) else 0
                self.logger.info(f"Fallback ultime reussi pour {reference}: {synth_image_filename} (taille: {img_size} octets)")
                
                s3_uploaded_url = self._upload_image_via_api(synth_image_path, reference)
                if s3_uploaded_url:
                    contenu['s3_image_url'] = s3_uploaded_url
        
        # Log final
        self.logger.info(f"Resume dates pour {data.get('Reference', reference)}:")
        self.logger.info(f" startBiddingDate ← '{contenu['start_bidding_date_full']}'")
        self.logger.info(f" expirationDate ← '{contenu['expiration_date_full']}'")
        self.logger.info(f" openingBidsDate ← '{contenu['ouverture_offres']}'")
        
        if contenu['s3_image_url']:
            self.logger.info(f" Capture/Image S3: {contenu['s3_image_url']}")
        
        img_path = contenu.get('image_path', '')
        if img_path:
            img_size = os.path.getsize(img_path) if os.path.exists(img_path) else 0
            self.logger.info(f"Image finale pour {data.get('Reference', reference)}: {contenu['image_filename']} (taille: {img_size} octets)")
        
        return contenu
    
    def process_single_detail(self, data):
        """Traite une consultation individuelle (utilisée en thread)"""
        reference = data.get("Reference", data.get("N° consultation", ""))
        url = data.get("URL_Detail", "")
        i = data.get("index", 0)
        
        self.logger.info(f"Thread: Traitement consultation {i}: {data.get('N° consultation', 'N/A')}")
        
        if not url:
            return None
        
        extraction_complete = getattr(self, 'extraction_complete_mode', True)
        contenu = self.extraire_contenu_detaille(url, data, reference) if extraction_complete else {}
        
        pdf_base64 = self.pdf_to_base64(contenu.get('pdf_path', '')) if contenu.get('pdf_path') else ""
        image_base64 = self.image_to_base64(contenu.get('image_path', '')) if contenu.get('image_path') else ""
        
        region_id = None
        clean_promoter = self.nettoyer_texte(data.get("Acheteur public", ""))
        clean_promoter_words = set(clean_promoter.split())
        
        for region, rid in REGION_IDS.items():
            clean_region = self.nettoyer_texte(region)
            clean_region_words = set(clean_region.split())
            if clean_region in clean_promoter or any(word in clean_promoter_words for word in clean_region_words):
                region_id = rid
                break
        
        if "ksar said" in clean_promoter or "ksar said" in clean_promoter:
            region_id = 27
        
        if not region_id:
            self.logger.warning(f"Region non mappee pour promoteur: {data.get('Acheteur public', '')}")
        
        raw_desc = self.nettoyer_texte(data.get("Objet Consultation", ""))
        if not raw_desc.strip():
            raw_desc = f"Appel d'offres TUNEPS - Reference: {reference}"
        
        type_detected = "national" if "national" in raw_desc.lower() else "international"
        
        start_bidding_full = contenu.get('start_bidding_date_full', contenu.get('publication_date_full', 'N/A')) if extraction_complete else data.get("Date Publication", "N/A")
        
        offre = OffreTuneps(
            reference=reference,
            description=raw_desc,
            full_content=contenu.get('texte_integral', '') if extraction_complete else raw_desc,
            promoter=self.nettoyer_texte(data.get("Acheteur public", "")),
            publicationDate=contenu.get('publication_date_full', data.get("Date Publication", "N/A")) if extraction_complete else data.get("Date Publication", "N/A"),
            startBiddingDate=start_bidding_full,
            expirationDate=contenu.get('expiration_date_full', data.get("Dernier Delai", "N/A")) if extraction_complete else data.get("Dernier Delai", "N/A"),
            ouverture_offres=contenu.get('ouverture_offres', "N/A") if extraction_complete else "N/A",
            offer_validity_duration=contenu.get('offer_validity_duration', 'N/A') if extraction_complete else 'N/A',
            cautionnement_provisoire=contenu.get('cautionnement_provisoire', '0') if extraction_complete else '0',
            pieces_jointes=contenu.get('pieces_jointes', []) if extraction_complete else [],
            cahier_charge=contenu.get('pdf_path', '') if extraction_complete else '',
            cahier_charge_pdf=contenu.get('pdf_path', '') if extraction_complete else '',
            cahier_charge_pdf_filename=contenu.get('pdf_filename', '') if extraction_complete else '',
            cahier_charge_pdf_base64=pdf_base64 if extraction_complete else "",
            cahier_charge_url=contenu.get('cahier_charge_url', '') if extraction_complete else '',
            image_path=contenu.get('image_path', '') if extraction_complete else '',
            image_filename=contenu.get('image_filename', '') if extraction_complete else '',
            image_base64=image_base64 if extraction_complete else "",
            s3_image_url=contenu.get('s3_image_url', '') if extraction_complete else '',
            lots=contenu.get('lots', []) if extraction_complete else [],
            mots_cles_detectes=[],
            sourceId=self.default_source_id,
            promoterId=None,
            fundingSource=None,
            procedure=contenu.get('procedure', 'N/A') if extraction_complete else 'N/A',
            type_marche=contenu.get('type_marche', 'Public') if extraction_complete else 'Public',
            url_source=url,
            region_id=region_id,
            type=type_detected
        )
        
        if self.save_to_pending(offre):
            self.offres_cache.append(offre)
            self.logger.info(f"Offre {reference} ajoutee (pending) en thread avec image S3: {offre.s3_image_url}")
            return offre
        else:
            self.logger.warning(f"Offre {reference} skippee (doublon avec pending ou validee)")
            return None
    
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def _get_soup_from_url(self, url: str):
        soup = None
        pdf_path = ""
        pdf_filename = ""
        image_path = ""
        image_filename = ""
        
        try:
            if self.use_selenium and self.driver:
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                pdf_links = soup.find_all('a', href=re.compile(r'.pdf$', re.I))
                if pdf_links:
                    pdf_url = urljoin(url, pdf_links[0]['href'])
                    if pdf_url and not self.skip_s3:
                        pdf_path, pdf_filename = self.telecharger_pdf_tuneps(pdf_url, url.split('/')[-1])
                        if pdf_path:
                            image_path, image_filename = self.pdf_to_png(pdf_path, url.split('/')[-1])
                            if image_path:
                                s3_uploaded_url = self._upload_image_via_api(image_path, url.split('/')[-1])
            else:
                response = self.session.get(url, timeout=30, allow_redirects=True)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    pdf_links = soup.find_all('a', href=re.compile(r'.pdf$', re.I))
                    if pdf_links and not self.skip_s3:
                        pdf_url = urljoin(url, pdf_links[0]['href'])
                        pdf_path, pdf_filename = self.telecharger_pdf_tuneps(pdf_url, url.split('/')[-1])
                        if pdf_path:
                            image_path, image_filename = self.pdf_to_png(pdf_path, url.split('/')[-1])
                            if image_path:
                                s3_uploaded_url = self._upload_image_via_api(image_path, url.split('/')[-1])
                                
        except Exception as e:
            self.logger.error(f"ERREUR SOUP: {e}")
        
        return soup, pdf_path, pdf_filename, image_path, image_filename
    
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def telecharger_pdf_tuneps(self, pdf_url: str, reference: str) -> Tuple[str, str]:
        try:
            if not pdf_url or not reference:
                self.logger.warning(f"URL PDF ou reference manquant pour {reference}")
                return "", ""
            
            filename = f"{reference}.pdf"
            pdf_path = self.generer_pdf_path(filename)
            
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                if file_size > 100:
                    self.logger.info(f"PDF deja present localement: {pdf_path} (taille: {file_size} octets)")
                    return pdf_path, filename
                else:
                    self.logger.warning(f"PDF local corrompu (taille: {file_size} octets) - Suppression et redownload")
                    os.remove(pdf_path)
            
            if self.skip_s3:
                self.logger.info(f"S3 skippe - Pas de telechargement pour {reference}")
                return "", ""
            
            response = self.session.get(pdf_url, timeout=30, stream=True)
            
            if response.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if os.path.exists(pdf_path):
                    file_size = os.path.getsize(pdf_path)
                    if file_size > 100:
                        self.logger.info(f"PDF telecharge: {pdf_path} (taille: {file_size} octets)")
                        return pdf_path, filename
                    else:
                        self.logger.error(f"PDF corrompu telecharge (taille: {file_size} octets): {pdf_path}")
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
            else:
                self.logger.error(f"Erreur telechargement PDF: Status {response.status_code}")
                return "", ""
                
        except Exception as e:
            self.logger.error(f"Erreur telechargement PDF: {e}")
            return "", ""
    
    def extraire_lots_depuis_url(self, url: str, soup=None):
        lots = []
        lots_text = ""
        
        if soup is None:
            soup = self._get_soup_from_url(url)[0]
        
        if not soup:
            return lots, "Aucun lot detecte"
        
        try:
            lot_divs = soup.find_all('div', class_=re.compile(r'lot-item'))
            for div in lot_divs:
                lot_title = div.get_text(strip=True)
                if lot_title and len(lot_title) > 10:
                    lots.append({"title": lot_title, "description": lot_title})
                    lots_text += f" {lot_title}"
            
            if lots:
                return lots, f"{len(lots)} lots detectes"
            
            return lots, "Aucun lot detecte"
            
        except Exception as e:
            self.logger.error(f"Erreur extraction lots: {e}")
            return lots, "Erreur extraction lots"
    
    def is_between_dates(self, date_str, start_date_str, end_date_str):
        """Vérifie si la date de publication est entre start_date et end_date"""
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
                return start_date <= pub_date
            elif end_date:
                return pub_date <= end_date
            else:
                return True
                
        except Exception as e:
            self.logger.warning(f"Erreur filtrage date '{date_str}': {e}")
            return False
    
    def should_stop_scraping(self, rows_data, page_num):
        """Condition d'arrêt basée sur dates anciennes"""
        if not rows_data:
            return False
        
        cutoff_date = datetime.now().date() - timedelta(days=self.DATE_CUTOFF_DAYS)
        all_old = True
        
        for r in rows_data:
            pub_date_str = r.get("Date Publication", "")
            exp_date_str = r.get("Dernier Delai", "")
            
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
            self.logger.info(f"Arret scraping a page {page_num}: Toutes dates (pub/exp) > {self.DATE_CUTOFF_DAYS} jours anciennes ({cutoff_date})")
            return True
        
        return False
    
    def extract_all_rows_data(self):
        consultations = []
        driver = self.driver
        
        try:
            time.sleep(1)
            
            script = """
            var style = document.createElement('style');
            style.innerHTML = '.mat-column-spShopMasterId { display: table-cell !important; visibility: visible !important; }';
            document.head.appendChild(style);
            """
            driver.execute_script(script)
            time.sleep(1)
            
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, mat-row")
            
            if not rows:
                return consultations
            
            self.logger.info(f"{len(rows)} lignes detectees")
            
            for idx, row in enumerate(rows):
                try:
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
                    
                    id1 = ""
                    try:
                        id1_cell = row.find_element(By.CSS_SELECTOR, ".mat-column-spShopMasterId")
                        id1 = id1_cell.text.strip() or driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", id1_cell).strip()
                    except:
                        pass
                    
                    if not id1:
                        for text in all_texts + js_texts:
                            if text and text.isdigit() and len(text) == 6:
                                id1 = text
                                break
                    
                    num_consultation = all_texts[0] if len(all_texts) > 0 else ""
                    
                    basic_data = {
                        "N° consultation": num_consultation,
                        "Acheteur public": all_texts[1] if len(all_texts) > 1 else "",
                        "Date Publication": all_texts[2] if len(all_texts) > 2 else "",
                        "Objet Consultation": all_texts[3] if len(all_texts) > 3 else "",
                        "Dernier Delai": all_texts[4] if len(all_texts) > 4 else "",
                        "_id1": id1
                    }
                    
                    consultations.append(basic_data)
                    
                except StaleElementReferenceException:
                    continue
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
            time.sleep(1)
            driver.execute_script("arguments[0].click();", next_button)
            
            WebDriverWait(driver, self.TIMEOUT).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr, mat-row"))
            )
            
            time.sleep(self.WAIT_TIME)
            return True
            
        except (TimeoutException, NoSuchElementException):
            return False
        except Exception as e:
            self.logger.error(f"Erreur click next: {str(e)[:50]}")
            return False
    
    _scrape_lock = threading.Lock()
    
    def scraper_offres_tuneps(self, start_date: str = None, end_date: str = None, extraction_complete: bool = False) -> List:
        if self.is_processing:
            self.logger.warning("Scraping deja en cours - Skip nouveau scraping")
            return []
        
        self.is_processing = True
        self.processing_start_time = time.time()
        self.extraction_complete_mode = extraction_complete
        
        self.logger.info(f"Flag processing SET a True - Debut scraping ({datetime.now().strftime('%d/%m/%Y %H:%M')}) - Mode complete: {extraction_complete}")
        
        with self._scrape_lock:
            self._init_driver()
            if not self.use_selenium or not self.driver:
                self.logger.error("Selenium unavailable - Falling back to requests mode")
                self.is_processing = False
                return []
            
            all_consultations = []
            all_refs = set()
            empty_pages = 0
            
            self.logger.info(f"Debut scraping TUNEPS ({datetime.now().strftime('%d/%m/%Y %H:%M')}) - Dates: {start_date} a {end_date} - Complete: {extraction_complete}")
            
            try:
                max_retries_get = 3
                for retry_get in range(max_retries_get):
                    try:
                        self.driver.get(self.BASE_URL)
                        time.sleep(self.WAIT_TIME)
                        self.logger.info(f"Page d'accueil chargee (tentative {retry_get+1})")
                        break
                    except TimeoutException as te:
                        self.logger.warning(f"Timeout sur driver.get(BASE_URL) (tentative {retry_get+1}/{max_retries_get}): {te}")
                        if retry_get < max_retries_get - 1:
                            self.logger.info("Reinitialisation driver et retry...")
                            self._init_driver()
                            time.sleep(5)
                        else:
                            raise te
                    except WebDriverException as wde:
                        self.logger.error(f"Erreur WebDriver sur get(BASE_URL) (tentative {retry_get+1}): {wde}")
                        if retry_get < max_retries_get - 1:
                            self._init_driver()
                            time.sleep(5)
                        else:
                            raise wde
                
                page = 1
                while True:
                    self.logger.info(f"Traitement page {page}...")
                    
                    try:
                        WebDriverWait(self.driver, self.TIMEOUT).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr, mat-row"))
                        )
                    except TimeoutException:
                        self.logger.warning("Timeout de chargement page")
                        break
                    
                    rows_data = self.extract_all_rows_data()
                    self.logger.info(f"{len(rows_data)} lignes extraites sur page {page}")
                    
                    rows_data = [r for r in rows_data if self.is_between_dates(r.get("Date Publication", ""), start_date, end_date)]
                    
                    if not rows_data:
                        empty_pages += 1
                        self.logger.info(f"Aucune consultation dans la plage sur cette page ({empty_pages}/3)")
                        if empty_pages >= 3:
                            self.logger.info("Arret automatique : aucune donnee dans la plage trouvee.")
                            break
                    else:
                        empty_pages = 0
                    
                    if self.should_stop_scraping(rows_data, page):
                        break
                    
                    for r in rows_data:
                        id1 = r.get("_id1", "")
                        num_cons = r.get("N° consultation", "")
                        
                        if id1 and num_cons:
                            r["URL_Detail"] = f"https://www.tuneps.tn/portail/consultations/consultationdetails/{id1}/{num_cons}"
                        else:
                            r["URL_Detail"] = ""
                            self.logger.warning(f"ID1 ou N° consultation manquant pour ligne: {r}")
                        
                        r["Source"] = "tuneps"
                        r["Pays"] = "tunisie"
                        
                        key = r["N° consultation"]
                        if key not in all_refs:
                            all_consultations.append(r)
                            all_refs.add(key)
                    
                    self.logger.info(f"{len(rows_data)} consultations dans la plage trouvees sur page {page}")
                    
                    if not self.click_next_page():
                        self.logger.info("Fin de pagination atteinte (pas de bouton next)")
                        break
                    
                    page += 1
                    time.sleep(random.uniform(*self.DELAY_BETWEEN_PAGES))
                
                self.logger.info(f"Extraction liste terminee : {len(all_consultations)} consultations trouvees dans la plage")
                
                if not all_consultations:
                    self.logger.info("Aucun appel d'offres trouve dans la plage.")
                    self.is_processing = False
                    return []
                
                offres = []
                
                self.logger.info(f"Lancement {len(all_consultations)} threads pour details (max_workers=5)")
                
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
                    
                    self.logger.info(f"Export Excel reussi : {excel_path} ({len(offres)} lignes)")
                else:
                    self.logger.warning("Aucune offre a exporter vers Excel")
                
                self.logger.info(f"Scraping termine: {len(offres)} offres traitees")
                return offres
                
            finally:
                processing_duration = time.time() - self.processing_start_time if self.processing_start_time else 0
                self.is_processing = False
                self.processing_start_time = None
                self.logger.info(f"Flag processing SET a False - Scraping termine en {processing_duration:.2f}s")
                
                if self.driver:
                    try:
                        self.driver.quit()
                        self.logger.info("Driver Selenium ferme apres scrape")
                    except Exception:
                        pass
                    self.driver = None
                
                self.logger.info(f"Termine a {datetime.now().strftime('%H:%M:%S')}")
    
    def get_offres_cache(self, page: int = 1, limit: int = 10):
        if self.is_processing:
            duration = time.time() - self.processing_start_time if self.processing_start_time else 0
            return {
                "processing": True,
                "message": f"Scraping en cours depuis {duration:.2f}s... Rafraichissez dans 10-20s.",
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
                    "region_id": offre.region_id,
                    "type": offre.type
                }
                for offre in paginated_offres
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
                self.logger.info(f"Offre {reference} mise a jour")
                return True
        
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
            self.logger.error(f"Erreur recuperation DB: {e}")
            return []

# ================================================
# FLASK APP
# ================================================

app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path='/static', template_folder=REACT_BUILD_DIR)
CORS(app, origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://localhost:5000", "*"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True)

scraper = TUNEPSScraper(use_selenium=True, skip_s3=True)

def run_automatic_scrape():
    try:
        tunisia_tz = pytz.timezone('Africa/Tunis')
        logger.info(f"Lancement extraction automatique TUNEPS pour aujourd'hui (mode rapide)")
        scraper.scraper_offres_tuneps(extraction_complete=False)
        logger.info(f"Extraction automatique terminee a {datetime.now(tunisia_tz).strftime('%H:%M:%S')} (Tunisie)")
    except Exception as e:
        logger.error(f"Scheduler scrape failed: {e}")

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
logger.info("Scheduler configure: Extraction automatique quotidienne a 7h30 (Tunisie) - Mode rapide")

# ================================================
# ROUTES API
# ================================================

@app.route('/api/test', methods=['GET'])
def test_api():
    logger.info("Route /api/test appelee")
    return jsonify({
        "message": "Backend OK",
        "pending_count": len(scraper.offres_cache),
        "mongo_uri": MONGO_URI,
        "processing": scraper.is_processing
    })

@app.route('/api/scrape', methods=['POST'])
def scrape():
    logger.info("Route /api/scrape appelee - Lancement en background")
    
    try:
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        complete_mode = data.get('extraction_complete', False)
        
        logger.info(f"Scraping lance pour dates:{start_date} a {end_date} - Complete: {complete_mode}")
        
        thread = threading.Thread(
            target=scraper.scraper_offres_tuneps,
            args=(start_date, end_date, complete_mode)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": f"Scraping lance en arriere-plan (mode {'complet' if complete_mode else 'rapide'}). Verifiez /api/status."
        })
        
    except Exception as e:
        logger.error(f"Erreur /api/scrape: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    logger.info("Route /api/status appelee")
    
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

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_offre(reference):
    logger.info(f"Route /api/validate appelee pour {reference}")
    
    existing_active = tenders_collection.find_one({"reference": reference, "status": "active"})
    if existing_active:
        return jsonify({
            "success": False,
            "message": "Offre deja validee en base",
            "offre_ref": reference
        })
    
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
    
    return jsonify({
        "success": False,
        "message": "Offre non trouvee",
        "offre_ref": reference
    })

@app.route('/api/update/<reference>', methods=['POST'])
def update_offre(reference):
    logger.info(f"Route /api/update appelee pour {reference}")
    
    data = request.json
    if scraper.update_offre_in_cache(reference, data):
        return jsonify({
            "success": True,
            "message": "Offre mise a jour",
            "offre_ref": reference
        })
    
    return jsonify({
        "success": False,
        "message": "Offre non trouvee",
        "offre_ref": reference
    })

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete_offre(reference):
    logger.info(f"Route /api/delete appelee pour {reference}")
    
    if scraper.delete_pending_offre(reference):
        return jsonify({
            "success": True,
            "message": "Offre supprimee",
            "offre_ref": reference
        })
    
    return jsonify({
        "success": False,
        "message": "Offre non trouvee",
        "offre_ref": reference
    })

@app.route('/api/tenders/delete/<reference>', methods=['DELETE'])
def delete_validated_offre(reference):
    logger.info(f"Route /api/tenders/delete appelee pour {reference}")
    
    if scraper.delete_validated_offre(reference):
        return jsonify({
            "success": True,
            "message": "Offre validee supprimee",
            "offre_ref": reference
        })
    
    return jsonify({
        "success": False,
        "message": "Offre validee non trouvee",
        "offre_ref": reference
    })

@app.route('/api/tenders', methods=['GET'])
def get_tenders():
    logger.info("Route /api/tenders appelee")
    tenders = scraper.get_tenders_from_db()
    return jsonify({"success": True, "tenders": tenders})

@app.route('/api/pending', methods=['GET'])
def get_pending():
    logger.info(f"Route /api/pending appelee avec args: {request.args}")
    
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        paginated = scraper.get_offres_cache(page=page, limit=limit)
        num_offres = len(paginated.get('offres', []))
        
        logger.info(f"Reponse /api/pending: {num_offres} offres retournees (processing: {paginated.get('processing', False)})")
        
        return jsonify({"success": True, "pending": paginated})
        
    except ValueError as ve:
        logger.error(f"Erreur params /api/pending: {ve}")
        return jsonify({"success": False, "error": "Params invalides (page/limit doivent être des entiers)"}), 400
    except Exception as e:
        logger.error(f"Erreur /api/pending: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download_pdf/<filename>')
def download_pdf(filename):
    logger.info(f"Route /api/download_pdf appelee pour {filename}")
    
    pdf_path = os.path.join(PDF_DIR, filename)
    if os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path)
        if file_size > 100:
            logger.info(f"Telechargement PDF demande: {filename} (taille: {file_size} octets)")
            return send_file(pdf_path, as_attachment=True)
        else:
            return jsonify({"success": False, "message": f"PDF corrompu (taille: {file_size} octets)"}), 404
    
    return jsonify({"success": False, "message": "PDF non trouve localement"}), 404

@app.route('/api/download_image/<filename>')
def download_image(filename):
    logger.info(f"Route /api/download_image appelee pour {filename}")
    
    image_path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(image_path):
        file_size = os.path.getsize(image_path)
        if file_size > 100:
            return send_file(image_path, as_attachment=True)
        else:
            return jsonify({"success": False, "message": f"Image corrompue (taille: {file_size} octets)"}), 404
    
    pdf_path = os.path.join(PDF_DIR, filename)
    if os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path)
        if file_size > 100:
            return send_file(pdf_path, as_attachment=True)
        else:
            return jsonify({"success": False, "message": f"PDF fallback corrompu (taille: {file_size} octets)"}), 404
    
    return jsonify({"success": False, "message": "Image/PDF non trouve localement"}), 404

@app.route('/api/download_excel/<filename>')
def download_excel(filename):
    logger.info(f"Route /api/download_excel appelee pour {filename}")
    
    excel_path = os.path.join(EXCEL_DIR, filename)
    if os.path.exists(excel_path):
        file_size = os.path.getsize(excel_path)
        if file_size > 100:
            logger.info(f"Telechargement Excel demande: {filename} (taille: {file_size} octets)")
            return send_file(excel_path, as_attachment=True)
        else:
            return jsonify({"success": False, "message": f"Excel corrompu (taille: {file_size} octets)"}), 404
    
    return jsonify({"success": False, "message": "Excel non trouve localement"}), 404

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(REACT_BUILD_DIR, path)):
        return send_file(os.path.join(REACT_BUILD_DIR, path))
    
    index_path = os.path.join(REACT_BUILD_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    
    fallback_html = """
    <html>
    <body>
    <h1>Frontend non trouve — Page de controle du scraper TUNEPS</h1>
    <p>Le repertoire react-frontend/build est introuvable.</p>
    </body>
    </html>
    """
    return Response(fallback_html, mimetype='text/html')

@app.errorhandler(404)
def not_found(error):
    logger.error(f"404 pour path: {request.path}")
    return jsonify({"error": "Route non trouvee"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 pour path: {request.path} | Erreur: {error}")
    return jsonify({"error": "Erreur interne serveur"}), 500

# ================================================
# CLI
# ================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='TUNEPS Scraper CLI')
    parser.add_argument('--scrape', action='store_true', help='Launch scraping')
    parser.add_argument('--status', action='store_true', help='Check scraping status')
    parser.add_argument('--pending', action='store_true', help='Get pending offers')
    parser.add_argument('--validate', type=str, help='Validate an offer by reference')
    parser.add_argument('--delete', type=str, help='Delete an offer by reference')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--complete', action='store_true', help='Use complete extraction mode')
    parser.add_argument('--page', type=int, default=1, help='Page number for pending')
    parser.add_argument('--limit', type=int, default=10, help='Limit for pending')
    
    args = parser.parse_args()
    
    scraper = TUNEPSScraper(use_selenium=True, skip_s3=True)
    
    if args.scrape:
        print("Starting TUNEPS scraping...")
        offres = scraper.scraper_offres_tuneps(
            start_date=args.start_date,
            end_date=args.end_date,
            extraction_complete=args.complete
        )
        print(f"Scraping completed: {len(offres)} offers found")
        print(json.dumps({"count": len(offres)}, indent=2))
        
    elif args.status:
        status_data = {
            "processing": scraper.is_processing,
            "pending_count": len(scraper.offres_cache),
            "processing_duration": time.time() - scraper.processing_start_time if scraper.processing_start_time else 0
        }
        print(json.dumps(status_data, indent=2))
        
    elif args.pending:
        pending_data = scraper.get_offres_cache(page=args.page, limit=args.limit)
        print(json.dumps(pending_data, indent=2))
        
    elif args.validate and args.validate != "":
        for offre in scraper.offres_cache:
            if offre.reference == args.validate:
                result = scraper.post_tender_to_database(offre)
                print(json.dumps(result, indent=2))
                break
        else:
            print(json.dumps({
                "success": False,
                "message": f"Offer {args.validate} not found in cache"
            }, indent=2))
            
    elif args.delete and args.delete != "":
        success = scraper.delete_pending_offre(args.delete)
        print(json.dumps({
            "success": success,
            "message": f"Deleted {args.delete}",
            "reference": args.delete
        }, indent=2))
        
    else:
        print("Starting Flask server on port 5001...")
        app.run(debug=False, port=5001, host='0.0.0.0')

if __name__ == "__main__":
    main()