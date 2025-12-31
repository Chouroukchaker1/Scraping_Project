# banque_simple.py - Scraper Banque Mondiale avec PostgreSQL
import os

# ✅ CRITICAL: Set encoding BEFORE importing psycopg2 to avoid Windows encoding issues
os.environ['PGCLIENTENCODING'] = 'WIN1252'

import logging
import psycopg2
import requests
import time
from datetime import datetime, timedelta
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
TABLE_NAME = "tenders_banque"

# Configuration API AppelOffres
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.appeloffres-dz.com")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
EMAIL = os.getenv("API_EMAIL", "maryam@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "123456789")

# IDs par défaut pour l'API
DEFAULT_SOURCE_ID = 818  # ID pour Banque Mondiale
DEFAULT_AVIS_ID = 2
DEFAULT_PAYS_ID = 219  # Tunisie par défaut
DEFAULT_CURRENCY_ID = 111  # TND par défaut
DEFAULT_PROMOTER_ID = 180897

# Liste des pays africains (pour filtrage)
AFRICAN_COUNTRIES = {
    'algeria', 'angola', 'benin', 'botswana', 'burkina faso', 'burundi', 'cabo verde', 'cameroon',
    'central african republic', 'chad', 'comoros', 'congo', 'democratic republic of congo',
    'congo, dem. rep.', 'congo, rep.', 'côte d\'ivoire', 'djibouti', 'egypt', 'equatorial guinea',
    'eritrea', 'eswatini', 'ethiopia', 'gabon', 'gambia', 'ghana', 'guinea', 'guinea-bissau',
    'kenya', 'lesotho', 'liberia', 'libya', 'madagascar', 'malawi', 'mali', 'mauritania',
    'mauritius', 'morocco', 'mozambique', 'namibia', 'niger', 'nigeria', 'rwanda',
    'sao tome and principe', 'senegal', 'seychelles', 'sierra leone', 'somalia', 'south africa',
    'south sudan', 'sudan', 'tanzania', 'togo', 'tunisia', 'uganda', 'zambia', 'zimbabwe',
    'gambia, the', 'africa'
}

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def insert_tender(tender_data):
    """Insère une offre dans PostgreSQL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = f"""
            INSERT INTO {TABLE_NAME}
            (reference, description, description_fr, publication_date, expiration_date,
             promoter, external_url, country, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (reference) DO NOTHING
        """

        cursor.execute(query, (
            tender_data.get('reference'),
            tender_data.get('description'),
            tender_data.get('description_fr'),
            tender_data.get('publication_date'),
            tender_data.get('expiration_date'),
            tender_data.get('promoter', 'Banque Mondiale'),
            tender_data.get('external_url'),
            tender_data.get('country'),
            'pending'
        ))

        conn.commit()
        inserted = cursor.rowcount > 0
        cursor.close()
        conn.close()
        return inserted
    except Exception as e:
        logger.error(f"Erreur insertion tender: {e}")
        return False

def scrape_worldbank_api(start_date, end_date):
    """Scrape l'API de la Banque Mondiale pour les marchés publics africains"""
    logger.info(f"🚀 Début scraping Banque Mondiale: {start_date} à {end_date}")

    # ✅ API URL de la Banque Mondiale pour les AVIS DE MARCHÉS (procurement notices)
    # Mise à jour vers v2 (v3 n'existe plus - 404)
    api_url = "https://search.worldbank.org/api/v2/procnotices"

    inserted_count = 0
    total_fetched = 0

    # Convertir les dates pour le filtrage
    try:
        filter_start = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        filter_end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        logger.info(f"📅 Filtrage: {filter_start} à {filter_end}")
    except:
        filter_start = None
        filter_end = None
        logger.warning("⚠️ Dates invalides, pas de filtrage par date")

    try:
        # ✅ Headers pour éviter le blocage Cloudflare
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8'
        }

        # Paramètres de recherche (uniquement ceux acceptés par l'API)
        params = {
            'format': 'json',
            'rows': 100,  # Nombre de résultats par page
            'os': 0  # Offset
        }

        # Boucle de pagination
        for page in range(10):  # Limite à 10 pages (1000 résultats max)
            params['os'] = page * 100

            logger.info(f"📄 Récupération page {page + 1}...")

            try:
                response = requests.get(api_url, params=params, headers=headers, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"⚠️ API returned status {response.status_code}")
                    break

                data = response.json()
                notices = data.get('procnotices', [])

                if not notices:
                    logger.info("✅ Aucun avis de marché supplémentaire trouvé")
                    break

                total_fetched += len(notices)
                logger.info(f"📦 Trouvé {len(notices)} avis de marchés (total: {total_fetched})")

                # Compter les pays africains avant filtrage
                african_count = 0

                # Traiter chaque avis de marché
                for record in notices:
                    try:
                        # Extraire les informations
                        notice_id = record.get('id', 'N/A')
                        project_id = record.get('project_id', '')
                        notice_type = record.get('notice_type', '')
                        procurement_method = record.get('procurement_method', '')
                        description = record.get('description', record.get('procurement_desc', record.get('bid_description', '')))
                        # ✅ Correction: l'API v2 utilise 'project_ctry_name' au lieu de 'country'
                        country = record.get('project_ctry_name', record.get('country', '')).strip()

                        # Filtrer uniquement les pays africains
                        if not country or country.lower() not in AFRICAN_COUNTRIES:
                            continue

                        african_count += 1

                        # Date de publication
                        pub_date_str = record.get('noticedate', record.get('publish_date', ''))
                        pub_date = None
                        pub_date_obj = None

                        if pub_date_str:
                            try:
                                # Essayer différents formats de date
                                for date_format in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%SZ']:
                                    try:
                                        pub_date_obj = datetime.strptime(str(pub_date_str).strip(), date_format)
                                        pub_date = pub_date_obj.strftime('%Y-%m-%d')
                                        break
                                    except:
                                        continue
                            except:
                                pub_date = None

                        # Filtrer par date si les dates sont spécifiées
                        if filter_start and filter_end and pub_date_obj:
                            if not (filter_start <= pub_date_obj <= filter_end):
                                continue

                        # Date limite
                        deadline_str = record.get('deadline', record.get('response_date', ''))
                        deadline = None
                        if deadline_str:
                            try:
                                for date_format in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%SZ']:
                                    try:
                                        deadline_obj = datetime.strptime(str(deadline_str).strip(), date_format)
                                        deadline = deadline_obj.strftime('%Y-%m-%d')
                                        break
                                    except:
                                        continue
                            except:
                                deadline = None

                        # Créer une référence unique
                        reference = f"WB-{project_id}-{notice_id}" if project_id else f"WB-NOTICE-{notice_id}"

                        logger.info(f"🌍 Avis africain trouvé: {country} - {description[:50]} ({pub_date})")

                        # Créer l'offre
                        tender = {
                            'reference': reference,
                            'description': f"{notice_type} - {description}" if notice_type else description,
                            'description_fr': f"{notice_type} - {description}" if notice_type else description,
                            'publication_date': pub_date,
                            'expiration_date': deadline,
                            'promoter': 'Banque Mondiale',
                            'external_url': record.get('url', f"https://projects.worldbank.org/en/projects-operations/procurement/{notice_id}"),
                            'country': country
                        }

                        # Insérer dans la base
                        if insert_tender(tender):
                            inserted_count += 1
                            logger.info(f"✅ Nouvelle offre: {tender['reference']} - {country}")

                    except Exception as e:
                        logger.error(f"❌ Erreur traitement record: {e}")
                        continue

                # Pause entre les pages
                time.sleep(1)

            except Exception as e:
                logger.error(f"❌ Erreur page {page + 1}: {e}")
                break

        logger.info(f"✅ Scraping terminé: {inserted_count} nouvelles offres sur {total_fetched} récupérées")
        return {
            'success': True,
            'inserted': inserted_count,
            'total_fetched': total_fetched
        }

    except Exception as e:
        logger.error(f"❌ Erreur scraping: {e}")
        return {
            'success': False,
            'error': str(e),
            'inserted': inserted_count,
            'total_fetched': total_fetched
        }

# ================================================
# FLASK APP
# ================================================

app = Flask(__name__)
CORS(app, origins=["*"])

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "Banque Mondiale",
        "database": "PostgreSQL",
        "table": TABLE_NAME
    })

