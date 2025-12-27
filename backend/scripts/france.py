# france.py - Scraper France Marchés Complet (Sans Mots-Clés, Skip BOAMP, Extraction Détails + Images)
import os
import json
import logging
import threading
import http.server
import socketserver
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import requests
import pandas as pd
from dateutil.parser import parse
from dateutil import tz
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import tenacity
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import unicodedata
import warnings
import traceback
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple, Set
import base64
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from difflib import SequenceMatcher
from collections import defaultdict
warnings.filterwarnings('ignore')

# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")
TABLE_NAME = "tenders_boamp"

# Configuration API
API_BASE_URL = "https://be.appeloffres.net/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILE_ENDPOINT = f"{API_BASE_URL}/files/tender"
BUSINESS_SECTOR_ENDPOINT = f"{API_BASE_URL}/business-sector"

EMAIL = "oumayma.dahmani@tunipages.tn"
PASSWORD = "Ah0F553KKu0A"
DEFAULT_SOURCE_ID = "1839"  # Source ID pour France Marchés
DEFAULT_PROMOTER_ID = "223472"
DEFAULT_AVIS_ID = "1"
DEFAULT_PAYS_ID = "70"

# Dossiers
PDF_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\pdf_boamp_extraction"
IMAGES_DIR = "images"
OUTPUT_DIR = "output"
TEMPLATES_DIR = "templates"
REACT_BUILD_DIR = "react-frontend/build"

