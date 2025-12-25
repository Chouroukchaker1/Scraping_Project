#!/usr/bin/env python3
"""
ARMP Flask API Scraper - Madagascar
Extraction des appels d'offres depuis http://www.armp.mg/marches_publics/
API Flask + MongoDB + Structure complète
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure
from bson import ObjectId
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import time

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ===== CONFIGURATION =====
# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tunip")
DB_NAME = os.getenv("DB_NAME", "tunip")
COLLECTION_NAME = "tenders_armp"  # Collection validées
PENDING_COLLECTION_NAME = "pending_tenders_armp"  # Collection en attente

# API AppelOffres Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILES_ENDPOINT = f"{API_BASE_URL}/files/tender"

# ARMP utilise le compte de Mariem Bousalem
EMAIL = os.getenv("API_EMAIL", "mariem.bousalem@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "L96BhA6ODugl")

# ARMP source_id = 410
DEFAULT_SOURCE_ID_ARMP = 410
DEFAULT_AVIS_ID = int(os.getenv("DEFAULT_AVIS_ID", "1"))
PAYS_MADAGASCAR = 123  # Madagascar country_id

# Paths
OUTPUT_DIR = "output"
EXCEL_DIR = "excel_armp"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EXCEL_DIR, exist_ok=True)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_armp.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ===== DATACLASS =====
@dataclass
class OffreARMP:
    """Modèle de données pour une offre ARMP"""
    reference: str
    promoteur: str
    localisation: str
    numero: str
    description: str
    date_debut: str
    date_limite: str
    cahier_charge_url: str
    source: str = "ARMP"
    pays: str = "Madagascar"
    status: str = "pending"
    createdAt: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extractionDate: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validationDate: Optional[str] = None

    def to_dict(self):
        return asdict(self)

def serialize_document(doc):
    """Convertit ObjectId en string pour JSON"""
    if not doc:
        return doc
    doc = doc.copy() if isinstance(doc, dict) else dict(doc)
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc

def serialize_tenders(tenders_list):
    """Sérialise une liste de tenders"""
    return [serialize_document(t) for t in tenders_list]

# ===== SCRAPER CLASS =====
class ARMPFlaskScraper:
    def __init__(self):
        self.base_url = "http://www.armp.mg/marches_publics/"
        self.session = requests.Session()
        self.session_appeloffres = requests.Session()  # Session séparée pour API

        # Headers pour simuler un navigateur réel
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'http://www.armp.mg/'
        })

        # MongoDB Connection
        self.mongo_client = None
        self.db = None
        self.tenders_collection = None
        self.pending_tenders_collection = None
        self.mongo_connected = self.connect_to_mongodb()

        # API AppelOffres
        self.access_token = None
        self.promoters_cache = {}  # Cache des promoteurs {nom: id}

        # Cache
        self.existing_offres_set = set()
        self.pending_offres_cache = []

        if self.mongo_connected:
            self._load_existing_offres_set()
            self._load_pending_cache()

        # État du scraping
        self.is_processing = False
        self.processing_start_time = None

    def connect_to_mongodb(self):
        """Connexion à MongoDB"""
        try:
            self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[DB_NAME]
            self.tenders_collection = self.db[COLLECTION_NAME]
            self.pending_tenders_collection = self.db[PENDING_COLLECTION_NAME]
            logger.info("✅ Connexion à MongoDB établie avec succès")
            return True
        except (ConnectionFailure, PyMongoError) as e:
            logger.error(f"❌ Erreur lors de la connexion à MongoDB: {e}")
            return False

    def _load_existing_offres_set(self):
        """Charge les références des offres existantes"""
        if not self.mongo_connected:
            return
        try:
            existing_offres = self.tenders_collection.find({}, {"reference": 1})
            self.existing_offres_set = {offre["reference"] for offre in existing_offres if "reference" in offre}
            logger.info(f"📦 Chargé {len(self.existing_offres_set)} offres validées depuis MongoDB")
        except PyMongoError as e:
            logger.error(f"❌ Erreur lors du chargement des offres existantes: {e}")

    def _load_pending_cache(self):
        """Charge les offres en attente dans le cache"""
        if not self.mongo_connected:
            return
        try:
            pending_docs = list(self.pending_tenders_collection.find({}).sort("createdAt", -1))
            self.pending_offres_cache = []
            for doc in pending_docs:
                doc.pop('_id', None)
                offre = OffreARMP(**doc)
                self.pending_offres_cache.append(offre)
            logger.info(f"📦 Chargé {len(self.pending_offres_cache)} offres pending depuis MongoDB")
        except PyMongoError as e:
            logger.error(f"❌ Erreur lors du chargement du cache pending: {e}")

    def parse_entite_fields(self, entite_text):
        """Divise le champ entite en ref, localisation, N° et PROMOTEUR"""
        fields = {
            'ref': '',
            'localisation': '',
            'numero': '',
            'promoteur': ''
        }

        if not entite_text:
            return fields

        text = entite_text.strip()

        # Nettoyer les tirets multiples
        text = re.sub(r'-{2,}', ' - ', text)
        text = re.sub(r'\s+', ' ', text)

        # Pattern pour N° complet
        num_pattern = r'(N°|No|Numéro)\s*[:\-]?\s*([^\s].*?)(?=\s*(?:$|Objet|Date|Localisation|Mode|ENTITE|REF|À\s+|$))'
        num_match = re.search(num_pattern, text, re.IGNORECASE)
        if num_match:
            numero_raw = num_match.group(2).strip()
            numero_raw = re.sub(r'^(SIGMP|AMI|AO)\s*[:\-]?\s*', '', numero_raw, flags=re.IGNORECASE).strip()
            fields['numero'] = numero_raw

        # Pattern pour REF
        ref_pattern = r'(REF|Réf|Référence)\s*[:\-]?\s*([A-Z0-9/.-]+)'
        ref_match = re.search(ref_pattern, text, re.IGNORECASE)
        if ref_match:
            fields['ref'] = ref_match.group(2).strip()

        # Pattern pour Localisation
        loc_pattern = r'(Localisation|Lieu|Ville|à|de)\s*[:\-]?\s*([A-Za-zÀ-ÿ\s,-]+?)(?=\s*(?:$|Mode|N°|Objet|REF))'
        loc_match = re.search(loc_pattern, text, re.IGNORECASE)
        if loc_match:
            fields['localisation'] = loc_match.group(2).strip()
            fields['localisation'] = re.sub(r'\s+', ' ', fields['localisation']).strip()

        # Pattern pour PROMOTEUR
        promoteur_patterns = [
            r'(?:MINISTERE|MINISTÈRE)\s+(?:DE\s+)?([A-ZÀ-Ÿ\s]+?)(?:\s+DE\s+|$)',
            r'(?:DIRECTION|DIRECTEUR)\s+(?:DE|REGIONALE|REGION)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:TRIBUNAL|COUR|JUGE|JUSTICE)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:HOPITAL|HÔPITAL|CENTRE\s+MÉDICAL)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:ÉCOLE|SCHOOL|UNIVERSITÉ|INSTITUT)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:AGENCE|OFFICE|BUREAU|SERVICE)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'([A-ZÀ-Ÿ]{2,}\s+[A-ZÀ-Ÿ\s]+?)(?:\s+(?:DE|DU|À|EN)\s+|$)',
            r'(?:PAOSTRA|PAOSTR)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)'
        ]

        for pattern in promoteur_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                promoteur_candidate = match.group(1).strip()
                promoteur_candidate = re.sub(r'\s+', ' ', promoteur_candidate)
                if len(promoteur_candidate) > 3 and not re.match(r'^\d+[A-Z\s]*$', promoteur_candidate):
                    fields['promoteur'] = promoteur_candidate
                    break

        # Fallback: extraire depuis le début
        if not fields['promoteur']:
            lines = text.split('\n')
            first_line = lines[0].strip() if lines else text
            inst_pattern = r'^([A-ZÀ-Ÿ\s]+?)(?:\s+REF|\s+N°|\s+Local|\s+Mode|$)'
            inst_match = re.search(inst_pattern, first_line, re.IGNORECASE)
            if inst_match:
                fields['promoteur'] = inst_match.group(1).strip()
            elif len(first_line) > 5:
                words = first_line.split()
                promoteur_words = words[:4]
                fields['promoteur'] = ' '.join(promoteur_words)

        # Fallback split
        if not any([fields['ref'], fields['numero']]):
            parts = re.split(r'[,/-]\s*', text)
            cities = ['antananarivo', 'toamasina', 'fianarantsoa', 'mahajanga', 'toliara', 'antsiranana', 'centrale', 'sava', 'vatomandry', 'atovavy']
            for i, part in enumerate(parts):
                part_lower = part.lower().strip()
                if re.match(r'(n°|no|numéro)', part_lower):
                    fields['numero'] = ' '.join([p.strip() for p in parts[i+1:] if p.strip()]).strip()
                elif re.match(r'[a-z]{2,}/\d{4}', part, re.IGNORECASE):
                    fields['ref'] = part.strip()
                elif any(city in part_lower for city in cities):
                    fields['localisation'] = part.strip()
                num_in_part = re.search(r'(N°|No)\s*([^\s].*)', part)
                if num_in_part:
                    fields['numero'] = num_in_part.group(2).strip()

        # Nettoyer les champs
        for key in fields:
            if fields[key]:
                fields[key] = re.sub(r'\s+', ' ', fields[key]).strip()
                fields[key] = re.sub(r'-\s*$', '', fields[key])
                if key == 'promoteur':
                    fields[key] = fields[key].title()

        return fields

    def extract_dates_from_text(self, text):
        """Extrait toutes les dates importantes du texte"""
        dates = {
            'date_debut': None,
            'date_fin': None,
            'heure_limite': None
        }

        if not text:
            return dates

        # Patterns pour différents formats de dates
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})',
        ]

        all_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            all_dates.extend(matches)

        # Patterns contextuels
        context_patterns = {
            'debut': r'(?:du|début|commence|démarrage).*?(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})',
            'fin': r'(?:au|fin|termine|jusqu).*?(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})',
        }

        for date_type, pattern in context_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if date_type == 'debut':
                    dates['date_debut'] = match.group(1)
                elif date_type == 'fin':
                    dates['date_fin'] = match.group(1)

        # Extraire l'heure
        heure_patterns = [
            r'(\d{1,2}[hH]\d{2}(?:[mM]in)?)',
            r'(\d{1,2}:\d{2})',
            r'(\d{1,2}\s*[hH]\s*\d{2})'
        ]

        for pattern in heure_patterns:
            match = re.search(pattern, text)
            if match:
                dates['heure_limite'] = match.group(1)
                break

        # Si dates trouvées sans contexte
        if all_dates and not any(dates.values()):
            if len(all_dates) >= 2:
                dates['date_debut'] = all_dates[0]
                dates['date_fin'] = all_dates[-1]
            elif len(all_dates) == 1:
                dates['date_fin'] = all_dates[0]

        return dates

    def get_page_content(self, url, timeout=30):
        """Récupère le contenu d'une page"""
        try:
            logger.info(f"📡 Récupération de: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur lors de la récupération de {url}: {e}")
            return None

    def extract_from_table(self, html_content):
        """Extrait les données depuis la structure de tableau HTML"""
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        appels_offres = []

        tables = soup.find_all('table')
        logger.info(f"🔍 Nombre de tables trouvées: {len(tables)}")

        for table_idx, table in enumerate(tables):
            logger.info(f"📊 Analyse de la table {table_idx + 1}")

            # Chercher les en-têtes
            headers = []
            thead = table.find('thead')
            if thead:
                header_cells = thead.find_all(['th', 'td'])
                headers = [cell.get_text().strip().upper() for cell in header_cells]
                logger.info(f"📋 En-têtes trouvés: {headers}")

            # Analyser les lignes de données
            tbody = table.find('tbody')
            if not tbody:
                rows = table.find_all('tr')
            else:
                rows = tbody.find_all('tr')

            logger.info(f"📝 Nombre de lignes de données: {len(rows)}")

            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue

                # Extraire le contenu des cellules
                cell_data = []
                for cell in cells:
                    cell_text = cell.get_text().strip()
                    links = cell.find_all('a', href=True)
                    cell_links = [urljoin(self.base_url, link['href']) for link in links if 'pdf' in link['href'].lower()]
                    cell_data.append({
                        'text': cell_text,
                        'links': cell_links
                    })

                if not cell_data:
                    continue

                # Construire l'objet appel d'offre
                appel = {}

                if len(cell_data) >= 1:
                    entite_raw = cell_data[0]['text']
                    entite_fields = self.parse_entite_fields(entite_raw)
                    appel.update(entite_fields)
                if len(cell_data) >= 2:
                    appel['objet'] = cell_data[1]['text']
                if len(cell_data) >= 3:
                    appel['date_info'] = cell_data[2]['text']
                if len(cell_data) >= 4:
                    appel['asap'] = cell_data[3]['links'][0] if cell_data[3]['links'] else cell_data[3]['text']

                # Chercher des liens PDF
                all_links = []
                for cell_info in cell_data:
                    all_links.extend(cell_info['links'])

                if all_links and not appel.get('asap'):
                    appel['asap'] = all_links[0]
                elif not appel.get('asap'):
                    appel['asap'] = 'Non disponible'

                # Extraire les dates
                dates = self.extract_dates_from_text(appel.get('date_info', ''))
                appel.update(dates)

                # Combiner heure avec date_fin
                if appel.get('heure_limite') and appel.get('date_fin'):
                    appel['date_fin'] = f"{appel['date_fin']} {appel['heure_limite']}"

                # Nettoyer les données
                for key, value in appel.items():
                    if isinstance(value, str):
                        appel[key] = re.sub(r'\s+', ' ', value).strip()

                if appel.get('objet'):
                    appels_offres.append(appel)
                    logger.info(f"✅ Offre extraite: {appel.get('promoteur', 'N/A')[:50]}...")

        return appels_offres

    def scrape_all_pages(self, max_pages=3):
        """Scrape plusieurs pages du site ARMP"""
        all_appels = []

        urls_to_try = [
            self.base_url,
            self.base_url + "index.php",
            self.base_url + "consultation.php",
            "http://www.armp.mg/index.php",
            "http://www.armp.mg/consultation.php"
        ]

        for url in urls_to_try:
            logger.info(f"🔍 Test de l'URL: {url}")
            content = self.get_page_content(url)
            if content:
                appels = self.extract_from_table(content)
                if appels:
                    all_appels.extend(appels)
                    logger.info(f"✅ {len(appels)} offres trouvées sur {url}")
                    break
                else:
                    logger.info(f"❌ Aucune offre sur {url}")

            time.sleep(1)

        # Supprimer les doublons
        seen_ids = set()
        unique_appels = []
        for appel in all_appels:
            appel_id = f"{appel.get('ref', '')}_{appel.get('numero', '')}_{appel.get('promoteur', '')}_{appel.get('objet', '')[:50]}".replace(' ', '_').replace('/', '_')
            if appel_id not in seen_ids:
                unique_appels.append(appel)
                seen_ids.add(appel_id)

        logger.info(f"📦 Total unique: {len(unique_appels)} offres")
        return unique_appels

    def scraper_offres_armp(self):
        """Lance le scraping des offres ARMP"""
        if self.is_processing:
            logger.warning("⚠️ Scraping déjà en cours")
            return []

        self.is_processing = True
        self.processing_start_time = time.time()

        try:
            logger.info("🚀 Début scraping ARMP")
            appels_offres = self.scrape_all_pages()

            if not appels_offres:
                logger.warning("⚠️ Aucune offre trouvée")
                return []

            # Sauvegarder en pending
            saved_count = 0
            for appel in appels_offres:
                # Créer la référence
                reference = appel.get('ref', '') or appel.get('numero', '') or f"ARMP-{int(time.time())}"

                # Vérifier si existe déjà
                if reference in self.existing_offres_set:
                    logger.info(f"⏭️ {reference} déjà validé, skip")
                    continue

                # Vérifier si déjà en pending
                existing_pending = self.pending_tenders_collection.find_one({"reference": reference})
                if existing_pending:
                    logger.info(f"⏭️ {reference} déjà en pending, skip")
                    continue

                # Créer l'offre
                offre = OffreARMP(
                    reference=reference,
                    promoteur=appel.get('promoteur', ''),
                    localisation=appel.get('localisation', ''),
                    numero=appel.get('numero', ''),
                    description=appel.get('objet', ''),
                    date_debut=appel.get('date_debut', '') or 'N/A',
                    date_limite=appel.get('date_fin', '') or 'N/A',
                    cahier_charge_url=appel.get('asap', '') or 'Non disponible'
                )

                # Sauvegarder
                self.save_to_pending(offre)
                saved_count += 1

            logger.info(f"✅ Scraping terminé: {saved_count} nouvelles offres sauvegardées en pending")

            # Recharger le cache
            self._load_pending_cache()

            # Exporter en Excel
            self.export_to_excel()

            return self.pending_offres_cache

        finally:
            self.is_processing = False
            duration = time.time() - self.processing_start_time if self.processing_start_time else 0
            logger.info(f"⏱️ Durée totale: {duration:.2f}s")

    # ========== FONCTIONS API APPELOFFRES ==========

    def normaliser_date_api(self, date_str: str) -> str:
        """Normalise une date pour l'API (format ISO 8601)"""
        if not date_str or date_str == "N/A":
            return datetime.now(timezone.utc).isoformat()

        try:
            date_str = date_str.strip()

            # Si déjà en format ISO, retourner tel quel
            if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', date_str):
                return date_str

            # Format: "2026-05-12 10 H 00" ou "2025-04-28"
            # Extraire juste la partie date YYYY-MM-DD
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_str)
            if date_match:
                date_part = date_match.group(1)
                date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                date_obj = date_obj.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
                iso_date = date_obj.isoformat()
                logger.debug(f"✅ Date normalisée: {date_str} → {iso_date}")
                return iso_date

            # Si aucun format reconnu, retourner date actuelle
            logger.warning(f"⚠️ Format de date non reconnu: '{date_str}', utilisation de la date actuelle")
            return datetime.now(timezone.utc).isoformat()

        except Exception as e:
            logger.error(f"❌ Erreur normalisation date '{date_str}': {e}")
            return datetime.now(timezone.utc).isoformat()

    def get_api_token(self):
        """Obtenir le token d'authentification de l'API AppelOffres"""
        if self.access_token:
            return True

        try:
            login_data = {"email": EMAIL, "password": API_PASSWORD}
            response = self.session_appeloffres.post(
                LOGIN_ENDPOINT,
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                if self.access_token:
                    logger.info(f"✅ Token API obtenu avec succès pour {EMAIL}")
                    return True

            logger.error(f"❌ Échec authentification API: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'authentification API: {e}")
            return False

    def find_or_create_promoter(self, promoter_name: str):
        """Trouve ou crée un promoteur dans l'API"""
        logger.info(f"🔍 find_or_create_promoter appelé pour: '{promoter_name}'")

        if not promoter_name or promoter_name.strip() == "":
            promoter_name = "Non spécifié"

        # Vérifier le cache
        if promoter_name in self.promoters_cache:
            logger.info(f"💾 Promoteur '{promoter_name}' trouvé dans cache")
            return self.promoters_cache[promoter_name]

        try:
            # Rechercher le promoteur
            logger.info(f"🔎 Recherche du promoteur '{promoter_name}' via API...")
            search_headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            search_response = self.session_appeloffres.get(
                f"{PROMOTER_ENDPOINT}?name={promoter_name}",
                headers=search_headers,
                timeout=10
            )

            logger.info(f"📡 Search response status: {search_response.status_code}")

            if search_response.status_code == 200:
                promoters = search_response.json()
                logger.info(f"📋 Found {len(promoters) if promoters else 0} promoters")
                if promoters and len(promoters) > 0:
                    promoter_id = promoters[0].get('id')
                    self.promoters_cache[promoter_name] = promoter_id
                    logger.info(f"✅ Promoteur '{promoter_name}' trouvé: ID {promoter_id}")
                    return promoter_id

            # Créer le promoteur s'il n'existe pas
            logger.info(f"🔨 Création du promoteur '{promoter_name}' via API...")
            create_data = {
                "name": promoter_name,
                "description": f"Promoteur ARMP Madagascar: {promoter_name}",
                "reference": re.sub(r'\W+', '_', promoter_name.upper())[:20],
                "isEnabled": True,
                "companyName": promoter_name,
                "address": {
                    "street": "ARMP Madagascar",
                    "city": "Antananarivo",
                    "country": "Madagascar",
                    "postalCode": "101"
                }
            }
            logger.info(f"📤 Data: {json.dumps(create_data, indent=2)}")
            create_response = self.session_appeloffres.post(
                PROMOTER_ENDPOINT,
                json=create_data,
                headers=search_headers,
                timeout=10
            )
            logger.info(f"📥 Response status: {create_response.status_code}")

            if create_response.status_code in [200, 201]:
                promoter_data = create_response.json()
                promoter_id = promoter_data.get('id')
                self.promoters_cache[promoter_name] = promoter_id
                logger.info(f"✅ Promoteur '{promoter_name}' créé: ID {promoter_id}")
                return promoter_id

            logger.error(f"❌ Impossible de créer le promoteur '{promoter_name}'")
            logger.error(f"Status: {create_response.status_code}, Response: {create_response.text[:500]}")
            return None

        except Exception as e:
            logger.error(f"❌ Erreur find_or_create_promoter: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def send_to_appeloffres(self, offre: OffreARMP):
        """Envoie une offre validée vers l'API AppelOffres"""
        logger.info(f"📨 send_to_appeloffres appelé pour: {offre.reference}")
        logger.info(f"   Promoteur: '{offre.promoteur}'")

        if not self.get_api_token():
            logger.error(f"❌ Impossible d'envoyer {offre.reference}: échec authentification")
            return False

        logger.info(f"🏢 Appel de find_or_create_promoter pour '{offre.promoteur}'...")
        promoter_id = self.find_or_create_promoter(offre.promoteur)
        logger.info(f"🏢 Résultat: promoter_id = {promoter_id}")

        if promoter_id is None:
            logger.error(f"❌ Impossible d'envoyer {offre.reference}: échec promoteur")
            return False

        # Préparer les données pour l'API
        tender_data = {
            "sourceId": DEFAULT_SOURCE_ID_ARMP,
            "avisId": DEFAULT_AVIS_ID,
            "reference": offre.reference,
            "description": offre.description,
            "description_fr": offre.description,  # Description en français
            "publicationDate": self.normaliser_date_api(offre.date_debut),
            "startBiddingDate": self.normaliser_date_api(offre.date_debut),  # Date de début des soumissions
            "expirationDate": self.normaliser_date_api(offre.date_limite),
            "promoterId": promoter_id,
            "type": "national",  # national ou international
            "nature": "public",
            "isMultiCurrency": False,
            "fundingSourceType": "national",  # national, international ou other
            "images": [],  # Images vides
            "country": "Madagascar",  # Nom du pays
            "process": "Appel d'offres",  # Type de procédure
            "addresses": [{"countryId": PAYS_MADAGASCAR}],
            "batches": [{
                "activitiesIds": [],
                "title": offre.description[:100] if offre.description else "Description non disponible",
                "deposit": "0"
            }],
            "specificationsReceivingAddress": offre.cahier_charge_url if offre.cahier_charge_url else "Non disponible"
        }

        # Nettoyer les valeurs None
        tender_data = {k: v for k, v in tender_data.items() if v is not None and v != ""}

        logger.info(f"📦 Tender data à envoyer: {json.dumps(tender_data, indent=2, ensure_ascii=False)[:1000]}")

        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }

            logger.info(f"🚀 Envoi vers {TENDER_ENDPOINT}...")
            response = self.session_appeloffres.post(
                TENDER_ENDPOINT,
                json=tender_data,
                headers=headers,
                timeout=30
            )
            logger.info(f"📥 Réponse reçue: {response.status_code}")

            if response.status_code in [200, 201]:
                logger.info(f"✅ Offre {offre.reference} envoyée à AppelOffres avec succès")
                return True
            else:
                logger.error(f"❌ Échec envoi {offre.reference}: {response.status_code}")
                try:
                    error_detail = response.json()
                    logger.error(f"❌ Détails erreur: {error_detail}")
                except:
                    logger.error(f"❌ Réponse: {response.text[:500]}")
                return False
        except Exception as e:
            logger.error(f"❌ Erreur envoi {offre.reference}: {e}")
            return False

    def save_to_pending(self, offre: OffreARMP):
        """Sauvegarde une offre dans la collection pending"""
        if not self.mongo_connected:
            logger.warning(f"⚠️ Offre {offre.reference} non sauvegardée: MongoDB non connecté")
            return

        try:
            doc = offre.to_dict()
            self.pending_tenders_collection.update_one(
                {"reference": offre.reference},
                {"$set": doc},
                upsert=True
            )
            logger.info(f"💾 Offre {offre.reference} sauvegardée dans pending")
        except PyMongoError as e:
            logger.error(f"❌ Erreur sauvegarde {offre.reference}: {e}")

    def validate_offre(self, reference: str):
        """Valide une offre ET l'envoie vers l'API AppelOffres"""
        if not self.mongo_connected:
            return {"success": False, "message": "MongoDB non connecté"}

        try:
            # Récupérer l'offre pending
            pending_doc = self.pending_tenders_collection.find_one({"reference": reference})
            if not pending_doc:
                return {"success": False, "message": "Offre non trouvée en pending"}

            # Mettre à jour le statut
            pending_doc['status'] = 'active'
            pending_doc['validationDate'] = datetime.now(timezone.utc).isoformat()
            pending_doc.pop('_id', None)

            # Créer l'objet OffreARMP
            offre = OffreARMP(**pending_doc)

            # Envoyer vers l'API AppelOffres
            api_success = self.send_to_appeloffres(offre)

            if not api_success:
                logger.warning(f"⚠️ Offre {reference} validée en local mais échec envoi API")
                return {"success": False, "message": "Échec de l'envoi vers l'API AppelOffres"}

            # Si l'envoi API réussit, sauvegarder dans validated
            self.tenders_collection.insert_one(pending_doc)

            # Supprimer de pending
            self.pending_tenders_collection.delete_one({"reference": reference})

            # Mettre à jour les caches
            self.existing_offres_set.add(reference)
            self.pending_offres_cache = [o for o in self.pending_offres_cache if o.reference != reference]

            logger.info(f"✅ Offre {reference} validée et envoyée à AppelOffres avec succès")
            return {"success": True, "message": "Offre validée et envoyée avec succès"}

        except PyMongoError as e:
            logger.error(f"❌ Erreur validation {reference}: {e}")
            return {"success": False, "message": str(e)}
        except Exception as e:
            logger.error(f"❌ Erreur validation {reference}: {e}")
            return {"success": False, "message": str(e)}

    def delete_pending_offre(self, reference: str):
        """Supprime une offre en attente"""
        if not self.mongo_connected:
            return {"success": False, "message": "MongoDB non connecté"}

        try:
            result = self.pending_tenders_collection.delete_one({"reference": reference})
            if result.deleted_count > 0:
                self.pending_offres_cache = [o for o in self.pending_offres_cache if o.reference != reference]
                logger.info(f"🗑️ Offre {reference} supprimée de pending")
                return {"success": True, "message": "Offre supprimée"}
            else:
                return {"success": False, "message": "Offre non trouvée"}
        except PyMongoError as e:
            logger.error(f"❌ Erreur suppression {reference}: {e}")
            return {"success": False, "message": str(e)}

    def delete_validated_offre(self, reference: str):
        """Supprime une offre validée"""
        if not self.mongo_connected:
            return {"success": False, "message": "MongoDB non connecté"}

        try:
            result = self.tenders_collection.delete_one({"reference": reference})
            if result.deleted_count > 0:
                self.existing_offres_set.discard(reference)
                logger.info(f"🗑️ Offre validée {reference} supprimée")
                return {"success": True, "message": "Offre validée supprimée"}
            else:
                return {"success": False, "message": "Offre non trouvée"}
        except PyMongoError as e:
            logger.error(f"❌ Erreur suppression validée {reference}: {e}")
            return {"success": False, "message": str(e)}

    def get_pending_offres(self, page: int = 1, limit: int = 10):
        """Récupère les offres en attente avec pagination"""
        if not self.mongo_connected:
            return {"success": False, "message": "MongoDB non connecté", "offres": [], "total": 0}

        try:
            skip = (page - 1) * limit
            total = self.pending_tenders_collection.count_documents({})
            cursor = self.pending_tenders_collection.find({}).sort("createdAt", -1).skip(skip).limit(limit)
            raw_offres = list(cursor)
            offres = serialize_tenders(raw_offres)

            import math
            total_pages = math.ceil(total / limit) if limit > 0 else 0

            return {
                "success": True,
                "offres": offres,
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": total_pages
            }
        except PyMongoError as e:
            logger.error(f"❌ Erreur récupération pending: {e}")
            return {"success": False, "message": str(e), "offres": [], "total": 0}

    def get_validated_offres(self, limit: int = 100):
        """Récupère les offres validées"""
        if not self.mongo_connected:
            return []

        try:
            cursor = self.tenders_collection.find({}).sort("createdAt", -1).limit(limit)
            raw_offres = list(cursor)
            offres = serialize_tenders(raw_offres)
            return offres
        except PyMongoError as e:
            logger.error(f"❌ Erreur récupération validées: {e}")
            return []

    def export_to_excel(self):
        """Exporte les offres en Excel"""
        try:
            if not self.pending_offres_cache:
                logger.warning("⚠️ Aucune offre à exporter")
                return

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_file = os.path.join(EXCEL_DIR, f"armp_offres_{timestamp}.xlsx")

            data = []
            for offre in self.pending_offres_cache:
                data.append({
                    'PROMOTEUR': offre.promoteur,
                    'REF': offre.reference,
                    'LOCALISATION': offre.localisation,
                    'N°': offre.numero,
                    'DESCRIPTION': offre.description,
                    'DATE_DEBUT': offre.date_debut,
                    'DATE LIMITE': offre.date_limite,
                    'CAHIER DE CHARGE': offre.cahier_charge_url,
                    'SOURCE': offre.source,
                    'PAYS': offre.pays,
                    'STATUS': offre.status
                })

            df = pd.DataFrame(data)
            df.to_excel(excel_file, index=False, engine='openpyxl')
            logger.info(f"📊 Export Excel: {excel_file} ({len(data)} lignes)")

        except Exception as e:
            logger.error(f"❌ Erreur export Excel: {e}")

    def close(self):
        """Ferme les connexions"""
        if self.mongo_connected and self.mongo_client:
            self.mongo_client.close()
            logger.info("🔒 Connexion MongoDB fermée")

# ===== FLASK API =====
app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["*"], supports_credentials=True)

