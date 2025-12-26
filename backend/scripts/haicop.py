"""
Extracteur de données des marchés publics tunisiens - Version FINALE avec IMAGE FIXE
Navigation forcée sur toutes les pages avec détection empirique
"""

import sys
import os
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import requests
import pandas as pd
from dateutil.parser import parse
from dateutil import tz
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import tenacity
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import base64
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import warnings
import traceback
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

warnings.filterwarnings('ignore')
load_dotenv()

# Configuration MongoDB pour HAICOP
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/appel_offre_haicop_tunisie-bd")
DB_NAME = os.getenv("DB_NAME", "haicop-tunisie")
COLLECTION_NAME = "tenders_tunisie_haicop-aprév"
PENDING_COLLECTION_NAME = "pending_tunisie-haicop"

# Configuration API pour HAICOP
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"  # ✅ NOUVEAU: Endpoint pour upload image
EMAIL = os.getenv("API_EMAIL", "ines.mtiri@tunipages.tn")
PASSWORD = os.getenv("API_PASSWORD", "InesMTIRI567@!")
DEFAULT_SOURCE_ID = "279"
TUNISIE_SOURCE_ID = 279
DEFAULT_PROMOTER_ID = "223472"
DEFAULT_AVIS_ID = "13"
DEFAULT_PAYS_ID = "219"
TUNISIE_PAYS_ID = 219

# ✅ NOUVEAU: Configuration image fixe
FIXED_IMAGE_SOURCE_PATH = r"C:\Users\lenovo\Downloads\Capture d'écran 2025-11-26 tunipages.png"

# Dossiers
IMAGES_DIR = "images"
OUTPUT_DIR = "output"
TEMPLATES_DIR = "templates"
REACT_BUILD_DIR = "react-frontend/build"
TUNISIE_PDF_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\pdf_tunisie_extraction"

