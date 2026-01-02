#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
import requests

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

# Configuration API Appeloffres.net
API_BASE_URL = os.getenv("API_BASE_URL", "https://be-stg.appeloffres.net/api")  # Utiliser staging
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
API_EMAIL = os.getenv("API_EMAIL", "oumayma.dahmani@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "Ah0F553KKu0A")
USER_AGENT = "SomaliaTendersScraper/1.0"

# IDs pour Somalia
DEFAULT_SOURCE_ID = 1701  # Source ID pour Somalia Jobs
DEFAULT_AVIS_ID = 11  # Avis standard
DEFAULT_COUNTRY_ID = 195  # Somalia country ID
DEFAULT_PROMOTER_ID = 223472  # Promoteur par défaut

# Token API global
api_token = None
promoters_cache = {}

class SomaliaJobsScraper:
    def __init__(self):
        self.base_url = "https://www.somalijobs.com"
        self.jobs_url = "https://www.somalijobs.com/jobs"

    def translate_date(self, date_text):
        """Traduit et parse les dates de l'anglais"""
        if not date_text:
            return None

        date_text = date_text.strip()

        # Aujourd'hui
        if 'Today' in date_text:
            return datetime.now().date()

        # Hier
        if 'Yesterday' in date_text:
            return (datetime.now() - timedelta(days=1)).date()

        # Il y a X jours
        days_match = re.search(r'(\d+)\s+days?\s+ago', date_text, re.IGNORECASE)
        if days_match:
            days = int(days_match.group(1))
            return (datetime.now() - timedelta(days=days)).date()

        # Dates avec mois (Dec, 15 ou Dec 15, 2024)
        month_patterns = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }

        for month_name, month_num in month_patterns.items():
            if month_name in date_text:
                day_match = re.search(r'\d+', date_text)
                if day_match:
                    day = int(day_match.group(0))
                    year = datetime.now().year
                    year_match = re.search(r'\d{4}', date_text)
                    if year_match:
                        year = int(year_match.group(0))

                    try:
                        return datetime(year, month_num, day).date()
                    except ValueError:
                        pass

        return None

    def translate_contract_type(self, contract_type):
        """Traduit les types de contrat"""
        if not contract_type:
            return "Non spécifié"

        translations = {
            'Full Time': 'Temps plein',
            'Part Time': 'Temps partiel',
            'Contract': 'Contrat',
            'Consultant': 'Consultant',
            'Temporary': 'Temporaire',
            'Permanent': 'Permanent',
            'Internship': 'Stage',
            'Volunteer': 'Bénévolat'
        }

        return translations.get(contract_type, contract_type)

    def clean_location(self, location_text):
        """Nettoie le texte du lieu"""
        if not location_text:
            return "Somalia"

        lines = [line.strip() for line in location_text.split('\n') if line.strip()]

        for line in lines:
            if (len(line) > 2 and len(line) < 50 and
                not any(word in line.lower() for word in ['full', 'time', 'part', 'contract', 'consultant']) and
                not any(word in line.lower() for word in ['management', 'development', 'finance', 'health']) and
                not line.isdigit()):
                return line

        return lines[0] if lines else "Somalia"

    def scrape_jobs(self, start_date=None, end_date=None, max_pages=10):
        """Scraper les offres d'emploi page par page avec arrêt automatique selon dates"""
        logger.info("Démarrage scraping SomaliaJobs...")
        if start_date:
            logger.info(f"Filtre date début: {start_date}")
        if end_date:
            logger.info(f"Filtre date fin: {end_date}")

        # Convertir les dates string en objets date pour comparaison
        start_date_obj = None
        end_date_obj = None
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except:
                logger.warning(f"Format de start_date invalide: {start_date}")
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except:
                logger.warning(f"Format de end_date invalide: {end_date}")

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        all_jobs = []
        consecutive_out_of_range = 0  # Compteur d'offres hors plage consécutives

        try:
            driver = webdriver.Chrome(options=chrome_options)

            # Scraper page par page
            for page in range(1, max_pages + 1):
                logger.info(f"📄 Scraping page {page}...")

                driver.get(self.jobs_url)
                time.sleep(5)

                # Défilement pour charger plus d'offres
                scroll_count = page * 3  # Plus on avance, plus on scroll
                for _ in range(scroll_count):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)

                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                job_containers = soup.find_all('a', class_='jobs-listing-container')
                logger.info(f"   → {len(job_containers)} offres visibles sur la page")

                # Déterminer quelles offres traiter (éviter les doublons)
                start_idx = (page - 1) * 20  # Environ 20 offres par "page"
                end_idx = page * 20
                page_containers = job_containers[start_idx:end_idx]

                logger.info(f"   → Traitement des offres {start_idx} à {min(end_idx, len(job_containers))}")

                if not page_containers:
                    logger.info("   ⚠️ Plus d'offres à traiter, arrêt du scraping")
                    break

                page_jobs_in_range = 0

                for idx, container in enumerate(page_containers, start_idx + 1):
                    try:
                        # URL
                        url = container.get('href', '')
                        if url and not url.startswith('http'):
                            url = urljoin(self.base_url, url)

                        # Référence depuis l'URL (format: /jobs/pays/17255307114898614/titre)
                        reference = "SJ-N/A"
                        if url:
                            match = re.search(r'/jobs/[^/]+/(\d+)', url)
                            if match:
                                reference = f"SJ-{match.group(1)}"

                        # Titre
                        titre_elem = container.find('h2', class_='jobs-listing-title')
                        titre = titre_elem.text.strip() if titre_elem else ""

                        # Entreprise
                        entreprise_elem = container.find('p', class_='jobs-listing-company')
                        entreprise = entreprise_elem.text.strip() if entreprise_elem else "Non spécifié"

                        # Texte complet pour extraction
                        full_text = container.get_text()

                        # Date
                        date_str = ""
                        patterns = [r'Today', r'Yesterday', r'Dec,?\s*\d+', r'Nov,?\s*\d+', r'Jan,?\s*\d+', r'\d+\s+days?\s+ago']
                        for pattern in patterns:
                            match = re.search(pattern, full_text, re.IGNORECASE)
                            if match:
                                date_str = match.group(0)
                                break

                        publication_date = self.translate_date(date_str)

                        # Lieu
                        location = "Somalia"
                        if date_str:
                            date_pos = full_text.find(date_str)
                            if date_pos != -1:
                                after_date = full_text[date_pos + len(date_str):]
                                location = self.clean_location(after_date)

                        # Type de contrat
                        contract_type_en = ""
                        types = ['Full Time', 'Part Time', 'Contract', 'Consultant', 'Temporary', 'Permanent', 'Internship']
                        for t in types:
                            if t in full_text:
                                contract_type_en = t
                                break

                        contract_type = self.translate_contract_type(contract_type_en)

                        # Catégorie
                        category = "Emploi"
                        if contract_type_en:
                            type_pos = full_text.find(contract_type_en)
                            if type_pos != -1:
                                after_type = full_text[type_pos + len(contract_type_en):]
                                lines = [l.strip() for l in after_type.split('\n') if l.strip()]
                                for line in lines:
                                    if line and len(line) > 2 and not line.isdigit():
                                        category = line
                                        break

                        # Vérifier si la date est dans la plage demandée
                        date_in_range = True
                        if publication_date and (start_date_obj or end_date_obj):
                            # Vérifier avec start_date
                            if start_date_obj and publication_date < start_date_obj:
                                date_in_range = False
                                logger.debug(f"   ❌ Job #{idx}: date {publication_date} < start_date {start_date_obj}")
                            # Vérifier avec end_date
                            if end_date_obj and publication_date > end_date_obj:
                                date_in_range = False
                                logger.debug(f"   ❌ Job #{idx}: date {publication_date} > end_date {end_date_obj}")

                        if titre and reference != "SJ-N/A":
                            job = {
                                "reference": reference,
                                "title": titre,
                                "description": f"Recrutement d'un {titre}",
                                "promoter": entreprise,
                                "publication_date": publication_date,
                                "location": location,
                                "url": url,
                                "country": "Somalia",
                                "category": category,
                                "contract_type": contract_type
                            }

                            if date_in_range:
                                all_jobs.append(job)
                                page_jobs_in_range += 1
                                consecutive_out_of_range = 0  # Reset compteur
                                logger.info(f"   ✅ Job #{idx}: {reference} - {titre[:50]} (Date: {publication_date})")
                            else:
                                consecutive_out_of_range += 1
                                logger.info(f"   ⏭️ Job #{idx}: {reference} hors plage de dates (Date: {publication_date})")

                                # Si on a 10 offres consécutives hors plage, on arrête
                                if consecutive_out_of_range >= 10:
                                    logger.info(f"   🛑 ARRÊT: 10 offres consécutives hors de la plage de dates")
                                    driver.quit()
                                    logger.info(f"Scraping terminé: {len(all_jobs)} offres extraites dans la plage de dates")
                                    return all_jobs

                    except Exception as e:
                        logger.warning(f"Erreur extraction job #{idx}: {e}")
                        continue

                # Fin de la boucle des containers de la page
                logger.info(f"   📊 Page {page}: {page_jobs_in_range} offres dans la plage de dates")

                # Si aucune offre dans la plage sur cette page et qu'on a déjà des résultats, on arrête
                if page_jobs_in_range == 0 and len(all_jobs) > 0 and (start_date_obj or end_date_obj):
                    logger.info(f"   🛑 ARRÊT: Aucune offre dans la plage sur cette page")
                    break

            # Fin de la boucle des pages
            driver.quit()
            logger.info(f"Scraping terminé: {len(all_jobs)} offres extraites")
            return all_jobs

        except Exception as e:
            logger.error(f"Erreur scraping: {e}", exc_info=True)
            if 'driver' in locals():
                driver.quit()
            return []

