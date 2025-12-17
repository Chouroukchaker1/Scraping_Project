"""
Scraper Banque Mondiale - Version Flask Optimisée
Port: 5010
Optimisations: ThreadPoolExecutor, timeouts réduits, cache des résultats
"""
import sys
import os
import json
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

# Configuration UTF-8 pour Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configuration MongoDB
MONGO_URI = "mongodb://localhost:27017/banque_mondiale"
DB_NAME = "worldbank_db"
COLLECTION_NAME = "tenders_worldbank"
PENDING_COLLECTION_NAME = "pending_tenders_worldbank"

# Configuration API
API_BASE_URL = "https://be.appeloffres.net/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"

EMAIL = "ines.mtiri@tunipages.tn"
PASSWORD = "InesMTIRI567@!"
DEFAULT_SOURCE_ID = 1464
DEFAULT_AVIS_ID = 8

# Mapping des pays africains
COUNTRIES_MAP = {
    "angola": 9, "botswana": 32, "burundi": 38, "kenya": 106, "lesotho": 113,
    "madagascar": 123, "malawi": 125, "mauritius": 133, "mozambique": 142,
    "namibia": 144, "rwanda": 176, "somalia": 195, "south africa": 4,
    "tanzania": 214, "uganda": 156, "zambia": 229, "zimbabwe": 230,
    "benin": 26, "burkina faso": 37, "cameroon": 41, "chad": 45, "congo": 228,
    "gabon": 72, "ghana": 74, "guinea": 82, "liberia": 117, "mali": 127,
    "niger": 148, "nigeria": 149, "senegal": 188, "togo": 215
}

# MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
tenders_collection = db[COLLECTION_NAME]
pending_collection = db[PENDING_COLLECTION_NAME]

# Flask App
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

