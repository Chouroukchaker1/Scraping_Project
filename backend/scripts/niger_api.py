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
            promoteur_tag = annonce_div.find('a', class_='ss_miz_f', href=re.compile(r'recherche_offre-structure-'))
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

            # Recherche avec icônes pour dates plus précises
            date_tags = annonce_div.find_all('i', class_=re.compile(r'fa-calendar'))
            for date_tag in date_tags:
                parent_text = date_tag.parent.get_text()
                date_match = re.search(date_pattern, parent_text)
                if date_match:
                    if 'calendar-times-o' in date_tag.get('class', []):
                        date_expiration = date_match.group(1)
                    else:
                        date_publication = date_match.group(1)

            # Localisation
            lieu = "Niger"
            lieu_tag = annonce_div.find('i', class_='fa-map-marker')
            if lieu_tag:
                lieu_text = lieu_tag.parent.get_text(strip=True)
                if lieu_text:
                    lieu = lieu_text

            # Type d'annonce/catégorie
            category = "Emploi"
            type_tag = annonce_div.find('a', class_='ss_miz_f', href=re.compile(r'recherche_offre-categorie-'))
            if type_tag:
                category = type_tag.get_text(strip=True)

            # Type de contrat
            contract_type = "Non spécifié"
            contract_tag = annonce_div.find('a', href=re.compile(r'recherche_offre-categorie-'))
            if contract_tag:
                contract_text = contract_tag.get_text(strip=True).lower()
                if 'cdi' in contract_text:
                    contract_type = "CDI"
                elif 'cdd' in contract_text:
                    contract_type = "CDD"
                elif 'stage' in contract_text:
                    contract_type = "Stage"
                elif 'consultant' in contract_text or 'freelance' in contract_text:
                    contract_type = "Consultant"

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
                "category": category,
                "contract_type": contract_type
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

            # Trouver les annonces avec la bonne classe
            annonces_divs = soup.find_all('div', class_='div_rz_ance_gnral')

            logger.info(f"Nombre de divs trouvés: {len(annonces_divs)}")

            jobs = []
            for idx, annonce_div in enumerate(annonces_divs):
                job = self.extract_annonce_data(annonce_div)
                if job:
                    logger.debug(f"Job extrait #{idx+1}: ref={job.get('reference')}, titre={job.get('title', '')[:50]}")
                    if job['reference'] != "NE-N/A":
                        jobs.append(job)
                    else:
                        logger.warning(f"Job #{idx+1} ignoré: référence=NE-N/A")
                else:
                    logger.warning(f"Job #{idx+1}: extraction a retourné None")

            logger.info(f"Page {page_num}: {len(jobs)} emplois extraits")
            return jobs

        except Exception as e:
            logger.error(f"Erreur scraping page {page_num}: {e}")
            return []

    def scrape_all_pages(self, max_pages=5, start_date=None, end_date=None):
        """Scraper toutes les pages avec filtrage par date"""
        logger.info(f"=== DEBUT scrape_all_pages, max_pages={max_pages} ===")

        # Convertir les dates en objets date
        start_date_obj = None
        end_date_obj = None
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                logger.info(f"Filtre date début: {start_date_obj}")
            except:
                logger.warning(f"Date de début invalide: {start_date}")

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                logger.info(f"Filtre date fin: {end_date_obj}")
            except:
                logger.warning(f"Date de fin invalide: {end_date}")

        all_jobs = []
        seen_references = set()
        consecutive_out_of_range = 0

        # Scraper la page principale
        logger.info("📄 Scraping page principale...")
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            annonces_divs = soup.find_all('div', class_='div_rz_ance_gnral')

            for idx, annonce_div in enumerate(annonces_divs, 1):
                job = self.extract_annonce_data(annonce_div)
                if job and job['reference'] != "NE-N/A" and job['reference'] not in seen_references:
                    # Vérifier si la date est dans la plage
                    date_in_range = True
                    if job.get('publication_date') and (start_date_obj or end_date_obj):
                        try:
                            # Convertir la date string en objet date pour comparaison
                            pub_date = datetime.strptime(job['publication_date'], '%Y-%m-%d').date()
                            if start_date_obj and pub_date < start_date_obj:
                                date_in_range = False
                            if end_date_obj and pub_date > end_date_obj:
                                date_in_range = False
                        except:
                            logger.warning(f"Date invalide pour job {job['reference']}: {job.get('publication_date')}")
                            date_in_range = True  # Inclure les jobs avec dates invalides

                    if date_in_range:
                        all_jobs.append(job)
                        seen_references.add(job['reference'])
                        consecutive_out_of_range = 0
                        logger.info(f"   ✅ Job #{idx}: {job['reference']} - {job['title'][:50]} (Date: {job.get('publication_date')})")
                    else:
                        consecutive_out_of_range += 1
                        logger.info(f"   ⏭️ Job #{idx}: {job['reference']} hors plage de dates (Date: {job.get('publication_date')})")

                        # Arrêt après 10 jobs consécutifs hors plage
                        if consecutive_out_of_range >= 10:
                            logger.info(f"   🛑 ARRÊT: 10 offres consécutives hors de la plage de dates")
                            logger.info(f"Scraping terminé: {len(all_jobs)} emplois extraits dans la plage de dates")
                            return all_jobs

            logger.info(f"📊 Page principale: {len(all_jobs)} emplois dans la plage de dates")
        except Exception as e:
            logger.error(f"Erreur scraping page principale: {e}")

        # Scraper les pages d'annonces
        for page in range(1, max_pages + 1):
            logger.info(f"📄 Scraping page {page}...")
            jobs = self.scrape_page(page)

            if not jobs:
                logger.info("Page vide, arrêt du scraping")
                break

            page_jobs_in_range = 0
            # Vérifier les doublons et filtrer par date
            for idx, job in enumerate(jobs, 1):
                if job['reference'] not in seen_references:
                    # Vérifier si la date est dans la plage
                    date_in_range = True
                    if job.get('publication_date') and (start_date_obj or end_date_obj):
                        try:
                            # Convertir la date string en objet date pour comparaison
                            pub_date = datetime.strptime(job['publication_date'], '%Y-%m-%d').date()
                            if start_date_obj and pub_date < start_date_obj:
                                date_in_range = False
                            if end_date_obj and pub_date > end_date_obj:
                                date_in_range = False
                        except:
                            logger.warning(f"Date invalide pour job {job['reference']}: {job.get('publication_date')}")
                            date_in_range = True  # Inclure les jobs avec dates invalides

                    if date_in_range:
                        all_jobs.append(job)
                        seen_references.add(job['reference'])
                        page_jobs_in_range += 1
                        consecutive_out_of_range = 0
                        logger.info(f"   ✅ Job #{idx}: {job['reference']} - {job['title'][:50]} (Date: {job.get('publication_date')})")
                    else:
                        consecutive_out_of_range += 1
                        logger.info(f"   ⏭️ Job #{idx}: {job['reference']} hors plage de dates (Date: {job.get('publication_date')})")

                        # Arrêt après 10 jobs consécutifs hors plage
                        if consecutive_out_of_range >= 10:
                            logger.info(f"   🛑 ARRÊT: 10 offres consécutives hors de la plage de dates")
                            logger.info(f"Scraping terminé: {len(all_jobs)} emplois extraits dans la plage de dates")
                            return all_jobs

            logger.info(f"📊 Page {page}: {page_jobs_in_range} emplois dans la plage de dates")

            # Si aucun emploi dans la plage sur toute la page, on arrête
            if page_jobs_in_range == 0 and (start_date_obj or end_date_obj):
                logger.info(f"🛑 ARRÊT: Page complète sans emplois dans la plage de dates")
                break

            time.sleep(1)  # Pause entre les pages

        logger.info(f"Scraping terminé: {len(all_jobs)} emplois extraits")
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
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        logger.info(f"Démarrage scraping Niger - max_pages: {max_pages}")
        if start_date:
            logger.info(f"Paramètre start_date: {start_date}")
        if end_date:
            logger.info(f"Paramètre end_date: {end_date}")

        scraper = NigerEmploiScraper()
        jobs = scraper.scrape_all_pages(max_pages=max_pages, start_date=start_date, end_date=end_date)

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

