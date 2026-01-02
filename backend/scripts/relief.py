# relief.py - Scraper ReliefWeb pour appels d'offres
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
        logging.FileHandler('scraper_relief.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# PostgreSQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_relief"

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"

# Relief utilise le compte Oumayma Dahmani
EMAIL = "oumayma.dahmani@tunipages.tn"
PASSWORD = "Ah0F553KKu0A"

DEFAULT_SOURCE_ID_RELIEF = int(os.getenv("DEFAULT_SOURCE_ID_RELIEF", "1716"))
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
class OffreRelief:
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

class ReliefWebScraper:
    def __init__(self):
        self.base_url = "https://api.reliefweb.int/v1/jobs"
        self.web_url = "https://reliefweb.int/jobs"
        self.session = requests.Session()
        self.session_appeloffres = requests.Session()
        self.appeloffres_headers = {}
        self.existing_offres_set = set()
        self.default_source_id = DEFAULT_SOURCE_ID_RELIEF
        self.promoters_cache: Dict[str, int] = {}

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.session.headers.update(self.headers)

        # Charger les offres existantes
        self._load_existing_offres()

        logger.info("✅ ReliefWebScraper initialisé")

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
                "companyName": promoter_name,  # Requis par l'API
                "address": {
                    "street": "International",
                    "city": "Global",
                    "zipCode": "00000",
                    "country": "International"
                }
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
                logger.error(f"❌ Échec création promoteur {promoter_name}: {create_response.status_code} - {create_response.text[:300]}")

            logger.warning(f"⚠️ Utilisation promoteur par défaut pour {promoter_name}")
            return 223472
        except Exception as e:
            logger.error(f"❌ Erreur promoteur: {e}")
            return 223472

    def scrape_relief_jobs(self, start_date=None, end_date=None, limit=100):
        """Scrape jobs from ReliefWeb website (HTML scraping with pagination)"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")

            logger.info(f"🔍 Scraping ReliefWeb website: {start_date} → {end_date}")
            logger.info("⚠️ Note: API ReliefWeb nécessite un appname approuvé, utilisation du scraping HTML")

            offres = []
            count = 0

            # Boucle sur plusieurs pages de pagination
            for page_num in range(0, 10):  # ReliefWeb utilise ?page=0, ?page=1, etc.
                if count >= limit:
                    break

                web_url = f"https://reliefweb.int/jobs?page={page_num}"
                logger.info(f"📄 Page {page_num + 1}: {web_url}")

                try:
                    response = self.session.get(web_url, timeout=30)

                    if response.status_code != 200:
                        logger.error(f"❌ Web error: {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Extraire les offres de la page
                    job_listings = soup.find_all('article', class_=re.compile(r'.*job.*|.*listing.*'))

                    if not job_listings:
                        # Essayer d'autres sélecteurs
                        job_listings = soup.find_all('div', class_=re.compile(r'.*job.*|.*card.*'))

                    if len(job_listings) == 0:
                        logger.info(f"🛑 Page {page_num + 1} vide - fin de pagination")
                        break

                    logger.info(f"✅ {len(job_listings)} offres trouvées sur page {page_num + 1}")

                    for job in job_listings:
                        if count >= limit:
                            break

                        try:
                            # Extraire le titre depuis h3
                            title_elem = job.find('h3', class_=re.compile(r'.*title.*'))
                            if not title_elem:
                                title_elem = job.find('h3') or job.find('h2')

                            if not title_elem:
                                continue

                            title = title_elem.get_text(strip=True)
                            if not title:
                                continue

                            # Extraire le lien (trouver le lien vers /job/...)
                            job_url = ""
                            job_id = f"relief-{count+1}"

                            # Le lien vers le job est généralement le 2ème lien ou celui contenant /job/
                            all_links = job.find_all('a', href=True)
                            for link in all_links:
                                href = link.get('href', '')
                                if '/job/' in href:
                                    job_url = href if href.startswith('http') else f"https://reliefweb.int{href}"
                                    # Extraire ID du lien (ex: /job/4192721/...)
                                    id_match = re.search(r'/job/(\d+)', job_url)
                                    if id_match:
                                        job_id = id_match.group(1)
                                    break

                            # Vérifier si déjà extrait
                            if job_id in self.existing_offres_set:
                                continue

                            # Extraire organisation
                            org_elem = job.find(class_=re.compile(r'.*source.*'))
                            promoter = org_elem.get_text(strip=True) if org_elem else "ReliefWeb"

                            # Extraire pays
                            country_elem = job.find('p', class_=re.compile(r'.*country.*'))
                            country = country_elem.get_text(strip=True) if country_elem else ""

                            # Extraire les dates réelles
                            pub_date = None
                            exp_date = None

                            # Chercher la date de publication (Posted date)
                            date_posted_elem = job.find('time', class_=re.compile(r'.*date.*posted.*'))
                            if not date_posted_elem:
                                date_posted_elem = job.find('time')
                            if not date_posted_elem:
                                # Chercher dans dd/dt pour "Posted"
                                posted_dt = job.find('dt', string=re.compile(r'Posted', re.I))
                                if posted_dt:
                                    date_posted_elem = posted_dt.find_next_sibling('dd')

                            if date_posted_elem:
                                date_str = date_posted_elem.get('datetime') or date_posted_elem.get_text(strip=True)
                                pub_date = self._parse_date(date_str)

                            # Chercher la date d'expiration (Closing date)
                            date_closing_elem = job.find('time', class_=re.compile(r'.*closing.*'))
                            if not date_closing_elem:
                                # Chercher dans dd/dt pour "Closing"
                                closing_dt = job.find('dt', string=re.compile(r'Closing|Deadline', re.I))
                                if closing_dt:
                                    date_closing_elem = closing_dt.find_next_sibling('dd')

                            if date_closing_elem:
                                date_str = date_closing_elem.get('datetime') or date_closing_elem.get_text(strip=True)
                                exp_date = self._parse_date(date_str)

                            # Fallback si dates non trouvées
                            if not pub_date:
                                pub_date = datetime.now(timezone.utc).isoformat()
                            if not exp_date:
                                exp_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

                            offre = OffreRelief(
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
                            logger.debug(f"✅ Extracted: {job_id} - {title[:50]}")

                        except Exception as e:
                            logger.debug(f"Erreur extraction offre: {e}")
                            continue

                except Exception as e:
                    logger.error(f"❌ Erreur scraping page {page_num + 1}: {e}")
                    break

            logger.info(f"✅ {len(offres)} offres extraites avec succès sur {page_num + 1} pages")
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
            promoter = source_list[0].get("name", "ReliefWeb") if source_list else "ReliefWeb"

            # Country
            country_list = fields.get("country", [])
            country = country_list[0].get("name", "") if country_list else ""

            # URL
            external_url = fields.get("url", "")

            offre = OffreRelief(
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

    def save_to_pending(self, offre: OffreRelief):
        """Save offer to PostgreSQL"""
        try:
            if offre.reference in self.existing_offres_set:
                logger.debug(f"⏭️ Doublon: {offre.reference}")
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
            logger.error(f"❌ Erreur save: {e}")
            return False

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
    def post_tender_to_database(self, offre: OffreRelief) -> dict:
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
                        error_detail = f"Status {response.status_code} - {response.text[:500]}"
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

    def _map_offre_to_tender_payload(self, offre: OffreRelief) -> dict:
        """Map offer to API payload"""
        promoter_id = self.get_or_create_promoter(offre.promoter)

        # Convert datetime objects to ISO string
        pub_date = offre.publicationDate.isoformat() if isinstance(offre.publicationDate, datetime) else offre.publicationDate
        start_date = offre.startBiddingDate.isoformat() if isinstance(offre.startBiddingDate, datetime) else offre.startBiddingDate
        exp_date = offre.expirationDate.isoformat() if isinstance(offre.expirationDate, datetime) else offre.expirationDate

        payload = {
            "title": offre.description[:200],
            "description": offre.description_fr[:500],
            "publicationDate": pub_date,
            "startBiddingDate": start_date,
            "expirationDate": exp_date,
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
            "images": []
        }

        return {k: v for k, v in payload.items() if v is not None}

# Initialize scraper
scraper = ReliefWebScraper()

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
        "service": "Relief Web Scraper",
        "database": db_status
    })

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Launch scraping"""
    try:
        data = request.json or {}
        date_filter_input = data.get('date_filter', '').strip()
        max_pages = int(data.get('max_pages', 10))

        logger.info(f"🚀 Lancement scraping ReliefWeb: date_filter={date_filter_input}, max_pages={max_pages}")

        # Parser la date de filtre
        date_filter = None
        if date_filter_input:
            try:
                date_filter = datetime.strptime(date_filter_input, '%Y-%m-%d')
                logger.info(f"Filtre activé: {date_filter.strftime('%Y-%m-%d')}")
            except:
                logger.warning("Format de date invalide, extraction sans filtre")
        else:
            logger.info("Extraction sans filtre de date")

        # Scraper toutes les offres
        offres = scraper.scrape_relief_jobs(limit=max_pages * 20)

        # Appliquer le filtre de date si nécessaire
        filtered_offres = []
        filtered_count = 0

        for offre in offres:
            if date_filter:
                # Parser la date de publication de l'offre
                try:
                    pub_date_str = offre.publicationDate
                    if pub_date_str:
                        # Supporte ISO format
                        pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                        if pub_date.date() == date_filter.date():
                            filtered_offres.append(offre)
                            logger.info(f"Date correspondante: {offre.reference} - {offre.description[:50]}...")
                        else:
                            filtered_count += 1
                            logger.info(f"Date différente ({pub_date.date()} != {date_filter.date()}), ignoré")
                    else:
                        filtered_count += 1
                except Exception as e:
                    logger.debug(f"Erreur parsing date pour {offre.reference}: {e}")
                    filtered_count += 1
            else:
                filtered_offres.append(offre)

        # Sauvegarder les offres filtrées
        saved = 0
        for offre in filtered_offres:
            if scraper.save_to_pending(offre):
                saved += 1

        logger.info(f"✅ {saved}/{len(filtered_offres)} offres sauvegardées ({filtered_count} filtrées)")

        return jsonify({
            "success": True,
            "message": f"Scraping terminé: {saved} nouvelles offres sur {len(filtered_offres)} extraites",
            "total": len(filtered_offres),
            "saved": saved,
            "filtered": filtered_count
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

@app.route('/api/validate/<reference>', methods=['POST'])
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

        offre = OffreRelief(**offre_dict)
        result = scraper.post_tender_to_database(offre)

        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Erreur validation: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<reference>', methods=['DELETE'])
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
@app.route('/api/delete-all', methods=['DELETE'])
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
            "deleted": deleted_count
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
    print("SCRAPER RELIEFWEB - VERSION API FLASK")
    print("=" * 80)
    print(f"Source ID: {DEFAULT_SOURCE_ID_RELIEF}")
    print(f"Email: {EMAIL}")
    print(f"API: {API_BASE_URL}")
    print(f"MongoDB: {DB_NAME}")
    print("=" * 80)

    app.run(host='0.0.0.0', port=5015, debug=False)