class WorldBankScraper:
    def __init__(self):
        self.api_url = "https://search.worldbank.org/api/v2/procnotices"
        self.base_project_url = "https://projects.banquemondiale.org/fr/projects-operations/procurement-detail/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        self.session = requests.Session()
        self.seen_ids = set()
        self.all_contracts = []
        self.auth_token = None
        self.load_existing_references()

    def load_existing_references(self):
        """Charge les références existantes pour éviter les doublons"""
        try:
            existing = list(pending_collection.find({}, {"reference": 1}))
            self.seen_ids = {doc.get("reference") for doc in existing if doc.get("reference")}
            print(f"✅ {len(self.seen_ids)} références déjà en base")
        except Exception as e:
            print(f"⚠️ Erreur chargement références: {e}")

    def scrape_contracts(self, start_date_str, end_date_str):
        """Scraping optimisé avec parallélisation"""
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            print(f"📅 Période: {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}")

            year = start_date.year
            results = []

            # Phase 1: Pagination optimisée (moins de pages)
            print("🔄 Phase 1: Extraction pagination...")
            results.extend(self.fetch_paginated(year, start_date, end_date, max_offset=2000))

            # Phase 2: Recherche par pays en parallèle (optimisé)
            print("🔄 Phase 2: Recherche par pays...")
            results.extend(self.search_countries_parallel(year, start_date, end_date))

            # Filtrer les doublons
            unique_contracts = []
            seen = set()
            for contract in results:
                ref = contract.get('reference')
                if ref and ref not in seen and ref not in self.seen_ids:
                    seen.add(ref)
                    unique_contracts.append(contract)

            print(f"✅ {len(unique_contracts)} contrats uniques trouvés")

            # Sauvegarder en pending
            saved_count = 0
            for contract in unique_contracts:
                if self.save_to_pending(contract):
                    saved_count += 1

            return {
                "success": True,
                "total": len(unique_contracts),
                "saved": saved_count,
                "message": f"{saved_count} contrats ajoutés en pending"
            }

        except Exception as e:
            print(f"❌ Erreur scraping: {e}")
            return {"success": False, "message": str(e)}

    def fetch_paginated(self, year, start_date, end_date, max_offset=2000):
        """Pagination optimisée avec moins d'appels"""
        contracts = []
        offset = 0
        rows = 200  # Plus de résultats par page

        while offset < max_offset:
            print(f"  Offset {offset}...")
            data = self.fetch_api({
                'os': offset, 'rows': rows, 'srt': 'publishdate', 'order': 'desc',
                'notice_type_exact': 'Contract Award', 'qterm': str(year),
            })

            if not data:
                break

            records = data.get('procnotices', [])
            if not records:
                break

            for record in records:
                if self.is_valid_contract(record, start_date, end_date):
                    contract = self.extract_contract_data(record)
                    if contract:
                        contracts.append(contract)

            offset += rows

        return contracts

    def search_countries_parallel(self, year, start_date, end_date):
        """Recherche par pays en parallèle (optimisé - moins de pays)"""
        # Top pays africains seulement
        top_countries = [
            'Kenya', 'Nigeria', 'South Africa', 'Ghana', 'Tanzania',
            'Uganda', 'Senegal', 'Ethiopia', 'Rwanda', 'Mozambique'
        ]

        contracts = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.search_country, country, year, start_date, end_date): country
                for country in top_countries
            }
            for future in as_completed(futures):
                try:
                    results = future.result(timeout=30)
                    contracts.extend(results)
                except Exception as e:
                    print(f"⚠️ Erreur pays: {e}")

        return contracts

    def search_country(self, country, year, start_date, end_date):
        """Recherche pour un pays"""
        contracts = []
        data = self.fetch_api({
            'os': 0, 'rows': 100,
            'qterm': f'{year} "{country}"',
            'notice_type_exact': 'Contract Award',
        })

        if data:
            for record in data.get('procnotices', []):
                if self.is_valid_contract(record, start_date, end_date):
                    contract = self.extract_contract_data(record)
                    if contract:
                        contracts.append(contract)

        return contracts

    def fetch_api(self, params, timeout=10):
        """Appel API avec timeout réduit"""
        try:
            full_params = {'format': 'json', 'apilang': 'en', 'srce': 'both', **params}
            response = self.session.get(
                self.api_url,
                params=full_params,
                headers=self.headers,
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def is_valid_contract(self, record, start_date, end_date):
        """Vérifie si le contrat est valide"""
        date_str = record.get('noticedate', '')
        if not self.is_in_period(date_str, start_date, end_date):
            return False

        country = record.get('project_ctry_name', '') or record.get('country', '')
        return self.is_african_country(country)

    def is_in_period(self, date_str, start_date, end_date):
        """Vérifie si la date est dans la période"""
        if not date_str:
            return False
        try:
            for fmt in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return start_date <= dt <= end_date
                except:
                    continue
        except:
            pass
        return False

    def is_african_country(self, country):
        """Vérifie si c'est un pays africain"""
        if not country:
            return False
        text = str(country).lower()
        return any(p in text for p in COUNTRIES_MAP.keys()) or 'africa' in text

    def extract_contract_data(self, record):
        """Extrait les données du contrat"""
        try:
            notice_id = record.get('id', '')
            reference = f"WB-{notice_id}"

            return {
                "reference": reference,
                "description": record.get('project_name', 'N/A'),
                "title": record.get('project_name', 'N/A'),
                "publicationDate": record.get('noticedate', ''),
                "pays": record.get('project_ctry_name', 'N/A'),
                "promoter": "Banque Mondiale",
                "source": "Banque Mondiale",
                "url_source": f"{self.base_project_url}{notice_id}",
                "notice_id": notice_id,
                "status": "pending",
                "createdAt": datetime.now().isoformat(),
                "extractionDate": datetime.now().isoformat(),
                "full_content": record.get('contract_desc', ''),
                "type": "international",
                "nature": "public",
                "avis": "Avis d'attribution",
            }
        except Exception as e:
            print(f"⚠️ Erreur extraction: {e}")
            return None

    def save_to_pending(self, contract):
        """Sauvegarde en collection pending"""
        try:
            reference = contract.get('reference')
            if not reference:
                return False

            # Vérifier si existe déjà
            existing = pending_collection.find_one({"reference": reference})
            if existing:
                return False

            # Insérer
            pending_collection.insert_one(contract)
            self.seen_ids.add(reference)
            return True

        except Exception as e:
            print(f"⚠️ Erreur sauvegarde: {e}")
            return False

    def login_to_api(self):
        """Login à l'API"""
        try:
            response = requests.post(
                LOGIN_ENDPOINT,
                json={"email": EMAIL, "password": PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('accessToken')
                return self.auth_token is not None
        except:
            pass
        return False

    def validate_tender(self, reference):
        """Valide une offre et l'envoie à l'API"""
        try:
            # Récupérer depuis pending
            tender_doc = pending_collection.find_one({"reference": reference})
            if not tender_doc:
                return {"success": False, "message": "Offre non trouvée"}

            # Login API
            if not self.login_to_api():
                return {"success": False, "message": "Échec authentification API"}

            # Créer promoteur
            promoter_id = self.find_or_create_promoter("Banque Mondiale")
            if not promoter_id:
                return {"success": False, "message": "Échec création promoteur"}

            # Préparer payload
            country_name = tender_doc.get('pays', '').lower()
            country_id = COUNTRIES_MAP.get(country_name, 1)

            payload = {
                "title": tender_doc.get('title', 'N/A'),
                "description": tender_doc.get('description', 'N/A'),
                "publicationDate": self.normalize_date(tender_doc.get('publicationDate')),
                "reference": reference,
                "avisId": DEFAULT_AVIS_ID,
                "sourceId": DEFAULT_SOURCE_ID,
                "promoterId": promoter_id,
                "type": "international",
                "nature": "public",
                "isEnabled": True,
                "fundingSourceType": "international",
                "fundingSource": "Banque Mondiale",
                "addresses": [{"countryId": country_id}],
                "batches": [{"activitiesIds": [461], "title": "Lot 1", "deposit": "0"}]
            }

            # Envoyer à l'API
            response = requests.post(
                TENDER_ENDPOINT,
                json=payload,
                headers={'Authorization': f'Bearer {self.auth_token}'},
                timeout=15
            )

            if response.status_code in [200, 201]:
                # Marquer comme validé
                tender_doc['status'] = 'validated'
                tender_doc['validationDate'] = datetime.now().isoformat()
                tenders_collection.insert_one(tender_doc)
                pending_collection.delete_one({"reference": reference})
                return {"success": True, "message": "Offre validée et postée"}
            else:
                return {"success": False, "message": f"Erreur API: {response.status_code}"}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def find_or_create_promoter(self, name):
        """Trouve ou crée un promoteur"""
        if not self.auth_token:
            return None

        try:
            # Chercher
            response = requests.get(
                f"{PROMOTER_ENDPOINT}?page=1&itemsPerPage=50",
                headers={'Authorization': f'Bearer {self.auth_token}'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                promoters = data.get('data', [])
                for p in promoters:
                    if p.get('companyName', '').strip().lower() == name.lower():
                        return p.get('id')

            # Créer si non trouvé
            payload = {
                "companyName": name,
                "address": {"street": "Adresse", "city": "Ville", "postalCode": "0000", "countryId": 219},
                "countryId": 219
            }

            response = requests.post(
                PROMOTER_ENDPOINT,
                json=payload,
                headers={'Authorization': f'Bearer {self.auth_token}'},
                timeout=10
            )

            if response.status_code == 201:
                return response.json().get('id')

        except:
            pass
        return 223472  # ID par défaut

    def normalize_date(self, date_str):
        """Normalise une date au format ISO"""
        if not date_str:
            return datetime.now().isoformat()

        try:
            for fmt in ['%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except:
                    continue
        except:
            pass

        return datetime.now().isoformat()

# Instance globale
scraper = WorldBankScraper()

# ==================== ROUTES API ====================

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Lance le scraping"""
    try:
        data = request.json
        start_date = data.get('startDate', '2025-12-01')
        end_date = data.get('endDate', '2025-12-17')

        result = scraper.scrape_contracts(start_date, end_date)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Récupère les offres en attente"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 100))

        skip = (page - 1) * limit

        pending_docs = list(
            pending_collection.find({"status": "pending"})
            .sort("createdAt", -1)
            .skip(skip)
            .limit(limit)
        )

        total = pending_collection.count_documents({"status": "pending"})

        # Convertir ObjectId en string
        for doc in pending_docs:
            doc['_id'] = str(doc['_id'])

        return jsonify({
            "success": True,
            "pending": pending_docs,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/validated', methods=['GET'])
def get_validated():
    """Récupère les offres validées"""
    try:
        validated_docs = list(
            tenders_collection.find({"status": "validated"})
            .sort("validationDate", -1)
            .limit(100)
        )

        for doc in validated_docs:
            doc['_id'] = str(doc['_id'])

        return jsonify({
            "success": True,
            "validated": validated_docs,
            "total": len(validated_docs)
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/validate/<reference>', methods=['POST'])
def validate(reference):
    """Valide une offre"""
    try:
        result = scraper.validate_tender(reference)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete(reference):
    """Supprime une offre pending"""
    try:
        result = pending_collection.delete_one({"reference": reference})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Offre supprimée"})
        return jsonify({"success": False, "message": "Offre non trouvée"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "Banque Mondiale Scraper",
        "port": 5010,
        "pending_count": pending_collection.count_documents({"status": "pending"}),
        "validated_count": tenders_collection.count_documents({"status": "validated"})
    })

@app.route('/', methods=['GET'])
def home():
    """Documentation"""
    return jsonify({
        "service": "Banque Mondiale Scraper API",
        "version": "1.0 - Optimisé",
        "endpoints": {
            "scrape": "POST /api/scrape - {startDate, endDate}",
            "pending": "GET /api/pending?page=1&limit=100",
            "validated": "GET /api/validated",
            "validate": "POST /api/validate/<reference>",
            "delete": "DELETE /api/delete/<reference>",
            "health": "GET /api/health"
        }
    })

if __name__ == "__main__":
    print("=" * 80)
    print("SCRAPER BANQUE MONDIALE - VERSION FLASK OPTIMISEE")
    print("=" * 80)
    print("Port: 5010")
    print("MongoDB: worldbank_db")
    print("Source: Banque Mondiale (ID: 1464)")
    print("Optimisations: ThreadPoolExecutor, timeouts reduits, cache")
    print("=" * 80)
    print("Serveur demarre sur: http://localhost:5010")
    print("=" * 80)

    app.run(debug=True, port=5010, host='0.0.0.0')