for directory in [PDF_DIR, IMAGES_DIR, OUTPUT_DIR, TEMPLATES_DIR, REACT_BUILD_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# ================================================
# POSTGRESQL HELPER FUNCTIONS
# ================================================

def get_db_connection():
    """Créer une connexion PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def get_all_tenders(status=None):
    """Récupère toutes les offres depuis PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if status:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY created_at DESC")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_existing_references():
    """Récupère l'ensemble des références existantes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT reference FROM {TABLE_NAME}")
        return {row[0] for row in cursor.fetchall() if row[0]}
    finally:
        cursor.close()
        conn.close()

def insert_tender(tender_dict):
    """Insère une offre en PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = f"""
            INSERT INTO {TABLE_NAME} (reference, description, description_fr, publication_date,
                                      expiration_date, promoter, source_id, avis_id, external_url,
                                      montant, nature, country, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reference) DO NOTHING
            RETURNING id
        """
        values = (
            tender_dict.get('reference'),
            tender_dict.get('description'),
            tender_dict.get('description_fr'),
            tender_dict.get('publicationDate') or tender_dict.get('publication_date'),
            tender_dict.get('expirationDate') or tender_dict.get('expiration_date'),
            tender_dict.get('promoter'),
            tender_dict.get('sourceId') or tender_dict.get('source_id'),
            tender_dict.get('avisId') or tender_dict.get('avis_id'),
            tender_dict.get('externalUrl') or tender_dict.get('external_url'),
            tender_dict.get('montant'),
            tender_dict.get('nature', 'public'),
            tender_dict.get('country', 'France'),
            tender_dict.get('status', 'pending')
        )
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()

def delete_tender(reference):
    """Supprime une offre"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    finally:
        cursor.close()
        conn.close()

def update_tender(reference, update_dict):
    """Met à jour une offre"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in update_dict.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)
        values.append(reference)
        query = f"UPDATE {TABLE_NAME} SET {', '.join(set_clauses)} WHERE reference = %s"
        cursor.execute(query, values)
        updated_count = cursor.rowcount
        conn.commit()
        return updated_count
    finally:
        cursor.close()
        conn.close()

def count_tenders(status=None):
    """Compte les offres"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if status:
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE status = %s", (status,))
        else:
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()

def get_tender_by_reference(reference):
    """Récupère une offre par référence"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE reference = %s", (reference,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def delete_all_pending():
    """Supprime toutes les offres pending"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE status = 'pending'")
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    finally:
        cursor.close()
        conn.close()

# Test connexion PostgreSQL
try:
    conn = get_db_connection()
    conn.close()
    print(f"✅ PostgreSQL connecté: {DB_NAME} (Table: {TABLE_NAME})")
except Exception as e:
    print(f"❌ Erreur connexion PostgreSQL: {e}")
    raise

INDEX_HTML_PATH = os.path.join(REACT_BUILD_DIR, 'index.html')
if not os.path.exists(INDEX_HTML_PATH):
    # Frontend HTML complet intégré ici pour éviter erreurs
    fallback_html = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Scraper France Marchés - Tous AO (Sans Mots-Clés)</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f4; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        input, button { padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; cursor: pointer; }
        button:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-success { background: #28a745; }
        .btn-clean { background: #6c757d; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f8f9fa; }
        .loading { text-align: center; color: #007bff; }
        .error { color: #dc3545; }
        .success { color: #28a745; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }
        .stat-card { background: #e9ecef; padding: 15px; border-radius: 4px; text-align: center; }
        .hidden { display: none; }
        .image-link { color: #007bff; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Scraper France Marchés - TOUS les AO (Sans Mots-Clés)</h1>
        <p>Extraction complète: descriptions, dates, images URI (skip BOAMP auto).</p>
        
        <!-- Contrôles -->
        <div class="controls">
            <input type="date" id="date_debut" value="" placeholder="Date début (YYYY-MM-DD)">
            <input type="date" id="date_fin" value="" placeholder="Date fin (YYYY-MM-DD)">
            <button onclick="scrapeData()">🔍 Extraire AO Complet</button>
            <button onclick="getPending()">📋 Voir Pending</button>
            <button onclick="getStats()">📈 Stats</button>
            <button onclick="cleanPending()" class="btn-clean">🗑️ Nettoyer Pending</button>
        </div>
        
        <!-- Stats -->
        <div id="stats-section" class="stats hidden"></div>
        
        <!-- Résultats Scraping -->
        <div id="scrape-results" class="hidden">
            <h2>✅ Résultats Extraction</h2>
            <div id="scrape-stats"></div>
            <table id="offres-table">
                <thead>
                    <tr>
                        <th>Référence</th>
                        <th>Description</th>
                        <th>Promoteur</th>
                        <th>Date Pub.</th>
                        <th>Date Exp.</th>
                        <th>Image URI</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- Pending -->
        <div id="pending-section" class="hidden">
            <h2>📋 Offres Pending</h2>
            <table id="pending-table">
                <thead>
                    <tr>
                        <th>Référence</th>
                        <th>Description</th>
                        <th>Promoteur</th>
                        <th>Date Pub.</th>
                        <th>Date Exp.</th>
                        <th>Image URI</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- Messages -->
        <div id="messages"></div>
    </div>

    <script>
        const API_BASE = 'http://localhost:5003/api';
        const MESSAGES_DIV = document.getElementById('messages');

        function showMessage(msg, type = 'info') {
            MESSAGES_DIV.innerHTML = `<div class="${type}">${new Date().toLocaleTimeString()}: ${msg}</div>`;
            setTimeout(() => MESSAGES_DIV.innerHTML = '', 5000);
        }

        function showLoading(show = true) {
            document.body.style.cursor = show ? 'wait' : 'default';
        }

        async function apiCall(endpoint, method = 'GET', body = null) {
            showLoading(true);
            try {
                const options = { method, headers: { 'Content-Type': 'application/json' } };
                if (body) options.body = JSON.stringify(body);
                const res = await fetch(`${API_BASE}${endpoint}`, options);
                const data = await res.json();
                if (!data.success) throw new Error(data.message || 'Erreur API');
                return data;
            } catch (err) {
                showMessage(`❌ ${err.message}`, 'error');
                throw err;
            } finally {
                showLoading(false);
            }
        }

        async function scrapeData() {
            const date_debut = document.getElementById('date_debut').value || '';
            const date_fin = document.getElementById('date_fin').value || '';
            if (!date_debut || !date_fin) {
                showMessage('⚠️ Veuillez sélectionner les dates', 'error');
                return;
            }
            try {
                showMessage('🔄 Extraction complète en cours... (détails + images)');
                const data = await apiCall('/scrape', 'POST', { date_debut, date_fin });
                showMessage(`✅ Extraction terminée: ${data.stats.new} nouvelles AO (skip ${data.stats.boamp_skipped} BOAMP)`, 'success');
                displayOffres(data.offres.offres, 'scrape-results');
                displayStats(data.stats, 'scrape-stats');
            } catch (err) {
                showMessage('❌ Erreur extraction', 'error');
            }
        }

        function displayOffres(offres, sectionId) {
            const section = document.getElementById(sectionId);
            const tbody = section.querySelector('tbody');
            tbody.innerHTML = '';
            offres.forEach(offre => {
                const tr = document.createElement('tr');
                const imgLink = offre.image_filename ? `<a href="${offre.image_filename}" target="_blank" class="image-link">Voir Image</a>` : 'N/A';
                tr.innerHTML = `
                    <td>${offre.reference}</td>
                    <td>${offre.description}</td>
                    <td>${offre.promoter}</td>
                    <td>${offre.publicationDate}</td>
                    <td>${offre.expirationDate}</td>
                    <td>${imgLink}</td>
                    <td>
                        <button onclick="validateOffre('${offre.reference}')" class="btn-success">✅ Valider & Envoyer</button>
                        <button onclick="deleteOffre('${offre.reference}')" class="btn-danger">🗑️ Supprimer</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            section.classList.remove('hidden');
        }

        async function getPending() {
            try {
                const page = 1;
                const limit = 20;
                const data = await apiCall(`/pending?page=${page}&limit=${limit}`);
                displayOffres(data.pending.offres, 'pending-section');
                showMessage(`📋 ${data.pending.total} offres pending`, 'success');
            } catch (err) {
                showMessage('❌ Erreur pending', 'error');
            }
        }

        async function validateOffre(reference) {
            try {
                const data = await apiCall(`/validate/${reference}`, 'POST');
                showMessage(data.message, data.api_success ? 'success' : 'error');
                if (data.success) getPending(); // Refresh
            } catch (err) {
                showMessage('❌ Erreur validation', 'error');
            }
        }

        async function deleteOffre(reference) {
            if (!confirm(`Supprimer ${reference} ?`)) return;
            try {
                const data = await apiCall(`/delete/${reference}`, 'DELETE');
                showMessage(data.message, 'success');
                getPending(); // Refresh
            } catch (err) {
                showMessage('❌ Erreur suppression', 'error');
            }
        }

        async function cleanPending() {
            if (!confirm('Nettoyer TOUS les pending ?')) return;
            try {
                const data = await apiCall('/clean_pending', 'POST');
                showMessage(data.message, 'success');
                getPending();
            } catch (err) {
                showMessage('❌ Erreur nettoyage', 'error');
            }
        }

        async function getStats() {
            try {
                const data = await apiCall('/stats');
                displayStats(data.stats, 'stats-section');
                document.getElementById('stats-section').classList.remove('hidden');
                showMessage('📈 Stats mises à jour', 'success');
            } catch (err) {
                showMessage('❌ Erreur stats', 'error');
            }
        }

        function displayStats(stats, containerId) {
            const container = document.getElementById(containerId);
            if (containerId === 'stats-section') {
                container.innerHTML = `
                    <div class="stat-card"><strong>Total Pending:</strong> ${stats.total_pending}</div>
                    <div class="stat-card"><strong>Total Validées:</strong> ${stats.total_validated}</div>
                    <div class="stat-card"><strong>BOAMP Skippés:</strong> ${stats.boamp_skipped}</div>
                    <div class="stat-card"><strong>Acceptés:</strong> ${stats.accepted}</div>
                `;
            } else {
                container.innerHTML = `<p><strong>Stats:</strong> URLs: ${stats.total_urls}, Nouvelles: ${stats.new}, BOAMP: ${stats.boamp_skipped}</p>`;
            }
        }

        // Auto-load dates (yesterday to today)
        window.onload = () => {
            const today = new Date().toISOString().split('T')[0];
            const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
            document.getElementById('date_debut').value = yesterday;
            document.getElementById('date_fin').value = today;
            getStats(); // Load initial stats
        };
    </script>
</body>
</html>'''
    with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(fallback_html)
    print(f"✅ Frontend HTML complet créé (intégrant extraction détails + images)")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_francemarches.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# PostgreSQL used instead of MongoDB

def capitalize_first_word(text: str) -> str:
    """Capitalise le premier mot d'une chaîne"""
    if not text:
        return text
    words = text.split()
    if words:
        words[0] = words[0].capitalize()
    return ' '.join(words)

@dataclass
class OffreBase:
    createdAt: str = ""
    updatedAt: str = ""
    extractionDate: str = ""
    deletedAt: Optional[str] = None
    status: str = "pending"
    description: str = ""
    full_content: str = ""
    expirationDate: str = ""
    publicationDate: str = ""
    startBiddingDate: Optional[str] = None
    type: str = "international"
    reference: str = ""
    specificationsReceivingAddress: str = ""
    offerValidityPeriod: str = ""
    nature: str = "public"
    fundingSource: Optional[str] = None
    fundingSourceType: str = "national"
    isMultiCurrency: bool = False
    sourceId: Optional[str] = None
    promoterId: Optional[str] = None
    currencyId: str = "4"
    createdById: Optional[str] = None
    updatedById: Optional[str] = None
    pays: str = "France"
    source: str = "FranceMarches"
    promoter: str = ""
    pieces_jointes: List[str] = field(default_factory=list)
    cahier_charge: str = ""
    cahier_charge_pdf: str = ""
    cahier_charge_pdf_filename: str = ""
    cahier_charge_pdf_base64: str = ""
    image_filename: str = ""  # URI de l'image extraite
    image_base64: str = ""   # Base64 si téléchargée
    lots: List[Dict] = field(default_factory=list)
    mots_cles_detectes: List[str] = field(default_factory=list)  # Vide
    avis: str = "appel d'offre"
    secteur_activite: str = ""  # Vide, sans secteur
    secteur_activite_id: Optional[int] = None
    activities_ids: List[int] = field(default_factory=list)  # Vide
    procedure: str = "N/A"
    type_marche: str = "Public"
    url_source: str = ""
    validationDate: Optional[str] = None

    def __post_init__(self):
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()
        if not self.updatedAt:
            self.updatedAt = datetime.now().isoformat()
        if not self.extractionDate:
            self.extractionDate = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)

class FranceMarchesScraperAll:
    def __init__(self, use_selenium=True, skip_s3=False):
        self.base_search_url = "https://www.francemarches.com/recherche"
        self.session = requests.Session()
        self.use_selenium = use_selenium
        self.driver = None
        self.access_token = None
        self.session_appeloffres = requests.Session()
        self.promoter_cache = {}
        self.offres_cache = []
        self.existing_offres_set = set()
        self.validated_references_set = set()
        self.logger = logging.getLogger(__name__)
        self.pdf_dir = PDF_DIR
        self.images_dir = IMAGES_DIR
        self.output_dir = OUTPUT_DIR
        self.skip_s3 = skip_s3
        self.stats_tracking = {
            "pages_scraped": 0,
            "duplicates_avoided": 0,
            "boamp_skipped": 0,
            "accepted": 0
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }
        self.session.headers.update(self.headers)
        self.appeloffres_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.default_source_id = DEFAULT_SOURCE_ID
        self.default_promoter_id = DEFAULT_PROMOTER_ID

        if self.use_selenium:
            try:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,3000")
                options.add_argument("--user-agent=" + self.headers["User-Agent"])
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                self.logger.info("✅ Selenium initialisé")
            except WebDriverException as e:
                self.logger.error(f"❌ ERREUR SELENIUM: {e}")
                self.use_selenium = False

        self.load_pending_offers()
        self._load_existing_offres_set()
        self._load_validated_references()

        if self.login_appeloffres():
            self.logger.info("✅ Connexion API réussie")
        else:
            self.logger.error("❌ Échec authentification")

        self.logger.info(f"🔥 Extraction TOUS les AO France Marchés (sans mots-clés, sans secteurs)")
        self.logger.info(f"📊 Source ID: {self.default_source_id}")
        self.logger.info(f"⚠️ Skip BOAMP sources")

    def _load_validated_references(self):
        try:
            validated_docs = get_all_tenders(status="active")
            self.validated_references_set = {doc["reference"] for doc in validated_docs if doc.get("reference")}
            self.logger.info(f"✅ {len(self.validated_references_set)} références validées")
        except Exception as e:
            self.logger.error(f"Erreur: {e}")

    def _load_existing_offres_set(self):
        try:
            pending_docs = get_all_tenders(status="pending")
            for doc in pending_docs:
                ref = doc.get("reference", "")
                desc_hash = hash(doc.get("description", ""))
                self.existing_offres_set.add((ref, desc_hash))
            self.logger.info(f"✅ {len(self.existing_offres_set)} doublons pending")
        except Exception as e:
            self.logger.error(f"Erreur: {e}")

    def load_pending_offers(self):
        try:
            pending_docs = get_all_tenders(status="pending")
            self.offres_cache = []
            for doc in pending_docs:
                doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
                offre = OffreBase(**doc_without_id)
                self.offres_cache.append(offre)
                desc_hash = hash(offre.description)
                self.existing_offres_set.add((offre.reference, desc_hash))
            self.logger.info(f"✅ {len(self.offres_cache)} offres pending")
        except Exception as e:
            self.logger.error(f"Erreur: {e}")

    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def login_appeloffres(self) -> bool:
        if self.access_token:
            return True
        try:
            payload = {"email": EMAIL, "password": PASSWORD}
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = self.session_appeloffres.post(LOGIN_ENDPOINT, json=payload, headers=headers, timeout=30)
            if response.status_code in [200, 201]:
                data = response.json()
                self.access_token = data.get("accessToken")
                if self.access_token:
                    self.appeloffres_headers["Authorization"] = f"Bearer {self.access_token}"
                    return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion: {e}")
            return False

    def get_or_create_promoter(self, promoter_name: str) -> str:
        if not promoter_name:
            return self.default_promoter_id
        clean_name = self.nettoyer_texte(promoter_name)
        if clean_name in self.promoter_cache:
            return self.promoter_cache[clean_name]

        if not self.login_appeloffres():
            return self.default_promoter_id

        capitalized_promoter = capitalize_first_word(promoter_name)
        payload = {
            "name": capitalized_promoter[:100],
            "description": f"Promoteur FranceMarches: {capitalized_promoter[:100]}",
            "reference": re.sub(r'\W+', '_', promoter_name.upper())[:20],
            "isEnabled": True,
            "companyName": capitalized_promoter[:100],
            "address": {"street": "1 Rue", "city": "Paris", "country": "France", "postalCode": "75001"}
        }
        try:
            response = self.session_appeloffres.post(PROMOTER_ENDPOINT, json=payload, headers=self.appeloffres_headers, timeout=30)
            if response.status_code in [200, 201]:
                promoter_id = response.json().get("id")
                self.promoter_cache[clean_name] = str(promoter_id)
                return str(promoter_id)
        except Exception as e:
            pass
        return self.default_promoter_id

    def clean_date_str(self, date_str: str) -> str:
        if not date_str:
            return ""
        date_str = re.sub(r'[\u200E\u200F\u202A-\u202E]', '', date_str)
        date_str = re.sub(r'[^\d/\-\s:]+', '', date_str)
        return date_str.strip()

    def format_date_to_french(self, date_text: str) -> str:
        date_text = self.clean_date_str(date_text)
        if not date_text or date_text in ["N/A", "None", "null", ""]:
            return "N/A"
        try:
            date_text = re.sub(r'(\d{4})-(\d{2})-(\d{2})(\d{2}):(\d{2}):(\d{2})', r'\1-\2-\3 \4:\5:\6', date_text)
            date_text = re.sub(r'(\d{2}:\d{2}:\d{2})00:00$', r'\1', date_text)
            date_text = re.sub(r'h', ':', date_text)
            date_text = re.sub(r'\s+', ' ', date_text).strip()
            parsed_date = parse(date_text, fuzzy=True, dayfirst=True, tzinfos={None: tz.gettz('Europe/Paris')})
            return f"{parsed_date.strftime('%d/%m/%Y')} {parsed_date.strftime('%H:%M')}"
        except Exception:
            try:
                date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})|(\d{2})/(\d{2})/(\d{4})', date_text)
                if date_match:
                    if date_match.group(1):
                        year, month, day = date_match.group(1), date_match.group(2), date_match.group(3)
                        return f"{day}/{month}/{year} 00:00"
                    else:
                        day, month, year = date_match.group(4), date_match.group(5), date_match.group(6)
                        return f"{day}/{month}/{year} 00:00"
            except:
                pass
            return "N/A"

    def nettoyer_texte(self, texte: str) -> str:
        if not texte:
            return ""
        texte = unicodedata.normalize('NFKD', str(texte))
        texte = ''.join(c for c in texte if not unicodedata.combining(c))
        texte = re.sub(r'\s+', ' ', texte)
        return texte.strip().lower()

    def extraire_detail_page(self, detail_url: str) -> Dict:
        """Extrait le contenu complet de la page détail, incluant description, expiration, image URI - CORRIGÉ pour robustesse"""
        try:
            response = self.session.get(detail_url, timeout=30, headers=self.headers)
            if response.status_code != 200:
                self.logger.error(f"❌ HTTP {response.status_code} pour {detail_url}")
                return {'skip': True}

            soup = BeautifulSoup(response.text, 'html.parser')

            # Source check - skip BOAMP (recherche plus robuste)
            source_text = soup.get_text().lower()
            if 'boamp' in source_text:
                self.stats_tracking["boamp_skipped"] += 1
                self.logger.warning(f"⏭️ Skip BOAMP détecté: {detail_url}")
                return {'skip': True}

            # Description complète - cherche sections principales
            desc_selectors = ['.description', '.content', 'h1', '.title', '[class*="desc"]', '[class*="objet"]']
            full_description = ""
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    full_description = desc_elem.get_text(strip=True)
                    break
            if not full_description:
                full_description = soup.title.string.strip() if soup.title else ""

            # Date expiration - patterns plus larges
            exp_patterns = [r'date\s*limite[s]?\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})', 
                          r'expiration\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})', 
                          r'cl[ôo]t?ure\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})']
            expiration_text = "N/A"
            for pattern in exp_patterns:
                match = re.search(pattern, soup.get_text(), re.I)
                if match:
                    expiration_text = match.group(1)
                    break
            expiration_date = self.format_date_to_french(expiration_text)

            # Publication date
            pub_patterns = [r'publication\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})', 
                          r'parution\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})']
            pub_text = "N/A"
            for pattern in pub_patterns:
                match = re.search(pattern, soup.get_text(), re.I)
                if match:
                    pub_text = match.group(1)
                    break
            publication_date = self.format_date_to_french(pub_text)

            # Image URI - cherche images scan/notice
            img_selectors = ['img[src*="scan"]', 'img[src*="notice"]', 'img[class*="image"]', 'img']
            image_uri = ""
            image_base64 = ""
            for selector in img_selectors:
                img_elem = soup.select_one(selector)
                if img_elem and 'src' in img_elem.attrs:
                    image_uri = urljoin(detail_url, img_elem['src'])
                    break

            if image_uri:
                try:
                    img_resp = self.session.get(image_uri, timeout=15, headers=self.headers)
                    if img_resp.status_code == 200 and len(img_resp.content) > 100:
                        image_base64 = base64.b64encode(img_resp.content).decode('utf-8')
                    else:
                        image_base64 = ""
                except Exception as e:
                    self.logger.warning(f"❌ Erreur téléchargement image {image_uri}: {e}")
                    image_base64 = ""

            # Promoter - cherche "acheteur" ou h3
            promoter_selectors = ['h3', '[class*="acheteur"]', '[class*="promoteur"]']
            promoter = ""
            for selector in promoter_selectors:
                promoter_elem = soup.select_one(selector)
                if promoter_elem:
                    promoter = promoter_elem.get_text(strip=True)
                    break

            # Reference from URL - robuste
            ref_match = re.search(r'/appel-offre/([^/?]+)', detail_url)
            reference = ref_match.group(1) if ref_match else detail_url.split('/')[-1]

            # Location - cherche code postal
            location_match = re.search(r'\((\d{5})\)', soup.get_text())
            location = f"(75 {location_match.group(1)})" if location_match else ""

            specifications = f"{promoter} - {location}".strip()

            self.logger.info(f"✅ Détails extraits: {reference} - {full_description[:50]}...")

            return {
                'reference': reference,
                'full_description': full_description,
                'expiration_date': expiration_date,
                'publication_date': publication_date,
                'promoter': promoter,
                'specificationsReceivingAddress': specifications,
                'image_filename': image_uri,
                'image_base64': image_base64,
                'detail_url': detail_url,
                'skip': False
            }
        except Exception as e:
            self.logger.error(f"❌ Erreur extraction détail {detail_url}: {traceback.format_exc()}")
            return {'skip': True}

    def _collect_search_results(self, date_debut: str, date_fin: str) -> List[str]:
        """Collecte les URLs des pages détail depuis la recherche - CORRIGÉ pour plus de robustesse"""
        detail_urls = set()  # Évite doublons
        page = 1
        max_pages = 50  # Limite pour éviter boucle infinie

        while page <= max_pages:
            params = {
                "type": "appel-d-offre",
                "sort": "date_publication_desc",
                "date_publication_from": date_debut,
                "date_publication_to": date_fin,
                "page": str(page)
            }
            try:
                response = self.session.get(self.base_search_url, params=params, timeout=30, headers=self.headers)
                if response.status_code != 200:
                    self.logger.error(f"❌ HTTP {response.status_code} page {page}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                offer_links = soup.find_all('a', href=re.compile(r'/appel-offre/[^/]+'))

                if not offer_links:
                    self.logger.info(f"✅ Fin pagination page {page}")
                    break

                new_urls = 0
                for link in offer_links:
                    href = link['href']
                    if href.startswith('/'):
                        href = 'https://www.francemarches.com' + href
                    detail_url = urljoin(self.base_search_url, href)
                    # Quick skip BOAMP in snippet
                    snippet = link.get_text().lower()
                    if 'boamp' not in snippet:
                        detail_urls.add(detail_url)
                        new_urls += 1

                self.stats_tracking["pages_scraped"] += 1
                self.logger.info(f" → Page {page}: {new_urls} nouveaux liens (total: {len(detail_urls)})")

                if new_urls < 5:  # Si peu de nouveaux, arrêter
                    break

                page += 1
                time.sleep(1.5)  # Rate limit augmenté

            except Exception as e:
                self.logger.error(f" ❌ Page {page} failed: {traceback.format_exc()}")
                break

        return list(detail_urls)

    def traiter_offre_detail(self, detail_data: Dict) -> Optional[OffreBase]:
        """Traite les données extraites de la page détail - CORRIGÉ"""
        if detail_data.get('skip'):
            return None

        reference = detail_data['reference']
        if not reference or len(reference) < 3:
            self.logger.warning(f"❌ Référence invalide: {reference}")
            return None

        desc_clean = self.nettoyer_texte(detail_data['full_description'])
        desc_hash = hash(desc_clean)

        if (reference, desc_hash) in self.existing_offres_set:
            self.stats_tracking["duplicates_avoided"] += 1
            self.logger.info(f"⏭️ Doublon: {reference}")
            return None

        if reference in self.validated_references_set:
            self.logger.info(f"⏭️ Déjà validée: {reference}")
            return None

        self.stats_tracking["accepted"] += 1
        self.logger.info(f"✅ ACCEPTÉ: {reference} - {detail_data['promoter'][:50]}...")

        capitalized_description = capitalize_first_word(self.nettoyer_texte(detail_data['full_description'])[:200])
        expiration_date = detail_data['expiration_date']
        if expiration_date == "N/A":
            avis = "appel d'offre et avis d'attribution"
        else:
            avis = "appel d'offre"

        offre = OffreBase(
            reference=reference,
            description=capitalized_description,
            full_content=detail_data['full_description'][:500],
            promoter=capitalize_first_word(detail_data['promoter'][:100]),
            publicationDate=detail_data['publication_date'],
            expirationDate=expiration_date,
            specificationsReceivingAddress=detail_data['specificationsReceivingAddress'],
            image_filename=detail_data['image_filename'],
            image_base64=detail_data['image_base64'],
            sourceId=self.default_source_id,
            mots_cles_detectes=[],  # Vide
            secteur_activite="",  # Vide
            secteur_activite_id=None,
            activities_ids=[],  # Vide
            url_source=detail_data['detail_url'],
            avis=avis,
            pays="France",
            source="FranceMarches"
        )

        self.offres_cache.append(offre)
        self.save_to_pending(offre)
        return offre

    def scraper_offres_complet(self, date_debut: str, date_fin: str) -> Dict:
        """Scraping complet: recherche → détails → extraction - CORRIGÉ pour erreurs extraction"""
        if not date_debut or not date_fin:
            today = datetime.now()
            date_fin = today.strftime("%Y-%m-%d")
            date_debut = (today - timedelta(days=1)).strftime("%Y-%m-%d")

        self.logger.info("=" * 80)
        self.logger.info(f"🔥 SCRAPING COMPLET FRANCE MARCHÉS: {date_debut} à {date_fin}")
        self.logger.info(f"📊 Sans mots-clés, sans secteurs - Skip BOAMP")
        self.logger.info("=" * 80)

        self.stats_tracking = {
            "pages_scraped": 0,
            "duplicates_avoided": 0,
            "boamp_skipped": 0,
            "accepted": 0
        }

        # Phase 1: Collecte URLs
        detail_urls = self._collect_search_results(date_debut, date_fin)
        self.logger.info(f"📥 {len(detail_urls)} URLs collectées")

        if not detail_urls:
            self.logger.warning("⚠️ Aucune URL trouvée - vérifiez dates ou site")
            return {"offres": [], "stats": {"total_urls": 0, "new": 0, "boamp_skipped": 0, "pending": 0, "pages_scraped": 0}}

        # Phase 2: Extraction détails (séquentiel pour stabilité, max 20 pour test)
        offres = []
        max_extract = min(20, len(detail_urls))  # Limite pour éviter surcharge

        for i, url in enumerate(detail_urls[:max_extract]):
            self.logger.info(f"🔍 Extraction détail {i+1}/{max_extract}: {url}")
            detail_data = self.extraire_detail_page(url)
            offre = self.traiter_offre_detail(detail_data)
            if offre:
                offres.append(offre)
            time.sleep(2)  # Rate limit pour éviter blocage

        self.logger.info("=" * 80)
        self.logger.info("📊 RÉSULTATS FINAUX:")
        self.logger.info(f" Pages scrapées: {self.stats_tracking['pages_scraped']}")
        self.logger.info(f" BOAMP skippés: {self.stats_tracking['boamp_skipped']}")
        self.logger.info(f" Doublons évités: {self.stats_tracking['duplicates_avoided']}")
        self.logger.info(f" ✅ ACCEPTÉS: {self.stats_tracking['accepted']}")
        self.logger.info(f" 📦 FINALES: {len(offres)}")
        self.logger.info("=" * 80)

        return {
            "offres": offres,
            "stats": {
                "total_urls": len(detail_urls),
                "new": len(offres),
                "boamp_skipped": self.stats_tracking["boamp_skipped"],
                "pending": len(self.offres_cache),
                "pages_scraped": self.stats_tracking["pages_scraped"]
            }
        }

    def get_offres_cache(self, page: int = 1, limit: int = 20):
        total = len(self.offres_cache)
        start = (page - 1) * limit
        end = start + limit
        paginated_offres = self.offres_cache[start:end]

        return {
            "offres": [
                {
                    "reference": offre.reference,
                    "description": offre.description,
                    "promoter": offre.promoter,
                    "publicationDate": offre.publicationDate,
                    "expirationDate": offre.expirationDate,
                    "image_filename": offre.image_filename,
                    "url_source": offre.url_source,
                    "status": offre.status,
                    "source": offre.source,
                    "pays": offre.pays,
                    "avis": offre.avis,
                    "full_content": offre.full_content[:100]
                }
                for offre in paginated_offres
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit
        }

    def save_to_pending(self, offre):
        try:
            desc_hash = hash(offre.description)
            if (offre.reference, desc_hash) in self.existing_offres_set:
                return False

            tender_dict = offre.to_dict()
            tender_dict["status"] = "pending"
            inserted_id = insert_tender(tender_dict)

            if inserted_id:
                self.existing_offres_set.add((offre.reference, desc_hash))
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Erreur save pending {offre.reference}: {e}")
            return False

    def delete_pending_offre(self, reference: str) -> bool:
        try:
            deleted_count = delete_tender(reference)
            if deleted_count > 0:
                self.offres_cache = [o for o in self.offres_cache if o.reference != reference]
                for ref, desc_hash in list(self.existing_offres_set):
                    if ref == reference:
                        self.existing_offres_set.discard((ref, desc_hash))
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Erreur delete {reference}: {e}")
            return False

    def map_offre_to_tender_payload(self, offre) -> dict:
        def parse_date_safe(date_str):
            if not date_str or date_str == "N/A":
                return None
            try:
                date_str = self.clean_date_str(date_str)
                date_str = re.sub(r'h', ':', date_str)
                date_str = re.sub(r'\s+', ' ', date_str).strip()
                dt = parse(date_str, fuzzy=True, dayfirst=True, tzinfos={None: tz.gettz('Europe/Paris')})
                return dt
            except:
                return None

        now = datetime.now(timezone.utc)
        pub_dt = parse_date_safe(offre.publicationDate)
        if pub_dt is None or pub_dt > now:
            pub_dt = now
        publication_ts = pub_dt.isoformat()

        exp_dt = parse_date_safe(offre.expirationDate)
        if exp_dt is None or exp_dt <= now:
            exp_dt = now + timedelta(days=30)
        exp_dt = exp_dt.replace(hour=12, minute=0, second=0, microsecond=0)
        expiration_ts = exp_dt.isoformat()

        start_dt = pub_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        start_bidding_ts = start_dt.isoformat()

        batches = [{"activitiesIds": [], "title": f"Lot 1: {offre.description[:80]}", "deposit": 0}]
        promoter_id = self.get_or_create_promoter(offre.promoter)
        avis_id = 8 if offre.expirationDate == "N/A" else int(DEFAULT_AVIS_ID)

        images_list = [offre.image_filename] if offre.image_filename else []

        payload = {
            "title": offre.description[:200],
            "description": offre.description[:500],
            "publicationDate": publication_ts,
            "startBiddingDate": start_bidding_ts,
            "expirationDate": expiration_ts,
            "reference": offre.reference,
            "avisId": avis_id,
            "sourceId": int(self.default_source_id),
            "promoterId": int(promoter_id),
            "businessSectorId": None,  # Sans secteur
            "type": "international",
            "nature": "public",
            "isEnabled": True,
            "images": images_list,
            "specificationsReceivingAddress": offre.url_source or "Non disponible",
            "fundingSourceType": "national",
            "currencyId": 4,
            "isMultiCurrency": False,
            "batches": batches,
            "addresses": [{"countryId": int(DEFAULT_PAYS_ID)}],
            "pays": offre.pays,
            "source": offre.source,
            "promoter": offre.promoter,
            "avis": offre.avis,
            "url_source": offre.url_source
        }

        return {k: v for k, v in payload.items() if v is not None and v != ""}

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def post_tender_to_database(self, offre) -> dict:
        existing = get_tender_by_reference(offre.reference)
        if existing:
            return {"success": False, "message": "Déjà validée", "offre_ref": offre.reference}

        tender_dict = offre.to_dict()
        tender_dict["status"] = "active"
        tender_dict["validationDate"] = datetime.now().isoformat()

        try:
            inserted_id = insert_tender(tender_dict)
            if inserted_id:
                delete_tender(offre.reference)
                self.validated_references_set.add(offre.reference)

            api_success = False
            api_id = None
            error_detail = ""

            try:
                if not self.login_appeloffres():
                    error_detail = "Échec connexion API"
                else:
                    payload = self.map_offre_to_tender_payload(offre)
                    response = self.session_appeloffres.post(TENDER_ENDPOINT, json=payload, headers=self.appeloffres_headers, timeout=30)
                    if response.status_code in [200, 201]:
                        response_data = response.json()
                        api_id = response_data.get("id")
                        api_success = True
                        update_tender(offre.reference, {"external_api_id": api_id})
                        self.logger.info(f"✅ API OK: {offre.reference} - ID: {api_id}")
                    else:
                        error_text = response.text[:500]
                        try:
                            error_json = response.json()
                            error_detail = str(error_json.get('message', error_text))
                        except:
                            error_detail = error_text
            except Exception as e:
                error_detail = str(e)[:200]

            message = f"✅ Validée (MongoDB + API ID: {api_id})" if api_success else f"⚠️ Validée MongoDB mais échec API: {error_detail}"
            return {
                "success": True,
                "message": message,
                "offre_ref": offre.reference,
                "api_id": api_id,
                "api_success": api_success,
                "api_error": error_detail if not api_success else None
            }
        except Exception as e:
            self.logger.error(f"❌ ERREUR MONGODB: {traceback.format_exc()}")
            return {"success": False, "message": f"Erreur MongoDB: {str(e)}", "offre_ref": offre.reference}

def nettoyer_base_pending():
    try:
        deleted_count = delete_all_pending()
        print(f"🗑️ {deleted_count} offres supprimées")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

# Flask App
app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path='', template_folder=REACT_BUILD_DIR)
CORS(app)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

scraper = FranceMarchesScraperAll(use_selenium=False, skip_s3=False)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    file_path = os.path.join(REACT_BUILD_DIR, path)
    if path != "" and os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path)
    else:
        if os.path.exists(INDEX_HTML_PATH):
            return send_file(INDEX_HTML_PATH)
        return "Erreur", 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    data = request.json
    date_debut = data.get('date_debut')
    date_fin = data.get('date_fin')
    logger.info(f"🚀 API /scrape appelée: {date_debut} à {date_fin}")
    result = scraper.scraper_offres_complet(date_debut, date_fin)
    paginated = scraper.get_offres_cache(page=1, limit=20)
    return jsonify({"success": True, "offres": paginated, "stats": result["stats"]})

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_offre(reference):
    for offre in scraper.offres_cache[:]:
        if offre.reference == reference:
            result = scraper.post_tender_to_database(offre)
            if result['success']:
                scraper.offres_cache.remove(offre)
            return jsonify(result)

    pending_doc = get_tender_by_reference(reference)
    if pending_doc and pending_doc.get('status') == 'pending':
        doc_without_id = {k: v for k, v in pending_doc.items() if k not in ['_id', 'id']}
        offre = OffreBase(**doc_without_id)
        result = scraper.post_tender_to_database(offre)
        if result['success']:
            scraper.offres_cache = [o for o in scraper.offres_cache if o.reference != reference]
            delete_tender(reference)
        return jsonify(result)

    return jsonify({"success": False, "message": "Non trouvée", "offre_ref": reference})

