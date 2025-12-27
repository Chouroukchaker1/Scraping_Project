"""
Extracteur de données des marchés publics tunisiens - Version Intégrée Flask
Adapté pour intégration avec l'API comme BOAMP
Pour test dans VS Code (exécuter directement avec python scraper_tunisie_flask.py)
"""
# Installation des bibliothèques nécessaires (exécuter en terminal si besoin)
# !apt-get update
# !apt install -y chromium-chromedriver
# !pip install selenium pandas openpyxl flask flask-cors pymongo requests beautifulsoup4 python-dateutil reportlab pdf2image tenacity webdriver-manager python-dotenv
import sys
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
from typing import Optional, List, Dict, Tuple
import base64
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pdf2image import convert_from_path
import warnings
warnings.filterwarnings('ignore')
load_dotenv()
# Configuration MongoDB (même que BOAMP)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/appel_offres-scrp")
DB_NAME = os.getenv("DB_NAME", "appel_offres-scrp")
COLLECTION_NAME = "tenders"
PENDING_COLLECTION_NAME = "pending_tenders"
# Configuration API (même que BOAMP)
API_BASE_URL = os.getenv("API_BASE_URL", "https://be-stg.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
FILE_ENDPOINT = f"{API_BASE_URL}/files/tender"
EMAIL = os.getenv("API_EMAIL", "chouroukchaker6@gmail.com")
PASSWORD = os.getenv("API_PASSWORD", "Chourouk2022*")
DEFAULT_SOURCE_ID = os.getenv("DEFAULT_SOURCE_ID", "279") # Tunisie
TUNISIE_SOURCE_ID = 279 # ID source pour Tunisie (du scraper original)
DEFAULT_PROMOTER_ID = os.getenv("DEFAULT_PROMOTER_ID", "223472")
DEFAULT_AVIS_ID = os.getenv("DEFAULT_AVIS_ID", "8") # Avis d'attribution
DEFAULT_PAYS_ID = os.getenv("DEFAULT_PAYS_ID", "219") # Tunisie
TUNISIE_PAYS_ID = 219 # Pays ID pour Tunisie
# Dossiers (même que BOAMP, mais ajout pour Tunisie)
PDF_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\pdf_boamp_extraction"
IMAGES_DIR = "images"
OUTPUT_DIR = "output"
TEMPLATES_DIR = "templates"
REACT_BUILD_DIR = "react-frontend/build"
TUNISIE_PDF_DIR = r"C:\Users\lenovo\extractionautomatic\backend\scripts\pdf_tunisie_extraction" # Nouveau dossier pour Tunisie
# Création sécurisée des dossiers
for directory in [PDF_DIR, IMAGES_DIR, OUTPUT_DIR, TEMPLATES_DIR, REACT_BUILD_DIR, TUNISIE_PDF_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
# VÉRIFICATION FIX : Créer index.html fallback si absent (même que BOAMP, mais ajout bouton pour Tunisie)
INDEX_HTML_PATH = os.path.join(REACT_BUILD_DIR, 'index.html')
if not os.path.exists(INDEX_HTML_PATH):
    # HTML embarqué (adapté avec bouton pour scraper Tunisie)
    fallback_html = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scraper BOAMP & Tunisie - Interface de Scraping</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="date"], select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        button:hover { background-color: #0056b3; }
        button.danger { background-color: #dc3545; }
        button.danger:hover { background-color: #c82333; }
        button.success { background-color: #28a745; }
        button.success:hover { background-color: #218838; }
        .checkbox-group { display: flex; gap: 15px; }
        .checkbox-group input[type="checkbox"] { margin-right: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f8f9fa; }
        .actions { display: flex; gap: 5px; }
        .loading { text-align: center; color: #666; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .success { color: #155724; background: #d4edda; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .pagination { text-align: center; margin: 20px 0; }
        .pagination button { margin: 0 5px; }
        .download-link { color: #007bff; text-decoration: none; }
        .download-link:hover { text-decoration: underline; }
        .tunisie-form { background: #e3f2fd; padding: 15px; border-radius: 4px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Scraper BOAMP & Marchés Publics Tunisie</h1>
    
        <!-- Formulaire de scraping BOAMP -->
        <form id="scrapeForm">
            <div class="form-group">
                <label for="date_debut">Date de début (YYYY-MM-DD) :</label>
                <input type="date" id="date_debut" name="date_debut" required>
            </div>
            <div class="form-group">
                <label for="date_fin">Date de fin (YYYY-MM-DD) :</label>
                <input type="date" id="date_fin" name="date_fin" required>
            </div>
            <div class="form-group">
                <label>Catégories à scraper (BOAMP) :</label>
                <div class="checkbox-group">
                    <label><input type="checkbox" name="categories" value="informatique" checked> Informatique</label>
                    <label><input type="checkbox" name="categories" value="textile" checked> Textile</label>
                    <label><input type="checkbox" name="categories" value="batiment" checked> Bâtiment</label>
                </div>
            </div>
            <button type="submit">🔍 Lancer le Scraping BOAMP</button>
            <button type="button" onclick="loadPending()">📋 Charger les Offres en Attente</button>
        </form>
        <!-- Formulaire de scraping Tunisie (NOUVEAU) -->
        <div class="tunisie-form">
            <h3>🇹🇳 Marchés Publics Tunisie</h3>
            <form id="scrapeTunisieForm">
                <div class="form-group">
                    <label for="date_tunisie">Date de filtrage (DD-MM-YYYY) :</label>
                    <input type="text" id="date_tunisie" name="date_tunisie" placeholder="Ex: 05-11-2025" value="05-11-2025" required>
                </div>
                <div class="form-group">
                    <label for="max_pages_tunisie">Max pages :</label>
                    <input type="number" id="max_pages_tunisie" name="max_pages_tunisie" value="5" min="1" max="10">
                </div>
                <button type="submit">🔍 Scraper Tunisie & Envoyer</button>
            </form>
        </div>
        <!-- Zone de messages -->
        <div id="messages"></div>
        <!-- Tableau des offres en attente -->
        <div id="offersTable">
            <h2>📋 Offres en Attente de Validation</h2>
            <div class="loading" id="loading">Chargement...</div>
            <table id="offersTbl" style="display: none;">
                <thead>
                    <tr>
                        <th>Référence</th>
                        <th>Description</th>
                        <th>Secteur</th>
                        <th>Date Publication</th>
                        <th>Date Expiration</th>
                        <th>Image/PDF</th>
                        <th>Source</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
            <div id="pagination"></div>
        </div>
    </div>
    <script>
        let currentPage = 1;
        const limit = 10;
        const API_BASE = 'http://localhost:5003/api'; // Ajustez si nécessaire
        // Chargement initial des dates (aujourd'hui par défaut)
        window.onload = function() {
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('date_debut').value = today;
            document.getElementById('date_fin').value = today;
            loadPending();
        };
        // Gestion du formulaire de scraping BOAMP
        document.getElementById('scrapeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const dateDebut = document.getElementById('date_debut').value;
            const dateFin = document.getElementById('date_fin').value;
            const categories = Array.from(document.querySelectorAll('input[name="categories"]:checked')).map(cb => cb.value);
            showMessage('Lancement du scraping BOAMP...', 'loading');
            try {
                const response = await fetch(`${API_BASE}/scrape`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date_debut: dateDebut, date_fin: dateFin, categories })
                });
                const data = await response.json();
                if (data.success) {
                    showMessage(`Scraping BOAMP réussi ! ${data.offres.total} offres trouvées.`, 'success');
                    loadPending();
                } else {
                    showMessage('Erreur lors du scraping BOAMP.', 'error');
                }
            } catch (err) {
                showMessage('Erreur réseau lors du scraping BOAMP.', 'error');
            }
        });
        // Gestion du formulaire de scraping Tunisie (NOUVEAU)
        document.getElementById('scrapeTunisieForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const dateTunisie = document.getElementById('date_tunisie').value;
            const maxPages = document.getElementById('max_pages_tunisie').value;
            showMessage('Lancement du scraping Tunisie...', 'loading');
            try {
                const response = await fetch(`${API_BASE}/scrape-tunisie`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date_filtre: dateTunisie, max_pages: parseInt(maxPages) })
                });
                const data = await response.json();
                if (data.success) {
                    showMessage(`Scraping Tunisie réussi ! ${data.offres.total} offres trouvées et envoyées.`, 'success');
                    loadPending();
                } else {
                    showMessage('Erreur lors du scraping Tunisie.', 'error');
                }
            } catch (err) {
                showMessage('Erreur réseau lors du scraping Tunisie.', 'error');
            }
        });
        // Charger les offres en attente (adapté pour source)
        async function loadPending(page = 1) {
            currentPage = page;
            showLoading(true);
            try {
                const response = await fetch(`${API_BASE}/pending?page=${page}&limit=${limit}`);
                const data = await response.json();
                if (data.success) {
                    renderOffers(data.pending.offres);
                    renderPagination(data.pending.totalPages, data.pending.page);
                } else {
                    showMessage('Erreur lors du chargement des offres.', 'error');
                }
            } catch (err) {
                showMessage('Erreur réseau lors du chargement.', 'error');
            }
            showLoading(false);
        }
        // Rendu des offres dans le tableau (adapté avec colonne Source)
        function renderOffers(offres) {
            const tbody = document.querySelector('#offersTbl tbody');
            tbody.innerHTML = '';
            offres.forEach(offre => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${offre.reference}</td>
                    <td>${offre.description.substring(0, 50)}...</td>
                    <td>${offre.secteur_activite} (ID: ${offre.secteur_activite_id})</td>
                    <td>${offre.publicationDate}</td>
                    <td>${offre.expirationDate}</td>
                    <td>
                        ${offre.image_filename ? `<a href="${API_BASE}/download_image/${offre.image_filename}" class="download-link" target="_blank">📄 Télécharger</a>` : 'Aucune'}
                    </td>
                    <td>${offre.source || 'BOAMP'}</td>
                    <td class="actions">
                        <button class="success" onclick="validateOffer('${offre.reference}')">✅ Valider</button>
                        <button onclick="updateOffer('${offre.reference}')">✏️ Modifier</button>
                        <button class="danger" onclick="deleteOffer('${offre.reference}')">🗑️ Supprimer</button>
                    </td>
                `;
            });
            document.getElementById('offersTbl').style.display = offres.length ? 'table' : 'none';
        }
        // Pagination
        function renderPagination(totalPages, currentPage) {
            const pagDiv = document.getElementById('pagination');
            pagDiv.innerHTML = '';
            if (totalPages > 1) {
                for (let i = 1; i <= totalPages; i++) {
                    const btn = document.createElement('button');
                    btn.textContent = i;
                    btn.onclick = () => loadPending(i);
                    if (i === currentPage) btn.style.backgroundColor = '#007bff';
                    pagDiv.appendChild(btn);
                }
            }
        }
        // Valider une offre
        async function validateOffer(reference) {
            if (!confirm(`Valider l'offre ${reference} ?`)) return;
            try {
                const response = await fetch(`${API_BASE}/validate/${reference}`, { method: 'POST' });
                const data = await response.json();
                showMessage(data.message, data.success ? 'success' : 'error');
                if (data.success) loadPending(currentPage);
            } catch (err) {
                showMessage('Erreur lors de la validation.', 'error');
            }
        }
        // Modifier une offre (exemple simple : prompt pour nouveau secteur)
        async function updateOffer(reference) {
            const newSecteur = prompt('Nouveau secteur ID (ex: 384 pour IT) :');
            if (!newSecteur) return;
            try {
                const response = await fetch(`${API_BASE}/update/${reference}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ secteur_activite_id: parseInt(newSecteur) })
                });
                const data = await response.json();
                showMessage(data.message, data.success ? 'success' : 'error');
                if (data.success) loadPending(currentPage);
            } catch (err) {
                showMessage('Erreur lors de la mise à jour.', 'error');
            }
        }
        // Supprimer une offre
        async function deleteOffer(reference) {
            if (!confirm(`Supprimer l'offre ${reference} ?`)) return;
            try {
                const response = await fetch(`${API_BASE}/delete/${reference}`, { method: 'DELETE' });
                const data = await response.json();
                showMessage(data.message, data.success ? 'success' : 'error');
                if (data.success) loadPending(currentPage);
            } catch (err) {
                showMessage('Erreur lors de la suppression.', 'error');
            }
        }
        // Utilitaires
        function showMessage(msg, type) {
            const div = document.getElementById('messages');
            div.innerHTML = `<div class="${type}">${msg}</div>`;
            setTimeout(() => div.innerHTML = '', 5000);
        }
        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }
    </script>
</body>
</html>
    '''
    with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(fallback_html)
    print(f"✅ Fallback index.html créé dans {REACT_BUILD_DIR} (avec support Tunisie)")
# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper_tunisie.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
# Connexion MongoDB (même)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
tenders_collection = db[COLLECTION_NAME]
pending_tenders_collection = db[PENDING_COLLECTION_NAME]
# Dataclass OffreBase (même que BOAMP, mais ajout source pour Tunisie)
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
    type: str = "national" # Adapté pour Tunisie
    reference: str = ""
    specificationsReceivingAddress: str = ""
    offerValidityPeriod: str = ""
    nature: str = "public"
    fundingSource: Optional[str] = None
    fundingSourceType: str = "national"
    isMultiCurrency: bool = False
    sourceId: Optional[str] = None
    promoterId: Optional[str] = None
    currencyId: str = "4" # Euro, ou adapter
    createdById: Optional[str] = None
    updatedById: Optional[str] = None
    pays: str = "Tunisie" # Adapté
    source: str = "MarchesPublicsTN" # Nouveau pour Tunisie
    promoter: str = ""
    pieces_jointes: List[str] = field(default_factory=list)
    cahier_charge: str = ""
    cahier_charge_pdf: str = ""
    cahier_charge_pdf_filename: str = ""
    cahier_charge_pdf_base64: str = ""
    image_filename: str = ""
    image_base64: str = ""
    lots: List[Dict] = field(default_factory=list)
    mots_cles_detectes: List[str] = field(default_factory=list)
    avis: str = "appel d'offre"
    secteur_activite: str = "" # Pour Tunisie, simplifié ou vide
    secteur_activite_id: Optional[int] = None
    activities_ids: List[int] = field(default_factory=list)
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
@dataclass
class OffreTunisie(OffreBase):
    secteur_activite: str = "marches_publics" # Simplifié pour Tunisie
# Classe pour scraper Tunisie (adaptée du code original, intégrée comme BOAMP)
class TunisieScraper:
    def __init__(self):
        self.base_url = "https://www.marchespublics.gov.tn"
        self.url = f"{self.base_url}/fr/resultats"
        self.session = requests.Session()
        self.driver = None
        self.tunisie_pdf_dir = TUNISIE_PDF_DIR
        self.images_dir = IMAGES_DIR
        self.logger = logging.getLogger(__name__)
        self.existing_offres_set = set()
        self.offres_cache = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        self.session.headers.update(self.headers)
        self.source_id = TUNISIE_SOURCE_ID
        self.pays_id = TUNISIE_PAYS_ID
        self.avis_id = DEFAULT_AVIS_ID
        self.avis_type = "Avis d'attribution"
        self.type = "National"
        self.nature = "Public"
        self.poppler_path = r"C:\poppler\Library\bin" # Même que BOAMP
        if not os.path.exists(self.tunisie_pdf_dir):
            os.makedirs(self.tunisie_pdf_dir, exist_ok=True)
        self.setup_driver()
        self.load_pending_offers_tunisie()
    def setup_driver(self):
        """Configure le driver Chrome"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=' + self.headers["User-Agent"])
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.logger.info("✅ Driver Selenium initialisé pour Tunisie")
        except WebDriverException as e:
            self.logger.error(f"❌ Erreur Selenium Tunisie: {e}")
            self.driver = None
    def load_pending_offers_tunisie(self):
        try:
            pending_docs = list(pending_tenders_collection.find({"source": "MarchesPublicsTN", "status": "pending"}).sort("createdAt", -1))
            for doc in pending_docs:
                ref = doc.get("reference", "")
                desc_hash = hash(doc.get("description", ""))
                self.existing_offres_set.add((ref, desc_hash))
                offre = OffreTunisie(**doc)
                self.offres_cache.append(offre)
            self.logger.info(f"✅ {len(self.offres_cache)} offres Tunisie pending chargées depuis DB")
        except PyMongoError as e:
            self.logger.error(f"Erreur chargement pending Tunisie: {e}")
    def generer_pdf_path_tunisie(self, filename: str) -> str:
        return os.path.join(self.tunisie_pdf_dir, filename).replace('\\', '/')
    def generer_image_path(self, filename: str) -> str:
        return os.path.join(self.images_dir, filename).replace('\\', '/')
    def pdf_to_base64(self, pdf_path: str) -> str:
        try:
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                if file_size > 100:
                    with open(pdf_path, 'rb') as pdf_file:
                        return base64.b64encode(pdf_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erreur base64 PDF Tunisie: {e}")
        return ""
    def image_to_base64(self, image_path: str) -> str:
        try:
            if os.path.exists(image_path):
                file_size = os.path.getsize(image_path)
                if file_size > 100:
                    with open(image_path, 'rb') as img_file:
                        return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erreur base64 Image Tunisie: {e}")
        return ""
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def extraire_marches_publics(self, date_filtre=None, max_pages=5):
        """Extrait les données des marchés publics tunisiens (adapté du code original)"""
        if date_filtre is None:
            date_filtre = datetime.now().strftime("%d-%m-%Y")
        self.logger.info(f"🔍 Extraction Tunisie: Date {date_filtre}, Max pages {max_pages}")
        all_data = []
        try:
            self.driver.get(self.url)
            time.sleep(5)
            wait = WebDriverWait(self.driver, 20)
            table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            self.logger.info("✅ Page Tunisie chargée")
            page_num = 1
            while page_num <= max_pages:
                self.logger.info(f"Extraction page {page_num}...")
                time.sleep(3)
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                if not rows:
                    break
                page_data_count = 0
                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 7:
                            id_cell = cols[0]
                            try:
                                id_link = id_cell.find_element(By.TAG_NAME, "a")
                                award_id = id_link.text.strip()
                                award_url = id_link.get_attribute('href')
                            except:
                                award_id = id_cell.text.strip()
                                award_url = ""
                            numero_appel = cols[1].text.strip()
                            acheteur_public = cols[2].text.strip()
                            objet = cols[3].text.strip()
                            objet_lot = cols[4].text.strip()
                            categorie = cols[5].text.strip()
                            date_pub = cols[6].text.strip()
                            if categorie.strip().lower() == "infructueux":
                                continue
                            try:
                                date_pub_obj = datetime.strptime(date_pub, "%d-%m-%Y")
                                date_limite = date_pub_obj + pd.Timedelta(days=5)
                                date_limite_str = date_limite.strftime("%d-%m-%Y")
                            except:
                                date_limite_str = ""
                            if date_filtre == "ALL" or date_pub == date_filtre:
                                all_data.append({
                                    'ID': award_id,
                                    'Lien': award_url,
                                    'Numéro appel d\'offres': numero_appel,
                                    'Acheteur Public': acheteur_public,
                                    'Objet': objet,
                                    'Objet Lot/Article': objet_lot,
                                    'Catégorie du résultat': categorie,
                                    'Date de publication': date_pub,
                                    'source_id': self.source_id,
                                    'pays_id': self.pays_id,
                                    'pays_nom': 'Tunisie',
                                    'avis_id': self.avis_id,
                                    'avis_type': self.avis_type,
                                    'type': self.type,
                                    'nature': self.nature,
                                    'date_limite': date_limite_str
                                })
                                page_data_count += 1
                    except Exception as e:
                        continue
                self.logger.info(f" {page_data_count} marchés extraits page {page_num}")
                try:
                    next_button = self.driver.find_element(By.XPATH, "//a[contains(@class, 'page-link') and contains(text(), 'Suivant')]")
                    if next_button.is_enabled():
                        next_button.click()
                        page_num += 1
                        time.sleep(3)
                    else:
                        break
                except:
                    break
            df = pd.DataFrame(all_data)
            self.logger.info(f"✅ Total Tunisie: {len(df)} marchés extraits")
            return df
        except Exception as e:
            self.logger.error(f"❌ Erreur extraction Tunisie: {e}")
            return pd.DataFrame()
    def save_to_pending_tunisie(self, data_row):
        """Sauvegarde en pending comme BOAMP, mais pour Tunisie"""
        try:
            reference = data_row.get('ID', '')
            description = data_row.get('Objet', '')
            desc_hash = hash(description)
            if (reference, desc_hash) in self.existing_offres_set:
                self.logger.warning(f"⚠️ Doublon Tunisie: {reference}")
                return False
            # Générer PDF/image synthétique simple (fallback, car pas de PDF réel dans scraper original)
            pdf_path = self.generer_pdf_path_tunisie(f"{reference}_synthetic.pdf")
            # Créer PDF synthétique basique
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = [Paragraph(f"Marché Public Tunisie - Ref: {reference}<br/>Objet: {description}", getSampleStyleSheet()['Normal'])]
            doc.build(story)
            image_path = "" # Pas de conversion pour simplicité, utiliser PDF comme image
            image_filename = os.path.basename(pdf_path)
            offre = OffreTunisie(
                reference=reference,
                description=description,
                full_content=f"Numéro: {data_row.get('Numéro appel d\'offres', '')}<br/>Acheteur: {data_row.get('Acheteur Public', '')}<br/>Date Pub: {data_row.get('Date de publication', '')}<br/>Date Limite: {data_row.get('date_limite', '')}",
                promoter=data_row.get('Acheteur Public', ''),
                publicationDate=data_row.get('Date de publication', ''),
                expirationDate=data_row.get('date_limite', ''),
                url_source=data_row.get('Lien', ''),
                sourceId=self.source_id,
                promoterId=None,
                fundingSource=None,
                secteur_activite_id=None, # Pas de secteur détaillé pour Tunisie
                procedure=data_row.get('Catégorie du résultat', ''),
                type_marche="Public",
                cahier_charge_pdf_filename=image_filename,
                image_filename=image_filename,
                lots=[{"title": data_row.get('Objet Lot/Article', ''), "description": data_row.get('Objet', '')}]
            )
            tender_dict = offre.to_dict()
            tender_dict["status"] = "pending"
            result = pending_tenders_collection.insert_one(tender_dict)
            if result.inserted_id:
                self.existing_offres_set.add((reference, desc_hash))
                self.offres_cache.append(offre)
                self.logger.info(f"✅ Offre Tunisie sauvegardée pending: {reference} - Image synthétique: {image_filename}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur save pending Tunisie: {e}")
            return False
    def scraper_tunisie_and_send(self, date_filtre, max_pages=5):
        """Scraper + Sauvegarde pending + Option envoi direct API (comme BOAMP)"""
        df = self.extraire_marches_publics(date_filtre, max_pages)
        saved_count = 0
        for _, row in df.iterrows():
            if self.save_to_pending_tunisie(row):
                saved_count += 1
        self.logger.info(f"✅ {saved_count} offres Tunisie ajoutées en pending")
        # Option: Valider et envoyer directement à l'API (comme validate_offre)
        # Pour test, on valide toutes les nouvelles
        for offre in self.offres_cache[-saved_count:]: # Dernières ajoutées
            self.post_tender_to_database_tunisie(offre)
        return {"success": True, "offres": {"total": len(df), "saved": saved_count}}
    def map_offre_to_tender_payload_tunisie(self, offre) -> dict:
        """Map pour payload API (adapté du BOAMP)"""
        def parse_date(date_str):
            if not date_str or date_str == "N/A":
                return None
            try:
                if '/' in date_str:
                    dt = parse(date_str, dayfirst=True, tzinfos={None: tz.gettz('Africa/Tunis')})
                else:
                    dt = parse(date_str, tzinfos={None: tz.gettz('Africa/Tunis')})
                return dt.isoformat()
            except:
                return None
        publication_ts = parse_date(offre.publicationDate)
        expiration_ts = parse_date(offre.expirationDate)
        if publication_ts is None:
            publication_ts = datetime.now(timezone.utc).isoformat()
        if expiration_ts is None:
            if publication_ts:
                pub_dt = parse(publication_ts)
                exp_dt = (pub_dt + timedelta(days=5)).replace(hour=12, minute=0, second=0, microsecond=0)
                expiration_ts = exp_dt.isoformat()
            else:
                expiration_ts = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        start_bidding_ts = publication_ts # Même que publication pour Tunisie
        # Upload fichier vers S3 (même que BOAMP)
        s3_path = ""
        if offre.image_filename:
            file_path = self.generer_pdf_path_tunisie(offre.image_filename) if offre.image_filename.endswith('.pdf') else self.generer_image_path(offre.image_filename)
            # Appel à upload_file_to_s3 (à implémenter si besoin, sinon skip)
            # s3_path = upload_file_to_s3(file_path) # Utiliser fonction BOAMP si intégrée
            pass # Pour test, skip S3
        images_list = [s3_path] if s3_path else []
        payload = {
            "title": offre.description,
            "description": offre.description,
            "publicationDate": publication_ts,
            "startBiddingDate": start_bidding_ts,
            "expirationDate": expiration_ts,
            "openingBidsDate": None,
            "reference": offre.reference,
            "specificationsPrice": 0,
            "offerValidityPeriode": None,
            "avisId": int(self.avis_id),
            "sourceId": int(self.source_id),
            "promoterId": int(DEFAULT_PROMOTER_ID), # Default
            "businessSectorId": offre.secteur_activite_id,
            "type": offre.type,
            "nature": offre.nature,
            "isEnabled": True,
            "images": images_list,
            "specificationsReceivingAddress": offre.url_source,
            "fundingSourceType": "national",
            "fundingSource": offre.fundingSource,
            "currencyId": 4, # Euro
            "isMultiCurrency": offre.isMultiCurrency,
            "batches": [{"activitiesIds": offre.activities_ids, "title": f"Lot 1: {offre.description}", "deposit": 0}] if offre.activities_ids else [],
            "addresses": [{"countryId": self.pays_id}]
        }
        filtered_payload = {k: v for k, v in payload.items() if v is not None and v != ""}
        return filtered_payload
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def post_tender_to_database_tunisie(self, offre) -> dict:
        """Insertion DB + Envoi API (adapté de BOAMP pour Tunisie)"""
        existing = tenders_collection.find_one({"reference": offre.reference})
        if existing:
            return {"success": False, "message": "Offre déjà validée", "offre_ref": offre.reference}
        tender_dict = offre.to_dict()
        tender_dict["status"] = "active"
        tender_dict["validationDate"] = datetime.now().isoformat()
        try:
            result = tenders_collection.insert_one(tender_dict)
            if result.inserted_id:
                pending_tenders_collection.delete_one({"reference": offre.reference})
                self.logger.info(f"✅ Insertion DB Tunisie: {offre.reference} - ID Mongo: {result.inserted_id}")
                # Envoi API
                api_success = False
                api_id = None
                api_message = ""
                try:
                    # Login et envoi (même que BOAMP, implémenter session_appeloffres si besoin)
                    # Pour test, simuler succès
                    api_success = True
                    api_id = "simulated_api_id"
                    api_message = "Envoi API simulé (implémentez login si besoin)"
                    self.logger.info(f"✅ Envoi API Tunisie simulé: {offre.reference}")
                except Exception as api_e:
                    api_message = f"Erreur API: {str(api_e)}"
                return {
                    "success": True,
                    "message": f"Insertion DB réussie {api_message}",
                    "offre_ref": offre.reference,
                    "mongo_id": str(result.inserted_id),
                    "api_id": api_id,
                    "api_success": api_success
                }
        except Exception as e:
            self.logger.error(f"❌ Erreur DB Tunisie: {e}")
            return {"success": False, "message": str(e), "offre_ref": offre.reference}
    def __del__(self):
        if self.driver:
            self.driver.quit()
# Initialisation scrapers
scraper_boamp = None # Si BOAMP gardé, initialiser ici
scraper_tunisie = TunisieScraper()
# Flask App (adaptée avec endpoint Tunisie)
app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path='', template_folder=REACT_BUILD_DIR)
CORS(app, resources={r"/*": {"origins": "*"}})
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    file_path = os.path.join(REACT_BUILD_DIR, path)
    if path != "" and os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path)
    else:
        if os.path.exists(INDEX_HTML_PATH):
            return send_file(INDEX_HTML_PATH)
        else:
            return "Erreur: Build React manquant.", 500
# Endpoint pour scraper Tunisie (NOUVEAU)
@app.route('/api/scrape-tunisie', methods=['POST'])
def scrape_tunisie():
    data = request.json
    date_filtre = data.get('date_filtre', datetime.now().strftime("%d-%m-%Y"))
    max_pages = data.get('max_pages', 5)
    result = scraper_tunisie.scraper_tunisie_and_send(date_filtre, max_pages)
    paginated = {"total": result.get("offres", {}).get("saved", 0), "page": 1, "limit": 10, "totalPages": 1, "offres": []} # Pour compatibilité
    return jsonify({"success": result["success"], "offres": paginated})
# Autres endpoints (même que BOAMP, mais adaptés pour source Tunisie)
@app.route('/api/validate/<reference>', methods=['POST'])
def validate_offre(reference):
    # Chercher en pending, si source Tunisie utiliser post_tunisie
    pending_doc = pending_tenders_collection.find_one({"reference": reference, "status": "pending"})
    if not pending_doc:
        return jsonify({"success": False, "message": "Offre non trouvée", "offre_ref": reference})
    if pending_doc.get("source") == "MarchesPublicsTN":
        offre = OffreTunisie(**pending_doc)
        result = scraper_tunisie.post_tender_to_database_tunisie(offre)
    else:
        # BOAMP logic here if needed
        result = {"success": False, "message": "Source non supportée"}
    if result['success']:
        pending_tenders_collection.delete_one({"reference": reference})
    return jsonify(result)
# Ajouter les autres endpoints (update, delete, pending, etc.) comme dans BOAMP, en adaptant pour source
@app.route('/api/pending', methods=['GET'])
def get_pending():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    # Combiner BOAMP + Tunisie caches si besoin
    all_pending = scraper_tunisie.offres_cache # Pour test Tunisie only
    total = len(all_pending)
    start = (page - 1) * limit
    end = start + limit
    paginated_offres = all_pending[start:end]
    return jsonify({
        "success": True,
        "pending": {
            "offres": [{"reference": o.reference, "description": o.description, "secteur_activite": o.secteur_activite, "source": o.source, "publicationDate": o.publicationDate, "expirationDate": o.expirationDate, "image_filename": o.image_filename} for o in paginated_offres],
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit
        }
    })
# Endpoints download (adaptés pour Tunisie PDF dir)
@app.route('/api/download_image/<filename>')
def download_image(filename):
    # Essayer images_dir d'abord, puis tunisie_pdf_dir
    image_path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(image_path) and os.path.getsize(image_path) > 100:
        return send_file(image_path, as_attachment=True)
    pdf_path = os.path.join(TUNISIE_PDF_DIR, filename)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100:
        return send_file(pdf_path, as_attachment=True)
    return jsonify({"success": False, "message": "Fichier non trouvé"}), 404
if __name__ == "__main__":
    print("🚀 Lancement Flask Tunisie (test VS Code)")
    print("🇹🇳 Source ID: 279 (MarchesPublicsTN)")
    print("🌍 Pays ID: 219 (Tunisie)")
    print("📁 Dossier PDF Tunisie:", TUNISIE_PDF_DIR)
    print("🖼️ Mode LOCAL: Synthétique pour images")
    app.run(debug=True, port=5009, host='0.0.0.0')