@app.route('/api/pending', methods=['GET'])
def get_pending():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        # ✅ Filtrage par date de publication
        date_filter = request.args.get('date')  # Format: YYYY-MM-DD ou DD-MM-YYYY ou DD/MM/YYYY
        start_date = request.args.get('start_date')  # Format: YYYY-MM-DD
        end_date = request.args.get('end_date')  # Format: YYYY-MM-DD

        all_tenders = get_all_tenders(status="pending")

        # ✅ Appliquer le filtrage par date
        if date_filter or start_date or end_date:
            filtered_tenders = []
            for tender in all_tenders:
                pub_date_str = tender.get('publication_date')
                if not pub_date_str:
                    continue

                try:
                    # Convertir la date de publication en objet datetime
                    if isinstance(pub_date_str, str):
                        for date_format in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                            try:
                                pub_date = datetime.strptime(pub_date_str, date_format)
                                break
                            except:
                                continue
                    else:
                        pub_date = pub_date_str

                    # Filtrer par date exacte
                    if date_filter:
                        for date_format in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                            try:
                                filter_date = datetime.strptime(date_filter, date_format)
                                if pub_date.date() == filter_date.date():
                                    filtered_tenders.append(tender)
                                break
                            except:
                                continue

                    # Filtrer par plage de dates
                    elif start_date and end_date:
                        start = datetime.strptime(start_date, '%Y-%m-%d')
                        end = datetime.strptime(end_date, '%Y-%m-%d')
                        if start.date() <= pub_date.date() <= end.date():
                            filtered_tenders.append(tender)

                    # Filtrer par date de début uniquement
                    elif start_date:
                        start = datetime.strptime(start_date, '%Y-%m-%d')
                        if pub_date.date() >= start.date():
                            filtered_tenders.append(tender)

                    # Filtrer par date de fin uniquement
                    elif end_date:
                        end = datetime.strptime(end_date, '%Y-%m-%d')
                        if pub_date.date() <= end.date():
                            filtered_tenders.append(tender)

                except Exception as e:
                    logger.warning(f"⚠️ Erreur parsing date {pub_date_str}: {e}")
                    continue

            all_tenders = filtered_tenders

        start = (page - 1) * limit
        end = start + limit

        tenders_page = all_tenders[start:end]

        # Mapper pour frontend
        mapped_tenders = []
        for tender in tenders_page:
            mapped = {
                'reference': tender.get('reference'),
                'description': tender.get('description'),
                'description_fr': tender.get('description_fr'),
                'publicationDate': tender.get('publication_date'),
                'expirationDate': tender.get('expiration_date'),
                'promoter': tender.get('promoter'),
                'external_url': tender.get('external_url'),
                'montant': tender.get('montant'),
                'country': tender.get('country'),
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        pending = get_all_tenders(status="pending")
        validated = get_all_tenders(status="validated")

        return jsonify({
            "success": True,
            "stats": {
                "pending_count": len(pending),
                "validated_count": len(validated),
                "total_count": len(pending) + len(validated)
            }
        })
    except Exception as e:
        logger.error(f"Erreur /api/stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Endpoint pour lancer le scraping de la Banque Mondiale"""
    try:
        data = request.json or {}
        start_date = data.get('startDate') or data.get('start_date')
        end_date = data.get('endDate') or data.get('end_date')

        logger.info(f"📥 Demande de scraping Banque Mondiale: {start_date} -> {end_date}")

        # Lancer le scraping
        result = scrape_worldbank_api(start_date, end_date)

        if result.get('success'):
            message = f"✅ Scraping terminé: {result['inserted']} nouvelles offres sur {result['total_fetched']} récupérées"
            logger.info(message)
            return jsonify({
                "success": True,
                "message": message,
                "count": result['inserted'],
                "total_fetched": result['total_fetched']
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Erreur scraping: {result.get('error', 'Erreur inconnue')}",
                "count": result.get('inserted', 0),
                "total_fetched": result.get('total_fetched', 0)
            }), 500

    except Exception as e:
        logger.error(f"Erreur /api/scrape: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ================================================
# API APPELOFFRES FUNCTIONS
# ================================================

def login_to_appeloffres():
    """Se connecte à l'API AppelOffres et retourne le token"""
    try:
        response = requests.post(
            LOGIN_ENDPOINT,
            json={"email": EMAIL, "password": API_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token') or data.get('accessToken') or data.get('token')
            logger.info("✅ Connexion API AppelOffres réussie")
            return token
        else:
            logger.error(f"❌ Échec login API: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Erreur login API: {e}")
        return None

def get_or_create_promoter(token, promoter_name):
    """Trouve ou crée un promoteur dans l'API"""
    if not promoter_name or promoter_name.strip() == '':
        promoter_name = 'Banque Mondiale'

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
                    logger.info(f"✅ Promoteur trouvé: {promoter_name} (ID: {promoter['id']})")
                    return promoter['id']

        # Créer le promoteur s'il n'existe pas
        create_response = requests.post(
            PROMOTER_ENDPOINT,
            json={
                "name": promoter_name,
                "companyName": promoter_name,  # Requis par l'API
                "address": "International"  # Requis par l'API
            },
            headers=headers,
            timeout=30
        )

        if create_response.status_code in [200, 201]:
            promoter_id = create_response.json().get('id')
            logger.info(f"✅ Promoteur créé: {promoter_name} (ID: {promoter_id})")
            return promoter_id
        else:
            logger.error(f"❌ Échec création promoteur: {create_response.status_code} - {create_response.text[:500]}")
            # Utiliser l'ID par défaut si création échoue
            logger.info(f"⚠️ Utilisation du promoteur par défaut (ID: {DEFAULT_PROMOTER_ID})")
            return DEFAULT_PROMOTER_ID

    except Exception as e:
        logger.error(f"❌ Erreur get_or_create_promoter: {e}")
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

        expiration_date = tender_data.get('expiration_date') or tender_data.get('closing_date')
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
        title = tender_data.get('title', '')[:500] or f"Banque Mondiale - {tender_data.get('reference', 'N/A')}"
        description = tender_data.get('description', '') or tender_data.get('title', '') or "Appel d'offres Banque Mondiale"

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
        images = [{"url": "https://placeholder.com/banque-mondiale.jpg", "description": "Banque Mondiale"}]

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
            "type": "international",  # Doit être "national" ou "international", pas "AO"
            "nature": "public",  # Valeur correcte pour l'API
            "isEnabled": True,
            "specificationsReceivingAddress": tender_data.get('url', 'https://projects.worldbank.org'),
            "fundingSourceType": "international",
            "fundingSource": "Banque Mondiale",
            "currencyId": int(DEFAULT_CURRENCY_ID),
            "isMultiCurrency": False,
            "batches": batches,
            "addresses": addresses,
            "images": images
        }

        return payload

    except Exception as e:
        logger.error(f"❌ Erreur create_tender_payload: {e}")
        raise

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
            return jsonify({"success": False, "message": "❌ Échec connexion à l'API AppelOffres"}), 500

        # 3. Obtenir ou créer le promoteur
        promoter_name = tender_dict.get('promoter') or 'Banque Mondiale'
        promoter_id = get_or_create_promoter(token, promoter_name)

        # 4. Créer le payload
        payload = create_tender_payload(tender_dict, promoter_id)
        logger.info(f"📤 Envoi de l'offre {reference} vers l'API AppelOffres...")

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

            logger.info(f"✅ Offre {reference} validée et envoyée à l'API (ID: {api_id})")
            return jsonify({
                "success": True,
                "message": f"Offre {reference} validée et postée avec succès !",
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
            logger.error(f"❌ Offre {reference} validée en base mais échec envoi API: {response.status_code}")
            logger.error(f"❌ Détail erreur API: {error_detail}")
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

@app.route('/api/update/<reference>', methods=['POST'])
def update_tender(reference):
    """Met à jour le country_id d'une offre"""
    try:
        data = request.json or {}
        country_id = data.get('country_id')

        if country_id is None:
            return jsonify({"success": False, "error": "country_id requis"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {TABLE_NAME} SET country_id = %s WHERE reference = %s", (country_id, reference))
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"📝 Offre {reference} mise à jour: country_id={country_id}")
        return jsonify({"success": True, "message": "Pays mis à jour avec succès"})
    except Exception as e:
        logger.error(f"Erreur update {reference}: {e}")
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

        logger.info(f"🗑️ Offre {reference} supprimée")
        return jsonify({"success": True, "message": f"Offre {reference} supprimée avec succès"})
    except Exception as e:
        logger.error(f"Erreur suppression {reference}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clear_pending', methods=['DELETE'])
def clear_pending():
    """Supprime toutes les offres pending"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = 'pending'")
        count = cursor.fetchone()[0]
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE status = 'pending'")
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"🗑️ {count} offres pending supprimées")
        return jsonify({"success": True, "message": f"{count} offres supprimées", "deleted_count": count})
    except Exception as e:
        logger.error(f"Erreur clear_pending: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/post_pending', methods=['POST'])
def post_pending():
    """Poste toutes les offres pending vers l'API (TODO: implémenter)"""
    try:
        pending = get_all_tenders(status="pending")

        # TODO: Implémenter l'envoi vers l'API réelle
        logger.info(f"📤 Tentative de post de {len(pending)} offres")

        return jsonify({
            "success": True,
            "posted": 0,
            "failed": 0,
            "remaining": len(pending),
            "message": "Fonctionnalité de post à implémenter"
        })
    except Exception as e:
        logger.error(f"Erreur post_pending: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("🚀 SCRAPER BANQUE MONDIALE")
    logger.info(f"📂 Database: PostgreSQL - {DB_NAME} (Table: {TABLE_NAME})")
    logger.info("=" * 80)

    app.run(host='0.0.0.0', port=5010, debug=False)
