#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import time
import re
import random
from datetime import datetime
from urllib.parse import urljoin
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration PostgreSQL
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'tenders_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Configuration API Appeloffres.net
API_BASE_URL = os.getenv("API_BASE_URL", "https://be-stg.appeloffres.net/api")  # Utiliser staging
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
API_EMAIL = os.getenv("API_EMAIL", "oumayma.dahmani@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "Ah0F553KKu0A")
USER_AGENT = "PPDAMalawiScraper/1.0"

# IDs pour Malawi
DEFAULT_SOURCE_ID = 1703  # Source ID pour PPDA Malawi
DEFAULT_AVIS_ID = 11  # Avis standard
DEFAULT_COUNTRY_ID = 129  # Malawi country ID

# Token API global avec expiration
api_token = None
token_expiration = None  # Timestamp d'expiration du token (24h)
promoters_cache = {}

class PPDA_Scraper:
    def __init__(self):
        self.base_url = "https://www.ppda.mw/tenders"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)

    def make_request(self, url, max_retries=3):
        """Faire une requête HTTP avec retry et gestion d'erreurs"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout (tentative {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur requête: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 3))
        return None

    def find_table(self, soup):
        """Trouver le tableau des appels d'offres"""
        table = soup.find('table', {'id': 'tenderstable'})
        if not table:
            table = soup.find('table', {'class': 'table table-bordered'})
        if not table:
            tables = soup.find_all('table', {'class': 'table'})
            for t in tables:
                if t.find('tbody') or len(t.find_all('tr')) > 3:
                    table = t
                    break
        if not table:
            all_tables = soup.find_all('table')
            for t in all_tables:
                rows = t.find_all('tr')
                if len(rows) > 3:
                    table = t
                    break
        return table

    def extract_row_data(self, row):
        """Extraire les données d'une ligne de tableau"""
        cols = row.find_all(['td', 'th'])

        if len(cols) < 3:
            return None

        try:
            title = ""
            institution = ""
            reference_no = ""
            publish_date = ""
            closing_date = ""
            download_link = ""

            if len(cols) >= 6:
                title = cols[0].get_text(strip=True)
                institution = cols[1].get_text(strip=True)
                reference_no = cols[2].get_text(strip=True)
                publish_date = cols[3].get_text(strip=True)
                closing_date = cols[4].get_text(strip=True)
                download_a = cols[5].find('a')
                if download_a and download_a.get('href'):
                    href = download_a['href']
                    download_link = urljoin(self.base_url, href)
            elif len(cols) == 5:
                title = cols[0].get_text(strip=True)
                institution = cols[1].get_text(strip=True)
                reference_no = cols[2].get_text(strip=True)
                publish_date = cols[3].get_text(strip=True)
                closing_date = cols[4].get_text(strip=True)
            else:
                for i, col in enumerate(cols):
                    text = col.get_text(strip=True)
                    if not text:
                        continue
                    if re.match(r'^\d{2}/\d{2}/\d{4}$', text) and not publish_date:
                        if i > 0 and not closing_date:
                            publish_date = text
                        else:
                            closing_date = text
                    elif re.match(r'^[A-Z]+/\d+/', text) or re.match(r'^\d+/\d+/', text):
                        reference_no = text
                    elif len(text) > 50:
                        title = text
                    elif len(text) < 50 and not institution:
                        institution = text
                links = row.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    if href and ('download' in href.lower() or 'pdf' in href.lower() or '.doc' in href.lower()):
                        download_link = urljoin(self.base_url, href)
                        break

            description = self.clean_description(title)

            if not description and not reference_no:
                return None

            tender = {
                "reference": reference_no if reference_no else "N/A",
                "title": title if title else "Appel d'offres PPDA",
                "description": description if description else "Appel d'offres",
                "promoter": institution if institution else "N/A",
                "publication_date": self.parse_date(publish_date),
                "expiration_date": self.parse_date(closing_date),
                "document_url": download_link if download_link else "",
                "country": "Malawi",
                "nature": "public",
                "type": "national",
                "funding_source_type": "national",
                "caution": "0"
            }

            return tender

        except Exception as e:
            logger.warning(f"Erreur extraction ligne: {e}")
            return None

    def clean_description(self, title):
        """Nettoyer la description"""
        if not title:
            return ""
        cleaned = re.sub(r'\([^)]*\)', '', title)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip().rstrip('.')
        return cleaned.strip()

    def parse_date(self, date_str):
        """Convertir une date au format PostgreSQL"""
        if not date_str or date_str == 'N/A':
            return None

        date_formats = ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']

        for date_format in date_formats:
            try:
                dt = datetime.strptime(date_str, date_format)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def scrape_page(self, page=1):
        """Scraper une page spécifique"""
        try:
            if page == 1:
                url = self.base_url
            else:
                url = f"{self.base_url}?page={page}"

            logger.info(f"Scraping page {page}: {url}")
            response = self.make_request(url)

            if not response:
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            table = self.find_table(soup)

            if not table:
                logger.warning(f"Aucun tableau trouvé sur la page {page}")
                return []

            rows = []
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                rows = table.find_all('tr')

            if rows and rows[0].find_all(['th']):
                rows = rows[1:]

            tenders = []
            for row in rows:
                tender = self.extract_row_data(row)
                if tender:
                    tenders.append(tender)

            logger.info(f"Page {page}: {len(tenders)} appels d'offres extraits")
            return tenders

        except Exception as e:
            logger.error(f"Erreur scraping page {page}: {e}")
            return []

    def scrape_all_pages(self, max_pages=10):
        """Scraper toutes les pages"""
        all_tenders = []
        consecutive_empty = 0

        for page in range(1, max_pages + 1):
            tenders = self.scrape_page(page)

            if not tenders:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("2 pages vides consécutives, arrêt du scraping")
                    break
                continue

            consecutive_empty = 0
            all_tenders.extend(tenders)

            time.sleep(random.uniform(1, 2))

        logger.info(f"Total: {len(all_tenders)} appels d'offres extraits")
        return all_tenders

    def filter_by_date(self, tenders, start_date=None):
        """Filtrer par date de publication"""
        if not start_date:
            return tenders

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Format de date invalide: {start_date}")
            return tenders

        filtered = []
        for tender in tenders:
            if tender['publication_date']:
                try:
                    pub_dt = datetime.strptime(tender['publication_date'], '%Y-%m-%d')
                    if pub_dt >= start_dt:
                        filtered.append(tender)
                except ValueError:
                    filtered.append(tender)
            else:
                filtered.append(tender)

        logger.info(f"Filtrage: {len(filtered)}/{len(tenders)} appels conservés")
        return filtered

