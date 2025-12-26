# pnud.py - Version Finale (Traduction Multi-langues → Français)
# AMÉLIORATIONS FINALES:
# - Détection automatique de la langue source (IT, EN, ES, FR, DE, etc.)
# - Traduction automatique vers le français
# - Nettoyage des références et numéros avant traduction
# - Description française simple et correcte sans codes
import os
import json
import logging
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, parse_qs, urlparse
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure
from bson import ObjectId
import tenacity
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import openpyxl
import time
import math
import asyncio
from playwright.async_api import async_playwright
from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_pnud.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tunip")
DB_NAME = os.getenv("DB_NAME", "tunip")
COLLECTION_NAME = os.getenv("PNUD_COLLECTION_NAME", "tenders_pnud")
PENDING_COLLECTION_NAME = os.getenv("PNUD_PENDING_COLLECTION_NAME", "pending_tenders_pnud")

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"

# PNUD utilise le compte de Marwa Idoudi (hardcodé, ne pas utiliser .env)
EMAIL = "marwa.aidoudi@tunipages.tn"
PASSWORD = "lopMP@!#"

DEFAULT_SOURCE_ID_PNUD = int(os.getenv("DEFAULT_SOURCE_ID_PNUD", "1656"))
DEFAULT_AVIS_ID = int(os.getenv("DEFAULT_AVIS_ID", "1"))

# Paths
OUTPUT_DIR = "output"
EXCEL_DIR = "excelpnud"
SCREENSHOTS_DIR = "screenshots"
PROMOTERS_XLS_FILE = os.path.join(EXCEL_DIR, "all_promoters.xlsx")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EXCEL_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Country Mapping
COUNTRY_MAPPING = {
    "TIMOR LESTE": 214, "SRI LANKA": 197, "PAKISTAN": 159, "KAZAKHSTAN": 105, "BANGLADESH": 23,
    "UZBEKISTAN": 157, "MAURITIUS": 133, "ANGOLA": 9, "ETHIOPIA": 66, "JORDAN": 104,
    "DENMARK": 59, "NIGERIA": 149, "GAMBIA": 73, "COLOMBIA": 50, "CUBA": 57,
    "EQUATORIAL GUINEA": 83, "SEYCHELLES": 190, "MAURITANIA": 134, "TURKEY": 220, "GUINEA-BISSAU": 84,
    "CAMBODIA": 40, "INDONESIA": 95, "MONGOLIA": 140, "CAMEROON": 41, "VIET NAM": 231,
    "MALI": 127, "TUNISIA": 219, "BRAZIL": 35, "GUINEA": 82, "SIERRA LEONE": 191,
    "MALAYSIA": 124, "TAJIKISTAN": 207, "THAILAND": 213, "TURKMENISTAN": 220, "AFGHANISTAN": 3,
    "SERBIA": 194, "BOSNIA AND HERZEGOVINA": 31, "UGANDA": 156, "UKRAINE": 221, "NEPAL": 146,
    "HONDURAS": 91, "PANAMA": 161, "BOLIVIA": 30, "ARGENTINA": 15, "ECUADOR": 224,
    "EGYPT": 222, "KYRGYZSTAN": 107, "LEBANON": 115, "INDIA": 94, "UNITED STATES OF AMERICA": 226,
    "BURUNDI": 38, "ALBANIA": 5, "BOTSWANA": 32, "ARMENIA": 16, "TONGA": 217,
    "CYPRUS": 48, "GERMANY": 7, "MONTENEGRO": 232, "MOLDOVA": 138, "IRAQ": 96,
    "SOMALIA": 195, "PALESTINIAN TERRITORIES": 160, "SOUTH SUDAN": 196, "MICRONESIA": 137, "COTE d'IVOIRE": 58,
    "LESOTHO": 113, "CONGO, DEM. REPUBLIC": 177, "SUDAN": 196, "KENYA": 106, "MALAWI": 125,
    "SENEGAL": 205, "CHAD": 210, "GEORGIA": 87, "MEXICO": 136, "CENTRAL AFRICAN REPUBLIC": 179,
    "URUGUAY": 224, "EL SALVADOR": 63, "COSTA RICA": 55, "PARAGUAY": 163, "GUYANA": 85,
    "PERU": 171, "LIBERIA": 117, "NORTH MACEDONIA": 122, "ZIMBABWE": 230, "MOZAMBIQUE": 142,
    "GHANA": 74, "ZAMBIA": 229, "LIBYA": 118, "SYRIA": 206, "YEMEN": 228,
    "JAPAN": 103, "CHINA": 46, "RUSSIA": 175, "CANADA": 44, "FRANCE": 71,
    "ITALY": 99, "SPAIN": 198, "UNITED KINGDOM": 225, "AUSTRALIA": 18, "NEW ZEALAND": 148,
    "SOUTH KOREA": 108, "SINGAPORE": 192, "PHILIPPINES": 172, "MYANMAR": 144, "LAOS": 111,
    "BHUTAN": 29, "MALDIVES": 126, "NICARAGUA": 147, "DOMINICAN REPUBLIC": 60, "HAITI": 89,
    "JAMAICA": 101, "TRINIDAD AND TOBAGO": 218, "BARBADOS": 24, "BAHAMAS": 22, "BELIZE": 27,
    "GUATEMALA": 81, "BELARUS": 25, "AZERBAIJAN": 20, "LATVIA": 112, "LITHUANIA": 119,
    "ESTONIA": 65, "FINLAND": 69, "SWEDEN": 204, "NORWAY": 152, "SWITZERLAND": 205,
    "AUSTRIA": 17, "POLAND": 173, "CZECH REPUBLIC": 56, "SLOVAKIA": 193, "HUNGARY": 93,
    "ROMANIA": 174, "BULGARIA": 37, "GREECE": 78, "PORTUGAL": 174, "NETHERLANDS": 145,
    "BELGIUM": 26, "LUXEMBOURG": 121, "IRELAND": 97, "ICELAND": 92, "MALTA": 128,
    "SLOVENIA": 195, "CROATIA": 54, "BOSNIA": 31, "ALGERIA": 6, "MOROCCO": 141,
    "ERITREA": 64, "DJIBOUTI": 58, "TANZANIA": 208, "RWANDA": 176, "CONGO": 51,
    "GABON": 72, "SAO TOME AND PRINCIPE": 184, "COMOROS": 52, "VIETNAM": 231
}

CODE_TO_COUNTRY = {
    "MNG": "MONGOLIA",
    "CRI": "COSTA RICA",
    "HTI": "HAITI",
    "LKA": "SRI LANKA",
    "TLS": "TIMOR-LESTE",
    "PHL": "PHILIPPINES",
    "VNM": "VIET NAM",
    "KAZ": "KAZAKHSTAN",
    "TKM": "TURKMENISTAN",
    "NPL": "NEPAL",
}

def map_nature_to_english(nature_fr: str) -> str:
    mapping = {
        "Privé": "private",
        "PPP": "ppp",
        "Autres": "other"
    }
    return mapping.get(nature_fr, "private")

def map_nature_to_french(nature_en: str) -> str:
    mapping = {
        "private": "Privé",
        "ppp": "PPP",
        "other": "Autres",
        "public": "Public"
    }
    return mapping.get(nature_en.lower(), "Privé")

@dataclass
class OffrePNUD:
    reference: str
    description: str
    description_fr: str
    publicationDate: str
    startBiddingDate: str
    expirationDate: str
    promoter: str
    sourceId: int
    avisId: int = DEFAULT_AVIS_ID
    pdfUrl: Optional[str] = None
    externalUrl: Optional[str] = None
    montant: Optional[str] = None
    fetchedAt: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    category: str = "international"
    country_id: Optional[int] = None
    country: str = ""
    process: Optional[str] = None
    nature: str = field(default="private")
    nature_display: str = field(default="Privé")
    image_path: Optional[str] = None