def get_db_connection():
    """Créer une connexion à la base de données"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'postgres_tenders'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'tenders_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres123')
        )
        return conn
    except Exception as e:
        logger.error(f"Erreur connexion DB: {e}")
        return None

def save_to_db(jobs):
    """Sauvegarder les jobs dans PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return {'saved': 0, 'duplicates': 0, 'errors': 0}

    saved = 0
    duplicates = 0
    errors = 0

    try:
        cur = conn.cursor()

        for job in jobs:
            try:
                cur.execute("""
                    INSERT INTO jobs_somalia (
                        reference, title, description, promoter,
                        publication_date, location, url,
                        country, category, contract_type
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reference) DO NOTHING
                    RETURNING id
                """, (
                    job['reference'],
                    job['title'],
                    job['description'],
                    job['promoter'],
                    job['publication_date'],
                    job['location'],
                    job['url'],
                    job['country'],
                    job['category'],
                    job['contract_type']
                ))

                if cur.fetchone():
                    saved += 1
                else:
                    duplicates += 1

            except Exception as e:
                conn.rollback()  # Rollback pour réinitialiser la transaction
                logger.error(f"Erreur sauvegarde job {job.get('reference')}: {e}")
                logger.debug(f"Job data: {job}")
                errors += 1
                continue

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Sauvegarde: {saved} nouveaux, {duplicates} doublons, {errors} erreurs")
        return {'saved': saved, 'duplicates': duplicates, 'errors': errors}

    except Exception as e:
        logger.error(f"Erreur DB: {e}")
        conn.rollback()
        return {'saved': 0, 'duplicates': 0, 'errors': errors}