scraper = ARMPFlaskScraper()

@app.route('/api/health', methods=['GET'])
def health():
    """Vérifie l'état du service"""
    try:
        pending_count = scraper.pending_tenders_collection.count_documents({}) if scraper.mongo_connected else 0
        validated_count = scraper.tenders_collection.count_documents({}) if scraper.mongo_connected else 0

        return jsonify({
            "status": "healthy",
            "mongodb_connected": scraper.mongo_connected,
            "pending_count": pending_count,
            "validated_count": validated_count,
            "is_processing": scraper.is_processing,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur health check: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Récupère les offres en attente"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        result = scraper.get_pending_offres(page, limit)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"❌ Erreur /api/pending: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/tenders', methods=['GET'])
def get_tenders():
    """Récupère les offres validées"""
    try:
        offres = scraper.get_validated_offres()
        return jsonify({"success": True, "tenders": offres, "count": len(offres)}), 200
    except Exception as e:
        logger.error(f"❌ Erreur /api/tenders: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Lance le scraping"""
    try:
        logger.info("🚀 /api/scrape appelée")

        # Lancer le scraping en synchrone (simple pour ARMP)
        offres = scraper.scraper_offres_armp()

        return jsonify({
            "success": True,
            "message": f"Scraping terminé: {len(offres)} nouvelles offres",
            "count": len(offres)
        }), 200
    except Exception as e:
        logger.error(f"❌ Erreur /api/scrape: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Statut du scraping"""
    if scraper.is_processing:
        duration = time.time() - scraper.processing_start_time if scraper.processing_start_time else 0
        return jsonify({
            "processing": True,
            "duration_seconds": round(duration, 2),
            "message": "Scraping en cours..."
        }), 200
    else:
        return jsonify({
            "processing": False,
            "pending_count": len(scraper.pending_offres_cache),
            "message": "Aucun scraping en cours"
        }), 200

@app.route('/api/validate/<path:reference>', methods=['POST'])
def validate(reference):
    """Valide une offre"""
    try:
        logger.info(f"✅ Validation de: {reference}")
        result = scraper.validate_offre(reference)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"❌ Erreur validation {reference}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete/<path:reference>', methods=['DELETE'])
def delete_pending(reference):
    """Supprime une offre en attente"""
    try:
        result = scraper.delete_pending_offre(reference)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"❌ Erreur suppression {reference}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/tenders/delete/<path:reference>', methods=['DELETE'])
def delete_validated(reference):
    """Supprime une offre validée"""
    try:
        result = scraper.delete_validated_offre(reference)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"❌ Erreur suppression validée {reference}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "ARMP Scraper API - Madagascar",
        "version": "1.0",
        "description": "API Flask pour scraper les appels d'offres ARMP Madagascar",
        "endpoints": {
            "GET /api/health": "Vérifie l'état du serveur",
            "GET /api/pending?page=1&limit=10": "Liste paginée des offres en attente",
            "GET /api/tenders": "Liste des offres validées",
            "POST /api/scrape": "Lance le scraping",
            "GET /api/status": "Statut du scraping",
            "POST /api/validate/<reference>": "Valide une offre",
            "DELETE /api/delete/<reference>": "Supprime une offre pending",
            "DELETE /api/tenders/delete/<reference>": "Supprime une offre validée"
        },
        "database": {
            "name": DB_NAME,
            "collection_pending": PENDING_COLLECTION_NAME,
            "collection_validated": COLLECTION_NAME
        },
        "fields": [
            "PROMOTEUR (institution/ministère)",
            "REF (référence)",
            "LOCALISATION",
            "N° (numéro)",
            "DESCRIPTION (objet)",
            "DATE_DEBUT",
            "DATE LIMITE",
            "CAHIER DE CHARGE (lien PDF)",
            "SOURCE (ARMP)",
            "PAYS (Madagascar)"
        ]
    })

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 SCRAPER ARMP - MADAGASCAR (Flask API + MongoDB)")
    print("=" * 80)
    print(f"📍 URL cible: {scraper.base_url}")
    print(f"📂 MongoDB: {MONGO_URI}")
    print(f"🔧 Database: {DB_NAME}")
    print(f"📋 Collection pending: {PENDING_COLLECTION_NAME}")
    print(f"📋 Collection validated: {COLLECTION_NAME}")
    print(f"🔌 Port: 5007")
    print("=" * 80)
    print("✅ ENDPOINTS DISPONIBLES:")
    print("   - GET  /api/health          (vérifier serveur)")
    print("   - GET  /api/pending         (offres en attente)")
    print("   - GET  /api/tenders         (offres validées)")
    print("   - POST /api/scrape          (lancer scraping)")
    print("   - POST /api/validate/<ref>  (valider offre)")
    print("   - DELETE /api/delete/<ref>  (supprimer pending)")
    print("   - DELETE /api/tenders/delete/<ref> (supprimer validée)")
    print("   - GET  /api/status          (statut scraping)")
    print("=" * 80)
    print("🔍 CHAMPS EXTRAITS:")
    print("   • PROMOTEUR (institution/ministère)")
    print("   • REF (référence)")
    print("   • LOCALISATION")
    print("   • N° (numéro)")
    print("   • DESCRIPTION (objet)")
    print("   • DATE_DEBUT")
    print("   • DATE LIMITE")
    print("   • CAHIER DE CHARGE (lien PDF)")
    print("=" * 80)

    try:
        app.run(debug=False, port=5007, host='0.0.0.0', threaded=True)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Arrêt du serveur demandé")
    finally:
        scraper.close()
        logger.info("👋 Serveur arrêté proprement")