def get_db_connection():
    """Créer une connexion à la base de données"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erreur connexion DB: {e}")
        return None

def save_to_db(tenders):
    """Sauvegarder les appels d'offres dans PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return {'saved': 0, 'duplicates': 0, 'errors': 0}

    saved = 0
    duplicates = 0
    errors = 0

    try:
        cur = conn.cursor()

        for tender in tenders:
            try:
                cur.execute("""
                    INSERT INTO tenders_ppda (
                        reference, title, description, promoter,
                        publication_date, expiration_date, document_url,
                        country, nature, type, funding_source_type, caution
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reference) DO NOTHING
                    RETURNING id
                """, (
                    tender['reference'],
                    tender['title'],
                    tender['description'],
                    tender['promoter'],
                    tender['publication_date'],
                    tender['expiration_date'],
                    tender['document_url'],
                    tender['country'],
                    tender['nature'],
                    tender['type'],
                    tender['funding_source_type'],
                    tender['caution']
                ))

                if cur.fetchone():
                    saved += 1
                else:
                    duplicates += 1

            except Exception as e:
                logger.error(f"Erreur sauvegarde tender {tender['reference']}: {e}")
                errors += 1
                conn.rollback()
                continue

        conn.commit()
        logger.info(f"Sauvegarde DB: {saved} nouveaux, {duplicates} doublons, {errors} erreurs")

    except Exception as e:
        logger.error(f"Erreur sauvegarde DB: {e}")
    finally:
        cur.close()
        conn.close()

    return {'saved': saved, 'duplicates': duplicates, 'errors': errors}

def get_pending_tenders():
    """Récupérer les appels d'offres en attente de validation"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM tenders_ppda
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """)
        tenders = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(t) for t in tenders]
    except Exception as e:
        logger.error(f"Erreur récupération tenders: {e}")
        return []

def is_token_valid():
    """Vérifie si le token est valide (existe et n'a pas expiré)"""
    global api_token, token_expiration
    from datetime import timedelta

    if not api_token:
        return False

    if not token_expiration:
        return False

    # Vérifier si le token n'a pas expiré (24h)
    if datetime.now() >= token_expiration:
        logger.info("⚠️ Token expiré (24h dépassées), reconnexion nécessaire")
        return False

    return True