# ================================================
# API APPELOFFRES.NET FUNCTIONS
# ================================================

def login_to_api():
    """Se connecte à l'API appeloffres.net et récupère le token"""
    global api_token
    try:
        payload = {'email': API_EMAIL, 'password': API_PASSWORD}
        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}

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

            logger.info(f"✅ Connexion API réussie. Token length: {len(api_token) if api_token else 0}")
            return bool(api_token)
        else:
            logger.error(f"❌ Erreur connexion API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception lors de la connexion API: {e}")
        return False

def find_or_create_promoter(promoter_name):
    """Trouve ou crée un promoteur dans l'API appeloffres.net"""
    global api_token, promoters_cache

    if not api_token:
        login_to_api()

    if not api_token:
        logger.error("❌ Impossible de créer promoteur sans token")
        return DEFAULT_PROMOTER_ID

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
            'companyName': promoter_name,  # Requis par l'API
            'countryId': DEFAULT_COUNTRY_ID,
            'address': {  # Doit être un objet
                'streetAddress': 'Mogadishu',
                'city': 'Mogadishu',
                'countryId': DEFAULT_COUNTRY_ID
            },
            'phoneNumber': '+252-1-000000',
            'email': f"{promoter_name.replace(' ', '_').lower()}@somalia.com",  # Email valide
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

        # Si échec, créer un promoteur générique "Somalia Employer"
        generic_name = "Somalia Employer"
        if generic_name.lower() in promoters_cache:
            return promoters_cache[generic_name.lower()]

        generic_payload = {
            'name': generic_name,
            'companyName': generic_name,
            'countryId': DEFAULT_COUNTRY_ID,
            'address': {
                'streetAddress': 'Mogadishu',
                'city': 'Mogadishu',
                'countryId': DEFAULT_COUNTRY_ID
            },
            'phoneNumber': '+252-1-000000',
            'email': 'info@somaliaemployer.com',
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

def send_job_to_api(job_data):
    """Envoie un emploi Somalia à l'API appeloffres.net"""
    global api_token
    max_retries = 3

    for attempt in range(max_retries):
        if not api_token:
            if not login_to_api():
                return False

        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT
        }

        # Préparer les dates
        pub_date = job_data.get('publication_date')
        if isinstance(pub_date, str):
            pub_date_obj = datetime.fromisoformat(pub_date.replace('Z', ''))
            publication_date = pub_date_obj.isoformat()
        else:
            pub_date_obj = pub_date if pub_date else datetime.now()
            publication_date = pub_date_obj.isoformat()

        # Ajouter 30 jours pour expiration
        exp_date_obj = pub_date_obj + timedelta(days=30)
        expiration_date = exp_date_obj.isoformat()

        # Trouver ou créer le promoteur
        promoter_name = job_data.get('promoter', 'Somalia Company')
        promoter_id = find_or_create_promoter(promoter_name)

        # Préparer le payload
        api_payload = {
            'title': job_data.get('title', '')[:255],
            'reference': job_data.get('reference', ''),
            'description': job_data.get('description', ''),
            'publicationDate': publication_date,
            'startBiddingDate': publication_date,
            'expirationDate': expiration_date,
            'openingBidsDate': expiration_date,
            'avisId': DEFAULT_AVIS_ID,
            'sourceId': DEFAULT_SOURCE_ID,
            'promoterId': promoter_id,
            'type': 'international',
            'nature': 'public',
            'isEnabled': True,
            'images': [],
            'addresses': [],  # Champ requis par l'API
            'batches': [],  # Champ requis par l'API
            'specificationsReceivingAddress': job_data.get('url', ''),
            'fundingSourceType': 'international',
            'fundingSource': promoter_name,
            'isMultiCurrency': False,
            'activitiesIds': [463],  # Services par défaut
            'countriesIds': [DEFAULT_COUNTRY_ID]
        }

        try:
            logger.info(f"📤 Envoi emploi {job_data.get('reference')} à l'API...")
            response = requests.post(TENDER_ENDPOINT, json=api_payload, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                logger.info(f"✅ Emploi {job_data.get('reference')} envoyé avec succès")
                return True
            elif response.status_code == 401:
                logger.warning("⚠️ Token expiré, reconnexion...")
                api_token = None
                continue
            else:
                logger.error(f"❌ Erreur API: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Exception envoi API: {e}")
            return False

    return False

# Routes Flask
@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'service': 'Somalia Jobs Scraper'}), 200

