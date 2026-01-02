# boamp_official.py - Scraper BOAMP Officiel via API OpenData
import os
import json
import logging
import re
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass, asdict
from typing import Optional, List
import time
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_boamp"

# Configuration API BOAMP
BOAMP_API_URL = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
BOAMP_PDF_BASE_URL = "https://www.boamp.fr/telechargements/FILES/PDF"
DEFAULT_SOURCE_ID = 1674  # Source ID BOAMP

# Configuration API Appeloffres.net
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
API_EMAIL = os.getenv("API_EMAIL", "oumayma.dahmani@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "Ah0F553KKu0A")
USER_AGENT = "TendersScraper/1.0"

# Cache pour les activités
activities_cache = []

# IDs pour BOAMP (France)
DEFAULT_PROMOTER_ID = int(os.getenv("DEFAULT_PROMOTER_ID", "223472"))  # Promoteur par défaut tunipages
DEFAULT_AVIS_ID = int(os.getenv("DEFAULT_AVIS_ID", "11"))
DEFAULT_COUNTRY_ID = 70  # France = 70 (pas 73)

# Token API global
api_token = None
promoters_cache = {}  # Cache des promoteurs {nom_normalisé: promoter_id}

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================================
# POSTGRESQL FUNCTIONS
# ================================================

def get_db_connection():
    """Créer une connexion PostgreSQL avec encodage UTF-8"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        client_encoding='UTF8'
    )
    # Forcer l'encodage UTF-8 pour la connexion
    conn.set_client_encoding('UTF8')
    return conn

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

def insert_tender(data):
    """Insère une offre dans PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (
                reference, description, description_fr, publication_date, expiration_date,
                promoter, source_id, avis_id, external_url, montant, nature,
                country, business_sector, activity, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reference) DO NOTHING
        """, (
            data.get('reference'),
            data.get('description'),
            data.get('description_fr'),
            data.get('publication_date'),
            data.get('expiration_date'),
            data.get('promoter'),
            data.get('source_id', DEFAULT_SOURCE_ID),
            data.get('avis_id', 1),
            data.get('external_url'),
            data.get('montant'),
            data.get('nature'),
            data.get('country', 'France'),
            data.get('business_sector'),
            data.get('activity'),
            data.get('status', 'pending')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Erreur insertion: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_existing_references():
    """Récupère toutes les références existantes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT reference FROM {TABLE_NAME}")
        return {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

# ================================================
# BOAMP SCRAPER
# ================================================

class BOAMPScraper:
    def __init__(self):
        self.api_url = BOAMP_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        })
        self.is_processing = False
        self.offres_cache = []
        self.load_pending_offers()
        logger.info(f"✅ BOAMP Scraper initialisé - {len(self.offres_cache)} offres pending")

    def load_pending_offers(self):
        """Charge les offres pending depuis PostgreSQL"""
        try:
            pending = get_all_tenders(status="pending")
            # Mapper les champs pour le frontend Dashboard (camelCase)
            self.offres_cache = []
            for offre in pending:
                # Formater les dates pour l'affichage
                pub_date = offre.get('publication_date')
                exp_date = offre.get('expiration_date')

                # Convertir timestamp PostgreSQL vers format court DD/MM/YYYY
                if pub_date and isinstance(pub_date, str):
                    try:
                        pub_date = datetime.strptime(pub_date.split()[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        pass
                if exp_date and isinstance(exp_date, str):
                    try:
                        exp_date = datetime.strptime(exp_date.split()[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        pass

                mapped = {
                    'reference': offre.get('reference'),
                    'description': offre.get('description'),
                    'description_fr': offre.get('description_fr'),
                    'publicationDate': pub_date,  # camelCase pour frontend
                    'expirationDate': exp_date,   # camelCase pour frontend
                    'publication_date': offre.get('publication_date'),  # snake_case pour backend
                    'expiration_date': offre.get('expiration_date'),    # snake_case pour backend
                    'promoter': offre.get('promoter'),
                    'source_id': offre.get('source_id'),
                    'external_url': offre.get('external_url'),
                    'url_source': offre.get('external_url'),  # Alias pour Dashboard
                    'montant': offre.get('montant'),
                    'nature': offre.get('nature'),
                    'country': offre.get('country'),
                    'pays': offre.get('country'),  # Alias pour Dashboard
                    'business_sector': offre.get('business_sector'),
                    'secteur_activite': offre.get('business_sector'),  # Alias pour Dashboard
                    'activity': offre.get('activity'),
                    'status': offre.get('status'),
                    'mots_cles_detectes': []  # Dashboard attend ce champ
                }
                self.offres_cache.append(mapped)
            logger.info(f"{len(self.offres_cache)} offres pending chargées")
        except Exception as e:
            logger.error(f"Erreur chargement pending: {e}")

    def scrape(self, start_date=None, end_date=None, limit=None):
        """Scrape BOAMP via API officielle avec pagination automatique pour extraire TOUTES les offres"""
        self.is_processing = True
        existing_refs = get_existing_references()
        new_count = 0
        offset = 0
        batch_size = 100  # L'API limite à 100 par requête
        total_fetched = 0
        max_pages = 50  # Maximum 50 pages = 5000 offres

        try:
            # Convertir les dates pour filtrage côté serveur
            from datetime import datetime
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

            logger.info(f"🚀 Scraping BOAMP du {start_date} au {end_date} - TOUTES LES OFFRES")
            logger.info(f"⚠️ Filtrage côté serveur pour récupérer TOUTES les offres de la période")

            # PAGINATION AUTOMATIQUE - Continue jusqu'à avoir toutes les offres de la période
            page_count = 0
            offers_in_range = 0
            stop_scraping = False

            while page_count < max_pages and not stop_scraping:
                page_count += 1

                # Paramètres API - Tri par date DESC (pas de filtre where car bugué)
                params = {
                    "limit": batch_size,
                    "offset": offset,
                    "order_by": "dateparution DESC"  # Les plus récentes en premier
                }

                # Requête API
                logger.info(f"📡 Page {page_count} - offset: {offset}, limit: {batch_size}")
                response = self.session.get(self.api_url, params=params, timeout=30)
                response.raise_for_status()

                # Gérer l'encodage - L'API BOAMP peut renvoyer du Latin-1 mal encodé
                try:
                    # Tenter décodage UTF-8 normal
                    data = response.json()
                except UnicodeDecodeError:
                    # Si échec, décoder manuellement en latin-1 puis reconvertir en UTF-8
                    text_content = response.content.decode('latin-1')
                    data = json.loads(text_content)
                total_count = data.get('total_count', 0)
                records = data.get('results', [])

                if not records:
                    logger.info(f"⏹️  Plus d'offres à récupérer (offset: {offset})")
                    break

                total_fetched += len(records)
                logger.info(f"📊 Page {offset // batch_size + 1}: {len(records)} annonces récupérées (total disponible: {total_count}, déjà récupéré: {total_fetched})")

                # Traiter les offres de cette page
                page_in_range_count = 0
                for record in records:
                    try:
                        # Vérifier si l'offre est dans la plage de dates demandée
                        date_pub_str = record.get('dateparution', '')
                        if date_pub_str and (start_date_obj or end_date_obj):
                            try:
                                # La date dans l'API est au format YYYY-MM-DD
                                date_pub = datetime.strptime(date_pub_str, '%Y-%m-%d').date()

                                # Si la date est antérieure à start_date, on a dépassé la plage
                                if start_date_obj and date_pub < start_date_obj:
                                    logger.info(f"⏹️  Offre {record.get('idweb')} ({date_pub}) hors plage ({start_date} - {end_date}), arrêt")
                                    stop_scraping = True
                                    break

                                # Si la date est dans la plage, continuer
                                if start_date_obj and date_pub < start_date_obj:
                                    continue  # Trop vieille
                                if end_date_obj and date_pub > end_date_obj:
                                    continue  # Trop récente
                            except ValueError:
                                pass  # Continuer si problème de parsing

                        # Extraire les données
                        ref = record.get('idweb') or record.get('id')
                        if not ref or ref in existing_refs:
                            continue

                        page_in_range_count += 1
                        offers_in_range += 1

                        # Nettoyer les secteurs - convertir le format PostgreSQL array en texte simple
                        descripteur = record.get('descripteur_libelle', '')
                        if descripteur:
                            # Si c'est au format PostgreSQL array {item1,item2}, le nettoyer
                            if isinstance(descripteur, str):
                                descripteur = descripteur.strip('{}').replace('"', '')
                            # Si c'est une liste, joindre
                            elif isinstance(descripteur, list):
                                descripteur = ', '.join(str(d) for d in descripteur)

                        type_marche = record.get('type_marche', '')
                        if isinstance(type_marche, str):
                            type_marche = type_marche.strip('{}').replace('"', '')
                        elif isinstance(type_marche, list):
                            type_marche = ', '.join(str(t) for t in type_marche)

                        # Mapper les champs avec encodage UTF-8 correct
                        tender_data = {
                            'reference': str(ref),
                            'description': (record.get('objet', '') or '')[:500],
                            'description_fr': record.get('objet', '') or '',
                            'publication_date': self.parse_date(record.get('dateparution')),
                            'expiration_date': self.parse_date(record.get('datelimitereponse')),
                            'promoter': record.get('nomacheteur', '') or '',
                            'source_id': DEFAULT_SOURCE_ID,
                            'external_url': f"https://www.boamp.fr/avis/detail/{ref}",
                            'montant': '',
                            'nature': record.get('nature', '') or '',
                            'country': 'France',
                            'business_sector': descripteur,
                            'activity': type_marche,
                            'status': 'pending'
                        }

                        if insert_tender(tender_data):
                            new_count += 1
                            self.offres_cache.append(tender_data)
                            logger.info(f"✅ Nouvelle offre: {ref}")

                    except Exception as e:
                        logger.error(f"Erreur traitement annonce: {e}")
                        continue

                # Log pour cette page
                logger.info(f"📋 Page {page_count}: {page_in_range_count} offres dans la plage de dates sur {len(records)}")

                # Si stop_scraping activé (date hors plage), arrêter
                if stop_scraping:
                    logger.info(f"🛑 Arrêt: offres hors plage de dates détectées")
                    break

                # Si aucune offre dans la plage sur cette page, continuer quand même (au cas où)
                # Mais si 3 pages consécutives sans offres, arrêter
                if page_in_range_count == 0:
                    logger.warning(f"⚠️ Aucune offre dans la plage sur cette page")

                # Si limit spécifié par l'utilisateur et atteint, arrêter
                if limit and new_count >= limit:
                    logger.info(f"✅ Limite utilisateur atteinte ({new_count}/{limit})")
                    break

                # Passer à la page suivante
                offset += batch_size
                time.sleep(0.5)  # Petit délai pour ne pas surcharger l'API

            logger.info(f"✅ Scraping terminé: {new_count} nouvelles offres ajoutées")
            logger.info(f"📊 Statistiques: {offers_in_range} offres trouvées dans la plage {start_date} - {end_date}, {new_count} ajoutées (nouvelles)")
            return {"success": True, "message": f"{new_count} nouvelles offres ajoutées ({offers_in_range} trouvées dans la période)", "count": new_count, "total_in_range": offers_in_range}

        except Exception as e:
            logger.error(f"❌ Erreur scraping: {e}")
            return {"success": False, "error": str(e)}
        finally:
            self.is_processing = False

    def parse_date(self, date_str):
        """Parse une date ISO vers format PostgreSQL"""
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return None

    def get_offres_cache(self, page=1, limit=10):
        """Retourne les offres en cache avec pagination"""
        total = len(self.offres_cache)
        start = (page - 1) * limit
        end = start + limit

        return {
            "offres": self.offres_cache[start:end],
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit,
            "processing": self.is_processing
        }

    def extract_images_from_boamp(self, reference):
        """Extrait les images/documents depuis une offre BOAMP"""
        images = []
        try:
            # L'API BOAMP fournit un lien vers les documents dans le champ 'liens'
            # Essayer de récupérer les documents depuis l'API
            params = {
                "where": f"idweb='{reference}'",
                "limit": 1
            }
            response = self.session.get(self.api_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = data.get('results', [])
            if results:
                record = results[0]
                # Chercher les liens vers documents/images
                # L'API BOAMP peut fournir des URLs dans différents champs
                liens = record.get('liens') or record.get('liens_dce') or []
                if isinstance(liens, list):
                    for lien in liens[:5]:  # Limiter à 5 images max
                        if isinstance(lien, dict):
                            url = lien.get('url') or lien.get('href')
                            if url and ('.pdf' in url.lower() or '.jpg' in url.lower() or '.png' in url.lower()):
                                images.append(url)
                        elif isinstance(lien, str) and lien.startswith('http'):
                            images.append(lien)

                # Fallback: utiliser le lien externe standard
                if not images:
                    external_url = f"https://www.boamp.fr/avis/detail/{reference}"
                    logger.info(f"📄 Pas d'images trouvées via API pour {reference}, utiliser: {external_url}")

            logger.info(f"🖼️  {len(images)} images extraites pour {reference}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction images pour {reference}: {e}")

        return images

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
            # Essayer plusieurs champs possibles pour le token (comme expertise.py)
            api_token = (
                data.get('accessToken') or
                data.get('access_token') or
                data.get('token') or
                data.get('data', {}).get('accessToken') or
                data.get('data', {}).get('access_token') or
                data.get('data', {}).get('token') or
                response.headers.get('x-access-token') or
                response.headers.get('Authorization')
            )

            # Nettoyer le token si format "Bearer xxx"
            if isinstance(api_token, str) and api_token.startswith('Bearer '):
                api_token = api_token.split(' ')[1]

            logger.info(f"✅ Connexion API réussie. Token length: {len(api_token) if api_token else 0}")
            if api_token:
                logger.info(f"🔑 Token trouvé: {api_token[:20]}...")
            else:
                logger.error(f"⚠️ Token vide. Réponse API: {data}")
            return bool(api_token)
        else:
            logger.error(f"❌ Erreur connexion API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception lors de la connexion API: {e}")
        return False

def find_closest_activity(business_sector):
    """Trouve l'activité la plus proche basée sur les mots-clés du secteur BOAMP"""

    if not business_sector:
        return []

    business_sector_lower = business_sector.lower()
    matched_ids = set()

    # Mapping complet des secteurs BOAMP vers les IDs d'activités de l'API
    # Ces IDs correspondent aux vraies activités dans appeloffres.net
    sector_mapping = {
        # Travaux/BTP/Construction (461)
        'travaux': 461, 'construction': 461, 'btp': 461, 'bâtiment': 461, 'batiment': 461,
        'voirie': 461, 'route': 461, 'chaussée': 461, 'chaussee': 461,
        'terrassement': 461, 'signalisation': 461, 'aménagement': 461, 'amenagement': 461,
        'électricité': 461, 'electricite': 461, 'electrique': 461, 'éclairage': 461, 'eclairage': 461,
        'plomberie': 461, 'chauffage': 461, 'climatisation': 461,
        'peinture': 461, 'menuiserie': 461, 'maçonnerie': 461, 'maconnerie': 461,
        'espaces verts': 461, 'jardinage': 461, 'paysagiste': 461,
        'câblage': 461, 'cablage': 461, 'réseaux': 461, 'reseaux': 461,
        'amiante': 461, 'désamiantage': 461, 'desamiantage': 461,

        # Fournitures (462)
        'fournitures': 462, 'fourniture': 462, 'équipement': 462, 'equipement': 462,
        'matériel': 462, 'materiel': 462,

        # Services (463)
        'étude': 463, 'etude': 463, 'conseil': 463, 'assistance': 463,
        'formation': 463, 'audit': 463, 'expertise': 463,
        'communication': 463, 'publicité': 463, 'publicite': 463,
        'événementiel': 463, 'evenementiel': 463,
        'nettoyage': 463, 'entretien': 463, 'curage': 463,
        'services': 463, 'prestations': 463, 'prestation': 463,
        'dératisation': 463, 'deratisation': 463, 'désinsectisation': 463, 'desinsectisation': 463,
        'assurance': 463, 'gaz': 462, 'électricité': 462, 'electricite': 462,
        'aire': 461, 'accueil': 461,

        # Informatique (464)
        'informatique': 464, 'logiciel': 464, 'numérique': 464, 'numerique': 464,
        'digital': 464, 'données': 464, 'donnees': 464,

        # Santé (465)
        'santé': 465, 'sante': 465, 'médical': 465, 'medical': 465,
        'hopital': 465, 'hôpital': 465, 'sanitaire': 465,

        # Transport (466)
        'transport': 466, 'véhicule': 466, 'vehicule': 466, 'automobile': 466,

        # Restauration/Alimentation (467)
        'restauration': 467, 'repas': 467, 'traiteur': 467, 'alimentation': 467,
        'denrées': 467, 'denrees': 467, 'alimentaire': 467,

        # Juridique (468)
        'juridique': 468, 'avocat': 468, 'legal': 468, 'droit': 468,

        # OPC/Coordination (469)
        'ordonnancement': 469, 'pilotage': 469, 'coordination': 469, 'opc': 469,

        # Sécurité (470)
        'sécurité': 470, 'securite': 470, 'surveillance': 470, 'gardiennage': 470,
    }

    # Chercher TOUS les mots-clés pertinents dans le secteur
    for keyword, activity_id in sector_mapping.items():
        if keyword in business_sector_lower:
            matched_ids.add(activity_id)

    result = list(matched_ids) if matched_ids else []

    logger.info(f"🎯 Secteur BOAMP: '{business_sector}' → activitiesIds: {result}")
    return result

def download_boamp_pdf(reference, publication_date=None):
    """Télécharge le PDF depuis BOAMP et retourne le chemin local"""
    try:
        # Format référence: 25-142632 où 25 = année 2025
        # Le PDF est dans: https://www.boamp.fr/telechargements/FILES/PDF/2025/12/25-142632.pdf
        # On doit extraire l'année et le mois de publication

        from datetime import datetime

        # Extraire l'année depuis la référence
        ref_parts = reference.split('-')
        if len(ref_parts) != 2:
            logger.warning(f"⚠️ Format référence invalide: {reference}")
            return None

        year_prefix = ref_parts[0][:2]  # "25"
        year = f"20{year_prefix}"  # "2025"

        # Utiliser la date de publication si fournie, sinon le mois actuel
        if publication_date and isinstance(publication_date, datetime):
            month = publication_date.strftime("%m")
            logger.info(f"📅 Utilisation date publication: {publication_date.strftime('%Y-%m')}")
        else:
            month = datetime.now().strftime("%m")
            logger.info(f"📅 Utilisation date actuelle pour le mois")

        pdf_url = f"{BOAMP_PDF_BASE_URL}/{year}/{month}/{reference}.pdf"
        logger.info(f"📥 Téléchargement PDF: {pdf_url}")

        response = requests.get(pdf_url, timeout=30)
        if response.status_code == 200:
            # Sauvegarder temporairement
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp_pdfs')
            os.makedirs(temp_dir, exist_ok=True)

            pdf_path = os.path.join(temp_dir, f"{reference}.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"✅ PDF téléchargé: {pdf_path} ({len(response.content)} bytes)")
            return pdf_path
        else:
            logger.warning(f"⚠️ PDF non trouvé: {pdf_url} (status: {response.status_code})")
            return None
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement PDF {reference}: {e}")
        return None

def upload_file_to_s3(file_path, reference=""):
    """Upload un fichier vers S3 via l'API appeloffres.net"""
    global api_token

    if not api_token:
        login_to_api()

    if not api_token:
        logger.error("❌ Impossible d'uploader sans token")
        return None

    try:
        headers = {
            'Authorization': f'Bearer {api_token}',
            'User-Agent': USER_AGENT
            # Pas de Content-Type ici, laissé à requests
        }

        # Lire le fichier et l'envoyer
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            data = {'description': f'PDF BOAMP {reference}'}

            logger.info(f"📤 Upload vers S3: {os.path.basename(file_path)}")
            response = requests.post(FILES_ENDPOINT, headers=headers, files=files, data=data, timeout=60)

            if response.status_code in [200, 201]:
                api_data = response.json()
                # L'API retourne {url: ...} ou {s3Url: ...}
                s3_url = api_data.get('url') or api_data.get('s3Url') or api_data.get('data', {}).get('url')

                if s3_url:
                    logger.info(f"✅ Upload S3 réussi: {s3_url}")

                    # Extraire le chemin relatif: 25/12/112728-373768.pdf
                    import re
                    relative_match = re.search(r'/tender-s3-prod/(.+?\.(?:png|pdf))\??', s3_url)
                    if relative_match:
                        relative_path = relative_match.group(1)
                        logger.info(f"📎 Chemin relatif extrait: {relative_path}")
                        return relative_path
                    else:
                        logger.warning(f"⚠️ Impossible d'extraire le chemin relatif de: {s3_url}")
                        return s3_url
                else:
                    logger.error(f"⚠️ URL S3 non trouvée dans la réponse: {api_data}")
                    return None
            else:
                logger.error(f"❌ Erreur upload S3: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Exception upload S3: {e}")
        return None
    finally:
        # Nettoyer le fichier temporaire
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Fichier temporaire supprimé: {file_path}")
        except:
            pass

def find_or_create_promoter(promoter_name):
    """Trouve ou crée un promoteur dans l'API appeloffres.net"""
    global api_token, promoters_cache

    if not api_token:
        if not login_to_api():
            return None

    # Normaliser le nom
    normalized = promoter_name.strip().upper() if promoter_name else "BOAMP"

    # Vérifier le cache
    if normalized in promoters_cache:
        logger.info(f"✅ Promoteur '{promoter_name}' trouvé dans cache avec ID: {promoters_cache[normalized]}")
        return promoters_cache[normalized]

    try:
        # Créer le promoteur - mettre la première lettre en majuscule
        promoter_display_name = promoter_name.strip().title() if promoter_name else "BOAMP"
        logger.info(f"➕ Création du promoteur '{promoter_display_name}' via API...")
        create_data = {
            "name": promoter_display_name,
            "description": f"Promoteur BOAMP: {promoter_display_name}",
            "reference": normalized[:20],
            "isEnabled": True,
            "companyName": promoter_display_name,
            "address": {
                "street": "Direction de l'information légale et administrative",
                "city": "Paris",
                "country": "France",
                "postalCode": "75015"
            }
        }

        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT
        }

        response = requests.post(PROMOTER_ENDPOINT, json=create_data, headers=headers, timeout=10)

        if response.status_code in [200, 201]:
            data = response.json()
            promoter_id = data.get('id')
            if promoter_id:
                promoters_cache[normalized] = int(promoter_id)
                logger.info(f"✅ Promoteur '{promoter_name}' créé avec ID: {promoter_id}")
                return int(promoter_id)

        logger.error(f"❌ Échec création promoteur '{promoter_name}': {response.status_code} - {response.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur find_or_create_promoter '{promoter_name}': {e}")
        return None

def send_tender_to_api(tender_data):
    """Envoie les données de l'offre BOAMP à l'API appeloffres.net"""
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

        # Parse dates from BOAMP format (peuvent être datetime objects ou strings)
        pub_date_raw = tender_data.get('publication_date', datetime.now())

        # Convertir en datetime object si c'est une string
        if isinstance(pub_date_raw, str):
            if 'T' not in pub_date_raw:
                pub_date_raw = f"{pub_date_raw}T00:00:00"
            publication_date_obj = datetime.fromisoformat(pub_date_raw.replace('Z', ''))
            publication_date = pub_date_raw
        else:
            # C'est déjà un datetime object de PostgreSQL
            publication_date_obj = pub_date_raw
            publication_date = publication_date_obj.isoformat()

        # Traiter expiration_date
        exp_date_raw = tender_data.get('expiration_date')
        has_expiration_date = bool(exp_date_raw)  # Pour déterminer le type d'avis

        if exp_date_raw:
            if isinstance(exp_date_raw, str):
                if 'T' not in exp_date_raw:
                    exp_date_raw = f"{exp_date_raw}T23:59:59"
                expiration_date = exp_date_raw
            else:
                # datetime object
                expiration_date = exp_date_raw.isoformat()
        else:
            # Si pas de date d'expiration, ajouter 1 mois (30 jours)
            exp_dt = publication_date_obj + timedelta(days=30)
            expiration_date = exp_dt.isoformat()

        start_bidding_date = publication_date
        opening_bids_date = expiration_date

        # Construire le titre à partir de l'objet (avec gestion UTF-8)
        raw_title = tender_data.get('object', tender_data.get('reference', 'Offre BOAMP'))
        if isinstance(raw_title, bytes):
            # Si c'est des bytes, décoder en forçant UTF-8 avec remplacement des caractères invalides
            title_value = raw_title.decode('utf-8', errors='replace')[:255]
        elif isinstance(raw_title, str):
            # Si c'est une string, nettoyer les caractères non-UTF-8
            title_value = raw_title.encode('utf-8', errors='replace').decode('utf-8')[:255]
        else:
            title_value = str(raw_title)[:255]

        raw_desc = tender_data.get('description')
        if raw_desc:
            if isinstance(raw_desc, bytes):
                description_value = raw_desc.decode('utf-8', errors='replace')
            elif isinstance(raw_desc, str):
                description_value = raw_desc.encode('utf-8', errors='replace').decode('utf-8')
            else:
                description_value = str(raw_desc)
        else:
            description_value = title_value

        # S'assurer que tous les IDs sont des integers
        try:
            source_id = int(tender_data.get('source_id', DEFAULT_SOURCE_ID)) if tender_data.get('source_id') else DEFAULT_SOURCE_ID
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ source_id conversion error: {tender_data.get('source_id')} -> using default {DEFAULT_SOURCE_ID}")
            source_id = DEFAULT_SOURCE_ID

        # Déterminer l'avisId: si pas de date limite → avis d'attribution (ID=8), sinon ID par défaut
        if not has_expiration_date:
            avis_id = 8  # Avis d'attribution (pas de date limite)
            logger.info(f"⚠️ Pas de date limite pour {tender_data.get('reference')} → avisId = 8 (avis d'attribution)")
        else:
            try:
                avis_id = int(tender_data.get('avis_id', DEFAULT_AVIS_ID)) if tender_data.get('avis_id') else DEFAULT_AVIS_ID
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ avis_id conversion error: {tender_data.get('avis_id')} -> using default {DEFAULT_AVIS_ID}")
                avis_id = DEFAULT_AVIS_ID

        # Créer ou trouver le promoteur basé sur le nom de l'acheteur
        promoter_name = tender_data.get('promoter') or "BOAMP - Organisme public français"
        promoter_id = find_or_create_promoter(promoter_name)

        if not promoter_id:
            logger.error(f"❌ Impossible de créer/trouver le promoteur '{promoter_name}'")
            return False

        # Extraire les images depuis BOAMP PDF
        reference = tender_data.get('reference', '')
        images = []

        # Télécharger le PDF BOAMP et l'uploader vers S3
        if reference:
            try:
                logger.info(f"📄 Téléchargement du PDF BOAMP pour {reference}...")
                # Passer la date de publication pour trouver le bon mois
                pdf_path = download_boamp_pdf(reference, publication_date_obj)

                if pdf_path:
                    logger.info(f"📤 Upload du PDF vers S3...")
                    s3_url = upload_file_to_s3(pdf_path, reference)

                    if s3_url:
                        images.append(s3_url)
                        logger.info(f"✅ PDF uploadé sur S3: {s3_url}")
                    else:
                        logger.warning(f"⚠️ Échec upload S3 pour {reference}")
                else:
                    logger.warning(f"⚠️ PDF non trouvé pour {reference}")
            except Exception as e:
                logger.error(f"❌ Erreur traitement PDF {reference}: {e}")

        # Extraire les secteurs d'activité depuis l'API appeloffres.net
        business_sector = tender_data.get('business_sector') or tender_data.get('activity') or ""

        # Utiliser la fonction qui récupère les vraies activités depuis l'API
        activities_ids = find_closest_activity(business_sector)

        logger.info(f"📋 Secteur BOAMP: '{business_sector}' → activitiesIds depuis API: {activities_ids}")

        api_payload = {
            'title': description_value,  # Titre = description
            'reference': tender_data.get('reference', ''),
            'description': description_value,
            'publicationDate': publication_date,
            'startBiddingDate': start_bidding_date,
            'expirationDate': expiration_date,
            'openingBidsDate': opening_bids_date,
            'avisId': avis_id,
            'sourceId': source_id,
            'promoterId': promoter_id,
            'type': 'national',
            'nature': 'public',
            'isEnabled': True,
            'images': images,  # Envoyer les images
            'specificationsReceivingAddress': tender_data.get('external_url', 'Non spécifié'),
            'fundingSourceType': 'national',  # Source de financement = national
            'fundingSource': promoter_name,  # Utiliser le nom du promoteur
            'isMultiCurrency': False,  # Requis par l'API
            # Pas de currencyId
            'batches': [{
                'activitiesIds': activities_ids,  # IDs des secteurs d'activité
                'title': description_value,  # Titre du batch = description
                'deposit': '0'
            }],
            'addresses': [{
                'countryId': DEFAULT_COUNTRY_ID  # France = 70, pas de regionId
            }],
            'specificationsPrice': '0',
            # Pas de offerValidityPeriode
            'costEstimateMin': None,
            'costEstimateMax': None,
        }

        logger.info(f"📤 Tentative {attempt + 1}/{max_retries} - Envoi offre {tender_data.get('reference')}")

        response = requests.post(TENDER_ENDPOINT, json=api_payload, headers=headers)

        if response.status_code in [200, 201]:
            logger.info(f"✅ Envoi API réussi pour {tender_data.get('reference')}")
            return True
        elif response.status_code == 400:
            logger.error(f"❌ Erreur 400 Bad Request: {response.text}")
            logger.error(f"Payload envoyé: {json.dumps(api_payload, indent=2, default=str)}")
            return False
        elif response.status_code == 401:
            logger.warning(f"⚠️ Token expiré, tentative de re-login (attempt {attempt + 1})...")
            if login_to_api():
                time.sleep(1)
                continue
            else:
                logger.error("❌ Re-login échoué")
                return False
        else:
            logger.error(f"❌ Erreur envoi API: {response.status_code} - {response.text}")
            return False

    return False

# ================================================
# FLASK APP
# ================================================

app = Flask(__name__)
CORS(app, origins=["*"])

scraper = BOAMPScraper()

@app.route('/api/pending', methods=['GET'])
def get_pending():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        result = scraper.get_offres_cache(page=page, limit=limit)
        return jsonify({"success": True, "pending": result})
    except Exception as e:
        logger.error(f"Erreur /api/pending: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    try:
        data = request.json or {}
        # Accepter plusieurs formats de paramètres
        start_date = data.get('start_date') or data.get('dateDebut') or data.get('date_debut')
        end_date = data.get('end_date') or data.get('dateFin') or data.get('date_fin')
        limit = data.get('limit')  # Pas de limite par défaut - extraire TOUT

        logger.info(f"📥 Requête scraping reçue: start={start_date}, end={end_date}, limit={limit}")

        result = scraper.scrape(start_date=start_date, end_date=end_date, limit=limit)

        # Recharger le cache après scraping
        scraper.load_pending_offers()

        # Retourner dans le format attendu par le frontend Dashboard
        return jsonify({
            "success": result.get("success", True),
            "message": result.get("message", "Scraping terminé"),
            "offres": {
                "offres": scraper.offres_cache[:10],  # Première page
                "total": len(scraper.offres_cache),
                "page": 1,
                "limit": 10,
                "totalPages": (len(scraper.offres_cache) + 9) // 10
            },
            "stats": {
                "accepted_with_keywords": result.get("count", 0),
                "rejected_no_keywords": 0,
                "total_fetched": result.get("total_fetched", 0)
            }
        })
    except Exception as e:
        logger.error(f"Erreur /api/scrape: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "processing": scraper.is_processing,
        "pending_count": len(scraper.offres_cache)
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "BOAMP Official"})

@app.route('/api/secteurs', methods=['GET'])
def get_secteurs():
    """Retourne les secteurs d'activité disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT business_sector FROM {TABLE_NAME} WHERE business_sector IS NOT NULL AND business_sector != ''")
        secteurs = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({"success": True, "results": secteurs})
    except Exception as e:
        logger.error(f"Erreur /api/secteurs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    """Retourne les mots-clés disponibles"""
    return jsonify({"success": True, "keywords": []})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retourne les statistiques des offres"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Count pending tenders
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = 'pending'")
        total_pending = cursor.fetchone()[0]

        # Count validated tenders
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = 'active'")
        total_validated = cursor.fetchone()[0]

        # Total
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        total = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "stats": {
                "total_pending": total_pending,
                "total_validated": total_validated,
                "total": total
            }
        })
    except Exception as e:
        logger.error(f"Erreur /api/stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_offer(reference):
    """Valide une offre ET l'envoie à l'API appeloffres.net"""
    try:
        # 1. Récupérer les données de l'offre depuis PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        tender = cursor.fetchone()
        cursor.close()
        conn.close()

        if not tender:
            return jsonify({"success": False, "error": "Offre non trouvée"}), 404

        # 2. Envoyer l'offre à l'API appeloffres.net
        logger.info(f"📤 Envoi de l'offre {reference} vers l'API appeloffres.net...")
        logger.debug(f"Tender data keys: {list(dict(tender).keys())}")
        try:
            api_success = send_tender_to_api(dict(tender))
        except Exception as e:
            logger.error(f"❌ Exception dans send_tender_to_api: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        if not api_success:
            logger.error(f"❌ Échec de l'envoi API pour {reference}")
            return jsonify({
                "success": False,
                "error": "Échec de l'envoi vers l'API appeloffres.net"
            }), 500

        # 3. Marquer l'offre comme validée dans PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {TABLE_NAME} SET status = 'validated' WHERE reference = %s", (reference,))
        conn.commit()
        cursor.close()
        conn.close()

        # 4. Recharger le cache
        scraper.load_pending_offers()

        logger.info(f"✅ Offre {reference} validée ET envoyée à l'API avec succès")
        return jsonify({
            "success": True,
            "message": f"Offre {reference} validée et envoyée à l'API avec succès"
        })
    except Exception as e:
        logger.error(f"Erreur validation {reference}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete_offer(reference):
    """Supprime une offre"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        conn.commit()
        cursor.close()
        conn.close()

        # Recharger le cache
        scraper.load_pending_offers()

        logger.info(f"🗑️ Offre supprimée: {reference}")
        return jsonify({"success": True, "message": f"Offre {reference} supprimée"})
    except Exception as e:
        logger.error(f"Erreur suppression {reference}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/delete_all', methods=['DELETE'])
def delete_all_offers():
    """Supprime TOUTES les offres pending"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Compter d'abord combien il y en a
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = 'pending'")
        count = cursor.fetchone()[0]

        # Supprimer toutes les offres pending
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE status = 'pending'")
        conn.commit()
        cursor.close()
        conn.close()

        # Vider le cache
        scraper.offres_cache = []

        logger.info(f"🗑️ TOUTES les offres pending supprimées ({count} offres)")
        return jsonify({"success": True, "message": f"{count} offres supprimées", "count": count})
    except Exception as e:
        logger.error(f"Erreur suppression toutes offres: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("🚀 SCRAPER BOAMP OFFICIEL")
    logger.info(f"📂 Database: PostgreSQL - {DB_NAME} (Table: {TABLE_NAME})")
    logger.info(f"🌐 API: {BOAMP_API_URL}")
    logger.info("=" * 80)

    app.run(host='0.0.0.0', port=5003, debug=False)