for directory in [IMAGES_DIR, OUTPUT_DIR, TEMPLATES_DIR, REACT_BUILD_DIR, TUNISIE_PDF_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_haicop_tunisie.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Connexion MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
tenders_collection = db[COLLECTION_NAME]
pending_tenders_collection = db[PENDING_COLLECTION_NAME]

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
    source: str = "MarchesPublicsTN"
    promoter: str = ""
    pieces_jointes: List[str] = field(default_factory=list)
    cahier_charge: str = ""
    cahier_charge_pdf: str = ""
    cahier_charge_pdf_filename: str = ""
    cahier_charge_pdf_base64: str = ""
    image_filename: str = ""
    image_base64: str = ""
    s3_image_url: str = ""  # ✅ NOUVEAU: URL S3 de l'image
    lots: List[Dict] = field(default_factory=list)
    mots_cles_detectes: List[str] = field(default_factory=list)
    avis: str = "appel d'offre"
    secteur_activite: str = ""
    secteur_activite_id: Optional[int] = None
    activities_ids: List[int] = field(default_factory=list)
    procedure: str = "N/A"
    type_marche: str = "Public"
    url_source: str = ""
    validationDate: Optional[str] = None
    
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
class OffreTunisie(OffreBase):
    secteur_activite: str = "marches_publics"

class TunisieScraper:
    def __init__(self):
        self.base_url = "https://www.marchespublics.gov.tn"
        self.url = f"{self.base_url}/fr/projets-annuels"
        self.session = requests.Session()
        self.driver = None
        self.tunisie_pdf_dir = TUNISIE_PDF_DIR
        self.images_dir = IMAGES_DIR
        self.logger = logging.getLogger(__name__)
        self.validated_offres_set = set()
        self.pending_cache = []
        self.offres_cache = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.session.headers.update(self.headers)
        self.source_id = TUNISIE_SOURCE_ID
        self.pays_id = TUNISIE_PAYS_ID
        self.avis_id = DEFAULT_AVIS_ID
        self.avis_type = "Projet Annuel"
        self.type = "national"
        self.nature = "public"
        
        if not os.path.exists(self.tunisie_pdf_dir):
            os.makedirs(self.tunisie_pdf_dir, exist_ok=True)
        
        self.setup_driver()
        self.load_existing_offres()
        self.api_session = requests.Session()
        self.api_session.headers.update(self.headers)
        self.api_token = None
        
        # ✅ NOUVEAU: Setup image fixe
        self.fixed_image_s3_path = self._setup_fixed_image_via_api()
        if self.fixed_image_s3_path:
            self.logger.info(f"✅ Image fixe configurée: {self.fixed_image_s3_path}")
        else:
            self.logger.warning("⚠️ Aucune image fixe configurée")
    
    def _setup_fixed_image_via_api(self) -> str:
        """
        ✅ NOUVEAU: Upload l'image fixe via /api/files/tender (comme TUNEPS)
        Retourne le chemin S3 de l'image uploadée
        """
        source_path = FIXED_IMAGE_SOURCE_PATH

        if not os.path.exists(source_path):
            self.logger.warning(f"⚠️ Image source non trouvée: {source_path}")
            return ""

        # Login d'abord
        if not self.login_to_api():
            self.logger.error("❌ Échec connexion API pour upload image")
            return ""

        try:
            with open(source_path, 'rb') as f:
                files = {'file': (os.path.basename(source_path), f, 'image/png')}
                data = {'tender': '100'}  # ID tender fictif

                response = self.api_session.post(
                    FILES_ENDPOINT,
                    files=files,
                    data=data,
                    headers={'Authorization': f"Bearer {self.api_token}"},
                    timeout=60
                )

            if response.status_code in [200, 201]:
                resp_json = response.json()
                url = resp_json.get('url', '')
                
                if url:
                    # Extraire le chemin S3 depuis l'URL
                    parsed = urlparse(url)
                    s3_path = parsed.path.lstrip('/')
                    # Enlever le préfixe bucket si présent
                    s3_path = re.sub(r'^tender-s3-prod/', '', s3_path)
                    self.logger.info(f"✅ Image fixe uploadée via API: {s3_path}")
                    return s3_path
                else:
                    self.logger.error(f"❌ Réponse upload sans URL: {resp_json}")
            else:
                self.logger.error(f"❌ Erreur upload image (status {response.status_code}): {response.text}")

        except Exception as e:
            self.logger.error(f"❌ Erreur upload image fixe: {e}\n{traceback.format_exc()}")

        return ""
    
    def setup_driver(self):
        """Configure le driver Chrome"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=' + self.headers["User-Agent"])
        
        try:
            # Use system ChromeDriver from environment variable or default path
            chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(
                service=Service(chromedriver_path),
                options=chrome_options
            )
            self.logger.info("✅ Driver Selenium initialisé")
        except WebDriverException as e:
            self.logger.error(f"❌ Erreur Selenium: {e}")
            self.driver = None
    
    def load_existing_offres(self):
        """Charge les offres existantes"""
        try:
            validated_docs = list(tenders_collection.find(
                {"source": "MarchesPublicsTN", "status": "active"}
            ).sort("createdAt", -1))
            
            for doc in validated_docs:
                doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
                ref = doc_without_id.get("reference", "")
                desc_hash = hash(doc_without_id.get("description", ""))
                self.validated_offres_set.add((ref, desc_hash))
            
            pending_docs = list(pending_tenders_collection.find(
                {"source": "MarchesPublicsTN", "status": "pending"}
            ).sort("createdAt", -1))
            
            for doc in pending_docs:
                doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
                offre = OffreTunisie(**doc_without_id)
                self.pending_cache.append(offre)
                self.offres_cache.append(offre)
            
            self.logger.info(f"✅ {len(pending_docs)} pending + {len(validated_docs)} validées chargées")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement: {e}")
    
    def parse_date_tunisie(self, date_str):
        """Parse les dates tunisiennes au format DD-MM-YYYY HH:MM:SS"""
        if not date_str or date_str.strip() == "":
            return None
        
        try:
            date_only = date_str.split()[0] if ' ' in date_str else date_str
            dt = datetime.strptime(date_only, "%d-%m-%Y")
            return dt
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur parsing date '{date_str}': {e}")
            return None
    
    def should_extract_by_date(self, publication_date_str, filter_date):
        """Vérifie si une offre doit être extraite selon le filtre de date"""
        if filter_date == "ALL":
            return True
        
        pub_date = self.parse_date_tunisie(publication_date_str)
        filter_dt = self.parse_date_tunisie(filter_date)
        
        if pub_date is None:
            self.logger.warning(f"⚠️ Date de publication invalide: {publication_date_str}")
            return False
        
        if filter_dt is None:
            self.logger.warning(f"⚠️ Date de filtre invalide: {filter_date}")
            return True
        
        return pub_date.date() >= filter_dt.date()
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3), 
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10)
    )
    def extraire_marches_publics(self, date_filtre=None, max_pages=None):
        """
        Extrait les données des projets annuels tunisiens
        STRATÉGIE: Navigation forcée jusqu'à trouver 3 pages vides consécutives
        """
        if date_filtre is None:
            date_filtre = "ALL"
        
        if max_pages is None:
            max_pages = 100
        
        self.logger.info(f"🔍 Extraction HAICOP/Tunisie: Date >= {date_filtre}, Max pages {max_pages}")
        
        all_data = []
        
        try:
            if not self.driver:
                self.logger.error("❌ Driver non initialisé")
                return pd.DataFrame()
            
            wait = WebDriverWait(self.driver, 20)
            
            page_num = 1
            consecutive_empty_pages = 0
            max_consecutive_empty = 3
            
            while page_num <= max_pages:
                try:
                    page_url = f"{self.url}?page={page_num}"
                    self.logger.info(f"🔄 Chargement page {page_num}/{max_pages}: {page_url}")
                    self.driver.get(page_url)
                    time.sleep(4)
                    
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    try:
                        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                        self.logger.info(f"✅ Table détectée page {page_num}")
                    except TimeoutException:
                        self.logger.warning(f"⚠️ Timeout table page {page_num}")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= max_consecutive_empty:
                            self.logger.info(f"🛑 Stop après {max_consecutive_empty} pages vides consécutives")
                            break
                        page_num += 1
                        continue
                    
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    
                    if not rows or len(rows) == 0:
                        self.logger.info(f"ℹ️ Aucune ligne sur page {page_num}")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= max_consecutive_empty:
                            self.logger.info(f"🛑 Stop après {max_consecutive_empty} pages vides consécutives")
                            break
                        page_num += 1
                        continue
                    
                    consecutive_empty_pages = 0
                    page_data_count = 0
                    
                    for row in rows:
                        try:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            
                            if len(cols) < 4:
                                continue
                            
                            id_cell = cols[0]
                            try:
                                id_link = id_cell.find_element(By.TAG_NAME, "a")
                                award_id = id_link.text.strip()
                                award_url = id_link.get_attribute('href')
                            except NoSuchElementException:
                                award_id = id_cell.text.strip()
                                award_url = ""
                            
                            acheteur_public = cols[1].text.strip()
                            objet = cols[2].text.strip()
                            date_pub = cols[3].text.strip()
                            
                            if not self.should_extract_by_date(date_pub, date_filtre):
                                self.logger.info(f"⏭️ Skip offre {award_id} - Date {date_pub} < filtre {date_filtre}")
                                continue
                            
                            date_pub_only = date_pub.split()[0] if ' ' in date_pub else date_pub
                            try:
                                date_pub_obj = datetime.strptime(date_pub_only, "%d-%m-%Y")
                                date_limite = date_pub_obj + timedelta(days=5)
                                date_limite_str = date_limite.strftime("%d-%m-%Y")
                            except:
                                date_limite_str = ""
                            
                            all_data.append({
                                'ID': award_id,
                                'Lien': award_url,
                                'Acheteur Public': acheteur_public,
                                'Objet': objet,
                                'Objet Lot/Article': objet,
                                'Catégorie du résultat': "",
                                'Date de publication': date_pub,
                                'source_id': self.source_id,
                                'pays_id': self.pays_id,
                                'pays_nom': 'Tunisie',
                                'avis_id': self.avis_id,
                                'avis_type': self.avis_type,
                                'type': self.type,
                                'nature': self.nature,
                                'date_limite': date_limite_str
                            })
                            page_data_count += 1
                            
                        except Exception as e:
                            self.logger.warning(f"⚠️ Erreur extraction row page {page_num}: {e}")
                            continue
                    
                    self.logger.info(
                        f"✅ Page {page_num}: {page_data_count} projets extraits "
                        f"(total cumulé: {len(all_data)})"
                    )
                    
                    page_num += 1
                    
                except Exception as page_e:
                    self.logger.error(f"❌ Erreur page {page_num}: {page_e}")
                    page_num += 1
                    continue
            
            df = pd.DataFrame(all_data)
            self.logger.info(
                f"✅ Extraction terminée: {len(df)} projets extraits sur {page_num-1} pages "
                f"(filtre date: {date_filtre})"
            )
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Erreur extraction: {e}")
            traceback.print_exc()
            return pd.DataFrame()
    
    def generer_pdf_path_tunisie(self, filename: str) -> str:
        return os.path.join(self.tunisie_pdf_dir, filename).replace('\\', '/')
    
    def pdf_to_base64(self, pdf_path: str) -> str:
        try:
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100:
                with open(pdf_path, 'rb') as pdf_file:
                    return base64.b64encode(pdf_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erreur base64 PDF: {e}")
        return ""
    
    def save_to_pending_tunisie(self, data_row):
        """Sauvegarde en pending pour HAICOP"""
        try:
            reference = data_row.get('ID', '')
            description = data_row.get('Objet', '')
            desc_hash = hash(description)
            
            if (reference, desc_hash) in self.validated_offres_set:
                self.logger.warning(f"⚠️ Doublon validé: {reference}")
                return False
            
            existing_pending = pending_tenders_collection.find_one({"reference": reference})
            
            if existing_pending:
                existing_desc = existing_pending.get('description', '')
                if existing_desc == description:
                    self.logger.info(f"ℹ️ Déjà en pending (skip): {reference}")
                    return False
            
            now = datetime.now().isoformat()

            # Génération PDF (optionnelle, continue si échec)
            image_filename = f"{reference}_synthetic.pdf"
            try:
                pdf_path = self.generer_pdf_path_tunisie(image_filename)
                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                story = [
                    Paragraph(f"Projet Annuel Tunisie - Ref: {reference}", getSampleStyleSheet()['Title']),
                    Paragraph(f"Objet: {description}", getSampleStyleSheet()['Normal']),
                    Paragraph(f"Acheteur: {data_row.get('Acheteur Public', '')}", getSampleStyleSheet()['Normal']),
                    Paragraph(f"Date Pub: {data_row.get('Date de publication', '')}", getSampleStyleSheet()['Normal']),
                    Paragraph("Contenu synthétique pour test HAICOP.", getSampleStyleSheet()['Normal'])
                ]
                doc.build(story)
                image_filename = os.path.basename(pdf_path)
            except Exception as e:
                self.logger.warning(f"⚠️ PDF non créé pour {reference}: {str(e)}")
                # Continue sans PDF
            full_content = (
                f"Acheteur: {data_row.get('Acheteur Public', '')}<br/>"
                f"Date Pub: {data_row.get('Date de publication', '')}<br/>"
                f"Date Limite: {data_row.get('date_limite', '')}"
            )
            
            # ✅ CORRECTION: Utiliser la date actuelle comme date de publication au lieu de la date du site
            update_fields = {
                "updatedAt": now,
                "extractionDate": now,
                "description": description,
                "full_content": full_content,
                "promoter": data_row.get('Acheteur Public', ''),
                "publicationDate": datetime.now().strftime("%d-%m-%Y"),  # ✅ Date de lancement = date de publication
                "expirationDate": data_row.get('date_limite', ''),
                "url_source": data_row.get('Lien', ''),
                "cahier_charge_pdf_filename": image_filename,
                "image_filename": image_filename,
                "s3_image_url": self.fixed_image_s3_path,  # ✅ NOUVEAU: Image fixe
                "lots": [{
                    "title": data_row.get('Objet Lot/Article', ''),
                    "description": data_row.get('Objet', '')
                }],
                "activities_ids": [461],
                "procedure": "Projet Annuel",
                "type_marche": "Public",
            }
            
            if existing_pending:
                result = pending_tenders_collection.update_one(
                    {"reference": reference},
                    {"$set": update_fields}
                )
                if result.modified_count > 0:
                    self.logger.info(f"✅ Offre MAJ en pending: {reference}")
                    return True
                else:
                    self.logger.info(f"ℹ️ Offre inchangée: {reference}")
                    return False
            else:
                # ✅ CORRECTION: Utiliser la date actuelle comme date de publication au lieu de la date du site
                offre = OffreTunisie(
                    reference=reference,
                    description=description,
                    full_content=full_content,
                    promoter=data_row.get('Acheteur Public', ''),
                    publicationDate=datetime.now().strftime("%d-%m-%Y"),  # ✅ Date de lancement = date de publication
                    expirationDate=data_row.get('date_limite', ''),
                    url_source=data_row.get('Lien', ''),
                    sourceId=self.source_id,
                    promoterId=None,
                    fundingSource=None,
                    secteur_activite_id=None,
                    procedure="Projet Annuel",
                    type_marche="Public",
                    cahier_charge_pdf_filename=image_filename,
                    image_filename=image_filename,
                    s3_image_url=self.fixed_image_s3_path,  # ✅ NOUVEAU: Image fixe
                    lots=[{
                        "title": data_row.get('Objet Lot/Article', ''), 
                        "description": data_row.get('Objet', '')
                    }],
                    activities_ids=[461]
                )
                
                tender_dict = offre.to_dict()
                tender_dict["status"] = "pending"
                
                result = pending_tenders_collection.insert_one(tender_dict)
                if result.inserted_id:
                    self.pending_cache.append(offre)
                    self.offres_cache.append(offre)
                    self.logger.info(f"✅ Offre ajoutée en pending: {reference}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur save pending: {e}")
            traceback.print_exc()
            return False
    
    def scraper_tunisie_and_send(self, date_filtre, max_pages=None):
        """Scraper + Sauvegarde pending"""
        df = self.extraire_marches_publics(date_filtre, max_pages)
        
        saved_count = 0
        for _, row in df.iterrows():
            if self.save_to_pending_tunisie(row):
                saved_count += 1
        
        self.logger.info(
            f"✅ {saved_count}/{len(df)} offres ajoutées/mises à jour en pending"
        )
        
        return {
            "success": True, 
            "offres": {
                "total": len(df), 
                "saved": saved_count,
                "filtered_by_date": date_filtre
            }
        }
    
    def login_to_api(self):
        """Login à l'API HAICOP"""
        try:
            login_data = {"email": EMAIL, "password": PASSWORD}
            self.logger.info(f"🔐 Login API HAICOP: {EMAIL[:3]}****")
            
            response = self.api_session.post(LOGIN_ENDPOINT, json=login_data)
            self.logger.info(f"📡 Réponse login: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.api_token = data.get('accessToken')
                
                if self.api_token:
                    self.api_session.headers.update({
                        'Authorization': f'Bearer {self.api_token}'
                    })
                    self.logger.info("✅ Login API réussi")
                    return True
                else:
                    self.logger.error("❌ Pas de 'accessToken' dans la réponse")
                    return False
            else:
                self.logger.error(f"❌ Erreur login: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erreur login API: {e}")
            return False
    
    def ensure_authenticated(self):
        """Assure l'authentification"""
        if not self.api_token:
            return self.login_to_api()
        return True
    
    def search_promoter(self, company_name: str) -> Optional[int]:
        """Recherche un promoteur existant"""
        if not self.ensure_authenticated():
            return None
        
        try:
            list_url = f"{PROMOTER_ENDPOINT}?page=1&itemsPerPage=50"
            response = self.api_session.get(list_url)
            
            if response.status_code == 200:
                data = response.json()
                promoters = data.get('data', []) or data.get('promoters', [])
                
                for promoter in promoters:
                    if promoter.get('companyName', '').strip().lower() == company_name.strip().lower():
                        promoter_id = promoter.get('id')
                        self.logger.info(f"✅ Promoteur trouvé: {company_name} - ID: {promoter_id}")
                        return promoter_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur recherche promoteur: {e}")
            return None
    
    def create_promoter_if_needed(self, promoter_name: str) -> Optional[int]:
        """Crée un promoteur si nécessaire"""
        if not promoter_name or not promoter_name.strip():
            return int(DEFAULT_PROMOTER_ID)
        
        promoter_name = promoter_name.strip()
        
        existing_id = self.search_promoter(promoter_name)
        if existing_id:
            return existing_id
        
        if not self.ensure_authenticated():
            return int(DEFAULT_PROMOTER_ID)
        
        try:
            address_obj = {
                "street": "Adresse par défaut, Tunisie",
                "city": "Tunis",
                "postalCode": "1000",
                "countryId": DEFAULT_PAYS_ID
            }
            
            promoter_data = {
                "companyName": promoter_name,
                "address": address_obj,
                "countryId": DEFAULT_PAYS_ID,
            }
            
            response = self.api_session.post(PROMOTER_ENDPOINT, json=promoter_data)
            
            if response.status_code == 201:
                data = response.json()
                promoter_id = data.get('id')
                self.logger.info(f"✅ Promoteur créé: {promoter_name} - ID: {promoter_id}")
                return promoter_id
            elif response.status_code == 409:
                return self.search_promoter(promoter_name) or int(DEFAULT_PROMOTER_ID)
            else:
                self.logger.error(f"❌ Erreur création promoteur: {response.status_code}")
                return int(DEFAULT_PROMOTER_ID)
                
        except Exception as e:
            self.logger.error(f"❌ Erreur promoteur: {e}")
            return int(DEFAULT_PROMOTER_ID)
    
    def map_offre_to_tender_payload_tunisie(self, offre) -> dict:
        """Map pour payload API HAICOP avec IMAGE FIXE"""
        def parse_date(date_str):
            if not date_str or date_str == "N/A":
                return None
            try:
                if '/' in date_str:
                    dt = parse(date_str, dayfirst=True, tzinfos={None: tz.gettz('Africa/Tunis')})
                else:
                    dt = parse(date_str, tzinfos={None: tz.gettz('Africa/Tunis')})
                return dt.isoformat()
            except:
                return None
        
        publication_ts = parse_date(offre.publicationDate)
        expiration_ts = parse_date(offre.expirationDate)
        
        if publication_ts is None:
            publication_ts = datetime.now(timezone.utc).isoformat()
        
        if expiration_ts is None:
            if publication_ts:
                pub_dt = parse(publication_ts)
                exp_dt = (pub_dt + timedelta(days=5)).replace(hour=12, minute=0, second=0, microsecond=0)
                expiration_ts = exp_dt.isoformat()
            else:
                expiration_ts = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        
        if expiration_ts and publication_ts:
            pub_dt = parse(publication_ts)
            exp_dt = max(parse(expiration_ts), pub_dt + timedelta(days=5))
            expiration_ts = exp_dt.isoformat()
        
        start_bidding_ts = publication_ts
        opening_bids_ts = expiration_ts
        
        promoter_id = self.create_promoter_if_needed(offre.promoter or "Promoteur Tunisie Default")
        
        # ✅ NOUVEAU: Utiliser l'image fixe
        images = []
        if self.fixed_image_s3_path:
            images = [self.fixed_image_s3_path]
            self.logger.info(f"✅ Image fixe incluse dans payload: {self.fixed_image_s3_path}")
        else:
            self.logger.warning(f"⚠️ Aucune image fixe disponible pour {offre.reference}")
        
        payload = {
            "title": offre.description,
            "description": offre.description,
            "publicationDate": publication_ts,
            "startBiddingDate": start_bidding_ts,
            "expirationDate": expiration_ts,
            "openingBidsDate": opening_bids_ts,
            "reference": offre.reference,
            "specificationsPrice": 0,
            "offerValidityPeriode": 10,
            "costEstimateMin": None,
            "costEstimateMax": None,
            "avisId": int(self.avis_id),
            "sourceId": int(self.source_id),
            "promoterId": promoter_id,
            "type": offre.type,
            "nature": offre.nature,
            "isEnabled": True,
            "images": images,  # ✅ NOUVEAU: Array avec l'image fixe
            "specificationsReceivingAddress": offre.url_source or "Adresse par défaut",
            "fundingSourceType": "national",
            "fundingSource": offre.fundingSource or "Source nationale",
            "currencyId": 111,
            "isMultiCurrency": offre.isMultiCurrency,
            "batches": [{
                "activitiesIds": offre.activities_ids or [461], 
                "title": f"Lot 1: {offre.description}", 
                "deposit": "0"
            }],
            "addresses": [{"countryId": self.pays_id, "regionId": 18}]
        }
        
        return {k: v for k, v in payload.items() if v is not None and v != ""}
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3), 
        wait=tenacity.wait_exponential(multiplier=2, min=1, max=10)
    )
    def post_to_haicop(self, payload):
        """Post avec retry vers API HAICOP"""
        if not self.ensure_authenticated():
            raise Exception("Auth failed")
        
        response = self.api_session.post(TENDER_ENDPOINT, json=payload)
        self.logger.info(f"📡 Réponse post tender: {response.status_code}")
        
        return response
    
    def post_tender_to_database_tunisie(self, offre) -> dict:
        """Validation: Insertion DB + Envoi API"""
        self.load_existing_offres()
        
        existing = tenders_collection.find_one({"reference": offre.reference})
        if existing:
            return {
                "success": False, 
                "message": "Offre déjà validée", 
                "offre_ref": offre.reference
            }
        
        tender_dict = offre.to_dict()
        tender_dict["status"] = "active"
        tender_dict["validationDate"] = datetime.now().isoformat()
        
        mongo_id = None
        
        try:
            result = tenders_collection.insert_one(tender_dict)
            mongo_id = result.inserted_id
            
            if result.inserted_id:
                self.logger.info(f"✅ Insertion DB: {offre.reference}")
                pending_tenders_collection.delete_one({"reference": offre.reference})
                
                api_success = False
                api_id = None
                api_message = ""
                
                try:
                    if self.ensure_authenticated():
                        payload = self.map_offre_to_tender_payload_tunisie(offre)
                        response = self.post_to_haicop(payload)
                        
                        if response.status_code == 201:
                            data = response.json()
                            api_id = data.get('id')
                            api_success = True
                            api_message = f"✅ Envoi API réussi - ID: {api_id}"
                            self.logger.info(api_message)
                        else:
                            api_message = f"❌ Erreur API: {response.status_code}"
                            self.logger.error(f"{api_message} - {response.text}")
                    else:
                        api_message = "❌ Échec authentification"
                        self.logger.error(api_message)
                        
                except Exception as api_e:
                    api_message = f"❌ Erreur API: {str(api_e)}"
                    self.logger.error(api_message)
                
                if not api_success:
                    if mongo_id:
                        tenders_collection.delete_one({"_id": mongo_id})
                        self.logger.info(f"🔄 Rollback DB pour {offre.reference}")
                    pending_tenders_collection.insert_one(tender_dict)
                    return {
                        "success": False,
                        "message": f"Échec envoi API. Offre remise en pending. {api_message}",
                        "offre_ref": offre.reference,
                        "api_success": False
                    }
                
                return {
                    "success": True,
                    "message": f"✅ Validation réussie: DB + API - ID: {api_id}",
                    "offre_ref": offre.reference,
                    "mongo_id": str(mongo_id),
                    "api_id": api_id,
                    "api_success": True
                }
            else:
                return {
                    "success": False, 
                    "message": "Échec insertion DB", 
                    "offre_ref": offre.reference
                }
                
        except Exception as e:
            self.logger.error(f"❌ Erreur DB: {e}")
            traceback.print_exc()
            return {
                "success": False, 
                "message": str(e), 
                "offre_ref": offre.reference
            }
    
    def __del__(self):
        if self.driver:
            self.driver.quit()

