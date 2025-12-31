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
from datetime import datetime
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

class NigerEmploiScraper:
    def __init__(self):
        self.base_url = "https://www.nigeremploi.com/"
        self.annonces_url = "https://www.nigeremploi.com/emplois-annonces.html"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })

    def parse_date(self, date_str):
        """Convertir une date au format PostgreSQL"""
        if not date_str:
            return None

        date_formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y']

        for date_format in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), date_format)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def extract_annonce_data(self, annonce_div):
        """Extrait les données d'une annonce depuis le HTML"""
        try:
            # Titre et lien
            titre_tag = annonce_div.find('span', class_='txt_fs11_c')
            titre = titre_tag.get_text(strip=True) if titre_tag else "Non spécifié"

            lien_tag = annonce_div.find('a', href=True)
            lien = lien_tag['href'] if lien_tag else ""
            if lien and not lien.startswith('http'):
                lien = self.base_url.rstrip('/') + '/' + lien.lstrip('/')

            # Référence
            reference = "NE-N/A"
            if lien:
                match = re.search(r'annonce-details-(\d+)', lien)
                if match:
                    reference = f"NE-{match.group(1)}"

            # Promoteur/Recruteur
            promoteur = "Non spécifié"
            promoteur_tag = annonce_div.find('a', class_='ss_miz_f')
            if promoteur_tag:
                promoteur = promoteur_tag.get('title', '').replace('Recruteur: ', '')
                if not promoteur or promoteur == 'Recruteur: ':
                    promoteur = promoteur_tag.get_text(strip=True)

            # Dates
            date_publication = ""
            date_expiration = ""

            all_text = annonce_div.get_text()
            date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            dates = re.findall(date_pattern, all_text)

            if len(dates) >= 1:
                date_publication = dates[0]
            if len(dates) >= 2:
                date_expiration = dates[1]

            # Localisation
            lieu = "Niger"
            lieu_tag = annonce_div.find('i', class_='fa-map-marker')
            if lieu_tag:
                lieu_text = lieu_tag.parent.get_text(strip=True)
                if lieu_text:
                    lieu = lieu_text

            job = {
                "reference": reference,
                "title": titre,
                "description": titre,
                "promoter": promoteur,
                "publication_date": self.parse_date(date_publication),
                "expiration_date": self.parse_date(date_expiration),
                "location": lieu,
                "url": lien,
                "country": "Niger",
                "category": "Emploi",
                "contract_type": "Non spécifié"
            }

            return job

        except Exception as e:
            logger.warning(f"Erreur extraction annonce: {e}")
            return None

    def scrape_page(self, page_num=1):
        """Scraper une page spécifique"""
        try:
            if page_num == 1:
                url = self.annonces_url
            else:
                url = f"{self.annonces_url}?page={page_num}"

            logger.info(f"Scraping page {page_num}: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Trouver les annonces
            annonces_divs = soup.find_all('div', class_='annonces_structure')
            if not annonces_divs:
                annonces_divs = soup.find_all('div', class_=re.compile(r'annonce'))

            jobs = []
            for annonce_div in annonces_divs:
                job = self.extract_annonce_data(annonce_div)
                if job:
                    jobs.append(job)

            logger.info(f"Page {page_num}: {len(jobs)} emplois extraits")
            return jobs

        except Exception as e:
            logger.error(f"Erreur scraping page {page_num}: {e}")
            return []

    def scrape_all_pages(self, max_pages=5):
        """Scraper toutes les pages"""
        all_jobs = []

        for page in range(1, max_pages + 1):
            jobs = self.scrape_page(page)

            if not jobs:
                logger.info("Page vide, arrêt du scraping")
                break

            all_jobs.extend(jobs)
            time.sleep(1)  # Pause entre les pages

        logger.info(f"Total: {len(all_jobs)} emplois extraits")
        return all_jobs

def get_db_connection():
    """Créer une connexion à la base de données"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erreur connexion DB: {e}")
        return None

def save_to_db(jobs):
    """Sauvegarder les emplois dans PostgreSQL"""
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
                    INSERT INTO jobs_niger (
                        reference, title, description, promoter,
                        publication_date, expiration_date, location, url,
                        country, category, contract_type
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reference) DO NOTHING
                    RETURNING id
                """, (
                    job['reference'],
                    job['title'],
                    job['description'],
                    job['promoter'],
                    job['publication_date'],
                    job['expiration_date'],
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
                logger.error(f"Erreur sauvegarde job {job['reference']}: {e}")
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

# Routes Flask
@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'service': 'Niger Emploi Scraper'}), 200

@app.route('/scrape', methods=['POST'])
def scrape():
    """Route principale de scraping"""
    try:
        data = request.get_json() or {}
        max_pages = data.get('max_pages', 5)

        logger.info(f"Démarrage scraping Niger - max_pages: {max_pages}")

        scraper = NigerEmploiScraper()
        jobs = scraper.scrape_all_pages(max_pages=max_pages)

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
            cur.execute("SELECT * FROM jobs_niger ORDER BY created_at DESC LIMIT %s", (limit,))
        else:
            cur.execute("SELECT * FROM jobs_niger WHERE status = %s ORDER BY created_at DESC LIMIT %s", (status, limit))

        jobs = cur.fetchall()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'jobs': [dict(j) for j in jobs],
            'count': len(jobs)
        }), 200

    except Exception as e:
        logger.error(f"Erreur récupération jobs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Statistiques des emplois"""
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
            FROM jobs_niger
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5018))
    logger.info(f"Démarrage serveur Niger Emploi sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