def login_to_api():
    """Se connecte à l'API appeloffres.net et récupère le token avec expiration 24h"""
    global api_token, token_expiration
    from datetime import timedelta

    # Vérifier si le token est déjà valide
    if is_token_valid():
        logger.info("✅ Token déjà valide, pas de reconnexion nécessaire")
        return True

    try:
        payload = {'email': API_EMAIL, 'password': API_PASSWORD}
        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}

        logger.info("🔐 Connexion à l'API appeloffres.net...")
        response = requests.post(LOGIN_ENDPOINT, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            api_token = (
                data.get('accessToken') or
                data.get('access_token') or
                data.get('token') or
                data.get('data', {}).get('accessToken') or
                data.get('data', {}).get('access_token') or
                data.get('data', {}).get('token')
            )

            if isinstance(api_token, str) and api_token.startswith('Bearer '):
                api_token = api_token.split(' ')[1]

            if api_token:
                # Définir l'expiration à 24h à partir de maintenant
                token_expiration = datetime.now() + timedelta(hours=24)
                logger.info(f"✅ Connexion API réussie. Token valide jusqu'à {token_expiration.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                logger.error("⚠️ Token vide dans la réponse API")
                return False
        else:
            logger.error(f"❌ Erreur connexion API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception lors de la connexion API: {e}")
        return False

def find_or_create_promoter(promoter_name):
    """Trouve ou crée un promoteur dans l'API appeloffres.net"""
    global api_token, promoters_cache

    # Vérifier et se connecter seulement si nécessaire
    if not is_token_valid():
        if not login_to_api():
            logger.error("❌ Impossible de créer promoteur sans token")
            return None

    # Normaliser le nom
    normalized_name = promoter_name.strip().lower()

    # Vérifier le cache
    if normalized_name in promoters_cache:
        return promoters_cache[normalized_name]

    try:
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT
        }

        # Rechercher d'abord
        search_response = requests.get(
            f"{PROMOTER_ENDPOINT}/search",
            params={'name': promoter_name},
            headers=headers,
            timeout=10
        )

        if search_response.status_code == 200:
            promoters = search_response.json()
            if promoters and len(promoters) > 0:
                promoter_id = promoters[0].get('id')
                promoters_cache[normalized_name] = promoter_id
                logger.info(f"✅ Promoteur trouvé: {promoter_name} (ID: {promoter_id})")
                return promoter_id

        # Créer s'il n'existe pas
        create_payload = {
            'name': promoter_name,
            'companyName': promoter_name,
            'countryId': DEFAULT_COUNTRY_ID,
            'address': {
                'streetAddress': 'Lilongwe',
                'city': 'Lilongwe',
                'countryId': DEFAULT_COUNTRY_ID
            },
            'phoneNumber': '+265-1-000000',
            'email': f"{promoter_name.replace(' ', '_').lower()}@malawi.mw",
            'type': 'public'
        }

        create_response = requests.post(
            PROMOTER_ENDPOINT,
            json=create_payload,
            headers=headers,
            timeout=10
        )

        if create_response.status_code in [200, 201]:
            promoter_data = create_response.json()
            promoter_id = promoter_data.get('id') or promoter_data.get('data', {}).get('id')
            if promoter_id:
                promoters_cache[normalized_name] = promoter_id
                logger.info(f"✅ Promoteur créé: {promoter_name} (ID: {promoter_id})")
                return promoter_id
        else:
            logger.error(f"❌ Erreur création promoteur: {create_response.status_code} - {create_response.text}")

        # Si échec, créer un promoteur générique "Malawi Government"
        generic_name = "Malawi Government"
        if generic_name.lower() in promoters_cache:
            return promoters_cache[generic_name.lower()]

        generic_payload = {
            'name': generic_name,
            'companyName': generic_name,
            'countryId': DEFAULT_COUNTRY_ID,
            'address': {
                'streetAddress': 'Lilongwe',
                'city': 'Lilongwe',
                'countryId': DEFAULT_COUNTRY_ID
            },
            'phoneNumber': '+265-1-000000',
            'email': 'info@malawi.gov.mw',
            'type': 'public'
        }

        generic_response = requests.post(
            PROMOTER_ENDPOINT,
            json=generic_payload,
            headers=headers,
            timeout=10
        )

        if generic_response.status_code in [200, 201]:
            generic_data = generic_response.json()
            generic_id = generic_data.get('id') or generic_data.get('data', {}).get('id')
            if generic_id:
                promoters_cache[generic_name.lower()] = generic_id
                logger.info(f"✅ Promoteur générique créé: ID {generic_id}")
                return generic_id

        logger.error("❌ Échec création de tous les promoteurs")
        return None

    except Exception as e:
        logger.error(f"❌ Erreur find_or_create_promoter: {e}")
        return None

def send_to_api(tender):
    """Envoyer un appel d'offres à l'API appeloffres.net"""
    global api_token
    max_retries = 3

    for attempt in range(max_retries):
        # Vérifier et se connecter seulement si nécessaire
        if not is_token_valid():
            if not login_to_api():
                return {'success': False, 'error': 'Échec de connexion API'}

        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT
        }

        # Préparer les dates
        pub_date = tender['publication_date']
        if isinstance(pub_date, str):
            pub_date_obj = datetime.fromisoformat(pub_date.replace('Z', ''))
            publication_date = pub_date_obj.isoformat()
        elif isinstance(pub_date, datetime):
            publication_date = pub_date.isoformat()
        else:
            publication_date = datetime.now().isoformat()

        exp_date = tender['expiration_date']
        if isinstance(exp_date, str):
            exp_date_obj = datetime.fromisoformat(exp_date.replace('Z', ''))
            expiration_date = exp_date_obj.isoformat()
        elif isinstance(exp_date, datetime):
            expiration_date = exp_date.isoformat()
        else:
            from datetime import timedelta
            expiration_date = (datetime.now() + timedelta(days=30)).isoformat()

        # Trouver ou créer le promoteur
        promoter_name = tender.get('promoter', 'Malawi Government')
        promoter_id = find_or_create_promoter(promoter_name)

        if not promoter_id:
            logger.error("❌ Impossible de créer/trouver le promoteur")
            return {'success': False, 'error': 'Promoter creation failed'}

        # Préparer le payload
        api_payload = {
            'title': tender.get('title', '')[:255],
            'reference': tender.get('reference', ''),
            'description': tender.get('description', ''),
            'publicationDate': publication_date,
            'startBiddingDate': publication_date,
            'expirationDate': expiration_date,
            'openingBidsDate': expiration_date,
            'avisId': DEFAULT_AVIS_ID,
            'sourceId': DEFAULT_SOURCE_ID,
            'promoterId': promoter_id,
            'type': 'national',
            'nature': 'public',
            'isEnabled': True,
            'images': [],
            'addresses': [],
            'batches': [],
            'specificationsReceivingAddress': tender.get('document_url', ''),
            'fundingSourceType': 'national',
            'fundingSource': promoter_name,
            'isMultiCurrency': False,
            'activitiesIds': [463],  # Services par défaut
            'countriesIds': [DEFAULT_COUNTRY_ID]
        }

        try:
            logger.info(f"📤 Envoi appel d'offres {tender.get('reference')} à l'API...")
            response = requests.post(TENDER_ENDPOINT, json=api_payload, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                logger.info(f"✅ Appel d'offres {tender.get('reference')} envoyé avec succès")
                return {'success': True, 'data': response.json()}
            elif response.status_code == 401:
                logger.warning("⚠️ Token expiré, reconnexion...")
                api_token = None
                continue
            else:
                logger.error(f"❌ Erreur API: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}

        except Exception as e:
            logger.error(f"❌ Exception envoi API: {e}")
            return {'success': False, 'error': str(e)}

    return {'success': False, 'error': 'Max retries exceeded'}

def update_tender_status(tender_id, status, api_id=None):
    """Mettre à jour le status d'un tender"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        if api_id:
            cur.execute("""
                UPDATE tenders_ppda
                SET status = %s, api_id = %s, validation_date = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, api_id, tender_id))
        else:
            cur.execute("""
                UPDATE tenders_ppda
                SET status = %s
                WHERE id = %s
            """, (status, tender_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erreur update status: {e}")
        return False

# Routes Flask
@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'service': 'PPDA Scraper'}), 200