# Initialisation scraper
scraper_tunisie = TunisieScraper()

# Flask App
app = Flask(__name__, 
            static_folder=REACT_BUILD_DIR, 
            static_url_path='', 
            template_folder=REACT_BUILD_DIR)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    file_path = os.path.join(REACT_BUILD_DIR, path)
    if path != "" and os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path)
    else:
        index_path = os.path.join(REACT_BUILD_DIR, 'index.html')
        if os.path.exists(index_path):
            return send_file(index_path)
        else:
            return "Erreur: Build React manquant.", 500

@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint de santé pour vérifier que le serveur fonctionne"""
    try:
        # Vérifier MongoDB
        pending_count = pending_tenders_collection.count_documents({})
        validated_count = tenders_collection.count_documents({})
        return jsonify({
            "success": True,
            "status": "healthy",
            "pending_count": pending_count,
            "validated_count": validated_count,
            "message": "Service HAICOP opérationnel"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "error",
            "error": str(e),
            "message": "Erreur de connexion MongoDB"
        }), 500

@app.route('/api/scrape-tunisie', methods=['POST'])
def scrape_tunisie():
    data = request.json
    date_filtre = data.get('date_filtre', "ALL")
    if not date_filtre or date_filtre.strip() == "":
        date_filtre = "ALL"
    max_pages = data.get('max_pages', None)
    
    result = scraper_tunisie.scraper_tunisie_and_send(date_filtre, max_pages)
    
    return jsonify({
        "success": result["success"], 
        "offres": result["offres"],
        "message": f"Extraction terminée: {result['offres']['saved']} offres ajoutées (sur {result['offres']['total']} trouvées)"
    })

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_offre(reference):
    pending_doc = pending_tenders_collection.find_one({
        "reference": reference, 
        "status": "pending"
    })
    
    if not pending_doc:
        return jsonify({
            "success": False, 
            "message": "Offre non trouvée en pending", 
            "offre_ref": reference
        })
    
    pending_doc_without_id = {k: v for k, v in pending_doc.items() if k != '_id'}
    
    if pending_doc_without_id.get("source") == "MarchesPublicsTN":
        offre = OffreTunisie(**pending_doc_without_id)
        result = scraper_tunisie.post_tender_to_database_tunisie(offre)
    else:
        result = {"success": False, "message": "Source non supportée"}
    
    if result['success']:
        pending_tenders_collection.delete_one({"reference": reference})
    
    return jsonify(result)

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Endpoint avec pagination (ancien, pour compatibilité)"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    try:
        all_pending_docs = list(pending_tenders_collection.find({
            "status": "pending"
        }).sort("createdAt", -1))
        
        all_pending = []
        for doc in all_pending_docs:
            doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
            if doc_without_id.get("source") == "MarchesPublicsTN":
                offre = OffreTunisie(**doc_without_id)
                all_pending.append(offre)
        
        total = len(all_pending)
        start = (page - 1) * limit
        end = start + limit
        paginated_offres = all_pending[start:end]
        
        return jsonify({
            "success": True,
            "pending": {
                "offres": [{
                    "reference": o.reference, 
                    "description": o.description, 
                    "secteur_activite": o.secteur_activite,
                    "promoter": o.promoter,
                    "source": o.source, 
                    "publicationDate": o.publicationDate, 
                    "expirationDate": o.expirationDate, 
                    "image_filename": o.image_filename, 
                    "secteur_activite_id": o.secteur_activite_id
                } for o in paginated_offres],
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": (total + limit - 1) // limit
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/pending-all', methods=['GET'])
def get_pending_all():
    """Endpoint pour récupérer TOUTES les offres en attente (sans pagination)"""
    try:
        all_pending_docs = list(pending_tenders_collection.find({
            "status": "pending"
        }).sort("createdAt", -1))
        
        all_pending = []
        for doc in all_pending_docs:
            doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
            if doc_without_id.get("source") == "MarchesPublicsTN":
                all_pending.append({
                    "reference": doc_without_id.get("reference"), 
                    "description": doc_without_id.get("description"), 
                    "secteur_activite": doc_without_id.get("secteur_activite"),
                    "promoter": doc_without_id.get("promoter"),
                    "source": doc_without_id.get("source"), 
                    "publicationDate": doc_without_id.get("publicationDate"), 
                    "expirationDate": doc_without_id.get("expirationDate"), 
                    "image_filename": doc_without_id.get("image_filename"), 
                    "secteur_activite_id": doc_without_id.get("secteur_activite_id"),
                    "createdAt": doc_without_id.get("createdAt")
                })
        
        return jsonify({
            "success": True,
            "offres": all_pending,
            "total": len(all_pending)
        })
    except Exception as e:
        logger.error(f"Erreur get_pending_all: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/validated-all', methods=['GET'])
def get_validated_all():
    """Endpoint pour récupérer TOUTES les offres validées (sans pagination)"""
    try:
        all_validated_docs = list(tenders_collection.find({
            "status": "active",
            "source": "MarchesPublicsTN"
        }).sort("validationDate", -1))
        
        all_validated = []
        for doc in all_validated_docs:
            doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
            all_validated.append({
                "reference": doc_without_id.get("reference"), 
                "description": doc_without_id.get("description"), 
                "secteur_activite": doc_without_id.get("secteur_activite"),
                "promoter": doc_without_id.get("promoter"),
                "source": doc_without_id.get("source"), 
                "publicationDate": doc_without_id.get("publicationDate"), 
                "expirationDate": doc_without_id.get("expirationDate"), 
                "validationDate": doc_without_id.get("validationDate"),
                "image_filename": doc_without_id.get("image_filename"), 
                "secteur_activite_id": doc_without_id.get("secteur_activite_id"),
                "createdAt": doc_without_id.get("createdAt")
            })
        
        return jsonify({
            "success": True,
            "offres": all_validated,
            "total": len(all_validated)
        })
    except Exception as e:
        logger.error(f"Erreur get_validated_all: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/download_image/<filename>')
def download_image(filename):
    image_path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(image_path) and os.path.getsize(image_path) > 100:
        return send_file(image_path, as_attachment=True)
    
    pdf_path = os.path.join(TUNISIE_PDF_DIR, filename)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100:
        return send_file(pdf_path, as_attachment=True)
    
    return jsonify({"success": False, "message": "Fichier non trouvé"}), 404

@app.route('/api/update/<reference>', methods=['POST'])
def update_offre(reference):
    data = request.json
    result = pending_tenders_collection.update_one(
        {"reference": reference},
        {"$set": {"secteur_activite_id": data.get("secteur_activite_id")}}
    )
    
    if result.modified_count > 0:
        return jsonify({
            "success": True, 
            "message": "Mise à jour réussie", 
            "offre_ref": reference
        })
    return jsonify({
        "success": False, 
        "message": "Offre non trouvée", 
        "offre_ref": reference
    })

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete_offre(reference):
    result = pending_tenders_collection.delete_one({"reference": reference})
    
    if result.deleted_count > 0:
        return jsonify({
            "success": True, 
            "message": "Suppression réussie", 
            "offre_ref": reference
        })
    return jsonify({
        "success": False, 
        "message": "Offre non trouvée", 
        "offre_ref": reference
    })

@app.route('/api/clear-all', methods=['DELETE'])
def clear_all():
    """Supprime toutes les offres pending et validated"""
    try:
        pending_result = pending_tenders_collection.delete_many({})
        validated_result = tenders_collection.delete_many({})

        return jsonify({
            "success": True,
            "message": f"{pending_result.deleted_count} pending et {validated_result.deleted_count} validated supprimées",
            "pending_deleted": pending_result.deleted_count,
            "validated_deleted": validated_result.deleted_count
        })
    except Exception as e:
        logger.error(f"Erreur clear-all: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/clean-duplicates', methods=['POST'])
def clean_duplicates():
    """Nettoie les doublons dans la collection pending"""
    try:
        from collections import defaultdict
        
        all_docs = list(pending_tenders_collection.find({"status": "pending"}))
        total_before = len(all_docs)
        
        docs_by_reference = defaultdict(list)
        for doc in all_docs:
            reference = doc.get('reference')
            if reference:
                docs_by_reference[reference].append(doc)
        
        deleted_count = 0
        
        for reference, docs in docs_by_reference.items():
            if len(docs) > 1:
                docs_sorted = sorted(docs, key=lambda x: x.get('createdAt', ''), reverse=True)
                docs_to_delete = docs_sorted[1:]
                
                for doc in docs_to_delete:
                    pending_tenders_collection.delete_one({"_id": doc['_id']})
                    deleted_count += 1
        
        final_count = pending_tenders_collection.count_documents({"status": "pending"})
        
        return jsonify({
            "success": True,
            "message": f"Nettoyage terminé: {deleted_count} doublons supprimés",
            "stats": {
                "before": total_before,
                "deleted": deleted_count,
                "after": final_count
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors du nettoyage: {str(e)}"
        })

if __name__ == "__main__":
    # Configuration UTF-8 pour Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("SCRAPER MARCHES PUBLICS TUNISIE - HAICOP - VERSION FINALE AVEC IMAGE")
    print("=" * 80)
    print(f"Source: Projets Annuels Tunisie (ID: {TUNISIE_SOURCE_ID})")
    print(f"Pays: Tunisie (ID: {TUNISIE_PAYS_ID})")
    print(f"Dossier PDF: {TUNISIE_PDF_DIR}")
    print(f"API HAICOP: {API_BASE_URL}")
    print(f"IMAGE FIXE: {FIXED_IMAGE_SOURCE_PATH}")
    print("=" * 80)
    print("STRATEGIE DE NAVIGATION:")
    print("   - Navigation forcee jusqu'a 100 pages par defaut")
    print("   - Stop automatique apres 3 pages vides consecutives")
    print("   - Extraction complete garantie de toutes les donnees disponibles")
    print("   - Upload automatique de l'image fixe via /api/files/tender")
    print("=" * 80)
    print(f"Serveur demarre sur: http://localhost:5011")
    print("=" * 80)

    app.run(debug=False, port=5011, host='0.0.0.0')
