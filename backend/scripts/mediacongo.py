# mediacongo.py - Scraper MediaCongo avec Flask API et PostgreSQL
import os

# CRITICAL: Set encoding BEFORE importing psycopg2 to avoid Windows encoding issues
os.environ['PGCLIENTENCODING'] = 'utf8'

import logging
import psycopg2
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_mediacongo"

# Configuration API AppelOffres
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
EMAIL = os.getenv("API_EMAIL", "maryam@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "123456789")

# IDs par défaut pour l'API
DEFAULT_SOURCE_ID = 818  # ID pour MediaCongo
DEFAULT_AVIS_ID = 2
DEFAULT_PAYS_ID = 219  # Tunisie par défaut
DEFAULT_CURRENCY_ID = 111  # TND par défaut
DEFAULT_PROMOTER_ID = 180897

# Configuration MediaCongo
BASE_URL = "https://www.mediacongo.net"
LIST_URL = "https://www.mediacongo.net/appels.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token API global avec expiration
api_token = None
token_expiration = None  # Timestamp d'expiration du token (24h)

# ================================================
# SCRAPING FUNCTIONS (UNCHANGED)
# ================================================

def parse_date(date_str):
    """Convertit une date au format DD.MM.YYYY ou DD/MM/YYYY en objet datetime"""
    if not date_str:
        return None

    # Nettoyer la date
    date_str = date_str.strip()

    # Essayer différents formats
    formats = [
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return None

def get_all_page_urls(session, max_pages=50):
    """Récupère toutes les URLs des appels d'offres de toutes les pages"""
    all_urls = set()
    page = 1

    while page <= max_pages:
        try:
            if page == 1:
                url = LIST_URL
            else:
                url = f"{BASE_URL}/appels-search--tri-appels_recents-page-{page}.html"

            logger.info(f"Chargement de la page {page}...")
            resp = session.get(url, timeout=30)  # Augmenté à 30s

            if resp.status_code != 200:
                logger.warning(f"Page {page} non accessible (code {resp.status_code})")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # Chercher les liens vers les appels d'offres
            links_found = 0
            for a in soup.select("a[href*='appel-societe']"):
                href = a.get("href")
                if href:
                    all_urls.add(urljoin(BASE_URL, href))
                    links_found += 1

            logger.info(f"{links_found} appels trouvés sur page {page}")

            if links_found == 0:
                logger.info(f"Aucun appel trouvé, fin de pagination")
                break

            page += 1
            time.sleep(0.5)  # Réduit de 1s à 0.5s pour accélérer

        except Exception as e:
            logger.error(f"Erreur page {page}: {e}")
            break

    return all_urls

def extract_date_from_page(soup, text):
    """Extrait la date d'insertion depuis la page"""
    # Chercher dans le texte visible
    patterns = [
        r'Insérée?\s+(?:le\s+)?:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})',
        r'Publiée?\s+(?:le\s+)?:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})',
        r'Date\s+(?:de\s+)?publication\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    # Chercher dans les métadonnées ou éléments spécifiques
    date_elements = soup.find_all(text=re.compile(r'Insérée?|Publiée?', re.IGNORECASE))
    for elem in date_elements:
        parent_text = elem.parent.get_text(strip=True) if elem.parent else ""
        match = re.search(r'([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})', parent_text)
        if match:
            return match.group(1)

    return ""

def extract_date_limite(soup, text):
    """Extrait la date limite avec plusieurs méthodes"""
    date_limite = ""

    # Patterns améliorés pour capturer la date limite
    date_patterns = [
        # Formats explicites
        r'Date\s+limite\s+(?:de\s+(?:dépôt|remise|soumission))?\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
        r'Date\s+de\s+(?:remise|clôture|dépôt)\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
        r'(?:Expire|Expiration)\s+(?:le)?\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
        r'Clôture\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',

        # Formats avec mots
        r'(?:avant\s+le|jusqu\'?au|au\s+plus\s+tard\s+le)\s+([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
        r'(?:soumission|offres)\s+(?:avant|jusqu\'?au)\s+(?:le)?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',

        # Formats en toutes lettres
        r'Date\s+limite\s*:?\s*([0-9]{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+[0-9]{4})',

        # Formats courts
        r'Limite\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
        r'Échéance\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
    ]

    # Essayer tous les patterns
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_limite = match.group(1).strip()
            break

    # Si pas trouvé, chercher dans des sections spécifiques
    if not date_limite:
        # Chercher dans les divs/sections qui pourraient contenir la date
        sections = soup.find_all(['div', 'p', 'span'], class_=re.compile(r'date|deadline|limite', re.IGNORECASE))
        for section in sections:
            section_text = section.get_text(strip=True)
            match = re.search(r'([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})', section_text)
            if match:
                date_limite = match.group(1)
                break

    return date_limite

def scrape_offre(session, url):
    """Extrait les données d'un appel d'offre avec retry automatique"""
    max_retries = 2

    for attempt in range(max_retries):
        try:
            time.sleep(0.5)  # Réduit le délai pour accélérer
            r = session.get(url, timeout=30)  # Augmenté à 30s

            if r.status_code != 200:
                logger.warning(f"Status {r.status_code} pour {url}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None

            s = BeautifulSoup(r.text, "html.parser")
            texte_complet = s.get_text(" ", strip=True)

            # TITRE
            titre = ""
            titre_tag = s.find("h1")
            if titre_tag:
                titre = titre_tag.get_text(strip=True)

            # NUMÉRO
            numero_ao = ""
            match_numero = re.search(r'AOF?\d+', titre + " " + texte_complet)
            if match_numero:
                numero_ao = match_numero.group()

            # ORGANISME
            organisme = ""
            org_patterns = [
                r'(?:Promoteur|Organisateur|Organisme)[:\s]+([^.\n]+)',
                r'(UCM|ASF|UNICEF|OMS|PNUD|IMA World Health|Expertise France|SERVTEC RDC|Ministère[^.\n]+)',
            ]
            for pattern in org_patterns:
                match = re.search(pattern, texte_complet, re.IGNORECASE)
                if match:
                    organisme = match.group(1).strip()
                    break

            # LIEU
            lieu = ""
            lieu_patterns = [
                r'(?:Lieu|Localité|Province)[:\s]+([^.\n]+)',
                r'(Kinshasa|Lubumbashi|Goma|Bukavu|Kananga|Matadi|Kisangani|Goma et Beni)',
            ]
            for pattern in lieu_patterns:
                match = re.search(pattern, texte_complet, re.IGNORECASE)
                if match:
                    lieu = match.group(1).strip()
                    break

            # DATE LIMITE - Utilisation de la nouvelle fonction améliorée
            date_expiration = extract_date_limite(s, texte_complet)

            # DATE INSERTION
            date_insertion = extract_date_from_page(s, texte_complet)

            # STATUT
            statut = "En cours"
            if date_expiration:
                date_exp_obj = parse_date(date_expiration)
                if date_exp_obj and date_exp_obj < datetime.now():
                    statut = "Expiré"
                elif date_exp_obj:
                    jours_restants = (date_exp_obj - datetime.now()).days
                    if jours_restants <= 3:
                        statut = "Urgent"

            # DESCRIPTION
            description = ""
            desc_tag = s.find("div", class_=re.compile("content|description|body|article"))
            if desc_tag:
                description = desc_tag.get_text(" ", strip=True)[:500]

            # LIENS
            liens = []
            for lien_tag in s.select("a[href]"):
                href = lien_tag.get("href")
                texte_lien = lien_tag.get_text(strip=True)
                if href and not any(x in href for x in ["/actualites", "/contact", "/accueil", "javascript", "#"]):
                    lien_complet = urljoin(BASE_URL, href)
                    if lien_complet != url:
                        liens.append(f"{texte_lien}: {lien_complet}")
            liens_str = " | ".join(liens[:5]) if liens else ""

            return {
                "Numéro AO": numero_ao,
                "Titre": titre,
                "Organisme": organisme,
                "Lieu": lieu,
                "Date limite": date_expiration,
                "Date d'insertion": date_insertion,
                "Statut": statut,
                "Description": description,
                "Liens associés": liens_str,
                "URL": url,
                "Pays": "RDC"  # Pays par défaut toujours RDC
            }

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout pour {url} (tentative {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
        except Exception as e:
            logger.error(f"Erreur scraping {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None

    return None

# ================================================
# POSTGRESQL FUNCTIONS
# ================================================

def get_db_connection():
    """Créer une connexion PostgreSQL"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    # Set UTF8 encoding after connection for proper data handling
    conn.set_client_encoding('UTF8')
    return conn

def convert_date_to_postgres(date_str):
    """Convertit DD.MM.YYYY ou DD/MM/YYYY vers YYYY-MM-DD pour PostgreSQL"""
    if not date_str:
        return None

    date_obj = parse_date(date_str)
    if date_obj:
        return date_obj.strftime('%Y-%m-%d')
    return None

def save_to_postgres(offers, status='pending'):
    """Sauvegarde les offres dans PostgreSQL"""
    if not offers:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    inserted_count = 0

    try:
        for idx, offer in enumerate(offers):
            # Générer une référence unique si manquante
            reference = offer.get("Numéro AO", "").strip()
            if not reference:
                timestamp = int(time.time())
                reference = f"MEDIACONGO-{timestamp}-{idx}"

            # Conversion des dates
            publication_date = convert_date_to_postgres(offer.get("Date d'insertion"))
            expiration_date = convert_date_to_postgres(offer.get("Date limite"))

            # Préparation des données
            title = offer.get("Titre", "")
            organisme = offer.get("Organisme", "")
            lieu = offer.get("Lieu", "")
            status_text = offer.get("Statut", "En cours")
            description = offer.get("Description", "")
            liens_associes = offer.get("Liens associés", "")
            url = offer.get("URL", "")
            pays = offer.get("Pays", "RDC")

            query = f"""
                INSERT INTO {TABLE_NAME}
                (reference, title, organisme, lieu, expiration_date, publication_date,
                 status_text, description, liens_associes, url, pays, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (reference) DO NOTHING
            """

            cursor.execute(query, (
                reference, title, organisme, lieu, expiration_date, publication_date,
                status_text, description, liens_associes, url, pays, status
            ))

            if cursor.rowcount > 0:
                inserted_count += 1

        conn.commit()
        logger.info(f"Sauvegardé {inserted_count} nouvelles offres dans PostgreSQL")

    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur sauvegarde PostgreSQL: {e}")
    finally:
        cursor.close()
        conn.close()

    return inserted_count

def get_all_tenders(status=None):
    """Récupère toutes les offres depuis PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if status:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY created_at DESC")
        results = cursor.fetchall()
        return [dict(row) for row in results]
    finally:
        cursor.close()
        conn.close()

# ================================================
# API APPELOFFRES FUNCTIONS
# ================================================

def is_token_valid():
    """Vérifie si le token est valide (existe et n'a pas expiré)"""
    global api_token, token_expiration

    if not api_token:
        return False

    if not token_expiration:
        return False

    # Vérifier si le token n'a pas expiré (24h)
    if datetime.now() >= token_expiration:
        logger.info("⚠️ Token expiré (24h dépassées), reconnexion nécessaire")
        return False

    return True

def login_to_appeloffres():
    """Se connecte à l'API AppelOffres et retourne le token avec expiration 24h"""
    global api_token, token_expiration

    # Vérifier si le token est déjà valide
    if is_token_valid():
        logger.info("✅ Token déjà valide, pas de reconnexion nécessaire")
        return api_token

    try:
        logger.info("🔐 Connexion à l'API AppelOffres...")
        response = requests.post(
            LOGIN_ENDPOINT,
            json={"email": EMAIL, "password": API_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            api_token = data.get('access_token') or data.get('accessToken') or data.get('token')

            if api_token:
                # Définir l'expiration à 24h à partir de maintenant
                token_expiration = datetime.now() + timedelta(hours=24)
                logger.info(f"✅ Connexion API réussie. Token valide jusqu'à {token_expiration.strftime('%Y-%m-%d %H:%M:%S')}")
                return api_token
            else:
                logger.error("⚠️ Token vide dans la réponse API")
                return None
        else:
            logger.error(f"Échec login API: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Erreur login API: {e}")
        return None

def get_or_create_promoter(token, promoter_name):
    """Trouve ou crée un promoteur dans l'API"""
    if not promoter_name or promoter_name.strip() == '':
        promoter_name = 'MediaCongo'

    try:
        headers = {'Authorization': f'Bearer {token}'}

        # Chercher le promoteur existant
        response = requests.get(
            f"{PROMOTER_ENDPOINT}?page=1&itemsPerPage=1000",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            promoters = response.json()
            for promoter in promoters:
                if promoter.get('name', '').lower() == promoter_name.lower():
                    logger.info(f"Promoteur trouvé: {promoter_name} (ID: {promoter['id']})")
                    return promoter['id']

        # Créer le promoteur s'il n'existe pas
        create_response = requests.post(
            PROMOTER_ENDPOINT,
            json={
                "name": promoter_name,
                "companyName": promoter_name,
                "address": "RDC"
            },
            headers=headers,
            timeout=30
        )

        if create_response.status_code in [200, 201]:
            promoter_id = create_response.json().get('id')
            logger.info(f"Promoteur créé: {promoter_name} (ID: {promoter_id})")
            return promoter_id
        else:
            logger.error(f"Échec création promoteur: {create_response.status_code}")
            logger.info(f"Utilisation du promoteur par défaut (ID: {DEFAULT_PROMOTER_ID})")
            return DEFAULT_PROMOTER_ID

    except Exception as e:
        logger.error(f"Erreur get_or_create_promoter: {e}")
        return DEFAULT_PROMOTER_ID

def create_tender_payload(tender_data, promoter_id):
    """Crée le payload pour l'API AppelOffres"""
    try:
        # Dates
        publication_date = tender_data.get('publication_date')
        if publication_date:
            if isinstance(publication_date, str):
                pub_dt = datetime.fromisoformat(publication_date.replace('Z', '+00:00'))
            else:
                pub_dt = publication_date
            publication_ts = pub_dt.isoformat()
        else:
            publication_ts = datetime.now().isoformat()

        expiration_date = tender_data.get('expiration_date')
        if expiration_date:
            if isinstance(expiration_date, str):
                exp_dt = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            else:
                exp_dt = expiration_date
            expiration_ts = exp_dt.isoformat()
        else:
            # +30 jours par défaut
            exp_dt = datetime.fromisoformat(publication_ts.replace('Z', '+00:00')) + timedelta(days=30)
            expiration_ts = exp_dt.isoformat()

        # Description et titre
        title = tender_data.get('title', '')[:500] or f"MediaCongo - {tender_data.get('reference', 'N/A')}"
        description = tender_data.get('description', '') or tender_data.get('title', '') or "Appel d'offres MediaCongo"

        # Country ID
        country_id = tender_data.get('country_id') or DEFAULT_PAYS_ID

        # Batch unique
        batches = [{
            "activitiesIds": [],
            "title": title[:200],
            "deposit": "0"
        }]

        # Addresses
        addresses = [{"countryId": int(country_id)}]

        # Images (placeholder)
        images = [{"url": "https://placeholder.com/mediacongo.jpg", "description": "MediaCongo"}]

        payload = {
            "title": title,
            "description": description,
            "publicationDate": publication_ts,
            "startBiddingDate": publication_ts,
            "expirationDate": expiration_ts,
            "openingBidsDate": expiration_ts,
            "reference": tender_data.get('reference', 'N/A'),
            "specificationsPrice": 0,
            "offerValidityPeriode": None,
            "avisId": int(DEFAULT_AVIS_ID),
            "sourceId": int(DEFAULT_SOURCE_ID),
            "promoterId": int(promoter_id),
            "type": "international",
            "nature": "public",
            "isEnabled": True,
            "specificationsReceivingAddress": tender_data.get('url', BASE_URL),
            "fundingSourceType": "international",
            "fundingSource": "MediaCongo",
            "currencyId": int(DEFAULT_CURRENCY_ID),
            "isMultiCurrency": False,
            "batches": batches,
            "addresses": addresses,
            "images": images
        }

        return payload

    except Exception as e:
        logger.error(f"Erreur create_tender_payload: {e}")
        raise

# ================================================
# FLASK APP
# ================================================

app = Flask(__name__)
CORS(app, origins=["*"])

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        pending = get_all_tenders(status="pending")
        validated = get_all_tenders(status="validated")

        return jsonify({
            "status": "healthy",
            "service": "MediaCongo",
            "database": "PostgreSQL",
            "table": TABLE_NAME,
            "pending_count": len(pending),
            "validated_count": len(validated)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Get all pending tenders"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        all_tenders = get_all_tenders(status="pending")
        start = (page - 1) * limit
        end = start + limit

        tenders_page = all_tenders[start:end]

        # Mapper pour frontend
        mapped_tenders = []
        for tender in tenders_page:
            mapped = {
                'reference': tender.get('reference'),
                'title': tender.get('title'),
                'organisme': tender.get('organisme'),
                'lieu': tender.get('lieu'),
                'publicationDate': tender.get('publication_date'),
                'expirationDate': tender.get('expiration_date'),
                'status_text': tender.get('status_text'),
                'description': tender.get('description'),
                'liens_associes': tender.get('liens_associes'),
                'url': tender.get('url'),
                'pays': tender.get('pays'),
                'status': tender.get('status')
            }
            mapped_tenders.append(mapped)

        return jsonify({
            "success": True,
            "pending": {
                "offres": mapped_tenders,
                "total": len(all_tenders),
                "page": page,
                "limit": limit,
                "totalPages": (len(all_tenders) + limit - 1) // limit
            }
        })
    except Exception as e:
        logger.error(f"Erreur /api/pending: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/validated', methods=['GET'])
def get_validated():
    """Get all validated tenders"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        all_tenders = get_all_tenders(status="validated")
        start = (page - 1) * limit
        end = start + limit

        tenders_page = all_tenders[start:end]

        return jsonify({
            "success": True,
            "validated": {
                "offres": tenders_page,
                "total": len(all_tenders),
                "page": page,
                "limit": limit
            }
        })
    except Exception as e:
        logger.error(f"Erreur /api/validated: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Endpoint pour lancer le scraping de MediaCongo"""
    try:
        data = request.json or {}
        date_filter_input = data.get('date_filter', '').strip()
        max_pages = int(data.get('max_pages', 20))

        logger.info(f"Demande de scraping MediaCongo: date_filter={date_filter_input}, max_pages={max_pages}")

        # Parser la date de filtre
        date_filter = None
        if date_filter_input:
            date_filter = parse_date(date_filter_input)
            if date_filter:
                logger.info(f"Filtre activé: {date_filter.strftime('%d.%m.%Y')}")
            else:
                logger.warning("Format de date invalide, extraction sans filtre")
        else:
            logger.info("Extraction sans filtre de date")

        # Initialisation
        session = requests.Session()
        session.headers.update(headers)

        # Récupération des URLs
        logger.info("ÉTAPE 1: Collecte des URLs")
        urls = get_all_page_urls(session, max_pages=max_pages)
        logger.info(f"Total: {len(urls)} appels d'offres trouvés")

        # Extraction des données
        logger.info("ÉTAPE 2: Extraction des données")
        scraped_data = []
        filtered_count = 0

        for idx, url in enumerate(urls, 1):
            logger.info(f"[{idx}/{len(urls)}] {url}")
            result = scrape_offre(session, url)

            if result:
                # Appliquer le filtre de date si nécessaire
                if date_filter:
                    insertion_date = parse_date(result["Date d'insertion"])
                    if insertion_date and insertion_date.date() == date_filter.date():
                        scraped_data.append(result)
                        logger.info(f"Date correspondante: {result['Titre'][:50]}...")
                    else:
                        filtered_count += 1
                        logger.info(f"Date différente, ignoré")
                else:
                    scraped_data.append(result)

        # Sauvegarder dans PostgreSQL
        logger.info("ÉTAPE 3: Sauvegarde dans PostgreSQL")
        inserted_count = save_to_postgres(scraped_data, status='pending')

        message = f"Scraping terminé: {inserted_count} nouvelles offres sur {len(scraped_data)} extraites"
        logger.info(message)

        return jsonify({
            "success": True,
            "message": message,
            "count": inserted_count,
            "total_scraped": len(scraped_data),
            "total_urls": len(urls),
            "filtered": filtered_count
        })

    except Exception as e:
        logger.error(f"Erreur /api/scrape: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_tender(reference):
    """Valide une offre et l'envoie à l'API AppelOffres"""
    try:
        # 1. Récupérer l'offre depuis la base
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        tender_data = cursor.fetchone()

        if not tender_data:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Offre non trouvée"}), 404

        tender_dict = dict(tender_data)

        # 2. Se connecter à l'API AppelOffres
        token = login_to_appeloffres()
        if not token:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Échec connexion à l'API AppelOffres"}), 500

        # 3. Obtenir ou créer le promoteur
        promoter_name = tender_dict.get('organisme') or 'MediaCongo'
        promoter_id = get_or_create_promoter(token, promoter_name)

        # 4. Créer le payload
        payload = create_tender_payload(tender_dict, promoter_id)
        logger.info(f"Envoi de l'offre {reference} vers l'API AppelOffres...")

        # 5. Envoyer à l'API
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = requests.post(TENDER_ENDPOINT, json=payload, headers=headers, timeout=30)

        if response.status_code in [200, 201]:
            api_data = response.json()
            api_id = api_data.get('id')

            # 6. Mettre à jour en base (status = validated + api_id)
            cursor.execute(
                f"UPDATE {TABLE_NAME} SET status = 'validated', validation_date = NOW(), api_id = %s WHERE reference = %s",
                (api_id, reference)
            )
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Offre {reference} validée et envoyée à l'API (ID: {api_id})")
            return jsonify({
                "success": True,
                "message": f"Offre {reference} validée et postée avec succès!",
                "api_id": api_id
            })
        else:
            # L'envoi API a échoué, mais on peut quand même valider en base
            cursor.execute(
                f"UPDATE {TABLE_NAME} SET status = 'validated', validation_date = NOW() WHERE reference = %s",
                (reference,)
            )
            conn.commit()
            cursor.close()
            conn.close()

            error_detail = response.text[:500]
            logger.error(f"Offre {reference} validée en base mais échec envoi API: {response.status_code}")
            logger.error(f"Détail erreur API: {error_detail}")
            return jsonify({
                "success": False,
                "message": f"Offre validée en base mais échec API: {response.status_code}",
                "api_error": error_detail
            }), 500

    except Exception as e:
        logger.error(f"Erreur validation {reference}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/delete_all', methods=['DELETE'])
def delete_all():
    """Supprime toutes les offres"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        count = cursor.fetchone()[0]
        cursor.execute(f"DELETE FROM {TABLE_NAME}")
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"{count} offres supprimées")
        return jsonify({"success": True, "message": f"{count} offres supprimées", "deleted_count": count})
    except Exception as e:
        logger.error(f"Erreur delete_all: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete_tender(reference):
    """Supprime une offre"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Offre {reference} supprimée")
        return jsonify({"success": True, "message": f"Offre {reference} supprimée avec succès"})
    except Exception as e:
        logger.error(f"Erreur suppression {reference}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("SCRAPER MEDIACONGO - FLASK API")
    logger.info(f"Database: PostgreSQL - {DB_NAME} (Table: {TABLE_NAME})")
    logger.info("Port: 5016")
    logger.info("=" * 80)

    app.run(host='0.0.0.0', port=5016, debug=True, use_reloader=False)
