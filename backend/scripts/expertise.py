# expertise.py - Scraper Expertise France avec PostgreSQL
import os

# Set encoding BEFORE importing psycopg2 to avoid Windows encoding issues
os.environ['PGCLIENTENCODING'] = 'WIN1252'

import logging
import psycopg2
import requests
import time
import re
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_expertise"

# Configuration API AppelOffres
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"

EMAIL = os.getenv("API_EMAIL", "maryam@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "123456789")

# IDs par défaut pour l'API
DEFAULT_SOURCE_ID = 1694  # ID pour Expertise France
DEFAULT_AVIS_ID = 2
DEFAULT_PAYS_ID = 219  # Tunisie par défaut
DEFAULT_CURRENCY_ID = 111  # TND par défaut
DEFAULT_PROMOTER_ID = 180897

# Country Mapping
COUNTRY_MAPPING = {
    'France': 'FR',
    'Tunisie': 'TN',
    'Maroc': 'MA',
    'Algérie': 'DZ',
    'Non trouvé': 'XX'
}

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User-Agent commun
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

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
    conn.set_client_encoding('UTF8')
    return conn

def save_to_postgres(offers, status='pending'):
    """Sauvegarde les offres en PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted_count = 0

    try:
        for offer in offers:
            # Parse date publication
            pub_date_str = offer.get('Mis en ligne le', '')
            pub_date = None
            if pub_date_str and pub_date_str != "Non trouvé":
                try:
                    pub_date_obj = datetime.strptime(pub_date_str, "%d/%m/%Y")
                    pub_date = pub_date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pub_date = None

            # Country code
            country_code = COUNTRY_MAPPING.get(offer.get('Localisation', ''), 'XX')

            query = f"""
                INSERT INTO {TABLE_NAME}
                (reference, title, description, promoter, avis, publication_date,
                 duration, localisation, country_code, url, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (reference) DO NOTHING
            """

            cursor.execute(query, (
                offer.get('Référence', 'Non trouvé'),
                offer.get('Titre', '')[:500],  # Limit title length
                offer.get('Description', ''),
                offer.get('Promoteur', 'Expertise France'),
                offer.get('Avis', 'Avis de candidature'),
                pub_date,
                offer.get('Durée', ''),
                offer.get('Localisation', ''),
                country_code,
                offer.get('URL', ''),
                status
            ))

            if cursor.rowcount > 0:
                inserted_count += 1

        conn.commit()
        logger.info(f"✓ {inserted_count}/{len(offers)} nouvelles offres sauvegardées en PostgreSQL (status={status})")
        return inserted_count

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erreur sauvegarde PostgreSQL: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

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

def get_tender_by_reference(reference):
    """Récupère une offre par référence"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        result = cursor.fetchone()
        return dict(result) if result else None
    finally:
        cursor.close()
        conn.close()

def delete_tender_by_reference(reference):
    """Supprime une offre par référence"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        conn.commit()
        deleted = cursor.rowcount > 0
        return deleted
    finally:
        cursor.close()
        conn.close()

def update_tender_status(reference, new_status, api_id=None):
    """Met à jour le status d'une offre"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if api_id:
            cursor.execute(
                f"UPDATE {TABLE_NAME} SET status = %s, api_id = %s, validation_date = NOW() WHERE reference = %s",
                (new_status, api_id, reference)
            )
        else:
            cursor.execute(
                f"UPDATE {TABLE_NAME} SET status = %s, validation_date = NOW() WHERE reference = %s",
                (new_status, reference)
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()

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
        promoter_name = 'Expertise France'

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

def create_tender_payload(tender_dict, promoter_id):
    """Crée le payload pour l'API AppelOffres"""
    try:
        # Dates
        publication_date = tender_dict.get('publication_date')
        if publication_date:
            if isinstance(publication_date, str):
                pub_dt = datetime.fromisoformat(publication_date.replace('Z', '+00:00'))
            else:
                pub_dt = publication_date
            publication_ts = pub_dt.isoformat()
        else:
            publication_ts = datetime.now().isoformat()

        expiration_date = tender_dict.get('expiration_date')
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
        title = tender_dict.get('title', '')[:500] or tender_dict.get('description', '')[:500] or f"Expertise France - {tender_dict.get('reference', 'N/A')}"
        description = tender_dict.get('description', '') or tender_dict.get('title', '') or "Appel d'offres Expertise France"

        # Country ID
        country_id = tender_dict.get('country_id') or DEFAULT_PAYS_ID

        # Batch unique
        batches = [{
            "activitiesIds": [],
            "title": title[:200],
            "deposit": "0"
        }]

        # Addresses
        addresses = [{"countryId": int(country_id)}]

        # Images (placeholder)
        images = [{"url": "https://placeholder.com/expertise-france.jpg", "description": "Expertise France"}]

        payload = {
            "title": title,
            "description": description,
            "publicationDate": publication_ts,
            "startBiddingDate": publication_ts,
            "expirationDate": expiration_ts,
            "openingBidsDate": expiration_ts,
            "reference": tender_dict.get('reference', 'N/A'),
            "specificationsPrice": 0,
            "offerValidityPeriode": None,
            "avisId": int(DEFAULT_AVIS_ID),
            "sourceId": int(DEFAULT_SOURCE_ID),
            "promoterId": int(promoter_id),
            "type": "international",  # Type international pour Expertise France
            "nature": "public",  # Nature publique
            "isEnabled": True,
            "specificationsReceivingAddress": tender_dict.get('url', 'https://expertise-france.gestmax.fr'),
            "fundingSourceType": "international",
            "fundingSource": "Expertise France",
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

# ================================================
# SCRAPING FUNCTIONS
# ================================================

def extract_offer_data(offer_url):
    """Extrait les données détaillées d'une offre d'emploi"""
    try:
        headers = {
            'User-Agent': USER_AGENT
        }
        response = requests.get(offer_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        offer_data = {}

        offer_data['Promoteur'] = "Expertise France"
        offer_data['Avis'] = "Avis de candidature"

        title_tag = soup.find('h1')
        if title_tag:
            offer_data['Titre'] = title_tag.get_text(strip=True)
        else:
            offer_data['Titre'] = "Non trouvé"

        date_publication = "Non trouvé"
        all_text = soup.get_text()

        date_patterns = [
            r'Mis en ligne le\s*:\s*(\d{2}/\d{2}/\d{4})',
            r'Mis en ligne le\s+:\s+(\d{2}/\d{2}/\d{4})',
            r'Mis\s+en\s+ligne\s+le\s*:\s*(\d{2}/\d{2}/\d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                date_publication = match.group(1)
                break

        if date_publication == "Non trouvé":
            all_paragraphs = soup.find_all('p')
            for p in all_paragraphs:
                p_text = p.get_text()
                if 'Mis en ligne' in p_text:
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', p_text)
                    if date_match:
                        date_publication = date_match.group(1)
                        break

        if date_publication == "Non trouvé":
            html_str = str(soup)
            match = re.search(r'Mis en ligne le[:\s]+(\d{2}/\d{2}/\d{4})', html_str, re.IGNORECASE)
            if match:
                date_publication = match.group(1)

        offer_data['Mis en ligne le'] = date_publication

        reference = "Non trouvé"
        ref_patterns = [
            r'RÉF\.\s*([A-Z0-9/]+)',
            r'REF\.\s*([A-Z0-9/]+)',
            r'Réf\.\s*([A-Z0-9/]+)',
            r'RÉF\s*:\s*([A-Z0-9/]+)',
        ]

        for pattern in ref_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                reference = match.group(1)
                break

        offer_data['Référence'] = reference

        # EXTRACTION DE LA DURÉE
        duree = "Non trouvé"

        duree_elem = soup.find('p', class_='field-vac_duree')
        if duree_elem:
            duree_text = duree_elem.get_text(strip=True)
            duree_text = re.sub(r'^Durée\s*:?\s*', '', duree_text, flags=re.IGNORECASE)
            if duree_text and len(duree_text) > 0:
                duree = duree_text

        if duree == "Non trouvé":
            duree_div = soup.find('div', class_=re.compile(r'.*duree.*', re.IGNORECASE))
            if duree_div:
                duree_text = duree_div.get_text(strip=True)
                duree_text = re.sub(r'^Durée\s*:?\s*', '', duree_text, flags=re.IGNORECASE)
                if duree_text and len(duree_text) > 0 and len(duree_text) < 200:
                    duree = duree_text

        if duree == "Non trouvé":
            all_p = soup.find_all('p')
            for i in range(len(all_p)):
                p_text = all_p[i].get_text(strip=True)
                if re.match(r'^Durée\s*:?\s*$', p_text, re.IGNORECASE):
                    if i + 1 < len(all_p):
                        next_p = all_p[i + 1]
                        duree_text = next_p.get_text(strip=True)
                        if duree_text and len(duree_text) < 200:
                            duree = duree_text
                            break
                elif p_text.lower().startswith('durée'):
                    duree_text = re.sub(r'^Durée\s*:?\s*', '', p_text, flags=re.IGNORECASE)
                    if duree_text and len(duree_text) < 200:
                        duree = duree_text
                        break

        offer_data['Durée'] = duree

        description_section = soup.find('div', class_='col-sm-8')
        if description_section:
            for element in description_section.find_all(['a', 'button']):
                element.decompose()

            description_text = description_section.get_text(separator=' ', strip=True)
            description_text = re.sub(r'\s+', ' ', description_text)
            offer_data['Description'] = description_text[:1000] + "..." if len(description_text) > 1000 else description_text
        else:
            offer_data['Description'] = "Non trouvé"

        # Définir le titre comme étant la description
        offer_data['Titre'] = offer_data['Description']

        localisation = "Non trouvé"
        loc_patterns = [
            r'Localisation\s*:\s*([^\n<]+)',
            r'lieu\s*:\s*([^\n<]+)'
        ]
        for pattern in loc_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                localisation = match.group(1).strip()
                break
        offer_data['Localisation'] = localisation

        offer_data['URL'] = offer_url

        return offer_data

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction de {offer_url}: {str(e)}")
        return None

def get_offers_by_date(target_date, max_pages=5):
    """
    Récupère toutes les offres dont la date de mise en ligne correspond à target_date
    Si target_date est vide ou "ALL", récupère toutes les offres sans filtre
    """
    base_url = "https://expertise-france.gestmax.fr/search"

    try:
        headers = {
            'User-Agent': USER_AGENT
        }

        filter_by_date = target_date and target_date.upper() != "ALL"

        if filter_by_date:
            logger.info(f"🎯 Recherche des offres mises en ligne le: {target_date}")
        else:
            logger.info(f"🎯 Recherche de TOUTES les offres disponibles")
        logger.info(f"📄 Parcours de {max_pages} pages maximum...\n")

        all_offer_links = set()

        for page in range(1, max_pages + 1):
            logger.info(f"📄 Parcours de la page {page}...")

            params = {
                'keywords': '',
                'page': page
            }

            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            voir_annonce_buttons = soup.find_all('a', string=re.compile(r'Voir l\'annonce', re.IGNORECASE))

            if not voir_annonce_buttons:
                logger.info(f"  ⚠ Aucune offre trouvée sur la page {page}. Arrêt.")
                break

            page_links = 0
            for button in voir_annonce_buttons:
                href = button.get('href')
                if href:
                    if href.startswith('/'):
                        href = 'https://expertise-france.gestmax.fr' + href
                    if href not in all_offer_links:
                        all_offer_links.add(href)
                        page_links += 1

            logger.info(f"  ✓ {page_links} nouvelles offres trouvées sur cette page")
            time.sleep(1)

        logger.info(f"\n✓ Total d'offres à vérifier: {len(all_offer_links)}")
        if filter_by_date:
            logger.info(f"🔍 Extraction et filtrage par date: {target_date}\n")
        else:
            logger.info(f"🔍 Extraction de toutes les offres\n")

        matching_offers = []

        for i, link in enumerate(all_offer_links, 1):
            logger.info(f"🔍 Extraction {i}/{len(all_offer_links)}: {link}")
            offer_data = extract_offer_data(link)

            if offer_data:
                mise_en_ligne = offer_data.get('Mis en ligne le', 'Non trouvé')

                if filter_by_date:
                    if mise_en_ligne == target_date:
                        matching_offers.append(offer_data)
                        logger.info(f"✅ CORRESPOND - Réf: {offer_data.get('Référence', 'N/A')} - Date: {mise_en_ligne}")
                    else:
                        logger.info(f"⏭️ Date: {mise_en_ligne} (ignoré)")
                else:
                    matching_offers.append(offer_data)
                    logger.info(f"✅ OK - Réf: {offer_data.get('Référence', 'N/A')} - Date: {mise_en_ligne}")
            else:
                logger.info(f"❌ Erreur d'extraction")

            time.sleep(1.5)

        logger.info(f"\n{'='*80}")
        if filter_by_date:
            logger.info(f"✅ RÉSULTAT: {len(matching_offers)} offre(s) trouvée(s) pour le {target_date}")
        else:
            logger.info(f"✅ RÉSULTAT: {len(matching_offers)} offre(s) extraite(s) au total")
        logger.info(f"{'='*80}\n")

        if matching_offers:
            save_to_postgres(matching_offers, status='pending')

        return matching_offers

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des offres: {str(e)}")
        return []

# ================================================
# HTML TEMPLATES
# ================================================

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Validation Avis de Candidature - Expertise France</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background-color: #f2f2f2; }
        .form-container { margin: 20px 0; padding: 20px; border: 1px solid #ddd; background: #f9f9f9; }
        button { background-color: #4CAF50; color: white; padding: 10px; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Offres en Attente de Validation</h1>

    <div class="form-container">
        <h2>Lancer le Scraping Manuel</h2>
        <form method="POST" action="/scrape">
            <label>Date (JJ/MM/AAAA, vide pour aujourd'hui): </label>
            <input type="text" name="target_date" placeholder="{{ current_date }}" value="{{ current_date }}"><br><br>
            <label>Nombre de pages max (défaut: 5): </label>
            <input type="number" name="max_pages" value="5" min="1" max="20"><br><br>
            <button type="submit">Lancer Scraping</button>
        </form>
    </div>

    {% with messages = get_flashed_messages() %}
        {% if messages %}
            <ul>
            {% for message in messages %}
                <li style="color: green;">{{ message }}</li>
            {% endfor %}
            </ul>
        {% endif %}
    {% endwith %}

    {% if offers %}
    <p>Nombre d'offres en attente: {{ offers|length }}</p>
    <table>
        <tr><th>Référence</th><th>Titre</th><th>Date</th><th>Actions</th></tr>
        {% for offer in offers %}
        <tr>
            <td>{{ offer.get('reference', 'N/A') }}</td>
            <td>{{ offer.get('title', 'N/A')[:50] }}...</td>
            <td>{{ offer.get('publication_date', 'N/A') }}</td>
            <td><a href="/validate/{{ offer['reference'] }}">Valider</a></td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p>Aucune offre en attente.</p>
    <p><em>Utilisez le formulaire ci-dessus pour lancer le scraping et charger des données.</em></p>
    {% endif %}
</body>
</html>
"""

VALIDATE_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Validation - {{ offer.get('title', '') }}</title>
</head>
<body>
    <h1>Valider: {{ offer.get('title', '') }}</h1>
    <p><strong>Promoteur:</strong> {{ offer.get('promoter', '') }}</p>
    <p><strong>Avis:</strong> {{ offer.get('avis', '') }}</p>
    <p><strong>Référence:</strong> {{ offer.get('reference', '') }}</p>
    <p><strong>Date:</strong> {{ offer.get('publication_date', '') }}</p>
    <p><strong>Durée:</strong> {{ offer.get('duration', '') }}</p>
    <p><strong>Description:</strong><br>{{ offer.get('description', '')[:500] }}...</p>
    <p><strong>Localisation:</strong> {{ offer.get('localisation', '') }} (Code: {{ offer.get('country_code', '') }})</p>
    <p><strong>URL:</strong> <a href="{{ offer.get('url', '') }}" target="_blank">Lien</a></p>

    <form method="POST">
        <button type="submit" style="background-color: #4CAF50; color: white; padding: 10px; border: none; cursor: pointer;">Valider et Envoyer à l'API</button>
    </form>

    <br><a href="/">Retour à la liste</a>
</body>
</html>
"""

# ================================================
# FLASK APP
# ================================================

app = Flask(__name__)
CORS(app)
app.secret_key = 'super_secret_key'
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

@app.route('/', methods=['GET'])
def index():
    current_date = datetime.now().strftime("%d/%m/%Y")
    pending_offers = get_all_tenders(status='pending')[:50]
    return render_template_string(INDEX_TEMPLATE, offers=pending_offers, current_date=current_date)

@app.route('/scrape', methods=['POST'])
def scrape():
    target_date_input = request.form.get('target_date', '').strip()
    max_pages_input = request.form.get('max_pages', '5').strip()

    if not target_date_input:
        target_date = datetime.now().strftime("%d/%m/%Y")
    else:
        try:
            datetime.strptime(target_date_input, "%d/%m/%Y")
            target_date = target_date_input
        except ValueError:
            flash("❌ Format de date invalide. Utilisation de la date d'aujourd'hui.")
            target_date = datetime.now().strftime("%d/%m/%Y")

    try:
        max_pages = int(max_pages_input)
    except ValueError:
        max_pages = 5

    offers = get_offers_by_date(target_date, max_pages)
    num_offers = len(offers)
    if num_offers > 0:
        flash(f"✅ Scraping terminé: {num_offers} offre(s) ajoutée(s) en attente.")
    else:
        flash(f"ℹ️ Scraping terminé: Aucune offre trouvée pour {target_date}.")

    return redirect(url_for('index'))

@app.route('/validate/<path:reference>', methods=['GET', 'POST'])
def validate_offer(reference):
    offer = get_tender_by_reference(reference)
    if not offer:
        flash("❌ Offre non trouvée.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Use the new API validation approach
        try:
            token = login_to_appeloffres()
            if not token:
                flash("❌ Erreur lors de la connexion à l'API AppelOffres.")
                return render_template_string(VALIDATE_TEMPLATE, offer=offer)

            promoter_name = offer.get('promoter') or 'Expertise France'
            promoter_id = get_or_create_promoter(token, promoter_name)

            payload = create_tender_payload(offer, promoter_id)
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            response = requests.post(TENDER_ENDPOINT, json=payload, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                api_data = response.json()
                api_id = api_data.get('id')
                update_tender_status(reference, 'validated', api_id)
                flash("✅ Offre validée et envoyée à l'API avec succès!")
                return redirect(url_for('index'))
            else:
                flash(f"❌ Erreur API: {response.status_code}")
                return render_template_string(VALIDATE_TEMPLATE, offer=offer)
        except Exception as e:
            logger.error(f"Erreur validation: {e}")
            flash("❌ Erreur lors de l'envoi à l'API. Vérifiez les logs du serveur.")
            return render_template_string(VALIDATE_TEMPLATE, offer=offer)

    return render_template_string(VALIDATE_TEMPLATE, offer=offer)

# ================================================
# API ENDPOINTS
# ================================================

@app.route('/pending-all', methods=['GET'])
@app.route('/api/pending-all', methods=['GET'])
def api_pending_all():
    """Retourne toutes les offres pending pour le frontend React"""
    try:
        pending_offers = get_all_tenders(status='pending')

        transformed_offers = []
        for offer in pending_offers:
            transformed_offer = {
                'reference': offer.get('reference'),
                'description': offer.get('description', offer.get('title', '')),
                'promoter': offer.get('promoter', 'Expertise France'),
                'date_publication': offer.get('publication_date'),
                'duree': offer.get('duration', ''),
                'localisation': offer.get('localisation', ''),
                'url': offer.get('url', ''),
                # Garder aussi les champs pour compatibilité
                'Référence': offer.get('reference', ''),
                'Titre': offer.get('title', ''),
                'Description': offer.get('description', ''),
                'Promoteur': offer.get('promoter', ''),
                'Avis': offer.get('avis', ''),
                'Mis en ligne le': offer.get('publication_date'),
                'Durée': offer.get('duration', ''),
                'Localisation': offer.get('localisation', ''),
                'URL': offer.get('url', ''),
                'country_code': offer.get('country_code', ''),
            }
            transformed_offers.append(transformed_offer)

        return jsonify({
            "success": True,
            "offres": transformed_offers,
            "count": len(transformed_offers)
        })
    except Exception as e:
        logger.error(f"Erreur /api/pending-all: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/validated-all', methods=['GET'])
@app.route('/api/validated-all', methods=['GET'])
def api_validated_all():
    """Retourne toutes les offres validées"""
    try:
        validated_offers = get_all_tenders(status='validated')
        return jsonify({
            "success": True,
            "offres": validated_offers,
            "count": len(validated_offers)
        })
    except Exception as e:
        logger.error(f"Erreur /api/validated-all: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        pending_offers = get_all_tenders(status='pending')
        validated_offers = get_all_tenders(status='validated')
        return jsonify({
            "status": "ok",
            "pending": len(pending_offers),
            "validated": len(validated_offers)
        })
    except Exception as e:
        logger.error(f"Erreur /health: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Lance le scraping via API"""
    try:
        data = request.get_json() or {}
        target_date = data.get('target_date', datetime.now().strftime("%d/%m/%Y"))
        max_pages = int(data.get('max_pages', 5))

        offers = get_offers_by_date(target_date, max_pages)
        return jsonify({
            "success": True,
            "message": f"{len(offers)} offres extraites",
            "count": len(offers)
        })
    except Exception as e:
        logger.error(f"Erreur /api/scrape: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/validate/<path:reference>', methods=['POST'])
def api_validate(reference):
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
        promoter_name = tender_dict.get('promoter') or 'Expertise France'
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

@app.route('/api/delete/<path:reference>', methods=['DELETE'])
def api_delete(reference):
    """Supprime une offre pending"""
    try:
        deleted = delete_tender_by_reference(reference)
        if deleted:
            return jsonify({"success": True, "message": "Offre supprimée"})
        else:
            return jsonify({"success": False, "message": "Offre non trouvée"}), 404
    except Exception as e:
        logger.error(f"Erreur /api/delete: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🚀 SCRAPER EXPERTISE FRANCE - PostgreSQL")
    logger.info(f"📂 Database: PostgreSQL - {DB_NAME} (Table: {TABLE_NAME})")
    logger.info(f"🌐 Port: 5013")
    logger.info("=" * 80)

    app.run(host='0.0.0.0', port=5013, debug=True, use_reloader=False)