@app.route('/scrape', methods=['POST'])
def scrape():
    """Route principale de scraping"""
    try:
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        max_pages = data.get('max_pages', 10)

        logger.info("Démarrage scraping SomaliaJobs")
        if start_date:
            logger.info(f"Paramètre start_date: {start_date}")
        if end_date:
            logger.info(f"Paramètre end_date: {end_date}")
        logger.info(f"Paramètre max_pages: {max_pages}")

        scraper = SomaliaJobsScraper()
        jobs = scraper.scrape_jobs(start_date=start_date, end_date=end_date, max_pages=max_pages)

        if not jobs:
            return jsonify({
                'success': False,
                'message': 'Aucun emploi trouvé',
                'stats': {'total': 0, 'saved': 0, 'duplicates': 0, 'errors': 0}
            }), 200

        # Sauvegarde dans PostgreSQL
        stats = save_to_db(jobs)
        stats['total'] = len(jobs)

        return jsonify({
            'success': True,
            'message': f'{stats["saved"]} nouveaux emplois extraits',
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Erreur scraping: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/jobs', methods=['GET'])
def get_jobs():
    """Récupérer les emplois"""
    try:
        status = request.args.get('status', 'pending')
        limit = int(request.args.get('limit', 100))

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        if status == 'all':
            cur.execute("""
                SELECT * FROM jobs_somalia
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT * FROM jobs_somalia
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (status, limit))

        jobs = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'count': len(jobs),
            'jobs': jobs
        }), 200

    except Exception as e:
        logger.error(f"Erreur récupération jobs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Statistiques des emplois"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM jobs_somalia")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM jobs_somalia WHERE status = 'pending'")
        pending = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM jobs_somalia WHERE status = 'validated'")
        validated = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM jobs_somalia WHERE status = 'failed'")
        failed = cur.fetchone()[0]

        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'pending': pending,
                'validated': validated,
                'failed': failed
            }
        }), 200

    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/validate/<reference>', methods=['POST'])
def validate_job(reference):
    """Valider un emploi et l'envoyer à l'API appeloffres.net"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer l'emploi
        cur.execute("SELECT * FROM jobs_somalia WHERE reference = %s", (reference,))
        job = cur.fetchone()

        if not job:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Emploi non trouvé'}), 404

        # Envoyer à l'API appeloffres.net
        logger.info(f"📤 Envoi de l'emploi {reference} vers l'API appeloffres.net...")
        api_success = send_job_to_api(dict(job))

        if not api_success:
            logger.error(f"❌ Échec de l'envoi API pour {reference}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': "Échec de l'envoi vers l'API appeloffres.net"
            }), 500

        # Marquer comme validé dans la DB
        cur.execute("""
            UPDATE jobs_somalia
            SET status = 'validated', updated_at = CURRENT_TIMESTAMP
            WHERE reference = %s
        """, (reference,))

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✅ Emploi {reference} validé ET envoyé à l'API")

        return jsonify({
            'success': True,
            'message': f'Emploi {reference} validé et envoyé à l\'API avec succès'
        }), 200

    except Exception as e:
        logger.error(f"Erreur validation {reference}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete/<reference>', methods=['DELETE'])
def delete_job(reference):
    """Supprimer un emploi spécifique"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor()

        cur.execute("DELETE FROM jobs_somalia WHERE reference = %s", (reference,))
        deleted_count = cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        if deleted_count == 0:
            return jsonify({'success': False, 'message': 'Emploi non trouvé'}), 404

        logger.info(f"🗑️ Emploi {reference} supprimé")

        return jsonify({
            'success': True,
            'message': f'Emploi {reference} supprimé'
        }), 200

    except Exception as e:
        logger.error(f"Erreur suppression {reference}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_all', methods=['POST'])
def delete_all():
    """Supprimer tous les emplois en attente"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor()

        # Supprimer tous les jobs avec status = 'pending'
        cur.execute("DELETE FROM jobs_somalia WHERE status = 'pending'")
        deleted_count = cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✅ {deleted_count} emplois supprimés")

        return jsonify({
            'success': True,
            'message': f'{deleted_count} emplois supprimés',
            'count': deleted_count
        }), 200

    except Exception as e:
        logger.error(f"Erreur delete_all: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5019))
    logger.info(f"Démarrage serveur Somalia Jobs sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