@app.route('/validate/<reference>', methods=['POST'])
def validate_job(reference):
    """Valider un emploi et marquer comme validé"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur DB'}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer l'emploi
        cur.execute("SELECT * FROM jobs_niger WHERE reference = %s", (reference,))
        job = cur.fetchone()

        if not job:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Emploi non trouvé'}), 404

        # Marquer comme validé dans la DB
        cur.execute("""
            UPDATE jobs_niger
            SET status = 'validated', updated_at = CURRENT_TIMESTAMP
            WHERE reference = %s
        """, (reference,))

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✅ Emploi {reference} validé")

        return jsonify({
            'success': True,
            'message': f'Emploi {reference} validé avec succès'
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

        # Supprimer l'emploi
        cur.execute("DELETE FROM jobs_niger WHERE reference = %s", (reference,))
        deleted = cur.rowcount > 0

        conn.commit()
        cur.close()
        conn.close()

        if deleted:
            logger.info(f"✅ Emploi {reference} supprimé")
            return jsonify({
                'success': True,
                'message': f'Emploi {reference} supprimé'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Emploi non trouvé'
            }), 404

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
        cur.execute("DELETE FROM jobs_niger WHERE status = 'pending'")
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
        logger.error(f"Erreur suppression: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5018))
    logger.info(f"Démarrage serveur Niger Emploi sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
