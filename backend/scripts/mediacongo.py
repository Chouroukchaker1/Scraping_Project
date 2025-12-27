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
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
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

# PostgreSQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_mediacongo"

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

# PostgreSQL connection helper
def get_db_connection():
    """Retourne une connexion PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# Test connection
try:
    conn = get_db_connection()
    conn.close()
    logger.info(f"✅ PostgreSQL connecté: {DB_NAME} (Table: {TABLE_NAME})")
except Exception as e:
    logger.error(f"❌ ERREUR PostgreSQL: {e}")

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
    """Convert PostgreSQL row to dict (already handled by RealDictCursor)"""
    if not doc:
        return doc
    if isinstance(doc, dict):
        # Convert id to string for consistency with frontend
        doc = doc.copy()
        if 'id' in doc:
            doc['_id'] = str(doc['id'])
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
        """Charge les références existantes depuis PostgreSQL"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Charger toutes les références existantes
            cursor.execute(f"SELECT reference FROM {TABLE_NAME}")
            for row in cursor.fetchall():
                if row[0]:
                    self.existing_offres_set.add(row[0])

            cursor.close()
            conn.close()

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
        """Scrape jobs from MediaCongo website (HTML scraping with pagination)"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")

            logger.info(f"🔍 Scraping MediaCongo website: {start_date} → {end_date}")

            offres = []
            count = 0

            # Boucle sur toutes les pages de pagination
            for page_num in range(1, 10):  # Max 10 pages pour éviter boucle infinie
                # URL de la page
                if page_num == 1:
                    web_url = "https://www.mediacongo.net/emplois.html"
                else:
                    web_url = f"https://www.mediacongo.net/emplois-search--tri-offres_recentes-page-{page_num}.html"

                logger.info(f"📄 Page {page_num}: {web_url}")

                try:
                    response = self.session.get(web_url, timeout=30)

                    if response.status_code != 200:
                        logger.warning(f"⚠️ Page {page_num}: Error {response.status_code}")
                        break  # Arrêter la pagination

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Trouver la table des offres d'emploi
                    table = soup.find('table')
                    if not table:
                        logger.warning(f"⚠️ Page {page_num}: Aucune table trouvée")
                        break  # Arrêter la pagination

                    # Extraire les lignes (rows) - ignorer la première ligne qui est le header
                    rows = table.find_all('tr')[1:]  # Skip header row

                    if len(rows) == 0:
                        logger.info(f"✅ Page {page_num}: Aucune offre (fin de pagination)")
                        break  # Arrêter la pagination

                    logger.info(f"✅ Page {page_num}: {len(rows)} offres trouvées")

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

                    # Si on a atteint la limite, arrêter la pagination
                    if count >= limit:
                        logger.info(f"✅ Limite de {limit} offres atteinte, arrêt pagination")
                        break

                except Exception as e:
                    logger.error(f"❌ Page {page_num}: Erreur scraping: {e}")
                    continue  # Passer à la page suivante

            logger.info(f"✅ {len(offres)} offres extraites avec succès sur {page_num} pages")
            return offres

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
        """Save offer to PostgreSQL"""
        try:
            logger.info(f"DEBUG: Tentative sauvegarde {offre.reference}")

            if offre.reference in self.existing_offres_set:
                logger.info(f"⏭️ Doublon: {offre.reference}")
                return False

            conn = get_db_connection()
            cursor = conn.cursor()

            tender_dict = offre.to_dict()

            # Insert dans PostgreSQL
            query = f"""
                INSERT INTO {TABLE_NAME}
                (reference, description, description_fr, publication_date, start_bidding_date,
                 expiration_date, promoter, source_id, avis_id, external_url, montant,
                 category, country, nature, status, created_at, updated_at, fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reference) DO NOTHING
            """

            cursor.execute(query, (
                tender_dict.get('reference'),
                tender_dict.get('description'),
                tender_dict.get('description_fr'),
                tender_dict.get('publicationDate'),
                tender_dict.get('startBiddingDate'),
                tender_dict.get('expirationDate'),
                tender_dict.get('promoter'),
                tender_dict.get('sourceId'),
                tender_dict.get('avisId'),
                tender_dict.get('externalUrl'),
                tender_dict.get('montant'),
                tender_dict.get('category'),
                tender_dict.get('country'),
                tender_dict.get('nature'),
                tender_dict.get('status', 'pending'),
                tender_dict.get('createdAt'),
                tender_dict.get('updatedAt'),
                tender_dict.get('fetchedAt')
            ))

            inserted = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()

            if inserted:
                self.existing_offres_set.add(offre.reference)
                logger.info(f"💾 Sauvegardé: {offre.reference}")
                return True
            else:
                logger.debug(f"⏭️ Déjà existant (ON CONFLICT): {offre.reference}")
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
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if already validated
            cursor.execute(f"SELECT id FROM {TABLE_NAME} WHERE reference = %s AND status = 'validated'", (offre.reference,))
            existing = cursor.fetchone()
            if existing:
                cursor.close()
                conn.close()
                return {"success": False, "message": "Déjà validée"}

            # Update status to validated
            validation_date = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                f"UPDATE {TABLE_NAME} SET status = %s, validation_date = %s WHERE reference = %s",
                ('validated', validation_date, offre.reference)
            )

            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                return {"success": False, "message": "Offre non trouvée"}

            record_id = cursor.lastrowid
            conn.commit()

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
                        cursor.execute(
                            f"UPDATE {TABLE_NAME} SET api_id = %s WHERE reference = %s",
                            (api_id, offre.reference)
                        )
                        conn.commit()
                        logger.info(f"✅ API OK: {offre.reference} - ID: {api_id}")
                    else:
                        error_detail = f"Status {response.status_code}"
                        logger.error(f"❌ API Error {response.status_code}: {response.text[:500]}")
            except Exception as e:
                error_detail = str(e)[:200]

            cursor.close()
            conn.close()

            message = f"Validée (PostgreSQL + API ID: {api_id})" if api_success else f"Validée PostgreSQL mais échec API: {error_detail}"

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
    try:
        conn = get_db_connection()
        conn.close()
        db_status = "connected"
    except:
        db_status = "disconnected"

    return jsonify({
        "status": "ok",
        "service": "MediaCongo Web Scraper",
        "database": db_status
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
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Count total
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = 'pending'")
        total = cursor.fetchone()['count']

        # Get paginated results
        cursor.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE status = 'pending' ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        offres = cursor.fetchall()

        cursor.close()
        conn.close()

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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE reference = %s AND status = 'pending'", (reference,))
        pending_doc = cursor.fetchone()

        cursor.close()
        conn.close()

        if not pending_doc:
            return jsonify({"success": False, "message": "Offre non trouvée"}), 404

        # Convert snake_case to camelCase for dataclass
        offre_dict = {
            'reference': pending_doc.get('reference'),
            'description': pending_doc.get('description'),
            'description_fr': pending_doc.get('description_fr'),
            'publicationDate': pending_doc.get('publication_date'),
            'startBiddingDate': pending_doc.get('start_bidding_date'),
            'expirationDate': pending_doc.get('expiration_date'),
            'promoter': pending_doc.get('promoter'),
            'sourceId': pending_doc.get('source_id'),
            'avisId': pending_doc.get('avis_id'),
            'externalUrl': pending_doc.get('external_url'),
            'montant': pending_doc.get('montant'),
            'category': pending_doc.get('category'),
            'country': pending_doc.get('country'),
            'nature': pending_doc.get('nature'),
        }

        offre = OffreMediaCongo(**offre_dict)
        result = scraper.post_tender_to_database(offre)

        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Erreur validation: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<path:reference>', methods=['DELETE'])
def delete_offre(reference):
    """Delete a pending offer"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        deleted_count = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        if deleted_count > 0:
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
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE status = 'pending'")
        deleted_count = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        scraper.existing_offres_set.clear()
        scraper._load_existing_offres()

        return jsonify({
            "success": True,
            "message": f"{deleted_count} offres supprimées",
            "count": deleted_count
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
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Count total
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = 'validated'")
        total = cursor.fetchone()['count']

        # Get paginated results
        cursor.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE status = 'validated' ORDER BY validation_date DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        offres = cursor.fetchall()

        cursor.close()
        conn.close()

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
