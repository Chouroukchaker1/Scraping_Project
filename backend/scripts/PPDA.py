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

# Configuration AppelOffres API
APPELOFFRES_API = {
    'base_url': os.getenv('APPELOFFRES_API_URL', 'https://tunisie.appeloffres.tn/api'),
    'token': os.getenv('APPELOFFRES_API_TOKEN', '')
}

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

def send_to_api(tender):
    """Envoyer un appel d'offres à l'API AppelOffres"""
    try:
        api_data = {
            'numero_reference': tender['reference'],
            'titre': tender['title'],
            'description': tender['description'],
            'promoteur': tender['promoter'],
            'date_publication': tender['publication_date'],
            'date_expiration': tender['expiration_date'],
            'photo': tender['document_url'],
            'pays': tender['country'],
            'nature': tender['nature'],
            'type': tender['type'],
            'type_financement': tender['funding_source_type'],
            'caution': tender['caution']
        }

        headers = {
            'Authorization': f"Bearer {APPELOFFRES_API['token']}",
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f"{APPELOFFRES_API['base_url']}/appels-offres",
            json=api_data,
            headers=headers,
            timeout=30
        )

        if response.status_code in [200, 201]:
            logger.info(f"✅ API success: {tender['reference']}")
            return {'success': True, 'data': response.json()}
        else:
            logger.error(f"❌ API error {response.status_code}: {tender['reference']}")
            return {'success': False, 'error': response.text}

    except Exception as e:
        logger.error(f"Erreur envoi API: {e}")
        return {'success': False, 'error': str(e)}

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
