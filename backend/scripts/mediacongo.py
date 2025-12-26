# mediacongo.py - Scraper MediaCongo pour opportunités et emplois RDC
import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
import tenacity
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

# Load environment variables
load_dotenv()

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_mediacongo.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tunip")
DB_NAME = os.getenv("DB_NAME", "tunip")
COLLECTION_NAME = os.getenv("MEDIACONGO_COLLECTION_NAME", "tenders_mediacongo")
PENDING_COLLECTION_NAME = os.getenv("MEDIACONGO_PENDING_COLLECTION_NAME", "pending_tenders_mediacongo")

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"

# MediaCongo utilise le compte Oumayma Dahmani
EMAIL = "mariem.bousalem@tunipages.tn"
PASSWORD = "L96BhA6ODugl"

DEFAULT_SOURCE_ID_MEDIACONGO = int(os.getenv("DEFAULT_SOURCE_ID_MEDIACONGO", "337"))
DEFAULT_AVIS_ID = int(os.getenv("DEFAULT_AVIS_ID", "1"))

# Paths
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MongoDB connection
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    db = mongo_client[DB_NAME]
    tenders_collection = db[COLLECTION_NAME]
    pending_tenders_collection = db[PENDING_COLLECTION_NAME]
    logger.info(f"✅ MongoDB connecté: {DB_NAME} (Collections: {COLLECTION_NAME}, {PENDING_COLLECTION_NAME})")
except Exception as e:
    logger.error(f"❌ ERREUR MongoDB: {e}")
    mongo_client = None
    db = None
    tenders_collection = None
    pending_tenders_collection = None

@dataclass
class OffreMediaCongo:
    reference: str
    description: str
    description_fr: str
    publicationDate: str
    startBiddingDate: str
    expirationDate: str
    promoter: str
    sourceId: int
    avisId: int = DEFAULT_AVIS_ID
    externalUrl: Optional[str] = None
    montant: Optional[str] = None
    fetchedAt: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    category: str = "international"
    country: str = ""
    nature: str = "private"
    createdAt: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"

    def to_dict(self):
        return asdict(self)

def serialize_document(doc):
    if not doc:
        return doc
    doc = doc.copy() if isinstance(doc, dict) else dict(doc)
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc

def serialize_tenders(tenders_list):
    return [serialize_document(t) for t in tenders_list]