@app.route('/scrape', methods=['POST'])
def scrape():
    """Route principale de scraping"""
    try:
        data = request.get_json() or {}
        start_date = data.get('start_date')
        max_pages = data.get('max_pages', 10)

        logger.info(f"Démarrage scraping PPDA - start_date: {start_date}, max_pages: {max_pages}")

        scraper = PPDA_Scraper()

        # Scraping
        tenders = scraper.scrape_all_pages(max_pages=max_pages)

        if not tenders:
            return jsonify({
                'success': False,
                'message': 'Aucun appel d\'offres trouvé',
                'stats': {'total': 0, 'saved': 0, 'duplicates': 0, 'errors': 0}
            }), 200

        # Filtrage par date
        if start_date:
            tenders = scraper.filter_by_date(tenders, start_date)

        # Sauvegarde dans PostgreSQL
        stats = save_to_db(tenders)
        stats['total'] = len(tenders)

        return jsonify({
            'success': True,
            'message': f'{stats["saved"]} nouveaux appels d\'offres extraits',
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Erreur scraping: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/tenders', methods=['GET'])
def get_tenders():
    """Récupérer les appels d'offres"""
    try:
        status = request.args.get('status', 'pending')
        limit = int(request.args.get('limit', 100))

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        if status == 'all':
            cur.execute("SELECT * FROM tenders_ppda ORDER BY created_at DESC LIMIT %s", (limit,))
        else:
            cur.execute("SELECT * FROM tenders_ppda WHERE status = %s ORDER BY created_at DESC LIMIT %s", (status, limit))

        tenders = cur.fetchall()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'tenders': [dict(t) for t in tenders],
            'count': len(tenders)
        }), 200

    except Exception as e:
        logger.error(f"Erreur récupération tenders: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/validate/<path:reference>', methods=['POST'])
def validate_single(reference):
    """Valider et envoyer un seul appel d'offres à l'API"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer le tender par référence
        cur.execute("SELECT * FROM tenders_ppda WHERE reference = %s", (reference,))
        tender = cur.fetchone()

        cur.close()
        conn.close()

        if not tender:
            return jsonify({
                'success': False,
                'message': f'Appel d\'offres {reference} non trouvé'
            }), 404

        # Envoyer à l'API
        logger.info(f"📤 Envoi de l'appel d'offres {reference} vers l'API...")
        result = send_to_api(dict(tender))

        if result['success']:
            api_id = result['data'].get('id') if 'data' in result else None
            update_tender_status(tender['id'], 'validated', api_id)
            logger.info(f"✅ Appel d'offres {reference} validé et envoyé à l'API")
            return jsonify({
                'success': True,
                'message': f'Appel d\'offres {reference} validé et envoyé à l\'API avec succès'
            }), 200
        else:
            update_tender_status(tender['id'], 'failed')
            logger.error(f"❌ Échec de l'envoi API pour {reference}")
            return jsonify({
                'success': False,
                'message': f'Échec de l\'envoi vers l\'API: {result.get("error", "Unknown error")}'
            }), 500

    except Exception as e:
        logger.error(f"Erreur validation {reference}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/validate', methods=['POST'])
def validate():
    """Valider et envoyer les appels d'offres à l'API"""
    try:
        pending_tenders = get_pending_tenders()

        if not pending_tenders:
            return jsonify({
                'success': True,
                'message': 'Aucun appel d\'offres en attente',
                'stats': {'total': 0, 'success': 0, 'failed': 0}
            }), 200

        success_count = 0
        failed_count = 0

        for tender in pending_tenders:
            result = send_to_api(tender)

            if result['success']:
                api_id = result['data'].get('id') if 'data' in result else None
                update_tender_status(tender['id'], 'validated', api_id)
                success_count += 1
            else:
                update_tender_status(tender['id'], 'failed')
                failed_count += 1

            time.sleep(0.5)

        return jsonify({
            'success': True,
            'message': f'{success_count} appels validés, {failed_count} échecs',
            'stats': {
                'total': len(pending_tenders),
                'success': success_count,
                'failed': failed_count
            }
        }), 200

    except Exception as e:
        logger.error(f"Erreur validation: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Statistiques des appels d'offres"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'validated') as validated,
                COUNT(*) FILTER (WHERE status = 'failed') as failed
            FROM tenders_ppda
        """)

        stats_data = dict(cur.fetchone())
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'stats': stats_data
        }), 200

    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_all', methods=['POST'])
def delete_all():
    """Supprimer tous les appels d'offres en attente"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor()
        cur.execute("DELETE FROM tenders_ppda WHERE status = 'pending'")
        deleted_count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✅ {deleted_count} appels d'offres supprimés")

        return jsonify({
            'success': True,
            'message': f'{deleted_count} appels d\'offres supprimés',
            'count': deleted_count
        }), 200
    except Exception as e:
        logger.error(f"Erreur suppression: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5017))
    logger.info(f"Démarrage serveur PPDA sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