def serialize_document(doc):
    if not doc:
        return doc
    doc = doc.copy() if isinstance(doc, dict) else dict(doc)
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc

def serialize_tenders(tenders_list):
    return [serialize_document(t) for t in tenders_list]

class PNUDScraper:
    def __init__(self):
        self.base_url = "https://procurement-notices.undp.org"
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.last_login_time = None
        self.session_appeloffres = requests.Session()
        self.existing_offres_set = set()
        self.default_source_id = DEFAULT_SOURCE_ID_PNUD
        self.promoters_cache: Dict[str, int] = {}
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session.headers.update(self.headers)
        
        # Initialiser le traducteur avec AUTO-DETECTION de toutes les langues → Français
        try:
            self.translator = GoogleTranslator(source='auto', target='fr')
            logger.info("✅ Traducteur Google initialisé (auto-détection multi-langues → FR)")
            logger.info("   Langues supportées: IT, EN, ES, DE, PT, NL, RU, AR, ZH, JA, etc.")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation traducteur: {e}")
            self.translator = None
        
        self.mongo_client = None
        self.db = None
        self.tenders_collection = None
        self.pending_tenders_collection = None
        self.mongo_connected = self.connect_to_mongodb()
        
        if self.mongo_connected:
            self._load_existing_offres_set()
        
        if self.get_api_token():
            self.load_all_promoters()
            self.export_promoters_to_xls(PROMOTERS_XLS_FILE)

    def connect_to_mongodb(self):
        try:
            self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[DB_NAME]
            self.tenders_collection = self.db[COLLECTION_NAME]
            self.pending_tenders_collection = self.db[PENDING_COLLECTION_NAME]
            logger.info("✅ Connexion à MongoDB établie avec succès")
            return True
        except (ConnectionFailure, PyMongoError) as e:
            logger.error(f"❌ Erreur lors de la connexion à MongoDB: {e}")
            return False

    def _load_existing_offres_set(self):
        if not self.mongo_connected:
            return
        try:
            existing_offres = self.tenders_collection.find({}, {"reference": 1})
            self.existing_offres_set = {offre["reference"] for offre in existing_offres if "reference" in offre}
            logger.info(f"📦 Chargé {len(self.existing_offres_set)} offres existantes depuis MongoDB")
        except PyMongoError as e:
            logger.error(f"❌ Erreur lors du chargement des offres existantes: {e}")

    def save_to_pending(self, offre: OffrePNUD):
        if not self.mongo_connected:
            logger.warning(f"Offre {offre.reference} non sauvegardée: MongoDB non connecté")
            return
        try:
            doc = asdict(offre)
            self.pending_tenders_collection.update_one(
                {"reference": offre.reference},
                {"$set": doc},
                upsert=True
            )
            logger.info(f"💾 Offre {offre.reference} sauvegardée dans pending_tenders")
        except PyMongoError as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de l'offre {offre.reference}: {e}")

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
    def get_api_token(self):
        current_time = datetime.now(timezone.utc)
        if self.access_token and self.last_login_time and (current_time - self.last_login_time).total_seconds() <= 86400:
            logger.info("🔑 Token réutilisé (moins de 24h depuis dernière connexion)")
            return True
        
        try:
            logger.info(f"🔑 Tentative de connexion API avec compte: {EMAIL}")
            response = self.session_appeloffres.post(
                LOGIN_ENDPOINT,
                json={"email": EMAIL, "password": PASSWORD},
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('accessToken')
                self.refresh_token = data.get('refreshToken')
                self.last_login_time = current_time
                
                if self.access_token:
                    logger.info("🔑 Token d'accès obtenu avec succès (valide 24h)")
                    return True
            
            logger.error(f"❌ Échec de l'authentification API: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'authentification API: {e}")
            raise

    def load_all_promoters(self):
        if not self.access_token:
            logger.warning("⚠️ Impossible de charger promoteurs: pas de token")
            return
        
        all_promoters = {}
        page = 1
        items_per_page = 100
        
        while True:
            params = {"page": page, "itemsPerPage": items_per_page}
            search_url = f"{PROMOTER_ENDPOINT}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
            
            response = self.session_appeloffres.get(search_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Échec chargement promoteurs page {page}: {response.status_code}")
                break
            
            data = response.json()
            promoters = data.get('data', [])
            
            if not promoters:
                break
            
            for promoter in promoters:
                name = promoter.get('name', '').strip().upper()
                promoter_id = promoter.get('id')
                if name and promoter_id:
                    all_promoters[name] = int(promoter_id)
            
            logger.info(f"📦 Page {page}: {len(promoters)} promoteurs chargés")
            page += 1
        
        self.promoters_cache = all_promoters
        logger.info(f"✅ Cache promoteurs chargé: {len(self.promoters_cache)} entrées")

    def export_promoters_to_xls(self, filename: str):
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Promoters"
            
            headers = ['ID', 'Name']
            ws.append(headers)
            
            for name, pid in sorted(self.promoters_cache.items(), key=lambda x: x[1]):
                ws.append([pid, name.lower().title()])
            
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            wb.save(filename)
            logger.info(f"💾 XLS promoteurs exporté/créé: {filename} ({len(self.promoters_cache)} lignes)")
        except Exception as e:
            logger.error(f"❌ Erreur export XLS promoteurs: {e}")

    def update_promoters_xls(self, promoter_name: str, promoter_id: int):
        try:
            if not os.path.exists(PROMOTERS_XLS_FILE):
                logger.warning(f"⚠️ Fichier XLS promoteurs non trouvé: {PROMOTERS_XLS_FILE}. Création d'un nouveau.")
                self.export_promoters_to_xls(PROMOTERS_XLS_FILE)
                return
            
            wb = openpyxl.load_workbook(PROMOTERS_XLS_FILE)
            ws = wb.active
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and row[0] == promoter_id:
                    logger.info(f"📝 Promoteur {promoter_name} (ID: {promoter_id}) déjà présent dans XLS, pas d'ajout")
                    wb.close()
                    return
            
            ws.append([promoter_id, promoter_name.lower().title()])
            
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            wb.save(PROMOTERS_XLS_FILE)
            logger.info(f"📝 Promoteur {promoter_name} (ID: {promoter_id}) ajouté au XLS: {PROMOTERS_XLS_FILE}")
            wb.close()
        except Exception as e:
            logger.error(f"❌ Erreur update XLS promoteurs pour {promoter_name}: {e}")

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
    def find_or_create_promoter(self, promoter_name: str) -> Optional[int]:
        if not self.access_token:
            logger.warning("⚠️ Impossible de find/create promoteur: pas de token")
            return None
        
        normalized = promoter_name.strip().upper()
        
        if normalized in self.promoters_cache:
            promoter_id = self.promoters_cache[normalized]
            logger.info(f"✅ Promoteur '{promoter_name}' trouvé dans le cache/output XLS avec ID: {promoter_id}")
            return promoter_id
        
        try:
            logger.info(f"➕ Promoteur '{promoter_name}' non trouvé dans cache/output XLS - Création via API")
            create_data = {
                "name": promoter_name,
                "description": f"Promoteur PNUD: {promoter_name}",
                "reference": re.sub(r'\W+', '_', promoter_name.upper())[:20],
                "isEnabled": True,
                "companyName": promoter_name,
                "address": {
                    "street": "UNDP Address",
                    "city": "New York",
                    "country": "United States",
                    "postalCode": "10017"
                }
            }
            
            headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json", "Accept": "application/json"}
            
            create_response = self.session_appeloffres.post(
                PROMOTER_ENDPOINT,
                json=create_data,
                headers=headers,
                timeout=10
            )
            
            if create_response.status_code in [200, 201]:
                create_data_resp = create_response.json()
                promoter_id = create_data_resp.get('id')
                if promoter_id:
                    self.promoters_cache[normalized] = int(promoter_id)
                    self.update_promoters_xls(promoter_name, int(promoter_id))
                    logger.info(f"✅ Promoteur '{promoter_name}' créé avec ID: {promoter_id}")
                    return int(promoter_id)
            
            logger.error(f"❌ Échec création promoteur '{promoter_name}': {create_response.status_code}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur find_or_create_promoter '{promoter_name}': {e}")
            return None

    def normaliser_date_api(self, date_str: str) -> str:
        if not date_str or date_str == "N/A":
            return datetime.now(timezone.utc).isoformat()
        
        try:
            date_str = date_str.strip()
            logger.debug(f"🔍 Normalisation de la date: '{date_str}'")
            
            if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}$', date_str):
                date_part = date_str.split('T')[0]
                date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                date_obj = date_obj.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
                iso_date = date_obj.isoformat()
                logger.debug(f"✅ Date ISO nettoyée: {iso_date}")
                return iso_date
            
            pattern = r'(\d{1,2})-([A-Za-z]{3})-(\d{2})'
            match = re.search(pattern, date_str, re.IGNORECASE)
            
            if match:
                day = match.group(1)
                month = match.group(2)
                year = match.group(3)
                date_string = f"{day}-{month}-{year} 00:00"
                date_obj = datetime.strptime(date_string, "%d-%b-%y %H:%M")
                date_obj = date_obj.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
                iso_date = date_obj.isoformat()
                logger.debug(f"✅ Date normalisée: {iso_date}")
                return iso_date
            else:
                logger.warning(f"⚠️ Pattern non trouvé pour: '{date_str}'")
                date_part = date_str.split('@')[0].strip() if '@' in date_str else date_str.split('(')[0].strip()
                try:
                    date_obj = datetime.strptime(date_part, "%d-%b-%y")
                    date_obj = date_obj.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
                except:
                    logger.warning(f"⚠️ Impossible de parser '{date_str}', utilisation de la date actuelle")
                    date_obj = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
                
                return date_obj.isoformat()
        except Exception as e:
            logger.error(f"❌ Erreur normalisation date '{date_str}': {e}")
            return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()

    def format_date_for_display(self, date_str: str) -> str:
        if not date_str or date_str == "N/A":
            return "N/A"
        try:
            iso_date = self.normaliser_date_api(date_str)
            dt = datetime.fromisoformat(iso_date)
            return dt.strftime("%d / %m / %Y")
        except Exception as e:
            logger.warning(f"⚠️ Erreur formatage affichage '{date_str}': {e}")
            return date_str

    def clean_text_for_translation(self, text: str) -> str:
        """
        Nettoie le texte avant traduction
        - Supprime les références (UNDP-XXX-12345, P123456, etc.)
        - Supprime les numéros isolés
        - Supprime les codes entre parenthèses
        """
        if not text:
            return ""
        
        cleaned = text.strip()
        
        # Supprimer les références UNDP-XXX-12345
        cleaned = re.sub(r'UNDP-[A-Z]{3}-\d+', '', cleaned, flags=re.IGNORECASE)
        
        # Supprimer les références de type P123456, P-123456
        cleaned = re.sub(r'\b[P]\-?\d{5,}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Supprimer les numéros de projet entre parenthèses
        cleaned = re.sub(r'\([P\d\-\s]+\)', '', cleaned)
        
        # Supprimer les codes/numéros au début
        cleaned = re.sub(r'^\d+\s*[-–]\s*', '', cleaned)
        
        # Supprimer les doubles espaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Supprimer les tirets en début/fin
        cleaned = re.sub(r'^[-–\s]+|[-–\s]+$', '', cleaned)
        
        return cleaned.strip()

    def translate_to_french(self, text: str) -> str:
        """
        ✅ TRADUCTION AUTOMATIQUE MULTI-LANGUES → FRANÇAIS
        
        Détecte automatiquement la langue source parmi:
        - Italien (IT)
        - Anglais (EN)
        - Espagnol (ES)
        - Allemand (DE)
        - Portugais (PT)
        - Néerlandais (NL)
        - Russe (RU)
        - Arabe (AR)
        - Chinois (ZH)
        - Japonais (JA)
        - Et 100+ autres langues supportées par Google Translate
        
        Retourne toujours une description en FRANÇAIS propre et correcte
        """
        if not text or len(text.strip()) == 0:
            logger.warning("⚠️ Texte vide, pas de traduction")
            return ""
        
        if not self.translator:
            logger.warning("⚠️ Traducteur non disponible, retour texte original")
            return text
        
        try:
            # 1. Nettoyer le texte avant traduction
            text_cleaned = self.clean_text_for_translation(text)
            
            if not text_cleaned or len(text_cleaned) < 5:
                logger.warning(f"⚠️ Texte trop court après nettoyage: '{text_cleaned}'")
                return text.strip()
            
            logger.debug(f"🧹 Texte nettoyé: '{text[:50]}...' → '{text_cleaned[:50]}...'")
            
            # 2. Traduire avec auto-détection de langue
            # GoogleTranslator va automatiquement détecter si c'est de l'italien, espagnol, anglais, etc.
            translated = self.translator.translate(text_cleaned)
            
            if not translated or len(translated.strip()) == 0:
                logger.warning(f"⚠️ Traduction vide pour '{text_cleaned[:50]}...', retour original")
                return text_cleaned
            
            # 3. Formater la phrase en français
            translated = translated.strip()
            
            # Première lettre en majuscule
            if translated and not translated[0].isupper():
                translated = translated[0].upper() + translated[1:]
            
            # Point final si manquant
            if translated and translated[-1] not in ['.', '!', '?']:
                translated += '.'
            
            logger.info(f"✅ Traduction (auto-détection → FR): '{text_cleaned[:40]}...' → '{translated[:40]}...'")
            return translated
            
        except Exception as e:
            logger.error(f"❌ Erreur traduction '{text[:50]}...': {e}")
            # En cas d'erreur, retourner le texte nettoyé
            cleaned = self.clean_text_for_translation(text)
            return cleaned if cleaned else text.strip()

    def validate_tender_data(self, offre: OffrePNUD) -> tuple[bool, str]:
        """
        Validation des données avant envoi API
        """
        errors = []
        
        if not offre.reference or len(offre.reference.strip()) == 0:
            errors.append("Référence vide")
        
        if not offre.description or len(offre.description.strip()) < 10:
            errors.append(f"Description EN invalide (trop courte: {len(offre.description if offre.description else '')} chars)")
        
        if not offre.description_fr or len(offre.description_fr.strip()) < 10:
            errors.append(f"Description FR invalide (trop courte: {len(offre.description_fr if offre.description_fr else '')} chars)")
        
        if not offre.promoter or len(offre.promoter.strip()) == 0:
            errors.append("Promoteur vide")
        
        if not offre.publicationDate or offre.publicationDate == "N/A":
            errors.append("Date de publication invalide")
        
        if not offre.expirationDate or offre.expirationDate == "N/A":
            errors.append("Date d'expiration invalide")
        
        if offre.country_id is not None and (not isinstance(offre.country_id, int) or offre.country_id <= 0):
            errors.append(f"Country ID invalide: {offre.country_id}")
        
        if not offre.nature or offre.nature not in ["private", "ppp", "other", "public"]:
            errors.append(f"Nature invalide: {offre.nature}")
        
        if not isinstance(offre.sourceId, int) or offre.sourceId <= 0:
            errors.append(f"Source ID invalide: {offre.sourceId}")
        
        if not isinstance(offre.avisId, int) or offre.avisId <= 0:
            errors.append(f"Avis ID invalide: {offre.avisId}")
        
        if errors:
            error_msg = f"Données invalides pour {offre.reference}: {'; '.join(errors)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        
        logger.info(f"✅ Validation réussie pour {offre.reference}")
        return True, ""

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
    def upload_screenshot(self, local_path: str) -> Optional[str]:
        if not self.get_api_token():
            logger.warning("⚠️ Impossible d'uploader: pas de token")
            return None
        
        try:
            with open(local_path, 'rb') as f:
                files = {'file': f}
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = self.session_appeloffres.post(FILES_ENDPOINT, files=files, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                data = response.json()
                url = data.get('url')
                if url:
                    parsed = urlparse(url)
                    if '/tender-s3/' in parsed.path:
                        image_path = parsed.path.split('/tender-s3/')[1]
                        logger.info(f"📸 Image uploadée: {image_path}")
                        os.remove(local_path)
                        return image_path
                    else:
                        logger.warning(f"⚠️ Format URL inattendu: {url}")
                        return None
            
            logger.error(f"❌ Échec upload: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur upload screenshot {local_path}: {e}")
            return None

    async def capture_screenshot_async(self, nego_url: str, screenshot_path: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(nego_url, wait_until='networkidle', timeout=30000)
                await page.screenshot(path=screenshot_path, full_page=True)
                await context.close()
                logger.info(f"📸 Screenshot capturé: {screenshot_path}")
            finally:
                await browser.close()

    def extract_tender_details_from_url(self, nego_url: str, reference: str, take_screenshot: bool = True) -> Optional[dict]:
        """
        Extraction des détails depuis l'URL
        """
        try:
            logger.info(f"🔍 Extraction détails depuis: {nego_url}")
            
            parsed_url = urlparse(nego_url)
            if 'cur_lang' not in parsed_url.query:
                if parsed_url.query:
                    nego_url += '&cur_lang=en'
                else:
                    nego_url += '?cur_lang=en'
                logger.debug(f"🌐 Lang EN forcée: {nego_url}")
            
            headers = {
                **self.headers,
                "Referer": f"{self.base_url}/index.cfm",
            }
            response = self.session.get(nego_url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code}: {nego_url}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if "Page Not Found" in soup.get_text() or "404" in soup.get_text():
                logger.warning(f"⚠️ Page non trouvée: {nego_url}")
                return None
            
            data = {
                'reference': reference,
                'title': None,
                'promoter': "United Nations Development Programme",
                'country': "",
                'process': None,
                'deadline': None,
                'posted': None,
                'pdf_url': None,
                'nego_url': nego_url,
                'nature': "Privé",
                'nature_display': "Privé",
                'image_path': None
            }
            
            content_text = soup.get_text()
            
            # EXTRACTION DU TITRE
            is_world_bank = 'banquemondiale.org' in nego_url or 'worldbank.org' in nego_url
            
            if is_world_bank:
                logger.debug("🏦 Source détectée: Banque Mondiale")
                
                summary_table = soup.find('table', class_=lambda x: x and ('brief' in x.lower() or 'summary' in x.lower() or 'avis' in x.lower()))
                if not summary_table:
                    summary_table = soup.find('table')
                
                if summary_table:
                    rows = summary_table.find_all('tr')
                    project_title = None
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label_cell = cells[0].get_text(strip=True).lower()
                            value_cell = cells[1].get_text(strip=True)
                            if 'intitulé du projet' in label_cell or 'project name' in label_cell:
                                project_title = value_cell.strip()
                                logger.debug(f"📌 Titre extrait de table: {project_title[:80]}...")
                                break
                            if 'pays' in label_cell or 'country' in label_cell:
                                next_row = rows[rows.index(row) + 1] if rows.index(row) + 1 < len(rows) else None
                                if next_row:
                                    next_cells = next_row.find_all(['td', 'th'])
                                    if len(next_cells) >= 2 and ('intitulé' in next_cells[0].get_text(strip=True).lower() or 'project' in next_cells[0].get_text(strip=True).lower()):
                                        project_title = next_cells[1].get_text(strip=True)
                                        logger.debug(f"📌 Titre extrait après Pays: {project_title[:80]}...")
                                        break
                
                if not project_title:
                    title_h1 = soup.find('h1', class_=lambda x: x and ('title' in x.lower() or 'heading' in x.lower()))
                    if not title_h1:
                        title_h1 = soup.find('h1')
                    if title_h1:
                        project_title = title_h1.get_text(strip=True)
                        project_title = re.sub(r'^[P\d\s-]+\s*-\s*', '', project_title.strip())
                
                if not project_title:
                    meta_title = soup.find('meta', property='og:title')
                    if meta_title and meta_title.get('content'):
                        project_title = meta_title['content'].strip()
                        project_title = re.sub(r'^[P\d\s-]+\s*-\s*', '', project_title)
                
                if project_title and len(project_title) > 10:
                    data['title'] = project_title
                    logger.debug(f"📌 Titre Banque Mondiale final: {data['title'][:80]}...")
                else:
                    data['title'] = f"World Bank Tender {reference}"
                    logger.warning(f"⚠️ Titre non trouvé pour Banque Mondiale, fallback: {data['title']}")
            
            else:
                logger.debug("🌐 Source détectée: UNDP")
                
                title_selectors = [
                    'h1.pnTitle', 'h1', '.page-title', '.content h1', 'title'
                ]
                for selector in title_selectors:
                    title_tag = soup.select_one(selector)
                    if title_tag:
                        title_text = title_tag.get_text(strip=True)
                        if title_text and len(title_text) > 10:
                            clean_title = re.sub(r'^Procurement Notices\s*-\s*UNDP-[A-Z0-9]+-\d+\s*-\s*', '', title_text, flags=re.IGNORECASE)
                            clean_title = re.sub(r'^\s*-\s*', '', clean_title).strip()
                            
                            if clean_title and len(clean_title) > 20:
                                data['title'] = clean_title
                                logger.debug(f"📌 Titre UNDP trouvé: {data['title'][:80]}...")
                                break
            
            if not data['title']:
                data['title'] = f"Tender {reference}"
                logger.warning(f"⚠️ Titre non trouvé, utilisation fallback: {data['title']}")
            
            logger.debug(f"🔖 Référence confirmée: {data['reference']}")
            
            # Extraction promoteur
            ref_code_match = re.match(r'UNDP-([A-Z]{3})-\d+', data['reference'])
            code = ref_code_match.group(1) if ref_code_match else None
            
            office_pattern = r'(?:Office|UNDP)\s*[:\-]?\s*UNDP-([A-Z]{3})\s*[-–]\s*([A-Z\s]+?)(?=\s*(?:DESCRIPTION|Contact|Deadline|\n\n|$))'
            office_match = re.search(office_pattern, content_text, re.IGNORECASE)
            if office_match:
                extracted_code = office_match.group(1)
                extracted_country = office_match.group(2).strip().upper()
                if extracted_code == code:
                    data['country'] = extracted_country
                    logger.debug(f"🌍 Country extrait via pattern office: {data['country']}")
            
            if code and not data['country']:
                data['country'] = CODE_TO_COUNTRY.get(code, "")
                if data['country']:
                    logger.debug(f"🌍 Country mappé via code {code}: {data['country']}")
            
            if not data['country']:
                country_pattern = r'Country\s*:\s*([A-Z\s]+?)(?=\s*(?:DESCRIPTION|Office|\(|\n\n|$))'
                country_match = re.search(country_pattern, content_text, re.IGNORECASE)
                if country_match:
                    data['country'] = country_match.group(1).strip().upper()
                    data['country'] = re.sub(r'\b(?:of|the|and|in)\b', '', data['country']).strip()
                    logger.debug(f"🌍 Country extrait (fallback): {data['country']}")
            
            if code and data['country']:
                data['promoter'] = f"UNDP-{code} - {data['country']}"
                logger.debug(f"🏢 Promoteur: {data['promoter']}")
            elif code:
                data['promoter'] = f"UNDP-{code}"
                logger.warning(f"⚠️ Country non trouvé, promoteur partiel: {data['promoter']}")
            
            # Process
            process_match = re.search(r'PROCUREMENT PROCESS\s*([^\n]+)', content_text, re.IGNORECASE)
            if process_match:
                data['process'] = process_match.group(1).strip()
                logger.debug(f"⚙️ Processus: {data['process']}")
            
            # Nature
            nature_fr = "Privé"
            if data['process']:
                process_lower = data['process'].lower()
                if 'ppp' in process_lower:
                    nature_fr = "PPP"
                elif 'rfp' in process_lower or 'rfq' in process_lower or 'eoi' in process_lower:
                    nature_fr = "Privé"
                else:
                    nature_fr = "Autres"
                logger.debug(f"📋 Nature: {nature_fr}")
            data['nature'] = nature_fr
            data['nature_display'] = nature_fr
            
            # Deadline
            deadline_pattern = r'DEADLINE\s*(\d{1,2}-[A-Za-z]{3}-\d{2}\s*(?:@\s*\d{1,2}:\d{2}\s*(?:AM|PM))?)'
            deadline_match = re.search(deadline_pattern, content_text, re.IGNORECASE)
            if deadline_match:
                data['deadline'] = deadline_match.group(1).strip()
                logger.debug(f"⏰ Deadline: {data['deadline']}")
            else:
                deadline_match_fallback = re.search(r'DEADLINE\s*([^\n]+)', content_text, re.IGNORECASE)
                if deadline_match_fallback:
                    data['deadline'] = deadline_match_fallback.group(1).strip()
                    logger.debug(f"⏰ Deadline (fallback): {data['deadline']}")
            
            # Published date
            published_pattern = r'PUBLISHED ON\s*(\d{1,2}-[A-Za-z]{3}-\d{2}\s*(?:@\s*\d{1,2}:\d{2}\s*(?:AM|PM))?)'
            published_match = re.search(published_pattern, content_text, re.IGNORECASE)
            if published_match:
                data['posted'] = published_match.group(1).strip()
                logger.debug(f"📅 Date publication: {data['posted']}")
            else:
                published_match_fallback = re.search(r'PUBLISHED ON\s*([^\n]+)', content_text, re.IGNORECASE)
                if published_match_fallback:
                    data['posted'] = published_match_fallback.group(1).strip()
                    logger.debug(f"📅 Date publication (fallback): {data['posted']}")
            
            # Tables fallback
            if not all([data['process'], data['deadline'], data['posted']]):
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            if 'process' in label and not data['process']:
                                data['process'] = value
                            elif 'deadline' in label and not data['deadline']:
                                data['deadline'] = value
                            elif ('published' in label or 'posted' in label) and not data['posted']:
                                data['posted'] = value
            
            # Nettoyer pays
            if data['country'] and not CODE_TO_COUNTRY.get(code, ""):
                data['country'] = ' '.join(data['country'].split())
                data['country'] = re.sub(r'[^A-Z\s]', '', data['country']).strip()
                if len(data['country']) > 50:
                    data['country'] = data['country'][:50]
            
            # PDF
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
            for link in pdf_links:
                href = link.get('href', '')
                if href:
                    if href.startswith('http'):
                        data['pdf_url'] = href
                    else:
                        data['pdf_url'] = urljoin(self.base_url, href)
                    logger.debug(f"📄 PDF: {data['pdf_url']}")
                    break
            
            # Screenshot
            if take_screenshot:
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{data['reference']}.png")
                try:
                    asyncio.run(self.capture_screenshot_async(nego_url, screenshot_path))
                    image_path = self.upload_screenshot(screenshot_path)
                    if image_path:
                        data['image_path'] = image_path
                    else:
                        logger.warning(f"⚠️ Échec upload pour {data['reference']}")
                except Exception as e:
                    logger.error(f"❌ Erreur screenshot/upload pour {data['reference']}: {e}")
                    if os.path.exists(screenshot_path):
                        os.remove(screenshot_path)
            else:
                logger.debug(f"⏭️ Screenshot sauté pour {data['reference']}")
            
            if not data['title']:
                data['title'] = f"UNDP Tender {data['reference']}"
            if not data['process']:
                data['process'] = "Request for Proposal (RFP)"
            
            logger.info(f"✅ Détails extraits pour {data['reference']}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction détails depuis {nego_url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def get_tender_urls_from_page(self, page_num: int) -> List[tuple]:
        try:
            logger.info(f"📄 Récupération des URLs depuis la page {page_num}...")
            url = f"{self.base_url}/index.cfm"
            params = {
                'cur_lang': 'en',
                'page': page_num,
                '_': int(time.time() * 1000)
            }
            
            headers = {
                **self.headers,
                "Referer": f"{self.base_url}/index.cfm",
            }
            
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} pour page {page_num}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            tender_urls = []
            
            no_results = soup.find(text=re.compile(r'No procurement notices|No results', re.I))
            if no_results:
                logger.info(f"ℹ️ Aucun résultat sur la page {page_num}")
                return []
            
            links = soup.find_all('a', href=re.compile(r'view_negotiation\.cfm', re.I))
            for link in links:
                href = link.get('href', '')
                nego_url = urljoin(self.base_url, href)
                
                reference = None
                link_text = link.get_text(strip=True)
                ref_match = re.search(r'UNDP-[A-Z]+-\d+', link_text)
                if ref_match:
                    reference = ref_match.group()
                else:
                    parent = link.find_parent(['tr', 'div', 'td', 'li'])
                    if parent:
                        parent_text = parent.get_text()
                        ref_match = re.search(r'UNDP-[A-Z]+-\d+', parent_text)
                        if ref_match:
                            reference = ref_match.group()
                
                if not reference:
                    parsed = urlparse(nego_url)
                    query_params = parse_qs(parsed.query)
                    nego_id = query_params.get('nego_id', [None])[0]
                    if nego_id:
                        reference = f"UNDP-TMP-{nego_id}"
                    else:
                        reference = f"UNDP-UNK-{int(time.time())}"
                
                tender_urls.append((nego_url, reference))
            
            tender_urls = list(dict.fromkeys(tender_urls))
            logger.info(f"✅ {len(tender_urls)} URLs trouvés sur la page {page_num}")
            return tender_urls
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération URLs page {page_num}: {e}")
            return []

    def scraper_offres_pnud(self, date_debut: str = None, date_fin: str = None) -> List[OffrePNUD]:
        tenders = []
        start_date = None
        end_date = None
        
        if date_debut:
            try:
                start_date = datetime.strptime(date_debut, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"⚠️ Date début invalide: {date_debut}")
        
        if date_fin:
            try:
                end_date = datetime.strptime(date_fin, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"⚠️ Date fin invalide: {date_fin}")
        
        take_screenshots = date_debut is not None or date_fin is not None
        if take_screenshots:
            logger.info(f"📸 Screenshots activés")
        else:
            logger.info("⏭️ Screenshots désactivés")
        
        page = 1
        processed_refs = set()
        max_pages = 3
        
        while page <= max_pages:
            try:
                logger.info(f"📖 Traitement de la page {page}/{max_pages}...")
                tender_urls = self.get_tender_urls_from_page(page)
                
                if not tender_urls:
                    logger.info(f"🏁 Aucun URL sur la page {page}")
                    break
                
                for idx, (nego_url, temp_ref) in enumerate(tender_urls, 1):
                    try:
                        if temp_ref in processed_refs or temp_ref in self.existing_offres_set:
                            logger.debug(f"⏭️ {temp_ref} déjà traité")
                            continue
                        
                        logger.info(f"🔄 [{idx}/{len(tender_urls)}] Traitement de {temp_ref}...")
                        
                        details = self.extract_tender_details_from_url(nego_url, temp_ref, take_screenshot=False)
                        if not details:
                            logger.warning(f"⚠️ Impossible d'extraire {temp_ref}")
                            continue
                        
                        reference = details['reference']
                        
                        if reference in processed_refs or reference in self.existing_offres_set:
                            logger.debug(f"⏭️ {reference} déjà traité")
                            continue
                        
                        processed_refs.add(reference)
                        
                        # Filtrer par date
                        if details['posted'] and start_date:
                            try:
                                posted_date_str = details['posted'].strip().split('@')[0].strip()
                                posted_date = datetime.strptime(posted_date_str, "%d-%b-%y").date()
                                if posted_date < start_date:
                                    logger.info(f"⏰ {reference} ignoré: date {posted_date} avant {start_date}")
                                    continue
                                if end_date and posted_date > end_date:
                                    logger.info(f"⏰ {reference} ignoré: date {posted_date} après {end_date}")
                                    continue
                            except Exception as e:
                                logger.warning(f"⚠️ Erreur parsing date pour {reference}: {e}")
                        
                        # Screenshot après filtrage
                        if take_screenshots:
                            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{reference}.png")
                            try:
                                asyncio.run(self.capture_screenshot_async(nego_url, screenshot_path))
                                image_path = self.upload_screenshot(screenshot_path)
                                if image_path:
                                    details['image_path'] = image_path
                                else:
                                    logger.warning(f"⚠️ Échec upload pour {reference}")
                            except Exception as e:
                                logger.error(f"❌ Erreur screenshot/upload pour {reference}: {e}")
                                if os.path.exists(screenshot_path):
                                    os.remove(screenshot_path)
                        
                        # Mapping pays
                        country_id = None
                        if details['country']:
                            clean_country = details['country'].strip().upper()
                            country_id = COUNTRY_MAPPING.get(clean_country)
                            if not country_id:
                                for country_name, cid in COUNTRY_MAPPING.items():
                                    if country_name in clean_country or clean_country in country_name:
                                        country_id = cid
                                        logger.info(f"🔍 Pays '{clean_country}' mappé à '{country_name}' (ID: {country_id})")
                                        break
                            if not country_id:
                                logger.warning(f"⚠️ Pays '{clean_country}' non trouvé dans mapping")
                        
                        # ✅ TRADUCTION AUTOMATIQUE (Italien/Anglais/Espagnol/etc. → Français)
                        description_fr = self.translate_to_french(details['title'])
                        
                        if not description_fr or len(description_fr.strip()) < 10:
                            logger.warning(f"⚠️ Traduction FR invalide pour {reference}, utilisation titre nettoyé")
                            description_fr = self.clean_text_for_translation(details['title'])
                            if not description_fr or len(description_fr) < 10:
                                description_fr = details['title']
                        
                        # Créer offre
                        publication_date = self.normaliser_date_api(details['posted'] or 'N/A')
                        nature_en = map_nature_to_english(details['nature'])

                        # ⚠️ VÉRIFICATION: Date de publication doit être valide
                        # Ignorer les offres avec dates invalides, vides ou N/A
                        dates_valides = (
                            publication_date not in ['N/A', '', None, 'None'] and
                            len(str(publication_date).strip()) > 1 and
                            publication_date != '-- / -- / ----'
                        )

                        if not dates_valides:
                            logger.warning(f"⛔ {reference} ignoré: Date de publication invalide ({publication_date})")
                            continue

                        # ✅ Date valide: publicationDate = startBiddingDate (toujours égales pour PNUD)
                        logger.info(f"✅ Dates valides pour {reference}: Publication = Lancement = {publication_date}")

                        offre = OffrePNUD(
                            reference=reference,
                            description=details['title'],
                            description_fr=description_fr,  # ✅ TOUJOURS EN FRANÇAIS
                            publicationDate=publication_date,
                            startBiddingDate=publication_date,  # ✅ Toujours égale à publicationDate
                            expirationDate=self.normaliser_date_api(details['deadline'] or 'N/A'),
                            promoter=details['promoter'],
                            country=details['country'],
                            country_id=country_id,
                            process=details['process'],
                            nature=nature_en,
                            nature_display=details['nature'],
                            pdfUrl=details['pdf_url'],
                            externalUrl=nego_url,
                            sourceId=self.default_source_id,
                            image_path=details['image_path']
                        )

                        # Valider les données
                        is_valid, error_msg = self.validate_tender_data(offre)
                        if not is_valid:
                            logger.error(f"❌ {reference} données invalides: {error_msg}")
                            continue
                        
                        self.save_to_pending(offre)
                        tenders.append(offre)
                        
                        # Logs
                        logger.info(f"✅ {reference} extrait avec succès")
                        logger.info(f"📌 Titre (original): {details['title'][:60]}...")
                        logger.info(f"📌 Titre (FR auto-traduit): {description_fr[:60]}...")
                        logger.info(f"🏢 Promoteur: {details['promoter']}")
                        logger.info(f"🌍 Pays: {details['country']} (ID: {country_id})")
                        logger.info(f"📋 Nature: {details['nature']} | API: {nature_en}")
                        logger.info(f"📅 Publié: {self.format_date_for_display(details['posted'] or 'N/A')}")
                        logger.info(f"⏰ Deadline: {self.format_date_for_display(details['deadline'] or 'N/A')}")
                        logger.info(f"📄 PDF: {'✓' if details['pdf_url'] else '✗'}")
                        logger.info(f"📸 Image: {'✓ ' + details['image_path'] if details['image_path'] else '✗'}")
                        logger.info(f"🔗 URL: {nego_url}\n")
                        
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur traitement {temp_ref}: {e}")
                        continue
                
                page += 1
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Erreur scraping page {page}: {e}")
                break
        
        # Sauvegarder Excel
        if tenders:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            xls_file = os.path.join(EXCEL_DIR, f"undp_tenders_{timestamp}.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "UNDP Tenders"
            
            headers = ['Référence', 'Titre Original', 'Titre FR (Auto-traduit)', 'Date Publication', 'Date Soumission', 'Date Limite',
                       'Promoteur', 'Pays', 'Pays ID', 'Processus', 'Nature (UI/FR)', 'Nature (DB/EN)',
                       'PDF URL', 'Page URL', 'Source ID', 'Image Path']
            ws.append(headers)
            
            for tender in tenders:
                ws.append([
                    tender.reference,
                    tender.description,
                    tender.description_fr,  # ✅ FRANÇAIS
                    self.format_date_for_display(tender.publicationDate),
                    self.format_date_for_display(tender.startBiddingDate),
                    self.format_date_for_display(tender.expirationDate),
                    tender.promoter,
                    tender.country,
                    tender.country_id,
                    tender.process,
                    tender.nature_display,
                    tender.nature,
                    tender.pdfUrl if tender.pdfUrl else "",
                    tender.externalUrl if tender.externalUrl else "",
                    tender.sourceId,
                    tender.image_path if tender.image_path else ""
                ])
            
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            wb.save(xls_file)
            logger.info(f"💾 EXCEL sauvegardé: {xls_file}")
        
        logger.info(f"📊 Total tenders extraits: {len(tenders)}")
        return tenders

    @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(2))
    def post_tender_to_database(self, offre: OffrePNUD):
        """Post tender avec validation"""
        is_valid, error_msg = self.validate_tender_data(offre)
        if not is_valid:
            logger.error(f"❌ Impossible de poster {offre.reference}: {error_msg}")
            return False
        
        if not self.get_api_token():
            logger.error(f"❌ Impossible de poster {offre.reference}: échec authentification")
            return False
        
        promoter_id = self.find_or_create_promoter(offre.promoter)
        if promoter_id is None:
            logger.error(f"❌ Impossible de poster {offre.reference}: échec promoteur")
            return False
        
        avis_id = int(offre.avisId)
        addresses = [{"countryId": offre.country_id}] if offre.country_id else [{"countryId": 226}]
        batches = [{"activitiesIds": [], "title": offre.description_fr[:100], "deposit": "0"}]
        
        tender_data = {
            "sourceId": int(offre.sourceId),
            "avisId": avis_id,
            "reference": offre.reference,
            "description": offre.description_fr,  # ✅ FRANÇAIS
            "description_fr": offre.description_fr,  # ✅ FRANÇAIS
            "publicationDate": offre.publicationDate,
            "startBiddingDate": offre.startBiddingDate,
            "expirationDate": offre.expirationDate,
            "promoterId": promoter_id,
            "type": offre.category,
            "nature": offre.nature,
            "isMultiCurrency": False,
            "fundingSourceType": "international",
            "addresses": addresses,
            "batches": batches,
            "images": [offre.image_path] if offre.image_path else [],
            "pdfUrl": offre.pdfUrl if offre.pdfUrl else None,
            "externalUrl": offre.externalUrl if offre.externalUrl else None,
            "montant": offre.montant if offre.montant else None,
            "country": offre.country if offre.country else "",
            "process": offre.process if offre.process else "Request for Proposal (RFP)",
            "specificationsReceivingAddress": offre.externalUrl if offre.externalUrl else "URL non disponible"
        }
        
        tender_data = {k: v for k, v in tender_data.items() if v is not None and v != ""}
        
        try:
            post_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            
            response = self.session_appeloffres.post(
                TENDER_ENDPOINT,
                json=tender_data,
                headers=post_headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Offre {offre.reference} postée avec succès")
                if self.mongo_connected:
                    self.tenders_collection.insert_one(asdict(offre))
                    self.pending_tenders_collection.delete_one({"reference": offre.reference})
                    self.existing_offres_set.add(offre.reference)
                    logger.info(f"💾 {offre.reference} sauvegardé dans MongoDB")
                return True
            else:
                logger.error(f"❌ Échec post {offre.reference}: {response.status_code}")
                try:
                    error_detail = response.json()
                    logger.error(f"❌ Détails erreur: {error_detail}")
                except:
                    logger.error(f"❌ Réponse: {response.text[:500]}")
                return False
        except Exception as e:
            logger.error(f"❌ Erreur post {offre.reference}: {e}")
            raise

    def close(self):
        self.session.close()
        self.session_appeloffres.close()
        if self.mongo_connected and self.mongo_client:
            self.mongo_client.close()
        logger.info("🔒 Sessions fermées")

# ============================================================================
# FLASK API - SECTION COMPLÈTE
# ============================================================================
app = Flask(__name__)
CORS(app)

scraper = PNUDScraper()

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Endpoint pour lancer le scraping"""
    try:
        data = request.json or {}
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        
        logger.info(f"🚀 Démarrage scraping PNUD (du {date_debut or 'début'} au {date_fin or 'fin'})")
        tenders = scraper.scraper_offres_pnud(date_debut, date_fin)
        
        return jsonify({
            "status": "success",
            "tenders_scraped": len(tenders),
            "message": f"{len(tenders)} offres ajoutées en attente",
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur lors du scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/pending_tenders', methods=['GET'])
def get_pending_tenders():
    """Récupère les offres en attente avec pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit
        
        if not scraper.mongo_connected:
            return jsonify({"status": "error", "message": "MongoDB non connecté"}), 500
        
        total = scraper.pending_tenders_collection.count_documents({})
        cursor = scraper.pending_tenders_collection.find({}).sort("fetchedAt", -1).skip(skip).limit(limit)
        raw_tenders = list(cursor)
        tenders = serialize_tenders(raw_tenders)
        
        total_pages = math.ceil(total / limit) if limit > 0 else 0
        
        return jsonify({
            "status": "success",
            "tenders": tenders,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": total_pages
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur récupération pending: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/tenders', methods=['GET'])
def get_tenders():
    """Récupère les tenders validés"""
    try:
        if not scraper.mongo_connected:
            return jsonify({"status": "error", "message": "MongoDB non connecté"}), 500
        
        cursor = scraper.tenders_collection.find({}).sort("fetchedAt", -1).limit(50)
        raw_tenders = list(cursor)
        tenders = serialize_tenders(raw_tenders)
        
        return jsonify({
            "status": "success",
            "tenders": tenders,
            "count": len(tenders)
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur récupération tenders: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_tender(reference):
    """Valide une offre en attente"""
    try:
        if not scraper.mongo_connected:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500
        
        pending_doc = scraper.pending_tenders_collection.find_one({"reference": reference})
        if not pending_doc:
            return jsonify({"success": False, "message": "Offre non trouvée en attente"}), 404
        
        pending_doc.pop('_id', None)
        
        if isinstance(pending_doc.get('avisId'), str):
            pending_doc['avisId'] = int(pending_doc['avisId'])
        if isinstance(pending_doc.get('sourceId'), str):
            pending_doc['sourceId'] = int(pending_doc['sourceId'])
        
        if 'nature_display' not in pending_doc:
            pending_doc['nature_display'] = map_nature_to_french(pending_doc.get('nature', 'private'))
        
        # ✅ Re-traduire si description FR invalide
        if not pending_doc.get('description_fr') or len(pending_doc['description_fr'].strip()) < 10:
            logger.warning(f"⚠️ Description FR invalide pour {reference}, re-traduction...")
            if pending_doc.get('description'):
                pending_doc['description_fr'] = scraper.translate_to_french(pending_doc['description'])
            else:
                return jsonify({"success": False, "message": "Description manquante, impossible de valider"}), 400
        
        offre = OffrePNUD(**pending_doc)
        
        is_valid, error_msg = scraper.validate_tender_data(offre)
        if not is_valid:
            return jsonify({"success": False, "message": f"Données invalides: {error_msg}"}), 400
        
        if scraper.post_tender_to_database(offre):
            return jsonify({"success": True, "message": "Offre validée et postée avec succès"})
        else:
            return jsonify({"success": False, "message": "Erreur lors du post vers l'API externe"}), 500
    except Exception as e:
        logger.error(f"❌ Erreur validation {reference}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/update/<reference>', methods=['POST'])
def update_tender(reference):
    """Met à jour une offre en attente"""
    try:
        if not scraper.mongo_connected:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500
        
        data = request.json or {}
        country_id = data.get('country_id')
        
        if country_id is None:
            return jsonify({"success": False, "message": "country_id requis"}), 400
        
        result = scraper.pending_tenders_collection.update_one(
            {"reference": reference},
            {"$set": {"country_id": int(country_id)}}
        )
        
        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Pays mis à jour avec succès"})
        else:
            return jsonify({"success": False, "message": "Offre non trouvée ou inchangée"}), 404
    except Exception as e:
        logger.error(f"❌ Erreur mise à jour {reference}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete_tender(reference):
    """Supprime une offre en attente"""
    try:
        if not scraper.mongo_connected:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500

        result = scraper.pending_tenders_collection.delete_one({"reference": reference})

        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Offre supprimée avec succès"})
        else:
            return jsonify({"success": False, "message": "Offre non trouvée"}), 404
    except Exception as e:
        logger.error(f"❌ Erreur suppression {reference}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete_all', methods=['DELETE', 'POST'])
def delete_all_tenders():
    """Supprime toutes les offres en attente"""
    try:
        if not scraper.mongo_connected:
            return jsonify({"success": False, "message": "MongoDB non connecté"}), 500

        result = scraper.pending_tenders_collection.delete_many({})

        logger.info(f"🗑️ {result.deleted_count} offres supprimées")
        return jsonify({
            "success": True,
            "message": f"{result.deleted_count} offres supprimées avec succès",
            "deleted_count": result.deleted_count
        })
    except Exception as e:
        logger.error(f"❌ Erreur suppression toutes offres: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/post_pending', methods=['POST'])
def post_pending_tenders():
    """Poste toutes les offres en attente"""
    try:
        posted_count = 0
        failed_count = 0
        
        if not scraper.mongo_connected:
            return jsonify({"status": "error", "message": "MongoDB non connecté"}), 500
        
        pending_docs = list(scraper.pending_tenders_collection.find({}))
        logger.info(f"📦 {len(pending_docs)} offres en attente à poster")
        
        for doc in pending_docs:
            try:
                doc.pop('_id', None)
                
                if isinstance(doc.get('avisId'), str):
                    doc['avisId'] = int(doc['avisId'])
                if isinstance(doc.get('sourceId'), str):
                    doc['sourceId'] = int(doc['sourceId'])
                
                if 'nature_display' not in doc:
                    doc['nature_display'] = map_nature_to_french(doc.get('nature', 'private'))
                
                # ✅ Re-traduire si description FR invalide
                if not doc.get('description_fr') or len(doc['description_fr'].strip()) < 10:
                    logger.warning(f"⚠️ Description FR invalide pour {doc.get('reference', 'unknown')}, re-traduction...")
                    if doc.get('description'):
                        doc['description_fr'] = scraper.translate_to_french(doc['description'])
                    else:
                        logger.error(f"❌ Pas de description pour {doc.get('reference', 'unknown')}, skip")
                        failed_count += 1
                        continue
                
                offre = OffrePNUD(**doc)
                
                is_valid, error_msg = scraper.validate_tender_data(offre)
                if not is_valid:
                    logger.error(f"❌ Données invalides pour {offre.reference}: {error_msg}")
                    failed_count += 1
                    continue
                
                if scraper.post_tender_to_database(offre):
                    posted_count += 1
                    logger.info(f"✅ [{posted_count}] {offre.reference} posté")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ [{failed_count}] {offre.reference} échec")
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"❌ Erreur post {doc.get('reference', 'unknown')}: {e}")
                failed_count += 1
        
        remaining = scraper.pending_tenders_collection.count_documents({})
        
        return jsonify({
            "status": "success",
            "posted": posted_count,
            "failed": failed_count,
            "remaining": remaining,
            "message": f"{posted_count} offres postées, {failed_count} échecs, {remaining} restantes"
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur post pending: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérifie l'état du service"""
    try:
        pending_count = scraper.pending_tenders_collection.count_documents({}) if scraper.mongo_connected else 0
        validated_count = scraper.tenders_collection.count_documents({}) if scraper.mongo_connected else 0
        last_login_str = scraper.last_login_time.strftime('%Y-%m-%d %H:%M:%S UTC') if scraper.last_login_time else 'None'
        
        return jsonify({
            "status": "healthy",
            "mongodb_connected": scraper.mongo_connected,
            "existing_tenders": len(scraper.existing_offres_set),
            "pending_tenders": pending_count,
            "validated_tenders": validated_count,
            "last_login_time": last_login_str,
            "token_valid_24h": (datetime.now(timezone.utc) - scraper.last_login_time).total_seconds() <= 86400 if scraper.last_login_time else False,
            "promoters_cached": len(scraper.promoters_cache),
            "translator_available": scraper.translator is not None,
            "supported_languages": "IT, EN, ES, DE, PT, NL, RU, AR, ZH, JA, FR, etc. (100+ langues) → FR",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur health check: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/export_promoters', methods=['GET'])
def export_promoters():
    """Exporte promoteurs en XLS"""
    try:
        filename = os.path.join(EXCEL_DIR, f"all_promoters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        scraper.export_promoters_to_xls(filename)
        return jsonify({"status": "success", "file": filename}), 200
    except Exception as e:
        logger.error(f"❌ Erreur export promoteurs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "UNDP Procurement Scraper",
        "version": "8.0 - Traduction Multi-langues → Français",
        "description": "Scraper UNDP avec traduction automatique de TOUTES les langues vers le français",
        "endpoints": {
            "POST /api/scrape": "Lance le scraping (body: {date_debut: 'YYYY-MM-DD', date_fin: 'YYYY-MM-DD'})",
            "GET /api/pending_tenders?page=1&limit=10": "Liste paginée des offres en attente",
            "GET /api/tenders": "Liste des tenders validés",
            "POST /api/validate/<reference>": "Valide et poste une offre spécifique",
            "POST /api/update/<reference>": "Met à jour une offre (body: {country_id: int})",
            "DELETE /api/delete/<reference>": "Supprime une offre en attente",
            "POST /api/post_pending": "Poste toutes les offres en attente vers l'API",
            "GET /api/health": "État du service",
            "GET /api/export_promoters": "Exporte tous promoteurs en XLS"
        },
        "features": [
            "✅ TRADUCTION AUTOMATIQUE multi-langues → Français",
            "✅ Détection auto de la langue source (Italien, Anglais, Espagnol, Allemand, etc.)",
            "✅ Support de 100+ langues (IT, EN, ES, DE, PT, NL, RU, AR, ZH, JA, etc.)",
            "✅ Nettoyage automatique des références avant traduction",
            "✅ Description TOUJOURS en français propre et correcte",
            "✅ Validation des données avant envoi API",
            "✅ Toutes les fonctionnalités précédentes conservées"
        ],
        "translation_info": {
            "method": "Auto-détection de langue avec Google Translate",
            "source_languages": "Toutes langues supportées par Google Translate",
            "target_language": "Français (FR)",
            "examples": {
                "Italien": "Fornitura di materiale → Fourniture de matériel.",
                "Anglais": "Supply of equipment → Fourniture d'équipement.",
                "Espagnol": "Suministro de material → Fourniture de matériel.",
                "Allemand": "Lieferung von Material → Fourniture de matériel."
            }
        }
    })

if __name__ == "__main__":
    try:
        logger.info("="*80)
        logger.info("🚀 DÉMARRAGE DU SCRAPER UNDP - VERSION 8.0")
        logger.info("="*80)
        logger.info(f"📡 API Base URL: {API_BASE_URL}")
        logger.info(f"🗄️ MongoDB: {'✅ Connecté' if scraper.mongo_connected else '❌ Non connecté'}")
        logger.info(f"📦 Offres existantes: {len(scraper.existing_offres_set)}")
        
        pending_count = scraper.pending_tenders_collection.count_documents({}) if scraper.mongo_connected else 0
        logger.info(f"⏳ Offres en attente: {pending_count}")
        logger.info(f"🏢 Promoteurs cachés: {len(scraper.promoters_cache)}")
        logger.info(f"🌐 Traducteur: {'✅ Disponible (multi-langues → FR)' if scraper.translator else '❌ Non disponible'}")
        logger.info("="*80)
        logger.info("✅ FONCTIONNALITÉS:")
        logger.info("   - Auto-détection de TOUTES les langues")
        logger.info("   - Traduction automatique → Français")
        logger.info("   - Italien → Français")
        logger.info("   - Anglais → Français")
        logger.info("   - Espagnol → Français")
        logger.info("   - Allemand → Français")
        logger.info("   - Et 100+ autres langues...")
        logger.info("   - Nettoyage références et numéros")
        logger.info("   - Description FR propre sans codes")
        logger.info("="*80 + "\n")
        
        app.run(debug=False, host='0.0.0.0', port=5006, threaded=True)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Arrêt du serveur demandé")
    finally:
        scraper.close()
        logger.info("👋 Serveur arrêté proprement")