class MediaCongoScraper:
    def __init__(self):
        self.base_url = "https://www.mediacongo.net/api/jobs"
        self.web_url = "https://www.mediacongo.net/emplois.html"
        self.session = requests.Session()
        self.session_appeloffres = requests.Session()
        self.appeloffres_headers = {}
        self.existing_offres_set = set()
        self.default_source_id = DEFAULT_SOURCE_ID_MEDIACONGO
        self.promoters_cache: Dict[str, int] = {}

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.session.headers.update(self.headers)

        # Charger les offres existantes
        self._load_existing_offres()

        logger.info("✅ MediaCongoScraper initialisé")

    def _load_existing_offres(self):
        """Charge les références existantes depuis MongoDB"""
        try:
            if pending_tenders_collection is None:
                return

            pending_docs = pending_tenders_collection.find({}, {"reference": 1})
            for doc in pending_docs:
                self.existing_offres_set.add(doc.get("reference"))

            validated_docs = tenders_collection.find({}, {"reference": 1})
            for doc in validated_docs:
                self.existing_offres_set.add(doc.get("reference"))

            logger.info(f"📦 {len(self.existing_offres_set)} offres existantes chargées")
        except Exception as e:
            logger.error(f"❌ Erreur chargement offres: {e}")

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
    def login_appeloffres(self):
        """Login to appeloffres API"""
        try:
            payload = {"email": EMAIL, "password": PASSWORD}
            response = self.session_appeloffres.post(LOGIN_ENDPOINT, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token") or data.get("accessToken") or data.get("token")

                if access_token:
                    self.appeloffres_headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                    logger.info("✅ Connexion API appeloffres réussie")
                    return True

            logger.error(f"❌ Login failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur login: {e}")
            return False

    def get_or_create_promoter(self, promoter_name: str) -> int:
        """Obtenir ou créer un promoteur"""
        if not promoter_name or promoter_name.strip() == "":
            return 223472  # DEFAULT_PROMOTER_ID

        promoter_clean = promoter_name.strip().lower()

        if promoter_clean in self.promoters_cache:
            return self.promoters_cache[promoter_clean]

        if not self.login_appeloffres():
            return 223472

        try:
            # Rechercher le promoteur existant
            search_response = self.session_appeloffres.get(
                f"{PROMOTER_ENDPOINT}?search={promoter_name}",
                headers=self.appeloffres_headers,
                timeout=30
            )

            if search_response.status_code == 200:
                promoters = search_response.json()
                if promoters and len(promoters) > 0:
                    promoter_id = promoters[0].get("id")
                    self.promoters_cache[promoter_clean] = promoter_id
                    logger.info(f"✅ Promoteur trouvé: {promoter_name} (ID: {promoter_id})")
                    return promoter_id

            # Créer nouveau promoteur
            payload = {
                "name": promoter_name,
                "companyName": promoter_name,
                "address": {"countryId": 219}  # RDC (countryId 219)
            }
            create_response = self.session_appeloffres.post(
                PROMOTER_ENDPOINT,
                json=payload,
                headers=self.appeloffres_headers,
                timeout=30
            )

            if create_response.status_code in [200, 201]:
                promoter_id = create_response.json().get("id")
                self.promoters_cache[promoter_clean] = promoter_id
                logger.info(f"✅ Promoteur créé: {promoter_name} (ID: {promoter_id})")
                return promoter_id
            else:
                logger.error(f"❌ Échec création promoteur {promoter_name}: {create_response.status_code} - {create_response.text[:200]}")

            return 223472
        except Exception as e:
            logger.error(f"❌ Erreur promoteur: {e}")
            return 223472

    def scrape_mediacongo_jobs(self, start_date=None, end_date=None, limit=100):
        """Scrape jobs from MediaCongo website (HTML scraping)"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")

            logger.info(f"🔍 Scraping MediaCongo website: {start_date} → {end_date}")

            # Scraping de la page web MediaCongo emplois.html
            web_url = "https://www.mediacongo.net/emplois.html"

            try:
                response = self.session.get(web_url, timeout=30)

                if response.status_code != 200:
                    logger.error(f"❌ Web error: {response.status_code}")
                    return []

                soup = BeautifulSoup(response.text, 'html.parser')

                # Trouver la table des offres d'emploi
                table = soup.find('table')
                if not table:
                    logger.warning("⚠️ Aucune table trouvée sur la page")
                    return []

                # Extraire les lignes (rows) - ignorer la première ligne qui est le header
                rows = table.find_all('tr')[1:]  # Skip header row
                logger.info(f"✅ {len(rows)} offres trouvées dans la table")

                offres = []
                count = 0
                for row in rows:
                    if count >= limit:
                        break

                    try:
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue

                        # Extraire les informations de chaque colonne
                        # Colonne 1: Fonction (titre + ID)
                        titre_cell = cells[1]
                        link_elem = titre_cell.find('a')
                        if not link_elem:
                            continue

                        title = link_elem.find('strong')
                        if not title:
                            continue
                        title = title.get_text(strip=True)

                        # Extraire l'ID (format: OEM42731)
                        id_elem = titre_cell.find('strong', class_='format_id_emploi')
                        job_id = id_elem.get_text(strip=True) if id_elem else f"MC-{count+1}"

                        # Vérifier si déjà extrait
                        if job_id in self.existing_offres_set:
                            continue

                        # Extraire le lien
                        job_url = link_elem.get('href', '')
                        if job_url and not job_url.startswith('http'):
                            job_url = f"https://www.mediacongo.net/{job_url}"

                        # Colonne 2: Organisme (promoter)
                        org_cell = cells[2]
                        promoter = org_cell.get_text(strip=True) or "MediaCongo"

                        # Colonne 3: Lieu (location)
                        lieu_cell = cells[3]
                        country = lieu_cell.get_text(strip=True) or "RDC"

                        # Colonne 4: Date d'insertion
                        date_cell = cells[4]
                        date_str = date_cell.get_text(strip=True)

                        # Parser la date (format: DD.MM.YYYY)
                        pub_date_obj = None
                        try:
                            date_parts = date_str.split('.')
                            if len(date_parts) == 3:
                                pub_date_obj = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]), tzinfo=timezone.utc)
                                pub_date = pub_date_obj.isoformat()
                            else:
                                pub_date_obj = datetime.now(timezone.utc)
                                pub_date = pub_date_obj.isoformat()
                        except:
                            pub_date_obj = datetime.now(timezone.utc)
                            pub_date = pub_date_obj.isoformat()

                        # Filtrer par date si spécifié
                        if start_date and end_date and pub_date_obj:
                            try:
                                start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

                                if not (start_dt <= pub_date_obj < end_dt):
                                    continue  # Skip offres en dehors de la plage de dates
                            except:
                                pass  # Si erreur de parsing, inclure l'offre quand même

                        # Date d'expiration: 30 jours après publication
                        exp_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

                        offre = OffreMediaCongo(
                            reference=job_id,
                            description=title,
                            description_fr=title[:500],
                            publicationDate=pub_date,
                            startBiddingDate=pub_date,
                            expirationDate=exp_date,
                            promoter=promoter,
                            sourceId=self.default_source_id,
                            externalUrl=job_url,
                            country=country,
                        )

                        offres.append(offre)
                        count += 1
                        logger.info(f"  ✓ {job_id}: {title[:60]}... | {promoter}")

                    except Exception as e:
                        logger.debug(f"Erreur extraction offre: {e}")
                        continue

                logger.info(f"✅ {len(offres)} offres extraites avec succès")
                return offres

            except Exception as e:
                logger.error(f"❌ Erreur scraping web: {e}")
                return []

        except Exception as e:
            logger.error(f"❌ Erreur scraping: {e}")
            return []

    def _extract_offre_from_api(self, item):
        """Extract offer from API response"""
        try:
            fields = item.get("fields", {})

            job_id = str(item.get("id", ""))
            if not job_id or job_id in self.existing_offres_set:
                return None

            title = fields.get("title", "Sans titre")
            body_html = fields.get("body", "")

            # Parse HTML body
            soup = BeautifulSoup(body_html, "html.parser")
            description = soup.get_text(separator=" ", strip=True)[:500] if soup else title

            # Dates
            date_created = fields.get("date", {}).get("created", "")
            date_closing = fields.get("date", {}).get("closing", "")

            pub_date = self._parse_date(date_created)
            exp_date = self._parse_date(date_closing)

            # Source
            source_list = fields.get("source", [])
            promoter = source_list[0].get("name", "MediaCongo") if source_list else "MediaCongo"

            # Country
            country_list = fields.get("country", [])
            country = country_list[0].get("name", "") if country_list else ""

            # URL
            external_url = fields.get("url", "")

            offre = OffreMediaCongo(
                reference=job_id,
                description=title,
                description_fr=description,
                publicationDate=pub_date,
                startBiddingDate=pub_date,
                expirationDate=exp_date,
                promoter=promoter,
                sourceId=self.default_source_id,
                externalUrl=external_url,
                country=country,
            )

            return offre

        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            return None

    def _parse_date(self, date_str):
        """Parse date string to ISO format"""
        if not date_str:
            return datetime.now(timezone.utc).isoformat()

        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.isoformat()
        except:
            return datetime.now(timezone.utc).isoformat()

    def save_to_pending(self, offre: OffreMediaCongo):
        """Save offer to pending collection"""
        try:
            logger.info(f"DEBUG: Tentative sauvegarde {offre.reference}")

            if pending_tenders_collection is None:
                logger.error("❌ MongoDB non connecté")
                return False

            logger.info(f"DEBUG: Vérif doublon - ref={offre.reference}, in_set={offre.reference in self.existing_offres_set}, set_size={len(self.existing_offres_set)}")

            if offre.reference in self.existing_offres_set:
                logger.info(f"⏭️ Doublon: {offre.reference}")
                return False

            tender_dict = offre.to_dict()
            result = pending_tenders_collection.insert_one(tender_dict)

            if result.inserted_id:
                self.existing_offres_set.add(offre.reference)
                logger.info(f"💾 Sauvegardé: {offre.reference}")
                return True

            logger.warning(f"⚠️ Pas d'inserted_id pour {offre.reference}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur save {offre.reference}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
    def post_tender_to_database(self, offre: OffreMediaCongo) -> dict:
        """Validate and send to API"""
        try:
            # Check if already validated
            existing = tenders_collection.find_one({"reference": offre.reference})
            if existing:
                return {"success": False, "message": "Déjà validée"}

            # Save to validated collection
            tender_dict = offre.to_dict()
            tender_dict["status"] = "validated"
            tender_dict["validationDate"] = datetime.now(timezone.utc).isoformat()

            result = tenders_collection.insert_one(tender_dict)

            if not result.inserted_id:
                return {"success": False, "message": "Erreur MongoDB"}

            # Delete from pending
            pending_tenders_collection.delete_one({"reference": offre.reference})

            # Send to API
            api_success = False
            api_id = None
            error_detail = ""

            try:
                if not self.login_appeloffres():
                    error_detail = "Échec connexion API"
                else:
                    payload = self._map_offre_to_tender_payload(offre)
                    response = self.session_appeloffres.post(
                        TENDER_ENDPOINT,
                        json=payload,
                        headers=self.appeloffres_headers,
                        timeout=30
                    )

                    if response.status_code in [200, 201]:
                        response_data = response.json()
                        api_id = response_data.get("id")
                        api_success = True
                        tenders_collection.update_one(
                            {"_id": result.inserted_id},
                            {"$set": {"api_id": api_id}}
                        )
                        logger.info(f"✅ API OK: {offre.reference} - ID: {api_id}")
                    else:
                        error_detail = f"Status {response.status_code}"
                        logger.error(f"❌ API Error {response.status_code}: {response.text[:500]}")
            except Exception as e:
                error_detail = str(e)[:200]

            message = f"Validée (MongoDB + API ID: {api_id})" if api_success else f"Validée MongoDB mais échec API: {error_detail}"

            return {
                "success": True,
                "message": message,
                "offre_ref": offre.reference,
                "api_id": api_id,
                "api_success": api_success,
                "api_error": error_detail if not api_success else None
            }

        except Exception as e:
            logger.error(f"❌ Erreur validation: {e}")
            return {"success": False, "message": str(e)}

    def _map_offre_to_tender_payload(self, offre: OffreMediaCongo) -> dict:
        """Map offer to API payload"""
        promoter_id = self.get_or_create_promoter(offre.promoter)

        payload = {
            "title": offre.description[:200],
            "description": offre.description_fr[:500],
            "publicationDate": offre.publicationDate,
            "startBiddingDate": offre.startBiddingDate,
            "expirationDate": offre.expirationDate,
            "reference": offre.reference,
            "avisId": offre.avisId,
            "sourceId": offre.sourceId,
            "promoterId": promoter_id,
            "type": "international",
            "nature": offre.nature,
            "isEnabled": True,
            "specificationsReceivingAddress": offre.externalUrl or "Non disponible",
            "fundingSourceType": "international",
            "currencyId": 4,
            "isMultiCurrency": False,
            "batches": [{
                "activitiesIds": [385],
                "title": offre.description[:80],
                "deposit": 0
            }],
            "addresses": [{"countryId": 219}],
            "images": []  # Champ obligatoire pour l'API
        }

        return {k: v for k, v in payload.items() if v is not None}

# Initialize scraper
scraper = MediaCongoScraper()

# Flask App
app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "MediaCongo Web Scraper",
        "mongodb": "connected" if mongo_client else "disconnected"
    })

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Launch scraping"""
    try:
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        limit = int(data.get('limit', 100))

        logger.info(f"🚀 Lancement scraping: {start_date} → {end_date}")

        offres = scraper.scrape_mediacongo_jobs(start_date, end_date, limit)

        saved = 0
        for offre in offres:
            if scraper.save_to_pending(offre):
                saved += 1

        logger.info(f"✅ {saved}/{len(offres)} offres sauvegardées")

        return jsonify({
            "success": True,
            "message": f"Scraping terminé: {saved} offres ajoutées",
            "total": len(offres),
            "saved": saved
        })

    except Exception as e:
        logger.error(f"❌ Erreur scrape: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Get pending offers"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        skip = (page - 1) * limit

        total = pending_tenders_collection.count_documents({"status": "pending"})
        offres = list(pending_tenders_collection.find({"status": "pending"})
                     .sort("createdAt", -1)
                     .skip(skip)
                     .limit(limit))

        return jsonify({
            "success": True,
            "pending": {
                "offres": serialize_tenders(offres),
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": (total + limit - 1) // limit
            }
        })
    except Exception as e:
        logger.error(f"❌ Erreur pending: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/validate/<path:reference>', methods=['POST'])
def validate_offre(reference):
    """Validate an offer"""
    try:
        pending_doc = pending_tenders_collection.find_one({"reference": reference, "status": "pending"})

        if not pending_doc:
            return jsonify({"success": False, "message": "Offre non trouvée"}), 404

        pending_doc.pop('_id', None)
        offre = OffreMediaCongo(**pending_doc)

        result = scraper.post_tender_to_database(offre)

        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Erreur validation: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<path:reference>', methods=['DELETE'])
def delete_offre(reference):
    """Delete a pending offer"""
    try:
        result = pending_tenders_collection.delete_one({"reference": reference})

        if result.deleted_count > 0:
            scraper.existing_offres_set.discard(reference)
            return jsonify({"success": True, "message": "Offre supprimée"})

        return jsonify({"success": False, "message": "Offre non trouvée"}), 404

    except Exception as e:
        logger.error(f"❌ Erreur delete: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete_all', methods=['POST'])
def delete_all():
    """Delete all pending offers"""
    try:
        result = pending_tenders_collection.delete_many({"status": "pending"})
        scraper.existing_offres_set.clear()
        scraper._load_existing_offres()

        return jsonify({
            "success": True,
            "message": f"{result.deleted_count} offres supprimées",
            "count": result.deleted_count
        })
    except Exception as e:
        logger.error(f"❌ Erreur delete_all: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/validated', methods=['GET'])
def get_validated():
    """Get validated offers"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        skip = (page - 1) * limit

        total = tenders_collection.count_documents({})
        offres = list(tenders_collection.find({})
                     .sort("validationDate", -1)
                     .skip(skip)
                     .limit(limit))

        return jsonify({
            "success": True,
            "validated": {
                "offres": serialize_tenders(offres),
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": (total + limit - 1) // limit
            }
        })
    except Exception as e:
        logger.error(f"❌ Erreur validated: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("=" * 80)
    print("SCRAPER MEDIACONGO - OPPORTUNITÉS ET EMPLOIS RDC")
    print("=" * 80)
    print(f"Source ID: {DEFAULT_SOURCE_ID_MEDIACONGO}")
    print(f"Email: {EMAIL}")
    print(f"API: {API_BASE_URL}")
    print(f"MongoDB: {DB_NAME}")
    print(f"Website: https://www.mediacongo.net/emplois.html")
    print("=" * 80)

    app.run(host='0.0.0.0', port=5016, debug=False)