@app.route('/api/delete/<reference>', methods=['DELETE'])
def delete_offre(reference):
    if scraper.delete_pending_offre(reference):
        return jsonify({"success": True, "message": "Supprimée", "offre_ref": reference})
    return jsonify({"success": False, "message": "Non trouvée", "offre_ref": reference})

@app.route('/api/pending', methods=['GET'])
def get_pending():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    paginated = scraper.get_offres_cache(page=page, limit=limit)
    return jsonify({"success": True, "pending": paginated})

@app.route('/api/clean_pending', methods=['POST'])
def clean_pending():
    try:
        deleted_count = delete_all_pending()
        scraper.offres_cache = []
        scraper.existing_offres_set = set()
        scraper._load_existing_offres_set()
        return jsonify({"success": True, "message": f"{deleted_count} supprimées", "count": deleted_count})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_pending = count_tenders(status="pending")
        total_validated = count_tenders(status="active")
        return jsonify({
            "success": True,
            "stats": {
                "total_pending": total_pending,
                "total_validated": total_validated,
                "boamp_skipped": scraper.stats_tracking.get("boamp_skipped", 0),
                "accepted": scraper.stats_tracking.get("accepted", 0),
                "pages_scraped": scraper.stats_tracking.get("pages_scraped", 0)
            }
        })
    except Exception as e:
        logger.error(f"❌ Erreur get_stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé du serveur"""
    try:
        # Vérifier la connexion PostgreSQL
        conn = get_db_connection()
        if conn:
            conn.close()
            db_status = "connected"
        else:
            db_status = "disconnected"

        return jsonify({
            "success": True,
            "status": "running",
            "database": db_status,
            "port": 5003,
            "service": "BOAMP Scraper"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de test simple"""
    return jsonify({
        "success": True,
        "message": "BOAMP API is running",
        "version": "2.0.0",
        "database": "PostgreSQL"
    })

@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    """Retourne la liste des mots-clés (vide pour BOAMP car extraction complète)"""
    return jsonify({
        "success": True,
        "keywords": [],
        "message": "BOAMP scraper extrait TOUS les AO sans filtrage par mots-clés"
    })

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 BACKEND API FRANCE MARCHÉS - Extraction Complète (Corrigé)")
    print("=" * 80)
    print("🔥 CONFIGURATION:")
    print(f" ✅ TOUS les AO (sans mots-clés, sans secteurs)")
    print(f" ✅ Source ID: {DEFAULT_SOURCE_ID}")
    print(f" ✅ DB: {DB_NAME}")
    print(f" ✅ Port API: 5003")
    print(f" ✅ Frontend: http://localhost:5003")
    print("=" * 80)
    print("🗑️ Nettoyage base pending...")
    nettoyer_base_pending()
    print("=" * 80)
    print("🌐 API démarrée sur http://localhost:5003")
    print("💡 Ouvrez http://localhost:5003 pour scraper")
    print("⚠️ Extraction via bouton frontend - Skip BOAMP auto - Limite 20 pour test")
    print("✅ Code corrigé: robustesse extraction, logs détaillés, rate limit")
    print("=" * 80)
    app.run(debug=True, port=5003, host='0.0.0.0')